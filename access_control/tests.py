from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import json

from .decorators import (
    action_required,
    menu_required,
    module_required,
)
from .models import (
    Action,
    GroupPermission,
    Menu,
    Module,
    UserPermission,
)
from .services import (
    get_access_control_dashboard_stats,
    get_accessible_actions,
    get_accessible_menus,
    get_accessible_modules,
    user_has_action_access,
    user_has_menu_access,
    user_has_module_access,
)

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


class ModuleAccessTests(TestCase):

    def setUp(self):
        self.module = Module.objects.create(
            name="Production Test",
            code="production_test",
        )

        self.user = User.objects.create_user(
            username="production_user",
            password="testpassword123",
        )

    def test_user_without_permission_has_no_access(self):
        self.assertFalse(
            user_has_module_access(self.user, self.module)
        )

    def test_direct_user_permission_grants_access(self):
        UserPermission.objects.create(
            user=self.user,
            module=self.module,
        )

        self.assertTrue(
            user_has_module_access(self.user, self.module)
        )

    def test_group_permission_grants_access(self):
        group = Group.objects.create(
            name="Production Team Test"
        )
        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            module=self.module,
        )

        self.assertTrue(
            user_has_module_access(self.user, self.module)
        )

    def test_superuser_has_access_to_active_module(self):
        superuser = User.objects.create_superuser(
            username="test_superadmin",
            email="admin@example.com",
            password="testpassword123",
        )

        self.assertTrue(
            user_has_module_access(superuser, self.module)
        )

    def test_inactive_module_denies_access(self):
        self.module.is_active = False
        self.module.save()

        UserPermission.objects.create(
            user=self.user,
            module=self.module,
        )

        self.assertFalse(
            user_has_module_access(self.user, self.module)
        )
    def test_anonymous_user_has_no_module_access(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(
            user_has_module_access(AnonymousUser(), self.module)
        )
    def test_module_access_query_count_without_permission(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as queries:
            user_has_module_access(self.user, self.module)

        query_count = len(queries)

        self.assertEqual(
            query_count,
            2,
            msg=(
                "Module access without permission should use "
                "2 database queries."
            ),
        )

    def test_module_access_query_count_with_direct_permission(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        UserPermission.objects.create(
            user=self.user,
            module=self.module,
        )

        with CaptureQueriesContext(connection) as queries:
            user_has_module_access(self.user, self.module)

        query_count = len(queries)

        self.assertEqual(
            query_count,
            1,
            msg=(
                "Module access with direct permission should use "
                "1 database query."
            ),
        )

    def test_module_access_query_count_with_group_permission(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        group = Group.objects.create(
            name="Query Test Group",
        )
        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            module=self.module,
        )

        with CaptureQueriesContext(connection) as queries:
            user_has_module_access(self.user, self.module)

        query_count = len(queries)

        self.assertEqual(
            query_count,
            2,
            msg=(
                "Module access with group permission should use "
                "2 database queries."
            ),
        )
    def test_inactive_user_with_permission_has_no_access(self):
        self.user.is_active = False
        self.user.save()

        UserPermission.objects.create(
            user=self.user,
            module=self.module,
        )

        self.assertFalse(
            user_has_module_access(self.user, self.module)
        )

    def test_inactive_user_with_group_permission_has_no_access(self):
        group = Group.objects.create(
            name="Inactive Production Team"
        )
        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            module=self.module,
        )

        self.user.is_active = False
        self.user.save()

        self.assertFalse(
            user_has_module_access(self.user, self.module)
        )


class MenuAccessTests(TestCase):

    def setUp(self):
        self.module = Module.objects.create(
            name="Menu Test Module",
            code="menu_test_module",
        )

        self.menu = Menu.objects.create(
            module=self.module,
            name="Product List Test",
            code="product_list_test",
        )

        self.user = User.objects.create_user(
            username="menu_test_user",
            password="testpassword123",
        )

    def test_module_permission_grants_menu_access(self):
        UserPermission.objects.create(
            user=self.user,
            module=self.module,
        )

        self.assertTrue(
            user_has_menu_access(self.user, self.menu)
        )

    def test_direct_menu_permission_grants_access(self):
        UserPermission.objects.create(
            user=self.user,
            menu=self.menu,
        )

        self.assertTrue(
            user_has_menu_access(self.user, self.menu)
        )

    def test_group_menu_permission_grants_access(self):
        group = Group.objects.create(name="Menu Test Group")
        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            menu=self.menu,
        )

        self.assertTrue(
            user_has_menu_access(self.user, self.menu)
        )

    def test_action_permission_grants_parent_menu_access(self):
        action = Action.objects.create(
            menu=self.menu,
            name="Edit",
            code="edit",
        )

        UserPermission.objects.create(
            user=self.user,
            action=action,
        )

        self.assertTrue(
            user_has_menu_access(self.user, self.menu)
        )

    def test_user_without_permission_has_no_menu_access(self):
        self.assertFalse(
            user_has_menu_access(self.user, self.menu)
        )

    def test_inactive_menu_denies_access(self):
        self.menu.is_active = False
        self.menu.save()

        UserPermission.objects.create(
            user=self.user,
            menu=self.menu,
        )

        self.assertFalse(
            user_has_menu_access(self.user, self.menu)
        )

    def test_inactive_parent_menu_denies_child_menu_access(self):
        parent_menu = Menu.objects.create(
            module=self.module,
            name="Parent Menu",
            code="parent_menu",
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=parent_menu,
            name="Child Menu",
            code="child_menu",
        )

        UserPermission.objects.create(
            user=self.user,
            menu=child_menu,
        )

        parent_menu.is_active = False
        parent_menu.save()

        self.assertFalse(
            user_has_menu_access(self.user, child_menu)
        )


    def test_child_menu_permission_grants_parent_navigation(self):
        parent_menu = Menu.objects.create(
            module=self.module,
            name="Parent Navigation",
            code="parent_navigation",
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=parent_menu,
            name="Child Navigation",
            code="child_navigation",
        )

        UserPermission.objects.create(
            user=self.user,
            menu=child_menu,
        )

        self.assertTrue(
            user_has_menu_access(self.user, parent_menu)
        )
   
    def test_deep_child_permission_grants_all_ancestor_navigation(self):
        root_menu = Menu.objects.create(
            module=self.module,
            name="Root Menu",
            code="root_menu",
        )

        middle_menu = Menu.objects.create(
            module=self.module,
            parent=root_menu,
            name="Middle Menu",
            code="middle_menu",
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=middle_menu,
            name="Deep Child Menu",
            code="deep_child_menu",
        )

        UserPermission.objects.create(
            user=self.user,
            menu=child_menu,
        )

        self.assertTrue(
            user_has_menu_access(self.user, child_menu)
        )

        self.assertTrue(
            user_has_menu_access(self.user, middle_menu)
        )

        self.assertTrue(
            user_has_menu_access(self.user, root_menu)
        )
    
    def test_inactive_grandparent_denies_deep_child_menu_access(self):
        root_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Root",
            code="inactive_root",
        )

        middle_menu = Menu.objects.create(
            module=self.module,
            parent=root_menu,
            name="Active Middle",
            code="active_middle",
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=middle_menu,
            name="Deep Child",
            code="deep_child",
        )

        UserPermission.objects.create(
            user=self.user,
            menu=child_menu,
        )

        root_menu.is_active = False
        root_menu.save()

        self.assertFalse(
            user_has_menu_access(self.user, child_menu)
        )

    def test_deep_action_permission_grants_all_ancestor_navigation(self):
        root_menu = Menu.objects.create(
            module=self.module,
            name="Production Root",
            code="production_root",
        )

        middle_menu = Menu.objects.create(
            module=self.module,
            parent=root_menu,
            name="Cutting",
            code="cutting",
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=middle_menu,
            name="Cutting Planning",
            code="cutting_planning",
        )

        child_action = Action.objects.create(
            menu=child_menu,
            name="Create Cutting Plan",
            code="create_cutting_plan",
        )

        UserPermission.objects.create(
            user=self.user,
            action=child_action,
        )

        self.assertTrue(
            user_has_menu_access(self.user, child_menu)
        )

        self.assertTrue(
            user_has_menu_access(self.user, middle_menu)
        )

        self.assertTrue(
            user_has_menu_access(self.user, root_menu)
        )
    def test_anonymous_user_has_no_menu_access(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(
            user_has_menu_access(AnonymousUser(), self.menu)
        )
    def test_inactive_descendant_permission_does_not_grant_parent_access(self): 
        parent_menu = Menu.objects.create(
            module=self.module,
            name="Parent Menu",
            code="parent_menu",
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=parent_menu,
            name="Inactive Child Menu",
            code="inactive_child_menu",
            is_active=False,
        )

        UserPermission.objects.create(
            user=self.user,
            menu=child_menu,
        )

        self.assertFalse(
            user_has_menu_access(self.user, parent_menu)
        )

    def test_inactive_intermediate_ancestor_denies_descendant_access(self):
        parent_menu = Menu.objects.create(
            module=self.module,
            name="Production Parent",
            code="production_parent",
        )

        inactive_menu = Menu.objects.create(
            module=self.module,
            parent=parent_menu,
            name="Inactive Planning",
            code="inactive_planning",
            is_active=False,
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=inactive_menu,
            name="Daily Progress",
            code="daily_progress",
        )

        UserPermission.objects.create(
            user=self.user,
            menu=child_menu,
        )

        self.assertFalse(
            user_has_menu_access(self.user, child_menu)
        )

        self.assertFalse(
            user_has_menu_access(self.user, parent_menu)
        )
    def test_inactive_action_permission_does_not_grant_menu_access(self):
        menu = Menu.objects.create(
            module=self.module,
            name="Inactive Action Menu",
            code="inactive_action_menu",
        )

        action = Action.objects.create(
            menu=menu,
            name="Inactive Action",
            code="inactive_action",
            is_active=False,
        )

        UserPermission.objects.create(
            user=self.user,
            action=action,
        )

        self.assertFalse(
            user_has_menu_access(self.user, menu)
        )
    def test_inactive_action_group_permission_does_not_grant_menu_access(self):
        from django.contrib.auth.models import Group

        group = Group.objects.create(
            name="Inactive Navigation Action Group"
        )
        self.user.groups.add(group)

        menu = Menu.objects.create(
            module=self.module,
            name="Group Inactive Action Menu",
            code="group_inactive_action_menu",
        )

        action = Action.objects.create(
            menu=menu,
            name="Inactive Group Action",
            code="inactive_group_action",
            is_active=False,
        )

        GroupPermission.objects.create(
            group=group,
            action=action,
        )

        self.assertFalse(
            user_has_menu_access(self.user, menu)
        )
    def test_menu_access_query_count_does_not_grow_with_children(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        # Measure queries with no child menus.
        with CaptureQueriesContext(connection) as initial_queries:
            user_has_menu_access(self.user, self.menu)

        initial_query_count = len(initial_queries)

        # Add 20 active child menus.
        for index in range(20):
            Menu.objects.create(
                module=self.module,
                parent=self.menu,
                name=f"Performance Child {index}",
                code=f"performance_child_{index}",
            )

        # Measure queries again with 20 child menus.
        with CaptureQueriesContext(connection) as expanded_queries:
            user_has_menu_access(self.user, self.menu)

        expanded_query_count = len(expanded_queries)

        self.assertEqual(
            initial_query_count,
            expanded_query_count,
            msg=(
                "Menu access query count should not increase "
                "when the number of child menus increases."
            ),
        )
    def test_menu_access_query_count_does_not_grow_with_depth(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        # Measure shallow menu access using a fresh instance.
        shallow_menu = Menu.objects.get(pk=self.menu.pk)

        with CaptureQueriesContext(connection) as shallow_queries:
            user_has_menu_access(self.user, shallow_menu)

        shallow_query_count = len(shallow_queries)

        # Build a hierarchy 10 levels deep.
        current_menu = self.menu

        for index in range(10):
            current_menu = Menu.objects.create(
                module=self.module,
                parent=current_menu,
                name=f"Depth Menu {index}",
                code=f"depth_menu_{index}",
            )

        # Fetch a fresh instance to avoid cached parent relations.
        deep_menu = Menu.objects.get(pk=current_menu.pk)

        with CaptureQueriesContext(connection) as deep_queries:
            user_has_menu_access(self.user, deep_menu)

        deep_query_count = len(deep_queries)

        self.assertEqual(
            shallow_query_count,
            deep_query_count,
            msg=(
                "Menu access query count should not increase "
                "with hierarchy depth."
            ),
        )
   
    def test_parent_menu_permission_grants_child_menu_access(self):
        parent_menu = Menu.objects.create(
            module=self.module,
            name="Production",
            code="production",
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=parent_menu,
            name="Cutting",
            code="cutting",
        )

        UserPermission.objects.create(
            user=self.user,
            menu=parent_menu,
        )

        self.assertTrue(
            user_has_menu_access(self.user, parent_menu)
        )

        self.assertTrue(
            user_has_menu_access(self.user, child_menu)
        )

    def test_inactive_user_with_permission_has_no_access(self):
        self.user.is_active = False
        self.user.save()

        UserPermission.objects.create(
            user=self.user,
            menu=self.menu,
        )

        self.assertFalse(
            user_has_menu_access(self.user, self.menu)
        )
        



class ActionAccessTests(TestCase):

    def setUp(self):
        self.module = Module.objects.create(
            name="Action Test Module",
            code="action_test_module",
        )

        self.menu = Menu.objects.create(
            module=self.module,
            name="Product Setup Test",
            code="product_setup_test",
        )

        self.action = Action.objects.create(
            menu=self.menu,
            name="Edit Product",
            code="edit_product",
        )
        self.second_action = Action.objects.create(
            menu=self.menu,
            name="Delete Product",
            code="delete_product",
        )

        self.user = User.objects.create_user(
            username="action_test_user",
            password="testpassword123",
        )

    def test_direct_action_permission_grants_access(self):
        UserPermission.objects.create(
            user=self.user,
            action=self.action,
        )

        self.assertTrue(
            user_has_action_access(self.user, self.action)
        )

    def test_group_action_permission_grants_access(self):
        group = Group.objects.create(
            name="Action Test Group"
        )
        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            action=self.action,
        )

        self.assertTrue(
            user_has_action_access(self.user, self.action)
        )

    def test_module_permission_grants_action_access(self):
        UserPermission.objects.create(
            user=self.user,
            module=self.module,
        )

        self.assertTrue(
            user_has_action_access(self.user, self.action)
        )

    def test_menu_permission_grants_action_access(self):
        UserPermission.objects.create(
            user=self.user,
            menu=self.menu,
        )

        self.assertFalse(
            user_has_action_access(self.user, self.action)
        )

    def test_user_without_permission_has_no_action_access(self):
        self.assertFalse(
            user_has_action_access(self.user, self.action)
        )

    def test_inactive_action_denies_access(self):
        self.action.is_active = False
        self.action.save()

        UserPermission.objects.create(
            user=self.user,
            action=self.action,
        )

        self.assertFalse(
            user_has_action_access(self.user, self.action)
        )

    def test_inactive_menu_denies_action_access(self):
        self.menu.is_active = False
        self.menu.save()

        self.assertFalse(
            user_has_action_access(self.user, self.action)
        )

    def test_inactive_module_denies_action_access(self):
        self.module.is_active = False
        self.module.save()

        self.assertFalse(
            user_has_action_access(self.user, self.action)
        )

    def test_direct_action_permission_does_not_grant_other_action(self):
        UserPermission.objects.create(
            user=self.user,
            action=self.action,
        )

        self.assertTrue(
            user_has_action_access(self.user, self.action)
        )

        self.assertFalse(
            user_has_action_access(self.user, self.second_action)
        )


    def test_group_action_permission_does_not_grant_other_action(self):
        group = Group.objects.create(name="Limited Action Group")
        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            action=self.action,
        )

        self.assertTrue(
            user_has_action_access(self.user, self.action)
        )

        self.assertFalse(
            user_has_action_access(self.user, self.second_action)
        )

    
    def test_inactive_parent_menu_denies_action_access(self):
        parent_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Parent",
            code="inactive_parent",
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=parent_menu,
            name="Active Child",
            code="active_child",
        )

        child_action = Action.objects.create(
            menu=child_menu,
            name="Create Record",
            code="create_record",
        )

        UserPermission.objects.create(
            user=self.user,
            action=child_action,
        )

        parent_menu.is_active = False
        parent_menu.save()

        self.assertFalse(
            user_has_action_access(self.user, child_action)
        )


    def test_inactive_grandparent_denies_deep_action_access(self):
        root_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Action Root",
            code="inactive_action_root",
        )

        middle_menu = Menu.objects.create(
            module=self.module,
            parent=root_menu,
            name="Active Action Middle",
            code="active_action_middle",
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=middle_menu,
            name="Deep Action Child",
            code="deep_action_child",
        )

        child_action = Action.objects.create(
            menu=child_menu,
            name="Create Record",
            code="create_deep_record",
        )

        UserPermission.objects.create(
            user=self.user,
            action=child_action,
        )

        root_menu.is_active = False
        root_menu.save()

        self.assertFalse(
            user_has_action_access(self.user, child_action)
        )
    def test_anonymous_user_has_no_action_access(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(
            user_has_action_access(AnonymousUser(), self.action)
        )

    
    def test_inactive_action_with_direct_permission_is_denied(self):
        self.action.is_active = False
        self.action.save(update_fields=["is_active"])

        UserPermission.objects.create(
            user=self.user,
            action=self.action,
        )

        self.assertFalse(
            user_has_action_access(self.user, self.action)
        )
    def test_inactive_action_with_group_permission_is_denied(self):
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="Inactive Action Test Group")
        self.user.groups.add(group)

        self.action.is_active = False
        self.action.save(update_fields=["is_active"])

        GroupPermission.objects.create(
            group=group,
            action=self.action,
        )

        self.assertFalse(
            user_has_action_access(self.user, self.action)
        )

    def test_inactive_user_with_permission_has_no_access(self):
        self.user.is_active = False
        self.user.save()

        UserPermission.objects.create(
            user=self.user,
            action=self.action,
        )

        self.assertFalse(
            user_has_action_access(self.user, self.action)
        )



