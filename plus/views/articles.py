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

def articles_list_view(request):
    """健康專欄文章列表"""
    category_slug = request.GET.get('category', '')
    view_mode = request.GET.get('view', 'list')  # 'list' 或 'grid'
    search_query = request.GET.get('q', '').strip()
    
    # 獲取所有分類
    categories = ArticleCategory.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    # 獲取文章
    articles = Article.objects.filter(status='published').select_related('category', 'author').prefetch_related('images')
    
    # 分類篩選
    selected_category = None
    if category_slug:
        try:
            selected_category = ArticleCategory.objects.get(slug=category_slug, is_active=True)
            articles = articles.filter(category=selected_category)
        except ArticleCategory.DoesNotExist:
            pass
    
    # 搜尋
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query)
        )
    
    # 排序
    articles = articles.order_by('-published_at', '-created_at')
    
    # 分頁
    paginator = Paginator(articles, 12)  # 每頁12篇文章
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'articles': page_obj,
        'categories': categories,
        'selected_category': selected_category,
        'view_mode': view_mode,
        'search_query': search_query,
    }
    
    return render(request, 'articles/articles_list.html', context)


def article_detail_view(request, slug):
    """文章詳情頁"""
    try:
        article = Article.objects.select_related('category', 'author').prefetch_related('images').get(
            slug=slug, 
            status='published'
        )
    except Article.DoesNotExist:
        from django.http import Http404
        raise Http404("文章不存在")
    
    # 增加瀏覽次數
    article.view_count += 1
    article.save(update_fields=['view_count'])
    
    # 獲取相關文章（同分類的其他文章）
    related_articles = Article.objects.filter(
        category=article.category,
        status='published'
    ).exclude(id=article.id).order_by('-published_at', '-created_at')[:6]
    
    # 獲取所有分類（用於側邊欄）
    categories = ArticleCategory.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    context = {
        'article': article,
        'related_articles': related_articles,
        'categories': categories,
    }
    
    return render(request, 'articles/article_detail.html', context)

