from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from config import RemoteApiConfig


class RemoteApiError(Exception):
    pass


class RemoteApiNetworkError(RemoteApiError):
    pass


class RemoteApiHttpError(RemoteApiError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class RemoteApiResponseError(RemoteApiError):
    def __init__(self, message: str, error_code: str = ""):
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True)
class RemoteApiSession:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RemoteApiClient:
    def __init__(self, config: RemoteApiConfig):
        self.config = config
        self.session: Optional[RemoteApiSession] = None

    def update_config(self, config: RemoteApiConfig) -> None:
        self.config = config

    def set_session(self, session: Optional[RemoteApiSession]) -> None:
        self.session = session

    def health(self) -> Mapping[str, Any]:
        return self._request("GET", "/health", auth_required=False)

    def login(self, username: str, password: str) -> RemoteApiSession:
        data = self._request(
            "POST",
            "/api/v1/auth/login",
            payload={"username": username, "password": password},
            auth_required=False,
        )
        session = RemoteApiSession(
            access_token=str(data["accessToken"]),
            refresh_token=str(data["refreshToken"]),
            token_type=str(data.get("tokenType") or "bearer"),
        )
        self.session = session
        return session

    def logout(self) -> None:
        if self.session is None:
            return
        refresh_token = self.session.refresh_token
        try:
            self._request(
                "POST",
                "/api/v1/auth/logout",
                payload={"refreshToken": refresh_token},
            )
        finally:
            self.session = None

    def get_current_user(self) -> Mapping[str, Any]:
        return self._request("GET", "/api/v1/auth/me")

    def list_materials(self, enabled: Optional[bool] = True) -> list[Mapping[str, Any]]:
        query = {} if enabled is None else {"enabled": enabled}
        return list(self._request("GET", "/api/v1/materials", query=query))

    def create_material(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._request("POST", "/api/v1/materials", payload=payload)

    def list_inventory_items(self, query: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return list(self._request("GET", "/api/v1/inventory-items", query=query))

    def create_inventory_item(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._request("POST", "/api/v1/inventory-items", payload=payload)

    def update_inventory_item(self, item_id: int, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._request("PATCH", f"/api/v1/inventory-items/{item_id}", payload=payload)

    def void_inventory_item(self, item_id: int) -> Mapping[str, Any]:
        return self._request("POST", f"/api/v1/inventory-items/{item_id}/void")

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Mapping[str, Any]] = None,
        query: Optional[Mapping[str, Any]] = None,
        auth_required: bool = True,
    ) -> Any:
        if not self.config.base_url.strip():
            raise RemoteApiResponseError("请先在设置中填写后端 API URL。")

        url = self._build_url(path, query)
        headers = {"Accept": "application/json"}
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth_required:
            if self.session is None:
                raise RemoteApiResponseError("请先登录 PMMS 后端。")
            headers["Authorization"] = f"Bearer {self.session.access_token}"

        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code == 401:
                self.session = None
            raise RemoteApiHttpError(exc.code, self._http_error_message(exc)) from exc
        except (TimeoutError, URLError, OSError) as exc:
            raise RemoteApiNetworkError(f"无法连接后端或请求超时：{exc}") from exc

        try:
            envelope = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise RemoteApiResponseError("后端返回了无法解析的响应。") from exc

        code = envelope.get("code")
        if code != 200:
            message = str(envelope.get("message") or "business_error")
            error_code = str(envelope.get("errorCode") or "")
            raise RemoteApiResponseError(message, error_code=error_code)
        return envelope.get("data")

    def _build_url(self, path: str, query: Optional[Mapping[str, Any]]) -> str:
        base_url = self.config.base_url.rstrip("/") + "/"
        url = urljoin(base_url, path.lstrip("/"))
        clean_query = {
            key: _query_value(value)
            for key, value in (query or {}).items()
            if value is not None and value != ""
        }
        if clean_query:
            url = f"{url}?{urlencode(clean_query)}"
        return url

    @staticmethod
    def _http_error_message(exc: HTTPError) -> str:
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        if not body:
            return f"后端请求失败：HTTP {exc.code}"
        return f"后端请求失败：HTTP {exc.code} {body[:300]}"


def _query_value(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value).lower()
    return value
