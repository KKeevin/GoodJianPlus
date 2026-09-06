from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sqlite3

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings, RequestFactory, SimpleTestCase
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_summernote.models import Attachment
from plus.models import Article, ArticleCategory, Coupon, Order, OrderEvent
from plus.models.commerce import PaymentReceipt
from plus.payment.ecpay import ECPayAPI
from plus.services.payments import settle_payment, fail_payment
from plus.services.inventory import consume_coupon, restore_coupon
from plus.utils.ratelimit import consume_limit
from plus.utils.request import get_client_ip
from plus.services.backups import create_backup, verify_backup
from plus.templatetags.rich_content import clean_article_html


def upload(fmt='PNG', size=(2600, 1300), mode='RGBA'):
    buffer = BytesIO()
    Image.new(mode, size, (20, 40, 60, 128) if mode == 'RGBA' else (20, 40, 60)).save(buffer, format=fmt)
    return SimpleUploadedFile('中文 original.' + fmt.lower(), buffer.getvalue())


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', ADMIN_REQUIRE_OTP=False)
class SecurityRegressions(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='security-buyer', password='A-long-password-1!')

    def order(self, **kwargs):
        return Order.objects.create(user=self.user, subtotal=100, total_amount=100,
            payment_method='ecpay', inventory_held=True, **kwargs)

    def test_user_creation_and_later_saves_do_not_access_relations(self):
        self.user.first_name = 'Test'
        self.user.save()
        self.assertIsNotNone(self.user.pk)

    def test_upload_cover_and_editor_attachment_and_no_reconversion(self):
        category = ArticleCategory.objects.create(name='Test', slug='test')
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            for fmt, mode in [('PNG', 'RGBA'), ('JPEG', 'RGB'), ('WEBP', 'RGBA')]:
                with self.subTest(fmt=fmt):
                    article = Article.objects.create(title='Image', slug=fmt.lower(), category=category, cover_image=upload(fmt, mode=mode))
                    self.assertRegex(article.cover_image.name, r'^articles/covers/img_[a-f0-9]{32}\.webp$')
                    with Image.open(article.cover_image.path) as image:
                        self.assertEqual(image.size, (2048, 1024))
                        self.assertEqual(image.format, 'WEBP')
                    before = article.cover_image.name
                    article.title = 'Changed'
                    article.save()
                    self.assertEqual(before, article.cover_image.name)
            attachment = Attachment.objects.create(file=upload())
            self.assertTrue(attachment.file.name.endswith('.webp'))
            with Image.open(attachment.file.path) as image:
                self.assertEqual(image.size, (2048, 1024))

    def test_palette_transparency_and_exif_orientation(self):
        category = ArticleCategory.objects.create(name='Test', slug='test')
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            image = Image.new('P', (10, 10), 0)
            stream = BytesIO()
            image.save(stream, format='PNG', transparency=0)
            article = Article.objects.create(title='P', slug='p', category=category,
                cover_image=SimpleUploadedFile('palette.png', stream.getvalue()))
            with Image.open(article.cover_image.path) as result:
                self.assertEqual(result.getpixel((0, 0))[3], 0)
            stream = BytesIO()
            image = Image.new('RGB', (20, 10))
            exif = image.getexif()
            exif[274] = 6
            image.save(stream, format='JPEG', exif=exif)
            article.cover_image = SimpleUploadedFile('rotated.jpg', stream.getvalue())
            article.save()
            with Image.open(article.cover_image.path) as result:
                self.assertEqual(result.size, (10, 20))

    def test_duplicate_success_preserves_shipped_status(self):
        order = self.order()
        settle_payment(order.pk, 'ecpay', 't1', Decimal('100'))
        Order.objects.filter(pk=order.pk).update(status='shipped')
        settle_payment(order.pk, 'ecpay', 't1', Decimal('100'))
        order.refresh_from_db()
        self.assertEqual(order.status, 'shipped')
        self.assertEqual(PaymentReceipt.objects.count(), 1)
        self.assertEqual(OrderEvent.objects.filter(order=order, status='confirmed').count(), 1)

    def test_late_success_is_reviewed_without_reviving_order(self):
        order = self.order(status='cancelled')
        self.assertFalse(settle_payment(order.pk, 'ecpay', 'late', Decimal('100')))
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertTrue(PaymentReceipt.objects.get().needs_review)

    def test_transaction_cannot_pay_another_order(self):
        one, two = self.order(), self.order()
        settle_payment(one.pk, 'ecpay', 'same', Decimal('100'))
        with self.assertRaises(ValidationError):
            settle_payment(two.pk, 'ecpay', 'same', Decimal('100'))
        two.refresh_from_db()
        self.assertEqual(two.payment_status, 'pending')

    def test_failed_callback_does_not_undo_paid_order(self):
        order = self.order()
        settle_payment(order.pk, 'ecpay', 'paid', Decimal('100'))
        fail_payment(order.pk)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')
        self.assertTrue(order.inventory_held)

    def test_coupon_is_consumed_and_restored_once(self):
        from django.utils import timezone
        coupon = Coupon.objects.create(code='ONCE', name='Once', discount_type='fixed', discount_value=1,
            used_count=2, valid_from=timezone.now(), valid_until=timezone.now())
        order = self.order(coupon_code=coupon.code)
        consume_coupon(order)
        consume_coupon(order)
        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 3)
        restore_coupon(order)
        restore_coupon(order)
        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 2)

    @override_settings(ECPAY_MERCHANT_ID='3002607', ECPAY_HASH_KEY='test-key', ECPAY_HASH_IV='test-iv')
    def test_ecpay_callback_identity_amount_signature_and_simulation(self):
        order = self.order()
        api = ECPayAPI()
        payload = dict(MerchantID='3002607', MerchantTradeNo=order.order_number, TradeAmt='100',
                       TradeNo='trade1', SimulatePaid='0', RtnCode='1', CustomField1='')
        for field, value in [('MerchantID', 'wrong'), ('TradeAmt', '1'), ('SimulatePaid', '1')]:
            with self.subTest(field=field):
                bad = {**payload, field: value}
                bad['CheckMacValue'] = api.generate_check_mac_value(bad)
                self.assertEqual(self.client.post(reverse('ecpay_return'), bad).status_code, 400)
        payload['CheckMacValue'] = api.generate_check_mac_value(payload)
        self.assertEqual(self.client.post(reverse('ecpay_return'), payload).content, b'1|OK')
        self.assertEqual(self.client.post(reverse('ecpay_return'), payload).content, b'1|OK')
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')

    def test_browser_result_cannot_mutate_order(self):
        order = self.order()
        self.client.post(reverse('ecpay_result', args=[order.pk]), {'RtnCode': '1'})
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'pending')

    def test_inline_webp_becomes_article_thumbnail(self):
        category = ArticleCategory.objects.create(name='Test', slug='test')
        article = Article.objects.create(title='Inline', slug='inline', category=category,
            status='published', content='<img src="/media/editor/photo.webp">')
        self.assertEqual(article.thumbnail_url, '/media/editor/photo.webp')
        self.assertContains(self.client.get(reverse('articles_list')), '/media/editor/photo.webp')

    def test_unprivileged_editor_upload_is_rejected(self):
        from plus.image_processing import can_upload_editor_image
        request = RequestFactory().get('/')
        request.user = self.user
        self.assertFalse(can_upload_editor_image(request))
        self.user.is_staff = True
        self.assertFalse(can_upload_editor_image(request))

    def test_invalid_attachment_is_not_stored(self):
        from plus.image_processing import ImageUploadError
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            with self.assertRaises(ImageUploadError):
                Attachment.objects.create(file=SimpleUploadedFile('fake.png', b'<script>bad</script>'))
            self.assertEqual(list(Path(root).rglob('*')), [])

    def test_refund_requires_evidence_and_received_goods_for_restock(self):
        from plus.models import ReturnRequest
        from plus.admin.commerce import ReturnRequestForm
        order = self.order(payment_status='paid')
        rma = ReturnRequest.objects.create(order=order, user=self.user, reason='defective', detail='Test', status='approved')
        data = dict(order=order.pk, user=self.user.pk, reason='defective', detail='Test', status='refunded')
        self.assertFalse(ReturnRequestForm(data=data, instance=rma).is_valid())
        data.update(refund_reference='provider-refund-123', restock_items=True)
        rma.refresh_from_db()
        self.assertFalse(ReturnRequestForm(data=data, instance=rma).is_valid())
        data['restock_items'] = False
        rma.refresh_from_db()
        self.assertTrue(ReturnRequestForm(data=data, instance=rma).is_valid())

    def test_stock_cannot_be_oversold(self):
        from types import SimpleNamespace
        from plus.models import Product, Category
        from plus.services.inventory import hold_stock_for_cart_items, InsufficientStock
        category = Category.objects.create(name='stock', slug='stock')
        product = Product.objects.create(name='Only one', slug='one', category=category, sku='one', price=100, stock_quantity=1)
        item = SimpleNamespace(product_id=product.pk, product=product, quantity=1)
        hold_stock_for_cart_items([item])
        with self.assertRaises(InsufficientStock):
            hold_stock_for_cart_items([item])
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 0)

    @patch('plus.payment.linepay.LinePayAPI.confirm_payment', return_value={'success': False})
    def test_linepay_timeout_keeps_reservation(self, confirm):
        order = self.order(payment_transaction_id='123')
        order.payment_method = 'linepay'
        order.save()
        self.client.force_login(self.user)
        self.client.get(reverse('linepay_confirm', args=[order.pk]), {'transactionId': '123'})
        order.refresh_from_db()
        self.assertTrue(order.inventory_held)
        self.assertEqual(order.payment_status, 'pending')

    def test_rate_limit_survives_cache_clear(self):
        from django.core.cache import cache
        self.assertTrue(consume_limit('test', 1, 60))
        cache.clear()
        self.assertFalse(consume_limit('test', 1, 60))

    @override_settings(LINE_PAY_CHANNEL_ID='test', LINE_PAY_CHANNEL_SECRET='secret')
    @patch('plus.payment.linepay.LinePayAPI.request_payment', return_value={'success': True, 'transactionId': '123', 'paymentUrl': 'https://example.com/pay'})
    def test_repeated_linepay_request_only_calls_provider_once(self, request_payment):
        order = self.order()
        order.payment_method = 'linepay'
        order.save()
        self.client.force_login(self.user)
        url = reverse('process_payment', args=[order.pk])
        self.assertTrue(self.client.post(url, {'payment_method': 'linepay'}).json()['success'])
        self.assertEqual(self.client.post(url, {'payment_method': 'linepay'}).status_code, 409)
        request_payment.assert_called_once()

    @override_settings(ECPAY_HASH_KEY='key', ECPAY_HASH_IV='iv')
    def test_invalid_unicode_signature_is_rejected(self):
        self.assertFalse(ECPayAPI().verify_check_mac_value({'CheckMacValue': '無效簽章'}))

    @override_settings(ADMIN_REQUIRE_OTP=True)
    def test_admin_mfa_enrollment_and_replay(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get('/admin/'), '/admin-mfa/', fetch_redirect_response=False)
        mfa_page = self.client.get('/admin-mfa/')
        self.assertEqual(mfa_page.status_code, 200)
        self.assertEqual(mfa_page.headers['Referrer-Policy'], 'same-origin')
        device = TOTPDevice.objects.get(user=self.user)
        token = f'{totp(device.bin_key):06d}'
        response = self.client.post('/admin-mfa/', {'password': 'A-long-password-1!', 'token': token})
        self.assertRedirects(response, '/admin/', fetch_redirect_response=False)
        self.assertEqual(self.client.get('/admin/').status_code, 200)
        device.refresh_from_db()
        self.assertTrue(device.confirmed)
        self.assertFalse(device.verify_token(token))


