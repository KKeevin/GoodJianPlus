from django.db import transaction
from django.db.models import F, Q

from plus.models import Coupon, Product


class InsufficientStock(Exception):
    def __init__(self, product_name):
        self.product_name = product_name
        super().__init__(product_name)


@transaction.atomic
def hold_stock_for_cart_items(items):
    """結帳時鎖定並預扣庫存。"""
    for item in items:
        if item.quantity <= 0:
            raise ValueError('商品數量必須大於零')
        changed = Product.objects.filter(pk=item.product_id, stock_quantity__gte=item.quantity).update(
            stock_quantity=F('stock_quantity') - item.quantity)
        if not changed:
            raise InsufficientStock(item.product.name)


def release_order_inventory(order):
    """付款失敗或取消時把預扣庫存還回去（只會執行一次）。"""
    with transaction.atomic():
        locked = type(order).objects.select_for_update().get(pk=order.pk)
        if not type(order).objects.filter(pk=order.pk, inventory_held=True).update(inventory_held=False):
            return
        for item in locked.items.select_related('product'):
            if item.product_id:
                Product.objects.filter(pk=item.product_id).update(
                    stock_quantity=F('stock_quantity') + item.quantity
                )
        order.inventory_held = False


def consume_coupon(order):
    if not order.coupon_code:
        return
    with transaction.atomic():
        locked = type(order).objects.select_for_update().get(pk=order.pk)
        if locked.coupon_reserved:
            return
        coupon = Coupon.objects.select_for_update().filter(code=order.coupon_code).first()
        if coupon is None:
            return
        changed = Coupon.objects.filter(pk=coupon.pk).filter(
            Q(usage_limit=0) | Q(usage_limit__isnull=True) | Q(used_count__lt=F('usage_limit'))
        ).update(used_count=F('used_count') + 1)
        if not changed:
            raise ValueError('優惠券已達使用上限')
        type(order).objects.filter(pk=order.pk).update(coupon_reserved=True)
        order.coupon_reserved = True


def restore_coupon(order):
    if not order.coupon_code:
        return
    with transaction.atomic():
        if type(order).objects.filter(pk=order.pk, coupon_reserved=True).update(coupon_reserved=False):
            Coupon.objects.filter(code=order.coupon_code, used_count__gt=0).update(used_count=F('used_count') - 1)
        order.coupon_reserved = False
