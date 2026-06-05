import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from auth.session import AuthSession
from config import AppSettings
from gui.pages.residual_material_page import ResidualMaterialPage


class ResidualMaterialPageAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_page_has_no_own_login_button(self):
        page = ResidualMaterialPage(
            settings=AppSettings(),
            auth_session=AuthSession.fallback_admin("admin"),
        )

        self.assertFalse(hasattr(page, "login_btn"))

    def test_fallback_admin_disables_remote_actions(self):
        page = ResidualMaterialPage(
            settings=AppSettings(),
            auth_session=AuthSession.fallback_admin("admin"),
        )

        self.assertFalse(page.refresh_btn.isEnabled())
        self.assertFalse(page.add_material_btn.isEnabled())
        self.assertIn("离线", page.login_state_label.text())

    def test_backend_user_enables_remote_actions_and_sets_client_session(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
            display_name="操作员",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)

        self.assertTrue(page.refresh_btn.isEnabled())
        self.assertTrue(page.add_material_btn.isEnabled())
        self.assertEqual(page.client.session.access_token, "access-token")
        self.assertIn("操作员", page.user_label.text())


if __name__ == "__main__":
    unittest.main()