class PermissionDecoratorTests(TestCase):

    def setUp(self):
        from django.test import RequestFactory

        self.factory = RequestFactory()

        self.module = Module.objects.create(
            name="Decorator Test Module",
            code="decorator_module",
        )

        self.menu = Menu.objects.create(
            module=self.module,
            name="Decorator Test Menu",
            code="decorator_menu",
        )

        self.action = Action.objects.create(
            menu=self.menu,
            name="Decorator Test Action",
            code="decorator_action",
        )

        self.user = User.objects.create_user(
            username="decorator_test_user",
            password="testpassword123",
        )

    def get_request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_module_decorator_allows_authorized_user(self):
        from django.http import HttpResponse

        UserPermission.objects.create(
            user=self.user,
            module=self.module,
        )

        @module_required("decorator_module")
        def protected_view(request):
            return HttpResponse("OK")

        response = protected_view(self.get_request(self.user))

        self.assertEqual(response.status_code, 200)

    def test_module_decorator_denies_unauthorized_user(self):
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponse

        @module_required("decorator_module")
        def protected_view(request):
            return HttpResponse("OK")

        with self.assertRaises(PermissionDenied):
            protected_view(self.get_request(self.user))

    def test_module_decorator_denies_inactive_user(self):
        from django.http import HttpResponse

        UserPermission.objects.create(
            user=self.user,
            module=self.module,
        )

        self.user.is_active = False
        self.user.save()

        @module_required("decorator_module")
        def protected_view(request):
            return HttpResponse("Secret content")

        request = self.get_request(self.user)

        with self.assertRaises(PermissionDenied):
            protected_view(request)

    def test_menu_decorator_allows_authorized_user(self):
        from django.http import HttpResponse

        UserPermission.objects.create(
            user=self.user,
            menu=self.menu,
        )

        @menu_required("decorator_module", "decorator_menu")
        def protected_view(request):
            return HttpResponse("OK")

        response = protected_view(self.get_request(self.user))

        self.assertEqual(response.status_code, 200)

    def test_menu_decorator_denies_unauthorized_user(self):
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponse

        @menu_required("decorator_module", "decorator_menu")
        def protected_view(request):
            return HttpResponse("OK")

        with self.assertRaises(PermissionDenied):
            protected_view(self.get_request(self.user))

    def test_action_decorator_allows_authorized_user(self):
        from django.http import HttpResponse

        UserPermission.objects.create(
            user=self.user,
            action=self.action,
        )

        @action_required(
                "decorator_module",
                "decorator_menu",
                "decorator_action",
            )
        def protected_view(request):
            return HttpResponse("OK")

        response = protected_view(self.get_request(self.user))

        self.assertEqual(response.status_code, 200)

    def test_action_decorator_denies_unauthorized_user(self):
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponse

        @action_required(
                "decorator_module",
                "decorator_menu",
                "decorator_action",
            )
        def protected_view(request):
            return HttpResponse("OK")

        with self.assertRaises(PermissionDenied):
            protected_view(self.get_request(self.user))

    def test_decorators_redirect_anonymous_users_to_login(self):
        from django.contrib.auth.models import AnonymousUser

        @module_required("decorator_module")
        def protected_view(request):
            from django.http import HttpResponse
            return HttpResponse("OK")

        response = protected_view(
            self.get_request(AnonymousUser())
        )

        self.assertEqual(response.status_code, 302)


    def test_menu_decorator_uses_correct_module(self):
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponse

        another_module = Module.objects.create(
            name="Another Decorator Module",
            code="another_decorator_module",
        )

        another_menu = Menu.objects.create(
            module=another_module,
            name="Same Menu Code",
            code="decorator_menu",
        )

        # Grant permission only for the menu in another module.
        UserPermission.objects.create(
            user=self.user,
            menu=another_menu,
        )

        @menu_required("decorator_module", "decorator_menu")
        def protected_view(request):
            return HttpResponse("OK")

        with self.assertRaises(PermissionDenied):
            protected_view(self.get_request(self.user))

    def test_action_decorator_uses_correct_menu(self):
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponse

        another_menu = Menu.objects.create(
            module=self.module,
            name="Another Decorator Menu",
            code="another_decorator_menu",
        )

        another_action = Action.objects.create(
            menu=another_menu,
            name="Same Action Code",
            code="decorator_action",
        )

        # Grant permission only for the action in another menu.
        UserPermission.objects.create(
            user=self.user,
            action=another_action,
        )

        @action_required(
            "decorator_module",
            "decorator_menu",
            "decorator_action",
        )
        def protected_view(request):
            return HttpResponse("OK")

        with self.assertRaises(PermissionDenied):
            protected_view(self.get_request(self.user))


    def test_action_decorator_allows_authorized_url_request(self):
        from django.test import override_settings
        from django.urls import reverse

        UserPermission.objects.create(
            user=self.user,
            action=self.action,
        )

        self.client.force_login(self.user)

        with override_settings(ROOT_URLCONF="access_control.test_urls"):
            response = self.client.get(
                reverse("test_protected_action")
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Access granted")


    def test_action_decorator_denies_unauthorized_url_request(self):
        from django.test import override_settings
        from django.urls import reverse

        self.client.force_login(self.user)

        with override_settings(ROOT_URLCONF="access_control.test_urls"):
            response = self.client.get(
                reverse("test_protected_action")
            )

        self.assertEqual(response.status_code, 403)

    def test_action_decorator_redirects_anonymous_url_request(self):
        from django.test import override_settings
        from django.urls import reverse

        with override_settings(
            ROOT_URLCONF="access_control.test_urls",
            LOGIN_URL="/accounts/login/",
        ):
            response = self.client.get(
                reverse("test_protected_action")
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_menu_decorator_denies_inactive_user(self):
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponse

        UserPermission.objects.create(
            user=self.user,
            menu=self.menu,
        )

        self.user.is_active = False
        self.user.save()

        @menu_required("decorator_module", "decorator_menu")
        def protected_view(request):
            return HttpResponse("Secret content")

        with self.assertRaises(PermissionDenied):
            protected_view(self.get_request(self.user))

    def test_action_decorator_denies_inactive_user(self):
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponse

        UserPermission.objects.create(
            user=self.user,
            action=self.action,
        )

        self.user.is_active = False
        self.user.save()

        @action_required(
            "decorator_module",
            "decorator_menu",
            "decorator_action",
        )
        def protected_view(request):
            return HttpResponse("Secret content")

        with self.assertRaises(PermissionDenied):
            protected_view(self.get_request(self.user))


class AccessControlDashboardViewTests(TestCase):

    def setUp(self):
        self.module = Module.objects.create(
            name="Access Control Dashboard",
            code="access_control",
        )

        self.user = User.objects.create_user(
            username="dashboard_user",
            password="TestPassword123!",
        )

        UserPermission.objects.create(
            user=self.user,
            module=self.module,
        )

    
    def test_dashboard_renders_html_for_authorized_user(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get("/access-control/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "text/html; charset=utf-8",
        )

        self.assertTemplateUsed(
            response,
            "access_control/home.html",
        )

        self.assertIn("dashboard", response.context)

        dashboard = response.context["dashboard"]

        self.assertIn("modules", dashboard)
        self.assertIn("menus", dashboard)
        self.assertIn("actions", dashboard)
        self.assertIn("group_permissions", dashboard)
        self.assertIn("user_permissions", dashboard)


    def test_dashboard_denies_user_without_module_permission(self):
        unauthorized_user = User.objects.create_user(
            username="unauthorized_dashboard_user",
            password="TestPassword123!",
        )

        self.client.login(
            username="unauthorized_dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get("/access-control/")

        self.assertEqual(response.status_code, 403)

    def test_dashboard_redirects_anonymous_user(self):
        response = self.client.get("/access-control/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_module_list_returns_accessible_modules(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("modules", response.json()["data"])

        modules = response.json()["data"]["modules"]

        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0]["code"], self.module.code)
    def test_module_list_sorts_by_name_ascending(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "name",
                "sort_dir": "asc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        module_names = [module["name"] for module in modules]

        self.assertEqual(module_names, sorted(module_names))
    def test_module_list_sorts_by_name_descending(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "name",
                "sort_dir": "desc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        module_names = [module["name"] for module in modules]

        self.assertEqual(module_names, sorted(module_names, reverse=True))
    def test_module_list_sorts_by_description_ascending(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "description",
                "sort_dir": "asc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        descriptions = [module["description"] or "" for module in modules]

        self.assertEqual(descriptions, sorted(descriptions))
    def test_module_list_sorts_by_sort_order_ascending(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "sort_order",
                "sort_dir": "asc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        sort_orders = [module["sort_order"] for module in modules]

        self.assertEqual(sort_orders, sorted(sort_orders))
    def test_module_list_sorts_by_sort_order_descending(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "sort_order",
                "sort_dir": "desc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        sort_orders = [module["sort_order"] for module in modules]

        self.assertEqual(sort_orders, sorted(sort_orders, reverse=True))

    def test_module_list_sorts_by_status_ascending(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "is_active",
                "sort_dir": "asc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        statuses = [module["is_active"] for module in modules]

        self.assertEqual(statuses, sorted(statuses))

    def test_module_list_sorts_by_status_descending(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "is_active",
                "sort_dir": "desc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        statuses = [module["is_active"] for module in modules]

        self.assertEqual(statuses, sorted(statuses, reverse=True))

    def test_module_list_rejects_invalid_sort_field(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "invalid_field",
                "sort_dir": "asc",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertIn("Invalid sorting field.", response.json()["message"])

    def test_module_list_rejects_invalid_sort_direction(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "name",
                "sort_dir": "sideways",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertIn("Invalid sorting direction.", response.json()["message"])

    def test_module_list_sorts_search_results_by_name_ascending(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "search": "access",
                "sort_by": "name",
                "sort_dir": "asc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        self.assertTrue(
            all("access" in module["name"].lower() for module in modules)
        )

        module_names = [module["name"] for module in modules]

        self.assertEqual(module_names, sorted(module_names))

    def test_module_list_sorts_before_pagination(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
            sort_order=2,
        )

        inventory_module = Module.objects.create(
            name="Inventory",
            code="inventory",
            sort_order=3,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inventory_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response_page_1 = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "name",
                "sort_dir": "asc",
                "page": 1,
                "page_size": 2,
            },
        )

        response_page_2 = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "all",
                "sort_by": "name",
                "sort_dir": "asc",
                "page": 2,
                "page_size": 2,
            },
        )

        self.assertEqual(response_page_1.status_code, 200)
        self.assertEqual(response_page_2.status_code, 200)

        modules_page_1 = response_page_1.json()["data"]["modules"]
        modules_page_2 = response_page_2.json()["data"]["modules"]

        page_1_names = [module["name"] for module in modules_page_1]
        page_2_names = [module["name"] for module in modules_page_2]

        combined_names = page_1_names + page_2_names

        self.assertEqual(combined_names, sorted(combined_names))

        self.assertEqual(len(page_1_names), 2)
        self.assertEqual(len(page_2_names), 1)

        pagination_page_1 = response_page_1.json()["data"]["pagination"]
        pagination_page_2 = response_page_2.json()["data"]["pagination"]

        self.assertEqual(pagination_page_1["total_items"], 3)
        self.assertEqual(pagination_page_1["total_pages"], 2)
        self.assertTrue(pagination_page_1["has_next"])
        self.assertFalse(pagination_page_1["has_previous"])

        self.assertEqual(pagination_page_2["page"], 2)
        self.assertFalse(pagination_page_2["has_next"])
        self.assertTrue(pagination_page_2["has_previous"])
    def test_module_list_paginates_results(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
            sort_order=2,
        )

        inventory_module = Module.objects.create(
            name="Inventory",
            code="inventory",
            sort_order=3,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inventory_module,
        )
        

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "page": 1,
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["modules"]), 2)
        self.assertEqual(data["pagination"]["page"], 1)
        self.assertEqual(data["pagination"]["page_size"], 2)
        self.assertEqual(data["pagination"]["total_items"], 3)
        self.assertEqual(data["pagination"]["total_pages"], 2)
        self.assertTrue(data["pagination"]["has_next"])
        self.assertFalse(data["pagination"]["has_previous"])

    def test_module_list_search_by_name(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
            description="Manage garment production",
            sort_order=2,
        )

        inventory_module = Module.objects.create(
            name="Inventory",
            code="inventory",
            description="Manage raw materials",
            sort_order=3,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inventory_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"search": "Production"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["modules"]), 1)
        self.assertEqual(data["modules"][0]["name"], "Production")
        self.assertEqual(data["pagination"]["total_items"], 1)

    def test_module_list_search_by_code(self):
        production_module = Module.objects.create(
            name="Production Management",
            code="production",
            description="Manage garment production",
            sort_order=2,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"search": "production"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["modules"]), 1)
        self.assertEqual(data["modules"][0]["code"], "production")
        self.assertEqual(data["pagination"]["total_items"], 1)


    def test_module_list_search_by_description(self):
        production_module = Module.objects.create(
            name="Production Management",
            code="production",
            description="Manage garment production workflow",
            sort_order=2,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"search": "workflow"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["modules"]), 1)
        self.assertEqual(data["modules"][0]["code"], "production")
        self.assertEqual(data["pagination"]["total_items"], 1)

    def test_module_list_search_returns_no_results(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"search": "nonexistent_module_xyz"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["modules"], [])
        self.assertEqual(data["pagination"]["total_items"], 0)
        self.assertEqual(data["pagination"]["total_pages"], 1)
        self.assertFalse(data["pagination"]["has_next"])
        self.assertFalse(data["pagination"]["has_previous"])

    def test_module_list_search_combines_with_pagination(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
            description="Manage garment production",
            sort_order=2,
        )

        production_planning_module = Module.objects.create(
            name="Production Planning",
            code="production_planning",
            description="Plan production schedules",
            sort_order=3,
        )

        production_tracking_module = Module.objects.create(
            name="Production Tracking",
            code="production_tracking",
            description="Track production progress",
            sort_order=4,
        )

        inventory_module = Module.objects.create(
            name="Inventory",
            code="inventory",
            description="Manage raw materials",
            sort_order=5,
        )

        UserPermission.objects.bulk_create([
            UserPermission(
                user=self.user,
                module=production_module,
            ),
            UserPermission(
                user=self.user,
                module=production_planning_module,
            ),
            UserPermission(
                user=self.user,
                module=production_tracking_module,
            ),
            UserPermission(
                user=self.user,
                module=inventory_module,
            ),
        ])

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "search": "production",
                "page": 1,
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["modules"]), 2)
        self.assertEqual(data["pagination"]["page"], 1)
        self.assertEqual(data["pagination"]["page_size"], 2)
        self.assertEqual(data["pagination"]["total_items"], 3)
        self.assertEqual(data["pagination"]["total_pages"], 2)
        self.assertTrue(data["pagination"]["has_next"])
        self.assertFalse(data["pagination"]["has_previous"])

        returned_codes = [
            module["code"]
            for module in data["modules"]
        ]

        self.assertEqual(
            returned_codes,
            ["production", "production_planning"],
        )

    def test_module_list_search_does_not_bypass_permissions(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
            description="Manage garment production",
            sort_order=2,
        )

        inventory_module = Module.objects.create(
            name="Inventory",
            code="inventory",
            description="Manage raw materials",
            sort_order=3,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"search": "Inventory"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["modules"], [])
        self.assertEqual(data["pagination"]["total_items"], 0)

    def test_module_list_search_is_case_insensitive(self):
        production_module = Module.objects.create(
            name="Production Management",
            code="production",
            description="Manage garment production",
            sort_order=2,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"search": "PRODUCTION"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["modules"]), 1)
        self.assertEqual(data["modules"][0]["code"], "production")
        self.assertEqual(data["pagination"]["total_items"], 1)

    def test_module_list_search_ignores_whitespace(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"search": "   "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["modules"]), 1)
        self.assertEqual(data["modules"][0]["code"], self.module.code)
        self.assertEqual(data["pagination"]["total_items"], 1)

    def test_module_list_returns_second_page(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
            sort_order=2,
        )

        inventory_module = Module.objects.create(
            name="Inventory",
            code="inventory",
            sort_order=3,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inventory_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "page": 2,
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["modules"]), 1)
        self.assertEqual(data["pagination"]["page"], 2)
        self.assertEqual(data["pagination"]["page_size"], 2)
        self.assertEqual(data["pagination"]["total_items"], 3)
        self.assertEqual(data["pagination"]["total_pages"], 2)
        self.assertFalse(data["pagination"]["has_next"])
        self.assertTrue(data["pagination"]["has_previous"])

    def test_module_list_handles_invalid_page_number(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "page": "invalid",
                "page_size": 20,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page"], 1)
        self.assertEqual(data["pagination"]["total_items"], 1)
        self.assertEqual(data["pagination"]["total_pages"], 1)
        self.assertFalse(data["pagination"]["has_next"])
        self.assertFalse(data["pagination"]["has_previous"])

    def test_module_list_denies_unauthorized_user(self):
        unauthorized_user = User.objects.create_user(
            username="unauthorized_module_user",
            password="testpass123",
        )

        self.client.login(
            username="unauthorized_module_user",
            password="testpass123",
        )

        response = self.client.get(
            reverse("access_control:module_list")

        )

        self.assertEqual(response.status_code, 403)

    def test_module_list_excludes_inactive_modules(self):
        inactive_module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inactive_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list")
        )

        self.assertEqual(response.status_code, 200)

        modules = response.json()["data"]["modules"]

        returned_codes = [
            module["code"]
            for module in modules
        ]

        self.assertIn(self.module.code, returned_codes)
        self.assertNotIn(inactive_module.code, returned_codes)

    def test_module_list_returns_only_group_permitted_modules(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        inventory_module = Module.objects.create(
            name="Inventory",
            code="inventory",
        )

        production_group = Group.objects.create(
            name="Production Team",
        )

        normal_user = User.objects.create_user(
            username="group_module_api_user",
            password="testpassword123",
        )

        normal_user.groups.add(production_group)

        # Grant the group access to the Access Control module.
        GroupPermission.objects.create(
            group=production_group,
            module=self.module,
        )

        # Grant the group access to Production only.
        GroupPermission.objects.create(
            group=production_group,
            module=production_module,
        )

        self.client.logout()

        self.client.login(
            username="group_module_api_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse("access_control:module_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        returned_codes = {
            module["code"]
            for module in modules
        }

        self.assertIn("access_control", returned_codes)
        self.assertIn("production", returned_codes)
        self.assertNotIn("inventory", returned_codes)

        self.assertEqual(len(modules), 2)

    def test_module_list_filters_inactive_modules(self):
        inactive_module = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inactive_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": "inactive"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        returned_codes = [
            module["code"]
            for module in modules
        ]

        self.assertIn(inactive_module.code, returned_codes)
        self.assertNotIn(self.module.code, returned_codes)

    def test_module_list_filters_active_modules(self):
        inactive_module = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inactive_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": "active"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        returned_codes = [
            module["code"]
            for module in modules
        ]

        self.assertIn(self.module.code, returned_codes)
        self.assertNotIn(inactive_module.code, returned_codes)

    def test_module_list_filters_all_modules(self):
        inactive_module = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inactive_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": "all"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        returned_codes = [
            module["code"]
            for module in modules
        ]

        self.assertIn(self.module.code, returned_codes)
        self.assertIn(inactive_module.code, returned_codes)
        self.assertEqual(len(modules), 2)

    def test_module_list_rejects_invalid_status(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": "invalid"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertEqual(
            response.json()["message"],
            "Invalid status filter.",
        )
        self.assertEqual(
            response.json()["allowed_values"],
            ["active", "inactive", "all"],
        )
    def test_superuser_can_list_all_modules_with_all_status(self):
        inactive_module = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        superuser = User.objects.create_superuser(
            username="module_superuser",
            password="TestPassword123!",
        )

        self.client.login(
            username="module_superuser",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": "all"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        returned_codes = [
            module["code"]
            for module in modules
        ]

        self.assertIn(self.module.code, returned_codes)
        self.assertIn(inactive_module.code, returned_codes)
        self.assertEqual(len(modules), 2)

    def test_superuser_can_list_only_active_modules_with_active_status(self):
        inactive_module = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        superuser = User.objects.create_superuser(
            username="module_superuser",
            password="TestPassword123!",
        )

        self.client.login(
            username="module_superuser",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": "active"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        returned_codes = [
            module["code"]
            for module in modules
        ]

        self.assertIn(self.module.code, returned_codes)
        self.assertNotIn(inactive_module.code, returned_codes)
        self.assertEqual(len(modules), 1)

    def test_superuser_can_list_only_inactive_modules_with_inactive_status(self):
        inactive_module = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        superuser = User.objects.create_superuser(
            username="module_superuser",
            password="TestPassword123!",
        )

        self.client.login(
            username="module_superuser",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": "inactive"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]

        returned_codes = [
            module["code"]
            for module in modules
        ]

        self.assertIn(inactive_module.code, returned_codes)
        self.assertNotIn(self.module.code, returned_codes)
        self.assertEqual(len(modules), 1)

    def test_module_list_shows_inactive_modules_with_group_permission(self):
        inactive_module = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        group = Group.objects.create(name="Inactive Module Viewers")
        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            module=inactive_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": "inactive"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]
        returned_codes = [module["code"] for module in modules]

        self.assertIn(inactive_module.code, returned_codes)
        self.assertNotIn(self.module.code, returned_codes)
        self.assertEqual(len(modules), 1)

    def test_module_list_all_status_respects_permission_isolation(self):
        inactive_module = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        unauthorized_module = Module.objects.create(
            name="Secret Module",
            code="secret_module",
        )

        UserPermission.objects.create(
            user=self.user,
            module=inactive_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": "all"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]
        returned_codes = [module["code"] for module in modules]

        self.assertIn(self.module.code, returned_codes)
        self.assertIn(inactive_module.code, returned_codes)
        self.assertNotIn(unauthorized_module.code, returned_codes)

    def test_module_list_all_status_respects_group_permission_isolation(self):
        inactive_module = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        unauthorized_module = Module.objects.create(
            name="Secret Module",
            code="secret_module",
        )

        group = Group.objects.create(name="Inactive Module Viewers")
        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            module=inactive_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": "all"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]
        returned_codes = [module["code"] for module in modules]

        self.assertIn(self.module.code, returned_codes)
        self.assertIn(inactive_module.code, returned_codes)
        self.assertNotIn(unauthorized_module.code, returned_codes)

    def test_module_list_normalizes_status_parameter(self):
        inactive_module = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inactive_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {"status": " ACTIVE "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        modules = response.json()["data"]["modules"]
        returned_codes = [module["code"] for module in modules]

        self.assertIn(self.module.code, returned_codes)
        self.assertNotIn(inactive_module.code, returned_codes)

    def test_module_list_inactive_status_works_with_pagination(self):
        inactive_module_1 = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            is_active=False,
        )

        inactive_module_2 = Module.objects.create(
            name="Inactive Inventory",
            code="inactive_inventory",
            is_active=False,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inactive_module_1,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inactive_module_2,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "inactive",
                "page": 2,
                "page_size": 1,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]
        modules = data["modules"]
        pagination = data["pagination"]

        self.assertEqual(len(modules), 1)
        self.assertEqual(pagination["page"], 2)
        self.assertEqual(pagination["page_size"], 1)
        self.assertEqual(pagination["total_items"], 2)
        self.assertEqual(pagination["total_pages"], 2)
        self.assertTrue(pagination["has_previous"])
        self.assertFalse(pagination["has_next"])

        returned_codes = [module["code"] for module in modules]

        self.assertNotIn(self.module.code, returned_codes)

    def test_module_list_inactive_status_works_with_search(self):
        inactive_production = Module.objects.create(
            name="Inactive Production",
            code="inactive_production",
            description="Production module",
            is_active=False,
        )

        inactive_inventory = Module.objects.create(
            name="Inactive Inventory",
            code="inactive_inventory",
            description="Inventory module",
            is_active=False,
        )

        active_production = Module.objects.create(
            name="Active Production",
            code="active_production",
            description="Production module",
            is_active=True,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inactive_production,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inactive_inventory,
        )

        UserPermission.objects.create(
            user=self.user,
            module=active_production,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "status": "inactive",
                "search": "production",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]
        modules = data["modules"]
        pagination = data["pagination"]

        returned_codes = [module["code"] for module in modules]

        self.assertIn(inactive_production.code, returned_codes)
        self.assertNotIn(inactive_inventory.code, returned_codes)
        self.assertNotIn(active_production.code, returned_codes)
        self.assertNotIn(self.module.code, returned_codes)

        self.assertEqual(pagination["total_items"], 1)
        self.assertEqual(pagination["total_pages"], 1)


    
    def test_module_list_limits_page_size_to_100(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "page": 1,
                "page_size": 500,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page_size"], 100)
        self.assertEqual(data["pagination"]["total_items"], 1)
        self.assertEqual(len(data["modules"]), 1)

    def test_module_list_enforces_minimum_page_size(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "page": 1,
                "page_size": -5,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page_size"], 1)
        self.assertEqual(len(data["modules"]), 1)

    def test_module_list_handles_invalid_page_size(self):
        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "page": 1,
                "page_size": "abc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page_size"], 20)
        self.assertEqual(data["pagination"]["total_items"], 1)
        self.assertEqual(len(data["modules"]), 1)

    def test_module_list_returns_modules_in_sort_order(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
            sort_order=3,
        )

        inventory_module = Module.objects.create(
            name="Inventory",
            code="inventory",
            sort_order=2,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        UserPermission.objects.create(
            user=self.user,
            module=inventory_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("access_control:module_list"),
            {
                "page": 1,
                "page_size": 20,
            },
        )

        self.assertEqual(response.status_code, 200)

        modules = response.json()["data"]["modules"]

        module_codes = [module["code"] for module in modules]

        self.assertEqual(
            module_codes,
            [
                "access_control",
                "inventory",
                "production",
            ],
        )

class AccessControlDashboardServiceTests(TestCase):

    def test_dashboard_stats_returns_correct_counts(self):
        module = Module.objects.create(
            name="Dashboard Service Module",
            code="dashboard_service_module",
        )

        menu = Menu.objects.create(
            module=module,
            name="Dashboard Service Menu",
            code="dashboard_service_menu",
        )

        Action.objects.create(
            menu=menu,
            name="Dashboard Service Action",
            code="dashboard_service_action",
        )

        group = Group.objects.create(
            name="Dashboard Service Group",
        )

        GroupPermission.objects.create(
            group=group,
            module=module,
        )

        user = User.objects.create_user(
            username="dashboard_service_user",
            password="TestPassword123!",
        )

        UserPermission.objects.create(
            user=user,
            menu=menu,
        )

        stats = get_access_control_dashboard_stats()

        self.assertEqual(stats["modules"], 1)
        self.assertEqual(stats["menus"], 1)
        self.assertEqual(stats["actions"], 1)
        self.assertEqual(stats["group_permissions"], 1)
        self.assertEqual(stats["user_permissions"], 1)

    def test_dashboard_stats_returns_zero_when_empty(self):
        stats = get_access_control_dashboard_stats()

        self.assertEqual(stats["modules"], 0)
        self.assertEqual(stats["menus"], 0)
        self.assertEqual(stats["actions"], 0)
        self.assertEqual(stats["group_permissions"], 0)
        self.assertEqual(stats["user_permissions"], 0)

    def test_dashboard_stats_update_after_records_are_created(self):
        stats_before = get_access_control_dashboard_stats()

        self.assertEqual(stats_before["modules"], 0)

        Module.objects.create(
            name="New Dashboard Module",
            code="new_dashboard_module",
        )

        stats_after = get_access_control_dashboard_stats()

        self.assertEqual(stats_after["modules"], 1)

    def test_dashboard_stats_uses_five_queries(self):
        with self.assertNumQueries(5):
            get_access_control_dashboard_stats()

class AccessibleModulesServiceTests(TestCase):

    def setUp(self):
        self.module_one = Module.objects.create(
            name="Module One",
            code="module_one",
            sort_order=1,
        )

        self.module_two = Module.objects.create(
            name="Module Two",
            code="module_two",
            sort_order=2,
        )

        self.inactive_module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
            sort_order=3,
        )

        self.user = User.objects.create_user(
            username="accessible_modules_user",
            password="TestPassword123!",
        )

    def test_user_sees_directly_permitted_modules(self):
        UserPermission.objects.create(
            user=self.user,
            module=self.module_two,
        )

        UserPermission.objects.create(
            user=self.user,
            module=self.module_one,
        )

        modules = get_accessible_modules(self.user)

        self.assertEqual(
            list(modules),
            [self.module_one, self.module_two],
        )

    def test_user_sees_group_permitted_modules(self):
        group = Group.objects.create(
            name="Module Access Group",
        )

        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            module=self.module_two,
        )

        modules = get_accessible_modules(self.user)

        self.assertEqual(
            list(modules),
            [self.module_two],
        )

    def test_user_sees_direct_and_group_permitted_modules(self):
        group = Group.objects.create(
            name="Combined Module Group",
        )

        self.user.groups.add(group)

        UserPermission.objects.create(
            user=self.user,
            module=self.module_one,
        )

        GroupPermission.objects.create(
            group=group,
            module=self.module_two,
        )

        modules = get_accessible_modules(self.user)

        self.assertEqual(
            list(modules),
            [self.module_one, self.module_two],
        )

    def test_inactive_modules_are_never_returned(self):
        UserPermission.objects.create(
            user=self.user,
            module=self.inactive_module,
        )

        modules = get_accessible_modules(self.user)

        self.assertNotIn(
            self.inactive_module,
            modules,
        )

    def test_superuser_sees_all_active_modules(self):
        self.user.is_superuser = True
        self.user.save()

        modules = get_accessible_modules(self.user)

        self.assertEqual(
            list(modules),
            [self.module_one, self.module_two],
        )

    def test_user_without_permissions_sees_no_modules(self):
        modules = get_accessible_modules(self.user)

        self.assertEqual(
            modules.count(),
            0,
        )

    def test_inactive_user_with_permission_sees_no_modules(self):
        self.user.is_active = False
        self.user.save()

        UserPermission.objects.create(
            user=self.user,
            module=self.module_one,
        )

        modules = get_accessible_modules(self.user)

        self.assertEqual(modules.count(), 0)


class AccessibleMenusServiceTests(TestCase):

    def setUp(self):
        self.module = Module.objects.create(
            name="Accessible Menus Module",
            code="accessible_menus_module",
        )

        self.parent = Menu.objects.create(
            module=self.module,
            name="Production",
            code="production",
        )

        self.child = Menu.objects.create(
            module=self.module,
            parent=self.parent,
            name="Cutting",
            code="cutting",
        )

        self.grandchild = Menu.objects.create(
            module=self.module,
            parent=self.child,
            name="Cutting Planning",
            code="cutting_planning",
        )

        self.user = User.objects.create_user(
            username="accessible_menu_user",
            password="testpassword123",
        )

    def test_direct_parent_permission_returns_descendants(self):
        UserPermission.objects.create(
            user=self.user,
            menu=self.parent,
        )

        menus = get_accessible_menus(
            self.user,
            self.module,
        )

        returned_ids = set(menus.values_list("id", flat=True))

        self.assertEqual(
            returned_ids,
            {
                self.parent.id,
                self.child.id,
                self.grandchild.id,
            },
        )

    def test_child_permission_returns_ancestor_navigation(self):
        UserPermission.objects.create(
            user=self.user,
            menu=self.grandchild,
        )

        menus = get_accessible_menus(
            self.user,
            self.module,
        )

        returned_ids = set(menus.values_list("id", flat=True))

        self.assertEqual(
            returned_ids,
            {
                self.parent.id,
                self.child.id,
                self.grandchild.id,
            },
        )

    def test_group_menu_permission_returns_accessible_hierarchy(self):
        group = Group.objects.create(
            name="Accessible Menus Group",
        )
        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            menu=self.child,
        )

        menus = get_accessible_menus(
            self.user,
            self.module,
        )

        returned_ids = set(menus.values_list("id", flat=True))

        self.assertEqual(
            returned_ids,
            {
                self.parent.id,
                self.child.id,
                self.grandchild.id,
            },
        )

    def test_action_permission_returns_menu_and_ancestors(self):
        action = Action.objects.create(
            menu=self.grandchild,
            name="Create Plan",
            code="create_plan",
        )

        UserPermission.objects.create(
            user=self.user,
            action=action,
        )

        menus = get_accessible_menus(
            self.user,
            self.module,
        )

        returned_ids = set(menus.values_list("id", flat=True))

        self.assertEqual(
            returned_ids,
            {
                self.parent.id,
                self.child.id,
                self.grandchild.id,
            },
        )

    def test_inactive_menus_are_never_returned(self):
        self.child.is_active = False
        self.child.save()

        UserPermission.objects.create(
            user=self.user,
            menu=self.parent,
        )

        menus = get_accessible_menus(
            self.user,
            self.module,
        )

        returned_ids = set(menus.values_list("id", flat=True))

        self.assertEqual(
            returned_ids,
            {self.parent.id},
        )

    def test_user_without_permissions_gets_no_menus(self):
        menus = get_accessible_menus(
            self.user,
            self.module,
        )

        self.assertEqual(menus.count(), 0)

    def test_superuser_gets_all_active_menus(self):
        self.user.is_superuser = True
        self.user.save()

        menus = get_accessible_menus(
            self.user,
            self.module,
        )

        self.assertEqual(menus.count(), 3)

    def test_inactive_user_with_permission_sees_no_menus(self):
        self.user.is_active = False
        self.user.save()

        UserPermission.objects.create(
            user=self.user,
            menu=self.parent,
        )

        menus = get_accessible_menus(self.user, self.module)

        self.assertEqual(menus.count(), 0)





