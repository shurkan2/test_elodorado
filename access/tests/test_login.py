from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from access.services import employee_access
from core.constants import AUTH_TOKEN_TTL, PointType
from retail_points.models import Employee, RetailPoint, RetailPointAddress

User = get_user_model()


class LoginTests(TestCase):
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
        self.user = User.objects.create_user("loginuser", "u@test.com", "secret")
        self.employee = Employee.objects.create(
            retail_point=self.dealer,
            user=self.user,
            full_name="Login User",
            phone="1",
            email="u@test.com",
            is_active=True,
        )
        Employee.objects.create(
            retail_point=self.dealer,
            full_name="Second",
            phone="2",
            email="s@test.com",
            is_active=True,
        )
        self.client = APIClient()

    def test_login_returns_token(self):
        response = self.client.post(
            reverse("api-login"),
            {"username": "loginuser", "password": "secret"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)
        token = Token.objects.get(user=self.user)
        self.assertEqual(token.key, response.data["token"])

    def test_login_inactive_employee_forbidden(self):
        self.employee.is_active = False
        self.employee.save()
        response = self.client.post(
            reverse("api-login"),
            {"username": "loginuser", "password": "secret"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_expired_token_rejected(self):
        token = Token.objects.create(user=self.user)
        Token.objects.filter(pk=token.pk).update(
            created=timezone.now() - AUTH_TOKEN_TTL - timedelta(hours=1)
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_provisioned_user_id_format(self):
        employee = Employee.objects.create(
            retail_point=self.dealer,
            full_name="Provisioned",
            phone="+79009990001",
            email="prov@test.com",
            is_active=True,
        )
        employee_access.provision_employee(employee)
        response = self.client.post(
            reverse("api-login"),
            {"username": f"user{employee.pk}", "password": "11111111"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("new_password", response.data)
        self.assertTrue(response.data["password_change_required"])
        self.assertEqual(len(response.data["new_password"]), 12)
        employee.refresh_from_db()
        self.assertFalse(employee.must_change_password)
        self.assertEqual(employee.admin_visible_password, response.data["new_password"])

    def test_first_login_old_password_rejected(self):
        employee = Employee.objects.create(
            retail_point=self.dealer,
            full_name="First Login",
            phone="+79009990002",
            email="first@test.com",
            is_active=True,
        )
        employee_access.provision_employee(employee)
        first = self.client.post(
            reverse("api-login"),
            {"username": f"user{employee.pk}", "password": "11111111"},
            format="json",
        )
        new_password = first.data["new_password"]
        second = self.client.post(
            reverse("api-login"),
            {"username": f"user{employee.pk}", "password": "11111111"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_401_UNAUTHORIZED)
        third = self.client.post(
            reverse("api-login"),
            {"username": f"user{employee.pk}", "password": new_password},
            format="json",
        )
        self.assertEqual(third.status_code, status.HTTP_200_OK)
        self.assertNotIn("new_password", third.data)

    def test_fresh_token_after_login_works(self):
        login = self.client.post(
            reverse("api-login"),
            {"username": "loginuser", "password": "secret"},
            format="json",
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")
        response = client.get(reverse("retail-points"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
