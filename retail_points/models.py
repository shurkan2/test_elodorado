from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.constants import PointType


class RetailPoint(models.Model):
    name = models.CharField("Название", max_length=50)
    point_type = models.CharField("Тип точки", max_length=10, choices=PointType.choices)
    daily_revenue = models.DecimalField(
        "Выручка за день",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
    )

    class Meta:
        verbose_name = "Торговая точка"
        verbose_name_plural = "Торговые точки"
        constraints = [
            models.UniqueConstraint(
                fields=["point_type"],
                condition=models.Q(point_type=PointType.HEAD),
                name="one_head_only",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_point_type_display()})"


class RetailPointAddress(models.Model):
    retail_point = models.OneToOneField(
        RetailPoint,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="address",
        verbose_name="Торговая точка",
    )
    country = models.CharField("Страна", max_length=100)
    city = models.CharField("Город", max_length=100)
    street = models.CharField("Улица", max_length=200)
    house_number = models.CharField("Номер дома", max_length=20)

    class Meta:
        verbose_name = "Адрес торговой точки"
        verbose_name_plural = "Адреса торговых точек"

    def __str__(self):
        return f"{self.city}, {self.street} {self.house_number}"


class Employee(models.Model):
    retail_point = models.ForeignKey(
        RetailPoint,
        on_delete=models.CASCADE,
        related_name="employees",
        verbose_name="Торговая точка",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
        verbose_name="Пользователь",
    )
    full_name = models.CharField("ФИО", max_length=200)
    phone = models.CharField("Телефон", max_length=30, unique=True)
    email = models.EmailField("E-mail", unique=True)
    is_active = models.BooleanField("Активен", default=True)
    must_change_password = models.BooleanField(
        "Требуется смена пароля при первом входе",
        default=False,
    )
    admin_visible_password = models.CharField(
        "Пароль для входа",
        max_length=128,
        blank=True,
        help_text="Текущий пароль для входа в API.",
    )
    admin_visible_api_key = models.CharField(
        "API-ключ",
        max_length=128,
        blank=True,
        help_text="Последний выданный ключ сотрудника.",
    )

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники и доступ к API"

    def __str__(self):
        return self.full_name

    def clean(self):
        if self.retail_point_id:
            validate_head_single_employee(self.retail_point, employee_pk=self.pk)


def validate_head_single_employee(
    retail_point: RetailPoint,
    *,
    employee_pk: int | None = None,
):
    if retail_point.point_type != PointType.HEAD:
        return
    count = retail_point.employees.count()
    if employee_pk is None:
        count += 1
    if count > 1:
        raise ValidationError(
            "У головного отдела уже есть сотрудник. "
            "Удалите текущего, затем добавьте нового."
        )


def validate_employee_count(retail_point: RetailPoint, *, employee_pk: int | None = None):
    validate_head_single_employee(retail_point, employee_pk=employee_pk)
    if retail_point.point_type == PointType.DEALER:
        count = retail_point.employees.count()
        if employee_pk is None:
            count += 1
        if count < 2:
            raise ValidationError(
                "У дилерского центра должно быть не менее двух сотрудников."
            )
