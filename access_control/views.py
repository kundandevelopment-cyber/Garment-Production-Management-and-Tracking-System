import re

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
import json

from django.core.exceptions import ValidationError
from django.db import transaction

from .decorators import module_required, action_required
from .forms import MenuForm, ActionForm
from .models import (
    Action,
    GroupPermission,
    Menu,
    Module,
    UserPermission,
)
from django.contrib.auth.models import Group
from .services import (
    get_accessible_modules,
    get_accessible_menus,
    get_accessible_actions,
    get_access_control_dashboard_stats,
    user_has_module_access,
    user_has_menu_access,
)
from .utils import get_pagination_data, paginate_queryset


@module_required("access_control")
def access_control_home(request):
    stats = get_access_control_dashboard_stats()

    return render(
        request,
        "access_control/home.html",
        {
            "dashboard": stats,
        },
    )

@action_required("access_control", "modules", "view_modules")
def module_management_page(request):
    return render(
        request,
        "access_control/module_list.html",
    )
@action_required(
    "access_control",
    "menus",
    "view",
)
def menu_management_page(request, module_id):
    module = get_object_or_404(
        Module,
        id=module_id,
        is_active=True,
    )

    modules = Module.objects.filter(
        is_active=True,
    ).order_by(
        "sort_order",
        "name",
    )

    return render(
        request,
        "access_control/menu_list.html",
        {
            "module": module,
            "modules": modules,
        },
    )
@action_required(
    "access_control",
    "actions",
    "view_actions",
)
def action_management_page(request, module_id, menu_id):
    module = get_object_or_404(
        Module,
        id=module_id,
        is_active=True,
    )

    menu = get_object_or_404(
        Menu,
        id=menu_id,
        module=module,
        is_active=True,
    )

    return render(
        request,
        "access_control/action_list.html",
        {
            "module": module,
            "menu": menu,
        },
    )

@action_required("access_control", "modules", "create_module")
def module_create_view(request):
    errors = {}

    form_data = {
        "name": "",
        "code": "",
        "description": "",
        "sort_order": "0",
        "is_active": True,
    }

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        form_data["name"] = request.POST.get("name", "").strip()
        form_data["code"] = request.POST.get("code", "").strip()
        form_data["description"] = request.POST.get("description", "").strip()
        form_data["sort_order"] = request.POST.get("sort_order", "0").strip()
        form_data["is_active"] = request.POST.get("is_active") == "on"

        # Validate module name
        if not form_data["name"]:
            errors["name"] = "Module name is required."
        elif len(form_data["name"]) > 100:
            errors["name"] = "Module name cannot exceed 100 characters."
        elif Module.objects.filter(name__iexact=form_data["name"]).exists():
            errors["name"] = "A module with this name already exists."

        # Validate module code
        if not form_data["code"]:
            errors["code"] = "Module code is required."
        elif len(form_data["code"]) > 100:
            errors["code"] = "Module code cannot exceed 100 characters."
        elif not re.fullmatch(r"[a-zA-Z0-9_-]+", form_data["code"]):
            errors["code"] = (
                "Use only letters, numbers, hyphens, and underscores."
            )
        elif Module.objects.filter(code__iexact=form_data["code"]).exists():
            errors["code"] = "A module with this code already exists."

        # Validate sort order
        sort_order = None

        try:
            sort_order = int(form_data["sort_order"])

            if sort_order < 0:
                errors["sort_order"] = "Sort order cannot be negative."

        except (TypeError, ValueError):
            errors["sort_order"] = "Enter a valid whole number."

        # AJAX validation response
        if errors:
            if is_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "errors": errors,
                    },
                    status=400,
                )

        else:
            Module.objects.create(
                name=form_data["name"],
                code=form_data["code"],
                description=form_data["description"],
                sort_order=sort_order,
                is_active=form_data["is_active"],
            )

            if is_ajax:
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Module created successfully.",
                    },
                    status=201,
                )

            return redirect("access_control:module_management")

    return render(
        request,
        "access_control/module_create.html",
        {
            "errors": errors,
            "form_data": form_data,
        },
    )


