import random
from decimal import Decimal

from django.db import transaction
from django.db.models import F

from core.constants import PointType
from core.db import safe_db_operation
from core.notifications import send_zero_stock_email
from products.models import Product
from retail_points.models import Employee, RetailPoint
from stock.models import DealerStock


class DealerStockRepo:
    def replenish_zero_stock(self):
        with safe_db_operation(
            user_message="Не удалось пополнить остатки. База данных недоступна.",
        ):
            items = DealerStock.objects.filter(quantity=0).select_related("dealer", "product")
            for item in items:
                item.quantity = random.randint(5, 25)
                item.save(update_fields=["quantity"])

    def hourly_write_off(self):
        with safe_db_operation(
            user_message="Не удалось выполнить списание. База данных недоступна.",
        ):
            self._hourly_write_off()

    @transaction.atomic
    def _hourly_write_off(self):
        dealers = list(RetailPoint.objects.filter(point_type=PointType.DEALER))
        if not dealers:
            return

        dealer = random.choice(dealers)
        stocks = list(
            DealerStock.objects.filter(dealer=dealer, quantity__gt=0).select_related("product")
        )
        if not stocks:
            return

        sample_size = random.randint(1, min(3, len(stocks)))
        selected = random.sample(stocks, sample_size)
        total_revenue = Decimal("0")
        zero_stock_pairs = []

        for stock in selected:
            deduct = random.randint(1, min(10, stock.quantity))
            stock.quantity -= deduct
            stock.save(update_fields=["quantity"])
            total_revenue += stock.product.price * deduct
            if stock.quantity == 0:
                zero_stock_pairs.append((stock.dealer_id, stock.product_id))

        if total_revenue > 0:
            RetailPoint.objects.filter(pk=dealer.pk).update(
                daily_revenue=F("daily_revenue") + total_revenue
            )

        for dealer_id, product_id in zero_stock_pairs:
            from stock.tasks import notify_zero_stock

            notify_zero_stock.delay(dealer_id, product_id)

    def send_zero_stock_email(self, dealer_id: int, product_id: int):
        head = RetailPoint.objects.filter(point_type=PointType.HEAD).select_related("address").first()
        if not head:
            return

        head_employee = Employee.objects.filter(retail_point=head, is_active=True).first()
        if not head_employee:
            return

        dealer = RetailPoint.objects.select_related("address").get(pk=dealer_id)
        product = Product.objects.get(pk=product_id)
        address = dealer.address
        address_str = f"{address.country}, {address.city}, {address.street}, {address.house_number}"

        send_zero_stock_email(
            head_email=head_employee.email,
            dealer_name=dealer.name,
            address=address_str,
            product_name=f"{product.brand} {product.model}",
        )
