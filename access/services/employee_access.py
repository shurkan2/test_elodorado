from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from rest_framework.authtoken.models import Token

from access.models import EmployeeApiKey
from core.constants import DEFAULT_EMPLOYEE_PASSWORD
from retail_points.models import Employee

User = get_user_model()

DEMO_CREDENTIALS: dict[str, tuple[str, str]] = {
    "head@example.com": ("head1", "head1pass"),
    "manager1a@example.com": ("dealer1", "dealer1pass"),
}


def demo_credentials_for_email(email: str) -> tuple[str | None, str | None]:
    login, password = DEMO_CREDENTIALS.get(email, (None, None))
    return login, password


def _should_require_password_change(password: str | None) -> bool:
    return password is None or password == DEFAULT_EMPLOYEE_PASSWORD


def default_username(employee: Employee) -> str:
    if not employee.pk:
        raise ValueError("Employee must be saved before provisioning.")
    return f"user{employee.pk}"


def ensure_user(employee: Employee, password: str | None = None, username: str | None = None) -> User:
    if employee.user_id:
        user = employee.user
        user.is_active = employee.is_active
        user.save(update_fields=["is_active"])
        return user

    if not employee.pk:
        raise ValueError("Employee must be saved before creating a user.")

    desired_username = username or default_username(employee)
    if User.objects.filter(username=desired_username).exists():
        raise ValidationError(f"Логин «{desired_username}» уже занят.")

    raw_password = password or DEFAULT_EMPLOYEE_PASSWORD
    user = User.objects.create_user(
        username=desired_username,
        email=employee.email,
        password=raw_password,
        is_active=employee.is_active,
    )
    employee.user = user
    employee.admin_visible_password = raw_password
    employee.save(update_fields=["user", "admin_visible_password"])
    return user


def update_username(employee: Employee, new_username: str) -> User:
    if not employee.user_id:
        raise ValidationError("У сотрудника нет учётной записи.")
    if User.objects.filter(username=new_username).exclude(pk=employee.user_id).exists():
        raise ValidationError(f"Логин «{new_username}» уже занят.")
    user = employee.user
    user.username = new_username
    user.save(update_fields=["username"])
    return user


def provision_employee(
    employee: Employee,
    *,
    password: str | None = None,
    username: str | None = None,
    issue_key: bool = True,
) -> Employee:
    if not employee.pk:
        raise ValueError("Employee must be saved before provisioning.")

    ensure_user(employee, password=password, username=username)

    employee.must_change_password = _should_require_password_change(password)
    employee.save(update_fields=["must_change_password"])

    if issue_key:
        _, raw_key = issue_api_key(employee)
        employee.admin_visible_api_key = raw_key
        employee.save(update_fields=["admin_visible_api_key"])

    return employee


def complete_first_login(employee: Employee) -> str:
    new_password = reset_password(employee, random_password=True)
    employee.must_change_password = False
    employee.save(update_fields=["must_change_password"])
    return new_password


def reset_password(employee: Employee, *, random_password: bool = True) -> str:
    if not employee.user_id:
        provision_employee(employee, issue_key=False)

    new_password = (
        get_random_string(12) if random_password else DEFAULT_EMPLOYEE_PASSWORD
    )
    user = employee.user
    user.set_password(new_password)
    user.save(update_fields=["password"])
    employee.admin_visible_password = new_password
    update_fields = ["admin_visible_password"]
    if not random_password:
        employee.must_change_password = True
        update_fields.append("must_change_password")
    employee.save(update_fields=update_fields)
    return new_password


def rotate_api_key(employee: Employee) -> str:
    if not employee.user_id:
        ensure_user(employee)
    _, raw_key = EmployeeApiKey.generate(employee)
    employee.admin_visible_api_key = raw_key
    employee.save(update_fields=["admin_visible_api_key"])
    return raw_key


def rotate_auth_token(user: User) -> Token:
    Token.objects.filter(user=user).delete()
    return Token.objects.create(user=user)


def ensure_token(user: User) -> Token:
    token, _ = Token.objects.get_or_create(user=user)
    return token


def issue_api_key(employee: Employee) -> tuple[EmployeeApiKey, str]:
    if not employee.user_id:
        ensure_user(employee)
    obj, raw_key = EmployeeApiKey.generate(employee)
    employee.admin_visible_api_key = raw_key
    employee.save(update_fields=["admin_visible_api_key"])
    return obj, raw_key


def revoke_api_key(employee: Employee) -> None:
    EmployeeApiKey.objects.filter(employee=employee).update(is_active=False)