class PureSecurityTests(SimpleTestCase):
    @override_settings(LINE_PAY_CHANNEL_ID='test', LINE_PAY_CHANNEL_SECRET='secret')
    @patch('plus.payment.linepay.requests.post')
    def test_linepay_signature_matches_sent_json(self, post):
        import json
        from plus.payment.linepay import LinePayAPI
        post.return_value.json.return_value = {'returnCode': '0000', 'info': {'transactionId': '123', 'orderId': '1'}}
        api = LinePayAPI()
        api.confirm_payment('123', Decimal('100'))
        sent = post.call_args.kwargs
        body = sent['data'].decode('utf-8')
        self.assertEqual(body, json.dumps(json.loads(body), separators=(',', ':')))
        self.assertEqual(sent['headers']['X-LINE-Authorization'], api._generate_signature(
            '/v3/payments/123/confirm', json.loads(body), sent['headers']['X-LINE-Authorization-Nonce']))

    @override_settings(TRUSTED_PROXY_NETWORKS=['127.0.0.1/32'])
    def test_forwarded_ip_is_only_trusted_from_proxy(self):
        factory = RequestFactory()
        request = factory.get('/', REMOTE_ADDR='198.51.100.2', HTTP_X_FORWARDED_FOR='fake')
        self.assertEqual(get_client_ip(request), '198.51.100.2')
        request = factory.get('/', REMOTE_ADDR='127.0.0.1', HTTP_X_FORWARDED_FOR='fake, 198.51.100.2')
        self.assertEqual(get_client_ip(request), '198.51.100.2')

    def test_article_html_strips_executable_content(self):
        cleaned = clean_article_html('<img src="/media/p.webp" onerror="alert(1)"><script>alert(1)</script><a href="javascript:alert(1)">x</a>')
        self.assertIn('/media/p.webp', cleaned)
        for forbidden in ('onerror', '<script', 'javascript:'):
            self.assertNotIn(forbidden, cleaned)

    def test_backup_restore_verification_and_no_overwrite(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            database = root / 'source.sqlite3'
            with sqlite3.connect(database) as conn:
                conn.execute('CREATE TABLE example (name TEXT)')
                conn.execute("INSERT INTO example VALUES ('kept')")
            conn.close()
            media = root / 'media'
            media.mkdir()
            (media / 'image.webp').write_bytes(b'test')
            archive = root / 'backup.zip'
            self.assertEqual(create_backup(database, media, archive), 2)
            self.assertEqual(verify_backup(archive), 2)
            with self.assertRaises(FileExistsError):
                create_backup(database, media, archive)
