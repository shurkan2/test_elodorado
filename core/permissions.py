from rest_framework.permissions import BasePermission

from core.constants import PointType
from retail_points.models import Employee


def get_active_employee(user):
    if not user or not user.is_authenticated:
        return None
    return (
        Employee.objects.select_related("retail_point", "user")
        .filter(user=user, is_active=True)
        .first()
    )


def is_network_staff(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    employee = get_active_employee(user)
    if not employee:
        return False
    return employee.retail_point.point_type == PointType.HEAD


class IsActiveEmployee(BasePermission):
    message = "Доступ только для активных сотрудников."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        return Employee.objects.filter(user=user, is_active=True).exists()


class IsNetworkStaff(BasePermission):
    message = "Доступ только для сотрудников головного отдела."

    def has_permission(self, request, view):
        return is_network_staff(request.user)
