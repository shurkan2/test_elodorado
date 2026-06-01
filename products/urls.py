from django.urls import path

from products.views.product import product_detail, products

urlpatterns = [
    path("", products, name="products"),
    path("<int:pk>/", product_detail, name="product-detail"),
]
