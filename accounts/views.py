
import json

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from access_control.services import get_accessible_modules
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from django.core.exceptions import ValidationError


from access_control.decorators import module_required, action_required
from access_control.utils import paginate_queryset, get_pagination_data

from .models import User
from .forms import UserCreateForm, UserEditForm
from django.contrib.auth.models import Group
from django.db import transaction
from access_control.models import (
    Module,
    Menu,
    Action,
    GroupPermission,
)



@module_required("access_control")
def user_list_view(request):
    queryset = User.objects.all().order_by("username")

    # Search
    search = request.GET.get("search", "").strip()
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )

    # Status filter
    status = request.GET.get("status", "all").strip().lower()

    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)
    else:
        status = "all"

    # Pagination
    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 20)

    page_obj, paginator = paginate_queryset(
        queryset,
        page_number=page_number,
        page_size=page_size,
    )

    context = {
        "users": page_obj.object_list,
        "page_obj": page_obj,
        "pagination": get_pagination_data(page_obj),
        "search": search,
        "status": status,
    }

    return render(request, "accounts/user_list.html", context)


@module_required("access_control")
@require_http_methods(["POST"])
def user_modal_form_view(request, user_id=None):
    """
    Unified AJAX endpoint for creating and editing users.
    """

    target_user = None

    if user_id is not None:
        target_user = get_object_or_404(User, pk=user_id)

        form = UserEditForm(
            request.POST,
            instance=target_user,
        )
    else:
        form = UserCreateForm(request.POST)

    if form.is_valid():
        user = form.save()

        return JsonResponse({
            "success": True,
            "message": (
                f"User '{user.username}' "
                f"{'updated' if target_user else 'created'} successfully."
            ),
        })

    return JsonResponse({
        "success": False,
        "errors": form.errors,
    }, status=400)


@module_required("access_control")
@require_http_methods(["POST"])
def user_toggle_active_view(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)

    # Prevent deactivating superuser accounts.
    if target_user.is_superuser:
        return JsonResponse({
            "success": False,
            "message": "Superuser accounts cannot be deactivated through this interface.",
        }, status=403)

    # Prevent self-deactivation.
    if target_user.pk == request.user.pk:
        return JsonResponse({
            "success": False,
            "message": "You cannot deactivate your own account.",
        }, status=403)

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=["is_active"])

    status = "activated" if target_user.is_active else "deactivated"

    return JsonResponse({
        "success": True,
        "message": f"User '{target_user.username}' {status} successfully.",
        "is_active": target_user.is_active,
        "user_id": target_user.pk,
    })

@module_required("access_control")
def group_list_view(request):
    queryset = Group.objects.all().order_by("name")

    search = request.GET.get("search", "").strip()

    if search:
        queryset = queryset.filter(name__icontains=search)

    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 20)

    page_obj, paginator = paginate_queryset(
        queryset,
        page_number=page_number,
        page_size=page_size,
    )

    context = {
        "groups": page_obj.object_list,
        "page_obj": page_obj,
        "pagination": get_pagination_data(page_obj),
        "search": search,
    }

    return render(
        request,
        "accounts/group_list.html",
        context,
    )

@module_required("access_control")
def group_modal_form_view(request, group_id=None):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=405)

    group = None
    if group_id is not None:
        group = get_object_or_404(Group, pk=group_id)

    name = request.POST.get("name", "").strip()

    if not name:
        return JsonResponse(
            {"errors": {"name": ["Group name is required."]}},
            status=400,
        )

    if Group.objects.filter(name__iexact=name).exclude(
        pk=group.pk if group else None
    ).exists():
        return JsonResponse(
            {"errors": {"name": ["A group with this name already exists."]}},
            status=400,
        )

    if group:
        group.name = name
        group.save()
        message = "Group updated successfully."
    else:
        Group.objects.create(name=name)
        message = "Group created successfully."

    return JsonResponse({"success": True, "message": message})


