import hashlib
import secrets

from django.db import models

from retail_points.models import Employee


class EmployeeApiKey(models.Model):
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name="api_key",
        verbose_name="Сотрудник",
    )
    key_hash = models.CharField("Хеш ключа", max_length=64, unique=True)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "API-ключ сотрудника"
        verbose_name_plural = "API-ключи сотрудников"

    def __str__(self):
        return f"API-ключ: {self.employee.full_name}"

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    @classmethod
    def generate(cls, employee: Employee) -> tuple["EmployeeApiKey", str]:
        raw_key = secrets.token_urlsafe(32)
        cls.objects.filter(employee=employee).delete()
        obj = cls.objects.create(
            employee=employee,
            key_hash=cls.hash_key(raw_key),
            is_active=True,
        )
        return obj, raw_key

    def is_valid(self) -> bool:
        return self.is_active
