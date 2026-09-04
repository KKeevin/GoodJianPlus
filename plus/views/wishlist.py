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

@verified_required
def wishlist_view(request):
    """我的收藏"""
    try:
        wishlist = request.user.wishlist
        products = wishlist.products.filter(status='published')
    except:
        wishlist = Wishlist.objects.create(user=request.user)
        products = []

    from plus.services.cart import get_or_create_cart
    cart = get_or_create_cart(request)
    cart_items_map = {item.product_id: item.quantity for item in cart.items.all()}

    for product in products:
        product.cart_quantity = cart_items_map.get(product.id, 0)
        product.available_quantity = max(0, product.stock_quantity - product.cart_quantity)

    context = {
        'products': products,
    }
    return render(request, 'wishlist/wishlist.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_wishlist(request):
    """加入/移除收藏 API"""
    # 檢查用戶是否已驗證
    if not request.user.is_verified:
        return JsonResponse({
            'success': False,
            'message': '請先驗證您的電子郵件地址以使用收藏功能',
            'requires_verification': True,
            'verification_url': reverse('resend_verification_email')
        })
    
    product_id = request.POST.get('product_id')
    try:
        product = Product.objects.get(id=product_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        if product in wishlist.products.all():
            wishlist.products.remove(product)
            is_favorited = False
            message = f'已從收藏中移除 {product.name}'
        else:
            wishlist.products.add(product)
            is_favorited = True
            message = f'已將 {product.name} 加入收藏'
        return JsonResponse({
            'success': True,
            'is_favorited': is_favorited,
            'message': message
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '商品不存在'
        })
    except Exception as e:
        logger.error(f'Toggle wishlist error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '操作失敗，請稍後再試'
        })


@login_required
@require_http_methods(["POST"])
def wishlist_add_all_to_cart(request):
    from plus.services.cart import get_or_create_cart
    try:
        wishlist = request.user.wishlist
        products = wishlist.products.filter(status='published', stock_quantity__gt=0)
    except Exception:
        products = Product.objects.none()
    cart = get_or_create_cart(request)
    added = 0
    for product in products:
        existing = CartItem.objects.filter(cart=cart, product=product).first()
        if existing:
            continue
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        added += 1
    if added:
        messages.success(request, f'已將 {added} 件收藏商品加入購物車')
        return redirect('cart')
    messages.info(request, '沒有可加入的收藏商品')
    return redirect('wishlist')