@module_required("access_control")
def module_list_view(request):
    status = request.GET.get("status", "active").strip().lower()

    if status not in ["active", "inactive", "all"]:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid status filter.",
                "allowed_values": ["active", "inactive", "all"],
            },
            status=400,
        )

    if status == "active":
        modules = Module.objects.filter(
            is_active=True,
        )

    elif status == "inactive":
        modules = Module.objects.filter(
            is_active=False,
        )

    else:
        modules = Module.objects.all()

    if not request.user.is_superuser:
        direct_permission_module_ids = UserPermission.objects.filter(
            user=request.user,
            module__isnull=False,
        ).values_list(
            "module_id",
            flat=True,
        )

        group_permission_module_ids = GroupPermission.objects.filter(
            group__in=request.user.groups.all(),
            module__isnull=False,
        ).values_list(
            "module_id",
            flat=True,
        )

        permitted_module_ids = direct_permission_module_ids.union(
            group_permission_module_ids,
        )

        modules = modules.filter(
            pk__in=permitted_module_ids,
        )

    search_query = request.GET.get("search", "").strip()

    if search_query:
        modules = modules.filter(
            Q(name__icontains=search_query)
            | Q(code__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    sort_by = request.GET.get("sort_by", "").strip()
    sort_dir = request.GET.get("sort_dir", "asc").strip().lower()

    allowed_sort_fields = {
        "name": "name",
        "description": "description",
        "sort_order": "sort_order",
        "is_active": "is_active",
    }

    if sort_by:
        if sort_by not in allowed_sort_fields:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid sorting field.",
                    "allowed_values": list(allowed_sort_fields.keys()),
                },
                status=400,
            )

        if sort_dir not in ["asc", "desc"]:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid sorting direction.",
                    "allowed_values": ["asc", "desc"],
                },
                status=400,
            )

        sort_field = allowed_sort_fields[sort_by]

        if sort_dir == "desc":
            sort_field = f"-{sort_field}"

        secondary_sort = (
            "sort_order" if sort_by == "name" else "name"
        )

        modules = modules.order_by(
            sort_field,
            secondary_sort,
        )

    else:
        # Preserve existing default sorting
        modules = modules.order_by(
            "sort_order",
            "name",
        )

    page_obj, _ = paginate_queryset(
        modules,
        page_number=request.GET.get("page", 1),
        page_size=request.GET.get("page_size", 20),
    )

    module_data = [
        {
            "id": module.id,
            "name": module.name,
            "code": module.code,
            "description": module.description,
            "sort_order": module.sort_order,
            "is_active": module.is_active,
        }
        for module in page_obj
    ]

    return JsonResponse({
        "success": True,
        "data": {
            "modules": module_data,
            "pagination": get_pagination_data(page_obj),
        },
    })

@login_required
def menu_list_view(request, module_id):

    module = Module.objects.filter(
        id=module_id,
        is_active=True,
    ).first()

    if module is None:
        return JsonResponse(
            {
                "success": False,
                "message": "Module not found.",
            },
            status=404,
        )

    # Check module-level access
    can_view_inactive = (
        request.user.is_superuser
        or user_has_module_access(request.user, module)
    )

    # Get menus accessible to the current user
    accessible_menus = get_accessible_menus(
        request.user,
        module,
    )

    # Users must have module-level or scoped menu access
    if not can_view_inactive and not accessible_menus.exists():
        return JsonResponse(
            {
                "success": False,
                "message": "You do not have permission to view these menus.",
            },
            status=403,
        )

    # Status filtering
    status = request.GET.get(
        "status",
        "active",
    ).strip().lower()

    if status not in ["active", "inactive", "all"]:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid status filter.",
            },
            status=400,
        )

    # Sorting
    sort_by = request.GET.get(
        "sort_by",
        "sort_order",
    ).strip().lower()

    sort_dir = request.GET.get(
        "sort_dir",
        "asc",
    ).strip().lower()

    allowed_sort_fields = [
        "name",
        "code",
        "sort_order",
    ]

    if sort_by not in allowed_sort_fields:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid sort field.",
            },
            status=400,
        )

    if sort_dir not in ["asc", "desc"]:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid sort direction.",
            },
            status=400,
        )

    # Apply status filtering
    if status == "active":
        menus = accessible_menus

    elif status == "inactive":
        if not can_view_inactive:
            menus = Menu.objects.none()
        else:
            menus = Menu.objects.filter(
                module=module,
                is_active=False,
            )

    else:  # all
        if not can_view_inactive:
            menus = accessible_menus
        else:
            menus = Menu.objects.filter(
                module=module,
            )

    # Search
    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    if search_query:
        menus = menus.filter(
            Q(name__icontains=search_query)
            | Q(code__icontains=search_query)
        )

    # Sorting
    sort_prefix = "-" if sort_dir == "desc" else ""

    sort_field_map = {
        "name": "name",
        "code": "code",
        "sort_order": "sort_order",
    }

    menus = menus.select_related("parent").order_by(
        f"{sort_prefix}{sort_field_map[sort_by]}",
        "name",
        "id",
    )

    # Pagination
    page_obj, _ = paginate_queryset(
        menus,
        page_number=request.GET.get("page", 1),
        page_size=request.GET.get("page_size", 20),
    )

    # Response data
    menu_data = [
    {
        "id": menu.id,
        "name": menu.name,
        "code": menu.code,
        "url_name": menu.url_name,
        "parent_id": menu.parent_id,
        "description": menu.description,
        "sort_order": menu.sort_order,
        "is_active": menu.is_active,
    }
    for menu in page_obj
    ]

    return JsonResponse({
        "success": True,
        "data": {
            "module": {
                "id": module.id,
                "name": module.name,
                "code": module.code,
                "sort_order": module.sort_order,
            },
            "menus": menu_data,
            "pagination": get_pagination_data(page_obj),
        },
    })

