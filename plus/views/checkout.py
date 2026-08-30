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

logger = logging.getLogger(__name__)

@login_required
def checkout(request):
    """結帳頁面"""
    try:
        cart = Cart.objects.get(user=request.user)
        items = cart.items.select_related('product').prefetch_related('product__images').all()
        if not items:
            messages.warning(request, '購物車是空的，無法結帳')
            return redirect('cart')
    except Cart.DoesNotExist:
        messages.warning(request, '購物車是空的，無法結帳')
        return redirect('cart')
    
    free_shipping_threshold, tax_rate = get_pricing_settings()
    
    # 計算金額
    subtotal = cart.total_price
    shipping_fee = resolve_shipping_fee(subtotal, free_shipping_threshold)
    tax_amount = subtotal * tax_rate
    total_amount = subtotal + shipping_fee + tax_amount
    
    # 取得配送方式
    shipping_methods = ShippingMethod.objects.filter(is_active=True).order_by('sort_order')
    
    # 取得用戶資訊
    user = request.user
    
    if request.method == 'POST':
        # 處理訂單提交
        shipping_name = request.POST.get('shipping_name', user.first_name or user.username)
        shipping_phone = request.POST.get('shipping_phone', user.phone)
        shipping_email = request.POST.get('shipping_email', user.email)
        shipping_address = request.POST.get('shipping_address', user.address)
        shipping_notes = request.POST.get('shipping_notes', '')
        shipping_method_id = request.POST.get('shipping_method')
        coupon_code = request.POST.get('coupon_code', '').strip()
        
        # 驗證必填欄位
        if not all([shipping_name, shipping_phone, shipping_email, shipping_address]):
            messages.error(request, '請填寫完整的收件人資訊')
            return redirect('checkout')
        
        try:
            with transaction.atomic():
                # 驗證庫存
                for item in items:
                    if item.product.stock_quantity < item.quantity:
                        messages.error(request, f'{item.product.name} 庫存不足')
                        return redirect('cart')
                
                shipping_fee = resolve_shipping_fee(
                    subtotal, free_shipping_threshold, shipping_method_id
                )
                
                # 重新計算稅額（基於商品小計）
                tax_amount = subtotal * tax_rate
                
                discount_amount, shipping_fee, coupon, _coupon_info, coupon_error = compute_coupon_discount(
                    coupon_code, subtotal, shipping_fee
                )
                if coupon_error:
                    messages.warning(request, coupon_error)
                elif coupon:
                    coupon.used_count += 1
                    coupon.save()
                
                # 計算最終金額
                final_total = subtotal + shipping_fee + tax_amount - discount_amount
                
                # 取得支付方式
                payment_method = request.POST.get('payment_method', 'cod')
                
                # 建立訂單
                order = Order.objects.create(
                    user=user,
                    shipping_name=shipping_name,
                    shipping_phone=shipping_phone,
                    shipping_email=shipping_email,
                    shipping_address=shipping_address,
                    shipping_notes=shipping_notes,
                    subtotal=subtotal,
                    shipping_fee=shipping_fee,
                    tax_amount=tax_amount,
                    discount_amount=discount_amount,
                    total_amount=final_total,
                    status='pending',
                    payment_status='pending',
                    payment_method=payment_method
                )
                
                # 建立訂單項目並減少庫存
                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_name=item.product.name,
                        product_sku=item.product.sku,
                        unit_price=item.product.price,
                        quantity=item.quantity,
                        subtotal=item.subtotal
                    )
                    # 減少庫存（預留庫存）
                    item.product.stock_quantity -= item.quantity
                    item.product.save()
                
                # 建立通知
                Notification.objects.create(
                    user=user,
                    type='order',
                    title='訂單已建立',
                    message=f'您的訂單 {order.order_number} 已成功建立，請盡快完成付款。'
                )
                
                logger.info(f'Order created: {order.order_number} by user {user.username}')
                
                # 訂單已建立，清空購物車（這是正確的邏輯）
                cart.items.all().delete()
                
                # 如果是貨到付款，直接跳轉到訂單詳情
                if payment_method == 'cod':
                    messages.success(request, f'訂單已成功建立！訂單編號：{order.order_number}')
                    return redirect('order_detail', order_id=order.id)
                else:
                    # 線上支付：跳轉到支付頁面（購物車已清空，但可以從訂單頁面繼續付款）
                    return redirect('payment', order_id=order.id)
                
        except Exception as e:
            logger.error(f'Checkout error: {str(e)}')
            messages.error(request, '訂單建立失敗，請稍後再試')
            return redirect('checkout')
    
    context = {
        'cart': cart,
        'items': items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'shipping_methods': shipping_methods,
        'user': user,
    }
    return render(request, 'checkout/checkout.html', context)


@login_required
@require_http_methods(["POST"])
def calculate_checkout_price(request):
    """計算結帳價格 API（用於優惠券和配送方式改變時）"""
    try:
        cart = Cart.objects.get(user=request.user)
        items = cart.items.select_related('product').all()
        if not items:
            return JsonResponse({
                'success': False,
                'message': '購物車是空的'
            })
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '購物車是空的'
        })
    
    free_shipping_threshold, tax_rate = get_pricing_settings()
    
    subtotal = cart.total_price
    shipping_method_id = request.POST.get('shipping_method')
    shipping_fee = resolve_shipping_fee(subtotal, free_shipping_threshold, shipping_method_id)
    tax_amount = subtotal * tax_rate
    
    coupon_code = request.POST.get('coupon_code', '').strip()
    discount_amount, shipping_fee, _coupon, coupon_info, coupon_error = compute_coupon_discount(
        coupon_code, subtotal, shipping_fee
    )
    if coupon_error:
        return JsonResponse({
            'success': False,
            'message': coupon_error
        })
    
    total_amount = subtotal + shipping_fee + tax_amount - discount_amount
    
    return JsonResponse({
        'success': True,
        'subtotal': float(subtotal),
        'shipping_fee': float(shipping_fee),
        'tax_amount': float(tax_amount),
        'discount_amount': float(discount_amount),
        'total_amount': float(total_amount),
        'coupon': coupon_info
    })

