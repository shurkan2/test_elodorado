from django import forms
from django.contrib import admin, messages
from django.forms.models import BaseInlineFormSet
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone
from django.utils.formats import date_format
from rest_framework.authtoken.models import Token

from access.services import employee_access
from core.constants import ADMIN_ASYNC_CLEAR_THRESHOLD, PointType
from core.db import safe_db_operation
from core.exceptions import DatabaseOperationError
from retail_points.forms import EmployeeAdminForm
from retail_points.models import Employee, RetailPoint, RetailPointAddress
from retail_points.repo.retail_point_repo import RetailPointRepo
from retail_points.tasks import clear_daily_revenue_async


class RetailPointAddressInline(admin.StackedInline):
    model = RetailPointAddress
    can_delete = False
    extra = 0


class EmployeeInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if not self.instance or not self.instance.pk:
            return
        if self.instance.point_type != PointType.HEAD:
            return
        pending = sum(
            1
            for form in self.forms
            if hasattr(form, "cleaned_data")
            and not form.cleaned_data.get("DELETE")
            and (form.cleaned_data or form.instance.pk)
        )
        if pending > 1:
            raise forms.ValidationError(
                "У головного отдела уже есть сотрудник. "
                "Удалите текущего, затем добавьте нового."
            )


class EmployeeInline(admin.TabularInline):
    model = Employee
    formset = EmployeeInlineFormSet
    extra = 0
    fields = ("full_name", "email", "phone", "is_active")
    show_change_link = True

    def get_max_num(self, request, obj=None, **kwargs):
        if obj and obj.point_type == PointType.HEAD:
            return 1
        return super().get_max_num(request, obj, **kwargs)

    def get_extra(self, request, obj=None, **kwargs):
        if obj and obj.point_type == PointType.HEAD and obj.employees.exists():
            return 0
        return super().get_extra(request, obj, **kwargs)


