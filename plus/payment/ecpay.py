"""
綠界科技 ECPay 全方位金流（AIO）。
申請 MerchantID / HashKey / HashIV 後貼到 .env 即可送出付款表單。
文件：https://developers.ecpay.com.tw/
"""
import hashlib
import logging
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import quote_plus

from django.conf import settings

logger = logging.getLogger(__name__)

STAGE_CHECKOUT_URL = 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5'
PROD_CHECKOUT_URL = 'https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5'


class ECPayAPI:
    def __init__(self):
        self.merchant_id = getattr(settings, 'ECPAY_MERCHANT_ID', '') or ''
        self.hash_key = getattr(settings, 'ECPAY_HASH_KEY', '') or ''
        self.hash_iv = getattr(settings, 'ECPAY_HASH_IV', '') or ''
        self.is_sandbox = getattr(settings, 'ECPAY_SANDBOX', True)
        self.checkout_url = STAGE_CHECKOUT_URL if self.is_sandbox else PROD_CHECKOUT_URL

    def is_configured(self):
        return bool(self.merchant_id and self.hash_key and self.hash_iv)

    @staticmethod
    def to_twd_amount(amount):
        return int(Decimal(amount).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

    def generate_check_mac_value(self, params):
        """綠界 CheckMacValue：依 key 排序、夾 HashKey/HashIV、URL encode、SHA256 大寫。"""
        items = []
        for key in sorted(params.keys(), key=lambda k: k.lower()):
            if key.lower() == 'checkmacvalue' or params[key] in (None, ''):
                continue
            items.append(f'{key}={params[key]}')
        raw = f'HashKey={self.hash_key}&{"&".join(items)}&HashIV={self.hash_iv}'
        encoded = quote_plus(raw, safe='').lower()
        return hashlib.sha256(encoded.encode('utf-8')).hexdigest().upper()

    def verify_check_mac_value(self, params):
        incoming = (params.get('CheckMacValue') or '').upper()
        if not incoming:
            return False
        computed = self.generate_check_mac_value(params)
        return incoming == computed

    def build_checkout_params(self, order, return_url, result_url, client_back_url):
        if not self.is_configured():
            return None, '綠界金流尚未設定 MerchantID / HashKey / HashIV，請見 docs/integrations.md'

        item_names = ' '.join(item.product_name for item in order.items.all()[:5]) or '商品'
        item_names = item_names.replace('#', ' ').replace('&', ' ')[:200]
        trade_date = order.created_at.strftime('%Y/%m/%d %H:%M:%S')
        params = {
            'MerchantID': self.merchant_id,
            'MerchantTradeNo': order.order_number[:20],
            'MerchantTradeDate': trade_date,
            'PaymentType': 'aio',
            'TotalAmount': str(self.to_twd_amount(order.total_amount)),
            'TradeDesc': '好健健 GoodJian Plus 訂單',
            'ItemName': item_names,
            'ReturnURL': return_url,
            'OrderResultURL': result_url,
            'ClientBackURL': client_back_url,
            'ChoosePayment': 'ALL',
            'EncryptType': '1',
            'NeedExtraPaidInfo': 'N',
        }
        params['CheckMacValue'] = self.generate_check_mac_value(params)
        return params, ''
