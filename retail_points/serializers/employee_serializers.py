from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from retail_points.models import Employee, validate_head_single_employee


class EmployeeUpsertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ("retail_point", "full_name", "phone", "email", "is_active")

    def validate(self, attrs):
        retail_point = attrs.get("retail_point") or (
            self.instance.retail_point if self.instance else None
        )
        if retail_point:
            try:
                validate_head_single_employee(
                    retail_point,
                    employee_pk=self.instance.pk if self.instance else None,
                )
            except DjangoValidationError as exc:
                raise serializers.ValidationError(
                    {"retail_point": exc.messages}
                ) from exc
        return attrs
