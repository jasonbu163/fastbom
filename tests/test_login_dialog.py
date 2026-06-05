import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from config import AppSettings, InMemorySettingsStore, load_settings
from gui.login_dialog import LoginDialog
from services.auth_service import AuthService


class LoginDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_backend_settings_adds_http_scheme_for_host_port(self):
        store = InMemorySettingsStore()
        settings = AppSettings()
        dialog = LoginDialog(AuthService(settings), settings=settings, settings_store=store)

        dialog.save_backend_settings("127.0.0.1:18080", 20)
        loaded = load_settings(store=store)

        self.assertEqual(loaded.remote_api.base_url, "http://127.0.0.1:18080")
        self.assertEqual(loaded.remote_api.timeout_seconds, 20)


if __name__ == "__main__":
    unittest.main()
