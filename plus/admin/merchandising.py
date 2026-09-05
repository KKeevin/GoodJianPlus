from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.template.response import TemplateResponse

from plus.models import Product


def listing_issues(product):
    issues = []
    if product.price is None or product.price <= 0:
        issues.append('售價須大於 0')
    if not product.short_description.strip():
        issues.append('缺少短介紹')
    if not product.description.strip():
        issues.append('缺少商品說明')
    if not product.images.exists():
        issues.append('尚未上傳圖片')
    if not product.category.is_active:
        issues.append('分類未啟用')
    return issues


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

    def clean(self):
        data = super().clean()
        for field in ('price', 'original_price', 'cost_price'):
            if data.get(field) is not None and data[field] < 0:
                self.add_error(field, '價格不可小於 0。')
        if data.get('status') == 'published' and data.get('price') == 0:
            self.add_error('price', '上架商品的售價須大於 0。')
        if data.get('original_price') and data.get('price') is not None and data['original_price'] < data['price']:
            self.add_error('original_price', '原價不可低於售價；沒有折扣時請留空。')
        return data


class StockAdjustmentForm(forms.Form):
    delta = forms.IntegerField(label='每件商品調整數量', min_value=-100000, max_value=100000,
                               help_text='補貨填正數；耗損填負數。會加減目前庫存，不會覆蓋顧客剛下單扣除的庫存。')
    reason = forms.CharField(label='調整原因', min_length=3, max_length=200,
                             widget=forms.Textarea(attrs={'rows': 3}), help_text='例如：採購入庫 PO-2026-001、盤點耗損。')

    def clean_delta(self):
        value = self.cleaned_data['delta']
        if value == 0:
            raise forms.ValidationError('調整數量不可為 0。')
        return value


class MerchandisingMixin:
    def adjust_stock(self, request, queryset):
        if not self.has_change_permission(request):
            raise PermissionDenied
        form = StockAdjustmentForm(request.POST if 'apply_stock' in request.POST else None)
        if 'apply_stock' in request.POST and form.is_valid():
            try:
                with transaction.atomic():
                    rows = list(queryset.select_for_update().order_by('pk'))
                    for product in rows:
                        before = product.stock_quantity
                        after = before + form.cleaned_data['delta']
                        if not 0 <= after <= 2147483647:
                            raise ValidationError(f'{product.sku}：調整後庫存超出有效範圍，本次全部不變更。')
                        product.stock_quantity = after
                        # Keep existing restock notifications for wishlisted products.
                        self.save_model(request, product, form, True)
                        self.log_change(request, product, f'庫存 {before} → {after}；原因：{form.cleaned_data["reason"]}')
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                self.message_user(request, f'已調整 {len(rows)} 件商品庫存，原因與數量已記錄於操作歷史。')
                return None
        return TemplateResponse(request, 'admin/plus/product/adjust_stock.html', {
            **self.admin_site.each_context(request), 'title': '批次庫存調整',
            'opts': self.model._meta, 'products': queryset, 'form': form,
            'select_across': request.POST.get('select_across', '0'),
        })

    adjust_stock.short_description = '補貨／耗損：批次調整庫存（記錄原因）'
