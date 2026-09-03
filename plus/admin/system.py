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
    NewsletterSubscriber,
)

try:
    from django_summernote.admin import SummernoteModelAdmin
    SUMMERNOTE_AVAILABLE = True
except ImportError:
    SUMMERNOTE_AVAILABLE = False
    class SummernoteModelAdmin(admin.ModelAdmin):
        pass

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'homepage_slogan', 'contact_email', 'contact_phone', 'free_shipping_threshold', 'is_maintenance_mode')
    fieldsets = (
        ('基本資訊', {
            'fields': ('site_name', 'site_description', 'homepage_slogan')
        }),
        ('聯絡資訊', {
            'fields': ('contact_email', 'contact_phone', 'contact_address')
        }),
        ('購物設定', {
            'fields': ('free_shipping_threshold', 'tax_rate', 'currency')
        }),
        ('系統設定', {
            'fields': ('is_maintenance_mode',)
        }),
    )
    
    def has_add_permission(self, request):
        # 限制只能有一筆設定記錄
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # 不允許刪除設定記錄
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from plus.context_processors import invalidate_site_settings_cache
        invalidate_site_settings_cache()


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    list_editable = ('is_read',)
    readonly_fields = ('created_at',)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('email',)
    list_editable = ('is_active',)
    actions = ['export_csv']

    @admin.action(description='匯出選取信箱為 CSV')
    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename=newsletter.csv'
        writer = csv.writer(response)
        writer.writerow(['email', 'is_active', 'created_at'])
        for row in queryset:
            writer.writerow([row.email, row.is_active, row.created_at.isoformat()])
        return response


admin.site.site_header = '好健健 GoodJian Plus 管理後台'
admin.site.site_title = '好健健管理系統'
admin.site.index_title = '歡迎使用好健健管理後台'
admin.site.index_template = 'admin/goodjian_index.html'

_orig_admin_index = admin.site.index


def _ops_admin_index(request, extra_context=None):
    extra_context = extra_context or {}
    from plus.admin.dashboard import get_ops_stats
    extra_context['ops_stats'] = get_ops_stats()
    return _orig_admin_index(request, extra_context=extra_context)


admin.site.index = _ops_admin_index

