from django.http import HttpResponse
from django.urls import path

from .decorators import action_required


@action_required(
    "decorator_module",
    "decorator_menu",
    "decorator_action",
)
def protected_action_view(request):
    return HttpResponse("Access granted")


urlpatterns = [
    path(
        "protected-action/",
        protected_action_view,
        name="test_protected_action",
    ),
]