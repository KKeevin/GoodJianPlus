from decimal import Decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('plus', '0024_storefront_health_extensions')]

    operations = [
        migrations.AddField(
            model_name='usergoal',
            name='target_date',
            field=models.DateField(blank=True, null=True, verbose_name='目標日期'),
        ),
        migrations.AddField(
            model_name='usergoal',
            name='daily_water_goal_ml',
            field=models.PositiveIntegerField(default=2000, validators=[django.core.validators.MinValueValidator(500), django.core.validators.MaxValueValidator(6000)], verbose_name='每日飲水目標（ml）'),
        ),
        migrations.AddField(
            model_name='usergoal',
            name='daily_steps_goal',
            field=models.PositiveIntegerField(default=8000, validators=[django.core.validators.MinValueValidator(1000), django.core.validators.MaxValueValidator(50000)], verbose_name='每日步數目標'),
        ),
        migrations.AddField(
            model_name='usergoal',
            name='weekly_workout_goal_minutes',
            field=models.PositiveIntegerField(default=150, validators=[django.core.validators.MinValueValidator(10), django.core.validators.MaxValueValidator(3000)], verbose_name='每週運動目標（分鐘）'),
        ),
        migrations.AddField(
            model_name='usergoal',
            name='sleep_goal_hours',
            field=models.DecimalField(decimal_places=1, default=Decimal('8.0'), max_digits=3, validators=[django.core.validators.MinValueValidator(Decimal('4.0')), django.core.validators.MaxValueValidator(Decimal('12.0'))], verbose_name='每日睡眠目標（小時）'),
        ),
        migrations.CreateModel(
            name='DailyHealthLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recorded_date', models.DateField(default=django.utils.timezone.localdate, verbose_name='記錄日期')),
                ('sleep_hours', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('24'))], verbose_name='睡眠時數')),
                ('sleep_quality', models.PositiveSmallIntegerField(blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='睡眠品質')),
                ('steps', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(100000)], verbose_name='步數')),
                ('resting_heart_rate', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(30), django.core.validators.MaxValueValidator(240)], verbose_name='靜止心率（bpm）')),
                ('systolic_bp', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(60), django.core.validators.MaxValueValidator(260)], verbose_name='收縮壓（mmHg）')),
                ('diastolic_bp', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(30), django.core.validators.MaxValueValidator(180)], verbose_name='舒張壓（mmHg）')),
                ('mood', models.PositiveSmallIntegerField(blank=True, choices=[(1, '很低落'), (2, '不太好'), (3, '普通'), (4, '不錯'), (5, '很好')], null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='心情')),
                ('energy_level', models.PositiveSmallIntegerField(blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='精神狀態')),
                ('notes', models.CharField(blank=True, max_length=500, verbose_name='今日筆記')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_health_logs', to=settings.AUTH_USER_MODEL, verbose_name='用戶')),
            ],
            options={
                'verbose_name': '每日健康紀錄',
                'verbose_name_plural': '每日健康紀錄',
                'ordering': ['-recorded_date'],
                'indexes': [models.Index(fields=['user', 'recorded_date'], name='plus_dailyh_user_id_d679eb_idx')],
                'constraints': [models.UniqueConstraint(fields=('user', 'recorded_date'), name='unique_daily_health_log')],
            },
        ),
    ]
