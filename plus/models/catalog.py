from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

from plus.models.users import CustomUser

class Category(models.Model):
    """商品分類"""
    name = models.CharField(max_length=50, unique=True, verbose_name='分類名稱')
    slug = models.SlugField(max_length=50, unique=True, verbose_name='URL標識')
    description = models.TextField(blank=True, verbose_name='分類描述')
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name='分類圖片')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='children', verbose_name='父分類')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '商品分類'
        verbose_name_plural = '商品分類管理'
        ordering = ['sort_order', 'name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def get_full_path(self):
        """獲取完整的分類路徑"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name


class Brand(models.Model):
    """品牌"""
    name = models.CharField(max_length=100, unique=True, verbose_name='品牌名稱')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='URL標識')
    description = models.TextField(blank=True, verbose_name='品牌描述')
    logo = models.ImageField(upload_to='brands/', blank=True, null=True, verbose_name='品牌Logo')
    website = models.URLField(blank=True, verbose_name='官方網站')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '品牌'
        verbose_name_plural = '品牌管理'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """商品"""
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已發佈'),
        ('discontinued', '已停產'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='商品名稱')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL標識')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='商品分類')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, null=True, blank=True, verbose_name='品牌')
    sku = models.CharField(max_length=50, unique=True, verbose_name='商品編號')
    description = models.TextField(verbose_name='商品描述')
    short_description = models.TextField(max_length=500, verbose_name='簡短描述')
    
    # 價格相關
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='售價')
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='原價')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='成本價')
    
    # 庫存相關
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='庫存數量')
    min_stock_level = models.PositiveIntegerField(default=5, verbose_name='最低庫存警戒')
    max_stock_level = models.PositiveIntegerField(default=1000, verbose_name='最高庫存上限')
    
    # 商品屬性
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='重量(kg)')
    dimensions = models.CharField(max_length=100, blank=True, verbose_name='尺寸')
    color = models.CharField(max_length=50, blank=True, verbose_name='顏色')
    size = models.CharField(max_length=50, blank=True, verbose_name='尺碼')
    
    # 營養成分 (針對食品類)
    calories_per_100g = models.PositiveIntegerField(null=True, blank=True, verbose_name='每100g熱量')
    protein_per_100g = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='每100g蛋白質(g)')
    carbs_per_100g = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='每100g碳水化合物(g)')
    fat_per_100g = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='每100g脂肪(g)')
    
    # 狀態與設定
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='商品狀態')
    is_featured = models.BooleanField(default=False, verbose_name='是否為推薦商品')
    is_digital = models.BooleanField(default=False, verbose_name='是否為數位商品')
    requires_shipping = models.BooleanField(default=True, verbose_name='是否需要配送')
    allow_backorder = models.BooleanField(default=False, verbose_name='是否允許預購')
    
    # SEO相關
    meta_title = models.CharField(max_length=100, blank=True, verbose_name='SEO標題')
    meta_description = models.CharField(max_length=160, blank=True, verbose_name='SEO描述')
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='發佈時間')

    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品管理'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return round((self.original_price - self.price) / self.original_price * 100)
        return 0


class ProductImage(models.Model):
    """商品圖片"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/', verbose_name='商品圖片')
    alt_text = models.CharField(max_length=200, blank=True, verbose_name='圖片替代文字')
    is_primary = models.BooleanField(default=False, verbose_name='是否為主圖')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='上傳時間')

    class Meta:
        verbose_name = '商品圖片'
        verbose_name_plural = '商品圖片管理'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.product.name} - 圖片{self.id}"


class ProductReview(models.Model):
    """商品評價"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='評價者')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='評分'
    )
    title = models.CharField(max_length=200, verbose_name='評價標題')
    content = models.TextField(verbose_name='評價內容')
    is_verified_purchase = models.BooleanField(default=False, verbose_name='已驗證購買')
    is_approved = models.BooleanField(default=True, verbose_name='是否已審核通過')
    helpful_count = models.PositiveIntegerField(default=0, verbose_name='有用票數')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='評價時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '商品評價'
        verbose_name_plural = '商品評價管理'
        unique_together = ['product', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} 對 {self.product.name} 的評價"

