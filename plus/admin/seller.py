"""Permission-checked fulfillment workspace, export and packing documents."""
import csv
from collections import defaultdict

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from plus.models import Order
from plus.services.order_workflow import ready_to_ship, transition_order


def csv_cell(value):
    value = str(value if value is not None else '')
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')) else value


class SellerOrderMixin:
    def get_urls(self):
        return [path('fulfillment/', self.admin_site.admin_view(self.fulfillment_view),
                     name='plus_order_fulfillment')] + super().get_urls()

    def fulfillment_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        base = self.get_queryset(request).prefetch_related('items').order_by('created_at', 'pk')
        queues = {
            'ready': ('待出貨', ready_to_ship(base)),
            'unpaid': ('待付款', base.filter(payment_status__in=('pending', 'failed')).exclude(
                payment_method='cod').filter(status__in=('pending', 'confirmed', 'processing'))),
            'shipped': ('運送中', base.filter(status='shipped')),
            'done': ('已完成', base.filter(status__in=('delivered', 'completed'))),
            'closed': ('取消／退款', base.filter(status__in=('cancelled', 'refunded'))),
            'all': ('全部訂單', base),
        }
        queue = request.GET.get('queue', 'ready')
        if queue not in queues:
            queue = 'ready'
        orders = queues[queue][1]
        query = request.GET.get('q', '').strip()[:100]
        if query:
            orders = orders.filter(Q(order_number__icontains=query) | Q(shipping_name__icontains=query)
                                   | Q(tracking_number__icontains=query) | Q(shipping_phone__icontains=query))
        errors = []
        selected = request.POST.getlist('orders') if request.method == 'POST' else []
        if request.method == 'POST':
            if not selected or len(selected) > 100 or any(not pk.isdecimal() for pk in selected):
                errors.append('請勾選 1 至 100 筆訂單。')
            else:
                chosen = list(orders.filter(pk__in=selected))
                if len(chosen) != len(set(selected)):
                    errors.append('部分訂單已離開目前清單，請重新整理後再試。')
                else:
                    action = request.POST.get('operation')
                    if action == 'print':
                        return self.packing_response(request, chosen)
                    if action == 'export':
                        return self.export_response(chosen)
                    if not self.has_change_permission(request):
                        raise PermissionDenied
                    if action not in ('processing', 'shipped'):
                        errors.append('請選擇有效的操作。')
                    else:
                        # The entire selection succeeds or rolls back, including history.
                        try:
                            with transaction.atomic():
                                for row in chosen:
                                    try:
                                        _, changed = transition_order(
                                            row.pk, action, actor=request.user,
                                            carrier=request.POST.get(f'carrier_{row.pk}', row.carrier),
                                            tracking_number=request.POST.get(f'tracking_{row.pk}', row.tracking_number),
                                        )
                                        if changed:
                                            self.log_change(request, row, f'出貨工作台：{dict(Order.STATUS_CHOICES)[action]}')
                                    except ValidationError as exc:
                                        raise ValidationError(f'{row.order_number}：{"；".join(exc.messages)}') from exc
                        except ValidationError as exc:
                            errors.extend(exc.messages)
                        else:
                            self.message_user(request, f'已處理 {len(chosen)} 筆訂單。', messages.SUCCESS)
                            return redirect(request.get_full_path())
        page = Paginator(orders, 25).get_page(request.GET.get('page'))
        for order in page.object_list:
            order.selected = str(order.pk) in selected
            order.input_carrier = request.POST.get(f'carrier_{order.pk}', order.carrier)
            order.input_tracking = request.POST.get(f'tracking_{order.pk}', order.tracking_number)
        context = {
            **self.admin_site.each_context(request), 'title': '出貨工作台',
            'opts': self.model._meta, 'page_obj': page, 'queue': queue, 'query': query,
            'queues': [{'key': key, 'label': label, 'count': qs.count()} for key, (label, qs) in queues.items()],
            'carriers': Order.CARRIER_CHOICES, 'errors': errors,
            'can_change': self.has_change_permission(request),
        }
        return TemplateResponse(request, 'admin/plus/order/fulfillment.html', context)

    def export_response(self, orders):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        response['Cache-Control'] = 'no-store'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['訂單編號', '訂單狀態', '付款方式', '付款狀態', '收件人', '電話', '地址', '物流商', '物流單號', '總金額', '商品', '配送備註'])
        for order in orders:
            writer.writerow([csv_cell(value) for value in [
                order.order_number, order.get_status_display(), order.get_payment_method_display(),
                order.get_payment_status_display(), order.shipping_name, order.shipping_phone,
                order.shipping_address, order.get_carrier_display(), order.tracking_number,
                order.total_amount, ' / '.join(f'{item.product_sku} × {item.quantity}' for item in order.items.all()),
                order.shipping_notes,
            ]])
        return response

    def packing_response(self, request, orders):
        picking = defaultdict(lambda: {'quantity': 0, 'name': '', 'sku': ''})
        for order in orders:
            for item in order.items.all():
                row = picking[(item.product_id, item.product_sku)]
                row.update(name=item.product_name, sku=item.product_sku)
                row['quantity'] += item.quantity
        response = TemplateResponse(request, 'admin/plus/order/packing.html', {
            'orders': orders, 'picking': sorted(picking.values(), key=lambda row: row['sku']),
        })
        response['Cache-Control'] = 'no-store'
        return response

    @staticmethod
    def fulfillment_url():
        return reverse('admin:plus_order_fulfillment')
