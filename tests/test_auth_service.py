import unittest
from unittest.mock import Mock

from config import AppSettings
from services.auth_service import AuthError, AuthService
from services.remote_api import RemoteApiSession


class AuthServiceTests(unittest.TestCase):
    def test_fallback_admin_login_creates_local_only_session(self):
        settings = AppSettings()
        service = AuthService(settings)

        session = service.login_fallback_admin("admin", "#456@admin")

        self.assertEqual(session.auth_mode, "fallback_admin")
        self.assertEqual(session.username, "admin")
        self.assertIsNone(session.remote_api_session)
        self.assertFalse(session.can_use_remote_features)

    def test_fallback_admin_rejects_wrong_password(self):
        service = AuthService(AppSettings())

        with self.assertRaises(AuthError):
            service.login_fallback_admin("admin", "wrong")

    def test_backend_login_rejects_admin_username_before_remote_call(self):
        client = Mock()
        service = AuthService(AppSettings(), client_factory=lambda _config: client)

        with self.assertRaises(AuthError):
            service.login_backend_user("admin", "secret")

        client.login.assert_not_called()

    def test_backend_login_creates_remote_enabled_session(self):
        client = Mock()
        client.login.return_value = RemoteApiSession("access-token", "refresh-token")
        client.get_current_user.return_value = {
            "username": "operator",
            "displayName": "操作员",
        }
        service = AuthService(AppSettings(), client_factory=lambda _config: client)

        session = service.login_backend_user("operator", "secret")

        self.assertEqual(session.auth_mode, "backend_user")
        self.assertEqual(session.username, "operator")
        self.assertEqual(session.display_name, "操作员")
        self.assertTrue(session.can_use_remote_features)
        self.assertEqual(session.remote_api_session.access_token, "access-token")


if __name__ == "__main__":
    unittest.main()
