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
def notification_list_view(request):
    """通知列表頁面"""
    # 獲取篩選參數
    filter_type = request.GET.get('filter', 'all')  # all, unread, read
    
    notifications = Notification.objects.filter(user=request.user)
    
    # 根據篩選類型過濾
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_type == 'read':
        notifications = notifications.filter(is_read=True)
    # filter_type == 'all' 時不額外過濾
    
    notifications = notifications.order_by('-created_at')
    
    # 統計數量
    total_count = Notification.objects.filter(user=request.user).count()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    read_count = Notification.objects.filter(user=request.user, is_read=True).count()
    
    # 分頁
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'notifications': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'filter_type': filter_type,
        'total_count': total_count,
        'unread_count': unread_count,
        'read_count': read_count,
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
def notification_detail_view(request, notification_id):
    """通知詳情頁面"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        # 標記為已讀
        if not notification.is_read:
            notification.is_read = True
            notification.save()
    except Notification.DoesNotExist:
        messages.error(request, '通知不存在')
        return redirect('notification_list')
    
    context = {
        'notification': notification,
    }
    return render(request, 'notifications/notification_detail.html', context)


@login_required
@require_http_methods(["POST"])
def notification_toggle_read(request, notification_id):
    """切換通知已讀/未讀狀態"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = not notification.is_read
        notification.save()
        return JsonResponse({
            'success': True,
            'is_read': notification.is_read,
            'message': '已更新通知狀態'
        })
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '通知不存在'
        })


@login_required
@require_http_methods(["POST"])
def notification_delete(request, notification_id):
    """刪除通知"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.delete()
        return JsonResponse({
            'success': True,
            'message': '通知已刪除'
        })
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '通知不存在'
        })


@login_required
def notification_api(request):
    """獲取通知列表API（用於下拉菜單）"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'type': notification.type,
            'title': notification.title,
            'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
            'is_read': notification.is_read,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
            'time_ago': get_time_ago(notification.created_at),
        })
    
    return JsonResponse({
        'success': True,
        'notifications': notifications_data,
        'unread_count': unread_count,
    })


@login_required
def notification_unread_count_api(request):
    """獲取未讀通知數量API"""
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({
        'success': True,
        'unread_count': unread_count,
    })


@login_required
@require_http_methods(["POST"])
def notification_mark_all_read(request):
    """標記所有通知為已讀"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({
        'success': True,
        'message': '已標記所有通知為已讀'
    })


@login_required
@require_http_methods(["POST"])
def notification_batch_action(request):
    """批量操作通知"""
    action = request.POST.get('action')  # mark_read, mark_unread, delete
    notification_ids = request.POST.getlist('notification_ids')
    
    if not notification_ids:
        return JsonResponse({
            'success': False,
            'message': '請選擇要操作的通知'
        })
    
    try:
        # 確保只操作當前用戶的通知
        notifications = Notification.objects.filter(
            id__in=notification_ids,
            user=request.user
        )
        
        if action == 'mark_read':
            notifications.update(is_read=True)
            message = f'已標記 {notifications.count()} 則通知為已讀'
        elif action == 'mark_unread':
            notifications.update(is_read=False)
            message = f'已標記 {notifications.count()} 則通知為未讀'
        elif action == 'delete':
            count = notifications.count()
            notifications.delete()
            message = f'已刪除 {count} 則通知'
        else:
            return JsonResponse({
                'success': False,
                'message': '無效的操作'
            })
        
        return JsonResponse({
            'success': True,
            'message': message
        })
    except Exception as e:
        logger.error(f'Batch action error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '操作失敗，請稍後再試'
        })


def get_time_ago(dt):
    """獲取相對時間（如：5分鐘前）"""
    from django.utils import timezone
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 0:
        return f'{diff.days}天前'
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f'{hours}小時前'
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f'{minutes}分鐘前'
    else:
        return '剛剛'

