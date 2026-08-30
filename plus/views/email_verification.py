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

def verify_email(request, token):
    """郵件驗證視圖"""
    try:
        verification_token = EmailVerificationToken.objects.get(
            token=token,
            token_type='email_verification',
            is_used=False
        )
        
        # 檢查 Token 是否有效
        if not verification_token.is_valid():
            messages.error(request, '驗證連結已過期，請重新申請驗證郵件。')
            return redirect('resend_verification_email')
        
        # 驗證用戶郵件（is_verified 會自動計算）
        user = verification_token.user
        user.email_verified = True
        user.save(update_fields=['email_verified', 'is_verified'])
        
        # 標記 Token 為已使用
        verification_token.is_used = True
        verification_token.save()
        
        # 創建驗證成功通知
        send_notification(
            user=user,
            notification_type='system',
            title='郵件驗證成功',
            message='您的電子郵件地址已成功驗證，現在可以享受完整的會員服務了！'
        )
        
        logger.info(f'Email verified for user: {user.username}')
        messages.success(request, '您的電子郵件地址已成功驗證！')
        
        # 如果用戶已登入，重定向到首頁；否則重定向到登入頁面
        if request.user.is_authenticated and request.user == user:
            return redirect('home')
        else:
            messages.info(request, '請登入以享受完整服務。')
            return redirect('login')
            
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, '無效的驗證連結，請檢查您的郵件或重新申請驗證。')
        return redirect('resend_verification_email')
    except Exception as e:
        logger.error(f'Email verification error: {str(e)}')
        messages.error(request, '驗證過程中發生錯誤，請稍後再試。')
        return redirect('home')


@login_required
def resend_verification_email(request):
    """重新發送驗證郵件"""
    if request.user.email_verified:
        messages.info(request, '您的電子郵件已經驗證過了。')
        return redirect('home')
    
    try:
        success = send_verification_email(request.user, request)
        if success:
            messages.success(request, '驗證郵件已重新發送，請檢查您的信箱。')
        else:
            messages.error(request, '發送失敗，請稍後再試。')
    except Exception as e:
        logger.error(f'Resend verification email error: {str(e)}')
        messages.error(request, '發送失敗，請稍後再試。')
    
    return redirect('profile')

