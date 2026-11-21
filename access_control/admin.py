
from django.contrib import admin
from .models import (
    Module,
    Menu,
    Action,
    GroupPermission,
    UserPermission,
)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
        "sort_order",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "module",
        "parent",
        "code",
        "is_active",
        "sort_order",
    )
    list_filter = ("module", "is_active")
    search_fields = ("name", "code", "module__name")
    ordering = ("module", "sort_order", "name")



@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "menu",
        "code",
        "is_active",
        "sort_order",
        "created_at",
    )

    list_filter = (
        "menu__module",
        "menu",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "menu__name",
    )

    ordering = ("menu", "sort_order", "name")



@admin.register(GroupPermission)
class GroupPermissionAdmin(admin.ModelAdmin):
    list_display = (
        "group",
        "module",
        "menu",
        "action",
        "created_at",
    )

    list_filter = (
        "group",
        "module",
    )

    search_fields = (
        "group__name",
        "module__name",
        "menu__name",
        "action__name",
    )


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "module",
        "menu",
        "action",
        "created_at",
    )

    list_filter = ("module",)

    search_fields = (
        "user__username",
        "user__email",
        "module__name",
        "menu__name",
        "action__name",
    )