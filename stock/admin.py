from django.contrib import admin
from django.utils.html import format_html

from core.constants import PointType
from retail_points.models import RetailPoint
from stock.models import DealerStock


class DealerFilter(admin.SimpleListFilter):
    title = "Дилерский центр"
    parameter_name = "dealer"

    def lookups(self, request, model_admin):
        dealers = RetailPoint.objects.filter(point_type=PointType.DEALER).order_by("name")
        return [(d.id, d.name) for d in dealers]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(dealer_id=self.value())
        return queryset


class InStockFilter(admin.SimpleListFilter):
    title = "Наличие"
    parameter_name = "in_stock"

    def lookups(self, request, model_admin):
        return [
            ("yes", "Есть в наличии"),
            ("no", "Нет в наличии"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(quantity__gt=0)
        if self.value() == "no":
            return queryset.filter(quantity=0)
        return queryset


@admin.register(DealerStock)
class DealerStockAdmin(admin.ModelAdmin):
    list_display = ("dealer_link", "product_link", "quantity")
    list_filter = (DealerFilter, InStockFilter)

    @admin.display(description="Дилер")
    def dealer_link(self, obj):
        url = f"/admin/retail_points/retailpoint/{obj.dealer_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.dealer.name)

    @admin.display(description="Продукт")
    def product_link(self, obj):
        url = f"/admin/products/product/{obj.product_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.product)
