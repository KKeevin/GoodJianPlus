from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.urls import reverse
from django.db import transaction
from django.db.models import Q, Avg, Count, Sum
from django.core.paginator import Paginator
from decimal import Decimal
import logging
import re
from datetime import datetime, timedelta

from plus.models import (
    CustomUser, UserProfile, Wishlist, Category, Brand, Product,
    ProductImage, ProductReview, Cart, CartItem, Order, OrderItem,
    Coupon, ShippingMethod, SiteSettings, Notification,
    Food, UserGoal, WeightLog, NutritionLog, DailyNutritionTarget,
    Article, ArticleCategory, ArticleImage, EmailVerificationToken,
    PhoneVerificationCode, EmailChangeRequest, ReturnRequest
)
from plus.forms import CustomUserRegistrationForm, QuickRegistrationForm, CustomAuthenticationForm
from plus.utils.email import (
    send_verification_email, send_welcome_email,
    send_password_reset_email as send_password_reset_email_util,
    send_order_status_update_email,
    send_email_change_verification_email
)
from plus.services.sms import send_sms_verification_code
from plus.services.notifications import send_notification
from plus.services.nutrition import (
    calculate_bmr, calculate_tdee, calculate_nutrition_targets,
    get_or_create_daily_nutrition_target,
)
from plus.services.checkout import (
    get_pricing_settings, resolve_shipping_fee, compute_coupon_discount,
)
from plus.decorators import verified_required
from plus.utils.request import get_client_ip
from plus.services.inventory import release_order_inventory, restore_coupon

logger = logging.getLogger(__name__)

@login_required
def order_list_view(request):
    """我的訂單列表"""
    orders = Order.objects.filter(user=request.user).prefetch_related(
        'items', 'items__product', 'items__product__images'
    ).order_by('-created_at')
    from plus.services.order_workflow import READY_PAYMENT, OPEN_STATUSES
    filters = {
        'all': ('全部', Q()),
        'unpaid': ('待付款', Q(payment_status__in=('pending', 'failed'), status__in=OPEN_STATUSES) & ~Q(payment_method='cod')),
        'preparing': ('待出貨', Q(status__in=OPEN_STATUSES) & READY_PAYMENT),
        'shipping': ('待收貨', Q(status__in=('shipped', 'delivered'))),
        'completed': ('已完成', Q(status='completed')),
        'closed': ('取消／退款', Q(status__in=('cancelled', 'refunded'))),
    }
    selected = request.GET.get('status', 'all')
    if selected not in filters:
        selected = 'all'
    tabs = [{'key': key, 'label': label, 'count': orders.filter(condition).count()}
            for key, (label, condition) in filters.items()]
    orders = orders.filter(filters[selected][1])
    query = request.GET.get('q', '').strip()[:100]
    if query:
        orders = orders.filter(Q(order_number__icontains=query) | Q(items__product_name__icontains=query)).distinct()
    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'orders': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'order_tabs': tabs, 'selected_status': selected, 'search_query': query,
    }
    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail_view(request, order_id):
    """訂單詳情"""
    try:
        order = Order.objects.prefetch_related(
            'items', 'items__product', 'items__product__images', 'return_requests', 'events'
        ).select_related('shipping_method').get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    context = {
        'order': order,
        'tracking_url': order.get_public_tracking_url(),
        'return_requests': order.return_requests.all(),
        'can_request_return': (
            order.payment_status == 'paid'
            and order.status in ('shipped', 'delivered', 'completed')
            and not order.return_requests.filter(status__in=('pending', 'approved', 'received')).exists()
        ),
        'return_reason_choices': ReturnRequest.REASON_CHOICES,
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
@require_http_methods(["POST"])
def cancel_order_view(request, order_id):
    """取消尚未付款的訂單並釋放庫存。"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    from django.core.exceptions import ValidationError
    from plus.services.order_workflow import transition_order
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk, user=request.user)
            if order.status not in ('pending', 'confirmed'):
                raise ValidationError('此訂單無法取消')
            transition_order(order.pk, 'cancelled', actor=request.user)
    except ValidationError as exc:
        messages.error(request, '；'.join(exc.messages))
        return redirect('order_detail', order_id=order.id)
    messages.success(request, '訂單已取消')
    return redirect('order_detail', order_id=order.id)


@login_required
@require_http_methods(["POST"])
def confirm_receipt_view(request, order_id):
    """確認收貨。"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    from django.core.exceptions import ValidationError
    from plus.services.order_workflow import transition_order
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk, user=request.user)
            if order.status not in ('shipped', 'delivered'):
                raise ValidationError('目前狀態無法確認收貨')
            transition_order(order.pk, 'completed', actor=request.user)
    except ValidationError as exc:
        messages.error(request, '；'.join(exc.messages))
        return redirect('order_detail', order_id=order.id)
    messages.success(request, '已確認收貨，感謝您的購買')
    return redirect('order_detail', order_id=order.id)


