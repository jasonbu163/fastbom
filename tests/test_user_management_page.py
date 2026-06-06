import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from auth import AuthSession
from config import AppSettings
from gui.pages.user_management_page import UserManagementPage


class UserManagementPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_fallback_admin_disables_remote_user_management(self):
        page = UserManagementPage(
            settings=AppSettings(),
            auth_session=AuthSession.fallback_admin("admin"),
        )

        self.assertFalse(page.refresh_btn.isEnabled())
        self.assertFalse(page.add_user_btn.isEnabled())
        self.assertIn("离线", page.login_state_label.text())

    def test_backend_session_enables_remote_actions_and_sets_client_session(self):
        session = AuthSession.backend_user(
            username="root",
            access_token="access-token",
            refresh_token="refresh-token",
            display_name="Root",
        )
        page = UserManagementPage(settings=AppSettings(), auth_session=session)

        self.assertTrue(page.refresh_btn.isEnabled())
        self.assertTrue(page.add_user_btn.isEnabled())
        self.assertEqual(page.client.session.access_token, "access-token")
        self.assertEqual(page.user_label.text(), "Root")

    def test_user_page_response_updates_table_and_pagination(self):
        session = AuthSession.backend_user(
            username="root",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = UserManagementPage(settings=AppSettings(), auth_session=session)

        page._on_refresh_all_loaded(
            {
                "current_user": {"username": "root", "displayName": "Root", "role": "admin", "status": "active"},
                "user_page": {
                    "items": [
                        {
                            "username": "viewer01",
                            "displayName": "Viewer 01",
                            "role": "viewer",
                            "status": "active",
                        }
                    ],
                    "meta": {"page": 2, "pageSize": 20, "total": 45},
                },
            }
        )

        self.assertEqual(page.table.rowCount(), 1)
        self.assertEqual(page.table.item(0, 0).text(), "viewer01")
        self.assertEqual(page.table.item(0, 1).text(), "Viewer 01")
        self.assertEqual(page.table.item(0, 2).text(), "查看员")
        self.assertEqual(page.table.item(0, 3).text(), "启用")
        self.assertEqual(page.total_label.text(), "共 45 条")
        self.assertEqual(page.page_label.text(), "第 2 / 3 页")
        page.table.selectRow(0)
        self.assertEqual(page._selected_user()["username"], "viewer01")

    def test_ordinary_user_loaded_from_backend_disables_management_buttons(self):
        session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = UserManagementPage(settings=AppSettings(), auth_session=session)

        page._on_refresh_all_loaded(
            {
                "current_user": {"username": "operator", "displayName": "Operator", "role": "operator", "status": "active"},
                "user_page": {"items": [], "meta": {"page": 1, "pageSize": 20, "total": 0}},
            }
        )

        self.assertTrue(page.refresh_btn.isEnabled())
        self.assertFalse(page.add_user_btn.isEnabled())
        self.assertFalse(page.edit_user_btn.isEnabled())
        self.assertTrue(page.change_own_password_btn.isEnabled())

    def test_admin_role_options_exclude_admin_unless_root_like_user(self):
        session = AuthSession.backend_user(
            username="admin01",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = UserManagementPage(settings=AppSettings(), auth_session=session)
        page.current_user = {"username": "admin01", "role": "admin"}
        page.users = [{"username": "viewer01", "role": "viewer"}]

        self.assertEqual(page._allowed_roles(), ["operator", "viewer"])

        page.current_user = {"username": "root", "role": "admin"}

        self.assertEqual(page._allowed_roles(), ["admin", "operator", "viewer"])


if __name__ == "__main__":
    unittest.main()