@login_required
def action_list_view(request, module_id, menu_id):

    module = Module.objects.filter(
        id=module_id,
        is_active=True,
    ).first()

    if module is None:
        return JsonResponse(
            {
                "success": False,
                "message": "Module not found.",
            },
            status=404,
        )

    menu = Menu.objects.filter(
        id=menu_id,
        module=module,
        is_active=True,
    ).first()

    if menu is None:
        return JsonResponse(
            {
                "success": False,
                "message": "Menu not found.",
            },
            status=404,
        )

    if not user_has_menu_access(request.user, menu):
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "You do not have permission to view "
                    "actions for this menu."
                ),
            },
            status=403,
        )

    # Status filtering
    status = request.GET.get(
        "status",
        "active",
    ).strip().lower()

    if status not in ["active", "inactive", "all"]:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid status filter.",
            },
            status=400,
        )

    # Sorting
    sort_by = request.GET.get(
        "sort_by",
        "sort_order",
    ).strip().lower()

    sort_dir = request.GET.get(
        "sort_dir",
        "asc",
    ).strip().lower()

    allowed_sort_fields = [
        "name",
        "code",
        "sort_order",
    ]

    if sort_by not in allowed_sort_fields:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid sort field.",
            },
            status=400,
        )

    if sort_dir not in ["asc", "desc"]:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid sort direction.",
            },
            status=400,
        )

    # Inactive record access
    can_view_inactive = (
        request.user.is_superuser
        or user_has_module_access(request.user, module)
    )

    if status == "active":
        actions = get_accessible_actions(
            request.user,
            menu,
        )

    elif status == "inactive":
        if not can_view_inactive:
            actions = Action.objects.none()
        else:
            actions = Action.objects.filter(
                menu=menu,
                is_active=False,
            )

    else:
        if not can_view_inactive:
            actions = get_accessible_actions(
                request.user,
                menu,
            )
        else:
            actions = Action.objects.filter(
                menu=menu,
            )

    # Search
    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    if search_query:
        actions = actions.filter(
            Q(name__icontains=search_query)
            | Q(code__icontains=search_query)
        )

    # Sorting
    sort_prefix = "-" if sort_dir == "desc" else ""

    sort_field_map = {
        "name": "name",
        "code": "code",
        "sort_order": "sort_order",
    }

    actions = actions.order_by(
        f"{sort_prefix}{sort_field_map[sort_by]}",
        "name",
        "id",
    )

    # Pagination
    page_obj, _ = paginate_queryset(
        actions,
        page_number=request.GET.get("page", 1),
        page_size=request.GET.get("page_size", 20),
    )

    # Response
    return JsonResponse({
        "success": True,
        "data": {
            "menu": {
                "id": menu.id,
                "name": menu.name,
                "code": menu.code,
                "sort_order": menu.sort_order,
            },
            "actions": [
                {
                    "id": action.id,
                    "name": action.name,
                    "code": action.code,
                    "description": action.description,
                    "sort_order": action.sort_order,
                    "is_active": action.is_active,
                }
                for action in page_obj
            ],
            "pagination": get_pagination_data(page_obj),
        },
    })

