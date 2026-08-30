from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django import forms
from plus.models import (
    CustomUser, UserProfile, Category, Brand, Product, ProductImage,
    ProductReview, Cart, CartItem, Order, OrderItem, Coupon,
    Wishlist, ShippingMethod, SiteSettings, Notification,
    Food, UserGoal, WeightLog, NutritionLog, DailyNutritionTarget,
    Article, ArticleCategory, ArticleImage, EmailVerificationToken
)

try:
    from django_summernote.admin import SummernoteModelAdmin
    SUMMERNOTE_AVAILABLE = True
except ImportError:
    SUMMERNOTE_AVAILABLE = False
    class SummernoteModelAdmin(admin.ModelAdmin):
        pass

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('added_at',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    inlines = [CartItemInline]
    list_display = ('__str__', 'user', 'total_items', 'total_price', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'session_key')
    readonly_fields = ('created_at', 'updated_at')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('subtotal',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ('order_number', 'user', 'shipping_name', 'status', 'payment_status', 'total_amount', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'user__username', 'shipping_name', 'shipping_phone', 'shipping_email')
    list_editable = ('status', 'payment_status')
    
    def save_model(self, request, obj, form, change):
        """保存訂單時檢查狀態變化，發送通知給用戶"""
        if change:  # 如果是更新
            try:
                old_obj = Order.objects.get(pk=obj.pk)
                old_status = old_obj.status
                old_payment_status = old_obj.payment_status
                
                # 訂單狀態變更通知
                if old_status != obj.status:
                    status_messages = {
                        'confirmed': '您的訂單已確認，正在準備出貨。',
                        'processing': '您的訂單正在處理中。',
                        'shipped': '您的訂單已出貨，請注意查收。',
                        'delivered': '您的訂單已送達，感謝您的購買！',
                        'cancelled': '您的訂單已取消。',
                        'refunded': '您的訂單已退款。',
                    }
                    message = status_messages.get(obj.status, f'您的訂單狀態已變更為：{obj.get_status_display()}。')
                    Notification.objects.create(
                        user=obj.user,
                        type='order',
                        title=f'訂單 {obj.order_number} 狀態更新',
                        message=message
                    )
                
                # 支付狀態變更通知
                if old_payment_status != obj.payment_status and obj.payment_status == 'paid':
                    Notification.objects.create(
                        user=obj.user,
                        type='order',
                        title='付款成功',
                        message=f'您的訂單 {obj.order_number} 已成功付款，交易編號：{obj.payment_transaction_id or "N/A"}'
                    )
            except Order.DoesNotExist:
                pass
        
        super().save_model(request, obj, form, change)
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    # date_hierarchy = 'created_at'  # 暫時移除以避免時區問題
    
    fieldsets = (
        ('訂單基本資訊', {
            'fields': ('order_number', 'user', 'status', 'payment_status')
        }),
        ('收件人資訊', {
            'fields': ('shipping_name', 'shipping_phone', 'shipping_email', 'shipping_address', 'shipping_notes')
        }),
        ('金額明細', {
            'fields': ('subtotal', 'shipping_fee', 'tax_amount', 'discount_amount', 'total_amount')
        }),
        ('時間記錄', {
            'fields': ('created_at', 'updated_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'discount_type', 'discount_value', 'is_active', 'usage_limit', 'used_count', 'valid_from', 'valid_until')
    list_filter = ('discount_type', 'is_active', 'valid_from', 'valid_until', 'created_at')
    search_fields = ('name', 'code', 'description')
    list_editable = ('is_active',)
    readonly_fields = ('used_count', 'created_at')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username',)
    filter_horizontal = ('products',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'estimated_days', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    list_editable = ('price', 'estimated_days', 'is_active', 'sort_order')
    ordering = ['sort_order', 'name']

