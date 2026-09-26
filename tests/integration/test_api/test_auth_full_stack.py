from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from argon2 import PasswordHasher
from dishka import Provider, Scope, make_async_container, provide
from litestar.stores.memory import MemoryStore
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.enums import RoleEnum
from core.auth.schemas import AccessTokenPayload
from core.auth.storages import TokenRevocationStorage
from core.auth.token_handlers import TokenHandler
from entrypoints.litestar.initializers.main import create_litestar_app
from infra.auth.token_handlers import PasetoTokenHandler
from infra.config.settings import SecretStrExtended, settings
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
    account = auth_client.get("/api/auth/account/me", headers=bearer)
    assert account.headers["cache-control"] == "no-store"
    assert account.json() == {
        "username": "owner",
        "role": "owner",
        "firstName": None,
        "lastName": None,
        "middleName": None,
        "gender": None,
        "hasAvatar": False,
        "settings": {"language": "en", "theme": "light", "telegramBots": {}},
    }
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
    assert auth_client.post("/api/auth/verify", headers=refreshed_bearer).status_code == 401
    assert auth_client.post("/api/auth/refresh", headers={"X-CSRF-Guard": "1"}).status_code == 401
    session.expire_all()
    stored_session = (await session.scalars(select(AuthSessionModel))).one()
    assert stored_session.is_revoked is True


async def test_verify_access_token_full_stack(
    auth_client: TestClient,
    session: AsyncSession,
) -> None:
    missing_token = auth_client.post("/api/auth/verify")
    assert missing_token.status_code == 401
    assert missing_token.headers["cache-control"] == "no-store"
    login = auth_client.post(
        "/api/auth/login",
        json={"username": "OWNER", "password": "integration-password"},
    )
    assert login.status_code == 200
    bearer = {"Authorization": f"Bearer {login.json()['accessToken']}"}

    verification = auth_client.post("/api/auth/verify", headers=bearer)
    assert verification.status_code == 200
    assert verification.headers["cache-control"] == "no-store"
    assert verification.json()["username"] == "owner"
    assert verification.json()["role"] == "owner"
    assert 0 < verification.json()["validForSeconds"] <= 900

    stored_session = (await session.scalars(select(AuthSessionModel))).one()
    async with auth_client.app.state.dishka_container() as request_container:
        token_handler = await request_container.get(TokenHandler)
    assert isinstance(token_handler, PasetoTokenHandler)
    expired_token_handler = PasetoTokenHandler(
        public_key_pem=token_handler.public_key_pem,
        secret_key_pem=token_handler.secret_key_pem,
        token_expire_seconds=-1,
    )
    expired_token = expired_token_handler.encode_token(
        AccessTokenPayload(username="owner", session_id=stored_session.id),
    )
    expired_verification = auth_client.post(
        "/api/auth/verify",
        headers={"Authorization": f"Bearer {expired_token.decode()}"},
    )
    assert expired_verification.status_code == 401
    assert expired_verification.headers["cache-control"] == "no-store"

    stored_session.is_revoked = True
    await session.commit()
    assert auth_client.post("/api/auth/verify", headers=bearer).status_code == 401
    stored_session.is_revoked = False
    await session.commit()

    user = (await session.scalars(select(UserModel).where(UserModel.username == "owner"))).one()
    user.role = RoleEnum.USER
    await session.commit()
    verification = auth_client.post("/api/auth/verify", headers=bearer)
    assert verification.status_code == 200
    assert verification.json()["role"] == "user"
    user.is_active = False
    await session.commit()
    assert auth_client.post("/api/auth/verify", headers=bearer).status_code == 401

    user.is_active = True
    user.role = RoleEnum.OWNER
    await session.commit()
    logout = auth_client.post(
        "/api/auth/logout",
        headers={**bearer, "X-CSRF-Guard": "1"},
    )
    assert logout.status_code == 200
    assert auth_client.post("/api/auth/verify", headers=bearer).status_code == 401


async def test_telegram_account_setting_full_stack(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings.telegram, "available", True)
    monkeypatch.setattr(
        settings.telegram,
        "service_secret",
        SecretStrExtended("test-service-secret"),
    )
    login = auth_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "integration-password"},
    )
    assert login.status_code == 200
    bearer = {"Authorization": f"Bearer {login.json()['accessToken']}"}
    account_path = "/api/auth/account/me"
    internal_path = "/api/auth/internal/telegram/personal-workspace/settings"
    service_headers = {"X-Telegram-Service-Secret": "test-service-secret"}

    initial = auth_client.get(account_path, headers=bearer)
    assert initial.status_code == 200
    assert initial.json()["settings"]["telegramBots"] == {}
    assert initial.headers["cache-control"] == "no-store"
    assert (
        auth_client.put(
            f"{account_path}/settings",
            headers=bearer,
            json={
                "language": "ru",
                "theme": "dark",
                "telegramBots": {"personal-workspace": {"enabled": True}},
            },
        ).status_code
        == 200
    )
    updated = auth_client.get(account_path, headers=bearer)
    assert updated.json()["settings"] == {
        "language": "ru",
        "theme": "dark",
        "telegramBots": {"personal-workspace": {"enabled": True}},
    }

    internal = auth_client.get(
        internal_path,
        headers=service_headers,
        params={"ownerUsername": "owner"},
    )
    assert internal.status_code == 200
    assert internal.json() == {"available": True, "enabled": True}
    assert internal.headers["cache-control"] == "no-store"
    unknown = auth_client.get(
        internal_path,
        headers=service_headers,
        params={"ownerUsername": "unknown"},
    )
    assert unknown.status_code == 200
    assert unknown.json() == {"available": True, "enabled": False}
