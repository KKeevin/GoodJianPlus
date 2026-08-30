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

@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'calories', 'protein', 'carbs', 'fat', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name',)
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['category', 'name']


@admin.register(UserGoal)
class UserGoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'goal_type', 'get_current_weight', 'target_weight', 'get_height', 'age', 'activity_level', 'tdee', 'updated_at')
    list_filter = ('goal_type', 'activity_level', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('created_at', 'updated_at', 'get_current_weight', 'get_height')
    fieldsets = (
        ('基本資訊', {
            'fields': ('user', 'goal_type', 'activity_level')
        }),
        ('身體數據', {
            'fields': ('get_current_weight', 'get_height', 'target_weight', 'age', 'gender'),
            'description': '注意：目前體重和身高直接從會員資料（UserProfile）讀取，請在會員資料中編輯。'
        }),
        ('身體組成目標', {
            'fields': (
                ('current_muscle_percentage', 'target_muscle_percentage'),
                ('current_fat_percentage', 'target_fat_percentage'),
                ('current_bone_percentage', 'target_bone_percentage'),
                ('current_water_percentage', 'target_water_percentage'),
            )
        }),
        ('營養目標', {
            'fields': ('bmr', 'tdee', 'target_calories', 'target_protein', 'target_carbs', 'target_fat')
        }),
        ('時間記錄', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_current_weight(self, obj):
        """顯示目前體重（從 UserProfile 讀取）"""
        return f"{obj.current_weight} kg" if obj.current_weight else "未設定"
    get_current_weight.short_description = '目前體重'
    get_current_weight.admin_order_field = 'user__profile__weight'
    
    def get_height(self, obj):
        """顯示身高（從 UserProfile 讀取）"""
        return f"{obj.height} cm" if obj.height else "未設定"
    get_height.short_description = '身高'
    get_height.admin_order_field = 'user__profile__height'


@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'weight', 'body_fat', 'muscle_mass', 'muscle_percentage', 'fat_percentage', 'recorded_at')
    list_filter = ('recorded_at',)
    search_fields = ('user__username', 'notes')
    readonly_fields = ('recorded_at',)
    ordering = ['-recorded_at']
    fieldsets = (
        ('基本資訊', {
            'fields': ('user', 'weight', 'recorded_at')
        }),
        ('身體組成', {
            'fields': ('body_fat', 'muscle_mass', 'muscle_percentage', 'fat_percentage', 'bone_percentage', 'water_percentage')
        }),
        ('備註', {
            'fields': ('notes',)
        }),
    )


@admin.register(NutritionLog)
class NutritionLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'food', 'quantity', 'meal_type', 'logged_at')
    list_filter = ('meal_type', 'logged_at')
    search_fields = ('user__username', 'food__name', 'notes')
    readonly_fields = ('logged_at',)
    ordering = ['-logged_at']


@admin.register(DailyNutritionTarget)
class DailyNutritionTargetAdmin(admin.ModelAdmin):
    list_display = ('user', 'target_date', 'target_calories', 'target_protein', 'target_carbs', 'target_fat', 'weight', 'created_at')
    list_filter = ('target_date', 'goal_type', 'activity_level', 'created_at')
    search_fields = ('user__username',)
    ordering = ['-target_date', '-created_at']
    date_hierarchy = 'target_date'

