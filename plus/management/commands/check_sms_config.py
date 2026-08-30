import os
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '檢查 SMS / ClickSend 相關環境變數與遷移狀態'

    def handle(self, *args, **options):
        self.stdout.write('=' * 50)
        self.stdout.write('SMS 配置檢查')
        self.stdout.write('=' * 50)

        sms_test_mode = os.getenv('SMS_TEST_MODE', 'Not set')
        sms_provider = os.getenv('SMS_PROVIDER', 'Not set')
        clicksend_username = os.getenv('CLICKSEND_USERNAME', 'Not set')
        clicksend_api_key = os.getenv('CLICKSEND_API_KEY', 'Not set')

        self.stdout.write(f'SMS_TEST_MODE: {sms_test_mode}')
        self.stdout.write(f'SMS_PROVIDER: {sms_provider}')
        if clicksend_username != 'Not set':
            self.stdout.write('CLICKSEND_USERNAME: set')
        else:
            self.stdout.write('CLICKSEND_USERNAME: Not set')
        if clicksend_api_key != 'Not set':
            self.stdout.write('CLICKSEND_API_KEY: set')
        else:
            self.stdout.write('CLICKSEND_API_KEY: Not set')

        errors = []
        warnings = []

        if sms_test_mode == 'Not set':
            errors.append('[X] SMS_TEST_MODE 未設置')
        elif sms_test_mode.lower() == 'true':
            warnings.append('[!] SMS_TEST_MODE 為 True，將使用測試模式（不會實際發送簡訊）')
        else:
            self.stdout.write('[OK] SMS_TEST_MODE 已設置為 False（將實際發送簡訊）')

        if sms_provider == 'Not set':
            errors.append('[X] SMS_PROVIDER 未設置')
        elif sms_provider.lower() != 'clicksend':
            warnings.append(f'[!] SMS_PROVIDER 設置為 {sms_provider}，不是 clicksend')
        else:
            self.stdout.write('[OK] SMS_PROVIDER 已設置為 clicksend')

        if clicksend_username == 'Not set':
            errors.append('[X] CLICKSEND_USERNAME 未設置')
        else:
            self.stdout.write('[OK] CLICKSEND_USERNAME 已設置')

        if clicksend_api_key == 'Not set':
            errors.append('[X] CLICKSEND_API_KEY 未設置')
        else:
            self.stdout.write('[OK] CLICKSEND_API_KEY 已設置')

        try:
            import requests  # noqa: F401
            self.stdout.write('[OK] requests 套件已安裝')
        except ImportError:
            errors.append('[X] requests 套件未安裝，請執行: pip install requests')

        try:
            output = StringIO()
            call_command('showmigrations', 'plus', '--list', stdout=output)
            output_str = output.getvalue()
            if '0013_phoneverificationcode' in output_str:
                self.stdout.write('[OK] PhoneVerificationCode 遷移存在')
            else:
                errors.append('[X] PhoneVerificationCode 模型遷移文件不存在')
        except Exception as e:
            warnings.append(f'[!] 無法檢查數據庫遷移狀態: {str(e)}')

        self.stdout.write('')
        self.stdout.write('=' * 50)
        if errors:
            self.stdout.write('[ERROR] 發現錯誤：')
            for error in errors:
                self.stdout.write(f'  {error}')
        elif warnings:
            self.stdout.write('[WARNING] 警告：')
            for warning in warnings:
                self.stdout.write(f'  {warning}')
        else:
            self.stdout.write('[SUCCESS] 所有配置檢查通過！')
        self.stdout.write('=' * 50)
