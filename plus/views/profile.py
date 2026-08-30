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

@login_required
def user_profile_view(request):
    """用戶個人資料頁面"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    # 處理 POST 請求（保存基本資料）
    if request.method == 'POST':
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
    """個人資料完善頁面"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    if request.method == 'POST':
        # 保存舊的體重和身高值，用於比較是否有變化
        old_weight = profile.weight
        old_height = profile.height
        
        profile.gender = request.POST.get('gender', '')
        # 身高和體重直接存儲為小數（支援小數點第二位）
        height_value = request.POST.get('height')
        new_height = Decimal(height_value) if height_value else None
        profile.height = new_height
        weight_value = request.POST.get('weight')
        new_weight = Decimal(weight_value) if weight_value else None
        profile.weight = new_weight
        profile.fitness_goal = request.POST.get('fitness_goal', '')
        profile.dietary_restrictions = request.POST.get('dietary_restrictions', '')
        
        # 只有在表單中有提供這些字段時才更新（避免清除基本資料）
        if 'birthday' in request.POST:
            birthday_value = request.POST.get('birthday', '').strip()
            if birthday_value:
                try:
                    from datetime import datetime
                    request.user.birthday = datetime.strptime(birthday_value, '%Y-%m-%d').date()
                except ValueError:
                    pass  # 如果日期格式錯誤，保留原值
            else:
                request.user.birthday = None
        
        if 'address' in request.POST:
            request.user.address = request.POST.get('address', '').strip()
        
        # 只有在表單中有提供這些字段時才更新（避免清除基本資料）
        if 'first_name' in request.POST:
            request.user.first_name = request.POST.get('first_name', '').strip()
        
        if 'phone' in request.POST:
            new_phone = request.POST.get('phone', '').strip()
            old_phone = request.user.phone
            
            # 如果手機號碼改變了
            if new_phone != old_phone:
                # 檢查新手機號碼是否已被其他帳號認證
                other_verified_user = CustomUser.objects.filter(
                    phone=new_phone,
                    phone_verified=True
                ).exclude(id=request.user.id).first()
                
                if other_verified_user:
                    messages.error(request, '此手機號碼已被其他帳號認證，無法使用。請使用其他手機號碼。')
                    return redirect('profile_complete')
                
                # 取消手機驗證狀態
                request.user.phone_verified = False
                logger.info(f'用戶修改手機號碼，取消驗證狀態: {request.user.username} ({old_phone} -> {new_phone})')
            
            request.user.phone = new_phone
        try:
            request.user.save()
            profile.save()
            
            # 如果體重或身高有變化，創建新的體重記錄
            weight_changed = new_weight is not None and (old_weight is None or new_weight != old_weight)
            height_changed = new_height is not None and (old_height is None or new_height != old_height)
            
            if weight_changed or height_changed:
                if new_weight is not None:
                    change_notes = []
                    if weight_changed:
                        change_notes.append('體重')
                    if height_changed:
                        change_notes.append('身高')
                    notes_text = '、'.join(change_notes) + '變更' if change_notes else '資料更新'
                    
                    WeightLog.objects.create(
                        user=request.user,
                        weight=new_weight,
                        notes=f'從會員資料更新：{notes_text}'
                    )
            
            # 同步更新到目標管理 (UserGoal)
            try:
                from datetime import date
                goal, goal_created = UserGoal.objects.get_or_create(user=request.user)
                
                # 同步身高（UserProfile 現在直接存儲為小數）
                if profile.height:
                    goal.height = Decimal(str(profile.height))
                
                # 同步體重（UserProfile 現在直接存儲為小數）
                if profile.weight:
                    goal.current_weight = Decimal(str(profile.weight))
                
                # 同步性別 (UserProfile: 'M'/'F' -> UserGoal: 'male'/'female')
                if profile.gender:
                    gender_map = {'M': 'male', 'F': 'female'}
                    goal.gender = gender_map.get(profile.gender)
                
                # 同步年齡 (從生日計算)
                if request.user.birthday:
                    today = date.today()
                    goal.age = today.year - request.user.birthday.year - ((today.month, today.day) < (request.user.birthday.month, request.user.birthday.day))
                
                # 如果所有必要數據都有了，重新計算 BMR 和 TDEE
                if goal.current_weight and goal.height and goal.age and goal.gender:
                    from plus.services.nutrition import calculate_bmr, calculate_tdee, calculate_nutrition_targets
                    bmr = calculate_bmr(goal.current_weight, goal.height, goal.age, goal.gender)
                    if bmr:
                        goal.bmr = bmr
                        tdee = calculate_tdee(bmr, goal.activity_level)
                        if tdee:
                            goal.tdee = tdee
                            target_calories, target_protein, target_carbs, target_fat = calculate_nutrition_targets(tdee, goal.goal_type)
                            if target_calories:
                                goal.target_calories = target_calories
                                goal.target_protein = target_protein
                                goal.target_carbs = target_carbs
                                goal.target_fat = target_fat
                
                goal.save()
            except Exception as e:
                logger.error(f'Sync profile to goal error: {str(e)}')
                # 不影響會員資料更新的成功返回
            
            messages.success(request, '個人資料已更新！')
            return redirect('profile')
        except Exception as e:
            logger.error(f'Profile update error for user {request.user.id}: {str(e)}')
            messages.error(request, '更新失敗，請稍後再試。')
    context = {
        'profile': profile,
        'user': request.user,
    }
    return render(request, 'registration/profile_completion.html', context)


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

