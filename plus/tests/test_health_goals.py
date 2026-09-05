from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from plus.models import DailyHealthLog, UserGoal, UserProfile


class HealthGoalExperienceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='health-user',
            email='health@example.com',
            password='Testpass123!',
            email_verified=True,
        )
        UserProfile.objects.create(
            user=self.user,
            height=Decimal('170'),
            weight=Decimal('68'),
            gender='M',
        )
        self.client.force_login(self.user)

    def test_daily_checkin_creates_and_updates_one_record_per_day(self):
        url = reverse('save_daily_health_log')
        payload = {
            'recorded_date': timezone.localdate().isoformat(),
            'sleep_hours': '7.5',
            'sleep_quality': '4',
            'steps': '8420',
            'resting_heart_rate': '66',
            'systolic_bp': '118',
            'diastolic_bp': '76',
            'mood': '4',
            'energy_level': '5',
            'notes': '狀態不錯',
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(DailyHealthLog.objects.count(), 1)

        payload['steps'] = '9100'
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DailyHealthLog.objects.count(), 1)
        self.assertEqual(DailyHealthLog.objects.get().steps, 9100)

    def test_daily_checkin_rejects_invalid_vitals_and_future_dates(self):
        url = reverse('save_daily_health_log')
        response = self.client.post(url, {'systolic_bp': '70', 'diastolic_bp': '90'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])

        response = self.client.post(url, {
            'recorded_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            'steps': '1000',
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])

    def test_goal_update_saves_action_targets(self):
        response = self.client.post(reverse('update_goal'), {
            'goal_type': 'maintain',
            'activity_level': 'moderate',
            'current_weight': '68',
            'target_weight': '66',
            'height': '170',
            'age': '30',
            'gender': 'male',
            'target_date': (timezone.localdate() + timedelta(days=60)).isoformat(),
            'daily_water_goal_ml': '2400',
            'daily_steps_goal': '9000',
            'weekly_workout_goal_minutes': '180',
            'sleep_goal_hours': '7.5',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        goal = UserGoal.objects.get(user=self.user)
        self.assertEqual(goal.daily_water_goal_ml, 2400)
        self.assertEqual(goal.daily_steps_goal, 9000)
        self.assertEqual(goal.weekly_workout_goal_minutes, 180)
        self.assertEqual(goal.sleep_goal_hours, Decimal('7.5'))

    def test_goal_page_exposes_health_dashboard(self):
        response = self.client.get(reverse('goal_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '今日健康 Check-in')
        self.assertContains(response, '你的 7 日節奏')
        self.assertIn('weekly_progress', response.context)
