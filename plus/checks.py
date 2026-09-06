from django.conf import settings
from django.core.checks import Warning, Error, register, Tags


@register(Tags.security, deploy=True)
def production_checks(app_configs, **kwargs):
    issues = []
    if not settings.ADMIN_REQUIRE_OTP:
        issues.append(Warning('後台雙重驗證尚未啟用。', hint='設定 ADMIN_REQUIRE_OTP=True 並完成綁定。', id='plus.W001'))
    if '*' in settings.ALLOWED_HOSTS:
        issues.append(Error('正式機不可使用萬用 ALLOWED_HOSTS。', id='plus.E001'))
    if settings.DATABASES['default']['ENGINE'].endswith('sqlite3'):
        issues.append(Warning('目前使用 SQLite；請定期驗證備份，擴量前測試 MySQL/PostgreSQL。', id='plus.W002'))
    return issues
