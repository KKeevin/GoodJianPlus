import csv
import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.admin.models import LogEntry
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from plus.models import Brand, Category, Coupon, Order, OrderEvent, OrderItem, Product, ProductImage
from plus.services.order_workflow import transition_order


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SellerCenterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('seller', 'seller@example.com', 'testpass123')
        cls.buyer = get_user_model().objects.create_user('buyer', 'buyer@example.com', 'testpass123')
        cls.category = Category.objects.create(name='用品', slug='supplies')
        cls.product = Product.objects.create(name='訓練墊', slug='training-mat', category=cls.category,
            sku='MAT', description='訓練使用', short_description='防滑設計', price=500, stock_quantity=20, status='published')

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse('admin:plus_order_fulfillment')

    def order(self, **kwargs):
        defaults = dict(user=self.buyer, shipping_name='小林', shipping_phone='0912345678',
            shipping_email='buyer@example.com', shipping_address='台北市', subtotal=500, total_amount=500,
            payment_method='cod', status='confirmed', inventory_held=True)
        defaults.update(kwargs)
        order = Order.objects.create(**defaults)
        OrderItem.objects.create(order=order, product=self.product, product_name=self.product.name,
            product_sku='MAT', unit_price=500, quantity=1, subtotal=500)
        return order

    def ship_data(self, *orders):
        data = {'orders': [str(o.pk) for o in orders], 'operation': 'shipped'}
        for order in orders:
            data.update({f'carrier_{order.pk}': 'hct', f'tracking_{order.pk}': f'TRACK{order.pk}'})
        return data

    def test_batch_shipping_records_history_and_notifies_once(self):
        order = self.order()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, self.ship_data(order))
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, 'shipped')
        self.assertIsNotNone(order.shipped_at)
        self.assertEqual(order.events.get().actor, self.admin)
        self.assertEqual(LogEntry.objects.filter(object_id=str(order.pk)).count(), 1)
        self.assertEqual(transition_order(order.pk, 'shipped')[1], False)
        self.assertEqual(order.events.count(), 1)

    def test_bad_row_rolls_back_entire_batch_and_preserves_input(self):
        first, second = self.order(), self.order()
        data = self.ship_data(first, second)
        data[f'tracking_{second.pk}'] = ''
        response = self.client.post(self.url, data)
        self.assertContains(response, '本次未變更任何訂單')
        self.assertContains(response, f'TRACK{first.pk}')
        self.assertEqual(Order.objects.filter(status='shipped').count(), 0)
        self.assertEqual(OrderEvent.objects.count(), 0)
        self.assertEqual(LogEntry.objects.count(), 0)

    def test_unpaid_online_and_closed_orders_cannot_ship(self):
        for kwargs in ({'payment_method': 'ecpay'}, {'status': 'cancelled'}, {'status': 'refunded'}, {'status': 'completed'}):
            order = self.order(**kwargs)
            with self.assertRaises(ValidationError):
                transition_order(order.pk, 'shipped', carrier='hct', tracking_number='123')

    def test_ready_queue_includes_pending_cod_and_paid_online(self):
        cod = self.order(status='pending')
        paid = self.order(payment_method='ecpay', payment_status='paid')
        unpaid = self.order(payment_method='ecpay')
        response = self.client.get(self.url)
        self.assertContains(response, cod.order_number)
        self.assertContains(response, paid.order_number)
        self.assertNotContains(response, unpaid.order_number)

    def test_permission_denies_staff_without_order_permission(self):
        staff = get_user_model().objects.create_user('staff', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_view_only_can_print_but_cannot_ship(self):
        staff = get_user_model().objects.create_user('viewer', is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename='view_order'))
        self.client.force_login(staff)
        order = self.order()
        self.assertEqual(self.client.post(self.url, self.ship_data(order)).status_code, 403)
        response = self.client.post(self.url, {'orders': [order.pk], 'operation': 'print'})
        self.assertContains(response, '彙總揀貨單')
        self.assertContains(response, '貨到付款應收')
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

    def test_export_handles_formula_and_phone(self):
        order = self.order(shipping_name='=HYPERLINK("evil")', shipping_phone='+886912345678')
        response = self.client.post(self.url, {'orders': [order.pk], 'operation': 'export'})
        rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
        self.assertTrue(rows[1][4].startswith("'="))
        self.assertTrue(rows[1][5].startswith("'+"))
        self.assertIn('no-store', response['Cache-Control'])

    def test_cancel_releases_stock_and_coupon_once(self):
        from django.utils import timezone
        coupon = Coupon.objects.create(code='ONE', name='ONE', discount_type='fixed', discount_value=10,
            used_count=2, valid_from=timezone.now(), valid_until=timezone.now())
        order = self.order(coupon_code=coupon.code)
        transition_order(order.pk, 'cancelled', actor=self.buyer)
        transition_order(order.pk, 'cancelled', actor=self.buyer)
        self.product.refresh_from_db()
        coupon.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 21)
        self.assertEqual(coupon.used_count, 1)

    def test_stock_adjustment_is_atomic_and_audited(self):
        url = reverse('admin:plus_product_changelist')
        data = {'action': 'adjust_stock', '_selected_action': [self.product.pk],
                'apply_stock': '1', 'delta': '-21', 'reason': '盤點耗損'}
        response = self.client.post(url, data)
        self.assertContains(response, '本次全部不變更')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 20)
        data['delta'] = '5'
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 25)
        self.assertTrue(LogEntry.objects.filter(change_message__contains='盤點耗損').exists())

    def test_duplicate_long_sku_gets_new_sku_and_zero_stock(self):
        self.product.sku = 'A' * 50
        self.product.save()
        self.client.post(reverse('admin:plus_product_changelist'), {
            'action': 'duplicate_products', '_selected_action': [self.product.pk]})
        clone = Product.objects.exclude(pk=self.product.pk).get()
        self.assertNotEqual(clone.sku, self.product.sku)
        self.assertLessEqual(len(clone.sku), 50)
        self.assertEqual(clone.stock_quantity, 0)
        self.assertEqual(clone.status, 'draft')

    def test_draft_preview_requires_permission(self):
        self.product.status = 'draft'
        self.product.save()
        url = reverse('product_detail', args=[self.product.pk]) + '?preview=1'
        self.assertContains(self.client.get(url), '管理員商品預覽')
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_primary_image_is_first(self):
        ProductImage.objects.create(product=self.product, image='products/secondary.png', sort_order=0)
        primary = ProductImage.objects.create(product=self.product, image='products/primary.png', is_primary=True, sort_order=10)
        self.assertEqual(self.product.images.first(), primary)

    def test_order_search_never_exposes_other_buyers(self):
        mine = self.order()
        other = self.order(user=self.admin)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('order_list'), {'status': 'preparing', 'q': '訓練墊'})
        self.assertContains(response, mine.order_number)
        self.assertNotContains(response, other.order_number)

    def test_cod_order_does_not_offer_online_payment(self):
        order = self.order(status='pending')
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('order_list'))
        self.assertContains(response, '貨到付款')
        self.assertNotContains(response, reverse('payment', args=[order.pk]))

    def test_product_pagination_preserves_all_filters(self):
        brand = Brand.objects.create(name='品牌', slug='brand')
        self.product.brand = brand
        self.product.save()
        for n in range(13):
            Product.objects.create(name=f'訓練墊{n}', slug=f'mat-{n}', category=self.category, brand=brand,
                sku=f'MAT-{n}', price=500, stock_quantity=5, status='published')
        response = self.client.get(reverse('products'), {'brand': 'brand', 'min_price': '100',
            'max_price': '900', 'in_stock': '1', 'q': '訓練墊', 'sort': 'price-low'})
        self.assertContains(response, 'brand=brand&amp;min_price=100&amp;max_price=900&amp;in_stock=1')
        self.assertContains(response, 'page=2')

    def test_nonfinite_prices_do_not_crash_catalog(self):
        for value in ('NaN', 'Infinity', '-1', '1e999999'):
            self.assertEqual(self.client.get(reverse('products'), {'min_price': value}).status_code, 200)
