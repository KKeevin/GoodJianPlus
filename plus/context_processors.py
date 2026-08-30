from django.conf import settings as django_settings
from .models import SiteSettings, Cart


def site_settings(request):
    """將網站設定添加到所有模板的context中"""
    context = {}

    try:
        site_config = SiteSettings.objects.first()
        if site_config:
            context.update({
                'site_settings': site_config,
                'site_name': site_config.site_name,
                'site_description': site_config.site_description,
                'homepage_slogan': site_config.homepage_slogan,
                'contact_email': site_config.contact_email,
                'contact_phone': site_config.contact_phone,
                'contact_address': site_config.contact_address,
                'free_shipping_threshold': site_config.free_shipping_threshold,
                'currency': site_config.currency,
            })
        else:
            context.update({
                'site_settings': None,
                'site_name': '好健健 GoodJian Plus',
                'site_description': '專業健身用品與營養餐食專家，讓健康生活變得簡單親民',
                'homepage_slogan': '健康生活觸手可及',
                'contact_email': 'service@goodjianplus.com',
                'contact_phone': '0800-892010',
                'contact_address': '台北市信義區健康路123號',
                'free_shipping_threshold': 1000,
                'currency': 'TWD',
            })
    except Exception:
        context.update({
            'site_settings': None,
            'site_name': '好健健 GoodJian Plus',
            'site_description': '專業健身用品與營養餐食專家，讓健康生活變得簡單親民',
            'homepage_slogan': '健康生活觸手可及',
            'contact_email': 'service@goodjianplus.com',
            'contact_phone': '0800-892010',
            'contact_address': '台北市信義區健康路123號',
            'free_shipping_threshold': 1000,
            'currency': 'TWD',
        })

    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                context['cart_count'] = cart.total_items
            else:
                context['cart_count'] = 0
        else:
            context['cart_count'] = 0
    except Exception:
        context['cart_count'] = 0

    context['static_version'] = getattr(django_settings, 'STATIC_VERSION', '1.0.2')

    return context
