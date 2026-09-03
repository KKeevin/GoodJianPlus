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
        from django.db.models import Sum
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0


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
    PAYMENT_METHOD_CHOICES = [
        ('cod', '貨到付款'),
        ('test_payment', '測試付款'),
        ('linepay', 'LINE Pay'),
        ('ecpay', '綠界科技 ECPay'),
    ]
    CARRIER_CHOICES = [
        ('', '尚未指定'),
        ('hct', '新竹物流'),
        ('tcat', '黑貓宅急便'),
        ('kerry', '嘉里大榮'),
        ('seven_eleven', '7-ELEVEN 交貨便'),
        ('family_mart', '全家店到店'),
        ('other', '其他'),
    ]
    INVOICE_TYPE_CHOICES = [
        ('personal', '個人／載具'),
        ('company', '公司戶統編'),
        ('donate', '捐贈發票'),
    ]

    order_number = models.CharField(max_length=50, unique=True, verbose_name='訂單編號')
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, verbose_name='訂購會員')
    
    # 收件人資訊
    shipping_name = models.CharField(max_length=100, verbose_name='收件人姓名')
    shipping_phone = models.CharField(max_length=20, verbose_name='收件人電話')
    shipping_email = models.EmailField(verbose_name='收件人信箱')
    shipping_address = models.TextField(verbose_name='收件地址')
    shipping_notes = models.TextField(blank=True, verbose_name='配送備註')
    shipping_method = models.ForeignKey(
        'ShippingMethod', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='配送方式'
    )
    carrier = models.CharField(max_length=30, choices=CARRIER_CHOICES, blank=True, verbose_name='物流商')
    tracking_number = models.CharField(max_length=80, blank=True, verbose_name='物流單號')
    tracking_url = models.URLField(blank=True, verbose_name='物流查詢網址')

    invoice_type = models.CharField(
        max_length=20, choices=INVOICE_TYPE_CHOICES, default='personal', verbose_name='發票類型'
    )
    invoice_title = models.CharField(max_length=100, blank=True, verbose_name='發票抬頭')
    invoice_tax_id = models.CharField(max_length=20, blank=True, verbose_name='統一編號')
    invoice_carrier = models.CharField(max_length=64, blank=True, verbose_name='載具／捐贈碼')

    # 金額相關
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品小計')
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='運費')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='稅額')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='折扣金額')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='總金額')
    coupon_code = models.CharField(max_length=50, blank=True, verbose_name='優惠券代碼')
    inventory_held = models.BooleanField(default=False, verbose_name='是否仍預扣庫存')
    
    # 支付相關
    payment_method = models.CharField(
        max_length=50, choices=PAYMENT_METHOD_CHOICES, default='cod', verbose_name='支付方式'
    )
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
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

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

    def get_public_tracking_url(self):
        from plus.services.shipping import resolve_tracking_url
        return resolve_tracking_url(self)


class ShippingAddress(models.Model):
    """會員常用收件地址"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='shipping_addresses', verbose_name='會員')
    label = models.CharField(max_length=40, default='住家', verbose_name='名稱')
    name = models.CharField(max_length=100, verbose_name='收件人')
    phone = models.CharField(max_length=20, verbose_name='電話')
    address = models.TextField(verbose_name='地址')
    is_default = models.BooleanField(default=False, verbose_name='預設')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '收件地址'
        verbose_name_plural = '收件地址'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.user.username} {self.label}'

    def save(self, *args, **kwargs):
        if self.is_default:
            type(self).objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


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


class ReturnRequest(models.Model):
    """售後／退貨申請"""
    STATUS_CHOICES = [
        ('pending', '待審核'),
        ('approved', '已核准'),
        ('rejected', '已拒絕'),
        ('received', '已收回商品'),
        ('refunded', '已退款'),
        ('cancelled', '已取消'),
    ]
    REASON_CHOICES = [
        ('defective', '商品瑕疵'),
        ('wrong_item', '寄錯商品'),
        ('not_as_described', '與描述不符'),
        ('changed_mind', '不想買了'),
        ('other', '其他'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests', verbose_name='訂單')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='申請人')
    reason = models.CharField(max_length=30, choices=REASON_CHOICES, verbose_name='原因')
    detail = models.TextField(verbose_name='說明')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='狀態')
    admin_notes = models.TextField(blank=True, verbose_name='後台備註')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申請時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '退貨申請'
        verbose_name_plural = '退貨申請'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.order_number} {self.get_status_display()}'

