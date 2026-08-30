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
from social_core.exceptions import AuthForbidden

logger = logging.getLogger(__name__)

def associate_by_email(strategy, details, backend, user=None, social=None, *args, **kwargs):
    """如果社交登入的 email 已存在於系統中，關聯到現有用戶而不是創建新用戶（支援 Google 和 Facebook）"""
    backend_name = backend.name if hasattr(backend, 'name') else str(backend)
    
    # 如果已經有用戶（從 social_user 步驟找到），也要保存原始姓名
    if user is not None:
        # 重新從資料庫載入用戶，確保獲取最新的資料
        user.refresh_from_db()
        kwargs['user'] = user
        kwargs['is_new'] = False
        # 保存原始姓名（防止 user.user_details 覆蓋）
        kwargs['original_first_name'] = user.first_name if user.first_name else ''
        kwargs['original_last_name'] = user.last_name if user.last_name else ''
        logger.info(f'{backend_name} OAuth: User found via social_user, saved original name - first_name: "{kwargs["original_first_name"]}", last_name: "{kwargs["original_last_name"]}"')
        return kwargs
    
    # 如果沒有用戶，檢查 email 是否已存在
    if details.get('email'):
        email = details.get('email')
        try:
            # 查找是否有現有用戶使用此 email
            existing_user = CustomUser.objects.filter(email=email).first()
            if existing_user:
                if not existing_user.email_verified:
                    logger.warning(
                        f'{backend_name} OAuth: refused to bind unverified email {email}'
                    )
                    raise AuthForbidden(backend)
                logger.info(f'{backend_name} OAuth: Email {email} already exists, associating with user {existing_user.username}')
                # 重新從資料庫載入用戶，確保獲取最新的資料
                existing_user.refresh_from_db()
                kwargs['user'] = existing_user
                kwargs['is_new'] = False
                # 保存原始姓名
                kwargs['original_first_name'] = existing_user.first_name if existing_user.first_name else ''
                kwargs['original_last_name'] = existing_user.last_name if existing_user.last_name else ''
                logger.info(f'{backend_name} OAuth: Saved original name - first_name: "{kwargs["original_first_name"]}", last_name: "{kwargs["original_last_name"]}"')
                # 確保後續步驟知道用戶已存在，不會創建新用戶
                return kwargs
        except AuthForbidden:
            raise
        except Exception as e:
            logger.error(f'Error checking existing email in {backend_name} OAuth: {str(e)}')
    
    return kwargs


def social_auth_pipeline(strategy, details, backend, user=None, social=None, *args, **kwargs):
    """社交登入管道處理函數 - 更新用戶驗證狀態和資料（支援 Google 和 Facebook）"""
    if user:
        updated = False
        is_new_user = kwargs.get('is_new', False)
        backend_name = backend.name if hasattr(backend, 'name') else str(backend)
        
        # 如果社交帳號有 email，標記為已驗證
        if details.get('email'):
            if user.email == details.get('email') and not user.email_verified:
                user.email_verified = True
                updated = True
            elif not user.email:
                user.email = details.get('email')
                user.email_verified = True
                updated = True
        
        # 處理姓名
        if is_new_user:
            # 新用戶：使用社交帳號的 first_name，清空 last_name
            social_first_name = details.get('first_name', '').strip()
            if social_first_name:
                user.first_name = social_first_name
                updated = True
            if user.last_name:
                user.last_name = ''
                updated = True
        else:
            # 現有用戶：如果原本有名字就保持，如果原本沒有名字就用社交帳號的
            if 'original_first_name' in kwargs:
                original_first_name = kwargs['original_first_name']
                if original_first_name:
                    # 原本有名字，恢復原始名字
                    if user.first_name != original_first_name:
                        user.first_name = original_first_name
                        updated = True
                else:
                    # 原本沒有名字，使用社交帳號的名字
                    social_first_name = details.get('first_name', '').strip()
                    if social_first_name and user.first_name != social_first_name:
                        user.first_name = social_first_name
                        updated = True
            
            if 'original_last_name' in kwargs:
                original_last_name = kwargs['original_last_name']
                if original_last_name:
                    # 原本有姓氏，恢復原始姓氏
                    if user.last_name != original_last_name:
                        user.last_name = original_last_name
                        updated = True
                else:
                    # 原本沒有姓氏，清空（因為我們只使用 first_name）
                    if user.last_name:
                        user.last_name = ''
                        updated = True
        
        # 如果用戶是新建的，發送歡迎通知
        if updated:
            user.save()
        
        if is_new_user:
            # 新用戶，發送歡迎通知
            try:
                provider_name = 'Google' if 'google' in backend_name.lower() else 'Facebook' if 'facebook' in backend_name.lower() else '社群'
                send_notification(
                    user=user,
                    notification_type='system',
                    title='歡迎加入好健健！',
                    message=f'感謝您使用 {provider_name} 帳號註冊，歡迎加入好健健大家庭！'
                )
            except:
                pass
        
        logger.info(f'{backend_name} OAuth: User {user.username} logged in via {backend_name} (is_new: {is_new_user})')
    
    return kwargs


