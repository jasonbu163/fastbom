import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main
from auth import AuthSession
from config import AppSettings, RemoteApiConfig


class MainStartupTests(unittest.TestCase):
    def test_main_window_uses_settings_saved_in_login_dialog(self):
        initial_settings = AppSettings()
        login_settings = AppSettings(
            app=initial_settings.app,
            bom=initial_settings.bom,
            output=initial_settings.output,
            solidworks=initial_settings.solidworks,
            dxf=initial_settings.dxf,
            remote_api=RemoteApiConfig(base_url="http://127.0.0.1:18080", timeout_seconds=20),
            auth=initial_settings.auth,
        )
        created_windows = []

        class FakeApplication:
            def __init__(self, _argv):
                pass

            def exec(self):
                return 0

        class FakeLoginDialog:
            DialogCode = SimpleNamespace(Accepted=1)

            def __init__(self, _auth_service, settings, settings_store):
                self.settings = login_settings
                self.auth_session = AuthSession.backend_user(
                    username="operator",
                    access_token="access-token",
                    refresh_token="refresh-token",
                )
                self.initial_settings = settings
                self.settings_store = settings_store

            def exec(self):
                return self.DialogCode.Accepted

        class FakeMainWindow:
            def __init__(self, **kwargs):
                created_windows.append(kwargs)

            def show(self):
                pass

        with (
            patch.object(main, "QApplication", FakeApplication),
            patch.object(main, "QtSettingsStore", return_value=object()),
            patch.object(main, "load_settings", return_value=initial_settings),
            patch.object(main, "apply_stylesheet"),
            patch.object(main, "LoginDialog", FakeLoginDialog),
            patch.object(main, "MainWindow", FakeMainWindow),
            patch.object(main.sys, "exit", Mock()),
        ):
            main.main()

        self.assertEqual(created_windows[0]["settings"].remote_api.base_url, "http://127.0.0.1:18080")
        self.assertEqual(created_windows[0]["settings"].remote_api.timeout_seconds, 20)


if __name__ == "__main__":
    unittest.main()
