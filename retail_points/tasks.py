from core.celery_utils import resilient_task
from retail_points.repo.retail_point_repo import RetailPointRepo


@resilient_task(queue="heavy")
def reset_daily_revenue(self):
    RetailPointRepo().reset_all_dealers_daily_revenue()


@resilient_task(queue="heavy")
def clear_daily_revenue_async(self, ids):
    RetailPointRepo().clear_daily_revenue(ids)
