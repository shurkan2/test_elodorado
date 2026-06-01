from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Product(models.Model):
    brand = models.CharField("Бренд", max_length=50)
    model = models.CharField("Модель", max_length=25)
    price = models.DecimalField("Цена", max_digits=12, decimal_places=2)
    release_date = models.DateField("Дата выхода на рынок")

    class Meta:
        verbose_name = "Продукт каталога"
        verbose_name_plural = "Продукты Каталога"

    def __str__(self):
        return f"{self.brand} {self.model}"

    def clean(self):
        if self.release_date and self.release_date > timezone.localdate():
            raise ValidationError({"release_date": "Дата выхода не может быть в будущем."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
