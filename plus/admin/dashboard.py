from django.db.models import F
from django.urls import reverse

from plus.models import NewsletterSubscriber, Order, Product, ProductReview, ReturnRequest


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
