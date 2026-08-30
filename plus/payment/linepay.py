"""
LINE Pay 支付整合模組
"""
import requests
import hmac
import hashlib
import base64
import json
import logging
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)


class LinePayAPI:
    """LINE Pay API 客戶端"""
    
    # LINE Pay API 端點
    SANDBOX_BASE_URL = 'https://sandbox-web-pay.line.me'
    PRODUCTION_BASE_URL = 'https://api-pay.line.me'
    
    def __init__(self):
        self.channel_id = getattr(settings, 'LINE_PAY_CHANNEL_ID', '')
        self.channel_secret = getattr(settings, 'LINE_PAY_CHANNEL_SECRET', '')
        self.is_sandbox = getattr(settings, 'LINE_PAY_SANDBOX', True)
        
        if self.is_sandbox:
            self.base_url = self.SANDBOX_BASE_URL
        else:
            self.base_url = self.PRODUCTION_BASE_URL
        
        if not self.channel_id or not self.channel_secret:
            logger.warning('LINE Pay credentials not configured')
    
    def _generate_signature(self, uri, body, nonce):
        """生成 LINE Pay 簽名"""
        message = f"{self.channel_secret}{uri}{json.dumps(body, separators=(',', ':'))}{nonce}"
        signature = base64.b64encode(
            hmac.new(
                self.channel_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        return signature
    
    def _get_headers(self, uri, body, nonce):
        """獲取請求標頭"""
        signature = self._generate_signature(uri, body, nonce)
        return {
            'Content-Type': 'application/json',
            'X-LINE-ChannelId': self.channel_id,
            'X-LINE-Authorization-Nonce': nonce,
            'X-LINE-Authorization': signature
        }
    
    def request_payment(self, order_id, amount, product_name, confirm_url, cancel_url, currency='TWD'):
        """
        請求支付
        
        Args:
            order_id: 訂單編號
            amount: 金額（Decimal）
            product_name: 商品名稱
            confirm_url: 確認回調 URL
            cancel_url: 取消回調 URL
            currency: 幣別（預設 TWD）
        
        Returns:
            dict: 包含 paymentUrl 和 transactionId 的字典
        """
        if not self.channel_id or not self.channel_secret:
            return {
                'success': False,
                'message': 'LINE Pay 未配置'
            }
        
        import uuid
        import time
        
        nonce = str(uuid.uuid4())
        uri = '/v3/payments/request'
        
        # 將金額轉換為整數（LINE Pay 使用最小貨幣單位）
        amount_int = int(amount * 100)  # TWD 使用元，轉換為分
        
        body = {
            'amount': amount_int,
            'currency': currency,
            'orderId': str(order_id),
            'packages': [
                {
                    'id': str(order_id),
                    'amount': amount_int,
                    'name': product_name[:100],  # 限制長度
                    'products': [
                        {
                            'name': product_name[:100],
                            'quantity': 1,
                            'price': amount_int
                        }
                    ]
                }
            ],
            'redirectUrls': {
                'confirmUrl': confirm_url,
                'cancelUrl': cancel_url
            }
        }
        
        headers = self._get_headers(uri, body, nonce)
        url = f"{self.base_url}{uri}"
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('returnCode') == '0000':
                return {
                    'success': True,
                    'paymentUrl': result['info']['paymentUrl']['web'],
                    'transactionId': result['info']['transactionId']
                }
            else:
                logger.error(f'LINE Pay request failed: {result}')
                return {
                    'success': False,
                    'message': result.get('returnMessage', '支付請求失敗')
                }
        except requests.exceptions.RequestException as e:
            logger.error(f'LINE Pay API error: {str(e)}')
            return {
                'success': False,
                'message': f'支付請求發生錯誤: {str(e)}'
            }
    
    def confirm_payment(self, transaction_id, amount, currency='TWD'):
        """
        確認支付
        
        Args:
            transaction_id: 交易 ID
            amount: 金額（Decimal）
            currency: 幣別（預設 TWD）
        
        Returns:
            dict: 確認結果
        """
        if not self.channel_id or not self.channel_secret:
            return {
                'success': False,
                'message': 'LINE Pay 未配置'
            }
        
        import uuid
        
        nonce = str(uuid.uuid4())
        uri = f'/v3/payments/{transaction_id}/confirm'
        
        # 將金額轉換為整數
        amount_int = int(amount * 100)
        
        body = {
            'amount': amount_int,
            'currency': currency
        }
        
        headers = self._get_headers(uri, body, nonce)
        url = f"{self.base_url}{uri}"
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('returnCode') == '0000':
                return {
                    'success': True,
                    'transactionId': result['info']['transactionId'],
                    'orderId': result['info'].get('orderId'),
                    'payInfo': result['info'].get('payInfo', {})
                }
            else:
                logger.error(f'LINE Pay confirm failed: {result}')
                return {
                    'success': False,
                    'message': result.get('returnMessage', '支付確認失敗')
                }
        except requests.exceptions.RequestException as e:
            logger.error(f'LINE Pay confirm API error: {str(e)}')
            return {
                'success': False,
                'message': f'支付確認發生錯誤: {str(e)}'
            }
    
    def get_payment_status(self, transaction_id):
        """
        查詢支付狀態
        
        Args:
            transaction_id: 交易 ID
        
        Returns:
            dict: 支付狀態資訊
        """
        if not self.channel_id or not self.channel_secret:
            return {
                'success': False,
                'message': 'LINE Pay 未配置'
            }
        
        import uuid
        
        nonce = str(uuid.uuid4())
        uri = f'/v3/payments/authorizations/{transaction_id}'
        body = {}
        
        headers = self._get_headers(uri, body, nonce)
        url = f"{self.base_url}{uri}"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('returnCode') == '0000':
                return {
                    'success': True,
                    'status': result['info'].get('payStatus'),
                    'transactionId': result['info'].get('transactionId'),
                    'orderId': result['info'].get('orderId')
                }
            else:
                return {
                    'success': False,
                    'message': result.get('returnMessage', '查詢失敗')
                }
        except requests.exceptions.RequestException as e:
            logger.error(f'LINE Pay status API error: {str(e)}')
            return {
                'success': False,
                'message': f'查詢支付狀態發生錯誤: {str(e)}'
            }

