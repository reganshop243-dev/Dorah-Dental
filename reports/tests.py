from django.test import TestCase

class ReportTest(TestCase):
    def test_report_imports(self):
        from . import views
        self.assertIsNotNone(views.aging_report)
