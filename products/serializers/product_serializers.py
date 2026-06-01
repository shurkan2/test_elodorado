from django.utils import timezone
from rest_framework import serializers

from products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "brand", "model", "price", "release_date")
        read_only_fields = ("id",)

    def validate_brand(self, value):
        if len(value) > 50:
            raise serializers.ValidationError("Длина бренда не более 50 символов.")
        return value

    def validate_model(self, value):
        if len(value) > 25:
            raise serializers.ValidationError("Длина модели не более 25 символов.")
        return value

    def validate_release_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Дата выхода не может быть в будущем.")
        return value
