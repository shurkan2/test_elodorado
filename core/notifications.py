from django.conf import settings
from django.core.mail import send_mail

from core.constants import PointType
from retail_points.models import Employee, RetailPoint


def _get_head_employee_email() -> str | None:
    head = RetailPoint.objects.filter(point_type=PointType.HEAD).first()
    if not head:
        return None
    employee = Employee.objects.filter(retail_point=head, is_active=True).first()
    return employee.email if employee else None


def send_zero_stock_email(*, head_email: str, dealer_name: str, address: str, product_name: str):
    subject = f"Нулевой остаток: {dealer_name}"
    body = (
        f"Дилерский центр: {dealer_name}\n"
        f"Адрес: {address}\n"
        f"Оборудование: {product_name}\n"
        f"Остаток по позиции стал равен нулю после списания."
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[head_email],
        fail_silently=False,
    )


def send_task_failure_email(*, task_name: str, error_message: str):
    """
    Отправка email ответственному (сотрудник головного отдела).

    TODO: позже заменить/дополнить централизованным логгером с документацией инцидентов.
    """
    head_email = _get_head_employee_email()
    if not head_email:
        return

    subject = f"Ошибка фоновой задачи: {task_name}"
    body = (
        f"Не удалось выполнить фоновую задачу «{task_name}».\n\n"
        f"Причина: {error_message}\n\n"
        f"Проверьте доступность базы данных и повторите операцию позже."
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[head_email],
        fail_silently=False,
    )
