from django.db import transaction
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from core.constants import PointType
from core.db import safe_db_operation
from core.exceptions import HeadAlreadyExists, HeadDeleteForbidden
from core.permissions import get_active_employee, is_network_staff
from products.models import Product
from retail_points.models import RetailPoint, RetailPointAddress
from retail_points.serializers.retail_point_serializers import (
    RetailPointCreateSerializer,
    RetailPointSerializer,
    RetailPointUpdateSerializer,
)
from stock.models import DealerStock


class RetailPointRepo:
    def _base_queryset(self):
        return RetailPoint.objects.select_related("address").prefetch_related("employees")

    def _scoped_queryset(self, request):
        qs = self._base_queryset()
        if is_network_staff(request.user):
            return qs
        employee = get_active_employee(request.user)
        return qs.filter(pk=employee.retail_point_id)

    def _can_manage_point(self, request, point: RetailPoint) -> bool:
        if is_network_staff(request.user):
            return True
        employee = get_active_employee(request.user)
        return employee and point.pk == employee.retail_point_id

    def index(self, request):
        qs = self._scoped_queryset(request)
        city = request.query_params.get("city")
        product_id = request.query_params.get("product_id")

        if city:
            qs = qs.filter(address__city__icontains=city)

        if product_id:
            qs = qs.filter(
                stock_items__product_id=product_id,
                stock_items__quantity__gt=0,
            ).distinct()

        serializer = RetailPointSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def above_avg_revenue(self, request):
        avg = (
            RetailPoint.objects.filter(point_type=PointType.DEALER)
            .aggregate(avg=Avg("daily_revenue"))["avg"]
        )
        if avg is None:
            return Response([], status=status.HTTP_200_OK)

        qs = self._base_queryset().filter(
            point_type=PointType.DEALER,
            daily_revenue__gt=avg,
        )
        serializer = RetailPointSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def show(self, request, pk):
        point = get_object_or_404(self._scoped_queryset(request), pk=pk)
        return Response(RetailPointSerializer(point).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def create(self, request):
        serializer = RetailPointCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        if data["point_type"] == PointType.HEAD and RetailPoint.objects.filter(point_type=PointType.HEAD).exists():
            raise HeadAlreadyExists()

        point = RetailPoint.objects.create(
            name=data["name"],
            point_type=data["point_type"],
        )
        RetailPointAddress.objects.create(
            retail_point=point,
            country=data["country"],
            city=data["city"],
            street=data["street"],
            house_number=data["house_number"],
        )
        point = self._base_queryset().get(pk=point.pk)
        return Response(RetailPointSerializer(point).data, status=status.HTTP_201_CREATED)

    def update(self, request, pk):
        point = get_object_or_404(RetailPoint, pk=pk)
        if not self._can_manage_point(request, point):
            return Response(
                {"detail": "Нет доступа к этой торговой точке."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if "daily_revenue" in request.data:
            return Response(
                {"daily_revenue": "Поле «Выручка за день» доступно только для чтения."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = RetailPointUpdateSerializer(point, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        point = serializer.save()
        point = self._base_queryset().get(pk=point.pk)
        return Response(RetailPointSerializer(point).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        point = get_object_or_404(RetailPoint, pk=pk)
        if point.point_type == PointType.HEAD:
            if RetailPoint.objects.filter(point_type=PointType.HEAD).count() <= 1:
                raise HeadDeleteForbidden()
        point.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def clear_daily_revenue(self, ids):
        with safe_db_operation(
            user_message="Не удалось очистить выручку. База данных недоступна.",
        ):
            RetailPoint.objects.filter(id__in=ids).update(daily_revenue=0)

    def reset_all_dealers_daily_revenue(self):
        with safe_db_operation(
            user_message="Не удалось обнулить выручку дилеров. База данных недоступна.",
        ):
            RetailPoint.objects.filter(point_type=PointType.DEALER).update(daily_revenue=0)
