from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
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
from plus.services.inventory import release_order_inventory, restore_coupon
from django.conf import settings

logger = logging.getLogger(__name__)

@login_required
def payment_view(request, order_id):
    """支付頁面"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        if order.payment_status == 'paid':
            messages.info(request, '此訂單已完成付款')
            return redirect('order_detail', order_id=order.id)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    
    context = {
        'order': order,
        'allow_test_payment': settings.DEBUG,
        'ecpay_enabled': bool(getattr(settings, 'ECPAY_MERCHANT_ID', '')),
        'linepay_enabled': bool(getattr(settings, 'LINE_PAY_CHANNEL_ID', '')),
    }
    return render(request, 'payment/payment.html', context)


@login_required
@require_http_methods(["POST"])
def process_payment(request, order_id):
    """處理支付"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        if order.payment_status == 'paid':
            return JsonResponse({
                'success': False,
                'message': '此訂單已完成付款'
            })
        
        payment_method = request.POST.get('payment_method', order.payment_method)
        
        if payment_method == 'test_payment':
            if not settings.DEBUG:
                return JsonResponse({
                    'success': False,
                    'message': '不支援的支付方式'
                })
            import uuid
            transaction_id = f"TXN{uuid.uuid4().hex[:16].upper()}"
            
            with transaction.atomic():
                order.payment_method = payment_method
                order.payment_status = 'paid'
                order.payment_transaction_id = transaction_id
                order.status = 'confirmed'
                order.save()
                
                # 建立通知
                Notification.objects.create(
                    user=request.user,
                    type='order',
                    title='付款成功',
                    message=f'您的訂單 {order.order_number} 已成功付款，交易編號：{transaction_id}'
                )
                
                # 發送訂單狀態更新郵件
                try:
                    send_order_status_update_email(order, request)
                except Exception as e:
                    logger.error(f'Failed to send order status update email: {str(e)}')
            
            logger.info(f'Payment processed: {transaction_id} for order {order.order_number}')
            
            return JsonResponse({
                'success': True,
                'message': '付款成功',
                'redirect_url': reverse('payment_success', kwargs={'order_id': order.id})
            })
        
        elif payment_method == 'linepay':
            # LINE Pay 支付
            from plus.payment.linepay import LinePayAPI
            
            linepay = LinePayAPI()
            
            # 構建回調 URL
            confirm_url = request.build_absolute_uri(reverse('linepay_confirm', kwargs={'order_id': order.id}))
            cancel_url = request.build_absolute_uri(reverse('linepay_cancel', kwargs={'order_id': order.id}))
            
            # 生成商品名稱
            product_names = [item.product_name for item in order.items.all()[:3]]
            product_name = '、'.join(product_names)
            if len(product_names) > 3:
                product_name += ' 等商品'
            
            # 請求支付
            result = linepay.request_payment(
                order_id=order.id,
                amount=order.total_amount,
                product_name=product_name or '商品',
                confirm_url=confirm_url,
                cancel_url=cancel_url
            )
            
            if result.get('success'):
                # 保存交易 ID
                order.payment_method = payment_method
                order.payment_transaction_id = result.get('transactionId')
                order.save()
                
                return JsonResponse({
                    'success': True,
                    'message': '正在跳轉到 LINE Pay...',
                    'redirect_url': result.get('paymentUrl')
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': result.get('message', 'LINE Pay 支付請求失敗')
                })

        elif payment_method == 'ecpay':
            from plus.payment.ecpay import ECPayAPI
            ecpay = ECPayAPI()
            if not ecpay.is_configured():
                return JsonResponse({
                    'success': False,
                    'message': '綠界金流尚未設定，請見 docs/integrations.md',
                })
            order.payment_method = 'ecpay'
            order.save(update_fields=['payment_method'])
            return JsonResponse({
                'success': True,
                'message': '正在前往綠界付款...',
                'redirect_url': reverse('ecpay_checkout', kwargs={'order_id': order.id}),
            })
        
        else:
            return JsonResponse({
                'success': False,
                'message': '不支援的支付方式'
            })
            
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '訂單不存在'
        })
    except Exception as e:
        logger.error(f'Payment processing error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '支付處理失敗，請稍後再試'
        })


@login_required
def payment_success_view(request, order_id):
    """支付成功頁面"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    
    context = {
        'order': order,
    }
    return render(request, 'payment/payment_success.html', context)


@login_required
def payment_failed_view(request, order_id):
    """支付失敗頁面"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        # 創建支付失敗通知
        send_notification(
            user=request.user,
            notification_type='order',
            title='付款失敗',
            message=f'您的訂單 {order.order_number} 付款失敗，請檢查付款資訊後重新嘗試，或選擇其他付款方式。'
        )
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    
    context = {
        'order': order,
    }
    return render(request, 'payment/payment_failed.html', context)


