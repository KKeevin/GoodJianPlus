from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from plus.models import Cart, CartItem, Category, Order, Product
from plus.payment.linepay import LinePayAPI
from plus.utils.http import safe_redirect_url


class SearchPageTests(TestCase):
    def test_search_returns_200(self):
        response = self.client.get(reverse('search'), {'q': 'yoga'})
        self.assertEqual(response.status_code, 200)


class LinePayAmountTests(TestCase):
    def test_twd_amount_is_yuan_not_cents(self):
        self.assertEqual(LinePayAPI.to_twd_amount(Decimal('199')), 199)
        self.assertEqual(LinePayAPI.to_twd_amount(Decimal('199.4')), 199)
        self.assertEqual(LinePayAPI.to_twd_amount(Decimal('199.5')), 200)


class SafeRedirectTests(TestCase):
    def test_rejects_external_host(self):
        request = self.client.get('/login/').wsgi_request
        url = safe_redirect_url(request, 'https://evil.example/phish', fallback='home')
        self.assertEqual(url, '/')

    def test_allows_local_path(self):
        request = self.client.get('/login/').wsgi_request
        url = safe_redirect_url(request, '/cart/', fallback='home')
        self.assertEqual(url, '/cart/')


class TestPaymentGuardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='payuser',
            email='payuser@example.com',
            password='Testpass123!',
        )

    @override_settings(DEBUG=False)
    def test_test_payment_rejected_when_debug_false(self):
        self.client.force_login(self.user)
        order = Order.objects.create(
            user=self.user,
            shipping_name='A',
            shipping_phone='0912345678',
            shipping_email='payuser@example.com',
            shipping_address='台北',
            subtotal=100,
            shipping_fee=0,
            tax_amount=0,
            discount_amount=0,
            total_amount=100,
            payment_status='pending',
            status='pending',
        )
        response = self.client.post(
            reverse('process_payment', kwargs={'order_id': order.id}),
            {'payment_method': 'test_payment'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'pending')


class InventoryConsistencyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='shopper',
            email='shopper@example.com',
            password='Testpass123!',
        )
        category = Category.objects.create(name='配件', slug='accessories')
        self.product = Product.objects.create(
            name='彈力帶',
            slug='resistance-band',
            category=category,
            sku='RB-001',
            description='測試商品',
            short_description='測試商品',
            price=Decimal('200'),
            stock_quantity=5,
            status='published',
        )
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

    def test_checkout_holds_stock_and_cancel_restores_it(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('checkout'), {
            'shipping_name': '測試',
            'shipping_phone': '0912345678',
            'shipping_email': 'shopper@example.com',
            'shipping_address': '台北市',
            'payment_method': 'cod',
        })
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        order = Order.objects.get(user=self.user)
        self.assertTrue(order.inventory_held)

        cancel = self.client.post(reverse('cancel_order', kwargs={'order_id': order.id}))
        self.assertEqual(cancel.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertFalse(order.inventory_held)
