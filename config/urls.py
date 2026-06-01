from django.contrib import admin
from django.urls import include, path

from access.views.login import api_login

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", api_login, name="api-login"),
    path("api/v1/points/", include("retail_points.urls")),
    path("api/v1/products/", include("products.urls")),
    path("api/v1/stock/", include("stock.urls")),
]
