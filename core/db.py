from contextlib import contextmanager

from django.db import DatabaseError, transaction
from django.db.utils import OperationalError

from core.exceptions import DatabaseOperationError


@contextmanager
def safe_db_operation(*, user_message: str):
    try:
        with transaction.atomic():
            yield
    except (DatabaseError, OperationalError) as exc:
        raise DatabaseOperationError(user_message) from exc
