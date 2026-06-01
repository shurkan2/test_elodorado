from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsActiveEmployee, IsNetworkStaff
from products.repo.product_repo import ProductRepo

repo = ProductRepo()


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsActiveEmployee])
def products(request):
    if request.method == "GET":
        return repo.index(request)
    if not IsNetworkStaff().has_permission(request, None):
        return Response(
            {"detail": "Управление каталогом доступно только головному отделу."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return repo.create(request)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated, IsActiveEmployee])
def product_detail(request, pk):
    if request.method == "GET":
        return repo.show(request, pk)
    if not IsNetworkStaff().has_permission(request, None):
        return Response(
            {"detail": "Управление каталогом доступно только головному отделу."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if request.method == "PUT":
        return repo.update(request, pk)
    return repo.delete(request, pk)
