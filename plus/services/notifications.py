from plus.models import Notification
import logging

logger = logging.getLogger(__name__)


def send_notification(user, notification_type, title, message):
    """
    發送通知的輔助函數

    Args:
        user: 用戶對象
        notification_type: 通知類型
        title: 通知標題
        message: 通知內容
    """
    if not user or not user.is_authenticated:
        return

    try:
        Notification.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message
        )
        logger.info(f'Notification sent to {user.username}: {title}')
    except Exception as e:
        logger.error(f'Failed to create notification: {str(e)}')
