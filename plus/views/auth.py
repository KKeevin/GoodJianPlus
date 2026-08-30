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

def custom_login_view(request):
    """登入頁面"""
    if request.user.is_authenticated:
        messages.info(request, '您已經登入了！')
        return redirect('home')
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = request.POST.get('remember_me')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if remember_me:
                    request.session.set_expiry(30 * 24 * 60 * 60)
                else:
                    request.session.set_expiry(0)
                logger.info(f'User logged in: {user.username}')
                next_url = request.POST.get('next') or request.GET.get('next', 'home')
                messages.success(request, f'歡迎回來，{user.first_name or user.username}！')
                return redirect(next_url)
            else:
                form.add_error(None, '使用者名稱或密碼錯誤')
                logger.warning(f'Failed login attempt for username: {username}')
        else:
            messages.error(request, '登入資料有誤，請檢查後重新提交。')
    else:
        form = CustomAuthenticationForm()
    context = {
        'form': form,
        'next': request.GET.get('next', ''),
        'page_title': '會員登入',
        'meta_description': '登入好健健會員帳戶，享受個人化健身服務和專屬優惠',
    }
    return render(request, 'registration/login.html', context)


def custom_logout_view(request):
    """登出"""
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        logger.info(f'User logged out: {username}')
        messages.success(request, '您已成功登出！')
    return redirect('home')


@require_http_methods(["POST"])
def ajax_login(request):
    """AJAX 登入"""
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    remember_me = request.POST.get('remember_me') == 'on'
    if not username or not password:
        return JsonResponse({
            'success': False,
            'message': '請填寫完整的登入資訊'
        })
    if '@' in username:
        try:
            user = CustomUser.objects.get(email=username)
            username = user.username
        except CustomUser.DoesNotExist:
            pass
    user = authenticate(username=username, password=password)
    if user is not None:
        login(request, user)
        if remember_me:
            request.session.set_expiry(30 * 24 * 60 * 60)
        else:
            request.session.set_expiry(0)
        logger.info(f'User logged in via AJAX: {user.username}')
        return JsonResponse({
            'success': True,
            'message': f'歡迎回來，{user.first_name or user.username}！',
            'redirect_url': '/'
        })
    else:
        logger.warning(f'Failed AJAX login attempt for: {username}')
        return JsonResponse({
            'success': False,
            'message': '使用者名稱或密碼錯誤'
        })


def check_login_status(request):
    """檢查登入狀態 API"""
    if request.user.is_authenticated:
        return JsonResponse({
            'logged_in': True,
            'username': request.user.username,
            'first_name': request.user.first_name,
            'email': request.user.email
        })
    else:
        return JsonResponse({'logged_in': False})


@require_http_methods(["POST"])
def validate_login_credentials(request):
    """驗證登入憑證（不實際登入）"""
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    if not username or not password:
        return JsonResponse({
            'valid': False,
            'message': '請填寫完整資訊'
        })
    if '@' in username:
        try:
            user = CustomUser.objects.get(email=username)
            username = user.username
        except CustomUser.DoesNotExist:
            pass
    user = authenticate(username=username, password=password)
    if user is not None:
        return JsonResponse({
            'valid': True,
            'message': '憑證有效'
        })
    else:
        return JsonResponse({
            'valid': False,
            'message': '使用者名稱或密碼錯誤'
        })

