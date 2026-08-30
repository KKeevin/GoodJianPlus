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

def index(request):
    """首頁"""
    # 注意：網站設定已通過 context_processors 全局提供，無需在此處獲取
    # 熱銷商品：隨機撷取標示為推薦商品且商品有貨的商品
    featured_products = Product.objects.filter(
        status='published',
        is_featured=True,
        stock_quantity__gt=0  # 只顯示有庫存的商品
    ).select_related('category', 'brand').prefetch_related('images', 'reviews').annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        review_count=Count('reviews', filter=Q(reviews__is_approved=True))
    ).order_by('?')[:4]  # 隨機排序並只取4個
    # 確保 featured_products 的 avg_rating 有值
    for product in featured_products:
        if product.avg_rating is None:
            product.avg_rating = 0
        if product.review_count is None:
            product.review_count = 0
    categories = Category.objects.filter(is_active=True, parent=None).order_by('sort_order')[:3]
    user_wishlist = []
    
    # 目標管理相關數據（僅登入用戶）
    today_target = None
    today_totals = None
    goal = None
    if request.user.is_authenticated:
        try:
            wishlist = request.user.wishlist
            user_wishlist = list(wishlist.products.values_list('id', flat=True))
        except:
            pass
        
        # 獲取今日營養目標和攝取數據
        from django.utils import timezone
        from datetime import datetime as dt
        from plus.services.nutrition import get_or_create_daily_nutrition_target
        
        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        
        # 獲取或創建今日營養目標
        today_target = get_or_create_daily_nutrition_target(request.user, today)
        
        # 獲取今日營養攝取記錄
        if today_target:
            record_start = timezone.make_aware(dt.combine(today, dt.min.time()))
            record_end = timezone.make_aware(dt.combine(today, dt.max.time()))
            
            today_nutrition_logs = NutritionLog.objects.filter(
                user=request.user,
                logged_at__gte=record_start,
                logged_at__lte=record_end
            )
            
            # 計算今日總營養攝取
            today_totals = {
                'calories': Decimal('0'),
                'protein': Decimal('0'),
                'carbs': Decimal('0'),
                'fat': Decimal('0'),
            }
            for log in today_nutrition_logs:
                today_totals['calories'] += log.total_calories
                today_totals['protein'] += log.total_protein
                today_totals['carbs'] += log.total_carbs
                today_totals['fat'] += log.total_fat
        
        # 獲取目標設定
        try:
            goal = UserGoal.objects.get(user=request.user)
        except UserGoal.DoesNotExist:
            goal = None
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'user_wishlist': user_wishlist,
        'today_target': today_target,
        'today_totals': today_totals,
        'goal': goal,
    }
    
    return render(request, 'index.html', context)


def products(request):
    """商品列表頁面"""
    category_slug = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'default')
    search_query = request.GET.get('q', '').strip()
    products = Product.objects.filter(status='published').select_related('category', 'brand').prefetch_related('images', 'reviews')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        ).distinct()
    selected_category = None
    parent_category = None
    subcategories = []
    if category_slug:
        try:
            selected_category = Category.objects.get(slug=category_slug, is_active=True)
            # 檢查是否有父類別
            if selected_category.parent:
                # 這是子類別，獲取父類別和所有同級子類別（用於顯示 category-tabs）
                parent_category = selected_category.parent
                # 獲取父類別下的所有子類別
                subcategories = Category.objects.filter(
                    parent=parent_category,
                    is_active=True
                ).order_by('sort_order', 'name')
                # 只過濾該子類別的商品（不包含父類別和其他子類別）
                products = products.filter(category=selected_category)
            else:
                # 檢查是否有子類別
                subcategories = Category.objects.filter(
                    parent=selected_category,
                    is_active=True
                ).order_by('sort_order', 'name')
                
                if subcategories.exists():
                    # 這是父類別且有子類別，包含所有子類別
                    parent_category = selected_category
                    # 過濾包含主類別和所有子類別的商品
                    category_ids = [selected_category.id] + list(subcategories.values_list('id', flat=True))
                    products = products.filter(category_id__in=category_ids)
                else:
                    # 普通類別（沒有父類別也沒有子類別），只過濾該類別
                    products = products.filter(category=selected_category)
        except Category.DoesNotExist:
            pass
    
    # 計算平均評分和評價數量（在排序之前）
    products = products.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        review_count=Count('reviews', filter=Q(reviews__is_approved=True))
    )
    
    if sort_by == 'price-low':
        products = products.order_by('price')
    elif sort_by == 'price-high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'popular':
        # review_count 已經在上面計算了，不需要重複註解
        products = products.order_by('-review_count', '-created_at')
    else:
        products = products.order_by('-is_featured', '-created_at')
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # 為每個產品添加 is_new 屬性，並確保 avg_rating 有值
    seven_days_ago = datetime.now() - timedelta(days=7)
    for product in page_obj.object_list:
        product.is_new = product.created_at.date() >= seven_days_ago.date()
        # 確保 avg_rating 有值（如果沒有評價則為 None，設為 0）
        if product.avg_rating is None:
            product.avg_rating = 0
    # 獲取頂層類別（用於顯示主類別按鈕）
    categories = Category.objects.filter(is_active=True, parent=None).order_by('sort_order')
    featured_products = Product.objects.filter(
        status='published',
        is_featured=True
    ).exclude(
        id__in=[p.id for p in page_obj.object_list]
    ).select_related('category', 'brand').prefetch_related('images', 'reviews').annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        review_count=Count('reviews', filter=Q(reviews__is_approved=True))
    )[:6]
    # 確保 featured_products 的 avg_rating 有值
    for product in featured_products:
        if product.avg_rating is None:
            product.avg_rating = 0
        if product.review_count is None:
            product.review_count = 0
    user_wishlist = []
    if request.user.is_authenticated:
        try:
            wishlist = request.user.wishlist
            user_wishlist = list(wishlist.products.values_list('id', flat=True))
        except:
            pass
    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'categories': categories,
        'selected_category': selected_category,  # 傳遞對象而不只是 slug
        'selected_category_slug': category_slug,  # 保留 slug 用於比較
        'parent_category': parent_category,
        'subcategories': subcategories,
        'sort_by': sort_by,
        'search_query': search_query,
        'featured_products': featured_products,
        'user_wishlist': user_wishlist,
    }
    return render(request, 'products/products.html', context)