@require_POST
@action_required(
    "access_control",
    "actions",
    "create_action",
)
def action_create_view(request, module_id, menu_id):
    module = get_object_or_404(
        Module,
        id=module_id,
        is_active=True,
    )

    menu = get_object_or_404(
        Menu,
        id=menu_id,
        module=module,
        is_active=True,
    )

    form = ActionForm(
        request.POST,
        menu=menu,
    )
    

    if form.is_valid():
        action = form.save(commit=False)

        # Always enforce the menu selected by the URL.
        action.menu = menu
        action.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Action created successfully.",
                "data": {
                    "id": action.id,
                    "menu_id": action.menu_id,
                    "name": action.name,
                    "code": action.code,
                    "description": action.description,
                    "sort_order": action.sort_order,
                    "is_active": action.is_active,
                },
            },
            status=201,
        )

    errors = {
        field: " ".join(
            error["message"]
            for error in error_list
        )
        for field, error_list in form.errors.get_json_data().items()
    }

    return JsonResponse(
        {
            "success": False,
            "errors": errors,
        },
        status=400,
    )

@require_POST
@action_required(
    "access_control",
    "actions",
    "update_action",
)
def action_edit_view(request, module_id, menu_id, action_id):
    module = get_object_or_404(
        Module,
        id=module_id,
        is_active=True,
    )

    menu = get_object_or_404(
        Menu,
        id=menu_id,
        module=module,
        is_active=True,
    )

    action = get_object_or_404(
    Action,
    id=action_id,
    menu=menu,
)

    form = ActionForm(
        request.POST,
        instance=action,
        menu=menu,
    )

    if form.is_valid():
        updated_action = form.save(commit=False)

        # Always preserve the menu selected by the URL.
        updated_action.menu = menu
        updated_action.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Action updated successfully.",
                "data": {
                    "id": updated_action.id,
                    "menu_id": updated_action.menu_id,
                    "name": updated_action.name,
                    "code": updated_action.code,
                    "description": updated_action.description,
                    "sort_order": updated_action.sort_order,
                    "is_active": updated_action.is_active,
                },
            },
            status=200,
        )

    errors = {
        field: " ".join(
            error["message"]
            for error in error_list
        )
        for field, error_list in form.errors.get_json_data().items()
    }

    return JsonResponse(
        {
            "success": False,
            "errors": errors,
        },
        status=400,
    )


@login_required
@require_POST
@action_required(
    "access_control",
    "actions",
    "delete_action",
)
def action_delete_view(request, module_id, menu_id, action_id):
    module = get_object_or_404(
        Module,
        id=module_id,
        is_active=True,
    )

    menu = get_object_or_404(
        Menu,
        id=menu_id,
        module=module,
    )

    action = get_object_or_404(
        Action,
        id=action_id,
        menu=menu,
    )

    # Check group permission assignments.
    group_permissions_count = GroupPermission.objects.filter(
        action=action,
    ).count()

    # Check individual user permission assignments.
    user_permissions_count = UserPermission.objects.filter(
        action=action,
    ).count()

    total_assignments = (
        group_permissions_count + user_permissions_count
    )

    if total_assignments:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "This action cannot be deleted because it has "
                    f"{group_permissions_count} group permission "
                    f"assignment(s) and {user_permissions_count} "
                    "user permission assignment(s). "
                    "Remove the permission assignments first."
                ),
            },
            status=409,
        )

    action_name = action.name
    action.delete()

    return JsonResponse(
        {
            "success": True,
            "message": (
                f'Action "{action_name}" deleted successfully.'
            ),
        },
        status=200,
    )