@login_required
def linepay_confirm(request, order_id):
    """LINE Pay 支付確認回調"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        # 獲取交易 ID 和訂單 ID
        transaction_id = request.GET.get('transactionId')
        order_id_param = request.GET.get('orderId')
        
        if not transaction_id:
            messages.error(request, '缺少交易資訊')
            return redirect('payment_failed', order_id=order.id)
        
        # 驗證交易 ID 是否匹配
        if order.payment_transaction_id != transaction_id:
            logger.warning(f'Transaction ID mismatch for order {order.order_number}')
            messages.error(request, '交易資訊不符，已取消此次確認')
            return redirect('payment_failed', order_id=order.id)
        
        # 確認支付
        from plus.payment.linepay import LinePayAPI
        linepay = LinePayAPI()
        
        result = linepay.confirm_payment(
            transaction_id=transaction_id,
            amount=order.total_amount
        )
        
        if result.get('success'):
            # 支付成功
            with transaction.atomic():
                order.payment_status = 'paid'
                order.payment_transaction_id = result.get('transactionId', transaction_id)
                order.status = 'confirmed'
                order.save()
                
                # 建立通知
                Notification.objects.create(
                    user=request.user,
                    type='order',
                    title='付款成功',
                    message=f'您的訂單 {order.order_number} 已成功透過 LINE Pay 付款完成。'
                )
                
                # 發送訂單狀態更新郵件
                try:
                    send_order_status_update_email(order, request)
                except Exception as e:
                    logger.error(f'Failed to send order status update email: {str(e)}')
            
            logger.info(f'LINE Pay confirmed: {transaction_id} for order {order.order_number}')
            messages.success(request, '付款成功！')
            return redirect('payment_success', order_id=order.id)
        else:
            # 支付失敗
            with transaction.atomic():
                order.payment_status = 'failed'
                order.save(update_fields=['payment_status'])
                release_order_inventory(order)
                restore_coupon(order)
            
            logger.error(f'LINE Pay confirm failed: {result.get("message")} for order {order.order_number}')
            messages.error(request, f'付款確認失敗：{result.get("message", "未知錯誤")}')
            return redirect('payment_failed', order_id=order.id)
            
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    except Exception as e:
        logger.error(f'LINE Pay confirm error: {str(e)}')
        messages.error(request, '支付確認處理發生錯誤')
        return redirect('payment_failed', order_id=order_id)


@login_required
def linepay_cancel(request, order_id):
    """LINE Pay 支付取消回調"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        messages.info(request, '您已取消 LINE Pay 付款')
        return redirect('payment', order_id=order.id)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')


@login_required
def ecpay_checkout(request, order_id):
    """自動送出綠界付款表單。"""
    from plus.payment.ecpay import ECPayAPI
    try:
        order = Order.objects.prefetch_related('items').get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    if order.payment_status == 'paid':
        return redirect('order_detail', order_id=order.id)
    ecpay = ECPayAPI()
    return_url = request.build_absolute_uri(reverse('ecpay_return'))
    result_url = request.build_absolute_uri(reverse('ecpay_result', kwargs={'order_id': order.id}))
    client_back_url = request.build_absolute_uri(reverse('payment', kwargs={'order_id': order.id}))
    params, error = ecpay.build_checkout_params(order, return_url, result_url, client_back_url)
    if error:
        messages.error(request, error)
        return redirect('payment', order_id=order.id)
    return render(request, 'payment/ecpay_checkout.html', {
        'order': order,
        'ecpay_url': ecpay.checkout_url,
        'ecpay_params': params,
    })


def _mark_ecpay_paid(order, trade_no):
    if order.payment_status == 'paid':
        return
    with transaction.atomic():
        order.payment_method = 'ecpay'
        order.payment_status = 'paid'
        order.payment_transaction_id = trade_no or order.payment_transaction_id
        order.status = 'confirmed'
        order.save()
        Notification.objects.create(
            user=order.user,
            type='order',
            title='付款成功',
            message=f'您的訂單 {order.order_number} 已透過綠界付款完成。',
        )
    try:
        send_order_status_update_email(order)
    except Exception as exc:
        logger.error('ECPay status email failed: %s', exc)


@csrf_exempt
@require_http_methods(["POST"])
def ecpay_return(request):
    """綠界伺服器背景通知（必須回傳 1|OK）。"""
    from plus.payment.ecpay import ECPayAPI
    ecpay = ECPayAPI()
    params = {key: request.POST.get(key) for key in request.POST}
    if not ecpay.verify_check_mac_value(params):
        logger.warning('ECPay ReturnURL CheckMacValue mismatch')
        return HttpResponse('0|CheckMacValueError')
    merchant_trade_no = params.get('MerchantTradeNo') or ''
    try:
        order = Order.objects.get(order_number=merchant_trade_no)
    except Order.DoesNotExist:
        logger.error('ECPay ReturnURL unknown order %s', merchant_trade_no)
        return HttpResponse('0|OrderNotFound')
    if params.get('RtnCode') == '1':
        _mark_ecpay_paid(order, params.get('TradeNo', ''))
    elif order.payment_status != 'paid':
        order.payment_status = 'failed'
        order.save(update_fields=['payment_status'])
        release_order_inventory(order)
        restore_coupon(order)
    return HttpResponse('1|OK')


@csrf_exempt
def ecpay_result(request, order_id):
    """綠界瀏覽器導回。"""
    from plus.payment.ecpay import ECPayAPI
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    if request.method == 'POST':
        ecpay = ECPayAPI()
        params = {key: request.POST.get(key) for key in request.POST}
        if ecpay.verify_check_mac_value(params) and params.get('RtnCode') == '1':
            _mark_ecpay_paid(order, params.get('TradeNo', ''))
            order.refresh_from_db()
    if request.user.is_authenticated and request.user == order.user:
        if order.payment_status == 'paid':
            messages.success(request, '付款成功！')
            return redirect('payment_success', order_id=order.id)
        messages.error(request, '付款未完成，請再試一次')
        return redirect('payment_failed', order_id=order.id)
    messages.info(request, '付款結果已記錄，請登入後查看訂單')
    return redirect('login')

