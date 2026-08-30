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

class ArticleImageInline(admin.TabularInline):
    """文章圖片內聯編輯"""
    model = ArticleImage
    extra = 1
    fields = ('image', 'alt_text', 'caption', 'sort_order')
    verbose_name = '相關圖片'
    verbose_name_plural = '相關圖片'


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'sort_order', 'article_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active', 'sort_order')
    ordering = ['sort_order', 'name']

    def article_count(self, obj):
        """顯示該分類下的文章數量"""
        count = obj.article_set.filter(status='published').count()
        return count
    article_count.short_description = '已發佈文章數'


@admin.register(Article)
class ArticleAdmin(SummernoteModelAdmin if SUMMERNOTE_AVAILABLE else admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'is_featured', 'view_count', 'display_author', 'published_at', 'created_at')
    list_filter = ('status', 'is_featured', 'category', 'published_at', 'created_at')
    search_fields = ('title', 'content', 'excerpt', 'author_name')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('status', 'is_featured')
    ordering = ['-published_at', '-created_at']
    inlines = [ArticleImageInline]
    
    # 如果使用 Summernote，指定哪些欄位使用富文本編輯器
    if SUMMERNOTE_AVAILABLE:
        summernote_fields = ('content',)
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('title', 'slug', 'category', 'cover_image', 'excerpt')
        }),
        ('文章內容', {
            'fields': ('content',),
            'classes': ('wide',),
            'description': '使用富文本編輯器編輯文章內容，支援格式化、插入圖片等功能' if SUMMERNOTE_AVAILABLE else '支援 HTML 標籤，可以直接輸入 HTML 代碼'
        }),
        ('狀態設定', {
            'fields': ('status', 'is_featured', 'published_at')
        }),
        ('作者資訊', {
            'fields': ('author', 'author_name')
        }),
        ('SEO設定', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('統計資訊', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('view_count', 'created_at', 'updated_at')
    
    def display_author(self, obj):
        """顯示作者"""
        return obj.display_author
    display_author.short_description = '作者'
    
    class Media:
        # 添加自定義 CSS 來調整富文本編輯器的寬度和修復下拉選單
        css = {
            'all': ('admin/css/admin-summernote-custom.css',)
        }
        js = ('admin/js/summernote-dropdown-fix.js',)


@admin.register(ArticleImage)
class ArticleImageAdmin(admin.ModelAdmin):
    list_display = ('article', 'image_preview', 'alt_text', 'caption', 'sort_order', 'created_at')
    list_filter = ('article', 'created_at')
    search_fields = ('article__title', 'alt_text', 'caption')
    list_editable = ('sort_order',)
    ordering = ['article', 'sort_order', '-created_at']
    
    def image_preview(self, obj):
        """顯示圖片預覽"""
        if obj.image:
            return format_html('<img src="{}" style="max-width: 100px; max-height: 100px;" />', obj.image.url)
        return '-'
    image_preview.short_description = '圖片預覽'

