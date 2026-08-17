from django.test import TestCase
from .models import NotificationSetting

class NotificationModelTest(TestCase):
    def test_settings_creation(self):
        settings = NotificationSetting.objects.create(
            enable_reminders=True, reminder_hours_before=24, channel='both'
        )
        self.assertTrue(settings.enable_reminders)
