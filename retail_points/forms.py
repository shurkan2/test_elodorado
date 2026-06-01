from django import forms

from django import forms as django_forms
from django.core.exceptions import ValidationError

from retail_points.models import Employee, validate_employee_count


class EmployeeAdminForm(forms.ModelForm):
    username = forms.CharField(
        label="Логин",
        max_length=150,
        required=False,
        help_text="По умолчанию user{id}. Можно изменить до сохранения учётной записи.",
    )

    class Meta:
        model = Employee
        fields = (
            "retail_point",
            "full_name",
            "phone",
            "email",
            "is_active",
            "admin_visible_password",
            "admin_visible_api_key",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["admin_visible_password"].disabled = True
        self.fields["admin_visible_api_key"].disabled = True
        if self.instance.pk and self.instance.user_id:
            self.fields["username"].initial = self.instance.user.username
        elif self.instance.pk:
            self.fields["username"].initial = f"user{self.instance.pk}"

    def clean(self):
        cleaned_data = super().clean()
        retail_point = cleaned_data.get("retail_point")
        if retail_point:
            try:
                validate_employee_count(
                    retail_point,
                    employee_pk=self.instance.pk if self.instance.pk else None,
                )
            except ValidationError as exc:
                raise django_forms.ValidationError(exc.messages) from exc
        return cleaned_data
