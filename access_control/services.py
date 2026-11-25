
from .models import (
    Module,
    Menu,
    Action,
    GroupPermission,
    UserPermission,
)
def _is_active_authenticated_user(user):
    return (
        user.is_authenticated
        and user.is_active
    )


def user_has_module_access(user, module):
    """
    Check whether a user has access to a module.

    Rules:
    - Unauthenticated users have no access.
    - Superusers have access to active modules.
    - Direct user permissions grant access.
    - Permissions inherited from Django groups grant access.
    - Inactive modules are never accessible.
    """

    if not _is_active_authenticated_user(user):
        return False

    if isinstance(module, int):
        module = Module.objects.filter(pk=module).first()

    if module is None or not module.is_active:
        return False

    if user.is_superuser:
        return True

    has_direct_permission = UserPermission.objects.filter(
        user=user,
        module=module,
    ).exists()

    if has_direct_permission:
        return True

    has_group_permission = GroupPermission.objects.filter(
        group__in=user.groups.all(),
        module=module,
    ).exists()

    return has_group_permission



def _menu_and_ancestors_are_active(menu):
    """
    Check whether the menu, its module, and all its ancestors
    are active using a single menu hierarchy query.
    """

    if menu is None or not menu.is_active:
        return False

    module = menu.module

    if not module.is_active:
        return False

    # Load this module's menu hierarchy in one query.
    menus = Menu.objects.filter(
        module_id=module.pk,
    ).values(
        "id",
        "parent_id",
        "is_active",
    )

    menu_map = {
        item["id"]: item
        for item in menus
    }

    current_menu_id = menu.pk
    visited = set()

    while current_menu_id is not None:
        if current_menu_id in visited:
            # Protect against corrupted cyclic hierarchy data.
            return False

        visited.add(current_menu_id)

        current_menu = menu_map.get(current_menu_id)

        if current_menu is None or not current_menu["is_active"]:
            return False

        current_menu_id = current_menu["parent_id"]

    return True







def user_has_menu_access(user, menu):
    """
    Check whether a user can access a menu.

    Access is granted by:
    - Module permission.
    - Direct or group permission on the requested menu.
    - Permission on an ancestor menu.
    - Permission on a descendant menu.
    - Action permission on a descendant menu.
    - Superuser privileges.

    Inactive menus and ancestors always deny access.
    """

    if not _is_active_authenticated_user(user):
        return False

    if isinstance(menu, int):
        menu = Menu.objects.select_related(
            "module",
            "parent",
        ).filter(pk=menu).first()

    if menu is None:
        return False

    if not _menu_and_ancestors_are_active(menu):
        return False

    if user.is_superuser:
        return True

    if user_has_module_access(user, menu.module):
        return True

    groups = user.groups.all()

    # Load all active menus in this module once.
    active_menus = Menu.objects.filter(
        module=menu.module,
        is_active=True,
    ).values(
        "id",
        "parent_id",
    )

    menu_map = {
        item["id"]: item
        for item in active_menus
    }

    children_by_parent = {}

    for item in menu_map.values():
        children_by_parent.setdefault(
            item["parent_id"], []
        ).append(item["id"])

    # Collect the requested menu and all active descendants.
    descendant_menu_ids = []
    menus_to_check = [menu.pk]
    visited = set()

    while menus_to_check:
        current_menu_id = menus_to_check.pop()

        if current_menu_id in visited:
            continue

        visited.add(current_menu_id)
        descendant_menu_ids.append(current_menu_id)

        menus_to_check.extend(
            children_by_parent.get(current_menu_id, [])
        )

    # Collect all active ancestors.
    ancestor_menu_ids = []
    current_menu_id = menu_map[menu.pk]["parent_id"]

    while current_menu_id is not None:
        if current_menu_id in visited:
            break

        visited.add(current_menu_id)
        ancestor_menu_ids.append(current_menu_id)

        current_menu = menu_map.get(current_menu_id)

        if current_menu is None:
            break

        current_menu_id = current_menu["parent_id"]

    # A menu permission on an ancestor, the requested menu,
    # or a descendant grants navigation access.
    accessible_menu_ids = (
        ancestor_menu_ids + descendant_menu_ids
    )

    if UserPermission.objects.filter(
        user=user,
        menu_id__in=accessible_menu_ids,
    ).exists():
        return True

    if GroupPermission.objects.filter(
        group__in=groups,
        menu_id__in=accessible_menu_ids,
    ).exists():
        return True

    # An action permission on a descendant grants
    # navigation access to its ancestor menus.
    if UserPermission.objects.filter(
        user=user,
        action__menu_id__in=descendant_menu_ids,
        action__is_active=True,
    ).exists():
        return True

    return GroupPermission.objects.filter(
        group__in=groups,
        action__menu_id__in=descendant_menu_ids,
        action__is_active=True,
    ).exists()



