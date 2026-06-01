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


class RBACTests(APITestCase):
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
            name="Dealer Moscow",
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
            name="Dealer Kazan",
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

        head_user = User.objects.create_user("head1", "head@test.com", "headpass")
        dealer_user = User.objects.create_user("dealer1", "dealer@test.com", "dealerpass")

        Employee.objects.create(
            retail_point=self.head,
            user=head_user,
            full_name="Head Emp",
            phone="+79000000001",
            email="head@test.com",
            is_active=True,
        )
        Employee.objects.create(
            retail_point=self.dealer1,
            user=dealer_user,
            full_name="Dealer Emp",
            phone="+79000000002",
            email="dealer@test.com",
            is_active=True,
        )
        Employee.objects.create(
            retail_point=self.dealer1,
            full_name="Dealer Emp 2",
            phone="+79000000003",
            email="dealer2@test.com",
            is_active=True,
        )

        self.product = Product.objects.create(
            brand="TestBrand",
            model="X1",
            price=Decimal("500"),
            release_date="2024-06-01",
        )
        DealerStock.objects.create(dealer=self.dealer1, product=self.product, quantity=5)
        DealerStock.objects.create(dealer=self.dealer2, product=self.product, quantity=3)

        self.head_token = Token.objects.create(user=head_user)
        self.dealer_token = Token.objects.create(user=dealer_user)

    def _auth_head(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.head_token.key}")

    def _auth_dealer(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.dealer_token.key}")

    def test_head_sees_all_points(self):
        self._auth_head()
        response = self.client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_dealer_sees_only_own_point_in_list(self):
        self._auth_dealer()
        response = self.client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Dealer Moscow")

    def test_dealer_filter_by_city_only_own(self):
        self._auth_dealer()
        response = self.client.get(reverse("retail-points"), {"city": "Moscow"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Dealer Moscow")

    def test_dealer_filter_by_city_other_city_empty(self):
        self._auth_dealer()
        response = self.client.get(reverse("retail-points"), {"city": "Kazan"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_dealer_filter_by_product_only_own(self):
        self._auth_dealer()
        response = self.client.get(reverse("retail-points"), {"product_id": self.product.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Dealer Moscow")

    def test_dealer_cannot_see_other_point_detail(self):
        self._auth_dealer()
        response = self.client.get(reverse("retail-point-detail", args=[self.dealer2.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_dealer_cannot_above_avg_revenue(self):
        self._auth_dealer()
        response = self.client.get(reverse("above-avg-revenue"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dealer_cannot_create_point(self):
        self._auth_dealer()
        response = self.client.post(
            reverse("retail-points"),
            {
                "name": "New Dealer",
                "point_type": PointType.DEALER,
                "country": "RU",
                "city": "X",
                "street": "Y",
                "house_number": "1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dealer_can_update_own_point(self):
        self._auth_dealer()
        response = self.client.put(
            reverse("retail-point-detail", args=[self.dealer1.id]),
            {"name": "Updated Dealer"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dealer_cannot_update_other_point(self):
        self._auth_dealer()
        response = self.client.put(
            reverse("retail-point-detail", args=[self.dealer2.id]),
            {"name": "Hack"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dealer_cannot_create_product(self):
        self._auth_dealer()
        response = self.client.post(
            reverse("products"),
            {
                "brand": "Brand",
                "model": "M",
                "price": "100",
                "release_date": "2024-01-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dealer_can_read_catalog(self):
        self._auth_dealer()
        response = self.client.get(reverse("products"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dealer_can_manage_own_stock(self):
        self._auth_dealer()
        response = self.client.post(
            reverse("dealer-stock"),
            {"product_id": self.product.id, "quantity": 10},
            format="json",
        )
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        stock = DealerStock.objects.get(dealer=self.dealer1, product=self.product)
        self.assertEqual(stock.quantity, 10)

    def test_dealer_stock_list_only_own(self):
        self._auth_dealer()
        response = self.client.get(reverse("dealer-stock"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(item["dealer_id"] == self.dealer1.id for item in response.data))
