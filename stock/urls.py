from django.urls import path

from stock.views import dealer_stock_detail, dealer_stock_list

urlpatterns = [
    path("", dealer_stock_list, name="dealer-stock"),
    path("<int:pk>/", dealer_stock_detail, name="dealer-stock-detail"),
]
