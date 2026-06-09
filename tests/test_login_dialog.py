import os
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from auth import AuthSession
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

    def test_backend_login_runs_without_blocking_dialog(self):
        started = threading.Event()
        release = threading.Event()

        class BlockingAuthService:
            def login_backend_user(self, _username: str, _password: str):
                started.set()
                release.wait(1)
                return AuthSession.backend_user(
                    username="operator",
                    access_token="access-token",
                    refresh_token="refresh-token",
                )

        dialog = LoginDialog(
            BlockingAuthService(),
            settings=AppSettings(),
            settings_store=InMemorySettingsStore(),
        )
        dialog.username_edit.setText("operator")
        dialog.password_edit.setText("secret")

        started_at = time.monotonic()
        dialog._login_backend()
        elapsed = time.monotonic() - started_at

        self.assertLess(elapsed, 0.2)
        self.assertFalse(dialog.backend_login_btn.isEnabled())
        self.assertTrue(started.wait(1))

        release.set()
        deadline = time.monotonic() + 1
        while dialog._login_thread is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)

        self.assertIsNone(dialog._login_thread)
        self.assertEqual(dialog.auth_session.username, "operator")


if __name__ == "__main__":
    unittest.main()
