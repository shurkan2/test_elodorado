from django.contrib import admin
from django.utils.html import format_html

from products.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("brand", "model", "price", "release_date")
    search_fields = ("brand", "model")
