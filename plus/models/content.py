from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

from plus.models.users import CustomUser

class ArticleCategory(models.Model):
    """文章分類"""
    name = models.CharField(max_length=100, unique=True, verbose_name='分類名稱')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='URL標識')
    description = models.TextField(blank=True, verbose_name='分類描述')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '文章分類'
        verbose_name_plural = '文章分類管理'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Article(models.Model):
    """健康專欄文章"""
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已發佈'),
        ('archived', '已歸檔'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='文章標題')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL標識')
    category = models.ForeignKey(ArticleCategory, on_delete=models.PROTECT, verbose_name='文章分類')
    
    # 封面圖片
    cover_image = models.ImageField(upload_to='articles/covers/', blank=True, null=True, verbose_name='封面圖片')
    
    # 文章內容
    content = models.TextField(verbose_name='文章內容（HTML）')
    excerpt = models.TextField(max_length=500, blank=True, verbose_name='文章摘要')
    
    # 狀態與設定
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='文章狀態')
    is_featured = models.BooleanField(default=False, verbose_name='是否為精選文章')
    view_count = models.PositiveIntegerField(default=0, verbose_name='瀏覽次數')
    
    # SEO相關
    meta_title = models.CharField(max_length=100, blank=True, verbose_name='SEO標題')
    meta_description = models.CharField(max_length=160, blank=True, verbose_name='SEO描述')
    meta_keywords = models.CharField(max_length=200, blank=True, verbose_name='SEO關鍵字')
    
    # 作者資訊
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='作者')
    author_name = models.CharField(max_length=100, blank=True, verbose_name='作者名稱（手動輸入）')
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='發佈時間')

    class Meta:
        verbose_name = '健康專欄文章'
        verbose_name_plural = '健康專欄文章管理'
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # 如果狀態改為已發佈且沒有發佈時間，設置發佈時間
        if self.status == 'published' and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def display_author(self):
        """顯示作者名稱"""
        if self.author:
            return self.author.get_full_name() or self.author.username
        return self.author_name or '好健健編輯團隊'

    @property
    def reading_time(self):
        """估算閱讀時間（分鐘）"""
        # 簡單計算：假設每分鐘閱讀200字
        import re
        text_content = re.sub(r'<[^>]+>', '', self.content)
        word_count = len(text_content)
        minutes = max(1, round(word_count / 200))
        return minutes


class ArticleImage(models.Model):
    """文章相關圖片"""
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='images', verbose_name='文章')
    image = models.ImageField(upload_to='articles/images/', verbose_name='圖片')
    alt_text = models.CharField(max_length=200, blank=True, verbose_name='替代文字')
    caption = models.CharField(max_length=200, blank=True, verbose_name='圖片說明')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '文章圖片'
        verbose_name_plural = '文章圖片管理'
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return f"{self.article.title} - 圖片 {self.id}"

