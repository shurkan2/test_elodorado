from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from access.services import employee_access
from core.constants import DEFAULT_EMPLOYEE_PASSWORD, PointType
from retail_points.models import Employee, RetailPoint, RetailPointAddress

User = get_user_model()


class EmployeeAccessTests(TestCase):
    def setUp(self):
        self.dealer = RetailPoint.objects.create(
            name="Dealer",
            point_type=PointType.DEALER,
            daily_revenue=Decimal("0"),
        )
        RetailPointAddress.objects.create(
            retail_point=self.dealer,
            country="RU",
            city="Moscow",
            street="S",
            house_number="1",
        )

    def test_provision_employee_default_credentials(self):
        employee = Employee.objects.create(
            retail_point=self.dealer,
            full_name="Test",
            phone="+79001110001",
            email="unique1@test.com",
            is_active=True,
        )
        employee_access.provision_employee(employee)
        employee.refresh_from_db()
        self.assertEqual(employee.user.username, f"user{employee.pk}")
        self.assertEqual(employee.admin_visible_password, DEFAULT_EMPLOYEE_PASSWORD)
        self.assertTrue(employee.must_change_password)
        self.assertTrue(employee.admin_visible_api_key)
        self.assertTrue(employee.api_key.is_active)

    def test_duplicate_email_rejected(self):
        Employee.objects.create(
            retail_point=self.dealer,
            full_name="A",
            phone="+79001110002",
            email="dup@test.com",
            is_active=True,
        )
        with self.assertRaises(IntegrityError):
            Employee.objects.create(
                retail_point=self.dealer,
                full_name="B",
                phone="+79001110003",
                email="dup@test.com",
                is_active=True,
            )

    def test_duplicate_phone_rejected(self):
        Employee.objects.create(
            retail_point=self.dealer,
            full_name="A",
            phone="+79001110004",
            email="a4@test.com",
            is_active=True,
        )
        with self.assertRaises(IntegrityError):
            Employee.objects.create(
                retail_point=self.dealer,
                full_name="B",
                phone="+79001110004",
                email="b4@test.com",
                is_active=True,
            )

    def test_reset_password_updates_visible_field(self):
        employee = Employee.objects.create(
            retail_point=self.dealer,
            full_name="Reset",
            phone="+79001110005",
            email="reset@test.com",
            is_active=True,
        )
        new_password = employee_access.reset_password(employee, random_password=False)
        employee.refresh_from_db()
        self.assertEqual(new_password, DEFAULT_EMPLOYEE_PASSWORD)
        self.assertEqual(employee.admin_visible_password, DEFAULT_EMPLOYEE_PASSWORD)
        self.assertTrue(employee.must_change_password)
