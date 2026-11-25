
from django.db import models
from django.contrib.auth.models import Group
from django.conf import settings
from django.core.exceptions import ValidationError


class Module(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["sort_order", "name"]


class Menu(models.Model):
    module = models.ForeignKey(
        Module,
        on_delete=models.PROTECT,
        related_name="menus",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=100)

    # Django URL pattern name for navigation
    url_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text=(
            "Django URL pattern name, for example: "
            "access_control:module_management"
        ),
    )

    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["module", "code"],
                name="unique_menu_code_per_module",
            )
        ]

    def __str__(self):
        return f"{self.module.name} - {self.name}"

    def clean(self):
        super().clean()

        if self.is_active and not self.module.is_active:
            raise ValidationError(
                "An active menu cannot belong to an inactive module."
            )

        if self.parent and self.parent.module != self.module:
            raise ValidationError(
                "Parent menu must belong to the same module."
            )

        current_parent = self.parent
        visited_objects = set()
        visited_database_ids = set()

        while current_parent is not None:
            if current_parent is self:
                raise ValidationError(
                    "Circular menu hierarchy detected."
                )

            if self.pk and current_parent.pk == self.pk:
                raise ValidationError(
                    "Circular menu hierarchy detected."
                )

            object_id = id(current_parent)

            if object_id in visited_objects:
                raise ValidationError(
                    "Circular menu hierarchy detected."
                )

            visited_objects.add(object_id)

            if current_parent.pk:
                if current_parent.pk in visited_database_ids:
                    raise ValidationError(
                        "Circular menu hierarchy detected."
                    )

                visited_database_ids.add(current_parent.pk)

            if self.is_active and not current_parent.is_active:
                raise ValidationError(
                    "An active menu cannot have an inactive ancestor."
                )

            current_parent = current_parent.parent


class Action(models.Model):
    menu = models.ForeignKey(
        Menu,
        on_delete=models.PROTECT,
        related_name="actions",
    )

    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=100)

    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["menu", "code"],
                name="unique_action_code_per_menu",
            )
        ]

    def __str__(self):
        return f"{self.menu.name} - {self.name}"

    def clean(self):
        super().clean()

        if self.menu and not self.menu.is_active:
            raise ValidationError(
                "Cannot configure an action under an inactive menu."
            )

        if self.menu and not self.menu.module.is_active:
            raise ValidationError(
                "Cannot configure an action under an inactive module."
            )


class GroupPermission(models.Model):
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="custom_permissions",
    )

    module = models.ForeignKey(
        Module,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    menu = models.ForeignKey(
        Menu,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    action = models.ForeignKey(
        Action,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        module__isnull=False,
                        menu__isnull=True,
                        action__isnull=True,
                    )
                    | models.Q(
                        module__isnull=True,
                        menu__isnull=False,
                        action__isnull=True,
                    )
                    | models.Q(
                        module__isnull=True,
                        menu__isnull=True,
                        action__isnull=False,
                    )
                ),
                name="group_permission_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["group", "module", "menu", "action"],
                name="unique_group_permission",
                nulls_distinct=False,
            ),
        ]

    def __str__(self):
        target = self.module or self.menu or self.action
        return f"{self.group.name} - {target}"

    def clean(self):
        super().clean()

        if self.module and not self.module.is_active:
            raise ValidationError(
                "Cannot grant permission to an inactive module."
            )

        if self.menu and not self.menu.is_active:
            raise ValidationError(
                "Cannot grant permission to an inactive menu."
            )

        if self.menu and not self.menu.module.is_active:
            raise ValidationError(
                "Cannot grant permission under an inactive module."
            )

        if self.action and not self.action.is_active:
            raise ValidationError(
                "Cannot grant permission to an inactive action."
            )

        if self.action and not self.action.menu.is_active:
            raise ValidationError(
                "Cannot grant permission under an inactive menu."
            )

        if self.action and not self.action.menu.module.is_active:
            raise ValidationError(
                "Cannot grant permission under an inactive module."
            )


class UserPermission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="custom_permissions",
    )

    module = models.ForeignKey(
        Module,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    menu = models.ForeignKey(
        Menu,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    action = models.ForeignKey(
        Action,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        module__isnull=False,
                        menu__isnull=True,
                        action__isnull=True,
                    )
                    | models.Q(
                        module__isnull=True,
                        menu__isnull=False,
                        action__isnull=True,
                    )
                    | models.Q(
                        module__isnull=True,
                        menu__isnull=True,
                        action__isnull=False,
                    )
                ),
                name="user_permission_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["user", "module", "menu", "action"],
                name="unique_user_permission",
                nulls_distinct=False,
            ),
        ]

    def clean(self):
        super().clean()

        if self.module and not self.module.is_active:
            raise ValidationError(
                "Cannot grant permission to an inactive module."
            )

        if self.menu and not self.menu.is_active:
            raise ValidationError(
                "Cannot grant permission to an inactive menu."
            )

        if self.menu and not self.menu.module.is_active:
            raise ValidationError(
                "Cannot grant permission under an inactive module."
            )

        if self.action and not self.action.is_active:
            raise ValidationError(
                "Cannot grant permission to an inactive action."
            )

        if self.action and not self.action.menu.is_active:
            raise ValidationError(
                "Cannot grant permission under an inactive menu."
            )

        if self.action and not self.action.menu.module.is_active:
            raise ValidationError(
                "Cannot grant permission under an inactive module."
            )

    def __str__(self):
        target = self.module or self.menu or self.action
        return f"{self.user.username} - {target}"
