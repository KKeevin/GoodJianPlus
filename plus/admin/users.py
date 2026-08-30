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

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = '會員資料'


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_verified', 'email_verified', 'is_verified', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_verified', 'phone_verified', 'email_verified', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    readonly_fields = ('is_verified',)  # is_verified 是自動計算的，設為只讀
    
    fieldsets = UserAdmin.fieldsets + (
        ('額外資訊', {'fields': ('phone', 'phone_verified', 'email_verified', 'birthday', 'address', 'avatar', 'is_verified')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('額外資訊', {'fields': ('phone', 'phone_verified', 'email_verified', 'birthday', 'address', 'avatar')}),
    )


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_type', 'token_short', 'is_used', 'is_valid_display', 'created_at', 'expires_at')
    list_filter = ('token_type', 'is_used', 'created_at', 'expires_at')
    search_fields = ('user__username', 'user__email', 'token')
    readonly_fields = ('token', 'created_at', 'expires_at')
    date_hierarchy = 'created_at'
    
    def token_short(self, obj):
        """顯示 Token 的前8個字元"""
        return f"{obj.token[:8]}..." if obj.token else "-"
    token_short.short_description = 'Token'
    
    def is_valid_display(self, obj):
        """顯示 Token 是否有效"""
        if obj.is_used:
            return "已使用"
        from django.utils import timezone
        if timezone.now() >= obj.expires_at:
            return "已過期"
        return "有效"
    is_valid_display.short_description = '狀態'

