from django.test import TestCase
from django.urls import reverse


PUBLIC_GET_URLS = [
    'home',
    'products',
    'login',
    'register',
    'articles_list',
    'privacy_policy',
    'terms_of_service',
    'delete_account',
    'shipping_info',
    'return_policy',
    'faq',
    'contact_us',
    'search',
    'bmi_calculator',
]


class PublicPageTests(TestCase):
    def test_public_pages_return_200(self):
        for name in PUBLIC_GET_URLS:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_admin_login_page_returns_200(self):
        response = self.client.get('/admin/login/', follow=False)
        self.assertIn(response.status_code, (200, 302))
