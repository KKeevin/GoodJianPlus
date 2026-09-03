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
    Coupon, ShippingMethod, SiteSettings, Notification, NewsletterSubscriber,
    Food, UserGoal, WeightLog, NutritionLog, DailyNutritionTarget,
    Article, ArticleCategory, ArticleImage, EmailVerificationToken,
    PhoneVerificationCode, EmailChangeRequest
)
from plus.forms import CustomUserRegistrationForm, QuickRegistrationForm, CustomAuthenticationForm
from plus.utils.ratelimit import ratelimit
from django.core.mail import send_mail
from django.conf import settings as django_settings
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

def privacy_policy_view(request):
    """隱私政策頁面"""
    return render(request, 'legal/privacy_policy.html')


def terms_of_service_view(request):
    """服務條款頁面"""
    return render(request, 'legal/terms_of_service.html')


def delete_account_view(request):
    """用戶資料刪除說明頁面"""
    return render(request, 'legal/delete_account.html')


def shipping_info_view(request):
    """配送資訊頁面"""
    return render(request, 'customer_service/shipping_info.html')


def return_policy_view(request):
    """退換貨政策頁面"""
    return render(request, 'customer_service/return_policy.html')


def faq_view(request):
    """常見問題頁面"""
    return render(request, 'customer_service/faq.html')


@ratelimit(limit=5, window=300)
def contact_us_view(request):
    """聯絡客服頁面"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip() or '網站留言'
        message = request.POST.get('message', '').strip()
        if not name or not email or not message:
            messages.error(request, '請填寫姓名、信箱與內容')
            return redirect('contact_us')
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            messages.error(request, '請輸入正確的電子郵件')
            return redirect('contact_us')
        site = SiteSettings.objects.first()
        to_email = (site.contact_email if site else '') or django_settings.DEFAULT_FROM_EMAIL
        body = f'姓名：{name}\n信箱：{email}\n\n{message}'
        try:
            send_mail(
                subject=f'[客服留言] {subject}',
                message=body,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            messages.success(request, '已送出，我們會盡快回覆您')
        except Exception:
            logger.exception('Contact form email failed')
            messages.error(request, '信件暫時無法送出，請改用上方信箱或電話聯絡')
        return redirect('contact_us')
    return render(request, 'customer_service/contact_us.html')


@require_http_methods(["POST"])
@ratelimit(limit=8, window=300)
def newsletter_subscribe(request):
    """電子報訂閱"""
    email = request.POST.get('email', '').strip().lower()
    if not email:
        return JsonResponse({
            'success': False,
            'message': '請輸入電子郵件'
        })
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return JsonResponse({
            'success': False,
            'message': '請輸入正確的電子郵件格式'
        })
    subscriber, created = NewsletterSubscriber.objects.update_or_create(
        email=email,
        defaults={'is_active': True},
    )
    logger.info('Newsletter subscription: %s created=%s', email, created)
    return JsonResponse({
        'success': True,
        'message': '感謝您的訂閱！我們將定期發送最新資訊給您。'
    })


def page_not_found(request, exception):
    return render(request, 'errors/404.html', status=404)


def server_error(request):
    return render(request, 'errors/500.html', status=500)

