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
from plus.forms_account import FitnessProfileForm, ShippingAddressForm
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

@login_required
def user_profile_view(request, *, fitness_form=None, address_form=None, editing_address=None, active_tab=None):
    """用戶個人資料頁面"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    # 處理 POST 請求（保存基本資料）
    if request.method == 'POST' and fitness_form is None and address_form is None:
        try:
            # 更新用戶基本資料
            user = request.user
            user.first_name = request.POST.get('first_name', '').strip()
            
            # 檢查手機號碼是否改變
            # 如果欄位是 disabled，POST 中不會有 phone 值，需要保留原值
            new_phone = request.POST.get('phone', '').strip()
            old_phone = user.phone
            
            # 如果 POST 中沒有 phone 值（欄位是 disabled），保留原值
            if 'phone' not in request.POST:
                new_phone = old_phone
            
            # 如果手機號碼改變了
            if new_phone != old_phone:
                # 檢查新手機號碼是否已被其他帳號認證
                other_verified_user = CustomUser.objects.filter(
                    phone=new_phone,
                    phone_verified=True
                ).exclude(id=user.id).first()
                
                if other_verified_user:
                    messages.error(request, '此手機號碼已被其他帳號認證，無法使用。請使用其他手機號碼。')
                    return redirect('profile')
                
                # 取消手機驗證狀態
                user.phone_verified = False
                logger.info(f'用戶修改手機號碼，取消驗證狀態: {user.username} ({old_phone} -> {new_phone})')
            
            user.phone = new_phone
            birthday_str = request.POST.get('birthday', '').strip()
            if birthday_str:
                try:
                    from datetime import datetime
                    user.birthday = datetime.strptime(birthday_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            user.address = request.POST.get('address', '').strip()
            user.save()
            
            messages.success(request, '基本資料已成功更新！')
            return redirect('profile')
        except Exception as e:
            logger.error(f'Profile update error: {str(e)}')
            messages.error(request, '更新失敗，請稍後再試。')
    
    # 計算總訂單數和最近訂單
    orders_count = Order.objects.filter(user=request.user).count()
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # 計算訂單統計
    total_spent = Order.objects.filter(
        user=request.user,
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # 計算收藏商品數
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist_count = wishlist.products.count()
    except Wishlist.DoesNotExist:
        wishlist_count = 0
    
    # 計算未讀通知數
    unread_notifications_count = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).count()
    
    # 計算體重記錄數
    weight_logs_count = WeightLog.objects.filter(user=request.user).count()
    
    # 計算營養記錄數（今天）
    from datetime import datetime as dt
    from django.utils import timezone
    local_now = timezone.localtime(timezone.now())
    today = local_now.date()
    today_start = timezone.make_aware(dt.combine(today, dt.min.time()))
    today_end = timezone.make_aware(dt.combine(today, dt.max.time()))
    today_nutrition_count = NutritionLog.objects.filter(
        user=request.user,
        logged_at__gte=today_start,
        logged_at__lte=today_end
    ).count()
    
    # 檢查是否有目標設定
    has_goal = UserGoal.objects.filter(user=request.user).exists()
    
    context = {
        'active_tab': active_tab or (request.GET.get('tab') if request.GET.get('tab') in {'info', 'fitness', 'addresses', 'orders', 'security'} else 'info'),
        'fitness_form': fitness_form if fitness_form is not None else FitnessProfileForm(instance=profile, prefix='fitness'),
        'address_form': address_form if address_form is not None else ShippingAddressForm(prefix='shipping', initial={
            'label': '住家', 'name': request.user.first_name or request.user.username,
            'phone': request.user.phone, 'address': request.user.address,
            'is_default': not request.user.shipping_addresses.exists(),
        }),
        'editing_address': editing_address,
        'addresses': request.user.shipping_addresses.all(),
        'fitness_completed': sum(bool(value) for value in [profile.gender, profile.height, profile.weight, profile.fitness_goal]),
        'user': request.user,
        'profile': profile,
        'orders_count': orders_count,
        'recent_orders': recent_orders,
        'total_spent': total_spent,
        'wishlist_count': wishlist_count,
        'unread_notifications_count': unread_notifications_count,
        'weight_logs_count': weight_logs_count,
        'today_nutrition_count': today_nutrition_count,
        'has_goal': has_goal,
        'needs_profile_update': request.user.needs_profile_update,
    }
    return render(request, 'registration/profile.html', context)


@login_required
def profile_completion_view(request):
    """Save fitness details from the account tab, retaining errors in place."""
    if request.method != 'POST':
        return redirect(reverse('profile') + '?tab=fitness')
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    old_weight, old_height = profile.weight, profile.height
    form = FitnessProfileForm(request.POST, instance=profile,
                              prefix='fitness' if 'fitness-gender' in request.POST else None)
    if not form.is_valid():
        return user_profile_view(request, fitness_form=form, active_tab='fitness')
    try:
        with transaction.atomic():
            profile = form.save()
            weight_changed = profile.weight is not None and profile.weight != old_weight
            height_changed = profile.height is not None and profile.height != old_height
            if profile.weight is not None and (weight_changed or height_changed):
                WeightLog.objects.create(user=request.user, weight=profile.weight,
                                         notes='從會員健身資料更新')
            # Height and current_weight are read-only properties backed by UserProfile.
            goal, _ = UserGoal.objects.get_or_create(user=request.user)
            goal.gender = {'M': 'male', 'F': 'female'}.get(profile.gender)
            birthday = request.user.birthday
            today = timezone.localdate()
            if birthday:
                goal.age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            if goal.age is not None and goal.age <= 0:
                goal.age = None
            goal.bmr = calculate_bmr(profile.weight, profile.height, goal.age, goal.gender)
            goal.tdee = calculate_tdee(goal.bmr, goal.activity_level)
            (goal.target_calories, goal.target_protein, goal.target_carbs,
             goal.target_fat) = calculate_nutrition_targets(goal.tdee, goal.goal_type)
            goal.save()
        messages.success(request, '健身資料已儲存！')
        return redirect(reverse('profile') + '?tab=fitness')
    except Exception:
        logger.exception('Fitness profile update failed for user %s', request.user.pk)
        form.add_error(None, '儲存失敗，請稍後再試。您的輸入內容已保留。')
    return user_profile_view(request, fitness_form=form, active_tab='fitness')


@login_required
def phone_profile_update_view(request):
    """手機註冊用戶更新電子郵件（僅限一次，需郵件驗證）"""
    user = request.user
    
    # 如果用戶已經完成更新，跳轉到首頁
    if not user.needs_profile_update:
        messages.info(request, '您已經完成資料更新了！')
        return redirect('home')
    
    # 檢查是否已經有待驗證的郵件變更請求
    pending_request = EmailChangeRequest.objects.filter(
        user=user,
        is_used=False
    ).first()
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        errors = []
        
        # 驗證電子郵件
        if not email:
            errors.append('請輸入電子郵件')
        elif '@' not in email or '.' not in email.split('@')[1]:
            errors.append('請輸入有效的電子郵件格式')
        elif email == user.email:
            errors.append('新電子郵件與當前電子郵件相同')
        elif CustomUser.objects.filter(email=email).exclude(id=user.id).exists():
            errors.append('此電子郵件已被使用')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # 發送郵件驗證
            old_email = user.email
            success = send_email_change_verification_email(user, email, request)
            
            if success:
                messages.success(request, f'驗證郵件已發送至 {email}，請檢查您的郵件並點擊確認連結以完成變更。')
                logger.info(f'手機註冊用戶請求變更郵件: {user.username} ({old_email} -> {email})')
            else:
                messages.error(request, '郵件發送失敗，請稍後再試')
    
    context = {
        'user': user,
        'pending_request': pending_request,
    }
    return render(request, 'registration/phone_profile_update.html', context)


@login_required
@login_required
def verify_email_change(request, token):
    """驗證電子郵件變更"""
    try:
        change_request = EmailChangeRequest.objects.get(token=token, is_used=False)
        
        # 檢查 Token 是否有效
        if not change_request.is_valid():
            messages.error(request, '驗證連結已過期，請重新申請變更。')
            return redirect('phone_profile_update')
        
        # 檢查是否為當前用戶
        if change_request.user != request.user:
            messages.error(request, '無效的驗證連結。')
            return redirect('home')
        
        # 檢查新郵件是否已被使用
        if CustomUser.objects.filter(email=change_request.new_email).exclude(id=request.user.id).exists():
            change_request.is_used = True
            change_request.save()
            messages.error(request, '此電子郵件已被其他帳號使用，無法變更。')
            return redirect('phone_profile_update')
        
        # 更新電子郵件
        old_email = request.user.email
        request.user.email = change_request.new_email
        request.user.email_verified = True  # 郵件變更驗證成功，標記為已認證（is_verified 會自動計算）
        request.user.needs_profile_update = False  # 標記為已完成更新
        request.user.save(update_fields=['email', 'email_verified', 'is_verified', 'needs_profile_update'])
        
        # 標記請求為已使用
        change_request.is_used = True
        change_request.save()
        
        logger.info(f'手機註冊用戶完成郵件變更: {request.user.username} ({old_email} -> {change_request.new_email})')
        messages.success(request, f'電子郵件已成功變更為 {change_request.new_email}！')
        return redirect('profile')
        
    except EmailChangeRequest.DoesNotExist:
        messages.error(request, '無效的驗證連結。')
        return redirect('home')
    except Exception as e:
        logger.error(f'Email change verification error: {str(e)}')
        messages.error(request, '驗證過程中發生錯誤，請稍後再試。')
        return redirect('home')