def search_products(request):
    """商品搜尋"""
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    products = Product.objects.filter(status='published')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query)
        )
    if category:
        products = products.filter(category__slug=category)
    context = {
        'products': products,
        'query': query,
        'category': category,
    }
    return render(request, 'products/search_results.html', context)


def product_detail_view(request, product_id):
    """商品詳情頁面"""
    try:
        product = Product.objects.get(id=product_id, status='published')
    except Product.DoesNotExist:
        messages.error(request, '商品不存在或已下架')
        return redirect('products')
    
    # 計算平均評分
    reviews = ProductReview.objects.filter(product=product, is_approved=True).order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # 檢查購物車中的數量
    cart_quantity = 0
    is_favorited = False
    user_review = None
    
    if request.user.is_authenticated:
        try:
            wishlist = request.user.wishlist
            is_favorited = product in wishlist.products.all()
        except:
            pass
        
        # 檢查購物車中該商品的數量
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.filter(cart=cart, product=product).first()
            if cart_item:
                cart_quantity = cart_item.quantity
        except Cart.DoesNotExist:
            pass
        
        # 檢查用戶是否已評價過該商品
        try:
            user_review = ProductReview.objects.filter(product=product, user=request.user).first()
        except:
            pass
    
    # 計算可購買數量（庫存 - 購物車已有數量）
    available_quantity = max(0, product.stock_quantity - cart_quantity)
    
    related_products = Product.objects.filter(
        category=product.category,
        status='published'
    ).exclude(id=product.id).annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        review_count=Count('reviews', filter=Q(reviews__is_approved=True))
    )[:4]
    
    # 確保 avg_rating 有值
    for related_product in related_products:
        if related_product.avg_rating is None:
            related_product.avg_rating = 0
    
    context = {
        'product': product,
        'reviews': reviews[:10],  # 顯示前10條評價
        'avg_rating': avg_rating,
        'is_favorited': is_favorited,
        'related_products': related_products,
        'cart_quantity': cart_quantity,
        'available_quantity': available_quantity,
        'user_review': user_review,  # 用戶的評價（如果有的話）
    }
    return render(request, 'products/product_detail.html', context)


