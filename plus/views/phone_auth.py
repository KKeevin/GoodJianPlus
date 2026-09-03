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
from plus.utils.ratelimit import ratelimit

logger = logging.getLogger(__name__)

@ratelimit(limit=5, window=600)
@require_http_methods(["POST"])
def send_phone_verification_code(request):
    """發送手機驗證碼"""
    try:
        phone = request.POST.get('phone', '').strip()
        
        # 驗證手機號碼格式（台灣手機號碼：09xxxxxxxx）
        if not phone or not re.match(r'^09\d{8}$', phone):
            return JsonResponse({
                'success': False,
                'message': '請輸入正確的手機號碼格式（09xxxxxxxx）'
            }, status=400)
        
        # 檢查該手機號碼是否已被其他帳號使用
        if request.user.is_authenticated:
            # 已登入狀態：檢查是否已被其他帳號認證
            other_verified_user = CustomUser.objects.filter(
                phone=phone,
                phone_verified=True
            ).exclude(id=request.user.id).first()
            
            if other_verified_user:
                return JsonResponse({
                    'success': False,
                    'message': '此手機號碼已被其他帳號認證，無法發送驗證碼。請使用其他手機號碼。'
                }, status=400)
        else:
            # 未登入狀態（登入頁面）：檢查是否已被其他帳號使用但未驗證
            unverified_user = CustomUser.objects.filter(
                phone=phone,
                phone_verified=False
            ).first()
            
            if unverified_user:
                return JsonResponse({
                    'success': False,
                    'message': '此手機號碼已被使用但尚未驗證，請先在會員中心完成手機號碼驗證後再使用手機登入。'
                }, status=400)
        
        # 檢查發送頻率（同一手機號碼 60 秒內只能發送一次）
        recent_code = PhoneVerificationCode.objects.filter(
            phone=phone,
            created_at__gte=timezone.now() - timedelta(seconds=60),
            is_used=False
        ).first()
        
        if recent_code:
            remaining_seconds = 60 - (timezone.now() - recent_code.created_at).total_seconds()
            return JsonResponse({
                'success': False,
                'message': f'請稍候 {int(remaining_seconds)} 秒後再試'
            }, status=429)
        
        # 生成驗證碼
        code = PhoneVerificationCode.generate_code()
        
        # 保存驗證碼到資料庫
        verification_code = PhoneVerificationCode.objects.create(
            phone=phone,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=10),  # 10 分鐘有效
            ip_address=get_client_ip(request)
        )
        
        # 發送 SMS
        sms_sent = send_sms_verification_code(phone, code)
        
        if not sms_sent:
            verification_code.delete()  # 如果發送失敗，刪除記錄
            return JsonResponse({
                'success': False,
                'message': '驗證碼發送失敗，請稍後再試'
            }, status=500)
        
        logger.info(f'手機驗證碼已發送到 {phone}')
        
        return JsonResponse({
            'success': True,
            'message': '驗證碼已發送至您的手機'
        })
        
    except Exception as e:
        logger.error(f'發送手機驗證碼錯誤: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '系統錯誤，請稍後再試'
        }, status=500)


