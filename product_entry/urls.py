
from django.urls import path

from . import views


app_name = "product_entry"

urlpatterns = [
    path(
        "",
        views.dashboard,
        name="dashboard",
    ),
]
