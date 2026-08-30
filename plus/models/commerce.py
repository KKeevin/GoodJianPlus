from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

from plus.models.users import CustomUser
from plus.models.catalog import Product

class Cart(models.Model):
    """購物車"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, verbose_name='會員')
    session_key = models.CharField(max_length=50, null=True, blank=True, verbose_name='訪客識別')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '購物車'
        verbose_name_plural = '購物車管理'

    def __str__(self):
        if self.user:
            return f"{self.user.username}的購物車"
        return f"訪客購物車({self.session_key})"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """購物車商品項目"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='商品')
    quantity = models.PositiveIntegerField(default=1, verbose_name='數量')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='加入時間')

    class Meta:
        verbose_name = '購物車項目'
        verbose_name_plural = '購物車項目管理'
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    """訂單"""
    STATUS_CHOICES = [
        ('pending', '待處理'),
        ('confirmed', '已確認'),
        ('processing', '處理中'),
        ('shipped', '已出貨'),
        ('delivered', '已送達'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('refunded', '已退款'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', '待付款'),
        ('paid', '已付款'),
        ('failed', '付款失敗'),
        ('refunded', '已退款'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True, verbose_name='訂單編號')
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, verbose_name='訂購會員')
    
    # 收件人資訊
    shipping_name = models.CharField(max_length=100, verbose_name='收件人姓名')
    shipping_phone = models.CharField(max_length=20, verbose_name='收件人電話')
    shipping_email = models.EmailField(verbose_name='收件人信箱')
    shipping_address = models.TextField(verbose_name='收件地址')
    shipping_notes = models.TextField(blank=True, verbose_name='配送備註')
    
    # 金額相關
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品小計')
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='運費')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='稅額')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='折扣金額')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='總金額')
    
    # 支付相關
    payment_method = models.CharField(max_length=50, default='cod', verbose_name='支付方式')
    payment_transaction_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='支付交易編號')
    
    # 狀態
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='訂單狀態')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='付款狀態')
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='訂單建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name='出貨時間')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='送達時間')

    class Meta:
        verbose_name = '訂單'
        verbose_name_plural = '訂單管理'
        ordering = ['-created_at']

    def __str__(self):
        return f"訂單 {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """生成訂單編號"""
        import random
        import string
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.digits, k=4))
        return f"GJ{timestamp}{random_str}"


class OrderItem(models.Model):
    """訂單項目"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='商品')
    product_name = models.CharField(max_length=200, verbose_name='商品名稱')  # 快照
    product_sku = models.CharField(max_length=50, verbose_name='商品編號')  # 快照
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='單價')  # 快照
    quantity = models.PositiveIntegerField(verbose_name='數量')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='小計')

    class Meta:
        verbose_name = '訂單項目'
        verbose_name_plural = '訂單項目管理'

    def __str__(self):
        return f"{self.order.order_number} - {self.product_name}"


class Coupon(models.Model):
    """優惠券"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', '百分比折扣'),
        ('fixed', '固定金額折扣'),
        ('free_shipping', '免運費'),
    ]
    
    code = models.CharField(max_length=50, unique=True, verbose_name='優惠碼')
    name = models.CharField(max_length=100, verbose_name='優惠券名稱')
    description = models.TextField(blank=True, verbose_name='描述')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, verbose_name='折扣類型')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='折扣值')
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='最低消費金額')
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='最大折扣金額')
    usage_limit = models.PositiveIntegerField(null=True, blank=True, verbose_name='使用次數限制')
    used_count = models.PositiveIntegerField(default=0, verbose_name='已使用次數')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    valid_from = models.DateTimeField(verbose_name='有效期開始')
    valid_until = models.DateTimeField(verbose_name='有效期結束')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '優惠券'
        verbose_name_plural = '優惠券管理'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_until and
            (self.usage_limit is None or self.used_count < self.usage_limit)
        )


class Wishlist(models.Model):
    """收藏清單"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wishlist')
    products = models.ManyToManyField(Product, blank=True, verbose_name='收藏商品')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '收藏清單'
        verbose_name_plural = '收藏清單管理'

    def __str__(self):
        return f"{self.user.username}的收藏清單"


class ShippingMethod(models.Model):
    """配送方式"""
    name = models.CharField(max_length=100, verbose_name='配送方式名稱')
    description = models.TextField(blank=True, verbose_name='描述')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='配送費用')
    estimated_days = models.PositiveIntegerField(verbose_name='預估配送天數')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='排序')

    class Meta:
        verbose_name = '配送方式'
        verbose_name_plural = '配送方式管理'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

