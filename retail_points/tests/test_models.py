from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from core.constants import PointType
from retail_points.models import Employee, RetailPoint, RetailPointAddress
from retail_points.serializers.employee_serializers import EmployeeUpsertSerializer

User = get_user_model()


class RetailPointModelTests(TestCase):
    def test_one_head_constraint(self):
        head = RetailPoint.objects.create(name="Head", point_type=PointType.HEAD)
        RetailPointAddress.objects.create(
            retail_point=head,
            country="RU",
            city="Moscow",
            street="A",
            house_number="1",
        )
        with self.assertRaises(IntegrityError):
            RetailPoint.objects.create(name="Head 2", point_type=PointType.HEAD)


class EmployeeRulesTests(TestCase):
    def setUp(self):
        self.head = RetailPoint.objects.create(name="Head", point_type=PointType.HEAD)
        RetailPointAddress.objects.create(
            retail_point=self.head,
            country="RU",
            city="Moscow",
            street="A",
            house_number="1",
        )
        self.dealer = RetailPoint.objects.create(name="Dealer", point_type=PointType.DEALER)
        RetailPointAddress.objects.create(
            retail_point=self.dealer,
            country="RU",
            city="SPB",
            street="B",
            house_number="2",
        )

    def test_head_one_employee(self):
        Employee.objects.create(
            retail_point=self.head,
            full_name="A",
            phone="+79004440001",
            email="head_emp@test.com",
        )
        self.assertEqual(self.head.employees.count(), 1)

    def test_head_rejects_second_employee_on_clean(self):
        Employee.objects.create(
            retail_point=self.head,
            full_name="A",
            phone="+79004440001",
            email="head_emp@test.com",
        )
        second = Employee(
            retail_point=self.head,
            full_name="B",
            phone="+79004440002",
            email="head_b@test.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            second.full_clean()
        self.assertIn("Удалите текущего", str(ctx.exception))

    def test_head_rejects_second_employee_on_save(self):
        Employee.objects.create(
            retail_point=self.head,
            full_name="A",
            phone="+79005550001",
            email="head_save_a@test.com",
        )
        second = Employee(
            retail_point=self.head,
            full_name="B",
            phone="+79005550002",
            email="head_save_b@test.com",
        )
        with self.assertRaises(ValidationError) as ctx:
            second.save()
        self.assertIn("Удалите текущего", str(ctx.exception))

    def test_employee_upsert_serializer_rejects_second_head(self):
        Employee.objects.create(
            retail_point=self.head,
            full_name="A",
            phone="+79006660001",
            email="head_ser_a@test.com",
        )
        serializer = EmployeeUpsertSerializer(
            data={
                "retail_point": self.head.pk,
                "full_name": "B",
                "phone": "+79006660002",
                "email": "head_ser_b@test.com",
                "is_active": True,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("retail_point", serializer.errors)

    def test_dealer_two_employees(self):
        Employee.objects.create(
            retail_point=self.dealer,
            full_name="A",
            phone="+79002220001",
            email="dealer_a@test.com",
        )
        Employee.objects.create(
            retail_point=self.dealer,
            full_name="B",
            phone="+79002220002",
            email="dealer_b@test.com",
        )
        self.assertGreaterEqual(self.dealer.employees.count(), 2)

    def test_duplicate_email(self):
        Employee.objects.create(
            retail_point=self.dealer,
            full_name="A",
            phone="+79003330001",
            email="same@test.com",
        )
        with self.assertRaises(IntegrityError):
            Employee.objects.create(
                retail_point=self.dealer,
                full_name="B",
                phone="+79003330002",
                email="same@test.com",
            )
