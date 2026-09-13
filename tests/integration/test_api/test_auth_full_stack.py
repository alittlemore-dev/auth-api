from collections.abc import AsyncGenerator

import pytest_asyncio
from argon2 import PasswordHasher
from dishka import Provider, Scope, make_async_container, provide
from litestar.stores.memory import MemoryStore
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.enums import RoleEnum
from core.auth.storages import TokenRevocationStorage
from entrypoints.litestar.initializers.main import create_litestar_app
from infra.ioc.registry import get_providers
from infra.postgresql.models import AuthSessionModel, UserModel
from infra.valkey.storages import ValkeyTokenRevocationStorage


class IntegrationRevocationProvider(Provider):
    # Only the external Valkey transport is replaced; HTTP, crypto, use cases and DB are real.
    @provide(scope=Scope.APP, override=True)
    def revocations(self) -> TokenRevocationStorage:
        return ValkeyTokenRevocationStorage(store=MemoryStore())


@pytest_asyncio.fixture
async def auth_client(session: AsyncSession) -> AsyncGenerator[TestClient]:
    session.add(
        UserModel(
            username="owner",
            password_hash=PasswordHasher().hash("integration-password"),
            role=RoleEnum.OWNER,
            is_active=True,
        )
    )
    await session.commit()
    container = make_async_container(*get_providers(), IntegrationRevocationProvider())
    app = create_litestar_app(
        lifespan=[],
        container=container,
        extra_plugins=[],
        extra_middlewares=[],
    )
    try:
        with TestClient(app, base_url="https://testserver.local") as client:
            yield client
    finally:
        await container.close()


async def test_login_refresh_logout_revokes_session_and_access(
    auth_client: TestClient,
    session: AsyncSession,
) -> None:
    assert auth_client.get("/api/auth/admin/accounts?page=1&pageSize=20").status_code == 401
    bad_login = auth_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "incorrect"},
    )
    assert bad_login.status_code == 401
    login = auth_client.post(
        "/api/auth/login",
        json={"username": "OWNER", "password": "integration-password"},
    )
    assert login.status_code == 200
    assert login.headers["cache-control"] == "no-store"
    for flag in ("Secure", "HttpOnly", "SameSite=lax", "Path=/api/auth"):
        assert flag in login.headers["set-cookie"]
    token = login.json()["accessToken"]
    bearer = {"Authorization": f"Bearer {token}"}
    account = auth_client.get("/api/auth/account/base", headers=bearer)
    assert account.json() == {"username": "owner", "role": "owner"}
    assert (
        auth_client.get("/api/auth/admin/accounts?page=1&pageSize=20", headers=bearer).status_code
        == 200
    )
    assert auth_client.post("/api/auth/refresh").status_code == 403
    assert (
        auth_client.post(
            "/api/auth/refresh",
            headers={"X-CSRF-Guard": "1", "Sec-Fetch-Site": "cross-site"},
        ).status_code
        == 403
    )
    refreshed = auth_client.post("/api/auth/refresh", headers={"X-CSRF-Guard": "1"})
    assert refreshed.status_code == 200
    refreshed_bearer = {"Authorization": f"Bearer {refreshed.json()['accessToken']}"}
    logout = auth_client.post(
        "/api/auth/logout",
        headers={**refreshed_bearer, "X-CSRF-Guard": "1"},
    )
    assert logout.status_code == 200
    assert "Max-Age=0" in logout.headers["set-cookie"]
    assert (
        auth_client.get("/api/auth/admin/accounts?page=1&pageSize=20", headers=bearer).status_code
        == 401
    )
    assert (
        auth_client.get(
            "/api/auth/admin/accounts?page=1&pageSize=20", headers=refreshed_bearer
        ).status_code
        == 401
    )
    assert auth_client.post("/api/auth/refresh", headers={"X-CSRF-Guard": "1"}).status_code == 401
    session.expire_all()
    stored_session = (await session.scalars(select(AuthSessionModel))).one()
    assert stored_session.is_revoked is True
