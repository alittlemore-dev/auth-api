from dataclasses import dataclass
from typing import Any

from httpx import Response
from litestar.testing import TestClient


@dataclass(kw_only=True, frozen=True, slots=True)
class APIHelper:
    client: TestClient

    @staticmethod
    def _headers_with_cookies(
        *,
        headers: dict[str, str],
        cookies: dict[str, str] | None,
    ) -> dict[str, str]:
        if cookies is None:
            return headers
        return {
            **headers,
            "Cookie": "; ".join(f"{name}={value}" for name, value in cookies.items()),
        }

    def get_health(self) -> Response:
        return self.client.get("/api/auth/healthcheck")

    def get_health_ready(self) -> Response:
        return self.client.get("/api/auth/healthcheck/ready")

    def get_admin_tools_auth_sessions(self) -> Response:
        return self.client.get("/api/auth/admin/tools/auth-sessions")

    def post_admin_tools_auth_sessions_prune(self) -> Response:
        return self.client.post("/api/auth/admin/tools/auth-sessions/prune")

    def get_admin_accounts(self, page: int | None = 1, page_size: int | None = 20) -> Response:
        params: dict[str, int] = {
            key: value
            for key, value in (("page", page), ("pageSize", page_size))
            if value is not None
        }
        return self.client.get("/api/auth/admin/accounts", params=params)

    def post_create_admin_account(self, data: dict[str, Any]) -> Response:
        return self.client.post("/api/auth/admin/accounts", json=data)

    def get_admin_account(self, username: str) -> Response:
        return self.client.get(f"/api/auth/admin/accounts/{username}")

    def put_admin_account_role(self, username: str, data: dict[str, Any]) -> Response:
        return self.client.put(f"/api/auth/admin/accounts/{username}/role", json=data)

    def put_admin_account_password(self, username: str, data: dict[str, Any]) -> Response:
        return self.client.put(f"/api/auth/admin/accounts/{username}/password", json=data)

    def post_activate_admin_account(self, username: str) -> Response:
        return self.client.post(f"/api/auth/admin/accounts/{username}/activate")

    def post_deactivate_admin_account(self, username: str) -> Response:
        return self.client.post(f"/api/auth/admin/accounts/{username}/deactivate")

    def delete_admin_account(self, username: str) -> Response:
        return self.client.delete(f"/api/auth/admin/accounts/{username}")

    def get_admin_account_sessions(self, username: str) -> Response:
        return self.client.get(f"/api/auth/admin/accounts/{username}/sessions")

    def post_revoke_admin_account_session(self, username: str, session_id: str) -> Response:
        return self.client.post(f"/api/auth/admin/accounts/{username}/sessions/{session_id}/revoke")

    def post_revoke_all_admin_account_sessions(self, username: str) -> Response:
        return self.client.post(f"/api/auth/admin/accounts/{username}/sessions/revoke-all")

    def post_revoke_other_admin_account_sessions(self, username: str) -> Response:
        return self.client.post(f"/api/auth/admin/accounts/{username}/sessions/revoke-others")

    def post_login(
        self,
        data: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> Response:
        return self.client.post("/api/auth/login", json=data, headers=headers)

    def post_refresh(
        self,
        *,
        cookies: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        csrf_guard: bool = True,
    ) -> Response:
        request_headers = dict(headers or {})
        if csrf_guard:
            request_headers["X-CSRF-Guard"] = "1"
        return self.client.post(
            "/api/auth/refresh",
            headers=self._headers_with_cookies(headers=request_headers, cookies=cookies),
        )

    def post_logout(
        self,
        *,
        cookies: dict[str, str] | None = None,
        csrf_guard: bool = True,
    ) -> Response:
        headers: dict[str, str] = {}
        if csrf_guard:
            headers["X-CSRF-Guard"] = "1"
        return self.client.post(
            "/api/auth/logout",
            headers=self._headers_with_cookies(headers=headers, cookies=cookies),
        )

    def get_get_base_current_user_account(self) -> Response:
        return self.client.get("/api/auth/account/base")
