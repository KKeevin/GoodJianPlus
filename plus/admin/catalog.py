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

from plus.admin.filters import HasImageFilter, StockStatusFilter
from plus.admin.merchandising import MerchandisingMixin, ProductAdminForm, listing_issues

try:
    from django_summernote.admin import SummernoteModelAdmin
    SUMMERNOTE_AVAILABLE = True
except ImportError:
    SUMMERNOTE_AVAILABLE = False
    class SummernoteModelAdmin(admin.ModelAdmin):
        pass

class CategoryInline(admin.TabularInline):
    """子類別內聯編輯"""
    model = Category
    fk_name = 'parent'
    extra = 1
    fields = ('name', 'slug', 'is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    verbose_name = '子類別'
    verbose_name_plural = '子類別管理（點擊父類別名稱進入編輯頁面可管理子類別）'
    can_delete = True
    show_change_link = True
    classes = ('collapse',)  # 預設收合，點擊展開
    
    def get_queryset(self, request):
        """顯示所有子類別（包括未啟用的）"""
        qs = super().get_queryset(request)
        return qs.order_by('sort_order', 'name')
    
    def has_add_permission(self, request, obj=None):
        """只有父類別（沒有 parent）才能添加子類別"""
        if obj and obj.parent:
            return False
        return True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    inlines = [CategoryInline]
    list_display = ('display_name', 'parent_display', 'subcategory_count', 'is_active', 'sort_order', 'created_at')
    
    def get_inline_instances(self, request, obj=None):
        """只有父類別（沒有 parent）才顯示子類別內聯編輯"""
        inline_instances = []
        # 如果是新增或編輯父類別（沒有 parent），顯示子類別內聯
        if obj is None or obj.parent is None:
            for inline_class in self.inlines:
                inline = inline_class(self.model, self.admin_site)
                inline_instances.append(inline)
        return inline_instances
    list_filter = ('is_active', 'parent', 'created_at')
    search_fields = ('name', 'description', 'parent__name')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active', 'sort_order')
    ordering = ['parent__sort_order', 'parent__name', 'sort_order', 'name']
    list_select_related = ('parent',)
    
    def display_name(self, obj):
        """顯示分類名稱，子類別用縮進表示"""
        if obj.parent:
            return format_html(
                '&nbsp;&nbsp;&nbsp;&nbsp;*** <span style="color: #666;">{}</span>',
                obj.name
            )
        return format_html('<strong style="color: #4CAF50; font-size: 1.1em;">{}</strong>', obj.name)
    display_name.short_description = '分類名稱'
    display_name.admin_order_field = 'name'
    
    def parent_display(self, obj):
        """顯示父類別，父類別顯示為「頂層分類」"""
        if obj.parent:
            return format_html(
                '<span style="color: #4CAF50; font-weight: 600;">{}</span>',
                obj.parent.name
            )
        return format_html('<span style="color: #999; font-style: italic;">頂層分類</span>')
    parent_display.short_description = '父類別'
    parent_display.admin_order_field = 'parent__name'
    
    def subcategory_count(self, obj):
        """顯示子類別數量"""
        count = obj.children.filter(is_active=True).count()
        if count > 0:
            return format_html(
                '<span style="color: #4CAF50; font-weight: bold; background: #e8f5e9; padding: 2px 8px; border-radius: 12px;">{} 個子類別</span>',
                count
            )
        return format_html('<span style="color: #999;">-</span>')
    subcategory_count.short_description = '子類別數量'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """自定義 parent 字段的選擇框，只顯示頂層分類"""
        if db_field.name == 'parent':
            # 獲取所有頂層分類
            kwargs['queryset'] = Category.objects.filter(parent=None, is_active=True).order_by('sort_order', 'name')
            # 自定義選擇框的顯示
            from django import forms
            
            class CategoryChoiceField(forms.ModelChoiceField):
                def label_from_instance(self, obj):
                    # 顯示分類名稱和子類別數量
                    sub_count = obj.children.filter(is_active=True).count()
                    if sub_count > 0:
                        return format_html('{} <span style="color: #999; font-size: 0.9em;">({} 個子類別)</span>', obj.name, sub_count)
                    return obj.name
            
            kwargs['form_class'] = CategoryChoiceField
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        """優化查詢，預先載入父類別和子類別"""
        qs = super().get_queryset(request)
        return qs.select_related('parent').prefetch_related('children')


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active',)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image_preview', 'image', 'alt_text', 'is_primary', 'sort_order')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.pk and getattr(obj, 'image', None):
            return format_html(
                '<img src="{}" alt="" style="height:56px;width:56px;object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return '儲存後顯示預覽'
    image_preview.short_description = '預覽'


@admin.register(Product)
class ProductAdmin(MerchandisingMixin, SummernoteModelAdmin if SUMMERNOTE_AVAILABLE else admin.ModelAdmin):
    form = ProductAdminForm
    inlines = [ProductImageInline]
    list_display = (
        'thumbnail', 'name', 'sku', 'category', 'price', 'stock_badge',
        'status', 'is_featured', 'listing_readiness', 'view_on_site_link', 'updated_at',
    )
    list_filter = ('status', 'is_featured', StockStatusFilter, HasImageFilter, 'category', 'brand', 'created_at')
    search_fields = ('name', 'sku', 'description', 'short_description')
    prepopulated_fields = {'slug': ('name',)}
    list_display_links = ('name',)
    list_editable = ('price', 'status', 'is_featured')
    readonly_fields = ('created_at', 'updated_at', 'view_on_site_link', 'listing_readiness')
    list_select_related = ('category', 'brand')
    list_per_page = 25
    autocomplete_fields = ('brand',)
    if SUMMERNOTE_AVAILABLE:
        summernote_fields = ('description',)
    actions = [
        'adjust_stock',
        'generate_ai_short_description',
        'publish_products',
        'unpublish_products',
        'mark_featured',
        'unmark_featured',
        'duplicate_products',
    ]

    @admin.action(description='以 AI 產生商品短介紹（需 OPENAI_API_KEY）')
    def generate_ai_short_description(self, request, queryset):
        from django.contrib import messages as admin_messages
        from plus.services.ai_copy import generate_product_copy
        ok = 0
        last_error = ''
        for product in queryset:
            text, err = generate_product_copy(product)
            if err:
                last_error = err
                continue
            product.short_description = text[:500]
            product.save(update_fields=['short_description'])
            ok += 1
        if ok == 0 and last_error:
            self.message_user(request, last_error, level=admin_messages.ERROR)
        else:
            extra = f'（{last_error}）' if last_error else ''
            self.message_user(request, f'已為 {ok} 件商品產生短介紹{extra}')

    @admin.action(description='發佈選取的商品')
    def publish_products(self, request, queryset):
        from django.utils import timezone
        now = timezone.now()
        updated = 0
        skipped = 0
        for product in queryset:
            if product.price <= 0 or not product.category.is_active:
                skipped += 1
                continue
            product.status = 'published'
            if not product.published_at:
                product.published_at = now
            product.save(update_fields=['status', 'published_at'])
            updated += 1
        self.message_user(request, f'已發佈 {updated} 件商品' + (f'；{skipped} 件價格或分類不符已跳過' if skipped else ''))

    @admin.action(description='改回草稿（下架）')
    def unpublish_products(self, request, queryset):
        updated = queryset.update(status='draft')
        self.message_user(request, f'已下架 {updated} 件商品')

    @admin.action(description='設為推薦商品')
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'已將 {updated} 件設為推薦')

    @admin.action(description='取消推薦')
    def unmark_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'已取消 {updated} 件推薦')

    @admin.action(description='複製為草稿商品（含圖片）')
    def duplicate_products(self, request, queryset):
        import uuid
        count = 0
        for product in queryset:
            image_rows = list(product.images.all())
            product.pk = None
            product.id = None
            product.name = f'{product.name[:196]}（複製）'
            product.slug = f'{product.slug[:180]}-copy-{uuid.uuid4().hex[:12]}'
            product.sku = f'{product.sku[:36]}-C{uuid.uuid4().hex[:12].upper()}'
            product.stock_quantity = 0
            product.status = 'draft'
            product.is_featured = False
            product.published_at = None
            product.save()
            for image in image_rows:
                image.pk = None
                image.id = None
                image.product = product
                image.save()
            count += 1
        self.message_user(request, f'已複製 {count} 件草稿（庫存歸零），請確認 SKU、庫存與名稱後再發佈')

    @admin.display(description='上架檢查')
    def listing_readiness(self, obj):
        if not obj.pk:
            return '儲存草稿後顯示檢查結果'
        issues = listing_issues(obj)
        return '、'.join(issues) if issues else '✓ 資料完整'

    def thumbnail(self, obj):
        images = list(obj.images.all())
        image = next((item for item in images if item.is_primary), None) or (images[0] if images else None)
        if image and image.image:
            return format_html(
                '<img src="{}" alt="" style="height:48px;width:48px;object-fit:cover;border-radius:6px;" />',
                image.image.url,
            )
        return format_html('<span style="color:#999;">無圖</span>')
    thumbnail.short_description = '主圖'

    def stock_badge(self, obj):
        qty = obj.stock_quantity
        if qty <= 0:
            return format_html('<span style="color:#fff;background:#c0392b;padding:2px 8px;border-radius:10px;">缺貨</span>')
        if qty <= obj.min_stock_level:
            return format_html(
                '<span style="color:#7a4d00;background:#fff3cd;padding:2px 8px;border-radius:10px;">{}（低）</span>',
                qty,
            )
        return str(qty)
    stock_badge.short_description = '庫存'
    stock_badge.admin_order_field = 'stock_quantity'

    def view_on_site_link(self, obj):
        if not obj.pk:
            return '—'
        url = reverse('product_detail', kwargs={'product_id': obj.pk})
        if obj.status != 'published':
            url += '?preview=1'
        return format_html('<a href="{}" target="_blank" rel="noopener">前台預覽</a>', url)
    view_on_site_link.short_description = '前台'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """自定義 category 字段的選擇框，用縮進顯示層級關係，並分組顯示"""
        if db_field.name == 'category':
            from django import forms
            from django.forms.widgets import Select
            
            class CategoryGroupedSelect(Select):
                """自定義選擇框，將父類別和子類別分組顯示"""
                def __init__(self, attrs=None, choices=()):
                    super().__init__(attrs, choices)
                    self.choices = choices
                
                def render(self, name, value, attrs=None, renderer=None):
                    """自定義渲染方法，實現分組顯示"""
                    if value is None:
                        value = ''
                    final_attrs = self.build_attrs(attrs, {'name': name})
                    output = [format_html('<select{}>', forms.utils.flatatt(final_attrs))]
                    
                    # 添加空選項
                    output.append('<option value="">---------</option>')
                    
                    # 獲取所有父類別
                    parent_categories = list(Category.objects.filter(
                        parent=None, 
                        is_active=True
                    ).order_by('sort_order', 'name'))
                    
                    for idx, parent in enumerate(parent_categories):
                        # 添加父類別選項
                        option_value = str(parent.pk)
                        selected = str(parent.pk) == str(value)
                        selected_attr = ' selected' if selected else ''
                        
                        output.append(format_html(
                            '<option value="{}"{}><strong>{}</strong></option>',
                            option_value,
                            selected_attr,
                            parent.name
                        ))
                        
                        # 獲取該父類別的所有子類別
                        subcategories = Category.objects.filter(
                            parent=parent,
                            is_active=True
                        ).order_by('sort_order', 'name')
                        
                        # 添加子類別選項
                        for subcat in subcategories:
                            option_value = str(subcat.pk)
                            selected = str(subcat.pk) == str(value)
                            selected_attr = ' selected' if selected else ''
                            
                            output.append(format_html(
                                '<option value="{}"{}>&nbsp;&nbsp;&nbsp;&nbsp;*** {} &gt; {}</option>',
                                option_value,
                                selected_attr,
                                parent.name,
                                subcat.name
                            ))
                        
                        # 在每個父類別組後添加分隔線（最後一個除外）
                        if idx < len(parent_categories) - 1:
                            output.append('<option value="" disabled>────────</option>')
                    
                    output.append('</select>')
                    return mark_safe(''.join(output))
            
            class CategoryChoiceField(forms.ModelChoiceField):
                widget = CategoryGroupedSelect
                
                def __init__(self, *args, **kwargs):
                    # 獲取所有分類（用於驗證）
                    kwargs['queryset'] = Category.objects.filter(is_active=True).select_related('parent')
                    super().__init__(*args, **kwargs)
            
            kwargs['form_class'] = CategoryChoiceField
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        """保存商品時檢查價格和庫存變化，發送通知給收藏用戶"""
        from django.utils import timezone
        if obj.status == 'published' and not obj.published_at:
            obj.published_at = timezone.now()
        if change:  # 如果是更新
            try:
                old_obj = Product.objects.get(pk=obj.pk)
                old_price = old_obj.price
                old_stock = old_obj.stock_quantity
                
                # 檢查價格是否下降（降價通知）
                if old_price and obj.price < old_price:
                    discount = old_price - obj.price
                    discount_percent = round((discount / old_price) * 100, 1)
                    # 通知所有收藏此商品的用戶
                    wishlists = Wishlist.objects.filter(products=obj)
                    for wishlist in wishlists:
                        Notification.objects.create(
                            user=wishlist.user,
                            type='wishlist',
                            title=f'{obj.name} 降價了！',
                            message=f'您收藏的商品「{obj.name}」降價了！原價 NT${old_price}，現價 NT${obj.price}，省下 NT${discount}（{discount_percent}%）。'
                        )
                
                # 檢查庫存從0變為有庫存（補貨通知）
                if old_stock == 0 and obj.stock_quantity > 0:
                    # 通知所有收藏此商品的用戶
                    wishlists = Wishlist.objects.filter(products=obj)
                    for wishlist in wishlists:
                        Notification.objects.create(
                            user=wishlist.user,
                            type='stock',
                            title=f'{obj.name} 已補貨！',
                            message=f'您收藏的商品「{obj.name}」已補貨！目前庫存 {obj.stock_quantity} 件，快來購買吧！'
                        )
            except Product.DoesNotExist:
                pass
        
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'brand').prefetch_related('images')

    class Media:
        css = {
            'all': ('admin/css/admin-summernote-custom.css',)
        }
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('name', 'slug', 'category', 'brand', 'sku', 'status', 'listing_readiness', 'view_on_site_link')
        }),
        ('內容描述', {
            'fields': ('short_description', 'description')
        }),
        ('價格與庫存', {
            'fields': ('price', 'original_price', 'cost_price', 'stock_quantity', 'min_stock_level', 'max_stock_level')
        }),
        ('商品屬性', {
            'fields': ('weight', 'dimensions', 'color', 'size'),
            'classes': ('collapse',)
        }),
        ('營養成分', {
            'fields': ('calories_per_100g', 'protein_per_100g', 'carbs_per_100g', 'fat_per_100g'),
            'classes': ('collapse',)
        }),
        ('設定', {
            'fields': ('is_featured', 'is_digital', 'requires_shipping', 'allow_backorder')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('時間戳記', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'title', 'is_verified_purchase', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_verified_purchase', 'is_approved', 'created_at')
    search_fields = ('product__name', 'user__username', 'title', 'content')
    list_editable = ('is_approved',)
    readonly_fields = ('created_at', 'updated_at')
    actions = ['approve_reviews', 'hide_reviews']

    @admin.action(description='通過審核（前台顯示）')
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'已通過 {updated} 則評價')

    @admin.action(description='隱藏評價')
    def hide_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'已隱藏 {updated} 則評價')

