from django.urls import path

from retail_points.views.retail_point import (
    above_avg_revenue,
    retail_point_detail,
    retail_points,
)

urlpatterns = [
    path("", retail_points, name="retail-points"),
    path("above-avg-revenue/", above_avg_revenue, name="above-avg-revenue"),
    path("<int:pk>/", retail_point_detail, name="retail-point-detail"),
]
