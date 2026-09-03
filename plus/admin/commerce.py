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
    Article, ArticleCategory, ArticleImage, EmailVerificationToken,
    ReturnRequest,
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
    can_delete = False
    readonly_fields = ('product', 'product_name', 'product_sku', 'unit_price', 'quantity', 'subtotal')
    fields = ('product_name', 'product_sku', 'unit_price', 'quantity', 'subtotal')


class ReturnRequestInline(admin.TabularInline):
    model = ReturnRequest
    extra = 0
    can_delete = False
    readonly_fields = ('user', 'reason', 'detail', 'status', 'created_at')
    fields = ('user', 'reason', 'status', 'detail', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline, ReturnRequestInline]
    list_display = (
        'order_number', 'user', 'shipping_name', 'status', 'payment_status',
        'payment_method', 'tracking_number', 'total_amount', 'created_at',
    )
    list_display_links = ('order_number',)
    list_filter = ('status', 'payment_status', 'payment_method', 'carrier', 'created_at')
    search_fields = (
        'order_number', 'user__username', 'shipping_name', 'shipping_phone',
        'shipping_email', 'tracking_number', 'invoice_tax_id',
    )
    list_editable = ('status', 'payment_status')
    list_select_related = ('user',)
    list_per_page = 25
    autocomplete_fields = ('user',)
    actions = ['mark_processing', 'mark_shipped', 'mark_delivered']

    def save_model(self, request, obj, form, change):
        from plus.services.fulfillment import stamp_fulfillment_times, notify_order_status_change
        old_status = None
        old_payment_status = None
        if change:
            old_obj = Order.objects.get(pk=obj.pk)
            old_status = old_obj.status
            old_payment_status = old_obj.payment_status
            stamp_fulfillment_times(obj)
        super().save_model(request, obj, form, change)
        if change:
            notify_order_status_change(obj, old_status, old_payment_status)

    def _apply_status(self, request, queryset, status, require_tracking=False):
        from plus.services.fulfillment import stamp_fulfillment_times, notify_order_status_change
        ok = 0
        skipped = 0
        for order in queryset:
            if require_tracking and not order.tracking_number:
                skipped += 1
                continue
            old_status = order.status
            old_payment = order.payment_status
            order.status = status
            stamp_fulfillment_times(order)
            order.save()
            notify_order_status_change(order, old_status, old_payment)
            ok += 1
        msg = f'已更新 {ok} 筆訂單'
        if skipped:
            msg += f'；{skipped} 筆未填物流單號已跳過'
        self.message_user(request, msg)

    @admin.action(description='標示為處理中（備貨）')
    def mark_processing(self, request, queryset):
        self._apply_status(request, queryset, 'processing')

    @admin.action(description='標示為已出貨（需已填物流單號）')
    def mark_shipped(self, request, queryset):
        self._apply_status(request, queryset, 'shipped', require_tracking=True)

    @admin.action(description='標示為已送達')
    def mark_delivered(self, request, queryset):
        self._apply_status(request, queryset, 'delivered')

    readonly_fields = ('order_number', 'created_at', 'updated_at')

    fieldsets = (
        ('訂單基本資訊', {
            'fields': ('order_number', 'user', 'status', 'payment_status', 'payment_method', 'payment_transaction_id')
        }),
        ('收件人資訊', {
            'fields': ('shipping_name', 'shipping_phone', 'shipping_email', 'shipping_address', 'shipping_notes', 'shipping_method')
        }),
        ('出貨與物流', {
            'fields': ('carrier', 'tracking_number', 'tracking_url', 'shipped_at', 'delivered_at'),
            'description': '填寫物流單號並將狀態改為「已出貨」，會員訂單頁會顯示查詢連結。',
        }),
        ('發票', {
            'fields': ('invoice_type', 'invoice_title', 'invoice_tax_id', 'invoice_carrier'),
        }),
        ('金額明細', {
            'fields': ('subtotal', 'shipping_fee', 'tax_amount', 'discount_amount', 'total_amount', 'coupon_code')
        }),
        ('時間記錄', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('order__order_number', 'user__username', 'detail')
    list_editable = ('status',)
    list_select_related = ('order', 'user')
    autocomplete_fields = ('order', 'user')
    readonly_fields = ('created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = ReturnRequest.objects.get(pk=obj.pk).status
        super().save_model(request, obj, form, change)
        if not change or old_status == obj.status:
            return
        status_text = obj.get_status_display()
        Notification.objects.create(
            user=obj.user,
            type='order',
            title=f'退貨申請更新：{status_text}',
            message=f'訂單 {obj.order.order_number} 的退貨申請已更新為「{status_text}」。{obj.admin_notes}'.strip(),
        )
        if obj.status == 'refunded' and obj.order.payment_status != 'refunded':
            order = obj.order
            order.status = 'refunded'
            order.payment_status = 'refunded'
            order.save(update_fields=['status', 'payment_status'])
            from plus.services.inventory import release_order_inventory, restore_coupon
            release_order_inventory(order)
            restore_coupon(order)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'discount_type', 'discount_value', 'is_active', 'usage_limit', 'used_count', 'valid_from', 'valid_until')
    list_filter = ('discount_type', 'is_active', 'valid_from', 'valid_until', 'created_at')
    search_fields = ('name', 'code', 'description')
    list_editable = ('is_active',)
    readonly_fields = ('used_count', 'created_at')

    def save_model(self, request, obj, form, change):
        if not obj.code:
            import secrets
            obj.code = secrets.token_hex(4).upper()
        super().save_model(request, obj, form, change)


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

