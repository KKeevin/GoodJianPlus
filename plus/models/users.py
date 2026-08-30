from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

class CustomUser(AbstractUser):
    """擴展的用戶模型"""
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='手機號碼')
    phone_verified = models.BooleanField(default=False, verbose_name='手機號碼已認證')
    email_verified = models.BooleanField(default=False, verbose_name='電子郵件已認證')
    birthday = models.DateField(null=True, blank=True, verbose_name='生日')
    address = models.TextField(blank=True, verbose_name='地址')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='頭像')
    is_verified = models.BooleanField(default=False, verbose_name='是否已驗證', editable=False, help_text='自動計算：手機或電子郵件任一驗證即為已驗證')
    needs_profile_update = models.BooleanField(default=False, verbose_name='需要更新資料')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='註冊時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '會員'
        verbose_name_plural = '會員管理'
        db_table = 'plus_user'

    def __str__(self):
        return self.username
    
    def save(self, *args, **kwargs):
        """覆寫 save 方法，自動計算 is_verified"""
        # 如果手機或電子郵件任一驗證，則設置為已驗證
        self.is_verified = self.phone_verified or self.email_verified
        super().save(*args, **kwargs)


class EmailVerificationToken(models.Model):
    """郵件驗證 Token"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='email_verification_tokens', verbose_name='用戶')
    token = models.CharField(max_length=64, unique=True, verbose_name='驗證碼')
    token_type = models.CharField(max_length=20, choices=[
        ('email_verification', '郵件驗證'),
        ('password_reset', '密碼重設'),
    ], default='email_verification', verbose_name='Token 類型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    expires_at = models.DateTimeField(verbose_name='過期時間')
    is_used = models.BooleanField(default=False, verbose_name='是否已使用')

    class Meta:
        verbose_name = '郵件驗證 Token'
        verbose_name_plural = '郵件驗證 Token 管理'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.token_type} - {self.token[:8]}...'

    def is_valid(self):
        """檢查 Token 是否有效"""
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at


class PhoneVerificationCode(models.Model):
    """手機驗證碼"""
    phone = models.CharField(max_length=20, verbose_name='手機號碼')
    code = models.CharField(max_length=6, verbose_name='驗證碼')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    expires_at = models.DateTimeField(verbose_name='過期時間')
    is_used = models.BooleanField(default=False, verbose_name='是否已使用')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 地址')
    
    class Meta:
        verbose_name = '手機驗證碼'
        verbose_name_plural = '手機驗證碼管理'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'code', 'is_used']),
        ]
    
    def __str__(self):
        return f'{self.phone} - {self.code}'
    
    def is_valid(self):
        """檢查驗證碼是否有效"""
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at
    
    @classmethod
    def generate_code(cls):
        """生成6位數驗證碼"""
        import secrets
        return f'{secrets.randbelow(900000) + 100000}'


class EmailChangeRequest(models.Model):
    """電子郵件變更請求"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='email_change_requests', verbose_name='用戶')
    new_email = models.EmailField(verbose_name='新電子郵件')
    token = models.CharField(max_length=64, unique=True, verbose_name='驗證 Token')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    expires_at = models.DateTimeField(verbose_name='過期時間')
    is_used = models.BooleanField(default=False, verbose_name='是否已使用')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 地址')
    
    class Meta:
        verbose_name = '電子郵件變更請求'
        verbose_name_plural = '電子郵件變更請求管理'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token', 'is_used']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.new_email}'
    
    def is_valid(self):
        """檢查 Token 是否有效"""
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at
    
    @classmethod
    def generate_token(cls):
        """生成驗證 Token"""
        import secrets
        return secrets.token_urlsafe(32)


class UserProfile(models.Model):
    """會員詳細資料"""
    GENDER_CHOICES = [
        ('M', '男性'),
        ('F', '女性'),
        ('O', '其他'),
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, verbose_name='性別')
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='身高(cm)')
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='體重(kg)')
    fitness_goal = models.CharField(max_length=100, blank=True, verbose_name='健身目標')
    dietary_restrictions = models.TextField(blank=True, verbose_name='飲食限制')
    emergency_contact = models.CharField(max_length=100, blank=True, verbose_name='緊急聯絡人')
    emergency_phone = models.CharField(max_length=20, blank=True, verbose_name='緊急聯絡人電話')
    
    class Meta:
        verbose_name = '會員資料'
        verbose_name_plural = '會員資料管理'

    def __str__(self):
        return f"{self.user.username}的資料"