def user_has_action_access(user, action):
    """
    Check whether a user can execute a specific action.

    Access is granted by:
    - Module permission.
    - Direct permission for this exact action.
    - Group permission for this exact action.
    - Superuser privileges.

    Menu permissions grant page access, not automatic
    permission to execute every action on that page.

    Inactive actions, menus, modules, and ancestors
    always deny access.
    """

    if not _is_active_authenticated_user(user):
        return False

    if isinstance(action, int):
        action = Action.objects.select_related(
            "menu",
            "menu__module",
        ).filter(pk=action).first()

    if action is None or not action.is_active:
        return False

    if not _menu_and_ancestors_are_active(action.menu):
        return False

    if user.is_superuser:
        return True

    if user_has_module_access(user, action.menu.module):
        return True

    # Direct permission for this exact action.
    if UserPermission.objects.filter(
        user=user,
        action=action,
    ).exists():
        return True

    # Permission inherited from any Django group.
    return GroupPermission.objects.filter(
        group__in=user.groups.all(),
        action=action,
    ).exists()
def get_access_control_dashboard_stats():
    """
    Return summary statistics for the Access Control dashboard.
    """

    return {
        "modules": Module.objects.count(),
        "menus": Menu.objects.count(),
        "actions": Action.objects.count(),
        "group_permissions": GroupPermission.objects.count(),
        "user_permissions": UserPermission.objects.count(),
    }


def get_accessible_modules(user):
    """
    Return active modules accessible through either:
    - Direct module permission
    - Group module permission
    - Accessible menu permission
    - Accessible action permission
    - Superuser access
    """

    if not _is_active_authenticated_user(user):
        return Module.objects.none()

    active_modules = Module.objects.filter(
        is_active=True,
    ).order_by(
        "sort_order",
        "name",
    )

    if user.is_superuser:
        return active_modules

    # 1. Direct module permissions
    direct_module_ids = UserPermission.objects.filter(
        user=user,
        module__is_active=True,
        module__isnull=False,
    ).values_list(
        "module_id",
        flat=True,
    )

    # 2. Group module permissions
    group_module_ids = GroupPermission.objects.filter(
        group__in=user.groups.all(),
        module__is_active=True,
        module__isnull=False,
    ).values_list(
        "module_id",
        flat=True,
    )

    # 3. Collect module IDs granted directly or through groups
    module_ids = set(direct_module_ids) | set(group_module_ids)

    # 4. Also include modules containing accessible menus/actions
    for module in active_modules:
        if get_accessible_menus(user, module).exists():
            module_ids.add(module.pk)

    return active_modules.filter(
        pk__in=module_ids,
    )


