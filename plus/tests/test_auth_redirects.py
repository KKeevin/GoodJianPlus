from django.test import TestCase
from django.urls import reverse


LOGIN_REQUIRED_GET_URLS = [
    'checkout',
    'order_list',
    'wishlist',
    'profile',
    'goal_management',
    'notification_list',
]


class AuthRedirectTests(TestCase):
    def test_login_required_pages_redirect_to_login(self):
        for name in LOGIN_REQUIRED_GET_URLS:
            with self.subTest(name=name):
                url = reverse(name)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    response.url.startswith('/login/'),
                    f'{name} redirected to {response.url}',
                )
