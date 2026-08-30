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
    PhoneVerificationCode, EmailChangeRequest
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
    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'orders': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    }
    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail_view(request, order_id):
    """訂單詳情"""
    try:
        order = Order.objects.prefetch_related(
            'items', 'items__product', 'items__product__images'
        ).get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    context = {
        'order': order,
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
    if order.payment_status == 'paid' or order.status not in ('pending', 'confirmed'):
        messages.error(request, '此訂單無法取消')
        return redirect('order_detail', order_id=order.id)
    if order.payment_status == 'paid':
        messages.error(request, '已付款訂單請聯絡客服辦理退款')
        return redirect('order_detail', order_id=order.id)
    with transaction.atomic():
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        release_order_inventory(order)
        restore_coupon(order)
    send_notification(
        user=request.user,
        notification_type='order',
        title='訂單已取消',
        message=f'您的訂單 {order.order_number} 已取消，庫存已釋出。',
    )
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
    if order.status not in ('shipped', 'delivered'):
        messages.error(request, '目前狀態無法確認收貨')
        return redirect('order_detail', order_id=order.id)
    order.status = 'completed'
    order.delivered_at = order.delivered_at or timezone.now()
    order.save(update_fields=['status', 'delivered_at'])
    messages.success(request, '已確認收貨，感謝您的購買')
    return redirect('order_detail', order_id=order.id)

