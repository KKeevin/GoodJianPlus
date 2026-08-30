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
from plus.utils.http import safe_redirect_url

logger = logging.getLogger(__name__)

def register_view(request):
    """會員註冊頁面"""
    if request.user.is_authenticated:
        messages.info(request, '您已經登入了！')
        return redirect('home')
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    # 設置用戶為未驗證狀態
                    user.email_verified = False  # 註冊時郵件尚未驗證
                    user.phone_verified = False  # 註冊時手機尚未驗證（通過郵件註冊）
                    user.save()  # is_verified 會自動計算為 False
                    Wishlist.objects.create(user=user)
                    logger.info(f'New user registered: {user.username} ({user.email})')
                    
                    # 發送郵件驗證信
                    send_verification_email(user, request)
                    
                    # 發送歡迎郵件（不包含驗證連結）
                    send_welcome_email(user)
                    
                    username = form.cleaned_data.get('username')
                    password = form.cleaned_data.get('password1')
                    user = authenticate(username=username, password=password)
                    if user is not None:
                        login(request, user)
                        # 創建註冊成功通知
                        send_notification(
                            user=user,
                            notification_type='registration',
                            title='歡迎加入好健健！',
                            message='感謝您註冊成為好健健會員！我們已發送驗證郵件至您的信箱，請驗證您的電子郵件地址以享受完整服務。'
                        )
                        messages.success(request, f'歡迎加入好健健，{user.first_name}！我們已發送驗證郵件至您的信箱，請驗證您的電子郵件地址。')
                        next_url = safe_redirect_url(request, request.GET.get('next'))
                        return redirect(next_url)
                    else:
                        messages.success(request, '註冊成功！我們已發送驗證郵件至您的信箱，請驗證後重新登入。')
                        return redirect('login')
            except Exception as e:
                logger.error(f'Registration error: {str(e)}')
                messages.error(request, '註冊過程中發生錯誤，請稍後再試。')
        else:
            messages.error(request, '註冊資料有誤，請檢查後重新提交。')
    else:
        form = CustomUserRegistrationForm()
    context = {
        'form': form,
        'page_title': '會員註冊',
        'meta_description': '加入好健健會員，享受專業健身器材、營養餐盒和個人化健康服務',
    }
    return render(request, 'registration/register.html', context)


def registration_success_view(request):
    """註冊成功頁面"""
    if not request.user.is_authenticated:
        return redirect('login')
    context = {
        'user': request.user,
        'show_completion_prompt': not hasattr(request.user, 'profile') or not request.user.profile.fitness_goal
    }
    return render(request, 'registration/success.html', context)


@require_http_methods(["POST"])
def quick_register_view(request):
    """快速註冊（AJAX）"""
    form = QuickRegistrationForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                # 設置用戶為未驗證狀態（is_verified 會自動計算）
                user.email_verified = False
                user.phone_verified = False
                user.save()
                Wishlist.objects.create(user=user)
                login(request, user)
                
                # 發送郵件驗證信
                send_verification_email(user, request)
                
                # 發送歡迎郵件
                send_welcome_email(user)
                
                # 創建註冊成功通知
                send_notification(
                    user=user,
                    notification_type='registration',
                    title='歡迎加入好健健！',
                    message='感謝您註冊成為好健健會員！我們已發送驗證郵件至您的信箱，請驗證您的電子郵件地址以享受完整服務。'
                )
                return JsonResponse({
                    'success': True,
                    'message': '註冊成功！我們已發送驗證郵件至您的信箱，請驗證您的電子郵件地址。',
                    'redirect_url': reverse('home')
                })
        except Exception as e:
            logger.error(f'Quick registration error: {str(e)}')
            return JsonResponse({
                'success': False,
                'message': '註冊過程中發生錯誤，請稍後再試。'
            })
    else:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]
        return JsonResponse({
            'success': False,
            'message': '註冊資料有誤',
            'errors': errors
        })


@require_http_methods(["POST"])
def check_username_availability(request):
    """檢查使用者名稱是否可用（AJAX）"""
    username = request.POST.get('username', '').strip()
    if not username:
        return JsonResponse({'available': False, 'message': '請輸入使用者名稱'})
    if len(username) < 3:
        return JsonResponse({'available': False, 'message': '使用者名稱至少需要3個字元'})
    if CustomUser.objects.filter(username=username).exists():
        return JsonResponse({'available': False, 'message': '此使用者名稱已被使用'})
    forbidden_words = ['admin', 'root', 'administrator', 'goodjian', '管理員']
    if any(word in username.lower() for word in forbidden_words):
        return JsonResponse({'available': False, 'message': '此使用者名稱不可使用'})
    return JsonResponse({'available': True, 'message': '使用者名稱可以使用'})


@require_http_methods(["POST"])
def check_email_availability(request):
    """檢查電子郵件是否可用（AJAX）"""
    email = request.POST.get('email', '').strip()
    if not email:
        return JsonResponse({'available': False, 'message': '請輸入電子郵件'})
    if CustomUser.objects.filter(email=email).exists():
        return JsonResponse({'available': False, 'message': '此電子郵件已被註冊'})
    return JsonResponse({'available': True, 'message': '電子郵件可以使用'})


@require_http_methods(["POST"])
def suggest_usernames(request):
    """建議可用的使用者名稱（AJAX）"""
    base_username = request.POST.get('username', '').strip()
    if not base_username:
        return JsonResponse({'suggestions': []})
    base_username = re.sub(r'[^a-zA-Z0-9_]', '', base_username)
    if len(base_username) < 2:
        return JsonResponse({'suggestions': []})
    suggestions = generate_username_suggestions(base_username)
    return JsonResponse({'suggestions': suggestions})


def generate_username_suggestions(base_username):
    """根據基礎使用者名稱產生建議"""
    suggestions = []
    for i in range(1, 100):
        suggestion = f"{base_username}{i}"
        if not CustomUser.objects.filter(username=suggestion).exists():
            suggestions.append(suggestion)
            if len(suggestions) >= 5:
                break
    if len(suggestions) < 5:
        for _ in range(5 - len(suggestions)):
            random_suffix = get_random_string(3, allowed_chars='0123456789')
            suggestion = f"{base_username}{random_suffix}"
            if not CustomUser.objects.filter(username=suggestion).exists():
                suggestions.append(suggestion)
    return suggestions

