from datetime import timedelta

from django.db import models


class PointType(models.TextChoices):
    HEAD = "HEAD", "Головной отдел"
    DEALER = "DEALER", "Дилерский центр"


ADMIN_ASYNC_CLEAR_THRESHOLD = 5
AUTH_TOKEN_TTL = timedelta(days=1)
DEFAULT_EMPLOYEE_PASSWORD = "11111111"
