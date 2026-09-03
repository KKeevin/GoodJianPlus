from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

from plus.models.users import CustomUser

class SiteSettings(models.Model):
    """網站設定"""
    site_name = models.CharField(max_length=100, default='好健健 GoodJian Plus', verbose_name='網站名稱')
    site_description = models.TextField(blank=True, verbose_name='網站描述')
    homepage_slogan = models.CharField(max_length=200, default='健康生活觸手可及', verbose_name='首頁標語')
    contact_email = models.EmailField(verbose_name='聯絡信箱')
    contact_phone = models.CharField(max_length=20, verbose_name='聯絡電話')
    contact_address = models.TextField(verbose_name='公司地址')
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=1000, verbose_name='免運門檻')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.05, verbose_name='稅率')
    currency = models.CharField(max_length=3, default='TWD', verbose_name='幣別')
    is_maintenance_mode = models.BooleanField(default=False, verbose_name='維護模式')

    class Meta:
        verbose_name = '網站設定'
        verbose_name_plural = '網站設定'

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        # 確保只有一筆設定記錄
        if not self.pk and SiteSettings.objects.exists():
            raise ValueError('只能存在一筆網站設定記錄')
        return super().save(*args, **kwargs)


class Notification(models.Model):
    """通知"""
    TYPE_CHOICES = [
        ('order', '訂單通知'),
        ('promotion', '促銷通知'),
        ('system', '系統通知'),
        ('review', '評價通知'),
        ('cart', '購物車通知'),
        ('wishlist', '收藏通知'),
        ('goal', '目標通知'),
        ('stock', '庫存通知'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='通知類型')
    title = models.CharField(max_length=200, verbose_name='標題')
    message = models.TextField(verbose_name='訊息內容')
    is_read = models.BooleanField(default=False, verbose_name='是否已讀')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知管理'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class NewsletterSubscriber(models.Model):
    """電子報訂閱"""
    email = models.EmailField(unique=True, verbose_name='電子郵件')
    is_active = models.BooleanField(default=True, verbose_name='訂閱中')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='訂閱時間')

    class Meta:
        verbose_name = '電子報訂閱'
        verbose_name_plural = '電子報訂閱'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

