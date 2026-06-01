from celery import Task
from celery import shared_task
from django.db import DatabaseError
from django.db.utils import OperationalError

from core.exceptions import DatabaseOperationError

DB_ERRORS = (DatabaseError, OperationalError, DatabaseOperationError)

TASK_DISPLAY_NAMES = {
    "retail_points.tasks.reset_daily_revenue": "Обнуление суточной выручки дилеров",
    "retail_points.tasks.clear_daily_revenue_async": "Очистка суточной выручки",
    "stock.tasks.replenish_zero_stock": "Пополнение нулевых остатков",
    "stock.tasks.hourly_write_off": "Часовое списание остатков",
}

NOTIFY_ON_FAILURE_TASKS = set(TASK_DISPLAY_NAMES.keys())


class ResilientTask(Task):
    autoretry_for = DB_ERRORS
    retry_backoff = 60
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if self.name in NOTIFY_ON_FAILURE_TASKS:
            from core.notifications import send_task_failure_email

            display_name = TASK_DISPLAY_NAMES.get(self.name, self.name)
            send_task_failure_email(task_name=display_name, error_message=str(exc))
        super().on_failure(exc, task_id, args, kwargs, einfo)


def resilient_task(**task_kwargs):
    return shared_task(bind=True, base=ResilientTask, **task_kwargs)
