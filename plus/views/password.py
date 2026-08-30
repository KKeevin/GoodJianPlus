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
from plus.utils.ratelimit import ratelimit

logger = logging.getLogger(__name__)

@ratelimit(limit=5, window=600)
@require_http_methods(["POST"])
def send_password_reset_email(request):
    """發送密碼重設郵件"""
    email = request.POST.get('email', '').strip()
    if not email:
        return JsonResponse({
            'success': False,
            'message': '請輸入電子郵件'
        })
    try:
        user = CustomUser.objects.get(email=email)
        # 發送密碼重設郵件
        success = send_password_reset_email_util(user, request)
        if success:
            logger.info(f'Password reset email sent to: {email}')
            return JsonResponse({
                'success': True,
                'message': '重設密碼連結已發送至您的信箱，請檢查您的郵件。'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '發送失敗，請稍後再試。'
            })
    except CustomUser.DoesNotExist:
        # 為了安全，即使郵件不存在也返回成功訊息
        return JsonResponse({
            'success': True,
            'message': '如果該電子郵件已註冊，我們已發送重設連結至您的信箱。'
        })
    except Exception as e:
        logger.error(f'Password reset error for {email}: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '發送失敗，請稍後再試。'
        })


@login_required
@require_http_methods(["POST"])
def set_password(request):
    """設定密碼（僅限沒有密碼的用戶，一次性機會）"""
    user = request.user
    
    # 檢查用戶是否已有密碼
    if user.has_usable_password():
        return JsonResponse({
            'success': False,
            'message': '您已經設定過密碼了'
        }, status=400)
    
    new_password = request.POST.get('new_password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()
    
    # 驗證輸入
    if not new_password or not confirm_password:
        return JsonResponse({
            'success': False,
            'message': '請填寫完整資訊'
        })
    
    # 驗證新密碼長度
    if len(new_password) < 8:
        return JsonResponse({
            'success': False,
            'message': '密碼長度至少需要 8 個字元'
        })
    
    # 驗證兩次輸入的密碼是否一致
    if new_password != confirm_password:
        return JsonResponse({
            'success': False,
            'message': '兩次輸入的密碼不一致'
        })
    
    try:
        # 設置新密碼
        user.set_password(new_password)
        user.save()
        
        # 更新會話認證 hash，保持用戶登入狀態
        update_session_auth_hash(request, user)
        
        # 創建密碼設定成功通知
        send_notification(
            user=user,
            notification_type='system',
            title='密碼設定成功',
            message='您的密碼已成功設定，請妥善保管。'
        )
        
        logger.info(f'Password set successfully for user: {user.username}')
        return JsonResponse({
            'success': True,
            'message': '密碼已成功設定！'
        })
    except Exception as e:
        logger.error(f'Set password error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '設定失敗，請稍後再試'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def change_password(request):
    """變更密碼 API"""
    old_password = request.POST.get('old_password', '').strip()
    new_password = request.POST.get('new_password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()
    
    # 驗證輸入
    if not old_password or not new_password or not confirm_password:
        return JsonResponse({
            'success': False,
            'message': '請填寫完整資訊'
        })
    
    # 驗證舊密碼
    if not check_password(old_password, request.user.password):
        return JsonResponse({
            'success': False,
            'message': '原始密碼錯誤'
        })
    
    # 驗證新密碼長度
    if len(new_password) < 8:
        return JsonResponse({
            'success': False,
            'message': '新密碼長度至少需要 8 個字元'
        })
    
    # 驗證兩次輸入的新密碼是否一致
    if new_password != confirm_password:
        return JsonResponse({
            'success': False,
            'message': '兩次輸入的新密碼不一致'
        })
    
    # 驗證新密碼不能與舊密碼相同
    if check_password(new_password, request.user.password):
        return JsonResponse({
            'success': False,
            'message': '新密碼不能與舊密碼相同'
        })
    
    try:
        # 設置新密碼
        request.user.set_password(new_password)
        request.user.save()
        
        # 更新會話認證 hash，保持用戶登入狀態
        update_session_auth_hash(request, request.user)
        
        # 創建密碼變更成功通知
        send_notification(
            user=request.user,
            notification_type='system',
            title='密碼變更成功',
            message='您的密碼已成功變更，如有疑問請聯繫客服。'
        )
        
        logger.info(f'Password changed successfully for user: {request.user.username}')
        return JsonResponse({
            'success': True,
            'message': '密碼已成功變更'
        })
    except Exception as e:
        logger.error(f'Error changing password for user {request.user.username}: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '變更密碼時發生錯誤，請稍後再試'
        })


def password_reset_confirm(request, token):
    """密碼重設確認頁面"""
    try:
        # 檢查 token 是否存在
        try:
            reset_token = EmailVerificationToken.objects.get(
                token=token,
                token_type='password_reset'
            )
        except EmailVerificationToken.DoesNotExist:
            logger.warning(f'Invalid password reset token: {token[:20]}...')
            messages.error(request, '無效的重設連結，請重新申請密碼重設。')
            context = {
                'token': token,
                'error': '無效的重設連結，請重新申請密碼重設。',
                'is_invalid': True
            }
            return render(request, 'registration/password_reset_confirm.html', context)
        except Exception as e:
            logger.error(f'Error querying password reset token: {str(e)}', exc_info=True)
            messages.error(request, '處理過程中發生錯誤，請稍後再試。')
            context = {
                'token': token,
                'error': '處理過程中發生錯誤，請稍後再試。',
                'is_invalid': True
            }
            return render(request, 'registration/password_reset_confirm.html', context)
        
        # 檢查 Token 是否已被使用
        if reset_token.is_used:
            logger.warning(f'Password reset token already used for user {reset_token.user.username}')
            messages.error(request, '此重設連結已被使用，請重新申請密碼重設。')
            context = {
                'token': token,
                'error': '此重設連結已被使用，請重新申請密碼重設。',
                'is_used': True
            }
            return render(request, 'registration/password_reset_confirm.html', context)
        
        # 檢查 Token 是否有效（未過期）
        if not reset_token.is_valid():
            logger.warning(f'Expired password reset token for user {reset_token.user.username}')
            messages.error(request, '重設連結已過期，請重新申請密碼重設。')
            context = {
                'token': token,
                'error': '重設連結已過期，請重新申請密碼重設。',
                'is_expired': True
            }
            return render(request, 'registration/password_reset_confirm.html', context)
        
        # 處理 POST 請求（提交新密碼）
        if request.method == 'POST':
            new_password = request.POST.get('new_password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()
            
            if not new_password or not confirm_password:
                messages.error(request, '請填寫完整資訊。')
            elif new_password != confirm_password:
                messages.error(request, '兩次輸入的密碼不一致。')
            elif len(new_password) < 8:
                messages.error(request, '密碼長度至少需要 8 個字元。')
            else:
                try:
                    # 設置新密碼
                    user = reset_token.user
                    user.set_password(new_password)
                    user.save()
                    
                    # 標記 Token 為已使用
                    reset_token.is_used = True
                    reset_token.save()
                    
                    # 創建密碼重設成功通知
                    send_notification(
                        user=user,
                        notification_type='password_reset',
                        title='密碼重設成功',
                        message='您的密碼已成功重設，如有疑問請聯繫客服。'
                    )
                    
                    logger.info(f'Password reset successful for user: {user.username}')
                    messages.success(request, '密碼已成功重設，請使用新密碼登入。')
                    return redirect('login')
                except Exception as e:
                    logger.error(f'Error setting new password for user {reset_token.user.username}: {str(e)}', exc_info=True)
                    messages.error(request, '重設密碼時發生錯誤，請稍後再試。')
        
        # GET 請求：顯示重設密碼表單
        context = {
            'token': token,
            'is_valid': True
        }
        return render(request, 'registration/password_reset_confirm.html', context)
    except Exception as e:
        # 最外層異常處理，捕獲所有未預期的錯誤
        logger.error(f'Unexpected error in password_reset_confirm view: {str(e)}', exc_info=True)
        messages.error(request, '處理過程中發生未預期的錯誤，請稍後再試。')
        context = {
            'token': token,
            'error': '處理過程中發生未預期的錯誤，請稍後再試。',
            'is_invalid': True
        }
        try:
            return render(request, 'registration/password_reset_confirm.html', context)
        except Exception as render_error:
            logger.error(f'Failed to render error template: {str(render_error)}', exc_info=True)
            from django.http import HttpResponse
            return HttpResponse(
                '<html><body><h1>密碼重設錯誤</h1><p>處理過程中發生錯誤，請聯繫客服。</p><a href="/login/">返回登入頁面</a></body></html>',
                status=500
            )

