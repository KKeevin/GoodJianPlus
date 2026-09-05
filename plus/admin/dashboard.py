from django.db.models import Count, F, Sum
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.urls import reverse

from plus.models import CustomUser, NewsletterSubscriber, Order, OrderItem, Product, ProductReview, ReturnRequest


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


def get_dashboard_data():
    from datetime import timedelta

    from django.utils import timezone

    today = timezone.localdate()
    month_start = today.replace(day=1)
    revenue_orders = Order.objects.filter(
        payment_status='paid',
    ).exclude(status__in=('cancelled', 'refunded'))
    month_revenue = revenue_orders.filter(created_at__date__gte=month_start).aggregate(
        total=Sum('total_amount'),
    )['total'] or 0
    top_products = list(
        OrderItem.objects.filter(
            order__payment_status='paid',
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
    sales_orders = []
    sales_revenue = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        daily_orders = Order.objects.filter(created_at__date=day)
        daily_revenue = revenue_orders.filter(created_at__date=day).aggregate(
            total=Sum('total_amount'),
        )['total'] or 0
        sales_labels.append(day.strftime('%m/%d'))
        sales_orders.append(daily_orders.count())
        sales_revenue.append(float(daily_revenue))

    status_labels = dict(Order.STATUS_CHOICES)
    status_data = Order.objects.values('status').annotate(total=Count('id')).order_by('status')

    return {
        'today_orders': Order.objects.filter(created_at__date=today).count(),
        'month_revenue': month_revenue,
        'active_products': Product.objects.filter(status='published').count(),
        'member_count': CustomUser.objects.filter(is_active=True).count(),
        'recent_orders': Order.objects.select_related('user').order_by('-created_at')[:8],
        'top_products': top_products,
        'sales_chart': {
            'labels': sales_labels,
            'orders': sales_orders,
            'revenue': sales_revenue,
        },
        'status_chart': {
            'labels': [status_labels[item['status']] for item in status_data],
            'values': [item['total'] for item in status_data],
        },
    }
