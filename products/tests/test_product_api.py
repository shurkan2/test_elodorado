from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core.constants import PointType
from products.models import Product
from retail_points.models import Employee, RetailPoint, RetailPointAddress

User = get_user_model()


class ProductAPITests(APITestCase):
    def setUp(self):
        head = RetailPoint.objects.create(name="Head", point_type=PointType.HEAD)
        RetailPointAddress.objects.create(
            retail_point=head,
            country="RU",
            city="Moscow",
            street="S",
            house_number="1",
        )
        user = User.objects.create_user("puser", "p@test.com", "pass")
        Employee.objects.create(
            retail_point=head,
            user=user,
            full_name="E",
            phone="1",
            email="p@test.com",
            is_active=True,
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_create_product_validation(self):
        response = self.client.post(
            reverse("products"),
            {
                "brand": "A" * 51,
                "model": "M",
                "price": "100",
                "release_date": "2024-01-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_future_release_date_rejected(self):
        future = timezone.localdate().replace(year=timezone.localdate().year + 1)
        response = self.client.post(
            reverse("products"),
            {
                "brand": "Brand",
                "model": "M",
                "price": "100",
                "release_date": future.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_crud_product(self):
        create = self.client.post(
            reverse("products"),
            {
                "brand": "Brand",
                "model": "Model",
                "price": "999.99",
                "release_date": "2024-01-01",
            },
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        pk = create.data["id"]
        update = self.client.put(
            reverse("product-detail", args=[pk]),
            {
                "brand": "Brand",
                "model": "New",
                "price": "1000",
                "release_date": "2024-01-01",
            },
            format="json",
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        delete = self.client.delete(reverse("product-detail", args=[pk]))
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)
