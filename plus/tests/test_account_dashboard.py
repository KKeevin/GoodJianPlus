from decimal import Decimal
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from plus.models import ShippingAddress, UserGoal, UserProfile, WeightLog


class AccountDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='account-owner', email='account@example.com', password='Testpass123!',
            first_name='測試會員', phone='0912345678', address='原聯絡地址',
            birthday=date(1995, 6, 15),
        )
        self.client.force_login(self.user)

    def test_sections_render_and_legacy_entries_redirect(self):
        for tab in ['info', 'fitness', 'addresses', 'orders', 'security']:
            response = self.client.get(reverse('profile'), {'tab': tab})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['active_tab'], tab)
            self.assertContains(response, 'aria-controls="addresses-tab"')
        self.assertRedirects(self.client.get(reverse('profile_complete')), reverse('profile') + '?tab=fitness')
        self.assertRedirects(self.client.get(reverse('address_book')), reverse('profile') + '?tab=addresses')
        self.assertEqual(self.client.get(reverse('profile'), {'tab': 'unknown'}).context['active_tab'], 'info')

    def test_fitness_saves_without_clearing_account_and_only_logs_changes(self):
        data = {'fitness-gender': 'M', 'fitness-height': '170.25', 'fitness-weight': '65.55',
                'fitness-fitness_goal': '提升體能', 'fitness-dietary_restrictions': '素食',
                'fitness-emergency_contact': '家人', 'fitness-emergency_phone': '0987654321'}
        self.assertRedirects(self.client.post(reverse('profile_complete'), data), reverse('profile') + '?tab=fitness')
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.weight, Decimal('65.55'))
        self.assertEqual(profile.emergency_contact, '家人')
        self.assertEqual(UserGoal.objects.get(user=self.user).height, Decimal('170.25'))
        goal = UserGoal.objects.get(user=self.user)
        self.assertEqual(goal.gender, 'male')
        self.assertGreater(goal.bmr, 0)
        self.assertGreater(goal.target_calories, 0)
        self.assertEqual(WeightLog.objects.filter(user=self.user).count(), 1)
        self.client.post(reverse('profile_complete'), data)
        self.assertEqual(WeightLog.objects.filter(user=self.user).count(), 1)
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.phone, self.user.address), ('測試會員', '0912345678', '原聯絡地址'))

    def test_invalid_fitness_keeps_values_and_does_not_save(self):
        UserProfile.objects.create(user=self.user, weight=Decimal('65'))
        for value in ['NaN', 'Infinity', 'oops', '-1', '301']:
            response = self.client.post(reverse('profile_complete'), {
                'fitness-gender': 'M', 'fitness-weight': value, 'fitness-fitness_goal': '保留的目標',
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['active_tab'], 'fitness')
            self.assertTrue(response.context['fitness_form'].errors)
            self.assertContains(response, '保留的目標')
            self.assertEqual(UserProfile.objects.get(user=self.user).weight, Decimal('65'))
        self.assertFalse(WeightLog.objects.filter(user=self.user).exists())

    def test_fitness_save_rolls_back_if_goal_sync_fails(self):
        UserProfile.objects.create(user=self.user, weight=Decimal('65'))
        with self.assertLogs('plus.views.profile', level='ERROR'):
            with patch('plus.views.profile.UserGoal.save', side_effect=RuntimeError('test failure')):
                response = self.client.post(reverse('profile_complete'), {'gender': 'M', 'height': '170', 'weight': '66'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['fitness_form'].non_field_errors())
        self.assertEqual(UserProfile.objects.get(user=self.user).weight, Decimal('65'))
        self.assertFalse(WeightLog.objects.filter(user=self.user).exists())

    def test_address_create_edit_default_and_delete(self):
        data = {'shipping-label': '住家', 'shipping-name': '收件人',
                'shipping-phone': '0912345678', 'shipping-address': '台北市測試路 1 號'}
        self.assertRedirects(self.client.post(reverse('address_book'), data), reverse('profile') + '?tab=addresses')
        first = ShippingAddress.objects.get(user=self.user)
        self.assertTrue(first.is_default)
        second = ShippingAddress.objects.create(user=self.user, label='公司', name='同一收件人', phone='02-12345678', address='公司地址')
        response = self.client.get(reverse('address_book'), {'edit': second.pk})
        self.assertEqual(response.context['editing_address'], second)
        self.assertContains(response, '公司地址')
        data.update({'address_id': second.pk, 'shipping-label': '新公司', 'shipping-is_default': 'on'})
        self.client.post(reverse('address_book'), data)
        second.refresh_from_db(); first.refresh_from_db()
        self.assertEqual(second.label, '新公司')
        self.assertTrue(second.is_default)
        self.assertFalse(first.is_default)
        self.assertEqual(self.user.shipping_addresses.count(), 2)
        self.client.post(reverse('address_delete', args=[second.pk]))
        first.refresh_from_db()
        self.assertTrue(first.is_default)

    def test_invalid_address_preserves_input(self):
        response = self.client.post(reverse('address_book'), {
            'shipping-label': '公司', 'shipping-name': '收件人', 'shipping-address': '保留地址',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_tab'], 'addresses')
        self.assertTrue(response.context['address_form'].errors)
        self.assertContains(response, '保留地址')
        self.assertFalse(self.user.shipping_addresses.exists())

    def test_addresses_are_private_and_mutations_require_post(self):
        other = get_user_model().objects.create_user(username='other', email='other@example.com')
        address = ShippingAddress.objects.create(user=other, name='其他會員', phone='0900000000', address='不應顯示的地址')
        self.assertNotContains(self.client.get(reverse('profile') + '?tab=addresses'), address.address)
        self.assertEqual(self.client.get(reverse('address_book'), {'edit': address.pk}).status_code, 404)
        self.assertEqual(self.client.post(reverse('address_book'), {'address_id': address.pk}).status_code, 404)
        for route in ['address_set_default', 'address_delete']:
            url = reverse(route, args=[address.pk])
            self.assertEqual(self.client.post(url).status_code, 404)
            self.assertEqual(self.client.get(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('profile')).status_code, 302)
