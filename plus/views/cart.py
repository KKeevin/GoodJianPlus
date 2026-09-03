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


def cart_view(request):
    """購物車頁面"""
    from plus.services.cart import get_or_create_cart
    cart = get_or_create_cart(request)
    items = cart.items.select_related('product').prefetch_related('product__images').all()
    # 獲取免運門檻（從網站設定）
    try:
        site_settings = SiteSettings.objects.first()
        free_shipping_threshold = site_settings.free_shipping_threshold if site_settings else Decimal('1000')
    except:
        free_shipping_threshold = Decimal('1000')
    
    free_shipping_remaining = 0
    if cart and cart.total_price < free_shipping_threshold:
        free_shipping_remaining = free_shipping_threshold - cart.total_price
    recommended_products = []
    if items:
        product_ids = [item.product.id for item in items]
        recommended_products = Product.objects.filter(
            status='published'
        ).exclude(
            id__in=product_ids
        ).select_related('category', 'brand').prefetch_related('images', 'reviews').annotate(
            avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
            review_count=Count('reviews', filter=Q(reviews__is_approved=True))
        ).order_by('-updated_at', '-id')[:4]
        
        # 確保 avg_rating 有值
        for product in recommended_products:
            if product.avg_rating is None:
                product.avg_rating = 0
    context = {
        'cart': cart,
        'items': items,
        'recommended_products': recommended_products,
        'free_shipping_remaining': int(free_shipping_remaining),
        'free_shipping_threshold': float(free_shipping_threshold),
    }
    return render(request, 'cart/cart.html', context)


def cart_count_api(request):
    """購物車數量 API"""
    from plus.services.cart import get_or_create_cart
    cart = get_or_create_cart(request)
    return JsonResponse({'count': cart.total_items})


@require_http_methods(["POST"])
def add_to_cart(request):
    """加入購物車 API"""
    from plus.services.cart import get_or_create_cart
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    try:
        product = Product.objects.get(id=product_id, status='published')
        if product.stock_quantity < quantity:
            if request.user.is_authenticated:
                send_notification(
                    user=request.user,
                    notification_type='cart',
                    title='商品庫存不足',
                    message=f'很抱歉，{product.name} 目前庫存不足（僅剩 {product.stock_quantity} 件），無法加入購物車。'
                )
            return JsonResponse({
                'success': False,
                'message': '庫存不足'
            })
        cart = get_or_create_cart(request)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        # 獲取商品圖片
        product_image_url = ''
        if product.images.exists():
            product_image_url = product.images.first().image.url
        else:
            product_image_url = '/static/img/products/default.png'
        
        # 計算購物車中該商品的數量（更新後的數量）
        cart_quantity = cart_item.quantity
        
        # 計算可購買數量（庫存 - 購物車已有數量）
        available_quantity = max(0, product.stock_quantity - cart_quantity)
        
        # 返回購物車項目詳細信息
        return JsonResponse({
            'success': True,
            'message': f'已將 {product.name} 加入購物車',
            'cart_count': cart.total_items,
            'cart_quantity': cart_quantity,  # 購物車中該商品的數量
            'available_quantity': available_quantity,  # 可購買數量
            'stock_quantity': product.stock_quantity,  # 總庫存
            'cart_item': {
                'id': cart_item.id,
                'product_id': product.id,
                'product_name': product.name,
                'product_sku': product.sku,
                'product_price': int(product.price),
                'quantity': cart_item.quantity,
                'subtotal': int(cart_item.subtotal),
                'stock_quantity': product.stock_quantity,
                'product_image_url': product_image_url,
                'is_new_item': created
            }
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '商品不存在'
        })
    except Exception as e:
        logger.error(f'Add to cart error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '加入購物車失敗，請稍後再試'
        })


@require_http_methods(["POST"])
def update_cart_item(request):
    """更新購物車項目數量"""
    from plus.services.cart import get_or_create_cart
    item_id = request.POST.get('item_id')
    quantity = int(request.POST.get('quantity', 1))
    if quantity < 1:
        return JsonResponse({
            'success': False,
            'message': '數量不能少於1'
        })
    try:
        cart = get_or_create_cart(request)
        item = CartItem.objects.get(id=item_id, cart=cart)
        if item.product.stock_quantity < quantity:
            if request.user.is_authenticated:
                send_notification(
                    user=request.user,
                    notification_type='cart',
                    title='購物車商品庫存不足',
                    message=f'{item.product.name} 目前庫存不足（僅剩 {item.product.stock_quantity} 件），請調整購買數量。'
                )
            return JsonResponse({
                'success': False,
                'message': f'庫存不足，僅剩 {item.product.stock_quantity} 件'
            })
        item.quantity = quantity
        item.save()
        return JsonResponse({
            'success': True,
            'message': '數量已更新',
            'subtotal': int(item.subtotal),
            'cart_count': item.cart.total_items
        })
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '購物車項目不存在'
        })
    except Exception as e:
        logger.error(f'Update cart item error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '更新失敗，請稍後再試'
        })


@require_http_methods(["POST"])
def remove_cart_item(request):
    """從購物車移除項目"""
    from plus.services.cart import get_or_create_cart
    item_id = request.POST.get('item_id')
    try:
        cart = get_or_create_cart(request)
        item = CartItem.objects.get(id=item_id, cart=cart)
        product_name = item.product.name
        item.delete()
        cart_empty = not cart.items.exists()
        return JsonResponse({
            'success': True,
            'message': f'已將 {product_name} 從購物車移除',
            'cart_empty': cart_empty,
            'cart_count': cart.total_items
        })
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '購物車項目不存在'
        })
    except Exception as e:
        logger.error(f'Remove cart item error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '移除失敗，請稍後再試'
        })


def cart_totals(request):
    """取得購物車總計資訊"""
    from plus.services.cart import get_or_create_cart
    try:
        try:
            site_settings = SiteSettings.objects.first()
            free_shipping_threshold = site_settings.free_shipping_threshold if site_settings else Decimal('1000')
        except Exception:
            free_shipping_threshold = Decimal('1000')
        
        cart = get_or_create_cart(request)
        subtotal = cart.total_price
        shipping_fee = Decimal('0') if subtotal >= free_shipping_threshold else Decimal('100')
        total = subtotal + shipping_fee
        return JsonResponse({
            'subtotal': int(subtotal),
            'shipping_fee': int(shipping_fee),
            'total': int(total)
        })
    except Exception:
        return JsonResponse({
            'subtotal': 0,
            'shipping_fee': 0,
            'total': 0
        })

