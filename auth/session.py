from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.remote_api import RemoteApiSession


@dataclass(frozen=True)
class AuthSession:
    auth_mode: str
    username: str
    display_name: str = ""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"

    @classmethod
    def fallback_admin(cls, username: str) -> "AuthSession":
        return cls(auth_mode="fallback_admin", username=username, display_name="离线管理员")

    @classmethod
    def backend_user(
        cls,
        username: str,
        access_token: str,
        refresh_token: str,
        token_type: str = "bearer",
        display_name: str = "",
    ) -> "AuthSession":
        return cls(
            auth_mode="backend_user",
            username=username,
            display_name=display_name or username,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
        )

    @property
    def can_use_remote_features(self) -> bool:
        return self.auth_mode == "backend_user" and bool(self.access_token)

    @property
    def remote_api_session(self) -> Optional[RemoteApiSession]:
        if not self.can_use_remote_features or not self.refresh_token:
            return None
        return RemoteApiSession(
            access_token=str(self.access_token),
            refresh_token=str(self.refresh_token),
            token_type=self.token_type,
        )
