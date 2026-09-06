import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from plus.models import Order
from plus.services.payments import payable, settle_payment, fail_payment

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
        if payment_method == 'test_payment' and not settings.DEBUG:
            return JsonResponse({'success': False, 'message': '不支援的支付方式'})
        if not payable(order) or payment_method != order.payment_method:
            return JsonResponse({'success': False, 'message': '訂單無法付款，請重新建立訂單或聯絡客服。'}, status=409)
        
        if payment_method == 'test_payment':
            import uuid
            transaction_id = f"TXN{uuid.uuid4().hex[:16].upper()}"
            
            if not settle_payment(order.pk, payment_method, transaction_id, order.total_amount):
                return JsonResponse({'success': False, 'message': '付款需要人工確認'}, status=409)

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
            if not linepay.channel_id or not linepay.channel_secret:
                return JsonResponse({'success': False, 'message': '此付款方式暫時無法使用，請聯絡客服。'}, status=503)
            import uuid
            request_marker = f'requesting:{uuid.uuid4().hex}'
            claimed = Order.objects.filter(pk=order.pk, status='pending', payment_status='pending',
                inventory_held=True, payment_method='linepay').filter(
                    Q(payment_transaction_id__isnull=True) | Q(payment_transaction_id='')
                ).update(payment_transaction_id=request_marker)
            if not claimed:
                return JsonResponse({'success': False, 'message': '已有付款處理中，請查看原付款頁或聯絡客服確認。'}, status=409)
            
            # 構建回調 URL
            confirm_url = request.build_absolute_uri(reverse('linepay_confirm', kwargs={'order_id': order.id}))
            cancel_url = request.build_absolute_uri(reverse('linepay_cancel', kwargs={'order_id': order.id}))
            
            # 生成商品名稱
            product_names = [item.product_name for item in order.items.all()[:4]]
            product_name = '、'.join(product_names[:3])
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
                updated = Order.objects.filter(pk=order.pk, status='pending', payment_status='pending', inventory_held=True,
                    payment_transaction_id=request_marker).update(payment_transaction_id=str(result.get('transactionId')))
                if not updated:
                    return JsonResponse({'success': False, 'message': '訂單狀態已變更，請聯絡客服。'}, status=409)
                
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
    if order.payment_status != 'paid':
        return redirect('order_detail', order_id=order.pk)
    
    context = {
        'order': order,
    }
    return render(request, 'payment/payment_success.html', context)


@login_required
def payment_failed_view(request, order_id):
    """支付失敗頁面"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
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
        
        if order.payment_status == 'paid':
            return redirect('order_detail', order_id=order.pk)
        if not payable(order) or order.payment_method != 'linepay':
            messages.error(request, '此訂單無法確認付款，請聯絡客服。')
            return redirect('order_detail', order_id=order.pk)
        if order_id_param and order_id_param != str(order.pk):
            return HttpResponse('OrderMismatch', status=400)

        # 確認支付
        from plus.payment.linepay import LinePayAPI
        linepay = LinePayAPI()
        
        result = linepay.confirm_payment(
            transaction_id=transaction_id,
            amount=order.total_amount
        )
        
        if result.get('success'):
            if (str(result.get('transactionId')) != transaction_id
                    or str(result.get('orderId')) != str(order.pk)):
                logger.error('LINE Pay response mismatch for order %s', order.pk)
                messages.error(request, '付款結果需要人工確認，請聯絡客服。')
                return redirect('order_detail', order_id=order.pk)
            settled = settle_payment(order.pk, 'linepay', transaction_id, order.total_amount)
            messages.info(request, '付款成功！' if settled else '付款已收到，訂單需要人工確認。')
            return redirect('order_detail', order_id=order.pk)
        # A timeout or repeated confirmation is not proof of payment failure.
        # Keep the reservation until a provider result or staff reconciliation is available.
        logger.warning('LINE Pay confirmation unresolved: order=%s', order.pk)
        messages.info(request, '付款結果尚待確認，請稍後查看訂單或聯絡客服。')
        return redirect('order_detail', order_id=order.pk)

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
    if not payable(order) or order.payment_method != 'ecpay':
        messages.error(request, '此訂單無法付款，請重新建立訂單。')
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
    return settle_payment(order.pk, 'ecpay', trade_no, order.total_amount)


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
    if not ecpay.valid_result(params, order):
        return HttpResponse('0|InvalidPaymentData', status=400)
    if params.get('RtnCode') == '1':
        try:
            _mark_ecpay_paid(order, params['TradeNo'])
        except ValidationError:
            return HttpResponse('0|TransactionMismatch', status=400)
    elif order.payment_method == 'ecpay':
        fail_payment(order.pk)
    return HttpResponse('1|OK')


@csrf_exempt
def ecpay_result(request, order_id):
    """綠界瀏覽器導回。"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, '訂單不存在')
        return redirect('order_list')
    # Browser redirects are display-only. Only authenticated server callbacks settle payments.
    if request.user.is_authenticated and request.user == order.user:
        if order.payment_status == 'paid':
            messages.success(request, '付款成功！')
            return redirect('payment_success', order_id=order.id)
        messages.info(request, '付款結果尚待確認，請稍後於訂單查看。')
        return redirect('order_detail', order_id=order.id)
    messages.info(request, '請登入後查看付款結果')
    return redirect('login')

