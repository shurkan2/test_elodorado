from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core.constants import PointType
from products.models import Product
from retail_points.models import Employee, RetailPoint, RetailPointAddress
from stock.models import DealerStock

User = get_user_model()


class RetailPointAPITests(APITestCase):
    def setUp(self):
        self.head = RetailPoint.objects.create(
            name="Head Office",
            point_type=PointType.HEAD,
            daily_revenue=Decimal("0"),
        )
        RetailPointAddress.objects.create(
            retail_point=self.head,
            country="RU",
            city="Moscow",
            street="Main",
            house_number="1",
        )
        self.dealer1 = RetailPoint.objects.create(
            name="Dealer Low",
            point_type=PointType.DEALER,
            daily_revenue=Decimal("100"),
        )
        RetailPointAddress.objects.create(
            retail_point=self.dealer1,
            country="RU",
            city="Moscow",
            street="Trade",
            house_number="2",
        )
        self.dealer2 = RetailPoint.objects.create(
            name="Dealer High",
            point_type=PointType.DEALER,
            daily_revenue=Decimal("1000"),
        )
        RetailPointAddress.objects.create(
            retail_point=self.dealer2,
            country="RU",
            city="Kazan",
            street="Trade",
            house_number="3",
        )
        for idx, point in enumerate((self.head, self.dealer1, self.dealer2)):
            Employee.objects.create(
                retail_point=point,
                full_name=f"Emp {point.name}",
                phone=f"+7900100000{idx}",
                email=f"emp{point.id}@test.com",
                is_active=True,
            )
        self.dealer1.employees.create(
            full_name="Second",
            phone="+79000000001",
            email="second@test.com",
            is_active=True,
        )

        self.user = User.objects.create_user("apiuser", "u@test.com", "pass")
        emp = Employee.objects.first()
        emp.user = self.user
        emp.is_active = True
        emp.save()
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        self.product = Product.objects.create(
            brand="TestBrand",
            model="X1",
            price=Decimal("500"),
            release_date="2024-06-01",
        )
        DealerStock.objects.create(dealer=self.dealer1, product=self.product, quantity=5)

    def test_list_all_points(self):
        response = self.client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_filter_by_city(self):
        response = self.client.get(reverse("retail-points"), {"city": "Kazan"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Dealer High")

    def test_above_avg_revenue(self):
        response = self.client.get(reverse("above-avg-revenue"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data]
        self.assertIn("Dealer High", names)
        self.assertNotIn("Head Office", names)

    def test_filter_by_product(self):
        response = self.client.get(reverse("retail-points"), {"product_id": self.product.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_daily_revenue_readonly_on_update(self):
        response = self.client.put(
            reverse("retail-point-detail", args=[self.dealer1.id]),
            {"name": "Updated", "daily_revenue": "9999"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.dealer1.refresh_from_db()
        self.assertEqual(self.dealer1.daily_revenue, Decimal("100"))

    def test_cannot_create_second_head(self):
        response = self.client.post(
            reverse("retail-points"),
            {
                "name": "Another Head",
                "point_type": PointType.HEAD,
                "country": "RU",
                "city": "X",
                "street": "Y",
                "house_number": "1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_delete_sole_head(self):
        response = self.client.delete(reverse("retail-point-detail", args=[self.head.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
