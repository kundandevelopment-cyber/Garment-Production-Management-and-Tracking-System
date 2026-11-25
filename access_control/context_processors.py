
from django.urls import reverse, NoReverseMatch

from .services import (
    get_accessible_modules,
    get_accessible_menus,
)


MENU_VIEW_NAMES = {
    "modules": {
        "access_control:module_management",
        "access_control:module_list",
        "access_control:module_create",
        "access_control:module_edit",
    },
    "menus": {
        "access_control:menu_management",
        "access_control:menu_list",
        "access_control:menu_create",
        "access_control:menu_edit",
        "access_control:menu_delete",
    },
    "actions": {
        "access_control:action_list",
        "access_control:action_create",
        "access_control:action_edit",
        "access_control:action_delete",
        "access_control:action_management",
    },
    "permissions": {
        "access_control:group_permission_list",
        "access_control:group_permission_update",
        "access_control:group_permission_available_tree",
        "access_control:group_permission_groups",
        "access_control:group_permission_management",
    },
}


def accessible_navigation(request):
    if not request.user.is_authenticated or not request.user.is_active:
        return {"navigation_modules": []}

    current_view = ""

    if request.resolver_match:
        current_view = request.resolver_match.view_name or ""

    modules = []

    for module in get_accessible_modules(request.user):
        menu_objects = list(
            get_accessible_menus(request.user, module)
        )

        menu_ids = {menu.id for menu in menu_objects}
        menus_by_parent = {}
        menus_by_code = {
            menu.code: menu for menu in menu_objects
        }

        for menu in menu_objects:
            menus_by_parent.setdefault(menu.parent_id, []).append(menu)

        for children in menus_by_parent.values():
            children.sort(
                key=lambda menu: (
                    menu.sort_order,
                    menu.name.lower(),
                )
            )

        # The Menus record is the target for Action Management.
        menus_management_record = menus_by_code.get("menus")

        def build_menu_tree(menu):
            menu_url = None

            # Generate dynamic Access Control management URLs.
            try:
                if menu.code == "menus":
                    menu_url = reverse(
                        "access_control:menu_management",
                        kwargs={"module_id": module.id},
                    )

                elif menu.code == "actions" and menus_management_record:
                    menu_url = reverse(
                        "access_control:action_management",
                        kwargs={
                            "module_id": module.id,
                            "menu_id": menus_management_record.id,
                        },
                    )

                elif menu.url_name:
                    menu_url = reverse(menu.url_name)

            except NoReverseMatch:
                menu_url = None

            children = [
                build_menu_tree(child)
                for child in menus_by_parent.get(menu.id, [])
            ]

            mapped_view_names = MENU_VIEW_NAMES.get(
                menu.code,
                set(),
            )

            is_active = (
                current_view == menu.url_name
                or current_view in mapped_view_names
            )

            has_active_child = any(
                child["is_active"] or child["has_active_child"]
                for child in children
            )

            return {
                "menu": menu,
                "url": menu_url,
                "children": children,
                "is_active": is_active,
                "has_active_child": has_active_child,
            }

        root_menus = [
            build_menu_tree(menu)
            for menu in menus_by_parent.get(None, [])
        ]

        # Keep accessible menus visible if their parent is unavailable.
        for menu in menu_objects:
            if menu.parent_id is not None and menu.parent_id not in menu_ids:
                root_menus.append(build_menu_tree(menu))

        modules.append({
            "module": module,
            "menus": root_menus,
        })

    return {
        "navigation_modules": modules,
    }
