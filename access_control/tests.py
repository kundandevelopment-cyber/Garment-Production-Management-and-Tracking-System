from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

from .models import Module, Menu, Action, GroupPermission, UserPermission

User = get_user_model()


class ActionValidationTests(TestCase):

    def test_action_under_inactive_menu_is_invalid(self):
        # Create a module
        module = Module.objects.create(
            name="Test Module",
            code="test_module",
        )

        # Create an inactive menu
        menu = Menu.objects.create(
            module=module,
            name="Test Menu",
            code="test_menu",
            is_active=False,
        )

        # Create an action under that inactive menu
        action = Action(
            menu=menu,
            name="Test Action",
            code="test_action",
            is_active=True,
        )

        # The action should fail validation
        with self.assertRaises(ValidationError):
            action.full_clean()
    def test_action_under_inactive_module_is_invalid(self):
        module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
        )

        menu = Menu.objects.create(
            module=module,
            name="Test Menu",
            code="test_menu",
            is_active=True,
        )

        action = Action(
            menu=menu,
            name="Test Action",
            code="test_action",
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            action.full_clean()



class GroupPermissionValidationTests(TestCase):

    def test_permission_for_inactive_menu_is_invalid(self):
        group = Group.objects.create(name="Test Group")

        module = Module.objects.create(
            name="Test Module",
            code="test_module",
        )

        menu = Menu.objects.create(
            module=module,
            name="Test Menu",
            code="test_menu",
            is_active=False,
        )

        permission = GroupPermission(
            group=group,
            menu=menu,
        )

        with self.assertRaises(ValidationError):
            permission.full_clean()

    def test_permission_for_inactive_module_is_invalid(self):
        group = Group.objects.create(name="Test Group")

        module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
        )

        permission = GroupPermission(
            group=group,
            module=module,
        )

        with self.assertRaises(ValidationError):
            permission.full_clean()

    def test_permission_for_inactive_action_is_invalid(self):
        group = Group.objects.create(name="Test Group")

        module = Module.objects.create(
            name="Test Module",
            code="test_module",
        )

        menu = Menu.objects.create(
            module=module,
            name="Test Menu",
            code="test_menu",
        )

        action = Action.objects.create(
            menu=menu,
            name="Test Action",
            code="test_action",
            is_active=False,
        )

        permission = GroupPermission(
            group=group,
            action=action,
        )

        with self.assertRaises(ValidationError):
            permission.full_clean()


class UserPermissionValidationTests(TestCase):

    def test_permission_for_inactive_menu_is_invalid(self):
        user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )

        module = Module.objects.create(
            name="Test Module",
            code="test_module",
        )

        menu = Menu.objects.create(
            module=module,
            name="Test Menu",
            code="test_menu",
            is_active=False,
        )

        permission = UserPermission(
            user=user,
            menu=menu,
        )

        with self.assertRaises(ValidationError):
            permission.full_clean()

    def test_permission_for_inactive_module_is_invalid(self):
        user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )

        module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
        )

        permission = UserPermission(
            user=user,
            module=module,
        )

        with self.assertRaises(ValidationError):
            permission.full_clean()

    def test_permission_for_inactive_action_is_invalid(self):
        user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )

        module = Module.objects.create(
            name="Test Module",
            code="test_module",
        )

        menu = Menu.objects.create(
            module=module,
            name="Test Menu",
            code="test_menu",
        )

        action = Action.objects.create(
            menu=menu,
            name="Test Action",
            code="test_action",
            is_active=False,
        )

        permission = UserPermission(
            user=user,
            action=action,
        )

        with self.assertRaises(ValidationError):
            permission.full_clean()