class MenuListViewTests(TestCase):

    def setUp(self):

        Module.objects.create(
            name="Access Control",
            code="access_control",
            is_active=True,
        )
        self.module = Module.objects.create(
            name="Menu API Module",
            code="menu_api_module",
        )

        self.parent = Menu.objects.create(
            module=self.module,
            name="Production",
            code="production",
        )

        self.child = Menu.objects.create(
            module=self.module,
            parent=self.parent,
            name="Cutting",
            code="cutting",
        )

        self.user = User.objects.create_user(
            username="menu_api_user",
            password="testpassword123",
            is_superuser=True,
        )

        self.client.login(
            username="menu_api_user",
            password="testpassword123",
        )

    def test_menu_list_returns_all_active_menus_for_superuser(self):
        response = self.client.get(
            reverse(
                "access_control:menu_list",
                args=[self.module.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]["menus"]), 2)

    def test_menu_list_returns_parent_child_relationship(self):
        response = self.client.get(
            reverse(
                "access_control:menu_list",
                args=[self.module.id],
            )
        )

        menus = response.json()["data"]["menus"]

        parent_data = next(
            menu for menu in menus
            if menu["id"] == self.parent.id
        )

        child_data = next(
            menu for menu in menus
            if menu["id"] == self.child.id
        )

        self.assertIsNone(parent_data["parent_id"])
        self.assertEqual(child_data["parent_id"], self.parent.id)

    def test_menu_list_does_not_return_inactive_menus(self):
        self.child.is_active = False
        self.child.save()

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                args=[self.module.id],
            )
        )

        menus = response.json()["data"]["menus"]

        self.assertEqual(len(menus), 1)
        self.assertEqual(menus[0]["id"], self.parent.id)

    def test_menu_list_returns_404_for_missing_module(self):
        response = self.client.get(
            reverse(
                "access_control:menu_list",
                args=[999999],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["success"])

    def test_menu_list_requires_login(self):
        self.client.logout()

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                args=[self.module.id],
            )
        )

        self.assertEqual(response.status_code, 302)
    def test_menu_list_returns_child_menus_for_parent_menu_permission(self):
        normal_user = User.objects.create_user(
            username="parent_menu_api_user",
            password="testpassword123",
        )

        # Allow access to the Access Control module.
        UserPermission.objects.create(
            user=normal_user,
            module=Module.objects.get(code="access_control"),
        )

        # Grant permission to the parent menu only.
        UserPermission.objects.create(
            user=normal_user,
            menu=self.parent,
        )

        self.client.logout()

        self.client.login(
            username="parent_menu_api_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                args=[self.module.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        menu_ids = {
            menu["id"]
            for menu in menus
        }

        self.assertIn(self.parent.id, menu_ids)
        self.assertIn(self.child.id, menu_ids)

        self.assertEqual(len(menus), 2)

    def test_menu_list_returns_child_menus_for_group_parent_menu_permission(self):
        from django.contrib.auth.models import Group

        production_group = Group.objects.create(
            name="Production Team",
        )

        normal_user = User.objects.create_user(
            username="group_parent_menu_api_user",
            password="testpassword123",
        )

        normal_user.groups.add(production_group)

        # Allow the group to access the Access Control module.
        GroupPermission.objects.create(
            group=production_group,
            module=Module.objects.get(code="access_control"),
        )

        # Grant permission to the parent menu only.
        GroupPermission.objects.create(
            group=production_group,
            menu=self.parent,
        )

        self.client.logout()

        self.client.login(
            username="group_parent_menu_api_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                args=[self.module.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        menu_ids = {
            menu["id"]
            for menu in menus
        }

        self.assertIn(self.parent.id, menu_ids)
        self.assertIn(self.child.id, menu_ids)

        self.assertEqual(len(menus), 2)
    def test_menu_list_does_not_return_unrelated_menu_branch(self):
        # Create an unrelated menu branch.
        inventory_menu = Menu.objects.create(
            module=self.module,
            name="Inventory",
            code="inventory",
        )

        inventory_child = Menu.objects.create(
            module=self.module,
            parent=inventory_menu,
            name="Stock",
            code="stock",
        )

        normal_user = User.objects.create_user(
            username="menu_isolation_user",
            password="testpassword123",
        )

        # Allow access to the Access Control module.
        UserPermission.objects.create(
            user=normal_user,
            module=Module.objects.get(code="access_control"),
        )

        # Grant permission only to the Production branch.
        UserPermission.objects.create(
            user=normal_user,
            menu=self.parent,
        )

        self.client.logout()

        self.client.login(
            username="menu_isolation_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                args=[self.module.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        menu_ids = {
            menu["id"]
            for menu in menus
        }

        # Production branch must be accessible.
        self.assertIn(self.parent.id, menu_ids)
        self.assertIn(self.child.id, menu_ids)

        # Inventory branch must not be exposed.
        self.assertNotIn(inventory_menu.id, menu_ids)
        self.assertNotIn(inventory_child.id, menu_ids)

        self.assertEqual(len(menus), 2)
    def test_menu_list_paginates_results(self):
        menus = []

        for index in range(3):
            menus.append(
                Menu.objects.create(
                    module=self.module,
                    name=f"Menu {index + 1}",
                    code=f"menu_{index + 1}",
                    sort_order=index + 1,
                )
            )

        self.client.login(
            username=self.user.username,
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "page": 1,
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["menus"]), 2)
        self.assertEqual(data["pagination"]["page"], 1)
        self.assertEqual(data["pagination"]["page_size"], 2)
        self.assertEqual(data["pagination"]["total_items"], 5)
        self.assertEqual(data["pagination"]["total_pages"], 3)      
        self.assertTrue(data["pagination"]["has_next"])
        self.assertFalse(data["pagination"]["has_previous"])

    def test_menu_list_returns_second_page(self):
        for index in range(3):
            Menu.objects.create(
                module=self.module,
                name=f"Menu {index + 1}",
                code=f"menu_{index + 1}",
                sort_order=index + 1,
            )

        self.client.login(
            username=self.user.username,
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "page": 2,
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["menus"]), 2)
        self.assertEqual(data["pagination"]["page"], 2)
        self.assertEqual(data["pagination"]["page_size"], 2)
        self.assertEqual(data["pagination"]["total_items"], 5)
        self.assertEqual(data["pagination"]["total_pages"], 3)
        self.assertTrue(data["pagination"]["has_next"])
        self.assertTrue(data["pagination"]["has_previous"])

    def test_menu_list_handles_invalid_page_number(self):
        self.client.login(
            username=self.user.username,
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "page": "invalid",
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page"], 1)
        self.assertEqual(data["pagination"]["page_size"], 2)
        self.assertEqual(data["pagination"]["total_items"], 2)
        self.assertEqual(data["pagination"]["total_pages"], 1)
        self.assertFalse(data["pagination"]["has_next"])
        self.assertFalse(data["pagination"]["has_previous"])

    def test_menu_list_limits_page_size_to_100(self):
        self.client.login(
            username=self.user.username,
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "page": 1,
                "page_size": 500,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page_size"], 100)
        self.assertEqual(data["pagination"]["total_items"], 2)
        self.assertEqual(len(data["menus"]), 2)

    def test_menu_list_enforces_minimum_page_size(self):
        self.client.login(
            username=self.user.username,
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "page": 1,
                "page_size": -5,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page_size"], 1)
        self.assertEqual(data["pagination"]["total_items"], 2)
        self.assertEqual(len(data["menus"]), 1)

    def test_menu_list_handles_invalid_page_size(self):
        self.client.login(
            username=self.user.username,
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "page": 1,
                "page_size": "abc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page_size"], 20)
        self.assertEqual(data["pagination"]["total_items"], 2)
        self.assertEqual(len(data["menus"]), 2)
    def test_menu_list_returns_menus_in_sort_order(self):
        Menu.objects.create(
            module=self.module,
            name="Third Menu",
            code="third_menu",
            sort_order=3,
        )

        Menu.objects.create(
            module=self.module,
            name="Second Menu",
            code="second_menu",
            sort_order=2,
        )

        self.client.login(
            username=self.user.username,
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "page": 1,
                "page_size": 20,
            },
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        menu_codes = [menu["code"] for menu in menus]

        self.assertEqual(
            menu_codes,
            [
                "cutting",
                "production",
                "second_menu",
                "third_menu",
            ],
)
    def test_menu_list_search_by_name(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        cutting_menu = Menu.objects.create(
            module=production_module,
            name="Cutting",
            code="cutting",
            sort_order=1,
        )

        sewing_menu = Menu.objects.create(
            module=production_module,
            name="Sewing",
            code="sewing",
            sort_order=2,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": production_module.id},
            ),
            {"search": "Cutting"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["menus"]), 1)
        self.assertEqual(data["menus"][0]["name"], "Cutting")
        self.assertEqual(data["pagination"]["total_items"], 1)

    def test_menu_list_search_by_code(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        Menu.objects.create(
            module=production_module,
            name="Cutting Department",
            code="cutting",
            sort_order=1,
        )

        Menu.objects.create(
            module=production_module,
            name="Sewing Department",
            code="sewing",
            sort_order=2,
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": production_module.id},
            ),
            {"search": "sewing"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["menus"]), 1)
        self.assertEqual(data["menus"][0]["code"], "sewing")
        self.assertEqual(data["pagination"]["total_items"], 1)

    def test_menu_list_search_returns_no_results(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        Menu.objects.create(
            module=production_module,
            name="Cutting",
            code="cutting",
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": production_module.id},
            ),
            {"search": "nonexistent_menu_xyz"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["menus"], [])
        self.assertEqual(data["pagination"]["total_items"], 0)
        self.assertEqual(data["pagination"]["total_pages"], 1)
        self.assertFalse(data["pagination"]["has_next"])
        self.assertFalse(data["pagination"]["has_previous"])

    def test_menu_list_search_is_case_insensitive(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        Menu.objects.create(
            module=production_module,
            name="Cutting Department",
            code="cutting",
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": production_module.id},
            ),
            {"search": "CUTTING"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["menus"]), 1)
        self.assertEqual(data["menus"][0]["code"], "cutting")
        self.assertEqual(data["pagination"]["total_items"], 1)

    def test_menu_list_search_ignores_whitespace(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        Menu.objects.create(
            module=production_module,
            name="Cutting Department",
            code="cutting",
        )

        Menu.objects.create(
            module=production_module,
            name="Sewing Department",
            code="sewing",
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": production_module.id},
            ),
            {"search": "   "},
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(len(data["menus"]), 2)
        self.assertEqual(data["pagination"]["total_items"], 2)

    def test_menu_list_search_combines_with_pagination(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        for number in range(1, 6):
            Menu.objects.create(
                module=production_module,
                name=f"Production Menu {number}",
                code=f"production_menu_{number}",
            )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": production_module.id},
            ),
            {
                "search": "Production",
                "page": 2,
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(len(data["menus"]), 2)
        self.assertEqual(data["pagination"]["page"], 2)
        self.assertEqual(data["pagination"]["page_size"], 2)
        self.assertEqual(data["pagination"]["total_items"], 5)
        self.assertEqual(data["pagination"]["total_pages"], 3)

    def test_menu_list_search_does_not_bypass_permissions(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        cutting_menu = Menu.objects.create(
            module=production_module,
            name="Cutting Department",
            code="cutting",
        )

        Menu.objects.create(
            module=production_module,
            name="Sewing Department",
            code="sewing",
        )

        normal_user = User.objects.create_user(
            username="menu_search_permission_user",
            password="TestPassword123!",
        )

        UserPermission.objects.create(
            user=normal_user,
            module=Module.objects.get(code="access_control"),
        )

        UserPermission.objects.create(
            user=normal_user,
            menu=cutting_menu,
        )

        self.client.logout()

        self.client.login(
            username="menu_search_permission_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": production_module.id},
            ),
            {"search": "Sewing"},
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(data["menus"], [])
        self.assertEqual(data["pagination"]["total_items"], 0)

    def test_menu_list_returns_inactive_menus_with_inactive_status(self):
        self.child.is_active = False
        self.child.save()

        inactive_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Quality",
            code="inactive_quality",
            is_active=False,
            sort_order=3,
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                args=[self.module.id],
            ),
            {"status": "inactive"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        menus = response.json()["data"]["menus"]

        returned_ids = [
            menu["id"]
            for menu in menus
        ]

        self.assertIn(self.child.id, returned_ids)
        self.assertIn(inactive_menu.id, returned_ids)
        self.assertNotIn(self.parent.id, returned_ids)
        self.assertEqual(len(menus), 2)
    def test_menu_list_returns_all_menus_with_all_status(self):
        self.child.is_active = False
        self.child.save()

        inactive_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Quality",
            code="inactive_quality",
            is_active=False,
            sort_order=3,
        )

        response = self.client.get(
            reverse("access_control:menu_list", args=[self.module.id]),
            {"status": "all"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        menus = response.json()["data"]["menus"]
        returned_ids = [menu["id"] for menu in menus]

        self.assertIn(self.parent.id, returned_ids)
        self.assertIn(self.child.id, returned_ids)
        self.assertIn(inactive_menu.id, returned_ids)
        self.assertEqual(len(menus), 3)

    def test_normal_user_with_menu_permission_cannot_view_inactive_menus(self):
        self.child.is_active = False
        self.child.save()

        inactive_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Quality",
            code="inactive_quality",
            is_active=False,
            sort_order=3,
        )

        normal_user = User.objects.create_user(
            username="inactive_menu_permission_user",
            password="testpassword123",
        )

        # Grant access to the Access Control module.
        UserPermission.objects.create(
            user=normal_user,
            module=Module.objects.get(code="access_control"),
        )

        # Grant only menu-level permission.
        UserPermission.objects.create(
            user=normal_user,
            menu=self.parent,
        )

        self.client.logout()

        self.client.login(
            username="inactive_menu_permission_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                args=[self.module.id],
            ),
            {"status": "inactive"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        menus = response.json()["data"]["menus"]

        returned_ids = [
            menu["id"]
            for menu in menus
        ]

        self.assertNotIn(self.child.id, returned_ids)
        self.assertNotIn(inactive_menu.id, returned_ids)
        self.assertEqual(len(menus), 0)

    
    def test_module_permission_user_can_view_inactive_menus(self):
        self.child.is_active = False
        self.child.save()

        inactive_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Quality",
            code="inactive_quality",
            is_active=False,
        )

        normal_user = User.objects.create_user(
            username="module_permission_menu_user",
            password="testpassword123",
        )

        UserPermission.objects.create(
            user=normal_user,
            module=Module.objects.get(code="access_control"),
        )

        UserPermission.objects.create(
            user=normal_user,
            module=self.module,
        )

        self.client.logout()
        self.client.login(
            username="module_permission_menu_user",
            password="testpassword123",
        )

        response = self.client.get(
            f"/access-control/modules/{self.module.id}/menus/?status=inactive"
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]
        menu_ids = [menu["id"] for menu in menus]

        self.assertIn(self.child.id, menu_ids)
        self.assertIn(inactive_menu.id, menu_ids)
        self.assertEqual(len(menus), 2)

        
    def test_menu_permission_user_status_all_returns_only_accessible_active_menus(self):
        self.child.is_active = False
        self.child.save()

        inactive_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Quality",
            code="inactive_quality",
            is_active=False,
        )

        normal_user = User.objects.create_user(
            username="menu_permission_all_user",
            password="testpassword123",
        )

        UserPermission.objects.create(
            user=normal_user,
            module=Module.objects.get(code="access_control"),
        )

        UserPermission.objects.create(
            user=normal_user,
            menu=self.parent,
        )

        self.client.logout()
        self.client.login(
            username="menu_permission_all_user",
            password="testpassword123",
        )

        response = self.client.get(
            f"/access-control/modules/{self.module.id}/menus/?status=all"
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]
        menu_ids = [menu["id"] for menu in menus]

        self.assertIn(self.parent.id, menu_ids)
        self.assertNotIn(self.child.id, menu_ids)
        self.assertNotIn(inactive_menu.id, menu_ids)
        self.assertEqual(len(menus), 1)

    
    def test_menu_list_rejects_invalid_status_filter(self):
        response = self.client.get(
            f"/access-control/modules/{self.module.id}/menus/?status=invalid"
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["message"],
            "Invalid status filter.",
        )

    
    def test_menu_list_normalizes_status_filter(self):
        self.child.is_active = False
        self.child.save()

        response = self.client.get(
            f"/access-control/modules/{self.module.id}/menus/?status=%20INACTIVE%20"
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]
        menu_ids = [menu["id"] for menu in menus]

        self.assertIn(self.child.id, menu_ids)
        self.assertEqual(len(menus), 1)

        
    def test_menu_list_combines_inactive_status_with_search(self):
        self.child.is_active = False
        self.child.save()

        inactive_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Quality",
            code="inactive_quality",
            is_active=False,
        )

        response = self.client.get(
            f"/access-control/modules/{self.module.id}/menus/"
            "?status=inactive&search=quality"
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        self.assertEqual(len(menus), 1)
        self.assertEqual(menus[0]["id"], inactive_menu.id)

    
    def test_menu_list_combines_inactive_status_with_pagination(self):
        self.child.is_active = False
        self.child.save()

        inactive_menu_2 = Menu.objects.create(
            module=self.module,
            name="Inactive Quality",
            code="inactive_quality",
            is_active=False,
            sort_order=2,
        )

        inactive_menu_3 = Menu.objects.create(
            module=self.module,
            name="Inactive Packing",
            code="inactive_packing",
            is_active=False,
            sort_order=3,
        )

        response = self.client.get(
            f"/access-control/modules/{self.module.id}/menus/"
            "?status=inactive&page=2&page_size=1"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(len(data["menus"]), 1)
        self.assertEqual(data["menus"][0]["id"], inactive_menu_2.id)

        self.assertEqual(data["pagination"]["page"], 2)
        self.assertEqual(data["pagination"]["page_size"], 1)
        self.assertEqual(data["pagination"]["total_items"], 3)
        self.assertEqual(data["pagination"]["total_pages"], 3)

    
    def test_menu_list_combines_all_status_with_search(self):
        inactive_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Quality",
            code="inactive_quality",
            is_active=False,
        )

        normal_user = User.objects.create_user(
            username="all_status_search_user",
            password="testpassword123",
        )

        UserPermission.objects.create(
            user=normal_user,
            module=Module.objects.get(code="access_control"),
        )

        UserPermission.objects.create(
            user=normal_user,
            module=self.module,
        )

        self.client.logout()
        self.client.login(
            username="all_status_search_user",
            password="testpassword123",
        )

        response = self.client.get(
            f"/access-control/modules/{self.module.id}/menus/"
            "?status=all&search=quality"
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        self.assertEqual(len(menus), 1)
        self.assertEqual(menus[0]["id"], inactive_menu.id)

    
    def test_menu_list_combines_all_status_with_pagination(self):
        Menu.objects.create(
            module=self.module,
            name="Quality",
            code="quality",
            is_active=False,
            sort_order=10,
        )

        Menu.objects.create(
            module=self.module,
            name="Packing",
            code="packing",
            is_active=False,
            sort_order=20,
        )

        normal_user = User.objects.create_user(
            username="all_status_pagination_user",
            password="testpassword123",
        )

        UserPermission.objects.create(
            user=normal_user,
            module=Module.objects.get(code="access_control"),
        )

        UserPermission.objects.create(
            user=normal_user,
            module=self.module,
        )

        self.client.logout()
        self.client.login(
            username="all_status_pagination_user",
            password="testpassword123",
        )

        response = self.client.get(
            f"/access-control/modules/{self.module.id}/menus/"
            "?status=all&page=2&page_size=2"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(len(data["menus"]), 2)
        self.assertEqual(data["pagination"]["page"], 2)
        self.assertEqual(data["pagination"]["page_size"], 2)
        self.assertEqual(data["pagination"]["total_items"], 4)
        self.assertEqual(data["pagination"]["total_pages"], 2)

    def test_menu_list_sorts_by_name_ascending(self):
        Menu.objects.create(
            module=self.module,
            name="Inventory",
            code="inventory",
        )

        Menu.objects.create(
            module=self.module,
            name="Quality",
            code="quality",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "sort_by": "name",
                "sort_dir": "asc",
            },
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        self.assertEqual(
            [menu["name"] for menu in menus],
            ["Cutting", "Inventory", "Production", "Quality"],
        )

    def test_menu_list_sorts_by_name_descending(self):
        Menu.objects.create(
            module=self.module,
            name="Inventory",
            code="inventory",
        )

        Menu.objects.create(
            module=self.module,
            name="Quality",
            code="quality",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "sort_by": "name",
                "sort_dir": "desc",
            },
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        self.assertEqual(
            [menu["name"] for menu in menus],
            ["Quality", "Production", "Inventory", "Cutting"],
        )

    def test_menu_list_sorts_by_code_ascending(self):
        Menu.objects.create(
            module=self.module,
            name="Inventory",
            code="inventory",
        )

        Menu.objects.create(
            module=self.module,
            name="Quality",
            code="quality",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "sort_by": "code",
                "sort_dir": "asc",
            },
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        self.assertEqual(
            [menu["code"] for menu in menus],
            ["cutting", "inventory", "production", "quality"],
        )

    def test_menu_list_sorts_by_code_descending(self):
        Menu.objects.create(
            module=self.module,
            name="Inventory",
            code="inventory",
        )

        Menu.objects.create(
            module=self.module,
            name="Quality",
            code="quality",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "sort_by": "code",
                "sort_dir": "desc",
            },
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        self.assertEqual(
            [menu["code"] for menu in menus],
            ["quality", "production", "inventory", "cutting"],
        )
    def test_menu_list_sorts_by_sort_order_ascending(self):
        Menu.objects.create(
            module=self.module,
            name="Inventory",
            code="inventory",
            sort_order=30,
        )

        Menu.objects.create(
            module=self.module,
            name="Quality",
            code="quality",
            sort_order=10,
        )

        Menu.objects.create(
            module=self.module,
            name="Sewing",
            code="sewing",
            sort_order=20,
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "sort_by": "sort_order",
                "sort_dir": "asc",
            },
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        self.assertEqual(
            [menu["sort_order"] for menu in menus],
            [0, 0, 10, 20, 30],
        )
    def test_menu_list_sorts_by_sort_order_descending(self):
        Menu.objects.create(
            module=self.module,
            name="Inventory",
            code="inventory",
            sort_order=30,
        )

        Menu.objects.create(
            module=self.module,
            name="Quality",
            code="quality",
            sort_order=10,
        )

        Menu.objects.create(
            module=self.module,
            name="Sewing",
            code="sewing",
            sort_order=20,
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "sort_by": "sort_order",
                "sort_dir": "desc",
            },
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        self.assertEqual(
            [menu["sort_order"] for menu in menus],
            [30, 20, 10, 0, 0],
        )
    def test_menu_list_rejects_invalid_sort_field(self):
        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "sort_by": "invalid_field",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["message"],
            "Invalid sort field.",
        )
    def test_menu_list_rejects_invalid_sort_direction(self):
        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "sort_by": "name",
                "sort_dir": "invalid",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["message"],
            "Invalid sort direction.",
        )
    def test_menu_list_search_results_are_sorted(self):
        Menu.objects.create(
            module=self.module,
            name="Quality Control",
            code="quality_control",
        )

        Menu.objects.create(
            module=self.module,
            name="Quality Inspection",
            code="quality_inspection",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "search": "Quality",
                "sort_by": "name",
                "sort_dir": "asc",
            },
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        self.assertEqual(
            [menu["name"] for menu in menus],
            ["Quality Control", "Quality Inspection"],
        )
    def test_menu_list_sorts_before_pagination(self):
        Menu.objects.create(
            module=self.module,
            name="Inventory",
            code="inventory",
        )

        Menu.objects.create(
            module=self.module,
            name="Quality",
            code="quality",
        )

        Menu.objects.create(
            module=self.module,
            name="Sewing",
            code="sewing",
        )

        response = self.client.get(
            reverse(
                "access_control:menu_list",
                kwargs={"module_id": self.module.id},
            ),
            {
                "sort_by": "name",
                "sort_dir": "asc",
                "page": 1,
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)

        menus = response.json()["data"]["menus"]

        self.assertEqual(
            [menu["name"] for menu in menus],
            ["Cutting", "Inventory"],
        )

        pagination = response.json()["data"]["pagination"]

        self.assertEqual(pagination["total_pages"], 3)
        self.assertEqual(pagination["total_items"], 5)\


class MenuCreateViewTests(TestCase):

   
    def setUp(self):
        # Access Control module required by action_required.
        self.access_module = Module.objects.create(
            name="Access Control",
            code="access_control",
        )

        # Menu required by action_required.
        self.access_menu = Menu.objects.create(
            module=self.access_module,
            name="Menus",
            code="menus",
        )

        # Action required by action_required.
        self.create_menu_action = Action.objects.create(
            menu=self.access_menu,
            name="Create Menu",
            code="create_menu",
        )

        # Module where menus will be created.
        self.module = Module.objects.create(
            name="Production",
            code="production",
        )

        self.user = User.objects.create_user(
            username="menu_create_admin",
            password="testpassword123",
            is_superuser=True,
        )

        self.client.login(
            username="menu_create_admin",
            password="testpassword123",
        )

        self.url = reverse(
            "access_control:menu_create",
            args=[self.module.id],
        )


    def test_create_menu_successfully(self):
        response = self.client.post(
            self.url,
            {
                "name": "Cutting",
                "code": "cutting",
                "description": "Cutting department",
                "sort_order": 1,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["success"])

        menu = Menu.objects.get(
            module=self.module,
            code="cutting",
        )

        self.assertEqual(menu.name, "Cutting")
        self.assertEqual(menu.sort_order, 1)

    def test_create_menu_with_parent(self):
        parent = Menu.objects.create(
            module=self.module,
            name="Production",
            code="production",
        )

        response = self.client.post(
            self.url,
            {
                "name": "Cutting",
                "code": "cutting",
                "parent": parent.id,
                "sort_order": 1,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 201)

        menu = Menu.objects.get(code="cutting")

        self.assertEqual(menu.parent, parent)

    def test_create_menu_rejects_missing_name(self):
        response = self.client.post(
            self.url,
            {
                "name": "",
                "code": "cutting",
                "sort_order": 0,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json()["errors"])

    def test_create_menu_rejects_missing_code(self):
        response = self.client.post(
            self.url,
            {
                "name": "Cutting",
                "code": "",
                "sort_order": 0,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "code",
            response.json()["errors"],
        )

    def test_create_menu_rejects_duplicate_code_in_same_module(self):
        Menu.objects.create(
            module=self.module,
            name="Cutting",
            code="cutting",
        )

        response = self.client.post(
            self.url,
            {
                "name": "Cutting Department",
                "code": "cutting",
                "sort_order": 1,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "__all__",
            response.json()["errors"],
        )

    def test_create_menu_rejects_parent_from_another_module(self):
        another_module = Module.objects.create(
            name="Inventory",
            code="inventory",
        )

        foreign_parent = Menu.objects.create(
            module=another_module,
            name="Stock",
            code="stock",
        )

        response = self.client.post(
            self.url,
            {
                "name": "Cutting",
                "code": "cutting",
                "parent": foreign_parent.id,
                "sort_order": 1,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("parent", response.json()["errors"])

    def test_create_menu_rejects_get_request(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(response.json()["success"])

    def test_create_menu_returns_404_for_missing_module(self):
        response = self.client.post(
            reverse(
                "access_control:menu_create",
                args=[999999],
            ),
            {
                "name": "Cutting",
                "code": "cutting",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_create_menu_requires_login(self):
        self.client.logout()

        response = self.client.post(
            self.url,
            {
                "name": "Cutting",
                "code": "cutting",
            },
        )

        self.assertEqual(response.status_code, 302)


class AccessibleActionsServiceTests(TestCase):

    def setUp(self):
        self.module = Module.objects.create(
            name="Action Test Module",
            code="action_test_module",
        )

        self.parent = Menu.objects.create(
            module=self.module,
            name="Production",
            code="production",
        )

        self.child = Menu.objects.create(
            module=self.module,
            parent=self.parent,
            name="Cutting",
            code="cutting",
        )

        self.view_action = Action.objects.create(
            menu=self.child,
            name="View",
            code="view",
            sort_order=1,
        )

        self.create_action = Action.objects.create(
            menu=self.child,
            name="Create",
            code="create",
            sort_order=2,
        )

        self.delete_action = Action.objects.create(
            menu=self.child,
            name="Delete",
            code="delete",
            sort_order=3,
        )

        self.user = User.objects.create_user(
            username="action_service_user",
            password="testpassword123",
        )

    def test_direct_action_permission_returns_only_permitted_action(self):
        UserPermission.objects.create(
            user=self.user,
            action=self.create_action,
        )

        actions = get_accessible_actions(
            self.user,
            self.child,
        )

        self.assertEqual(
            list(actions.values_list("id", flat=True)),
            [self.create_action.id],
        )

    def test_group_action_permission_returns_only_permitted_action(self):
        group = Group.objects.create(
            name="Action Test Group",
        )
        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            action=self.view_action,
        )

        actions = get_accessible_actions(
            self.user,
            self.child,
        )

        self.assertEqual(
            list(actions.values_list("id", flat=True)),
            [self.view_action.id],
        )

    def test_menu_permission_returns_no_actions(self):
        UserPermission.objects.create(
            user=self.user,
            menu=self.child,
        )

        actions = get_accessible_actions(
            self.user,
            self.child,
        )

        self.assertEqual(actions.count(), 0)

    def test_parent_menu_permission_returns_no_child_actions(self):
        UserPermission.objects.create(
            user=self.user,
            menu=self.parent,
        )

        actions = get_accessible_actions(
            self.user,
            self.child,
        )

        self.assertEqual(actions.count(), 0)

    def test_superuser_returns_all_active_actions(self):
        self.user.is_superuser = True
        self.user.save()

        actions = get_accessible_actions(
            self.user,
            self.child,
        )

        self.assertEqual(actions.count(), 3)

    def test_inactive_action_is_never_returned(self):
        self.create_action.is_active = False
        self.create_action.save()

        UserPermission.objects.create(
            user=self.user,
            action=self.view_action,
        )

        UserPermission.objects.create(
            user=self.user,
            action=self.delete_action,
        )

        actions = get_accessible_actions(
            self.user,
            self.child,
        )

        self.assertEqual(actions.count(), 2)

        action_ids = set(
            actions.values_list("id", flat=True)
        )

        self.assertEqual(
            action_ids,
            {
                self.view_action.id,
                self.delete_action.id,
            },
        )

        self.assertNotIn(
            self.create_action.id,
            action_ids,
        )

    def test_inactive_parent_menu_denies_actions(self):
        self.parent.is_active = False
        self.parent.save()

        self.user.is_superuser = True
        self.user.save()

        actions = get_accessible_actions(
            self.user,
            self.child,
        )

        self.assertEqual(actions.count(), 0)

    def test_user_without_permissions_gets_no_actions(self):
        actions = get_accessible_actions(
            self.user,
            self.child,
        )

        self.assertEqual(actions.count(), 0)

    def test_group_parent_menu_permission_returns_no_child_actions(self):
        group = Group.objects.create(
            name="Production Managers",
        )

        self.user.groups.add(group)

        GroupPermission.objects.create(
            group=group,
            menu=self.parent,
        )

        actions = get_accessible_actions(
            self.user,
            self.child,
        )

        self.assertEqual(actions.count(), 0)

        self.assertEqual(
            list(actions.values_list("code", flat=True)),
            [],
        )
    def test_inactive_user_with_permission_sees_no_actions(self):
        self.user.is_active = False
        self.user.save()

        UserPermission.objects.create(
            user=self.user,
            action=self.view_action,
        )

        actions = get_accessible_actions(
            self.user,
            self.child,
        )

        self.assertEqual(actions.count(), 0)



class ActionListViewTests(TestCase):

    def setUp(self):
        self.access_control_module = Module.objects.create(
            name="Access Control",
            code="access_control",
            is_active=True,
        )

        self.module = Module.objects.create(
            name="Action API Module",
            code="action_api_module",
        )

        self.menu = Menu.objects.create(
            module=self.module,
            name="Production",
            code="production",
        )

        self.action_one = Action.objects.create(
            menu=self.menu,
            name="Create Production",
            code="create_production",
        )

        self.action_two = Action.objects.create(
            menu=self.menu,
            name="Update Production",
            code="update_production",
        )

        self.user = User.objects.create_user(
            username="action_api_user",
            password="testpassword123",
            is_superuser=True,
        )

        self.client.login(
            username="action_api_user",
            password="testpassword123",
        )

    def test_action_list_returns_all_active_actions_for_superuser(self):
        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]["actions"]), 2)

    def test_action_list_returns_menu_information(self):
        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            )
        )

        menu_data = response.json()["data"]["menu"]

        self.assertEqual(menu_data["id"], self.menu.id)
        self.assertEqual(menu_data["name"], "Production")
        self.assertEqual(menu_data["code"], "production")

    def test_action_list_does_not_return_inactive_actions(self):
        self.action_two.is_active = False
        self.action_two.save()

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            )
        )

        actions = response.json()["data"]["actions"]

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["id"], self.action_one.id)

    def test_action_list_returns_404_for_missing_module(self):
        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[999999, self.menu.id],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["success"])

    def test_action_list_returns_404_for_missing_menu(self):
        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, 999999],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["success"])

    def test_action_list_returns_404_when_menu_belongs_to_another_module(self):
        another_module = Module.objects.create(
            name="Another Module",
            code="another_module",
        )

        another_menu = Menu.objects.create(
            module=another_module,
            name="Another Menu",
            code="another_menu",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, another_menu.id],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_action_list_requires_login(self):
        self.client.logout()

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            )
        )

        self.assertEqual(response.status_code, 302)

    def test_action_list_returns_only_permitted_actions_for_normal_user(self):
        normal_user = User.objects.create_user(
            username="normal_action_user",
            password="testpassword123",
        )

        UserPermission.objects.create(
            user=normal_user,
            module=self.access_control_module,
        )

        UserPermission.objects.create(
            user=normal_user,
            action=self.action_one,
        )

        self.client.logout()

        self.client.login(
            username="normal_action_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        actions = response.json()["data"]["actions"]

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["id"], self.action_one.id)
        self.assertEqual(actions[0]["code"], "create_production")

    def test_action_list_returns_only_group_permitted_actions(self):
        from django.contrib.auth.models import Group

        production_group = Group.objects.create(
            name="Production Operators",
        )

        normal_user = User.objects.create_user(
            username="group_action_user",
            password="testpassword123",
        )

        normal_user.groups.add(production_group)

        GroupPermission.objects.create(
            group=production_group,
            module=self.access_control_module,
        )

        GroupPermission.objects.create(
            group=production_group,
            action=self.action_one,
        )

        self.client.logout()

        self.client.login(
            username="group_action_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        actions = response.json()["data"]["actions"]

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["id"], self.action_one.id)
        self.assertEqual(actions[0]["code"], "create_production")

    def test_action_list_returns_no_actions_for_menu_permission(self):
        normal_user = User.objects.create_user(
            username="menu_permission_user",
            password="testpassword123",
        )

        UserPermission.objects.create(
            user=normal_user,
            module=self.access_control_module,
        )

        UserPermission.objects.create(
            user=normal_user,
            menu=self.menu,
        )

        self.client.logout()

        self.client.login(
            username="menu_permission_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        actions = response.json()["data"]["actions"]

        self.assertEqual(actions, [])

    def test_action_list_returns_no_actions_for_group_menu_permission(self):
        from django.contrib.auth.models import Group

        production_group = Group.objects.create(
            name="Production Managers",
        )

        normal_user = User.objects.create_user(
            username="group_menu_permission_user",
            password="testpassword123",
        )

        normal_user.groups.add(production_group)

        GroupPermission.objects.create(
            group=production_group,
            module=self.access_control_module,
        )

        GroupPermission.objects.create(
            group=production_group,
            menu=self.menu,
        )

        self.client.logout()

        self.client.login(
            username="group_menu_permission_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        actions = response.json()["data"]["actions"]

        self.assertEqual(actions, [])

    def test_action_list_returns_no_actions_for_group_parent_menu_permission(self):
        from django.contrib.auth.models import Group

        parent_menu = Menu.objects.create(
            module=self.module,
            name="Production Management",
            code="production_management",
        )

        child_menu = Menu.objects.create(
            module=self.module,
            parent=parent_menu,
            name="Cutting",
            code="cutting",
        )

        Action.objects.create(
            menu=child_menu,
            name="Start Cutting",
            code="start_cutting",
        )

        Action.objects.create(
            menu=child_menu,
            name="Complete Cutting",
            code="complete_cutting",
        )

        production_group = Group.objects.create(
            name="Cutting Operators",
        )

        normal_user = User.objects.create_user(
            username="parent_menu_group_user",
            password="testpassword123",
        )

        normal_user.groups.add(production_group)

        GroupPermission.objects.create(
            group=production_group,
            module=self.access_control_module,
        )

        GroupPermission.objects.create(
            group=production_group,
            menu=parent_menu,
        )

        self.client.logout()

        self.client.login(
            username="parent_menu_group_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, child_menu.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        actions = response.json()["data"]["actions"]

        self.assertEqual(actions, [])

    def test_action_list_paginates_results(self):
        Action.objects.create(
            menu=self.menu,
            name="Delete Production",
            code="delete_production",
        )

        Action.objects.create(
            menu=self.menu,
            name="View Production",
            code="view_production",
        )

        Action.objects.create(
            menu=self.menu,
            name="Approve Production",
            code="approve_production",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            ),
            {
                "page": 1,
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(len(data["actions"]), 2)

        self.assertEqual(
            data["pagination"],
            {
                "page": 1,
                "page_size": 2,
                "total_items": 5,
                "total_pages": 3,
                "has_next": True,
                "has_previous": False,
            },
        )

    def test_action_list_returns_second_page(self):
        Action.objects.create(
            menu=self.menu,
            name="Delete Production",
            code="delete_production",
        )

        Action.objects.create(
            menu=self.menu,
            name="View Production",
            code="view_production",
        )

        Action.objects.create(
            menu=self.menu,
            name="Approve Production",
            code="approve_production",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            ),
            {
                "page": 2,
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(len(data["actions"]), 2)

        self.assertEqual(
            data["pagination"],
            {
                "page": 2,
                "page_size": 2,
                "total_items": 5,
                "total_pages": 3,
                "has_next": True,
                "has_previous": True,
            },
        )

    def test_action_list_handles_invalid_page_number(self):
        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            ),
            {
                "page": "invalid",
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(len(data["actions"]), 2)

        self.assertEqual(
            data["pagination"],
            {
                "page": 1,
                "page_size": 2,
                "total_items": 2,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False,
            },
        )

    def test_action_list_limits_page_size_to_100(self):
        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            ),
            {
                "page": 1,
                "page_size": 500,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page_size"], 100)
        self.assertEqual(data["pagination"]["total_items"], 2)
        self.assertEqual(len(data["actions"]), 2)

    def test_action_list_enforces_minimum_page_size(self):
        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            ),
            {
                "page": 1,
                "page_size": -5,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page_size"], 1)
        self.assertEqual(data["pagination"]["total_items"], 2)
        self.assertEqual(len(data["actions"]), 1)

    def test_action_list_handles_invalid_page_size(self):
        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            ),
            {
                "page": 1,
                "page_size": "abc",
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(data["pagination"]["page_size"], 20)
        self.assertEqual(data["pagination"]["total_items"], 2)
        self.assertEqual(len(data["actions"]), 2)

    def test_action_list_returns_actions_in_sort_order(self):
        self.action_one.sort_order = 1
        self.action_one.save()

        self.action_two.sort_order = 4
        self.action_two.save()

        Action.objects.create(
            menu=self.menu,
            name="Delete Production",
            code="delete_production",
            sort_order=3,
        )

        Action.objects.create(
            menu=self.menu,
            name="View Production",
            code="view_production",
            sort_order=2,
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        actions = response.json()["data"]["actions"]

        self.assertEqual(
            [action["code"] for action in actions],
            [
                "create_production",
                "view_production",
                "delete_production",
                "update_production",
            ],
        )

    def test_action_list_supports_sorting_fields_and_directions(self):
        Action.objects.create(
            menu=self.menu,
            name="Approve Production",
            code="approve_production",
            sort_order=30,
        )

        Action.objects.create(
            menu=self.menu,
            name="Delete Production",
            code="delete_production",
            sort_order=10,
        )

        test_cases = [
            ("name", "asc", [
                "approve_production",
                "create_production",
                "delete_production",
                "update_production",
            ]),
            ("name", "desc", [
                "update_production",
                "delete_production",
                "create_production",
                "approve_production",
            ]),
            ("code", "asc", [
                "approve_production",
                "create_production",
                "delete_production",
                "update_production",
            ]),
            ("code", "desc", [
                "update_production",
                "delete_production",
                "create_production",
                "approve_production",
            ]),
            ("sort_order", "asc", [
                "create_production",
                "update_production",
                "delete_production",
                "approve_production",
            ]),
            ("sort_order", "desc", [
                "approve_production",
                "delete_production",
                "create_production",
                "update_production",
            ]),
        ]

        url = reverse(
            "access_control:action_list",
            args=[self.module.id, self.menu.id],
        )

        for sort_by, sort_dir, expected_codes in test_cases:
            with self.subTest(sort_by=sort_by, sort_dir=sort_dir):
                response = self.client.get(
                    url,
                    {
                        "sort_by": sort_by,
                        "sort_dir": sort_dir,
                    },
                )

                self.assertEqual(response.status_code, 200)

                actions = response.json()["data"]["actions"]

                self.assertEqual(
                    [action["code"] for action in actions],
                    expected_codes,
                )

    def test_action_list_rejects_invalid_sorting_parameters(self):
        url = reverse(
            "access_control:action_list",
            args=[self.module.id, self.menu.id],
        )

        test_cases = [
            (
                {"sort_by": "invalid_field"},
                "Invalid sort field.",
            ),
            (
                {"sort_by": "name", "sort_dir": "invalid"},
                "Invalid sort direction.",
            ),
        ]

        for params, expected_message in test_cases:
            with self.subTest(params=params):
                response = self.client.get(url, params)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json()["message"],
                    expected_message,
                )

    def test_action_list_combines_search_sorting_and_pagination(self):
        Action.objects.create(
            menu=self.menu,
            name="Batch Z",
            code="batch_z",
        )

        Action.objects.create(
            menu=self.menu,
            name="Batch A",
            code="batch_a",
        )

        Action.objects.create(
            menu=self.menu,
            name="Batch M",
            code="batch_m",
        )

        url = reverse(
            "access_control:action_list",
            args=[self.module.id, self.menu.id],
        )

        params = {
            "search": "Batch",
            "sort_by": "name",
            "sort_dir": "asc",
            "page_size": 2,
        }

        response = self.client.get(
            url,
            {**params, "page": 1},
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(
            [action["code"] for action in data["actions"]],
            ["batch_a", "batch_m"],
        )

        self.assertEqual(data["pagination"]["total_items"], 3)
        self.assertEqual(data["pagination"]["total_pages"], 2)

        response = self.client.get(
            url,
            {**params, "page": 2},
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(
            [action["code"] for action in data["actions"]],
            ["batch_z"],
        )

        self.assertEqual(data["pagination"]["has_previous"], True)
        self.assertEqual(data["pagination"]["has_next"], False)

    def test_action_list_paginates_only_permitted_actions(self):
        Action.objects.create(
            menu=self.menu,
            name="Delete Production",
            code="delete_production",
        )

        Action.objects.create(
            menu=self.menu,
            name="View Production",
            code="view_production",
        )

        normal_user = User.objects.create_user(
            username="paginated_action_user",
            password="testpassword123",
        )

        UserPermission.objects.create(
            user=normal_user,
            module=self.access_control_module,
        )

        UserPermission.objects.create(
            user=normal_user,
            action=self.action_one,
        )

        self.client.logout()

        self.client.login(
            username="paginated_action_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                args=[self.module.id, self.menu.id],
            ),
            {
                "page": 1,
                "page_size": 1,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(len(data["actions"]), 1)
        self.assertEqual(
            data["actions"][0]["code"],
            "create_production",
        )

        self.assertEqual(data["pagination"]["total_items"], 1)
        self.assertEqual(data["pagination"]["total_pages"], 1)

    def test_action_list_search_by_name(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        production_menu = Menu.objects.create(
            module=production_module,
            name="Production",
            code="production",
        )

        Action.objects.create(
            menu=production_menu,
            name="Start Production",
            code="start_production",
        )

        Action.objects.create(
            menu=production_menu,
            name="Stop Production",
            code="stop_production",
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                kwargs={
                    "module_id": production_module.id,
                    "menu_id": production_menu.id,
                },
            ),
            {"search": "Start Production"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["actions"]), 1)
        self.assertEqual(data["actions"][0]["name"], "Start Production")
        self.assertEqual(data["pagination"]["total_items"], 1)

    def test_action_list_search_by_code(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        production_menu = Menu.objects.create(
            module=production_module,
            name="Production",
            code="production",
        )

        Action.objects.create(
            menu=production_menu,
            name="Start Production",
            code="start_production",
        )

        Action.objects.create(
            menu=production_menu,
            name="Stop Production",
            code="stop_production",
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                kwargs={
                    "module_id": production_module.id,
                    "menu_id": production_menu.id,
                },
            ),
            {"search": "stop_production"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["actions"]), 1)
        self.assertEqual(data["actions"][0]["code"], "stop_production")
        self.assertEqual(data["pagination"]["total_items"], 1)

    def test_action_list_search_returns_no_results(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        production_menu = Menu.objects.create(
            module=production_module,
            name="Production",
            code="production",
        )

        Action.objects.create(
            menu=production_menu,
            name="Start Production",
            code="start_production",
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                kwargs={
                    "module_id": production_module.id,
                    "menu_id": production_menu.id,
                },
            ),
            {"search": "nonexistent_action_xyz"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["actions"], [])
        self.assertEqual(data["pagination"]["total_items"], 0)
        self.assertEqual(data["pagination"]["total_pages"], 1)
        self.assertFalse(data["pagination"]["has_next"])
        self.assertFalse(data["pagination"]["has_previous"])

    def test_action_list_search_is_case_insensitive(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        production_menu = Menu.objects.create(
            module=production_module,
            name="Production",
            code="production",
        )

        Action.objects.create(
            menu=production_menu,
            name="Start Production",
            code="start_production",
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                kwargs={
                    "module_id": production_module.id,
                    "menu_id": production_menu.id,
                },
            ),
            {"search": "START PRODUCTION"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["actions"]), 1)
        self.assertEqual(data["actions"][0]["code"], "start_production")
        self.assertEqual(data["pagination"]["total_items"], 1)

    def test_action_list_search_ignores_whitespace(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        production_menu = Menu.objects.create(
            module=production_module,
            name="Production",
            code="production",
        )

        Action.objects.create(
            menu=production_menu,
            name="Start Production",
            code="start_production",
        )

        Action.objects.create(
            menu=production_menu,
            name="Stop Production",
            code="stop_production",
        )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                kwargs={
                    "module_id": production_module.id,
                    "menu_id": production_menu.id,
                },
            ),
            {"search": "   "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["actions"]), 2)
        self.assertEqual(data["pagination"]["total_items"], 2)

    def test_action_list_search_combines_with_pagination(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        production_menu = Menu.objects.create(
            module=production_module,
            name="Production",
            code="production",
        )

        for number in range(1, 6):
            Action.objects.create(
                menu=production_menu,
                name=f"Production Action {number}",
                code=f"production_action_{number}",
            )

        UserPermission.objects.create(
            user=self.user,
            module=production_module,
        )

        self.client.login(
            username="dashboard_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                kwargs={
                    "module_id": production_module.id,
                    "menu_id": production_menu.id,
                },
            ),
            {
                "search": "Production Action",
                "page": 2,
                "page_size": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(len(data["actions"]), 2)
        self.assertEqual(data["pagination"]["page"], 2)
        self.assertEqual(data["pagination"]["page_size"], 2)
        self.assertEqual(data["pagination"]["total_items"], 5)
        self.assertEqual(data["pagination"]["total_pages"], 3)

    def test_action_list_search_does_not_bypass_permissions(self):
        production_module = Module.objects.create(
            name="Production",
            code="production",
        )

        production_menu = Menu.objects.create(
            module=production_module,
            name="Production",
            code="production",
        )

        cutting_action = Action.objects.create(
            menu=production_menu,
            name="Start Cutting",
            code="start_cutting",
        )

        Action.objects.create(
            menu=production_menu,
            name="Approve Production",
            code="approve_production",
        )

        normal_user = User.objects.create_user(
            username="action_search_permission_user",
            password="TestPassword123!",
        )

        UserPermission.objects.create(
            user=normal_user,
            module=Module.objects.get(code="access_control"),
        )

        UserPermission.objects.create(
            user=normal_user,
            action=cutting_action,
        )

        self.client.logout()

        self.client.login(
            username="action_search_permission_user",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "access_control:action_list",
                kwargs={
                    "module_id": production_module.id,
                    "menu_id": production_menu.id,
                },
            ),
            {"search": "Approve Production"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]

        self.assertEqual(data["actions"], [])
        self.assertEqual(data["pagination"]["total_items"], 0)



class ActionEditViewTests(TestCase):

    def setUp(self):
        self.access_control_module = Module.objects.create(
            name="Access Control",
            code="access_control",
            is_active=True,
        )

        self.actions_menu = Menu.objects.create(
            module=self.access_control_module,
            name="Actions",
            code="actions",
            is_active=True,
        )

        self.update_action_permission = Action.objects.create(
            menu=self.actions_menu,
            name="Update Action",
            code="update_action",
            is_active=True,
        )

        self.target_module = Module.objects.create(
            name="Production",
            code="production",
            is_active=True,
        )

        self.target_menu = Menu.objects.create(
            module=self.target_module,
            name="Cutting",
            code="cutting",
            is_active=True,
        )

        self.another_menu = Menu.objects.create(
            module=self.target_module,
            name="Sewing",
            code="sewing",
            is_active=True,
        )

        self.target_action = Action.objects.create(
            menu=self.target_menu,
            name="Start Cutting",
            code="start_cutting",
            description="Start cutting operation",
            sort_order=1,
            is_active=True,
        )

        self.superuser = User.objects.create_superuser(
            username="action_edit_admin",
            email="action_edit_admin@example.com",
            password="TestPassword123!",
        )

        self.normal_user = User.objects.create_user(
            username="action_edit_user",
            password="TestPassword123!",
        )

        self.url = reverse(
            "access_control:action_edit",
            args=[
                self.target_module.id,
                self.target_menu.id,
                self.target_action.id,
            ],
        )

    def authorize_normal_user(self):
        UserPermission.objects.create(
            user=self.normal_user,
            action=self.update_action_permission,
        )

    def test_action_edit_requires_login(self):
        response = self.client.post(
            self.url,
            {
                "name": "Updated Cutting",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.target_action.refresh_from_db()

        self.assertEqual(
            self.target_action.name,
            "Start Cutting",
        )

    def test_action_edit_denies_user_without_permission(self):
        self.client.force_login(self.normal_user)

        response = self.client.post(
            self.url,
            {
                "name": "Updated Cutting",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.target_action.refresh_from_db()

        self.assertEqual(
            self.target_action.name,
            "Start Cutting",
        )

    def test_action_edit_allows_authorized_user(self):
        self.authorize_normal_user()
        self.client.force_login(self.normal_user)

        response = self.client.post(
            self.url,
            {
                "name": "Updated Cutting",
                "code": "updated_cutting",
                "description": "Updated cutting operation",
                "sort_order": 5,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(
            data["message"],
            "Action updated successfully.",
        )
        self.assertEqual(
            data["data"]["name"],
            "Updated Cutting",
        )
        self.assertEqual(
            data["data"]["code"],
            "updated_cutting",
        )
        self.assertEqual(
            data["data"]["menu_id"],
            self.target_menu.id,
        )

        self.target_action.refresh_from_db()

        self.assertEqual(
            self.target_action.name,
            "Updated Cutting",
        )

    def test_action_edit_allows_superuser(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "name": "Approved Cutting",
                "code": "approved_cutting",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.target_action.refresh_from_db()

        self.assertEqual(
            self.target_action.name,
            "Approved Cutting",
        )

    def test_action_edit_allows_unchanged_code(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "name": "Updated Cutting Name",
                "code": "start_cutting",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.target_action.refresh_from_db()

        self.assertEqual(
            self.target_action.code,
            "start_cutting",
        )

    def test_action_edit_rejects_missing_name(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "name": "",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertIn("name", response.json()["errors"])

    def test_action_edit_rejects_missing_code(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "name": "Updated Cutting",
                "code": "",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertIn("code", response.json()["errors"])

    def test_action_edit_rejects_duplicate_code_in_same_menu(self):
        Action.objects.create(
            menu=self.target_menu,
            name="Another Cutting Action",
            code="another_cutting",
        )

        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "name": "Updated Cutting",
                "code": "another_cutting",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

        self.target_action.refresh_from_db()

        self.assertEqual(
            self.target_action.code,
            "start_cutting",
        )

    def test_action_edit_allows_same_code_in_different_menu(self):
        Action.objects.create(
            menu=self.another_menu,
            name="Existing Sewing Action",
            code="updated_cutting",
        )

        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "name": "Updated Cutting",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 200)

    def test_action_edit_ignores_submitted_different_menu(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "menu": self.another_menu.id,
                "name": "Updated Cutting",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.target_action.refresh_from_db()

        self.assertEqual(
            self.target_action.menu_id,
            self.target_menu.id,
        )

    def test_action_edit_returns_404_for_missing_module(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:action_edit",
                args=[
                    999999,
                    self.target_menu.id,
                    self.target_action.id,
                ],
            ),
            {
                "name": "Updated Cutting",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_action_edit_returns_404_for_missing_menu(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:action_edit",
                args=[
                    self.target_module.id,
                    999999,
                    self.target_action.id,
                ],
            ),
            {
                "name": "Updated Cutting",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_action_edit_returns_404_for_missing_action(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:action_edit",
                args=[
                    self.target_module.id,
                    self.target_menu.id,
                    999999,
                ],
            ),
            {
                "name": "Updated Cutting",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_action_edit_returns_404_when_action_belongs_to_another_menu(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:action_edit",
                args=[
                    self.target_module.id,
                    self.another_menu.id,
                    self.target_action.id,
                ],
            ),
            {
                "name": "Updated Cutting",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_action_edit_returns_404_for_inactive_module(self):
        self.target_module.is_active = False
        self.target_module.save()

        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "name": "Updated Cutting",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_action_edit_returns_404_for_inactive_menu(self):
        self.target_menu.is_active = False
        self.target_menu.save()

        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "name": "Updated Cutting",
                "code": "updated_cutting",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_action_edit_allows_reactivating_inactive_action(self):
        self.target_action.is_active = False
        self.target_action.save()

        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "name": "Start Cutting",
                "code": "start_cutting",
                "description": "Reactivated cutting operation",
                "sort_order": 1,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(
            data["message"],
            "Action updated successfully.",
        )

        self.target_action.refresh_from_db()

        self.assertTrue(self.target_action.is_active)
        self.assertEqual(
            self.target_action.name,
            "Start Cutting",
        )
        self.assertEqual(
            self.target_action.code,
            "start_cutting",
        )
        self.assertEqual(
            self.target_action.description,
            "Reactivated cutting operation",
        )

    def test_action_edit_rejects_get_request(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    
class ActionDeleteViewTests(TestCase):

    def setUp(self):
        self.access_control_module = Module.objects.create(
            name="Access Control",
            code="access_control",
            is_active=True,
        )

        self.actions_menu = Menu.objects.create(
            module=self.access_control_module,
            name="Actions",
            code="actions",
            is_active=True,
        )

        self.delete_action_permission = Action.objects.create(
            menu=self.actions_menu,
            name="Delete Action",
            code="delete_action",
            is_active=True,
        )

        self.target_module = Module.objects.create(
            name="Production",
            code="production",
            is_active=True,
        )

        self.target_menu = Menu.objects.create(
            module=self.target_module,
            name="Cutting",
            code="cutting",
            is_active=True,
        )

        self.target_action = Action.objects.create(
            menu=self.target_menu,
            name="Start Cutting",
            code="start_cutting",
            is_active=True,
        )

        self.superuser = User.objects.create_superuser(
            username="action_delete_admin",
            email="action_delete_admin@example.com",
            password="TestPassword123!",
        )

        self.normal_user = User.objects.create_user(
            username="action_delete_user",
            password="TestPassword123!",
        )

        self.group = Group.objects.create(
            name="Production Team",
        )

        self.url = reverse(
            "access_control:action_delete",
            args=[
                self.target_module.id,
                self.target_menu.id,
                self.target_action.id,
            ],
        )

    def authorize_normal_user(self):
        UserPermission.objects.create(
            user=self.normal_user,
            action=self.delete_action_permission,
        )

    def test_action_delete_requires_login(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Action.objects.filter(
                id=self.target_action.id,
            ).exists()
        )

    def test_action_delete_denies_user_without_permission(self):
        self.client.force_login(self.normal_user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            Action.objects.filter(
                id=self.target_action.id,
            ).exists()
        )

    def test_action_delete_allows_authorized_user(self):
        self.authorize_normal_user()
        self.client.force_login(self.normal_user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertIn(
            "Start Cutting",
            data["message"],
        )

        self.assertFalse(
            Action.objects.filter(
                id=self.target_action.id,
            ).exists()
        )

    def test_action_delete_allows_superuser(self):
        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            Action.objects.filter(
                id=self.target_action.id,
            ).exists()
        )

    def test_action_delete_blocks_group_permission_assignment(self):
        GroupPermission.objects.create(
            group=self.group,
            action=self.target_action,
        )

        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 409)

        data = response.json()

        self.assertFalse(data["success"])
        self.assertIn(
            "1 group permission assignment(s)",
            data["message"],
        )

        self.assertTrue(
            Action.objects.filter(
                id=self.target_action.id,
            ).exists()
        )

    def test_action_delete_blocks_user_permission_assignment(self):
        UserPermission.objects.create(
            user=self.normal_user,
            action=self.target_action,
        )

        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 409)

        data = response.json()

        self.assertFalse(data["success"])
        self.assertIn(
            "1 user permission assignment(s)",
            data["message"],
        )

        self.assertTrue(
            Action.objects.filter(
                id=self.target_action.id,
            ).exists()
        )

    def test_action_delete_blocks_both_permission_assignments(self):
        GroupPermission.objects.create(
            group=self.group,
            action=self.target_action,
        )

        UserPermission.objects.create(
            user=self.normal_user,
            action=self.target_action,
        )

        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 409)

        data = response.json()

        self.assertIn(
            "1 group permission assignment(s)",
            data["message"],
        )
        self.assertIn(
            "1 user permission assignment(s)",
            data["message"],
        )

        self.assertTrue(
            Action.objects.filter(
                id=self.target_action.id,
            ).exists()
        )

    def test_action_delete_allows_inactive_action_without_assignments(self):
        self.target_action.is_active = False
        self.target_action.save()

        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            Action.objects.filter(
                id=self.target_action.id,
            ).exists()
        )

    def test_action_delete_returns_404_for_missing_module(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:action_delete",
                args=[
                    999999,
                    self.target_menu.id,
                    self.target_action.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_action_delete_returns_404_for_missing_menu(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:action_delete",
                args=[
                    self.target_module.id,
                    999999,
                    self.target_action.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_action_delete_returns_404_for_missing_action(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:action_delete",
                args=[
                    self.target_module.id,
                    self.target_menu.id,
                    999999,
                ],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_action_delete_returns_404_when_menu_belongs_to_another_module(self):
        another_module = Module.objects.create(
            name="Inventory",
            code="inventory",
            is_active=True,
        )

        another_menu = Menu.objects.create(
            module=another_module,
            name="Stock",
            code="stock",
            is_active=True,
        )

        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:action_delete",
                args=[
                    self.target_module.id,
                    another_menu.id,
                    self.target_action.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_action_delete_returns_404_when_action_belongs_to_another_menu(self):
        another_menu = Menu.objects.create(
            module=self.target_module,
            name="Sewing",
            code="sewing",
            is_active=True,
        )

        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:action_delete",
                args=[
                    self.target_module.id,
                    another_menu.id,
                    self.target_action.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_action_delete_returns_404_for_inactive_module(self):
        self.target_module.is_active = False
        self.target_module.save()

        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 404)

    def test_action_delete_rejects_get_request(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

class GroupPermissionListAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="group_permission_admin",
            password="testpassword123",
        )

        self.client.login(
            username="group_permission_admin",
            password="testpassword123",
        )

        # Required by module_required("access_control")
        Module.objects.create(
            name="Access Control",
            code="access_control",
            is_active=True,
        )

        self.group = Group.objects.create(
            name="Test Production Group",
        )

        self.module = Module.objects.create(
            name="Test Production Module",
            code="test_production_module",
        )

        self.menu = Menu.objects.create(
            module=self.module,
            name="Test Production Menu",
            code="test_production_menu",
        )

        self.action = Action.objects.create(
            menu=self.menu,
            name="Test Production Action",
            code="test_production_action",
        )

        self.url = reverse(
            "access_control:group_permission_list",
            kwargs={"group_id": self.group.id},
        )

    def test_authenticated_user_can_retrieve_group_permissions(self):
        GroupPermission.objects.create(
            group=self.group,
            module=self.module,
        )

        GroupPermission.objects.create(
            group=self.group,
            menu=self.menu,
        )

        GroupPermission.objects.create(
            group=self.group,
            action=self.action,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertTrue(response_data["success"])

        self.assertEqual(
            response_data["data"]["group"]["id"],
            self.group.id,
        )

        self.assertEqual(
            response_data["data"]["group"]["name"],
            self.group.name,
        )

        self.assertEqual(
            response_data["data"]["total_permissions"],
            3,
        )

        permissions = response_data["data"]["permissions"]

        self.assertEqual(
            {permission["target_type"] for permission in permissions},
            {"module", "menu", "action"},
        )

    def test_group_permission_list_returns_correct_target_data(self):
        GroupPermission.objects.create(
            group=self.group,
            module=self.module,
        )

        GroupPermission.objects.create(
            group=self.group,
            menu=self.menu,
        )

        GroupPermission.objects.create(
            group=self.group,
            action=self.action,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        permissions = response.json()["data"]["permissions"]

        module_permission = next(
            permission
            for permission in permissions
            if permission["target_type"] == "module"
        )

        menu_permission = next(
            permission
            for permission in permissions
            if permission["target_type"] == "menu"
        )

        action_permission = next(
            permission
            for permission in permissions
            if permission["target_type"] == "action"
        )

        self.assertEqual(
            module_permission["target_id"],
            self.module.id,
        )

        self.assertEqual(
            module_permission["target_name"],
            self.module.name,
        )

        self.assertEqual(
            menu_permission["target_id"],
            self.menu.id,
        )

        self.assertEqual(
            menu_permission["target_name"],
            self.menu.name,
        )

        self.assertEqual(
            action_permission["target_id"],
            self.action.id,
        )

        self.assertEqual(
            action_permission["target_name"],
            self.action.name,
        )

    def test_group_without_permissions_returns_empty_list(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertTrue(response_data["success"])

        self.assertEqual(
            response_data["data"]["permissions"],
            [],
        )

        self.assertEqual(
            response_data["data"]["total_permissions"],
            0,
        )

    def test_nonexistent_group_returns_404(self):
        url = reverse(
            "access_control:group_permission_list",
            kwargs={"group_id": 999999},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_is_redirected(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

class GroupPermissionUpdateAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="group_permission_update_admin",
            password="testpassword123",
        )

        self.client.login(
            username="group_permission_update_admin",
            password="testpassword123",
        )

        # Required for module_required("access_control")
        Module.objects.create(
            name="Access Control",
            code="access_control",
            is_active=True,
        )

        self.group = Group.objects.create(
            name="Test Permission Group",
        )

        self.module = Module.objects.create(
            name="Test Module",
            code="test_module",
        )

        self.menu = Menu.objects.create(
            module=self.module,
            name="Test Menu",
            code="test_menu",
        )

        self.action = Action.objects.create(
            menu=self.menu,
            name="Test Action",
            code="test_action",
        )

        self.url = reverse(
            "access_control:group_permission_update",
            kwargs={"group_id": self.group.id},
        )

    def post_permissions(self, permissions):
        return self.client.post(
            self.url,
            data=json.dumps({
                "permissions": permissions,
            }),
            content_type="application/json",
        )

    def test_valid_permissions_replace_existing_assignments(self):
        old_module = Module.objects.create(
            name="Old Module",
            code="old_module",
        )

        GroupPermission.objects.create(
            group=self.group,
            module=old_module,
        )

        permissions = [
            {
                "target_type": "module",
                "target_id": self.module.id,
            },
            {
                "target_type": "menu",
                "target_id": self.menu.id,
            },
            {
                "target_type": "action",
                "target_id": self.action.id,
            },
        ]

        response = self.post_permissions(permissions)

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertTrue(response_data["success"])
        self.assertEqual(
            response_data["data"]["total_permissions"],
            3,
        )

        saved_permissions = GroupPermission.objects.filter(
            group=self.group,
        )

        self.assertEqual(saved_permissions.count(), 3)

        self.assertTrue(
            saved_permissions.filter(
                module=self.module,
            ).exists()
        )

        self.assertTrue(
            saved_permissions.filter(
                menu=self.menu,
            ).exists()
        )

        self.assertTrue(
            saved_permissions.filter(
                action=self.action,
            ).exists()
        )

        self.assertFalse(
            saved_permissions.filter(
                module=old_module,
            ).exists()
        )

    def test_empty_permissions_remove_all_assignments(self):
        GroupPermission.objects.create(
            group=self.group,
            module=self.module,
        )

        response = self.post_permissions([])

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            GroupPermission.objects.filter(
                group=self.group,
            ).count(),
            0,
        )

        self.assertEqual(
            response.json()["data"]["total_permissions"],
            0,
        )

    def test_duplicate_targets_are_rejected(self):
        GroupPermission.objects.create(
            group=self.group,
            module=self.module,
        )

        permissions = [
            {
                "target_type": "module",
                "target_id": self.module.id,
            },
            {
                "target_type": "module",
                "target_id": self.module.id,
            },
        ]

        response = self.post_permissions(permissions)

        self.assertEqual(response.status_code, 400)

        self.assertFalse(response.json()["success"])

        # Existing permissions must remain untouched.
        self.assertTrue(
            GroupPermission.objects.filter(
                group=self.group,
                module=self.module,
            ).exists()
        )

        self.assertEqual(
            GroupPermission.objects.filter(
                group=self.group,
            ).count(),
            1,
        )

    def test_nonexistent_target_is_rejected(self):
        GroupPermission.objects.create(
            group=self.group,
            module=self.module,
        )

        response = self.post_permissions([
            {
                "target_type": "module",
                "target_id": 999999,
            },
        ])

        self.assertEqual(response.status_code, 400)

        self.assertTrue(
            GroupPermission.objects.filter(
                group=self.group,
                module=self.module,
            ).exists()
        )

    def test_inactive_module_assignment_is_rejected(self):
        GroupPermission.objects.create(
            group=self.group,
            module=self.module,
        )

        inactive_module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
        )

        response = self.post_permissions([
            {
                "target_type": "module",
                "target_id": inactive_module.id,
            },
        ])

        self.assertEqual(response.status_code, 400)

        # Failed validation must not remove the old assignment.
        self.assertTrue(
            GroupPermission.objects.filter(
                group=self.group,
                module=self.module,
            ).exists()
        )

        self.assertFalse(
            GroupPermission.objects.filter(
                group=self.group,
                module=inactive_module,
            ).exists()
        )

    def test_malformed_json_is_rejected(self):
        GroupPermission.objects.create(
            group=self.group,
            module=self.module,
        )

        response = self.client.post(
            self.url,
            data="{invalid json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(response.json()["success"])

        # Existing assignment remains.
        self.assertTrue(
            GroupPermission.objects.filter(
                group=self.group,
                module=self.module,
            ).exists()
        )

    def test_nonexistent_group_returns_404(self):
        url = reverse(
            "access_control:group_permission_update",
            kwargs={"group_id": 999999},
        )

        response = self.client.post(
            url,
            data=json.dumps({
                "permissions": [],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_invalid_target_type_is_rejected(self):
        response = self.post_permissions([
            {
                "target_type": "invalid",
                "target_id": self.module.id,
            },
        ])

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])


def test_invalid_target_id_types_are_rejected(self):
    invalid_ids = [
        "1",
        True,
        1.5,
        0,
        -1,
        None,
    ]

    for target_id in invalid_ids:
        with self.subTest(target_id=target_id):
            response = self.post_permissions([
                {
                    "target_type": "module",
                    "target_id": target_id,
                },
            ])

            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.json()["success"])


def test_unauthenticated_user_cannot_update_permissions(self):
    self.client.logout()

    response = self.post_permissions([
        {
            "target_type": "module",
            "target_id": self.module.id,
        },
    ])

    self.assertEqual(response.status_code, 302)

    self.assertEqual(
        GroupPermission.objects.filter(group=self.group).count(),
        0,
    )

class GroupPermissionAvailableTreeAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="available_tree_admin",
            password="testpassword123",
        )

        self.client.login(
            username="available_tree_admin",
            password="testpassword123",
        )

        # Required for module_required("access_control")
        self.access_control_module = Module.objects.create(
            name="Access Control",
            code="access_control",
            is_active=True,
        )

        self.module = Module.objects.create(
            name="Test Module",
            code="test_module",
            sort_order=1,
        )

        self.menu = Menu.objects.create(
            module=self.module,
            name="Test Menu",
            code="test_menu",
            sort_order=1,
        )

        self.action = Action.objects.create(
            menu=self.menu,
            name="Test Action",
            code="test_action",
            sort_order=1,
        )

        self.url = reverse(
            "access_control:group_permission_available_tree",
        )

    def test_authenticated_user_can_retrieve_permission_tree(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertIn("modules", data["data"])
        self.assertEqual(data["data"]["total_modules"], 2)

    def test_permission_tree_contains_correct_hierarchy(self):
        response = self.client.get(self.url)

        data = response.json()

        modules = data["data"]["modules"]

        test_module = next(
            module
            for module in modules
            if module["id"] == self.module.id
        )

        self.assertEqual(test_module["name"], "Test Module")
        self.assertEqual(test_module["code"], "test_module")

        self.assertEqual(len(test_module["menus"]), 1)

        menu = test_module["menus"][0]

        self.assertEqual(menu["id"], self.menu.id)
        self.assertEqual(menu["name"], "Test Menu")
        self.assertEqual(menu["code"], "test_menu")

        self.assertEqual(len(menu["actions"]), 1)

        action = menu["actions"][0]

        self.assertEqual(action["id"], self.action.id)
        self.assertEqual(action["name"], "Test Action")
        self.assertEqual(action["code"], "test_action")

    def test_inactive_modules_menus_and_actions_are_excluded(self):
        inactive_module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
        )

        inactive_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Menu",
            code="inactive_menu",
            is_active=False,
        )

        inactive_action = Action.objects.create(
            menu=self.menu,
            name="Inactive Action",
            code="inactive_action",
            is_active=False,
        )

        response = self.client.get(self.url)

        data = response.json()

        modules = data["data"]["modules"]

        module_ids = [
            module["id"]
            for module in modules
        ]

        self.assertNotIn(inactive_module.id, module_ids)

        test_module = next(
            module
            for module in modules
            if module["id"] == self.module.id
        )

        menu_ids = [
            menu["id"]
            for menu in test_module["menus"]
        ]

        self.assertNotIn(inactive_menu.id, menu_ids)

        test_menu = next(
            menu
            for menu in test_module["menus"]
            if menu["id"] == self.menu.id
        )

        action_ids = [
            action["id"]
            for action in test_menu["actions"]
        ]

        self.assertNotIn(inactive_action.id, action_ids)

    def test_permission_tree_is_ordered_by_sort_order(self):
        second_module = Module.objects.create(
            name="Second Module",
            code="second_module",
            sort_order=2,
        )

        second_menu = Menu.objects.create(
            module=self.module,
            name="Second Menu",
            code="second_menu",
            sort_order=2,
        )

        second_action = Action.objects.create(
            menu=self.menu,
            name="Second Action",
            code="second_action",
            sort_order=2,
        )

        response = self.client.get(self.url)

        data = response.json()

        modules = data["data"]["modules"]

        self.assertEqual(
            [module["name"] for module in modules],
            ["Access Control", "Test Module", "Second Module"],
        )

        test_module = next(
            module
            for module in modules
            if module["id"] == self.module.id
        )

        self.assertEqual(
            [menu["name"] for menu in test_module["menus"]],
            ["Test Menu", "Second Menu"],
        )

        test_menu = test_module["menus"][0]

        self.assertEqual(
            [action["name"] for action in test_menu["actions"]],
            ["Test Action", "Second Action"],
        )

    def test_unauthenticated_user_cannot_retrieve_permission_tree(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

class GroupPermissionGroupsAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="group_permission_groups_admin",
            password="testpassword123",
        )

        self.client.login(
            username="group_permission_groups_admin",
            password="testpassword123",
        )

        Module.objects.create(
            name="Access Control",
            code="access_control",
            is_active=True,
        )

        self.url = reverse(
            "access_control:group_permission_groups",
        )

    def test_authenticated_user_can_retrieve_groups(self):
        Group.objects.create(name="Production")
        Group.objects.create(name="Inventory")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["total_groups"], 2)

    def test_groups_are_ordered_alphabetically(self):
        Group.objects.create(name="Production")
        Group.objects.create(name="Accounts")
        Group.objects.create(name="Inventory")

        response = self.client.get(self.url)

        groups = response.json()["data"]["groups"]

        self.assertEqual(
            [group["name"] for group in groups],
            ["Accounts", "Inventory", "Production"],
        )

    def test_empty_groups_returns_empty_list(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(data["groups"], [])
        self.assertEqual(data["total_groups"], 0)

    def test_unauthenticated_user_cannot_retrieve_groups(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

class MenuDeleteViewTests(TestCase):

    def setUp(self):
        self.access_control_module = Module.objects.create(
            name="Access Control",
            code="access_control",
            is_active=True,
        )

        self.menus_menu = Menu.objects.create(
            module=self.access_control_module,
            name="Menus",
            code="menus",
            is_active=True,
        )

        self.delete_menu_permission = Action.objects.create(
            menu=self.menus_menu,
            name="Delete Menu",
            code="delete_menu",
            is_active=True,
        )

        self.target_module = Module.objects.create(
            name="Production",
            code="production",
            is_active=True,
        )

        self.target_menu = Menu.objects.create(
            module=self.target_module,
            name="Cutting",
            code="cutting",
            is_active=True,
        )

        self.superuser = User.objects.create_superuser(
            username="menu_delete_admin",
            email="menu_delete_admin@example.com",
            password="TestPassword123!",
        )

        self.normal_user = User.objects.create_user(
            username="menu_delete_user",
            password="TestPassword123!",
        )

        self.group = Group.objects.create(
            name="Production Team",
        )

        self.url = reverse(
            "access_control:menu_delete",
            args=[
                self.target_module.id,
                self.target_menu.id,
            ],
        )

    def test_menu_delete_requires_login(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Menu.objects.filter(
                id=self.target_menu.id,
            ).exists()
        )

    def test_menu_delete_allows_superuser(self):
        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertTrue(response.json()["success"])

        self.assertFalse(
            Menu.objects.filter(
                id=self.target_menu.id,
            ).exists()
        )

    def test_menu_delete_blocks_child_menus(self):
        child_menu = Menu.objects.create(
            module=self.target_module,
            parent=self.target_menu,
            name="Fabric Cutting",
            code="fabric_cutting",
        )

        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 409)

        self.assertFalse(response.json()["success"])

        self.assertTrue(
            Menu.objects.filter(
                id=self.target_menu.id,
            ).exists()
        )

        self.assertTrue(
            Menu.objects.filter(
                id=child_menu.id,
            ).exists()
        )

    def test_menu_delete_blocks_linked_actions(self):
        Action.objects.create(
            menu=self.target_menu,
            name="Start Cutting",
            code="start_cutting",
        )

        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 409)

        self.assertFalse(response.json()["success"])

        self.assertTrue(
            Menu.objects.filter(
                id=self.target_menu.id,
            ).exists()
        )

    def test_menu_delete_blocks_group_permission_assignment(self):
        GroupPermission.objects.create(
            group=self.group,
            menu=self.target_menu,
        )

        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 409)

        data = response.json()

        self.assertFalse(data["success"])

        self.assertEqual(
            data["data"]["group_permissions_count"],
            1,
        )

        self.assertEqual(
            data["data"]["user_permissions_count"],
            0,
        )

        self.assertTrue(
            Menu.objects.filter(
                id=self.target_menu.id,
            ).exists()
        )

    def test_menu_delete_blocks_user_permission_assignment(self):
        UserPermission.objects.create(
            user=self.normal_user,
            menu=self.target_menu,
        )

        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 409)

        data = response.json()

        self.assertFalse(data["success"])

        self.assertEqual(
            data["data"]["group_permissions_count"],
            0,
        )

        self.assertEqual(
            data["data"]["user_permissions_count"],
            1,
        )

        self.assertTrue(
            Menu.objects.filter(
                id=self.target_menu.id,
            ).exists()
        )

    def test_menu_delete_blocks_both_permission_assignments(self):
        GroupPermission.objects.create(
            group=self.group,
            menu=self.target_menu,
        )

        UserPermission.objects.create(
            user=self.normal_user,
            menu=self.target_menu,
        )

        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 409)

        data = response.json()

        self.assertEqual(
            data["data"]["group_permissions_count"],
            1,
        )

        self.assertEqual(
            data["data"]["user_permissions_count"],
            1,
        )

        self.assertTrue(
            Menu.objects.filter(
                id=self.target_menu.id,
            ).exists()
        )

    def test_menu_delete_returns_404_for_missing_menu(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:menu_delete",
                args=[
                    self.target_module.id,
                    999999,
                ],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_menu_delete_returns_404_for_missing_module(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "access_control:menu_delete",
                args=[
                    999999,
                    self.target_menu.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_menu_delete_rejects_get_request(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

        self.assertTrue(
            Menu.objects.filter(
                id=self.target_menu.id,
            ).exists()
        )