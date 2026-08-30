# Generated manually to set verification status for existing users

from django.db import migrations


def set_verification_status(apps, schema_editor):
    """設置現有用戶的驗證狀態"""
    CustomUser = apps.get_model('plus', 'CustomUser')
    
    for user in CustomUser.objects.all():
        # 判斷手機號碼是否已驗證
        # 如果用戶有手機號碼且郵箱是臨時郵箱，表示是通過手機註冊的
        if user.phone and user.email and '@temp.goodjian.shop' in user.email:
            user.phone_verified = True
        else:
            user.phone_verified = False
        
        # 判斷電子郵件是否已驗證
        # 如果用戶已驗證且郵箱不是臨時郵箱，表示郵件已驗證
        if user.is_verified and user.email and '@temp.goodjian.shop' not in user.email:
            user.email_verified = True
        else:
            user.email_verified = False
        
        user.save(update_fields=['phone_verified', 'email_verified'])


def reverse_verification_status(apps, schema_editor):
    """反向操作：重置驗證狀態"""
    CustomUser = apps.get_model('plus', 'CustomUser')
    CustomUser.objects.all().update(phone_verified=False, email_verified=False)


class Migration(migrations.Migration):

    dependencies = [
        ('plus', '0017_customuser_email_verified_customuser_phone_verified'),
    ]

    operations = [
        migrations.RunPython(set_verification_status, reverse_verification_status),
    ]

