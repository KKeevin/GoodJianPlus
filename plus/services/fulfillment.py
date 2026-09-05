"""訂單狀態變更的副作用：出貨時間、站內通知、狀態信、庫存。"""
import logging

from django.utils import timezone

from plus.models import Notification
from plus.services.inventory import release_order_inventory, restore_coupon
from plus.utils.email import send_order_status_update_email

logger = logging.getLogger(__name__)

STATUS_MESSAGES = {
    'confirmed': '您的訂單已確認，正在準備出貨。',
    'processing': '您的訂單正在處理中。',
    'shipped': '您的訂單已出貨，請注意查收。',
    'delivered': '您的訂單已送達，感謝您的購買！',
    'completed': '您的訂單已完成，感謝您的購買！',
    'cancelled': '您的訂單已取消。',
    'refunded': '您的訂單已退款。',
}


def stamp_fulfillment_times(order):
    """依狀態補上出貨／送達時間，不另存檔。"""
    now = timezone.now()
    if order.status == 'shipped' and not order.shipped_at:
        order.shipped_at = now
    if order.status in ('delivered', 'completed') and not order.delivered_at:
        order.delivered_at = now


def notify_order_status_change(order, old_status, old_payment_status, request=None, inventory_handled=False):
    if old_status != order.status:
        if order.status == 'cancelled' and old_status != 'cancelled' and not inventory_handled:
            release_order_inventory(order)
            restore_coupon(order)
        message = STATUS_MESSAGES.get(
            order.status,
            f'您的訂單狀態已變更為：{order.get_status_display()}。',
        )
        if order.status == 'shipped' and order.tracking_number:
            carrier = order.get_carrier_display() if order.carrier else '物流'
            message += f' {carrier} 單號：{order.tracking_number}'
        Notification.objects.create(
            user=order.user,
            type='order',
            title=f'訂單 {order.order_number} 狀態更新',
            message=message,
        )
        try:
            send_order_status_update_email(order, request)
        except Exception as exc:
            logger.error('Failed to send order status email: %s', exc)

    if old_payment_status != order.payment_status and order.payment_status == 'paid':
        Notification.objects.create(
            user=order.user,
            type='order',
            title='付款成功',
            message=f'您的訂單 {order.order_number} 已成功付款，交易編號：{order.payment_transaction_id or "N/A"}',
        )
