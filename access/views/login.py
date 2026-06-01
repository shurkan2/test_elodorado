from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from access.services import employee_access
from retail_points.models import Employee

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def api_login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    if not username or not password:
        return Response(
            {"detail": "Укажите username и password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if not user:
        return Response(
            {"detail": "Неверные учётные данные."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return Response(
            {"detail": "Учётная запись деактивирована."},
            status=status.HTTP_403_FORBIDDEN,
        )

    employee = (
        Employee.objects.filter(user=user, is_active=True)
        .select_related("retail_point")
        .first()
    )
    if not employee:
        return Response(
            {"detail": "Доступ только для активных сотрудников."},
            status=status.HTTP_403_FORBIDDEN,
        )

    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    if employee.must_change_password:
        new_password = employee_access.complete_first_login(employee)
        token = employee_access.rotate_auth_token(user)
        return Response(
            {
                "token": token.key,
                "new_password": new_password,
                "password_change_required": True,
            }
        )

    token = employee_access.rotate_auth_token(user)
    return Response({"token": token.key})
