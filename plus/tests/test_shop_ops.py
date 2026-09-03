from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from plus.models import NewsletterSubscriber, Order
from plus.payment.ecpay import ECPayAPI
from plus.services.shipping import resolve_tracking_url


class TrackingUrlTests(TestCase):
    def test_hct_public_query_url(self):
        User = get_user_model()
        user = User.objects.create_user(
            username='shipuser',
            email='ship@example.com',
            password='Testpass123!',
        )
        order = Order.objects.create(
            user=user,
            shipping_name='A',
            shipping_phone='0912345678',
            shipping_email='ship@example.com',
            shipping_address='台北',
            subtotal=100,
            shipping_fee=0,
            tax_amount=0,
            discount_amount=0,
            total_amount=100,
            carrier='hct',
            tracking_number='1234567890',
        )
        url = resolve_tracking_url(order)
        self.assertIn('1234567890', url)
        self.assertIn('hct.com.tw', url)

    def test_manual_tracking_url_wins(self):
        User = get_user_model()
        user = User.objects.create_user(
            username='shipuser2',
            email='ship2@example.com',
            password='Testpass123!',
        )
        order = Order.objects.create(
            user=user,
            shipping_name='A',
            shipping_phone='0912345678',
            shipping_email='ship2@example.com',
            shipping_address='台北',
            subtotal=100,
            shipping_fee=0,
            tax_amount=0,
            discount_amount=0,
            total_amount=100,
            carrier='hct',
            tracking_number='123',
            tracking_url='https://example.com/t/abc',
        )
        self.assertEqual(resolve_tracking_url(order), 'https://example.com/t/abc')


class ECPayMacTests(TestCase):
    @override_settings(ECPAY_HASH_KEY='pwFHCqoQZGmho4w6', ECPAY_HASH_IV='EkRm7iFT261dpevs')
    def test_check_mac_is_stable(self):
        api = ECPayAPI()
        params = {
            'MerchantID': '3002607',
            'MerchantTradeNo': 'GJTEST0001',
            'TotalAmount': '100',
        }
        mac = api.generate_check_mac_value(params)
        self.assertEqual(len(mac), 64)
        self.assertTrue(api.verify_check_mac_value({**params, 'CheckMacValue': mac}))


class NewsletterPersistTests(TestCase):
    def test_subscribe_saves_email(self):
        response = self.client.post(reverse('newsletter_subscribe'), {'email': 'news@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertTrue(NewsletterSubscriber.objects.filter(email='news@example.com', is_active=True).exists())


class CsrfOriginsTests(TestCase):
    def test_csrf_origins_configured(self):
        from django.conf import settings
        self.assertIsInstance(settings.CSRF_TRUSTED_ORIGINS, list)
        self.assertGreaterEqual(len(settings.CSRF_TRUSTED_ORIGINS), 1)
