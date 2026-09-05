"""Shared, transaction-safe operations for the seller center and admin actions."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from plus.models import Order, OrderEvent
from plus.services.fulfillment import stamp_fulfillment_times, notify_order_status_change


READY_PAYMENT = Q(payment_status='paid') | Q(payment_method='cod', payment_status='pending')
OPEN_STATUSES = ('pending', 'confirmed', 'processing')
TRANSITIONS = {
    'pending': {'confirmed', 'processing', 'shipped', 'cancelled'},
    'confirmed': {'processing', 'shipped', 'cancelled'},
    'processing': {'shipped', 'cancelled'},
    'shipped': {'delivered', 'completed'},
    'delivered': {'completed'},
    'completed': set(), 'cancelled': set(), 'refunded': set(),
}


def ready_to_ship(queryset=None):
    queryset = queryset if queryset is not None else Order.objects.all()
    return queryset.filter(READY_PAYMENT, status__in=OPEN_STATUSES).exclude(
        return_requests__status__in=('pending', 'approved', 'received')
    )


def validate_transition(order, status):
    if status == order.status:
        return
    if status not in TRANSITIONS.get(order.status, set()):
        raise ValidationError('此訂單狀態無法進行這項操作，請重新整理訂單。')
    if status in ('confirmed', 'processing', 'shipped'):
        if not (order.payment_status == 'paid' or (
            order.payment_method == 'cod' and order.payment_status == 'pending'
        )):
            raise ValidationError('尚未付款的線上付款訂單無法備貨或出貨。')
        if order.return_requests.filter(status__in=('pending', 'approved', 'received')).exists():
            raise ValidationError('訂單有處理中的退貨申請，請先處理售後。')
    if status == 'shipped' and (not order.carrier or not order.tracking_number.strip()):
        raise ValidationError('出貨前請填寫物流商與物流單號。')
    if status == 'cancelled' and order.payment_status == 'paid':
        raise ValidationError('已付款訂單請透過退貨／退款流程處理。')


@transaction.atomic
def transition_order(order_id, status, *, actor=None, carrier=None, tracking_number=None):
    order = Order.objects.select_for_update().get(pk=order_id)
    old_status, old_payment = order.status, order.payment_status
    if status == old_status:
        return order, False
    if carrier is not None:
        if carrier not in dict(Order.CARRIER_CHOICES):
            raise ValidationError('請選擇有效的物流商。')
        order.carrier = carrier
    if tracking_number is not None:
        tracking_number = tracking_number.strip()
        if len(tracking_number) > 80 or any(ord(c) < 32 for c in tracking_number):
            raise ValidationError('物流單號格式不正確（最多 80 字）。')
        order.tracking_number = tracking_number
    validate_transition(order, status)
    order.status = status
    stamp_fulfillment_times(order)
    order.save()
    OrderEvent.objects.create(order=order, actor=actor, status=status)
    # Inventory changes must share the transaction. Emails are sent after commit.
    if status == 'cancelled':
        from plus.services.inventory import release_order_inventory, restore_coupon
        release_order_inventory(order)
        restore_coupon(order)
    transaction.on_commit(lambda: notify_order_status_change(
        order, old_status, old_payment, inventory_handled=True,
    ))
    return order, True