def get_accessible_menus(user, module):
    """
    Return all active menus accessible to a user within a module.

    Menu permissions grant access to the target menu,
    its descendants, and ancestor navigation.

    Action permissions grant access to the action's menu
    and its ancestor navigation.
    """

    if not _is_active_authenticated_user(user):
        return Menu.objects.none()

    if isinstance(module, int):
        module = Module.objects.filter(pk=module).first()

    if module is None or not module.is_active:
        return Menu.objects.none()

    active_menus = Menu.objects.filter(
        module=module,
        is_active=True,
    ).values(
        "id",
        "parent_id",
        "sort_order",
        "name",
    )

    menu_map = {
        item["id"]: item
        for item in active_menus
    }

    if not menu_map:
        return Menu.objects.none()

    if user.is_superuser or user_has_module_access(user, module):
        return Menu.objects.filter(
            module=module,
            is_active=True,
        ).order_by(
            "sort_order",
            "name",
        )

    children_by_parent = {}

    for item in menu_map.values():
        children_by_parent.setdefault(
            item["parent_id"], []
        ).append(item["id"])

    # Identify menus whose entire ancestor hierarchy is active.
    valid_menu_ids = set()
    menus_to_check = children_by_parent.get(None, [])

    while menus_to_check:
        current_menu_id = menus_to_check.pop()

        if current_menu_id in valid_menu_ids:
            continue

        valid_menu_ids.add(current_menu_id)

        menus_to_check.extend(
            children_by_parent.get(current_menu_id, [])
        )

    if not valid_menu_ids:
        return Menu.objects.none()

    groups = user.groups.all()

    # Collect direct and group menu permissions.
    user_menu_ids = set(
        UserPermission.objects.filter(
            user=user,
            menu_id__in=valid_menu_ids,
        ).values_list(
            "menu_id",
            flat=True,
        )
    )

    group_menu_ids = set(
        GroupPermission.objects.filter(
            group__in=groups,
            menu_id__in=valid_menu_ids,
        ).values_list(
            "menu_id",
            flat=True,
        )
    )

    permitted_menu_ids = user_menu_ids | group_menu_ids

    # Collect menus containing active permitted actions.
    user_action_menu_ids = set(
        UserPermission.objects.filter(
            user=user,
            action__menu_id__in=valid_menu_ids,
            action__is_active=True,
        ).values_list(
            "action__menu_id",
            flat=True,
        )
    )

    group_action_menu_ids = set(
        GroupPermission.objects.filter(
            group__in=groups,
            action__menu_id__in=valid_menu_ids,
            action__is_active=True,
        ).values_list(
            "action__menu_id",
            flat=True,
        )
    )

    action_menu_ids = (
        user_action_menu_ids | group_action_menu_ids
    )

    accessible_menu_ids = set()

    # Menu permissions grant access to ancestors and descendants.
    for permitted_menu_id in permitted_menu_ids:
        current_menu_id = permitted_menu_id

        while current_menu_id is not None:
            if current_menu_id not in valid_menu_ids:
                break

            accessible_menu_ids.add(current_menu_id)

            current_menu_id = menu_map[current_menu_id]["parent_id"]

        menus_to_check = [permitted_menu_id]

        visited_descendants = set()

        while menus_to_check:
            current_menu_id = menus_to_check.pop()

            if current_menu_id not in valid_menu_ids:
                continue

            if current_menu_id in visited_descendants:
                continue

            visited_descendants.add(current_menu_id)
            accessible_menu_ids.add(current_menu_id)

            menus_to_check.extend(
                children_by_parent.get(current_menu_id, [])
            )

    # Action permissions grant access to their menu and ancestors.
    for action_menu_id in action_menu_ids:
        current_menu_id = action_menu_id

        while current_menu_id is not None:
            if current_menu_id not in valid_menu_ids:
                break

            accessible_menu_ids.add(current_menu_id)

            current_menu_id = menu_map[current_menu_id]["parent_id"]

    if not accessible_menu_ids:
        return Menu.objects.none()

    return Menu.objects.filter(
        module=module,
        pk__in=accessible_menu_ids,
    ).order_by(
        "sort_order",
        "name",
    )


def get_accessible_actions(user, menu):
    """
    Return active actions accessible to a user within a menu.

    Access is granted by:
    - Superuser privileges.
    - Module permission (all actions).
    - Direct permission for a specific action.
    - Group permission for a specific action.

    Menu permission grants page access but does not
    automatically grant access to all actions.
    """

    if not _is_active_authenticated_user(user):
        return Action.objects.none()

    if isinstance(menu, int):
        menu = Menu.objects.select_related(
            "module",
        ).filter(pk=menu).first()

    if menu is None or not menu.is_active:
        return Action.objects.none()

    if not _menu_and_ancestors_are_active(menu):
        return Action.objects.none()

    # Superuser can access every active action.
    if user.is_superuser:
        return Action.objects.filter(
            menu=menu,
            is_active=True,
        ).order_by(
            "sort_order",
            "name",
        )

    # Module permission grants every action in the module.
    if user_has_module_access(user, menu.module):
        return Action.objects.filter(
            menu=menu,
            is_active=True,
        ).order_by(
            "sort_order",
            "name",
        )

    # Collect actions explicitly assigned to the user.
    direct_action_ids = UserPermission.objects.filter(
        user=user,
        action__menu=menu,
        action__is_active=True,
    ).values_list(
        "action_id",
        flat=True,
    )

    # Collect actions explicitly assigned through groups.
    group_action_ids = GroupPermission.objects.filter(
        group__in=user.groups.all(),
        action__menu=menu,
        action__is_active=True,
    ).values_list(
        "action_id",
        flat=True,
    )

    accessible_action_ids = (
        set(direct_action_ids)
        | set(group_action_ids)
    )

    # Only explicitly permitted actions are returned.
    return Action.objects.filter(
        menu=menu,
        is_active=True,
        id__in=accessible_action_ids,
    ).order_by(
        "sort_order",
        "name",
    )
