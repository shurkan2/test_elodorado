from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core.constants import PointType
from retail_points.models import Employee, RetailPoint, RetailPointAddress

User = get_user_model()


class PermissionTests(APITestCase):
    def setUp(self):
        self.point = RetailPoint.objects.create(name="D", point_type=PointType.DEALER)
        RetailPointAddress.objects.create(
            retail_point=self.point,
            country="RU",
            city="Moscow",
            street="S",
            house_number="1",
        )

    def test_anonymous_denied(self):
        response = self.client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_employee_denied(self):
        user = User.objects.create_user("nemp", "n@test.com", "pass")
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_active_employee_allowed(self):
        user = User.objects.create_user("emp", "e@test.com", "pass")
        Employee.objects.create(
            retail_point=self.point,
            user=user,
            full_name="E",
            phone="1",
            email="e@test.com",
            is_active=True,
        )
        Employee.objects.create(
            retail_point=self.point,
            full_name="E2",
            phone="2",
            email="e2@test.com",
            is_active=True,
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
