"""
郵件發送工具模組
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import logging
import secrets

from ..models import CustomUser, EmailVerificationToken, EmailChangeRequest

logger = logging.getLogger(__name__)


def _site_base_url():
    domain = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
    protocol = 'https' if not settings.DEBUG else 'http'
    return f'{protocol}://{domain}'


def generate_verification_token():
    """生成驗證 Token"""
    return secrets.token_urlsafe(32)


def create_verification_token(user, token_type='email_verification', expires_hours=24):
    """
    創建驗證 Token
    
    Args:
        user: 用戶對象
        token_type: Token 類型 ('email_verification' 或 'password_reset')
        expires_hours: 過期時間（小時）
    
    Returns:
        EmailVerificationToken 對象
    """
    # 刪除舊的未使用 Token
    EmailVerificationToken.objects.filter(
        user=user,
        token_type=token_type,
        is_used=False
    ).delete()
    
    # 創建新 Token
    token = generate_verification_token()
    expires_at = timezone.now() + timedelta(hours=expires_hours)
    
    verification_token = EmailVerificationToken.objects.create(
        user=user,
        token=token,
        token_type=token_type,
        expires_at=expires_at
    )
    
    return verification_token


def send_email_with_template(subject, template_name, context, recipient_list, from_email=None):
    """
    使用模板發送 HTML 郵件
    
    Args:
        subject: 郵件主題
        template_name: 模板名稱（相對於 templates/emails/）
        context: 模板上下文
        recipient_list: 收件人列表
        from_email: 發件人（默認為 DEFAULT_FROM_EMAIL）
    
    Returns:
        bool: 是否發送成功
    """
    try:
        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        # 渲染 HTML 模板
        html_message = render_to_string(f'emails/{template_name}', context)
        
        # 生成純文本版本（從 HTML 中提取）
        text_message = strip_tags(html_message)
        
        # 發送郵件
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=from_email,
            to=recipient_list
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()
        
        logger.info(f'Email sent successfully to {recipient_list}: {subject}')
        return True
    except Exception as e:
        logger.error(f'Failed to send email to {recipient_list}: {str(e)}')
        return False


def send_verification_email(user, request=None):
    """
    發送郵件驗證信
    
    Args:
        user: 用戶對象
        request: HttpRequest 對象（用於生成完整 URL）
    
    Returns:
        bool: 是否發送成功
    """
    try:
        # 創建驗證 Token
        verification_token = create_verification_token(
            user=user,
            token_type='email_verification',
            expires_hours=48  # 48 小時內有效
        )
        
        # 生成驗證連結
        if request:
            verification_url = request.build_absolute_uri(
                reverse('verify_email', kwargs={'token': verification_token.token})
            )
        else:
            # 如果沒有 request，使用默認域名
            verification_url = f"{_site_base_url()}{reverse('verify_email', kwargs={'token': verification_token.token})}"
        
        # 準備郵件內容
        context = {
            'user': user,
            'verification_url': verification_url,
            'token': verification_token.token,
            'expires_hours': 48,
            'site_name': '好健健 GoodJian Plus',
        }
        
        # 發送郵件
        subject = '請驗證您的電子郵件地址 - 好健健 GoodJian Plus'
        success = send_email_with_template(
            subject=subject,
            template_name='verification.html',
            context=context,
            recipient_list=[user.email]
        )
        
        if success:
            logger.info(f'Verification email sent to {user.email}')
        else:
            logger.error(f'Failed to send verification email to {user.email}')
        
        return success
    except Exception as e:
        logger.error(f'Error sending verification email to {user.email}: {str(e)}')
        return False


def send_welcome_email(user):
    """
    發送歡迎郵件（註冊成功後）
    
    Args:
        user: 用戶對象
    
    Returns:
        bool: 是否發送成功
    """
    try:
        context = {
            'user': user,
            'site_name': '好健健 GoodJian Plus',
            'site_url': _site_base_url(),
        }
        
        subject = '歡迎加入好健健 GoodJian Plus！'
        success = send_email_with_template(
            subject=subject,
            template_name='welcome.html',
            context=context,
            recipient_list=[user.email]
        )
        
        if success:
            logger.info(f'Welcome email sent to {user.email}')
        else:
            logger.error(f'Failed to send welcome email to {user.email}')
        
        return success
    except Exception as e:
        logger.error(f'Error sending welcome email to {user.email}: {str(e)}')
        return False


def send_password_reset_email(user, request=None):
    """
    發送密碼重設郵件
    
    Args:
        user: 用戶對象
        request: HttpRequest 對象（用於生成完整 URL）
    
    Returns:
        bool: 是否發送成功
    """
    try:
        # 創建密碼重設 Token
        reset_token = create_verification_token(
            user=user,
            token_type='password_reset',
            expires_hours=2  # 2 小時內有效
        )
        
        # 生成重設連結（確保使用正確的 URL，不是 admin 的 URL）
        if request:
            # 使用 request.build_absolute_uri 但確保路徑正確
            reset_path = reverse('password_reset_confirm', kwargs={'token': reset_token.token})
            reset_url = request.build_absolute_uri(reset_path)
            # 確保 URL 不包含 /admin/
            if '/admin/' in reset_url:
                # 如果包含 /admin/，手動構建正確的 URL
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
                reset_url = f"{protocol}://{domain}{reset_path}"
        else:
            # 如果沒有 request，使用默認域名
            reset_path = reverse('password_reset_confirm', kwargs={'token': reset_token.token})
            reset_url = f"{_site_base_url()}{reset_path}"
        
        # 記錄生成的 URL 以便調試
        logger.info(f'Generated password reset URL: {reset_url} for user {user.email}')
        
        # 準備郵件內容
        context = {
            'user': user,
            'reset_url': reset_url,
            'token': reset_token.token,
            'expires_hours': 2,
            'site_name': '好健健 GoodJian Plus',
        }
        
        # 發送郵件
        subject = '重設您的密碼 - 好健健 GoodJian Plus'
        success = send_email_with_template(
            subject=subject,
            template_name='password_reset.html',
            context=context,
            recipient_list=[user.email]
        )
        
        if success:
            logger.info(f'Password reset email sent to {user.email}')
        else:
            logger.error(f'Failed to send password reset email to {user.email}')
        
        return success
    except Exception as e:
        logger.error(f'Error sending password reset email to {user.email}: {str(e)}')
        return False


def send_order_confirmation_email(order, request=None):
    """
    發送訂單確認郵件
    
    Args:
        order: 訂單對象
        request: HttpRequest 對象（用於生成完整 URL）
    
    Returns:
        bool: 是否發送成功
    """
    try:
        # 生成訂單詳情連結
        if request:
            order_url = request.build_absolute_uri(
                reverse('order_detail', kwargs={'order_id': order.id})
            )
        else:
            order_url = f"{_site_base_url()}{reverse('order_detail', kwargs={'order_id': order.id})}"
        
        # 準備郵件內容
        context = {
            'order': order,
            'order_url': order_url,
            'user': order.user,
            'site_name': '好健健 GoodJian Plus',
            'items': order.items.all(),
        }
        
        # 發送郵件
        subject = f'訂單確認 - 訂單編號：{order.order_number}'
        success = send_email_with_template(
            subject=subject,
            template_name='order_confirmation.html',
            context=context,
            recipient_list=[order.user.email]
        )
        
        if success:
            logger.info(f'Order confirmation email sent to {order.user.email} for order {order.order_number}')
        else:
            logger.error(f'Failed to send order confirmation email to {order.user.email}')
        
        return success
    except Exception as e:
        logger.error(f'Error sending order confirmation email: {str(e)}')
        return False


def send_order_status_update_email(order, request=None):
    """
    發送訂單狀態更新郵件
    
    Args:
        order: 訂單對象
        request: HttpRequest 對象（用於生成完整 URL）
    
    Returns:
        bool: 是否發送成功
    """
    try:
        # 生成訂單詳情連結
        if request:
            order_url = request.build_absolute_uri(
                reverse('order_detail', kwargs={'order_id': order.id})
            )
        else:
            order_url = f"{_site_base_url()}{reverse('order_detail', kwargs={'order_id': order.id})}"
        
        # 準備郵件內容
        context = {
            'order': order,
            'order_url': order_url,
            'user': order.user,
            'site_name': '好健健 GoodJian Plus',
            'status_display': order.get_status_display(),
            'tracking_number': order.tracking_number,
            'tracking_url': order.get_public_tracking_url(),
            'carrier_display': order.get_carrier_display() if order.carrier else '',
        }
        
        # 發送郵件
        subject = f'訂單狀態更新 - 訂單編號：{order.order_number}'
        success = send_email_with_template(
            subject=subject,
            template_name='order_status_update.html',
            context=context,
            recipient_list=[order.user.email]
        )
        
        if success:
            logger.info(f'Order status update email sent to {order.user.email} for order {order.order_number}')
        else:
            logger.error(f'Failed to send order status update email to {order.user.email}')
        
        return success
    except Exception as e:
        logger.error(f'Error sending order status update email: {str(e)}')
        return False


def send_email_change_verification_email(user, new_email, request=None):
    """
    發送電子郵件變更驗證信
    
    Args:
        user: 用戶對象
        new_email: 新的電子郵件地址
        request: HttpRequest 對象（用於生成完整 URL）
    
    Returns:
        bool: 是否發送成功
    """
    try:
        # 刪除舊的未使用請求
        EmailChangeRequest.objects.filter(
            user=user,
            is_used=False
        ).delete()
        
        # 創建新的變更請求
        token = EmailChangeRequest.generate_token()
        expires_at = timezone.now() + timedelta(hours=48)  # 48 小時內有效
        
        # 獲取 IP 地址
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
        
        change_request = EmailChangeRequest.objects.create(
            user=user,
            new_email=new_email,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address
        )
        
        # 生成驗證連結
        if request:
            verification_url = request.build_absolute_uri(
                reverse('verify_email_change', kwargs={'token': token})
            )
        else:
            # 如果沒有 request，使用默認域名
            verification_url = f"{_site_base_url()}{reverse('verify_email_change', kwargs={'token': token})}"
        
        # 準備郵件內容
        context = {
            'user': user,
            'new_email': new_email,
            'verification_url': verification_url,
            'token': token,
            'expires_hours': 48,
            'site_name': '好健健 GoodJian Plus',
        }
        
        # 發送郵件
        subject = '請確認您的電子郵件變更 - 好健健 GoodJian Plus'
        success = send_email_with_template(
            subject=subject,
            template_name='email_change_verification.html',
            context=context,
            recipient_list=[new_email]  # 發送到新郵件地址
        )
        
        if success:
            logger.info(f'Email change verification email sent to {new_email} for user {user.username}')
        else:
            logger.error(f'Failed to send email change verification email to {new_email}')
            change_request.delete()  # 如果發送失敗，刪除請求
        
        return success
    except Exception as e:
        logger.error(f'Error sending email change verification email: {str(e)}')
        return False