@action_required("access_control", "modules", "update_module")
def module_edit_view(request, module_id):
    module = get_object_or_404(Module, id=module_id)

    errors = {}

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    form_data = {
        "name": module.name,
        "code": module.code,
        "description": module.description,
        "sort_order": str(module.sort_order),
        "is_active": module.is_active,
    }

    if request.method == "POST":
        form_data["name"] = request.POST.get("name", "").strip()
        form_data["code"] = request.POST.get("code", "").strip()
        form_data["description"] = request.POST.get("description", "").strip()
        form_data["sort_order"] = request.POST.get("sort_order", "0").strip()
        form_data["is_active"] = request.POST.get("is_active") == "on"

        # Protect the core Access Control module
        if module.code == "access_control" and not form_data["is_active"]:
            errors["is_active"] = (
                "The Access Control module cannot be deactivated."
            )

        # Validate module name
        if not form_data["name"]:
            errors["name"] = "Module name is required."
        elif len(form_data["name"]) > 100:
            errors["name"] = "Module name cannot exceed 100 characters."
        elif Module.objects.filter(
            name__iexact=form_data["name"]
        ).exclude(id=module.id).exists():
            errors["name"] = "A module with this name already exists."

        # Validate module code
        if not form_data["code"]:
            errors["code"] = "Module code is required."
        elif len(form_data["code"]) > 100:
            errors["code"] = "Module code cannot exceed 100 characters."
        elif not re.fullmatch(r"[a-zA-Z0-9_-]+", form_data["code"]):
            errors["code"] = (
                "Use only letters, numbers, hyphens, and underscores."
            )
        elif Module.objects.filter(
            code__iexact=form_data["code"]
        ).exclude(id=module.id).exists():
            errors["code"] = "A module with this code already exists."

        # Validate sort order
        sort_order = None

        try:
            sort_order = int(form_data["sort_order"])

            if sort_order < 0:
                errors["sort_order"] = "Sort order cannot be negative."

        except (TypeError, ValueError):
            errors["sort_order"] = "Enter a valid whole number."

        # AJAX validation response
        if errors:
            if is_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "errors": errors,
                    },
                    status=400,
                )

        else:
            module.name = form_data["name"]
            module.code = form_data["code"]
            module.description = form_data["description"]
            module.sort_order = sort_order
            module.is_active = form_data["is_active"]
            module.save()

            if is_ajax:
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Module updated successfully.",
                    },
                    status=200,
                )

            return redirect("access_control:module_management")

    return render(
        request,
        "access_control/module_create.html",
        {
            "module": module,
            "form_data": form_data,
            "errors": errors,
            "is_edit": True,
        },
    )


@action_required(
    "access_control",
    "menus",
    "create_menu",
)
def menu_create_view(request, module_id):

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "Only POST requests are allowed.",
            },
            status=405,
        )

    module = get_object_or_404(
        Module,
        id=module_id,
        is_active=True,
    )

    form = MenuForm(
        request.POST,
        module=module,
    )

    if form.is_valid():

        menu = form.save(commit=False)

        # Always enforce the module selected by the URL.
        menu.module = module
        menu.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Menu created successfully.",
                "data": {
                    "id": menu.id,
                    "name": menu.name,
                    "code": menu.code,
                    "url_name": menu.url_name,
                    "parent_id": menu.parent_id,
                    "parent_name": menu.parent.name if menu.parent else None,
                    "description": menu.description,
                    "sort_order": menu.sort_order,
                    "is_active": menu.is_active,
                },
            },
            status=201,
        )

    errors = {
        field: " ".join(
            error["message"]
            for error in error_list
        )
        for field, error_list in form.errors.get_json_data().items()
    }

    return JsonResponse(
        {
            "success": False,
            "errors": errors,
        },
        status=400,
    )


@login_required
@require_POST
@action_required("access_control", "menus", "update_menu")
def menu_edit_view(request, module_id, menu_id):
    module = get_object_or_404(
        Module,
        id=module_id,
        is_active=True,
    )

    menu = get_object_or_404(
        Menu,
        id=menu_id,
        module=module,
    )

    form = MenuForm(
        request.POST,
        module=module,
        instance=menu,
    )

    if form.is_valid():
        updated_menu = form.save(commit=False)
        updated_menu.module = module
        updated_menu.save()

        return JsonResponse({
            "success": True,
            "message": "Menu updated successfully.",
            "data": {
                    "id": updated_menu.id,
                    "name": updated_menu.name,
                    "code": updated_menu.code,
                    "url_name": updated_menu.url_name,
                    "parent_id": updated_menu.parent_id,
                    "parent_name": (
                        updated_menu.parent.name
                        if updated_menu.parent
                        else None
                    ),
                    "description": updated_menu.description,
                    "sort_order": updated_menu.sort_order,
                    "is_active": updated_menu.is_active,
                },
        }, status=200)

    return JsonResponse({
        "success": False,
        "errors": form.errors,
    }, status=400)