@ratelimit(limit=8, window=60)
@require_http_methods(["POST"])
def phone_login(request):
    """手機號碼登入/註冊"""
    try:
        phone = request.POST.get('phone', '').strip()
        code = request.POST.get('verification_code', '').strip()
        remember_me = request.POST.get('remember_me', 'false').lower() == 'true'
        next_url = request.POST.get('next', '') or request.GET.get('next', '')
        
        # 驗證輸入
        if not phone or not re.match(r'^09\d{8}$', phone):
            return JsonResponse({
                'success': False,
                'message': '請輸入正確的手機號碼格式'
            }, status=400)
        
        if not code or len(code) != 6 or not code.isdigit():
            return JsonResponse({
                'success': False,
                'message': '請輸入6位數驗證碼'
            }, status=400)
        
        # 查找有效的驗證碼
        verification_code = PhoneVerificationCode.objects.filter(
            phone=phone,
            code=code,
            is_used=False
        ).order_by('-created_at').first()
        
        if not verification_code or not verification_code.is_valid():
            return JsonResponse({
                'success': False,
                'message': '驗證碼錯誤或已過期，請重新發送'
            }, status=400)
        
        # 標記驗證碼為已使用
        verification_code.is_used = True
        verification_code.save()
        
        # 查找或創建用戶
        # 優先選擇已認證的手機號碼對應的帳號
        verified_user = CustomUser.objects.filter(phone=phone, phone_verified=True).first()
        
        if verified_user:
            # 如果有已認證的帳號，使用該帳號登入
            user = verified_user
            logger.info(f'用戶通過手機登入（已認證帳號）: {user.username} (phone: {phone})')
        else:
            # 如果沒有已認證的帳號，檢查是否有未認證的帳號
            unverified_user = CustomUser.objects.filter(phone=phone, phone_verified=False).first()
            
            if unverified_user:
                # 如果有未認證的帳號，返回錯誤
                return JsonResponse({
                    'success': False,
                    'message': '此手機號碼尚未完成驗證，請先在會員中心完成手機號碼驗證後再使用手機登入。'
                }, status=400)
            
            # 如果完全沒有該手機號碼的帳號，自動註冊新用戶
            username = f'user_{phone}'  # 使用手機號碼作為預設用戶名
            # 確保用戶名唯一
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f'user_{phone}_{counter}'
                counter += 1
            
            try:
                # 創建用戶時不設置密碼，讓用戶在首次登入時設定
                user = CustomUser.objects.create_user(
                    username=username,
                    phone=phone,
                    email=f'{username}@temp.goodjian.shop',  # 臨時郵箱
                    phone_verified=True,  # 手機號碼已認證（is_verified 會自動計算）
                    needs_profile_update=True,  # 標記需要更新資料
                    password=None,  # 不設置密碼，讓用戶在首次登入時設定
                )
                # 清除密碼，確保用戶沒有可用密碼
                user.set_unusable_password()
                user.save()
                
                # 創建用戶資料
                UserProfile.objects.create(user=user)
                
                # 創建購物車
                Cart.objects.create(user=user)
                
                # 創建收藏清單
                Wishlist.objects.create(user=user)
                
                logger.info(f'新用戶通過手機註冊: {phone} (username: {username})')
            except Exception as e:
                logger.error(f'創建用戶失敗: {str(e)}')
                return JsonResponse({
                    'success': False,
                    'message': '註冊失敗，請稍後再試'
                }, status=500)
        
        # 登入用戶
        session_key = request.session.session_key
        login(request, user)
        from plus.services.cart import merge_session_cart
        merge_session_cart(request, user, session_key=session_key)
        
        # 設置 session 過期時間
        if remember_me:
            request.session.set_expiry(30 * 24 * 60 * 60)  # 30 天
        else:
            request.session.set_expiry(0)  # 瀏覽器關閉時過期
        
        # 處理跳轉 URL
        # 如果是新註冊的用戶，需要先更新資料
        if user.needs_profile_update:
            from django.urls import reverse
            redirect_url = reverse('phone_profile_update')
        elif not next_url:
            redirect_url = '/'
        else:
            redirect_url = safe_redirect_url(request, next_url, fallback='/')
        
        return JsonResponse({
            'success': True,
            'message': '登入成功！',
            'redirect_url': redirect_url,
            'needs_profile_update': user.needs_profile_update
        })
        
    except Exception as e:
        logger.error(f'手機登入錯誤: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '系統錯誤，請稍後再試'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def verify_phone_in_profile(request):
    """在個人資料頁面驗證手機號碼"""
    try:
        phone = request.POST.get('phone', '').strip()
        code = request.POST.get('verification_code', '').strip()
        
        # 驗證輸入
        if not phone or not re.match(r'^09\d{8}$', phone):
            return JsonResponse({
                'success': False,
                'message': '請輸入正確的手機號碼格式'
            }, status=400)
        
        if not code or len(code) != 6 or not code.isdigit():
            return JsonResponse({
                'success': False,
                'message': '請輸入6位數驗證碼'
            }, status=400)
        
        # 檢查手機號碼是否與當前用戶的手機號碼一致
        # 如果不一致，先保存手機號碼（用戶可能在驗證前修改了手機號碼但還沒保存）
        if phone != request.user.phone:
            # 檢查新手機號碼是否已被其他帳號認證
            other_verified_user = CustomUser.objects.filter(
                phone=phone,
                phone_verified=True
            ).exclude(id=request.user.id).first()
            
            if other_verified_user:
                return JsonResponse({
                    'success': False,
                    'message': '此手機號碼已被其他帳號認證，無法使用。請使用其他手機號碼。'
                }, status=400)
            
            # 保存新的手機號碼（is_verified 會自動計算）
            request.user.phone = phone
            request.user.phone_verified = False  # 取消之前的驗證狀態
            request.user.save(update_fields=['phone', 'phone_verified', 'is_verified'])
        
        # 檢查該手機號碼是否已被其他帳號認證
        other_verified_user = CustomUser.objects.filter(
            phone=phone,
            phone_verified=True
        ).exclude(id=request.user.id).first()
        
        if other_verified_user:
            return JsonResponse({
                'success': False,
                'message': '此手機號碼已被其他帳號認證，無法再次認證。請使用其他手機號碼。'
            }, status=400)
        
        # 查找有效的驗證碼
        verification_code = PhoneVerificationCode.objects.filter(
            phone=phone,
            code=code,
            is_used=False
        ).order_by('-created_at').first()
        
        if not verification_code or not verification_code.is_valid():
            return JsonResponse({
                'success': False,
                'message': '驗證碼錯誤或已過期，請重新發送'
            }, status=400)
        
        # 標記驗證碼為已使用
        verification_code.is_used = True
        verification_code.save()
        
        # 確保手機號碼被保存（如果用戶在驗證時填寫了新的手機號碼但還沒保存）
        if request.user.phone != phone:
            request.user.phone = phone
        
        # 設置手機號碼為已驗證（is_verified 會自動計算）
        request.user.phone_verified = True
        request.user.save(update_fields=['phone', 'phone_verified', 'is_verified'])
        
        # 發送手機號碼驗證成功通知
        send_notification(
            user=request.user,
            notification_type='system',
            title='手機號碼已驗證',
            message='恭喜！您的手機號碼已成功驗證。現在您可以使用手機號碼登入，並享受更安全的帳號保護。'
        )
        
        logger.info(f'用戶在個人資料頁面完成手機驗證: {request.user.username} (phone: {phone})')
        
        return JsonResponse({
            'success': True,
            'message': '手機號碼驗證成功！現在您可以使用手機號碼登入了。'
        })
        
    except Exception as e:
        logger.error(f'手機驗證錯誤: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '驗證過程中發生錯誤，請稍後再試'
        }, status=500)

