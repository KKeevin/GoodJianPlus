"""One settlement path for authenticated provider results; never revive closed orders."""
import logging
from django.core.exceptions import ValidationError
from django.db import transaction
from plus.models import Order, Notification
from plus.models.commerce import PaymentReceipt
from plus.services.order_workflow import transition_order

logger = logging.getLogger(__name__)


def payable(order):
    return (order.status == 'pending' and order.payment_status == 'pending'
            and order.inventory_held)


@transaction.atomic
def settle_payment(order_id, provider, transaction_id, amount):
    order = Order.objects.select_for_update().get(pk=order_id)
    if not transaction_id or amount != order.total_amount:
        raise ValidationError('付款金額或交易編號不符')
    receipt, created = PaymentReceipt.objects.get_or_create(
        provider=provider, transaction_id=str(transaction_id),
        defaults={'order': order, 'amount': amount},
    )
    if receipt.order_id != order.pk or receipt.amount != amount:
        raise ValidationError('交易編號已屬於其他訂單')
    if not created:
        return not receipt.needs_review
    if order.payment_status == 'paid' and str(order.payment_transaction_id) == str(transaction_id):
        return True
    if (not payable(order) or order.payment_method != provider
            or order.return_requests.filter(status__in=('pending', 'approved', 'received')).exists()):
        receipt.needs_review = True
        receipt.reason = '付款已到帳但訂單不可自動確認，請核對並處理退款；禁止直接出貨。'
        receipt.save(update_fields=['needs_review', 'reason'])
        logger.error('Payment requires reconciliation: receipt=%s order=%s', receipt.pk, order.pk)
        return False
    order.payment_status = 'paid'
    order.payment_transaction_id = str(transaction_id)
    order.save(update_fields=['payment_status', 'payment_transaction_id', 'updated_at'])
    transition_order(order.pk, 'confirmed')
    Notification.objects.create(user=order.user, type='order', title='付款成功',
        message=f'訂單 {order.order_number} 已完成付款。')
    return True


@transaction.atomic
def fail_payment(order_id):
    from plus.services.inventory import release_order_inventory, restore_coupon
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.payment_status != 'pending' or order.status != 'pending':
        return
    order.payment_status = 'failed'
    order.save(update_fields=['payment_status', 'updated_at'])
    release_order_inventory(order)
    restore_coupon(order)
