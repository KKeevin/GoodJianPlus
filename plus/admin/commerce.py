from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django import forms
from django.db import transaction
from django.core.exceptions import ValidationError
from plus.admin.seller import SellerOrderMixin
from plus.models import OrderEvent
from plus.services.order_workflow import validate_transition, transition_order
from plus.models import (
    CustomUser, UserProfile, Category, Brand, Product, ProductImage,
    ProductReview, Cart, CartItem, Order, OrderItem, Coupon,
    Wishlist, ShippingMethod, SiteSettings, Notification,
    Food, UserGoal, WeightLog, NutritionLog, DailyNutritionTarget,
    Article, ArticleCategory, ArticleImage, EmailVerificationToken,
    ReturnRequest,
    ShippingAddress,
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

    def has_add_permission(self, request, obj=None):
        return False


class ReturnRequestInline(admin.TabularInline):
    model = ReturnRequest
    extra = 0
    can_delete = False
    readonly_fields = ('user', 'reason', 'detail', 'status', 'created_at')
    fields = ('user', 'reason', 'status', 'detail', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    can_delete = False
    readonly_fields = ('status', 'actor', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

    def clean(self):
        data = super().clean()
        if self.instance.pk and 'status' in data:
            old = Order.objects.select_for_update().get(pk=self.instance.pk)
            new_payment = data.get('payment_status', old.payment_status)
            if new_payment != old.payment_status and (
                new_payment == 'refunded' or old.payment_status in ('paid', 'refunded')
            ):
                raise ValidationError('不可直接回退已付款狀態；退款請透過售後流程處理。')
            old.carrier = data.get('carrier', old.carrier)
            old.tracking_number = data.get('tracking_number', old.tracking_number)
            old.payment_status = data.get('payment_status', old.payment_status)
            validate_transition(old, data['status'])
        return data


@admin.register(Order)
class OrderAdmin(SellerOrderMixin, admin.ModelAdmin):
    form = OrderAdminForm
    change_list_template = 'admin/plus/order/change_list.html'
    inlines = [OrderItemInline, ReturnRequestInline, OrderEventInline]
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
    list_editable = ()
    list_select_related = ('user',)
    list_per_page = 25
    autocomplete_fields = ('user',)
    actions = ['mark_processing', 'mark_shipped', 'mark_delivered']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        from plus.services.fulfillment import stamp_fulfillment_times, notify_order_status_change
        old_status = None
        old_payment_status = None
        if change:
            old_obj = Order.objects.select_for_update().get(pk=obj.pk)
            old_status = old_obj.status
            old_payment_status = old_obj.payment_status
            stamp_fulfillment_times(obj)
        super().save_model(request, obj, form, change)
        if change:
            if old_status != obj.status:
                OrderEvent.objects.create(order=obj, actor=request.user, status=obj.status)
            if obj.status == 'cancelled' and old_status != 'cancelled':
                from plus.services.inventory import release_order_inventory, restore_coupon
                release_order_inventory(obj)
                restore_coupon(obj)
            transaction.on_commit(lambda: notify_order_status_change(obj, old_status, old_payment_status, inventory_handled=True))

    def _apply_status(self, request, queryset, status, require_tracking=False):
        ok = 0
        skipped = 0
        for order in queryset:
            try:
                _, changed = transition_order(order.pk, status, actor=request.user)
            except ValidationError:
                skipped += 1
                continue
            if changed:
                self.log_change(request, order, f'批次更新：{status}')
                ok += 1
        msg = f'已更新 {ok} 筆訂單'
        if skipped:
            msg += f'；{skipped} 筆付款、物流資料或狀態不符已跳過，請至出貨工作台確認'
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

    readonly_fields = ('order_number', 'user', 'created_at', 'updated_at', 'subtotal',
                       'shipping_fee', 'tax_amount', 'discount_amount', 'total_amount',
                       'coupon_code', 'payment_method', 'payment_transaction_id', 'shipped_at', 'delivered_at')

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
            OrderEvent.objects.create(order=order, status='refunded', actor=request.user)
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


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'label', 'name', 'phone', 'is_default', 'created_at')
    list_filter = ('is_default', 'created_at')
    search_fields = ('user__username', 'name', 'phone', 'address', 'label')

