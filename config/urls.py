
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),

    path(
        '',
        RedirectView.as_view(
            pattern_name='access_control:home',
            permanent=False,
        ),
        name='home',
    ),

    path(
        'access-control/',
        include('access_control.urls'),
    ),

    path(
        'accounts/',
        include('accounts.urls'),
    ),
    path(
    'product-entry/',
    include('product_entry.urls'),
),
]
