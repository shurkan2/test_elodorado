from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsActiveEmployee, IsNetworkStaff
from retail_points.repo.retail_point_repo import RetailPointRepo

repo = RetailPointRepo()


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsActiveEmployee])
def retail_points(request):
    if request.method == "POST":
        if not IsNetworkStaff().has_permission(request, None):
            return Response(
                {"detail": "Создание торговых точек доступно только головному отделу."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return repo.create(request)

    return repo.index(request)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsActiveEmployee, IsNetworkStaff])
def above_avg_revenue(request):
    return repo.above_avg_revenue(request)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated, IsActiveEmployee])
def retail_point_detail(request, pk):
    if request.method == "GET":
        return repo.show(request, pk)
    if request.method == "PUT":
        return repo.update(request, pk)
    if not IsNetworkStaff().has_permission(request, None):
        return Response(
            {"detail": "Удаление торговых точек доступно только головному отделу."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return repo.delete(request, pk)
