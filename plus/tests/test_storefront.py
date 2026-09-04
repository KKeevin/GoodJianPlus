from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from plus.models import Brand, Cart, CartItem, Category, Product
from plus.services.body_metrics import calculate_bmi, bmi_category


class GuestCartTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='配件', slug='accessories-guest')
        self.product = Product.objects.create(
            name='瑜珈墊',
            slug='yoga-mat-guest',
            category=category,
            sku='YG-GUEST',
            description='測試',
            short_description='測試',
            price=Decimal('399'),
            stock_quantity=10,
            status='published',
        )

    def test_guest_can_add_to_cart(self):
        response = self.client.post(reverse('api_add_to_cart'), {
            'product_id': self.product.id,
            'quantity': 2,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(Cart.objects.filter(user__isnull=True).count(), 1)
        cart = Cart.objects.get(user__isnull=True)
        self.assertEqual(cart.items.get(product=self.product).quantity, 2)

    def test_guest_cart_merges_on_login(self):
        self.client.post(reverse('api_add_to_cart'), {
            'product_id': self.product.id,
            'quantity': 1,
        })
        User = get_user_model()
        User.objects.create_user(
            username='guestmerge',
            email='guestmerge@example.com',
            password='Testpass123!',
        )
        login = self.client.post(reverse('login'), {
            'username': 'guestmerge',
            'password': 'Testpass123!',
        })
        self.assertEqual(login.status_code, 302)
        user = User.objects.get(username='guestmerge')
        cart = Cart.objects.get(user=user)
        self.assertEqual(cart.items.get(product=self.product).quantity, 1)
        self.assertFalse(Cart.objects.filter(user__isnull=True).exists())

    def test_guest_quick_view_api(self):
        response = self.client.get(reverse('quick_view_product', kwargs={'product_id': self.product.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['product']['stock_quantity'], 10)
        self.assertEqual(data['product']['cart_quantity'], 0)
        self.assertEqual(data['product']['available_quantity'], 10)

    def test_guest_quick_view_limit_reached(self):
        # 訪客加入全部庫存 (10) 到購物車
        self.client.post(reverse('api_add_to_cart'), {
            'product_id': self.product.id,
            'quantity': 10,
        })
        response = self.client.get(reverse('quick_view_product', kwargs={'product_id': self.product.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['product']['stock_quantity'], 10)
        self.assertEqual(data['product']['cart_quantity'], 10)
        self.assertEqual(data['product']['available_quantity'], 0)


class ProductFilterTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='補給', slug='protein-filter')
        brand = Brand.objects.create(name='測試牌', slug='test-brand')
        Product.objects.create(
            name='有貨蛋白',
            slug='in-stock-protein',
            category=category,
            brand=brand,
            sku='PR-IN',
            description='測試',
            short_description='測試',
            price=Decimal('500'),
            stock_quantity=3,
            status='published',
        )
        Product.objects.create(
            name='缺貨蛋白',
            slug='out-stock-protein',
            category=category,
            sku='PR-OUT',
            description='測試',
            short_description='測試',
            price=Decimal('800'),
            stock_quantity=0,
            status='published',
        )

    def test_in_stock_filter_hides_empty(self):
        response = self.client.get(reverse('products'), {'in_stock': '1'})
        self.assertEqual(response.status_code, 200)
        names = [p.name for p in response.context['products']]
        self.assertIn('有貨蛋白', names)
        self.assertNotIn('缺貨蛋白', names)

    def test_brand_filter(self):
        response = self.client.get(reverse('products'), {'brand': 'test-brand'})
        names = [p.name for p in response.context['products']]
        self.assertEqual(names, ['有貨蛋白'])


class BmiCalculatorTests(TestCase):
    def test_calculator_url_goes_to_goal_management(self):
        response = self.client.get(reverse('bmi_calculator'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/goals/', response.url)

    def test_formulas(self):
        self.assertEqual(calculate_bmi(65, 170), Decimal('22.5'))
        self.assertEqual(bmi_category(Decimal('22.5'))[1], '健康')
