from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '發送一封測試郵件到 EMAIL_HOST_USER'

    def handle(self, *args, **options):
        self.stdout.write('=' * 50)
        self.stdout.write('正在測試郵件發送...')
        self.stdout.write(f'發件人：{settings.EMAIL_HOST_USER}')
        self.stdout.write(f'SMTP 伺服器：{settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        self.stdout.write('=' * 50)

        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            self.stderr.write('[錯誤] 請先在 .env 設置 EMAIL_HOST_USER 與 EMAIL_HOST_PASSWORD')
            return

        try:
            send_mail(
                subject='好健健 GoodJian Plus - 郵件功能測試',
                message='這是一封測試郵件。如果您收到此郵件，表示郵件功能設置成功！',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],
                fail_silently=False,
            )
            self.stdout.write('[成功] 測試郵件已發送！')
        except Exception as e:
            self.stderr.write(f'[失敗] 發送失敗：{str(e)}')
