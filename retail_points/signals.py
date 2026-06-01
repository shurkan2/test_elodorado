from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from access.services import employee_access
from retail_points.models import Employee, validate_head_single_employee


@receiver(post_save, sender=Employee)
def auto_provision_employee(sender, instance, created, **kwargs):
    import sys

    if "test" in sys.argv:
        return
    if not created or instance.user_id or not instance.is_active:
        return
    login, password = employee_access.demo_credentials_for_email(instance.email)
    employee_access.provision_employee(
        instance,
        password=password,
        username=login,
    )


@receiver(pre_save, sender=Employee)
def enforce_head_single_employee(sender, instance, **kwargs):
    if instance.retail_point_id:
        validate_head_single_employee(instance.retail_point, employee_pk=instance.pk)
