from core.celery_utils import resilient_task
from stock.repo.dealer_stock_repo import DealerStockRepo


@resilient_task(queue="heavy")
def replenish_zero_stock(self):
    DealerStockRepo().replenish_zero_stock()


@resilient_task(queue="heavy")
def hourly_write_off(self):
    DealerStockRepo().hourly_write_off()


@resilient_task(queue="light")
def notify_zero_stock(self, dealer_id, product_id):
    DealerStockRepo().send_zero_stock_email(dealer_id, product_id)
