from django.core.management.base import BaseCommand
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.db import connection


class Command(BaseCommand):
    help = (
        '補上 social_django 舊套件（default / social_auth）的遷移紀錄，'
        '修正 Django 5 執行 migrate 時 KeyError: (social_django, code) 的問題。'
    )

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        recorder.ensure_schema()
        applied = recorder.applied_migrations()

        if ('social_django', '0001_initial') not in applied:
            self.stdout.write('尚未套用 social_django.0001_initial，不需修復。')
            return

        loader = MigrationLoader(connection, ignore_no_migrations=True)
        missing = []
        for migration in loader.disk_migrations.values():
            if migration.app_label != 'social_django' or not migration.replaces:
                continue
            for app_label, name in migration.replaces:
                key = (app_label, name)
                if key not in applied:
                    missing.append(key)

        if not missing:
            self.stdout.write(self.style.SUCCESS('social_django 遷移紀錄已完整，無需修復。'))
            return

        seen = set()
        for app_label, name in missing:
            if (app_label, name) in seen:
                continue
            seen.add((app_label, name))
            recorder.record_applied(app_label, name)
            self.stdout.write(f'已補上遷移紀錄：{app_label}.{name}')

        self.stdout.write(self.style.SUCCESS('修復完成，請再執行 python manage.py migrate'))
