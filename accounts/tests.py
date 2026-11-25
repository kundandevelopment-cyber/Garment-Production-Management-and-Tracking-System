
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from access_control.models import (
    Action,
    GroupPermission,
    Menu,
    Module,
    UserPermission,
)


User = get_user_model()


class GroupPermissionAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.module = Module.objects.create(
            name="Access Control",
            code="access_control",
        )

        cls.menu = Menu.objects.create(
            module=cls.module,
            name="Permissions",
            code="permissions",
        )

        cls.action = Action.objects.create(
            menu=cls.menu,
            name="Manage Group Permissions",
            code="manage_group_permissions",
        )

        cls.group = Group.objects.create(
            name="Production Test Group",
        )

        cls.user = User.objects.create_user(
            username="permission_test_user",
            password="TestPassword123!",
        )

        cls.superuser = User.objects.create_superuser(
            username="permission_test_admin",
            email="admin@example.com",
            password="TestPassword123!",
        )

    def setUp(self):
        self.url = reverse(
            "accounts:group_permissions",
            kwargs={"group_id": self.group.pk},
        )

    def grant_permission_management_access(self, user):
        """
        Grant the user module, menu, and action permissions.
        This satisfies the complete access-control hierarchy.
        """
        UserPermission.objects.create(
            user=user,
            module=self.module,
        )

        UserPermission.objects.create(
            user=user,
            menu=self.menu,
        )

        UserPermission.objects.create(
            user=user,
            action=self.action,
        )

    def test_unauthenticated_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_user_without_permission_is_denied_get(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_user_with_permission_can_access_get(self):
        self.grant_permission_management_access(self.user)
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_user_without_permission_cannot_modify_group_permissions(self):
        self.client.force_login(self.user)

        existing_permission = GroupPermission.objects.create(
            group=self.group,
            module=self.module,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                "permissions": [],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            GroupPermission.objects.filter(
                pk=existing_permission.pk,
                group=self.group,
                module=self.module,
            ).exists()
        )

    def test_superuser_can_access_group_permissions(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_user_with_permission_can_update_group_permissions(self):
        self.grant_permission_management_access(self.user)
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            data=json.dumps({
                "permissions": [],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))

    
    def test_saving_permissions_preserves_inactive_module_permission(self):
        self.grant_permission_management_access(self.user)
        self.client.force_login(self.user)

        inactive_module = Module.objects.create(
            name="Inactive Module",
            code="inactive_module",
            is_active=False,
        )

        GroupPermission.objects.create(
            group=self.group,
            module=inactive_module,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                "permissions": [
                    {
                        "type": "module",
                        "id": self.module.pk,
                    }
                ],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            GroupPermission.objects.filter(
                group=self.group,
                module=inactive_module,
            ).exists()
        )

        self.assertTrue(
            GroupPermission.objects.filter(
                group=self.group,
                module=self.module,
            ).exists()
        )

    def test_saving_permissions_preserves_inactive_menu_permission(self):
        self.grant_permission_management_access(self.user)
        self.client.force_login(self.user)

        inactive_menu = Menu.objects.create(
            module=self.module,
            name="Inactive Menu",
            code="inactive_menu",
            is_active=False,
        )

        GroupPermission.objects.create(
            group=self.group,
            menu=inactive_menu,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                "permissions": [],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            GroupPermission.objects.filter(
                group=self.group,
                menu=inactive_menu,
            ).exists()
        )


    def test_saving_permissions_preserves_inactive_action_permission(self):
        self.grant_permission_management_access(self.user)
        self.client.force_login(self.user)

        inactive_action = Action.objects.create(
            menu=self.menu,
            name="Inactive Action",
            code="inactive_action",
            is_active=False,
        )

        GroupPermission.objects.create(
            group=self.group,
            action=inactive_action,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                "permissions": [],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            GroupPermission.objects.filter(
                group=self.group,
                action=inactive_action,
            ).exists()
        )

    def test_active_child_menu_appears_when_parent_is_inactive(self):
        self.grant_permission_management_access(self.user)
        self.client.force_login(self.user)

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

        # Simulate a parent being deactivated after
        # its child menu was already created.
        Menu.objects.filter(
            pk=parent_menu.pk,
        ).update(is_active=False)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        module_data = next(
            module
            for module in response_data["modules"]
            if module["id"] == self.module.pk
        )

        displayed_menu_ids = {
            menu["id"]
            for menu in module_data["menus"]
        }

        self.assertIn(
            child_menu.pk,
            displayed_menu_ids,
        )


