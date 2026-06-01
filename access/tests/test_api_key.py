from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from access.services import employee_access
from core.constants import PointType
from products.models import Product
from retail_points.models import Employee, RetailPoint, RetailPointAddress
from stock.models import DealerStock

User = get_user_model()


class EmployeeApiKeyTests(TestCase):
    def setUp(self):
        self.dealer = RetailPoint.objects.create(
            name="My Dealer",
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
        self.employee = Employee.objects.create(
            retail_point=self.dealer,
            full_name="A",
            phone="1",
            email="a@test.com",
            is_active=True,
        )
        Employee.objects.create(
            retail_point=self.dealer,
            full_name="B",
            phone="2",
            email="b@test.com",
            is_active=True,
        )
        user = User.objects.create_user("dealer_api", "a@test.com", "pass")
        self.employee.user = user
        self.employee.save()
        _, self.raw_key = employee_access.issue_api_key(self.employee)
        self.client = APIClient()
        self.client.credentials(HTTP_X_API_KEY=self.raw_key)
        product = Product.objects.create(
            brand="B",
            model="M",
            price=Decimal("100"),
            release_date="2024-01-01",
        )
        DealerStock.objects.create(dealer=self.dealer, product=product, quantity=3)

    def test_read_own_point(self):
        response = self.client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "My Dealer")

    def test_read_own_stock(self):
        response = self.client.get(reverse("dealer-stock"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_points_scoped_to_own_dealer(self):
        other = RetailPoint.objects.create(
            name="Other",
            point_type=PointType.DEALER,
            daily_revenue=Decimal("0"),
        )
        RetailPointAddress.objects.create(
            retail_point=other,
            country="RU",
            city="SPB",
            street="X",
            house_number="2",
        )
        response = self.client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "My Dealer")

    def test_invalid_key(self):
        client = APIClient()
        client.credentials(HTTP_X_API_KEY="invalid-key")
        response = client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_employee_denied(self):
        self.employee.is_active = False
        self.employee.save()
        response = self.client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
