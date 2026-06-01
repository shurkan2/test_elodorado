from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.admin.sites import AdminSite

from core.constants import PointType
from core.exceptions import DatabaseOperationError
from core.notifications import send_task_failure_email
from retail_points.admin import RetailPointAdmin
from retail_points.models import Employee, RetailPoint, RetailPointAddress
from retail_points.tasks import reset_daily_revenue

User = get_user_model()


class AdminMessageTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = RetailPointAdmin(RetailPoint, AdminSite())
        self.point = RetailPoint.objects.create(
            name="D",
            point_type=PointType.DEALER,
            daily_revenue=Decimal("100"),
        )
        RetailPointAddress.objects.create(
            retail_point=self.point,
            country="RU",
            city="Moscow",
            street="S",
            house_number="1",
        )
        self.user = User.objects.create_superuser("admin", "a@test.com", "pass")

    def _add_messages(self, request):
        request.session = "session"
        messages = FallbackStorage(request)
        request._messages = messages

    def test_clear_revenue_db_error_shows_russian_message(self):
        request = self.factory.post("/")
        request.user = self.user
        self._add_messages(request)
        queryset = RetailPoint.objects.filter(pk=self.point.pk)

        with patch(
            "retail_points.admin.RetailPointRepo.clear_daily_revenue",
            side_effect=DatabaseOperationError("База данных недоступна."),
        ):
            self.admin.clear_daily_revenue(request, queryset)

        stored = list(request._messages)
        self.assertTrue(any("База данных недоступна" in str(m) for m in stored))


class TaskFailureNotificationTests(TestCase):
    def setUp(self):
        self.head = RetailPoint.objects.create(
            name="Head",
            point_type=PointType.HEAD,
            daily_revenue=Decimal("0"),
        )
        RetailPointAddress.objects.create(
            retail_point=self.head,
            country="RU",
            city="Moscow",
            street="A",
            house_number="1",
        )
        Employee.objects.create(
            retail_point=self.head,
            full_name="Head Emp",
            phone="1",
            email="head@test.com",
            is_active=True,
        )

    def test_send_task_failure_email_russian(self):
        send_task_failure_email(
            task_name="Тестовая задача",
            error_message="Ошибка БД",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Тестовая задача", mail.outbox[0].subject)
        self.assertIn("Ошибка БД", mail.outbox[0].body)


class TaskTests(TestCase):
    def test_reset_daily_revenue(self):
        RetailPoint.objects.create(
            name="D",
            point_type=PointType.DEALER,
            daily_revenue=Decimal("500"),
        )
        reset_daily_revenue.run()
        dealer = RetailPoint.objects.get(point_type=PointType.DEALER)
        self.assertEqual(dealer.daily_revenue, Decimal("0"))