@login_required
@require_http_methods(["POST"])
def request_return_view(request, order_id):
    """會員申請退貨。"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    if order.payment_status != 'paid' or order.status not in ('shipped', 'delivered', 'completed'):
        messages.error(request, '此訂單目前無法申請退貨')
        return redirect('order_detail', order_id=order.id)
    if order.return_requests.filter(status__in=('pending', 'approved', 'received')).exists():
        messages.error(request, '此訂單已有進行中的退貨申請')
        return redirect('order_detail', order_id=order.id)
    reason = request.POST.get('reason', '')
    detail = request.POST.get('detail', '').strip()
    if reason not in dict(ReturnRequest.REASON_CHOICES):
        messages.error(request, '請選擇退貨原因')
        return redirect('order_detail', order_id=order.id)
    if len(detail) < 8:
        messages.error(request, '請再補充退貨說明（至少 8 個字）')
        return redirect('order_detail', order_id=order.id)
    ReturnRequest.objects.create(
        order=order,
        user=request.user,
        reason=reason,
        detail=detail,
    )
    send_notification(
        user=request.user,
        notification_type='order',
        title='已收到退貨申請',
        message=f'訂單 {order.order_number} 的退貨申請已送出，客服審核後會再通知您。',
    )
    messages.success(request, '退貨申請已送出')
    return redirect('order_detail', order_id=order.id)


@login_required
@require_http_methods(["POST"])
def cancel_return_view(request, order_id, return_id):
    """取消尚在待審核的退貨申請。"""
    try:
        rma = ReturnRequest.objects.get(id=return_id, order_id=order_id, user=request.user)
    except ReturnRequest.DoesNotExist:
        messages.error(request, '找不到退貨申請')
        return redirect('order_list')
    if rma.status != 'pending':
        messages.error(request, '此申請已在處理中，請聯絡客服')
        return redirect('order_detail', order_id=order_id)
    rma.status = 'cancelled'
    rma.save(update_fields=['status', 'updated_at'])
    messages.success(request, '已取消退貨申請')
    return redirect('order_detail', order_id=order_id)


@login_required
@require_http_methods(["POST"])
def reorder_view(request, order_id):
    from plus.services.cart import get_or_create_cart
    try:
        order = Order.objects.prefetch_related('items', 'items__product').get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    cart = get_or_create_cart(request)
    added = 0
    skipped = []
    for item in order.items.all():
        product = item.product
        if not product or product.status != 'published' or product.stock_quantity < 1:
            skipped.append(item.product_name)
            continue
        qty = min(item.quantity, product.stock_quantity)
        existing = CartItem.objects.filter(cart=cart, product=product).first()
        if existing:
            existing.quantity = min(existing.quantity + qty, product.stock_quantity)
            existing.save(update_fields=['quantity'])
        else:
            CartItem.objects.create(cart=cart, product=product, quantity=qty)
        added += 1
    if added:
        messages.success(request, f'已將 {added} 項商品加入購物車')
    if skipped:
        messages.warning(request, '以下商品目前無法再次購買：' + '、'.join(skipped[:8]))
    if not added:
        return redirect('order_detail', order_id=order.id)
    return redirect('cart')

