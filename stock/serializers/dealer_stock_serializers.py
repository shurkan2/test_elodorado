from rest_framework import serializers

from products.models import Product
from stock.models import DealerStock


class DealerStockSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField(read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    dealer_id = serializers.IntegerField(source="dealer.id", read_only=True)

    class Meta:
        model = DealerStock
        fields = ("id", "dealer_id", "product", "product_id", "quantity")
