from django.db.models import Count, F, Sum
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse
from django.urls import reverse

from plus.models import CustomUser, NewsletterSubscriber, Order, OrderItem, Product, ProductReview, ReturnRequest


def get_admin_user_label(user):
    if user.is_superuser:
        role_label = '總管理者'
    elif user.groups.exists():
        role_label = user.groups.order_by('id').values_list('name', flat=True).first()
    elif user.is_staff:
        role_label = '管理員'
    else:
        return user.username
    return f'{user.username} ({role_label})'


@staff_member_required
def admin_user_label_view(request):
    return JsonResponse({'label': get_admin_user_label(request.user)})


@staff_member_required
def recent_actions_view(request):
    log_entries = LogEntry.objects.filter(user=request.user).select_related('content_type').order_by('-action_time')[:50]
    context = admin.site.each_context(request)
    context.update({
        'title': '最近的動作',
        'subtitle': '你的最近後台操作',
        'log_entries': log_entries,
    })
    return render(request, 'admin/recent_actions.html', context)


def get_ops_stats():
    low_stock = Product.objects.filter(
        stock_quantity__gt=0, stock_quantity__lte=F('min_stock_level')
    ).count()
    out_of_stock = Product.objects.filter(stock_quantity=0).count()
    pending_reviews = ProductReview.objects.filter(is_approved=False).count()
    return {
        'awaiting_payment': Order.objects.filter(payment_status='pending').exclude(status='cancelled').count(),
        'to_ship': Order.objects.filter(status__in=('confirmed', 'processing')).count(),
        'shipped': Order.objects.filter(status='shipped').count(),
        'pending_returns': ReturnRequest.objects.filter(status='pending').count(),
        'draft_products': Product.objects.filter(status='draft').count(),
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'pending_reviews': pending_reviews,
        'newsletter': NewsletterSubscriber.objects.filter(is_active=True).count(),
        'links': {
            'awaiting_payment': reverse('admin:plus_order_changelist') + '?payment_status__exact=pending',
            'to_ship': reverse('admin:plus_order_changelist') + '?status__exact=confirmed',
            'shipped': reverse('admin:plus_order_changelist') + '?status__exact=shipped',
            'pending_returns': reverse('admin:plus_returnrequest_changelist') + '?status__exact=pending',
            'draft_products': reverse('admin:plus_product_changelist') + '?status__exact=draft',
            'low_stock': reverse('admin:plus_product_changelist') + '?stock_status=low',
            'out_of_stock': reverse('admin:plus_product_changelist') + '?stock_status=out',
            'pending_reviews': reverse('admin:plus_productreview_changelist') + '?is_approved__exact=0',
            'newsletter': reverse('admin:plus_newslettersubscriber_changelist'),
        },
    }


def get_dashboard_data(days=7):
    from datetime import timedelta

    from django.utils import timezone

    today = timezone.localdate()
    days = days if days in (1, 7, 30) else 7
    range_start = today - timedelta(days=days - 1)
    revenue_orders = Order.objects.filter(
        payment_status='paid',
    ).exclude(status__in=('cancelled', 'refunded'))
    range_orders = Order.objects.filter(created_at__date__gte=range_start)
    valid_range_orders = range_orders.exclude(status__in=('cancelled', 'refunded'))
    range_revenue = revenue_orders.filter(created_at__date__gte=range_start).aggregate(
        total=Sum('total_amount'),
    )['total'] or 0
    range_order_count = valid_range_orders.count()
    top_products = list(
        OrderItem.objects.filter(
            order__payment_status='paid',
            order__created_at__date__gte=range_start,
        ).exclude(order__status__in=('cancelled', 'refunded')).values(
            'product_name',
        ).annotate(
            quantity=Sum('quantity'),
            revenue=Sum('subtotal'),
        ).order_by('-revenue')[:5]
    )
    max_product_revenue = max((item['revenue'] for item in top_products), default=0)
    for item in top_products:
        item['revenue_width'] = int(item['revenue'] / max_product_revenue * 100) if max_product_revenue else 0

    sales_labels = []
    sales_order_counts = []
    sales_revenue = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        daily_orders = Order.objects.filter(created_at__date=day)
        daily_revenue = revenue_orders.filter(created_at__date=day).aggregate(
            total=Sum('total_amount'),
        )['total'] or 0
        sales_labels.append(day.strftime('%m/%d'))
        sales_order_counts.append(daily_orders.count())
        sales_revenue.append(float(daily_revenue))

    status_labels = dict(Order.STATUS_CHOICES)
    status_data = range_orders.values('status').annotate(total=Count('id')).order_by('status')
    low_stock_products = list(Product.objects.filter(
        stock_quantity__lte=F('min_stock_level'),
    ).order_by('stock_quantity', 'name')[:6])

    return {
        'range_days': days,
        'range_label': {1: '今日', 7: '近 7 天', 30: '近 30 天'}[days],
        'today_orders': Order.objects.filter(created_at__date=today).count(),
        'range_orders': range_order_count,
        'range_revenue': range_revenue,
        'average_order_value': range_revenue / range_order_count if range_order_count else 0,
        'active_products': Product.objects.filter(status='published').count(),
        'member_count': CustomUser.objects.filter(is_active=True).count(),
        'recent_orders': Order.objects.select_related('user').order_by('-created_at')[:8],
        'top_products': top_products,
        'low_stock_products': low_stock_products,
        'sales_chart': {
            'labels': sales_labels,
            'orders': sales_order_counts,
            'revenue': sales_revenue,
        },
        'status_chart': {
            'labels': [status_labels[item['status']] for item in status_data],
            'values': [item['total'] for item in status_data],
        },
    }
