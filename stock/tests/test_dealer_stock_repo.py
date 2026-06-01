from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from core.constants import PointType
from products.models import Product
from retail_points.models import RetailPoint, RetailPointAddress
from stock.models import DealerStock
from stock.repo.dealer_stock_repo import DealerStockRepo


class DealerStockRepoTests(TestCase):
    def setUp(self):
        self.dealer = RetailPoint.objects.create(
            name="Dealer",
            point_type=PointType.DEALER,
            daily_revenue=Decimal("0"),
        )
        RetailPointAddress.objects.create(
            retail_point=self.dealer,
            country="RU",
            city="Moscow",
            street="S",
            house_number="1",
        )
        self.product = Product.objects.create(
            brand="B",
            model="M",
            price=Decimal("100"),
            release_date="2024-01-01",
        )
        self.stock = DealerStock.objects.create(dealer=self.dealer, product=self.product, quantity=0)

    def test_replenish_zero_stock(self):
        DealerStockRepo().replenish_zero_stock()
        self.stock.refresh_from_db()
        self.assertGreaterEqual(self.stock.quantity, 5)
        self.assertLessEqual(self.stock.quantity, 25)

    @patch("stock.tasks.notify_zero_stock.delay")
    def test_hourly_write_off_adds_revenue(self, mock_notify):
        self.stock.quantity = 20
        self.stock.save()
        with patch("stock.repo.dealer_stock_repo.random.randint", side_effect=[1, 5]):
            with patch("stock.repo.dealer_stock_repo.random.choice", return_value=self.dealer):
                with patch("stock.repo.dealer_stock_repo.random.sample", return_value=[self.stock]):
                    DealerStockRepo().hourly_write_off()
        self.dealer.refresh_from_db()
        self.assertGreater(self.dealer.daily_revenue, 0)
