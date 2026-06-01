import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from access.services import employee_access
from core.constants import PointType
from products.models import Product
from retail_points.models import Employee, RetailPoint, RetailPointAddress
from stock.models import DealerStock

User = get_user_model()

DEALER_CITIES = [
    ("Russia", "Moscow"),
    ("Russia", "Saint Petersburg"),
    ("Russia", "Kazan"),
    ("Russia", "Novosibirsk"),
    ("Russia", "Yekaterinburg"),
    ("Russia", "Samara"),
    ("Russia", "Rostov-on-Don"),
    ("Russia", "Krasnodar"),
    ("Russia", "Voronezh"),
    ("Russia", "Perm"),
    ("Russia", "Ufa"),
]

PRODUCTS = [
    ("Apple", "iPhone 15", "89990"),
    ("Apple", "MacBook Air M3", "129990"),
    ("Samsung", "Galaxy S24", "79990"),
    ("Samsung", "Galaxy Tab S9", "69990"),
    ("Sony", "WH-1000XM5", "34990"),
    ("LG", "OLED C4 55", "149990"),
    ("Xiaomi", "Redmi Note 13", "24990"),
    ("Huawei", "MatePad 11", "45990"),
    ("ASUS", "ROG Zephyrus G14", "159990"),
    ("Lenovo", "ThinkPad X1", "139990"),
    ("Dell", "XPS 15", "169990"),
    ("HP", "Pavilion 15", "64990"),
    ("Canon", "EOS R50", "89990"),
    ("Nikon", "Z50 II", "99990"),
    ("Bose", "QuietComfort Ultra", "32990"),
]

class Command(BaseCommand):
    help = "Заполнить базу начальными данными торговой сети"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Удалить существующие данные перед заполнением",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            DealerStock.objects.all().delete()
            Product.objects.all().delete()
            Employee.objects.all().delete()
            RetailPointAddress.objects.all().delete()
            RetailPoint.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin")
            self.stdout.write("Created superuser admin/admin")

        if not RetailPoint.objects.filter(point_type=PointType.HEAD).exists():
            head = RetailPoint.objects.create(
                name="Central Head Office",
                point_type=PointType.HEAD,
                daily_revenue=Decimal("0"),
            )
            RetailPointAddress.objects.create(
                retail_point=head,
                country="Russia",
                city="Moscow",
                street="Tverskaya",
                house_number="1",
            )
            Employee.objects.create(
                retail_point=head,
                full_name="Ivan Head Manager",
                phone="+79001112233",
                email="head@example.com",
                is_active=True,
            )
            self.stdout.write("Created head office")

        dealers = list(RetailPoint.objects.filter(point_type=PointType.DEALER))
        while len(dealers) < 10:
            idx = len(dealers) + 1
            country, city = DEALER_CITIES[idx % len(DEALER_CITIES)]
            dealer = RetailPoint.objects.create(
                name=f"Dealer Center {city} #{idx}",
                point_type=PointType.DEALER,
                daily_revenue=Decimal(str(random.randint(10000, 500000))),
            )
            RetailPointAddress.objects.create(
                retail_point=dealer,
                country=country,
                city=city,
                street=f"Trade Street {idx}",
                house_number=str(idx * 10),
            )
            Employee.objects.create(
                retail_point=dealer,
                full_name=f"Manager {idx}A",
                phone=f"+7900{idx:03d}00001",
                email=f"manager{idx}a@example.com",
                is_active=True,
            )
            Employee.objects.create(
                retail_point=dealer,
                full_name=f"Manager {idx}B",
                phone=f"+7900{idx:03d}00002",
                email=f"manager{idx}b@example.com",
                is_active=True,
            )
            dealers.append(dealer)

        if Product.objects.count() < len(PRODUCTS):
            for brand, model, price in PRODUCTS:
                Product.objects.get_or_create(
                    brand=brand,
                    model=model,
                    defaults={
                        "price": Decimal(price),
                        "release_date": "2024-01-15",
                    },
                )
            self.stdout.write("Created products")

        products = list(Product.objects.all())
        dealers = list(RetailPoint.objects.filter(point_type=PointType.DEALER))
        for dealer in dealers:
            sample = random.sample(products, k=min(8, len(products)))
            for product in sample:
                DealerStock.objects.get_or_create(
                    dealer=dealer,
                    product=product,
                    defaults={"quantity": random.randint(0, 30)},
                )

        for employee in Employee.objects.filter(user__isnull=True, is_active=True):
            login, password = employee_access.demo_credentials_for_email(employee.email)
            employee_access.provision_employee(
                employee,
                username=login,
                password=password,
            )

        self.stdout.write(self.style.SUCCESS("Начальные данные загружены"))
