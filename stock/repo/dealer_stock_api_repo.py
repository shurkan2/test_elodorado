from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response

from core.constants import PointType
from core.permissions import get_active_employee, is_network_staff
from products.models import Product
from stock.models import DealerStock
from stock.serializers.dealer_stock_serializers import DealerStockSerializer


class DealerStockCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=0)


class DealerStockApiRepo:
    def _scoped_queryset(self, request):
        qs = DealerStock.objects.select_related("product", "dealer")
        if is_network_staff(request.user):
            return qs
        employee = get_active_employee(request.user)
        return qs.filter(dealer_id=employee.retail_point_id)

    def index(self, request):
        stocks = self._scoped_queryset(request).order_by("dealer_id", "product__brand")
        return Response(DealerStockSerializer(stocks, many=True).data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = DealerStockCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        product = get_object_or_404(Product, pk=data["product_id"])

        if is_network_staff(request.user):
            dealer_id = request.data.get("dealer_id")
            if not dealer_id:
                return Response(
                    {"dealer_id": "Обязательное поле для головного отдела."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from retail_points.models import RetailPoint

            dealer = get_object_or_404(
                RetailPoint,
                pk=dealer_id,
                point_type=PointType.DEALER,
            )
        else:
            employee = get_active_employee(request.user)
            dealer = employee.retail_point
            if dealer.point_type != PointType.DEALER:
                return Response(
                    {"detail": "Остатки можно вести только в дилерских центрах."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        stock, created = DealerStock.objects.get_or_create(
            dealer=dealer,
            product=product,
            defaults={"quantity": data["quantity"]},
        )
        if not created:
            stock.quantity = data["quantity"]
            stock.save(update_fields=["quantity"])

        stock = self._scoped_queryset(request).get(pk=stock.pk)
        return Response(
            DealerStockSerializer(stock).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        stock = get_object_or_404(self._scoped_queryset(request), pk=pk)
        stock.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
