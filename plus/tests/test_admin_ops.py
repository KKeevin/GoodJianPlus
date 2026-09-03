from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from plus.models import Category, Product


class MerchandiserAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username='opsadmin',
            email='opsadmin@example.com',
            password='Testpass123!',
        )
        self.category = Category.objects.create(name='蛋白粉', slug='protein')
        self.product = Product.objects.create(
            name='乳清蛋白',
            slug='whey',
            category=self.category,
            sku='WHEY-001',
            description='測試商品',
            short_description='短介',
            price=990,
            stock_quantity=2,
            min_stock_level=5,
            status='draft',
        )
        self.client.force_login(self.admin)

    def test_product_changelist_shows_low_stock(self):
        response = self.client.get(reverse('admin:plus_product_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WHEY-001')

    def test_stock_filter_low(self):
        response = self.client.get(reverse('admin:plus_product_changelist'), {'stock_status': 'low'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WHEY-001')

    def test_publish_action_sets_published_at(self):
        response = self.client.post(reverse('admin:plus_product_changelist'), {
            'action': 'publish_products',
            '_selected_action': [str(self.product.pk)],
            'index': 0,
        })
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'published')
        self.assertIsNotNone(self.product.published_at)

    def test_ops_dashboard_on_admin_index(self):
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '營運總覽')
        self.assertContains(response, '待出貨')
