from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from plus.services.backups import create_backup


class Command(BaseCommand):
    help = '備份目前 SQLite 與 media，驗證內容及資料庫完整性。'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True)

    def handle(self, *args, **options):
        database = settings.DATABASES['default']
        if not database['ENGINE'].endswith('sqlite3'):
            raise CommandError('此指令限 SQLite；MySQL 請使用資料庫原生備份工具。')
        try:
            count = create_backup(database['NAME'], settings.MEDIA_ROOT, options['output'])
        except (ValueError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f'備份及驗證成功：{count} 個檔案。請另存至異機。'))
