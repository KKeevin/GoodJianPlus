from django.db import transaction
from django.db.models import F

from plus.models import Coupon, Product


class InsufficientStock(Exception):
    def __init__(self, product_name):
        self.product_name = product_name
        super().__init__(product_name)


def hold_stock_for_cart_items(items):
    """結帳時鎖定並預扣庫存。"""
    for item in items:
        product = Product.objects.select_for_update().get(pk=item.product_id)
        if product.stock_quantity < item.quantity:
            raise InsufficientStock(product.name)
        product.stock_quantity = F('stock_quantity') - item.quantity
        product.save(update_fields=['stock_quantity'])


def release_order_inventory(order):
    """付款失敗或取消時把預扣庫存還回去（只會執行一次）。"""
    if not order.inventory_held:
        return
    with transaction.atomic():
        locked = type(order).objects.select_for_update().get(pk=order.pk)
        if not locked.inventory_held:
            return
        for item in locked.items.select_related('product'):
            if item.product_id:
                Product.objects.filter(pk=item.product_id).update(
                    stock_quantity=F('stock_quantity') + item.quantity
                )
        locked.inventory_held = False
        locked.save(update_fields=['inventory_held'])
        order.inventory_held = False


def consume_coupon(order):
    if not order.coupon_code:
        return
    with transaction.atomic():
        coupon = Coupon.objects.select_for_update().filter(code=order.coupon_code).first()
        if coupon is None:
            return
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            raise ValueError('優惠券已達使用上限')
        coupon.used_count = F('used_count') + 1
        coupon.save(update_fields=['used_count'])


def restore_coupon(order):
    if not order.coupon_code:
        return
    Coupon.objects.filter(code=order.coupon_code, used_count__gt=0).update(
        used_count=F('used_count') - 1
    )