@login_required
@require_POST
@action_required("access_control", "menus", "delete_menu")
def menu_delete_view(request, module_id, menu_id):
    module = get_object_or_404(
        Module,
        id=module_id,
        is_active=True,
    )

    menu = get_object_or_404(
        Menu,
        id=menu_id,
        module=module,
    )

    # Prevent deleting a menu that contains child menus.
    child_menus_count = Menu.objects.filter(
        parent=menu,
    ).count()

    if child_menus_count:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "This menu cannot be deleted because it contains "
                    f"{child_menus_count} child menu(s). "
                    "Remove or move the child menus first."
                ),
            },
            status=409,
        )

    # Prevent deleting a menu that has linked actions.
    linked_actions_count = Action.objects.filter(
        menu=menu,
    ).count()

    if linked_actions_count:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "This menu cannot be deleted because it contains "
                    f"{linked_actions_count} action(s). "
                    "Remove the linked actions first."
                ),
            },
            status=409,
        )

    # Prevent deleting a menu assigned to groups.
    group_permissions_count = GroupPermission.objects.filter(
        menu=menu,
    ).count()

    # Prevent deleting a menu assigned directly to users.
    user_permissions_count = UserPermission.objects.filter(
        menu=menu,
    ).count()

    if group_permissions_count or user_permissions_count:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "This menu cannot be deleted because it has "
                    f"{group_permissions_count} group permission "
                    f"assignment(s) and {user_permissions_count} "
                    "direct user permission assignment(s). "
                    "Remove these permission assignments first."
                ),
                "data": {
                    "group_permissions_count": group_permissions_count,
                    "user_permissions_count": user_permissions_count,
                },
            },
            status=409,
        )

    menu_name = menu.name
    menu.delete()

    return JsonResponse(
        {
            "success": True,
            "message": f'Menu "{menu_name}" deleted successfully.',
        },
        status=200,
    )

@login_required
@module_required("access_control")
def group_permission_list_view(request, group_id):
    group = get_object_or_404(
        Group,
        id=group_id,
    )

    permissions = GroupPermission.objects.filter(
        group=group,
    ).select_related(
        "module",
        "menu",
        "action",
    ).order_by("id")

    permission_data = []

    for permission in permissions:
        target_type = None
        target_id = None
        target_name = None

        if permission.module_id:
            target_type = "module"
            target_id = permission.module_id
            target_name = permission.module.name

        elif permission.menu_id:
            target_type = "menu"
            target_id = permission.menu_id
            target_name = permission.menu.name

        elif permission.action_id:
            target_type = "action"
            target_id = permission.action_id
            target_name = permission.action.name

        permission_data.append({
            "id": permission.id,
            "target_type": target_type,
            "target_id": target_id,
            "target_name": target_name,
        })

    return JsonResponse({
        "success": True,
        "data": {
            "group": {
                "id": group.id,
                "name": group.name,
            },
            "permissions": permission_data,
            "total_permissions": len(permission_data),
        },
    })

