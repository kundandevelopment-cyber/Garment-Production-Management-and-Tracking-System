
from django.urls import path
from . import views

app_name = "access_control"

urlpatterns = [
    # =========================
    # Access Control Dashboard
    # =========================
    path(
        "",
        views.access_control_home,
        name="home",
    ),

    # =========================
    # Module Management
    # =========================
    path(
        "modules/manage/",
        views.module_management_page,
        name="module_management",
    ),
    path(
        "modules/",
        views.module_list_view,
        name="module_list",
    ),
    path(
        "modules/create/",
        views.module_create_view,
        name="module_create",
    ),
    path(
        "modules/<int:module_id>/edit/",
        views.module_edit_view,
        name="module_edit",
    ),

    # =========================
    # Menu Management - Pages
    # =========================
    path(
        "modules/<int:module_id>/menus/manage/",
        views.menu_management_page,
        name="menu_management",
    ),

    # =========================
    # Menu Management - List API
    # =========================
    path(
        "modules/<int:module_id>/menus/",
        views.menu_list_view,
        name="menu_list",
    ),

    # =========================
    # Menu Management - Create API
    # =========================
    path(
        "modules/<int:module_id>/menus/create/",
        views.menu_create_view,
        name="menu_create",
    ),

    # Menu Management - Edit API
    path(
        "modules/<int:module_id>/menus/<int:menu_id>/edit/",
        views.menu_edit_view,
        name="menu_edit",
    ),


    path(
        "modules/<int:module_id>/menus/<int:menu_id>/delete/",
        views.menu_delete_view,
        name="menu_delete",
    ),



    # =========================
    # Action Management - List API
    # =========================
    path(
        "modules/<int:module_id>/menus/<int:menu_id>/actions/",
        views.action_list_view,
        name="action_list",
    ),
    path(
        "modules/<int:module_id>/menus/<int:menu_id>/actions/create/",
        views.action_create_view,
        name="action_create",
    ),
    path(
        "modules/<int:module_id>/menus/<int:menu_id>/actions/<int:action_id>/edit/",
        views.action_edit_view,
        name="action_edit",
    ),
    path(
        "modules/<int:module_id>/menus/<int:menu_id>/actions/<int:action_id>/delete/",
        views.action_delete_view,
        name="action_delete",
    ),
    # =========================
    # Action Management - Page
    # =========================
    path(
        "modules/<int:module_id>/menus/<int:menu_id>/actions/manage/",
        views.action_management_page,
        name="action_management",
    ),
        # =========================
    # Group Permission Management - List API
    # =========================
    path(
        "group-permissions/groups/<int:group_id>/",
        views.group_permission_list_view,
        name="group_permission_list",
    ),
    path(
        "group-permissions/groups/<int:group_id>/update/",
        views.group_permission_update_view,
        name="group_permission_update",
    ),
    path(
        "group-permissions/available/",
        views.group_permission_available_tree_view,
        name="group_permission_available_tree",
    ),
    path(
        "group-permissions/groups/",
        views.group_permission_groups_view,
        name="group_permission_groups",
    ),
    path(
        "group-permissions/manage/",
        views.group_permission_management_page,
        name="group_permission_management",
    ),
 
]
