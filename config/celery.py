import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "replenish-zero-stock": {
        "task": "stock.tasks.replenish_zero_stock",
        "schedule": crontab(hour=9, minute=0),
    },
    "hourly-write-off": {
        "task": "stock.tasks.hourly_write_off",
        "schedule": crontab(minute=0),
    },
    "reset-dealer-revenue": {
        "task": "retail_points.tasks.reset_daily_revenue",
        "schedule": crontab(hour=21, minute=15),
    },
}