def google_login(request):
    """Google 登入入口 - 重定向到 social_django 的認證流程"""
    from django.urls import reverse
    # 保存 next 參數到 session
    next_url = safe_redirect_url(request, request.GET.get('next'), fallback='/')
    if next_url:
        request.session['next_url'] = next_url
    
    # 重定向到 social_django 的 Google OAuth 認證
    return redirect(reverse('social:begin', args=['google-oauth2']))


def facebook_login(request):
    """Facebook 登入入口 - 重定向到 social_django 的認證流程"""
    from django.urls import reverse
    # 保存 next 參數到 session
    next_url = safe_redirect_url(request, request.GET.get('next'), fallback='/')
    if next_url:
        request.session['next_url'] = next_url
    
    # 重定向到 social_django 的 Facebook OAuth 認證
    return redirect(reverse('social:begin', args=['facebook']))


def line_login(request):
    """LINE 登入入口 - 重定向到 social_django 的認證流程"""
    from django.urls import reverse
    # 保存 next 參數到 session
    next_url = safe_redirect_url(request, request.GET.get('next'), fallback='/')
    if next_url:
        request.session['next_url'] = next_url
    
    # 重定向到 social_django 的 LINE OAuth 認證
    return redirect(reverse('social:begin', args=['line']))


@login_required
def google_callback(request):
    """Google 登入回調處理 - 這個函數實際上不會被直接調用，因為 social_django 會自動處理"""
    # social_django 會自動處理回調，這個函數只是作為備用
    next_url = safe_redirect_url(request, request.session.pop('next_url', '/'), fallback='/')
    messages.success(request, f'歡迎回來，{request.user.first_name or request.user.username}！')
    return redirect(next_url)


def social_auth_error(request):
    """處理社交登入錯誤（例如用戶取消授權）"""
    # social_django 會將錯誤訊息和類型作為 URL 參數傳遞
    error_message = request.GET.get('message', '')
    error_type = request.GET.get('error', '')
    backend = request.GET.get('backend', '')
    
    # 根據後端判斷是哪個社交平台
    provider_name = '社群'
    if 'google' in backend.lower():
        provider_name = 'Google'
    elif 'facebook' in backend.lower():
        provider_name = 'Facebook'
    
    # 檢查是否為用戶取消授權
    if 'access_denied' in request.GET or 'canceled' in error_message.lower() or 'AuthCanceled' in error_type:
        messages.warning(request, f'您已取消 {provider_name} 登入授權。如需使用 {provider_name} 登入，請重新嘗試並完成授權。')
    elif error_message:
        messages.error(request, f'登入過程中發生錯誤：{error_message}')
    elif error_type:
        messages.error(request, f'登入過程中發生錯誤：{error_type}')
    else:
        messages.warning(request, '登入過程中發生錯誤，請稍後再試。')
    
    return redirect('login')


def social_auth_complete(request, backend, *args, **kwargs):
    """包裝 social_django 的 complete 視圖，處理 AuthCanceled 異常"""
    from social_django.views import complete as social_complete
    from social_core.exceptions import AuthCanceled, AuthException
    
    # 判斷是哪個社交平台
    provider_name = '社群'
    if 'google' in backend.lower():
        provider_name = 'Google'
    elif 'facebook' in backend.lower():
        provider_name = 'Facebook'
    elif 'line' in backend.lower():
        provider_name = 'LINE'
    
    try:
        return social_complete(request, backend, *args, **kwargs)
    except AuthCanceled:
        messages.warning(request, f'您已取消 {provider_name} 登入授權。如需使用 {provider_name} 登入，請重新嘗試並完成授權。')
        return redirect('login')
    except AuthException as e:
        messages.error(request, f'登入過程中發生錯誤：{str(e)}')
        return redirect('login')

