# Generated migration - Modified to include data migration

from django.db import migrations, models
from decimal import Decimal


def convert_height_weight_to_decimal(apps, schema_editor):
    """將整數格式的身高和體重轉換為小數格式"""
    UserProfile = apps.get_model('plus', 'UserProfile')
    for profile in UserProfile.objects.all():
        if profile.height is not None:
            # 將整數（例如 1756）轉換為小數（175.6）
            profile.height = Decimal(str(profile.height)) / Decimal('10')
        if profile.weight is not None:
            # 將整數（例如 705）轉換為小數（70.5）
            profile.weight = Decimal(str(profile.weight)) / Decimal('10')
        profile.save()


def reverse_convert_height_weight_to_integer(apps, schema_editor):
    """將小數格式的身高和體重轉換回整數格式（反向遷移）"""
    UserProfile = apps.get_model('plus', 'UserProfile')
    for profile in UserProfile.objects.all():
        if profile.height is not None:
            # 將小數（例如 175.6）轉換為整數（1756）
            profile.height = int(float(profile.height) * 10)
        if profile.weight is not None:
            # 將小數（例如 70.5）轉換為整數（705）
            profile.weight = int(float(profile.weight) * 10)
        profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ('plus', '0007_dailynutritiontarget'),
    ]

    operations = [
        # 先轉換數據
        migrations.RunPython(convert_height_weight_to_decimal, reverse_convert_height_weight_to_integer),
        # 再修改欄位類型
        migrations.AlterField(
            model_name='userprofile',
            name='height',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='身高(cm)'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='weight',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='體重(kg)'),
        ),
    ]