@require_http_methods(["GET"])
def quick_view_product(request, product_id):
    """商品快速預覽 API"""
    try:
        product = Product.objects.select_related('category', 'brand').prefetch_related('images', 'reviews').get(
            id=product_id, 
            status='published'
        )
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '商品不存在或已下架'
        })
    
    # 計算平均評分
    reviews = product.reviews.filter(is_approved=True)
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    review_count = reviews.count()
    
    # 檢查購物車中的數量
    cart_quantity = 0
    is_favorited = False
    if request.user.is_authenticated:
        try:
            wishlist = request.user.wishlist
            is_favorited = product in wishlist.products.all()
        except:
            pass
        
        # 檢查購物車中該商品的數量
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.filter(cart=cart, product=product).first()
            if cart_item:
                cart_quantity = cart_item.quantity
        except Cart.DoesNotExist:
            pass
    
    # 計算可購買數量（庫存 - 購物車已有數量）
    available_quantity = max(0, product.stock_quantity - cart_quantity)
    
    # 準備商品圖片
    images = []
    for img in product.images.all()[:5]:  # 最多5張圖片
        images.append({
            'url': img.image.url,
            'alt': img.alt_text or product.name
        })
    
    if not images:
        images.append({
            'url': '/static/img/products/default.png',
            'alt': product.name
        })
    
    data = {
        'success': True,
        'product': {
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'price': float(product.price),
            'original_price': float(product.original_price) if product.original_price else None,
            'discount_percentage': product.discount_percentage,
            'short_description': product.short_description,
            'description': product.description[:200] + '...' if len(product.description) > 200 else product.description,
            'stock_quantity': product.stock_quantity,
            'cart_quantity': cart_quantity,  # 購物車中已有數量
            'available_quantity': available_quantity,  # 可購買數量
            'category': product.category.name,
            'brand': product.brand.name if product.brand else None,
            'images': images,
            'avg_rating': round(avg_rating, 1) if avg_rating else 0,
            'review_count': review_count,
            'is_favorited': is_favorited,
            'is_featured': product.is_featured,
        }
    }
    
    return JsonResponse(data)


@login_required
@require_http_methods(["POST"])
def submit_review(request):
    """提交或更新商品評價"""
    product_id = request.POST.get('product_id')
    rating = int(request.POST.get('rating', 5))
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    
    if not all([product_id, title, content]):
        return JsonResponse({
            'success': False,
            'message': '請填寫完整的評價資訊'
        })
    
    if rating < 1 or rating > 5:
        return JsonResponse({
            'success': False,
            'message': '評分必須在1-5之間'
        })
    
    try:
        product = Product.objects.get(id=product_id, status='published')
        
        # 檢查是否已經評價過
        existing_review = ProductReview.objects.filter(product=product, user=request.user).first()
        if existing_review:
            # 更新現有評價（允許用戶修改自己的評價）
            existing_review.rating = rating
            existing_review.title = title
            existing_review.content = content
            # 保留原有的 is_approved 狀態，不改變審核狀態
            existing_review.save()
            message = '評價已更新成功！'
            is_update = True
        else:
            # 創建新評價
            # 檢查是否購買過（驗證購買）
            has_purchased = OrderItem.objects.filter(
                order__user=request.user,
                order__status__in=['completed', 'delivered'],
                product=product
            ).exists()
            
            review = ProductReview.objects.create(
                product=product,
                user=request.user,
                rating=rating,
                title=title,
                content=content,
                is_verified_purchase=has_purchased,
                is_approved=True  # 可以設為需要審核
            )
            # 創建評價提交成功通知
            send_notification(
                user=request.user,
                notification_type='review',
                title='評價提交成功',
                message=f'您對「{product.name}」的評價已成功提交，感謝您的寶貴意見！'
            )
            message = '評價已提交，感謝您的回饋！'
            is_update = False
        
        logger.info(f'Review {"updated" if is_update else "submitted"} for product {product_id} by user {request.user.username}')
        return JsonResponse({
            'success': True,
            'message': message,
            'is_update': is_update
        })
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '商品不存在'
        })
    except Exception as e:
        logger.error(f'Submit review error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '提交失敗，請稍後再試'
        })


@login_required
@require_http_methods(["POST"])
def delete_review(request):
    """刪除商品評價"""
    review_id = request.POST.get('review_id')
    
    try:
        review = ProductReview.objects.get(id=review_id, user=request.user)
        product_name = review.product.name
        review.delete()
        
        logger.info(f'Review deleted by user {request.user.username}')
        return JsonResponse({
            'success': True,
            'message': '評價已刪除'
        })
        
    except ProductReview.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '評價不存在或無權限刪除'
        })
    except Exception as e:
        logger.error(f'Delete review error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '刪除失敗，請稍後再試'
        })


def get_categories_api(request):
    """取得商品分類 API"""
    categories = Category.objects.filter(is_active=True, parent=None)
    data = []
    for category in categories:
        children = []
        for child in category.children.filter(is_active=True):
            children.append({
                'id': child.id,
                'name': child.name,
                'slug': child.slug
            })
        data.append({
            'id': category.id,
            'name': category.name,
            'slug': category.slug,
            'children': children
        })
    return JsonResponse({'categories': data})

