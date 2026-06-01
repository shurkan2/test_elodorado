from rest_framework import serializers

from retail_points.models import Employee, RetailPoint, RetailPointAddress


class RetailPointAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailPointAddress
        fields = ("country", "city", "street", "house_number")


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ("id", "full_name", "phone", "email", "is_active")
        read_only_fields = fields


class RetailPointSerializer(serializers.ModelSerializer):
    address = RetailPointAddressSerializer(read_only=True)
    employees = EmployeeSerializer(many=True, read_only=True)

    class Meta:
        model = RetailPoint
        fields = ("id", "name", "point_type", "daily_revenue", "address", "employees")
        read_only_fields = ("id", "daily_revenue")


class RetailPointCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    point_type = serializers.ChoiceField(choices=RetailPoint._meta.get_field("point_type").choices)
    country = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    street = serializers.CharField(max_length=200)
    house_number = serializers.CharField(max_length=20)

    def validate_name(self, value):
        if len(value) > 50:
            raise serializers.ValidationError("Длина названия не более 50 символов.")
        return value


class RetailPointUpdateSerializer(serializers.ModelSerializer):
    address = RetailPointAddressSerializer(required=False)

    class Meta:
        model = RetailPoint
        fields = ("name", "point_type", "address")
        read_only_fields = ("point_type",)

    def validate_name(self, value):
        if len(value) > 50:
            raise serializers.ValidationError("Длина названия не более 50 символов.")
        return value

    def update(self, instance, validated_data):
        address_data = validated_data.pop("address", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if address_data:
            RetailPointAddress.objects.filter(retail_point=instance).update(**address_data)
        return instance
