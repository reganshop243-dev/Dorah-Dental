from django.test import TestCase
from django.contrib.auth.models import User
from .models import CompanySettings

class CoreModelTest(TestCase):
    def test_company_settings(self):
        settings = CompanySettings.get_settings()
        self.assertEqual(settings.business_name, "Dora's Dental Gem")
