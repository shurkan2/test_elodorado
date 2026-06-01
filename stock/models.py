from django.core.exceptions import ValidationError
from django.db import models

from core.constants import PointType
from products.models import Product
from retail_points.models import RetailPoint


class DealerStock(models.Model):
    dealer = models.ForeignKey(
        RetailPoint,
        on_delete=models.CASCADE,
        related_name="stock_items",
        limit_choices_to={"point_type": PointType.DEALER},
        verbose_name="Дилерский центр",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="dealer_stocks",
        verbose_name="Продукт",
    )
    quantity = models.PositiveIntegerField("Количество", default=0)

    class Meta:
        verbose_name = "Учёт наличия"
        verbose_name_plural = "Учёт наличия"
        constraints = [
            models.UniqueConstraint(fields=["dealer", "product"], name="unique_dealer_product"),
        ]

    def __str__(self):
        return f"{self.dealer.name} — {self.product} ({self.quantity})"

    def clean(self):
        if self.dealer_id and self.dealer.point_type != PointType.DEALER:
            raise ValidationError({"dealer": "Остатки допустимы только у дилерских центров."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
