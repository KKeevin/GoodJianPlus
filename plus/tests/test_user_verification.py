from django.contrib.auth import get_user_model
from django.test import TestCase


class UserVerificationTests(TestCase):
    def test_partial_email_verification_save_updates_account_flag(self):
        user = get_user_model().objects.create_user(
            username='verification-user',
            email='verification@example.com',
            password='Testpass123!',
        )

        user.email_verified = True
        user.save(update_fields=['email_verified'])
        user.refresh_from_db()

        self.assertTrue(user.email_verified)
        self.assertTrue(user.is_verified)
        self.assertTrue(user.has_verified_contact)

    def test_contact_property_does_not_depend_on_stale_cached_flag(self):
        user = get_user_model().objects.create_user(
            username='stale-verification-user',
            email='stale@example.com',
            password='Testpass123!',
        )
        get_user_model().objects.filter(pk=user.pk).update(
            email_verified=True, is_verified=False
        )
        user.refresh_from_db()

        self.assertTrue(user.has_verified_contact)
