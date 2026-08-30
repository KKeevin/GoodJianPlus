from decimal import Decimal

from plus.models import Coupon, ShippingMethod, SiteSettings


def get_pricing_settings():
    """讀取免運門檻與稅率，fallback 與原本 view 相同。"""
    try:
        site_settings = SiteSettings.objects.first()
        free_shipping_threshold = site_settings.free_shipping_threshold if site_settings else Decimal('1000')
        tax_rate = site_settings.tax_rate if site_settings else Decimal('0.05')
    except Exception:
        free_shipping_threshold = Decimal('1000')
        tax_rate = Decimal('0.05')
    return free_shipping_threshold, tax_rate


def resolve_shipping_fee(subtotal, free_shipping_threshold, shipping_method_id=None):
    """計算運費，數字與原本 checkout / calculate_checkout_price 相同。"""
    if shipping_method_id:
        try:
            shipping_method = ShippingMethod.objects.get(id=shipping_method_id, is_active=True)
            if subtotal >= free_shipping_threshold:
                return Decimal('0')
            return shipping_method.price
        except ShippingMethod.DoesNotExist:
            return Decimal('0') if subtotal >= free_shipping_threshold else Decimal('100')
    return Decimal('0') if subtotal >= free_shipping_threshold else Decimal('100')


def compute_coupon_discount(coupon_code, subtotal, shipping_fee):
    """
    試算優惠券折扣，不增加 used_count。
    回傳 (discount_amount, shipping_fee, coupon, coupon_info, error_message)
    """
    discount_amount = Decimal('0')
    coupon = None
    coupon_info = None
    if not coupon_code:
        return discount_amount, shipping_fee, coupon, coupon_info, None

    try:
        coupon = Coupon.objects.get(code=coupon_code, is_active=True)
        if coupon.is_valid and subtotal >= coupon.minimum_amount:
            if coupon.discount_type == 'percentage':
                discount_amount = subtotal * (Decimal(str(coupon.discount_value)) / Decimal('100'))
                if coupon.maximum_discount:
                    discount_amount = min(discount_amount, Decimal(str(coupon.maximum_discount)))
            elif coupon.discount_type == 'fixed':
                discount_amount = Decimal(str(coupon.discount_value))
            elif coupon.discount_type == 'free_shipping':
                discount_amount = shipping_fee
                shipping_fee = Decimal('0')
            coupon_info = {
                'code': coupon.code,
                'name': coupon.name,
                'discount_type': coupon.discount_type,
                'discount_value': float(coupon.discount_value),
            }
            return discount_amount, shipping_fee, coupon, coupon_info, None
        return discount_amount, shipping_fee, coupon, None, '優惠券無效或不符合使用條件'
    except Coupon.DoesNotExist:
        return discount_amount, shipping_fee, None, None, '優惠券不存在'
