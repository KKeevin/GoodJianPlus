from django.contrib import admin
from django.db.models import Count, F


class StockStatusFilter(admin.SimpleListFilter):
    title = '庫存狀態'
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return (
            ('out', '缺貨'),
            ('low', '低於警戒庫存'),
            ('ok', '庫存充足'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'out':
            return queryset.filter(stock_quantity=0)
        if self.value() == 'low':
            return queryset.filter(stock_quantity__gt=0, stock_quantity__lte=F('min_stock_level'))
        if self.value() == 'ok':
            return queryset.filter(stock_quantity__gt=F('min_stock_level'))
        return queryset


class HasImageFilter(admin.SimpleListFilter):
    title = '商品圖片'
    parameter_name = 'has_image'

    def lookups(self, request, model_admin):
        return (
            ('yes', '已有圖片'),
            ('no', '尚未上傳圖片'),
        )

    def queryset(self, request, queryset):
        qs = queryset.annotate(_img_count=Count('images'))
        if self.value() == 'yes':
            return qs.filter(_img_count__gt=0)
        if self.value() == 'no':
            return qs.filter(_img_count=0)
        return queryset
