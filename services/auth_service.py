from __future__ import annotations

from typing import Callable

from auth.session import AuthSession
from config import AppSettings, RemoteApiConfig
from services.remote_api import RemoteApiClient, RemoteApiError


class AuthError(Exception):
    pass


class AuthService:
    def __init__(
        self,
        settings: AppSettings,
        client_factory: Callable[[RemoteApiConfig], RemoteApiClient] = RemoteApiClient,
    ):
        self.settings = settings
        self.client_factory = client_factory

    def login_fallback_admin(self, username: str, password: str) -> AuthSession:
        expected_username = self.settings.auth.fallback_admin_username
        expected_password = self.settings.auth.fallback_admin_password
        if username.strip() != expected_username or password != expected_password:
            raise AuthError("离线账号或密码不正确。")
        return AuthSession.fallback_admin(username=expected_username)

    def login_backend_user(self, username: str, password: str) -> AuthSession:
        normalized_username = username.strip()
        if not normalized_username or not password:
            raise AuthError("请输入服务器账号和密码。")
        if normalized_username.lower() == "admin":
            raise AuthError("admin 是本地离线账号，不能用于服务器远程功能登录。")

        client = self.client_factory(self.settings.remote_api)
        try:
            remote_session = client.login(normalized_username, password)
            user = client.get_current_user()
        except RemoteApiError as exc:
            raise AuthError(str(exc)) from exc

        backend_username = str(user.get("username") or normalized_username)
        if backend_username.lower() == "admin":
            raise AuthError("服务器 admin 账号不能解锁远程物料库。")

        return AuthSession.backend_user(
            username=backend_username,
            display_name=str(user.get("displayName") or backend_username),
            access_token=remote_session.access_token,
            refresh_token=remote_session.refresh_token,
            token_type=remote_session.token_type,
        )