@module_required("access_control")
def group_members_view(request, group_id):
    group = get_object_or_404(Group, pk=group_id)

    if request.method == "GET":
        users = User.objects.all().order_by("username")
        selected_user_ids = list(
            group.user_set.values_list("id", flat=True)
        )

        return JsonResponse({
            "users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.get_full_name(),
                    "selected": user.id in selected_user_ids,
                }
                for user in users
            ],
        })

    if request.method == "POST":
        user_ids = request.POST.getlist("user_ids")

        valid_users = User.objects.filter(id__in=user_ids)
        group.user_set.set(valid_users)

        return JsonResponse({
            "success": True,
            "message": "Group members updated successfully.",
        })

    return JsonResponse({"error": "Method not allowed."}, status=405)


@module_required("access_control")
@require_http_methods(["POST"])
def group_delete_view(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    group_name = group.name
    group.delete()

    return JsonResponse({
        "success": True,
        "message": f'Group "{group_name}" deleted successfully.',
    })



@action_required(
    "access_control",
    "permissions",
    "manage_group_permissions",
)
def group_permissions_view(request, group_id):
    group = get_object_or_404(Group, pk=group_id)

    # ==========================================
    # GET: Build permission assignment tree
    # ==========================================

    if request.method == "GET":

        modules = Module.objects.filter(
            is_active=True,
        ).order_by(
            "sort_order",
            "name",
        )

        menus = Menu.objects.filter(
            is_active=True,
            module__is_active=True,
        ).order_by(
            "sort_order",
            "name",
        )

        actions = Action.objects.filter(
            is_active=True,
            menu__is_active=True,
            menu__module__is_active=True,
        ).order_by(
            "sort_order",
            "name",
        )

        # Existing permissions assigned to this group.
        assigned_permissions = GroupPermission.objects.filter(
            group=group,
        ).values(
            "module_id",
            "menu_id",
            "action_id",
        )

        assigned = []

        for permission in assigned_permissions:
            if permission["module_id"]:
                assigned.append({
                    "type": "module",
                    "id": permission["module_id"],
                })

            elif permission["menu_id"]:
                assigned.append({
                    "type": "menu",
                    "id": permission["menu_id"],
                })

            elif permission["action_id"]:
                assigned.append({
                    "type": "action",
                    "id": permission["action_id"],
                })

        # Build menu nodes.
        menu_map = {}

        for menu in menus:
            menu_map[menu.id] = {
                "id": menu.id,
                "name": menu.name,
                "module_id": menu.module_id,
                "parent_id": menu.parent_id,
                "children": [],
                "actions": [],
            }

        # Attach child menus to their parents.
        for menu_data in menu_map.values():
            parent_id = menu_data["parent_id"]

            if parent_id in menu_map:
                menu_map[parent_id]["children"].append(
                    menu_data
                )

        # Attach actions to their menus.
        for action in actions:
            if action.menu_id in menu_map:
                menu_map[action.menu_id]["actions"].append({
                    "id": action.id,
                    "name": action.name,
                })

        # Collect root menus by module.
        module_menu_map = {
            module.id: []
            for module in modules
        }

        for menu_data in menu_map.values():
            parent_id = menu_data["parent_id"]

            # If a parent is inactive or unavailable,
            # display this menu as a root node.
            if (
                parent_id is None
                or parent_id not in menu_map
            ):
                module_menu_map[
                    menu_data["module_id"]
                ].append(menu_data)

        # Build final response.
        module_data = []

        for module in modules:
            module_data.append({
                "id": module.id,
                "name": module.name,
                "menus": module_menu_map[module.id],
            })

        return JsonResponse({
            "success": True,
            "modules": module_data,
            "assigned": assigned,
        })

    # ==========================================
    # POST: Validate and save permissions
    # ==========================================

    if request.method == "POST":

        try:
            payload = json.loads(request.body)

        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({
                "success": False,
                "message": "Invalid JSON data.",
            }, status=400)

        if not isinstance(payload, dict):
            return JsonResponse({
                "success": False,
                "message": "Invalid request data.",
            }, status=400)

        permissions = payload.get("permissions")

        if not isinstance(permissions, list):
            return JsonResponse({
                "success": False,
                "message": "Permissions must be a list.",
            }, status=400)

        valid_types = {
            "module": Module,
            "menu": Menu,
            "action": Action,
        }

        permission_objects = []
        seen = set()

        # Validate everything before replacing permissions.
        for item in permissions:

            if not isinstance(item, dict):
                return JsonResponse({
                    "success": False,
                    "message": "Invalid permission entry.",
                }, status=400)

            permission_type = item.get("type")
            permission_id = item.get("id")

            if permission_type not in valid_types:
                return JsonResponse({
                    "success": False,
                    "message": "Invalid permission type.",
                }, status=400)

            try:
                permission_id = int(permission_id)

            except (TypeError, ValueError):
                return JsonResponse({
                    "success": False,
                    "message": "Invalid permission ID.",
                }, status=400)

            if permission_id <= 0:
                return JsonResponse({
                    "success": False,
                    "message": "Invalid permission ID.",
                }, status=400)

            key = (permission_type, permission_id)

            if key in seen:
                return JsonResponse({
                    "success": False,
                    "message": "Duplicate permission entry.",
                }, status=400)

            seen.add(key)

            model = valid_types[permission_type]

            if permission_type == "module":
                target = model.objects.filter(
                    pk=permission_id,
                    is_active=True,
                ).first()

            elif permission_type == "menu":
                target = model.objects.filter(
                    pk=permission_id,
                    is_active=True,
                    module__is_active=True,
                ).first()

            else:
                target = model.objects.filter(
                    pk=permission_id,
                    is_active=True,
                    menu__is_active=True,
                    menu__module__is_active=True,
                ).first()

            if target is None:
                return JsonResponse({
                    "success": False,
                    "message": (
                        f"Selected {permission_type} is missing "
                        "or inactive."
                    ),
                }, status=400)

            permission = GroupPermission(
                group=group,
                module=(
                    target
                    if permission_type == "module"
                    else None
                ),
                menu=(
                    target
                    if permission_type == "menu"
                    else None
                ),
                action=(
                    target
                    if permission_type == "action"
                    else None
                ),
            )

            try:
                permission.clean()

            except ValidationError as exc:
                return JsonResponse({
                    "success": False,
                    "message": str(exc),
                }, status=400)

            permission_objects.append(permission)

        # ==========================================
        # Determine currently visible target IDs
        # ==========================================

        visible_module_ids = list(
            Module.objects.filter(
                is_active=True,
            ).values_list(
                "id",
                flat=True,
            )
        )

        visible_menu_ids = list(
            Menu.objects.filter(
                is_active=True,
                module__is_active=True,
            ).values_list(
                "id",
                flat=True,
            )
        )

        visible_action_ids = list(
            Action.objects.filter(
                is_active=True,
                menu__is_active=True,
                menu__module__is_active=True,
            ).values_list(
                "id",
                flat=True,
            )
        )

        # ==========================================
        # Atomic replacement of visible permissions
        # ==========================================

        with transaction.atomic():

            visible_permissions = (
                GroupPermission.objects.filter(
                    group=group,
                ).filter(
                    Q(module_id__in=visible_module_ids)
                    | Q(menu_id__in=visible_menu_ids)
                    | Q(action_id__in=visible_action_ids)
                )
            )

            # Delete only permissions belonging to
            # currently visible targets.
            visible_permissions.delete()

            # Preserve permissions attached to inactive
            # targets and create the submitted assignments.
            GroupPermission.objects.bulk_create(
                permission_objects,
            )

        return JsonResponse({
            "success": True,
            "message": "Group permissions saved successfully.",
        })

    return JsonResponse({
        "error": "Method not allowed.",
    }, status=405)



@login_required
def application_home_view(request):
    """
    Redirect users to the first module they can access.
    """

    modules = get_accessible_modules(request.user)

    if not modules.exists():
        return render(
            request,
            "accounts/no_access.html",
        )

    if request.user.is_superuser:
        return redirect("access_control:home")

    first_module = modules.first()

    if first_module.code == "access_control":
        return redirect("access_control:home")

    if first_module.code == "product_entry":
        # Product Entry landing page will be connected
        # when that module's pages are implemented.
        return render(
            request,
            "accounts/module_pending.html",
            {"module": first_module},
        )

    return render(
        request,
        "accounts/module_pending.html",
        {"module": first_module},
    )