@admin.register(RetailPoint)
class RetailPointAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "point_type", "daily_revenue", "city_display")
    readonly_fields = ("id",)
    list_filter = ("point_type",)
    inlines = (RetailPointAddressInline, EmployeeInline)
    actions = ("clear_daily_revenue",)

    @admin.display(description="Город")
    def city_display(self, obj):
        return obj.address.city if hasattr(obj, "address") else "—"

    @admin.action(description="Очистить суточную выручку")
    def clear_daily_revenue(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        if len(ids) > ADMIN_ASYNC_CLEAR_THRESHOLD:
            try:
                clear_daily_revenue_async.delay(ids)
            except Exception:
                self.message_user(
                    request,
                    "Не удалось поставить задачу в очередь. Проверьте доступность брокера сообщений.",
                    messages.ERROR,
                )
                return
            self.message_user(
                request,
                f"Очистка выручки поставлена в очередь для {len(ids)} точек.",
                messages.SUCCESS,
            )
            return

        try:
            with safe_db_operation(
                user_message="Не удалось очистить выручку. База данных недоступна. Попробуйте позже.",
            ):
                RetailPointRepo().clear_daily_revenue(ids)
            self.message_user(
                request,
                f"Суточная выручка очищена для {len(ids)} точек.",
                messages.SUCCESS,
            )
        except DatabaseOperationError as exc:
            self.message_user(request, exc.message, messages.ERROR)
        except Exception:
            self.message_user(request, "Произошла непредвиденная ошибка.", messages.ERROR)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    form = EmployeeAdminForm
    change_form_template = "admin/retail_points/employee/change_form.html"
    list_display = (
        "full_name",
        "retail_point",
        "is_active",
        "username_display",
        "admin_visible_password",
        "token_issued_at",
        "api_key_status",
    )
    list_filter = ("is_active", "retail_point__point_type")
    search_fields = ("full_name", "email", "phone", "user__username")
    exclude = ("user",)
    readonly_fields = (
        "auth_token_key",
        "token_issued_at",
        "last_login_display",
        "api_key_status",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "retail_point",
                    "full_name",
                    "phone",
                    "email",
                    "is_active",
                    "username",
                ),
            },
        ),
        (
            "Доступ к API",
            {
                "fields": (
                    "admin_visible_password",
                    "auth_token_key",
                    "token_issued_at",
                    "last_login_display",
                    "admin_visible_api_key",
                    "api_key_status",
                ),
            },
        ),
    )
    actions = (
        "rotate_auth_token_action",
        "issue_api_key_action",
        "revoke_api_key_action",
        "reset_password_action",
    )

    def get_urls(self):
        custom_urls = [
            path(
                "<int:object_id>/reset-password/",
                self.admin_site.admin_view(self.reset_password_view),
                name="retail_points_employee_reset_password",
            ),
            path(
                "<int:object_id>/rotate-api-key/",
                self.admin_site.admin_view(self.rotate_api_key_view),
                name="retail_points_employee_rotate_api_key",
            ),
        ]
        return custom_urls + super().get_urls()

    def reset_password_view(self, request, object_id):
        employee = self.get_object(request, object_id)
        if employee is None:
            self.message_user(request, "Сотрудник не найден.", messages.ERROR)
            return redirect("admin:retail_points_employee_changelist")
        try:
            new_password = employee_access.reset_password(employee, random_password=True)
            self.message_user(
                request,
                f"Новый пароль для «{employee.full_name}» ({employee.user.username}): {new_password}",
                messages.WARNING,
            )
        except Exception as exc:
            self.message_user(request, str(exc), messages.ERROR)
        return redirect("admin:retail_points_employee_change", object_id)

    def rotate_api_key_view(self, request, object_id):
        employee = self.get_object(request, object_id)
        if employee is None:
            self.message_user(request, "Сотрудник не найден.", messages.ERROR)
            return redirect("admin:retail_points_employee_changelist")
        try:
            raw_key = employee_access.rotate_api_key(employee)
            self.message_user(
                request,
                f"Новый API-ключ для «{employee.full_name}»: {raw_key}",
                messages.WARNING,
            )
        except Exception as exc:
            self.message_user(request, str(exc), messages.ERROR)
        return redirect("admin:retail_points_employee_change", object_id)

    @admin.display(description="Логин")
    def username_display(self, obj):
        if obj.user_id:
            return obj.user.username
        if obj.pk:
            return f"user{obj.pk} (не создан)"
        return "—"

    @admin.display(description="Токен авторизации")
    def auth_token_key(self, obj):
        if not obj.user_id:
            return "—"
        token = Token.objects.filter(user_id=obj.user_id).first()
        return token.key if token else "—"

    @admin.display(description="Последний вход / выдача токена")
    def token_issued_at(self, obj):
        if not obj.user_id:
            return "—"
        token = Token.objects.filter(user_id=obj.user_id).first()
        if not token:
            return "—"
        return date_format(timezone.localtime(token.created), "SHORT_DATETIME_FORMAT")

    @admin.display(description="Статус API-ключа")
    def api_key_status(self, obj):
        from access.models import EmployeeApiKey

        key = EmployeeApiKey.objects.filter(employee=obj).first()
        if not key:
            return "не выдан"
        if key.is_active:
            return "активен"
        return "отозван"

    @admin.display(description="Последний вход (учётная запись)")
    def last_login_display(self, obj):
        if not obj.user_id or not obj.user.last_login:
            return "—"
        return date_format(timezone.localtime(obj.user.last_login), "SHORT_DATETIME_FORMAT")

    def save_model(self, request, obj, form, change):
        username = form.cleaned_data.get("username", "").strip()
        super().save_model(request, obj, form, change)

        if not obj.user_id and obj.is_active:
            desired = username or employee_access.default_username(obj)
            employee_access.provision_employee(obj, username=desired)
        elif obj.user_id:
            obj.user.is_active = obj.is_active
            obj.user.save(update_fields=["is_active"])
            if username and username != obj.user.username:
                employee_access.update_username(obj, username)

    @admin.action(description="Сбросить пароль (случайный)")
    def reset_password_action(self, request, queryset):
        for employee in queryset:
            try:
                new_password = employee_access.reset_password(employee, random_password=True)
                login = employee.user.username if employee.user_id else "—"
                self.message_user(
                    request,
                    f"«{employee.full_name}» ({login}): {new_password}",
                    messages.WARNING,
                )
            except Exception as exc:
                self.message_user(
                    request,
                    f"«{employee.full_name}»: {exc}",
                    messages.ERROR,
                )

    @admin.action(description="Перевыпустить токен авторизации")
    def rotate_auth_token_action(self, request, queryset):
        for employee in queryset:
            if not employee.is_active:
                self.message_user(
                    request,
                    f"«{employee.full_name}»: сотрудник неактивен.",
                    messages.ERROR,
                )
                continue
            try:
                if not employee.user_id:
                    employee_access.provision_employee(employee, issue_key=False)
                token = employee_access.rotate_auth_token(employee.user)
                issued = date_format(
                    timezone.localtime(token.created),
                    "SHORT_DATETIME_FORMAT",
                )
                self.message_user(
                    request,
                    f"«{employee.full_name}» — токен (до 24 ч): {token.key} | выдан: {issued}",
                    messages.WARNING,
                )
            except Exception as exc:
                self.message_user(
                    request,
                    f"«{employee.full_name}»: {exc}",
                    messages.ERROR,
                )

    @admin.action(description="Выдать / перевыпустить API-ключ")
    def issue_api_key_action(self, request, queryset):
        for employee in queryset:
            if not employee.is_active:
                self.message_user(
                    request,
                    f"«{employee.full_name}»: сотрудник неактивен.",
                    messages.ERROR,
                )
                continue
            try:
                raw_key = employee_access.rotate_api_key(employee)
                self.message_user(
                    request,
                    f"«{employee.full_name}» — API-ключ: {raw_key}",
                    messages.WARNING,
                )
            except Exception as exc:
                self.message_user(
                    request,
                    f"«{employee.full_name}»: {exc}",
                    messages.ERROR,
                )

    @admin.action(description="Отозвать API-ключ")
    def revoke_api_key_action(self, request, queryset):
        for employee in queryset:
            employee_access.revoke_api_key(employee)
        self.message_user(request, "API-ключи отозваны.", messages.SUCCESS)
