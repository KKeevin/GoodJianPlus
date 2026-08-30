"""
SMS 服務模組
用於發送手機驗證碼
"""
import os
import logging
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def send_sms_verification_code(phone, code):
    """
    發送 SMS 驗證碼
    
    Args:
        phone: 手機號碼
        code: 驗證碼
    
    Returns:
        bool: 發送是否成功
    """
    # 檢查是否為測試模式
    sms_test_mode = os.getenv('SMS_TEST_MODE', 'True').lower() == 'true'
    
    if sms_test_mode:
        # 測試模式：只記錄到日誌，不實際發送
        logger.info(f'[SMS TEST MODE] 發送驗證碼到 {phone}: {code}')
        print(f'[SMS TEST MODE] 發送驗證碼到 {phone}: {code}')
        return True
    
    # 生產模式：實際發送 SMS
    # 這裡可以整合各種 SMS 服務提供商，例如：
    # - Twilio
    # - AWS SNS
    # - 台灣的簡訊服務商（如：三竹、互聯電信等）
    
    sms_provider = os.getenv('SMS_PROVIDER', '').lower()
    
    if sms_provider == 'twilio':
        return _send_via_twilio(phone, code)
    elif sms_provider == 'aws_sns':
        return _send_via_aws_sns(phone, code)
    elif sms_provider == 'mitake':  # 三竹資訊
        return _send_via_mitake(phone, code)
    elif sms_provider == 'clicksend':  # ClickSend
        return _send_via_clicksend(phone, code)
    else:
        # 預設：記錄到日誌
        logger.warning(f'未配置 SMS 服務提供商，使用測試模式。發送驗證碼到 {phone}: {code}')
        print(f'[未配置 SMS] 發送驗證碼到 {phone}: {code}')
        return True


def _send_via_twilio(phone, code):
    """通過 Twilio 發送 SMS"""
    try:
        from twilio.rest import Client
        
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        from_number = os.getenv('TWILIO_FROM_NUMBER')
        
        if not all([account_sid, auth_token, from_number]):
            logger.error('Twilio 配置不完整')
            return False
        
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=f'您的好健健驗證碼是：{code}，有效期限為 10 分鐘。',
            from_=from_number,
            to=phone
        )
        logger.info(f'Twilio SMS 發送成功: {message.sid}')
        return True
    except Exception as e:
        logger.error(f'Twilio SMS 發送失敗: {str(e)}')
        return False


def _send_via_aws_sns(phone, code):
    """通過 AWS SNS 發送 SMS"""
    try:
        import boto3
        
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_region = os.getenv('AWS_REGION', 'ap-northeast-1')
        
        if not all([aws_access_key_id, aws_secret_access_key]):
            logger.error('AWS SNS 配置不完整')
            return False
        
        sns = boto3.client(
            'sns',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        
        # 台灣手機號碼需要加上 +886
        if phone.startswith('09'):
            phone = '+886' + phone[1:]
        elif not phone.startswith('+'):
            phone = '+886' + phone
        
        response = sns.publish(
            PhoneNumber=phone,
            Message=f'您的好健健驗證碼是：{code}，有效期限為 10 分鐘。'
        )
        logger.info(f'AWS SNS SMS 發送成功: {response["MessageId"]}')
        return True
    except Exception as e:
        logger.error(f'AWS SNS SMS 發送失敗: {str(e)}')
        return False


def _send_via_mitake(phone, code):
    """通過三竹資訊發送 SMS"""
    try:
        import requests
        
        mitake_username = os.getenv('MITAKE_USERNAME')
        mitake_password = os.getenv('MITAKE_PASSWORD')
        mitake_api_url = os.getenv('MITAKE_API_URL', 'https://api.mitake.com.tw/api/mtk/SmSend')
        
        if not all([mitake_username, mitake_password]):
            logger.error('三竹資訊配置不完整')
            return False
        
        data = {
            'username': mitake_username,
            'password': mitake_password,
            'dstaddr': phone,
            'smbody': f'您的好健健驗證碼是：{code}，有效期限為 10 分鐘。',
            'encoding': 'UTF8'
        }
        
        response = requests.post(mitake_api_url, data=data, timeout=10)
        response.raise_for_status()
        
        logger.info(f'三竹資訊 SMS 發送成功: {response.text}')
        return True
    except Exception as e:
        logger.error(f'三竹資訊 SMS 發送失敗: {str(e)}')
        return False


def _send_via_clicksend(phone, code):
    """通過 ClickSend 發送 SMS"""
    try:
        import requests
        import base64
        
        clicksend_username = os.getenv('CLICKSEND_USERNAME')
        clicksend_api_key = os.getenv('CLICKSEND_API_KEY')
        clicksend_from_number = os.getenv('CLICKSEND_FROM_NUMBER', '')  # 可選，如果未設置則使用 ClickSend 預設
        
        if not all([clicksend_username, clicksend_api_key]):
            logger.error('ClickSend 配置不完整')
            return False
        
        # ClickSend API 使用 HTTP Basic Auth
        # API 端點：https://rest.clicksend.com/v3/sms/send
        api_url = 'https://rest.clicksend.com/v3/sms/send'
        
        # 準備手機號碼格式（台灣手機號碼需要轉換為國際格式）
        if phone.startswith('09'):
            # 台灣手機號碼：09xxxxxxxx -> +8869xxxxxxxx
            formatted_phone = '+886' + phone[1:]
        elif phone.startswith('+886'):
            formatted_phone = phone
        elif phone.startswith('0'):
            # 如果以 0 開頭但不是 09，轉換為 +886
            formatted_phone = '+886' + phone[1:]
        else:
            formatted_phone = phone
        
        # 準備消息內容
        message_text = f'您的好健健驗證碼是：{code}，有效期限為 10 分鐘。'
        
        # 構建請求數據
        payload = {
            'messages': [
                {
                    'source': 'php',
                    'body': message_text,
                    'to': formatted_phone
                }
            ]
        }
        
        # 如果設置了發送號碼，添加到消息中
        if clicksend_from_number:
            payload['messages'][0]['from'] = clicksend_from_number
        
        # 準備 HTTP Basic Auth
        credentials = f'{clicksend_username}:{clicksend_api_key}'
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
        
        # 發送請求
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        # 檢查響應
        if result.get('response_code') == 'SUCCESS' or result.get('http_code') == 200:
            logger.info(f'ClickSend SMS 發送成功: {result}')
            return True
        else:
            logger.error(f'ClickSend SMS 發送失敗: {result}')
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f'ClickSend SMS 請求失敗: {str(e)}')
        return False
    except Exception as e:
        logger.error(f'ClickSend SMS 發送失敗: {str(e)}')
        return False

