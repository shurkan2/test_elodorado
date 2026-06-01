from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("retail_points", "0005_employee_must_change_password"),
    ]

    operations = [
        migrations.AlterField(
            model_name="employee",
            name="admin_visible_api_key",
            field=models.CharField(
                blank=True,
                help_text="Последний выданный ключ сотрудника.",
                max_length=128,
                verbose_name="API-ключ",
            ),
        ),
        migrations.AlterField(
            model_name="employee",
            name="admin_visible_password",
            field=models.CharField(
                blank=True,
                help_text="Текущий пароль для входа в API.",
                max_length=128,
                verbose_name="Пароль для входа",
            ),
        ),
    ]
