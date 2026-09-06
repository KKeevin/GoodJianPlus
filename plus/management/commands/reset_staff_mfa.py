from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = '僅在可信 SSH 主機使用：清除指定後台帳戶驗證器，下次登入重新綁定。'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('--confirm', action='store_true')

    def handle(self, *args, **options):
        if not options['confirm']:
            raise CommandError('請確認身分後加上 --confirm；這會使指定帳戶既有 OTP session 失效。')
        user = get_user_model().objects.filter(username=options['username'], is_staff=True).first()
        if user is None:
            raise CommandError('找不到後台帳戶')
        TOTPDevice.objects.filter(user=user).delete()
        self.stdout.write('已清除驗證器，請重新登入並綁定。')
