
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "accounts"

urlpatterns = [
    path("", views.application_home_view, name="home"),
    # =========================
    # User Management
    # =========================
    path("users/", views.user_list_view, name="user_list"),

    # Create user
    path(
        "users/modal/create/",
        views.user_modal_form_view,
        name="user_modal_create",
    ),

    # Edit user
    path(
        "users/modal/<int:user_id>/edit/",
        views.user_modal_form_view,
        name="user_modal_edit",
    ),

    # Activate / deactivate user
    path(
        "users/<int:user_id>/toggle-active/",
        views.user_toggle_active_view,
        name="user_toggle_active",
    ),

    # =========================
    # Group Management
    # =========================
    path("groups/", views.group_list_view, name="group_list"),

    # Create group
    path(
        "groups/modal/create/",
        views.group_modal_form_view,
        name="group_modal_create",
    ),

    # Edit group
    path(
        "groups/modal/<int:group_id>/edit/",
        views.group_modal_form_view,
        name="group_modal_edit",
    ),

    # View / update group members
    path(
        "groups/<int:group_id>/members/",
        views.group_members_view,
        name="group_members",
    ),

    # Delete group
    path(
        "groups/<int:group_id>/delete/",
        views.group_delete_view,
        name="group_delete",
    ),
    path(
    "groups/<int:group_id>/permissions/",
    views.group_permissions_view,
    name="group_permissions",
    ),
    # =========================
# Authentication
# =========================
path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
]