class MenuValidationTests(TestCase):

    def test_parent_menu_must_belong_to_same_module(self):
        module_one = Module.objects.create(
            name="Module One",
            code="module_one",
        )

        module_two = Module.objects.create(
            name="Module Two",
            code="module_two",
        )

        parent_menu = Menu.objects.create(
            module=module_one,
            name="Parent Menu",
            code="parent_menu",
        )

        child_menu = Menu(
            module=module_two,
            parent=parent_menu,
            name="Child Menu",
            code="child_menu",
        )

        with self.assertRaises(ValidationError):
            child_menu.full_clean()

    def test_menu_cannot_be_its_own_parent(self):
            module = Module.objects.create(
                name="Test Module",
                code="test_module",
            )

            menu = Menu(
                module=module,
                name="Self Parent Menu",
                code="self_parent_menu",
            )

            menu.parent = menu

            with self.assertRaises(ValidationError):
                menu.full_clean()

    def test_menu_cannot_create_indirect_parent_cycle(self):
        module = Module.objects.create(
            name="Test Module",
            code="test_module",
        )

        menu_a = Menu.objects.create(
            module=module,
            name="Menu A",
            code="menu_a",
        )

        menu_b = Menu.objects.create(
            module=module,
            name="Menu B",
            code="menu_b",
            parent=menu_a,
        )

        menu_c = Menu.objects.create(
            module=module,
            name="Menu C",
            code="menu_c",
            parent=menu_b,
        )

        menu_a.parent = menu_c

        with self.assertRaises(ValidationError):
            menu_a.full_clean()
    def test_active_menu_cannot_have_inactive_parent(self):
        module = Module.objects.create(
            name="Test Module",
            code="test_module",
        )

        parent_menu = Menu.objects.create(
            module=module,
            name="Inactive Parent",
            code="inactive_parent",
            is_active=False,
        )

        child_menu = Menu(
            module=module,
            parent=parent_menu,
            name="Active Child",
            code="active_child",
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            child_menu.full_clean()

    def test_active_menu_cannot_belong_to_inactive_module(self):
        module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
        )

        menu = Menu(
            module=module,
            name="Active Menu",
            code="active_menu",
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            menu.full_clean()

    def test_menu_code_must_be_unique_within_module(self):
        module = Module.objects.create(
            name="Test Module",
            code="test_module",
        )

        Menu.objects.create(
            module=module,
            name="First Menu",
            code="duplicate_code",
        )

        duplicate_menu = Menu(
            module=module,
            name="Second Menu",
            code="duplicate_code",
        )

        with self.assertRaises(ValidationError):
            duplicate_menu.full_clean()

    def test_same_menu_code_allowed_in_different_modules(self):
        module_one = Module.objects.create(
            name="Production",
            code="production",
        )

        module_two = Module.objects.create(
            name="Inventory",
            code="inventory",
        )

        Menu.objects.create(
            module=module_one,
            name="Dashboard",
            code="dashboard",
        )

        menu_two = Menu(
            module=module_two,
            name="Dashboard",
            code="dashboard",
        )

        menu_two.full_clean()

    def test_active_menu_cannot_have_inactive_ancestor(self):
        module = Module.objects.create(
            name="Test Module",
            code="test_module",
        )

        grandparent = Menu.objects.create(
            module=module,
            name="Inactive Grandparent",
            code="inactive_grandparent",
            is_active=False,
        )

        parent = Menu.objects.create(
            module=module,
            name="Active Parent",
            code="active_parent",
            is_active=True,
        )

        child = Menu(
            module=module,
            parent=parent,
            name="Active Child",
            code="active_child",
            is_active=True,
        )

        # Connect the parent to the inactive grandparent.
        parent.parent = grandparent

        with self.assertRaises(ValidationError):
            child.full_clean()

    def test_save_does_not_automatically_call_full_clean(self):
        module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
        )

        menu = Menu(
            module=module,
            name="Invalid Active Menu",
            code="invalid_active_menu",
            is_active=True,
        )

        menu.save()

        self.assertTrue(
            Menu.objects.filter(pk=menu.pk).exists()
        )

    def test_bulk_create_does_not_call_full_clean(self):
        module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
        )

        menu = Menu(
            module=module,
            name="Invalid Active Menu",
            code="invalid_active_menu",
            is_active=True,
        )

        Menu.objects.bulk_create([menu])

        self.assertTrue(
            Menu.objects.filter(code="invalid_active_menu").exists()
        )

    def test_queryset_update_bypasses_model_validation(self):
        module = Module.objects.create(
            name="Active Module",
            code="active_module",
            is_active=True,
        )

        menu = Menu.objects.create(
            module=module,
            name="Active Menu",
            code="active_menu",
            is_active=True,
        )

        Module.objects.filter(pk=module.pk).update(is_active=False)

        menu.refresh_from_db()

        self.assertFalse(menu.module.is_active)
        self.assertTrue(menu.is_active)