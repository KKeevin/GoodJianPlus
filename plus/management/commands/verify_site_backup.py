from django.core.management.base import BaseCommand, CommandError
from plus.services.backups import verify_backup


class Command(BaseCommand):
    help = '在暫存目錄驗證備份，不覆蓋正式資料。'

    def add_arguments(self, parser):
        parser.add_argument('archive')

    def handle(self, *args, **options):
        try:
            count = verify_backup(options['archive'])
        except Exception as exc:
            raise CommandError('備份驗證失敗') from exc
        self.stdout.write(self.style.SUCCESS(f'驗證成功：{count} 個檔案。'))
