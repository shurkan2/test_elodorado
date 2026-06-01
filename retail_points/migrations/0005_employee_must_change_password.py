from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("retail_points", "0004_employee_credentials"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="must_change_password",
            field=models.BooleanField(
                default=False,
                verbose_name="Требуется смена пароля при первом входе",
            ),
        ),
        migrations.AlterField(
            model_name="employee",
            name="admin_visible_password",
            field=models.CharField(
                blank=True,
                help_text="Текущий пароль для входа в API (отображение для HR).",
                max_length=128,
                verbose_name="Пароль для входа (отображение)",
            ),
        ),
    ]
