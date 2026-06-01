from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from access.models import EmployeeApiKey
from core.constants import AUTH_TOKEN_TTL
from retail_points.models import Employee


def _active_employee_for_user(user) -> Employee | None:
    if not user or not user.is_authenticated:
        return None
    return (
        Employee.objects.select_related("retail_point")
        .filter(user=user, is_active=True)
        .first()
    )


class ExpiringTokenAuthentication(TokenAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            bearer = auth[7:].strip()
            if bearer:
                return self.authenticate_credentials(bearer)
        return super().authenticate(request)

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)

        if not user.is_active:
            raise AuthenticationFailed("Учётная запись деактивирована.")

        if not _active_employee_for_user(user):
            raise AuthenticationFailed("Доступ только для активных сотрудников.")

        if timezone.now() - token.created > AUTH_TOKEN_TTL:
            raise AuthenticationFailed("Токен истёк. Выполните вход снова.")

        return user, token


class EmployeeApiKeyAuthentication(BaseAuthentication):
    keyword = "X-API-Key"

    def authenticate(self, request):
        raw_key = request.headers.get(self.keyword)
        if not raw_key:
            return None

        key_hash = EmployeeApiKey.hash_key(raw_key)
        try:
            api_key = EmployeeApiKey.objects.select_related(
                "employee__user",
                "employee__retail_point",
            ).get(key_hash=key_hash)
        except EmployeeApiKey.DoesNotExist as exc:
            raise AuthenticationFailed("Неверный API-ключ.") from exc

        if not api_key.is_valid():
            raise AuthenticationFailed("API-ключ деактивирован.")

        employee = api_key.employee
        if not employee.is_active:
            raise AuthenticationFailed("Сотрудник деактивирован.")

        user = employee.user
        if not user or not user.is_active:
            raise AuthenticationFailed("У сотрудника нет активной учётной записи.")

        return user, api_key