@login_required
@require_POST
@module_required("access_control")
def group_permission_update_view(request, group_id):
    group = get_object_or_404(
        Group,
        id=group_id,
    )

    try:
        payload = json.loads(request.body)

    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({
            "success": False,
            "message": "Invalid JSON payload.",
        }, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({
            "success": False,
            "message": "JSON body must be an object.",
        }, status=400)

    permissions_data = payload.get("permissions")

    if not isinstance(permissions_data, list):
        return JsonResponse({
            "success": False,
            "message": "Permissions must be a list.",
        }, status=400)

    allowed_types = {"module", "menu", "action"}

    # Validate the entire payload before changing existing assignments.
    permission_objects = []
    seen_targets = set()

    for index, item in enumerate(permissions_data):

        if not isinstance(item, dict):
            return JsonResponse({
                "success": False,
                "message": f"Permission at index {index} must be an object.",
            }, status=400)

        target_type = item.get("target_type")
        target_id = item.get("target_id")

        if target_type not in allowed_types:
            return JsonResponse({
                "success": False,
                "message": f"Invalid target_type at index {index}.",
            }, status=400)

        # Reject booleans, strings, floats, zero, and negative IDs.
        if type(target_id) is not int or target_id <= 0:
            return JsonResponse({
                "success": False,
                "message": f"Invalid target_id at index {index}.",
            }, status=400)

        target_key = (target_type, target_id)

        if target_key in seen_targets:
            return JsonResponse({
                "success": False,
                "message": f"Duplicate permission at index {index}.",
            }, status=400)

        seen_targets.add(target_key)

        # Resolve the target and build the permission instance.
        try:
            if target_type == "module":
                target = Module.objects.get(
                    id=target_id,
                )
                permission = GroupPermission(
                    group=group,
                    module=target,
                )

            elif target_type == "menu":
                target = Menu.objects.select_related(
                    "module",
                ).get(
                    id=target_id,
                )
                permission = GroupPermission(
                    group=group,
                    menu=target,
                )

            else:
                target = Action.objects.select_related(
                    "menu",
                    "menu__module",
                ).get(
                    id=target_id,
                )
                permission = GroupPermission(
                    group=group,
                    action=target,
                )

        except (Module.DoesNotExist, Menu.DoesNotExist, Action.DoesNotExist):
            return JsonResponse({
                "success": False,
                "message": f"Target not found at index {index}.",
            }, status=400)

        # Run model-level validation, including inactive target checks.
        try:
            permission.full_clean()

        except ValidationError as exc:
            return JsonResponse({
                "success": False,
                "message": f"Invalid permission at index {index}.",
                "errors": exc.message_dict if hasattr(exc, "message_dict") else exc.messages,
            }, status=400)

        permission_objects.append(permission)

    # All assignments are valid. Replace existing permissions atomically.
    try:
        with transaction.atomic():
            GroupPermission.objects.filter(
                group=group,
            ).delete()

            GroupPermission.objects.bulk_create(
                permission_objects,
            )

    except Exception:
        return JsonResponse({
            "success": False,
            "message": "Failed to update group permissions.",
        }, status=500)

    return JsonResponse({
        "success": True,
        "message": "Group permissions updated successfully.",
        "data": {
            "group": {
                "id": group.id,
                "name": group.name,
            },
            "total_permissions": len(permission_objects),
        },
    }, status=200)

@login_required
@module_required("access_control")
def group_permission_available_tree_view(request):
    modules = Module.objects.filter(
        is_active=True,
    ).order_by(
        "sort_order",
        "id",
    )

    permission_tree = []

    for module in modules:
        menus = Menu.objects.filter(
            module=module,
            is_active=True,
        ).order_by(
            "sort_order",
            "id",
        )

        menu_data = []

        for menu in menus:
            actions = Action.objects.filter(
                menu=menu,
                is_active=True,
            ).order_by(
                "sort_order",
                "id",
            )

            action_data = [
                {
                    "id": action.id,
                    "name": action.name,
                    "code": action.code,
                }
                for action in actions
            ]

            menu_data.append({
                "id": menu.id,
                "name": menu.name,
                "code": menu.code,
                "actions": action_data,
            })

        permission_tree.append({
            "id": module.id,
            "name": module.name,
            "code": module.code,
            "menus": menu_data,
        })

    return JsonResponse({
        "success": True,
        "data": {
            "modules": permission_tree,
            "total_modules": len(permission_tree),
        },
    })

@login_required
@module_required("access_control")
def group_permission_groups_view(request):
    groups = Group.objects.all().order_by("name", "id")

    group_data = [
        {
            "id": group.id,
            "name": group.name,
        }
        for group in groups
    ]

    return JsonResponse({
        "success": True,
        "data": {
            "groups": group_data,
            "total_groups": len(group_data),
        },
    })

@login_required
@module_required("access_control")
def group_permission_management_page(request):
    return render(
        request,
        "access_control/group_permission_management.html",
    )





