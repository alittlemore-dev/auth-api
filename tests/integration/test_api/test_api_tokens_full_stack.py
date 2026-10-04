from datetime import UTC, datetime, timedelta

import pytest
from argon2 import PasswordHasher
from litestar.testing import TestClient
from sqlalchemy import String, select, type_coerce, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.enums import RoleEnum
from core.auth.schemas import AccessTokenPayload
from core.auth.token_handlers import TokenHandler
from infra.auth.token_handlers import PasetoTokenHandler
from infra.postgresql.models import ApiTokenModel, UserModel
from tests.integration.test_api.test_auth_full_stack import (
    auth_client as auth_client,
)
from tests.integration.test_api.test_auth_full_stack import (
    telegram_status as telegram_status,
)

BASE = "/api/auth/account/me/api-tokens"
PASSWORD = "integration-password"  # noqa: S105


def browser_headers(client: TestClient, *, username: str = "owner") -> dict[str, str]:
    login = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['accessToken']}", "X-CSRF-Guard": "1"}


def token_payload(*, permissions: list[str] | None = None) -> dict[str, object]:
    return {
        "name": "local CLI",
        "password": PASSWORD,
        "permissions": permissions or ["auth.account.read"],
        "expiresAt": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
    }


async def test_api_token_lifecycle_hash_encryption_and_logout_independence(
    auth_client: TestClient,
    session: AsyncSession,
) -> None:
    browser = browser_headers(auth_client)
    created = auth_client.post(BASE, json=token_payload(), headers=browser)
    assert created.status_code == 201
    assert created.headers["cache-control"] == "no-store"
    first = created.json()
    secret = first["secret"]
    token_id = first["token"]["id"]
    assert secret.startswith("alm_pat_")
    assert first["token"]["status"] == "active"
    assert "secret" not in first["token"]
    assert first["token"]["lastUsedAt"] is None
    stored_hash, stored_secret = (
        await session.execute(
            select(
                ApiTokenModel.secret_hash,
                type_coerce(ApiTokenModel.secret, String),
            ).where(ApiTokenModel.id == token_id)
        )
    ).one()
    assert secret not in stored_secret
    assert stored_hash != secret
    assert len(stored_hash) == 64
    token_bearer = {"Authorization": f"Bearer {secret}"}
    verified = auth_client.post("/api/auth/verify/v2", headers=token_bearer)
    assert verified.status_code == 200
    assert verified.json() == {
        "username": "owner",
        "role": "owner",
        "credentialType": "pat",
        "credentialId": token_id,
        "permissions": ["auth.account.read"],
        "validForSeconds": verified.json()["validForSeconds"],
        "cacheTtlSeconds": 0,
    }
    assert 0 < verified.json()["validForSeconds"] <= 3600
    assert verified.headers["cache-control"] == "no-store"
    assert auth_client.post("/api/auth/verify", headers=token_bearer).status_code == 401
    assert auth_client.get("/api/auth/account/me", headers=token_bearer).status_code == 200
    assert (
        auth_client.patch("/api/auth/account/me", json={}, headers=token_bearer).status_code == 403
    )
    assert auth_client.get(BASE, headers=token_bearer).status_code == 403
    assert auth_client.post("/api/auth/logout", headers=token_bearer).status_code == 403
    assert (
        auth_client.get(
            "/api/auth/admin/accounts?page=1&pageSize=20", headers=token_bearer
        ).status_code
        == 403
    )
    token_list = auth_client.get(BASE, headers=browser)
    assert token_list.json()["tokens"][0]["lastUsedAt"] is not None
    assert "secret" not in token_list.text
    assert "secretHash" not in token_list.text
    wrong_password = auth_client.post(
        f"{BASE}/{token_id}/reveal",
        json={"password": "wrong"},
        headers=browser,
    )
    assert wrong_password.status_code == 403
    assert wrong_password.json()["message"] == "Current-password confirmation failed"
    revealed = auth_client.post(
        f"{BASE}/{token_id}/reveal",
        json={"password": PASSWORD},
        headers=browser,
    )
    assert revealed.json() == {"secret": secret}
    assert revealed.headers["cache-control"] == "no-store"
    second = auth_client.post(BASE, json=token_payload(), headers=browser).json()
    assert second["secret"] != secret
    assert auth_client.post("/api/auth/logout", headers=browser).status_code == 200
    assert auth_client.post("/api/auth/verify/v2", headers=token_bearer).status_code == 200
    browser = browser_headers(auth_client)
    revoked = auth_client.post(f"{BASE}/{token_id}/revoke", headers=browser)
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert auth_client.post("/api/auth/verify/v2", headers=token_bearer).status_code == 401
    assert (
        auth_client.post(
            f"{BASE}/{token_id}/reveal",
            json={"password": PASSWORD},
            headers=browser,
        ).status_code
        == 403
    )
    assert auth_client.post("/api/auth/verify/v2", headers=browser).status_code == 200
    assert (
        auth_client.post(
            "/api/auth/verify/v2",
            headers={"Authorization": f"Bearer {second['secret']}"},
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "invalid",
    [
        {"name": " "},
        {"permissions": []},
        {"permissions": ["*"]},
        {"permissions": ["auth.account.unknown"]},
        {"expiresAt": "2020-01-01T00:00:00Z"},
        {"expiresAt": "2099-01-01T00:00:00Z"},
        {"expiresAt": "2026-10-04T00:00:00"},
    ],
)
def test_api_token_creation_validation(auth_client: TestClient, invalid: dict[str, object]) -> None:
    browser = browser_headers(auth_client)
    response = auth_client.post(BASE, json={**token_payload(), **invalid}, headers=browser)
    assert response.status_code == 400
    assert response.headers["cache-control"] == "no-store"
    assert auth_client.get(BASE, headers=browser).json() == {"tokens": []}


def test_api_token_management_csrf_password_rate_limit(auth_client: TestClient) -> None:
    browser = browser_headers(auth_client)
    assert auth_client.post(BASE, json=token_payload()).status_code == 401
    no_csrf = {"Authorization": browser["Authorization"]}
    assert auth_client.post(BASE, json=token_payload(), headers=no_csrf).status_code == 403
    assert (
        auth_client.post(
            BASE,
            json=token_payload(),
            headers={**browser, "Sec-Fetch-Site": "cross-site"},
        ).status_code
        == 403
    )
    for _ in range(10):
        response = auth_client.post(
            BASE, json={**token_payload(), "password": "wrong"}, headers=browser
        )
        if response.status_code == 429:
            break
        assert response.status_code == 403
    limited = auth_client.post(BASE, json=token_payload(), headers=browser)
    assert limited.status_code == 429
    assert limited.headers["cache-control"] == "no-store"


async def test_role_filtered_permissions_ownership_expiry_and_role_changes(
    auth_client: TestClient,
    session: AsyncSession,
) -> None:
    session.add(
        UserModel(
            username="moderator",
            password_hash=PasswordHasher().hash(PASSWORD),
            role=RoleEnum.MODERATOR,
            is_active=True,
        )
    )
    await session.commit()
    owner_browser = browser_headers(auth_client)
    created = auth_client.post(
        BASE,
        json=token_payload(
            permissions=[
                "auth.account.read",
                "auth.accounts.read",
            ]
        ),
        headers=owner_browser,
    ).json()
    moderator = browser_headers(auth_client, username="moderator")
    permissions = auth_client.get(f"{BASE}/permissions", headers=moderator).json()["permissions"]
    codes = {permission["code"] for permission in permissions}
    assert "auth.accounts.read" not in codes
    assert "competency.articles.read" in codes
    assert "workspace.resumes.read" in codes
    assert (
        auth_client.post(
            BASE,
            json=token_payload(
                permissions=[
                    "auth.accounts.read",
                ]
            ),
            headers=moderator,
        ).status_code
        == 400
    )
    assert (
        auth_client.post(
            f"{BASE}/{created['token']['id']}/reveal",
            json={
                "password": PASSWORD,
            },
            headers=moderator,
        ).status_code
        == 404
    )
    assert (
        auth_client.post(f"{BASE}/{created['token']['id']}/revoke", headers=moderator).status_code
        == 404
    )
    await session.execute(
        update(UserModel).where(UserModel.username == "owner").values(role=RoleEnum.MODERATOR)
    )
    await session.commit()
    pat = {"Authorization": f"Bearer {created['secret']}"}
    assert auth_client.post("/api/auth/verify/v2", headers=pat).json()["permissions"] == [
        "auth.account.read"
    ]
    assert (
        auth_client.get("/api/auth/admin/accounts?page=1&pageSize=20", headers=pat).status_code
        == 403
    )
    await session.execute(
        update(ApiTokenModel)
        .where(ApiTokenModel.id == created["token"]["id"])
        .values(
            expires_at=datetime.now(tz=UTC) - timedelta(seconds=1),
        )
    )
    await session.commit()
    assert auth_client.post("/api/auth/verify/v2", headers=pat).status_code == 401
    expired_reveal = auth_client.post(
        f"{BASE}/{created['token']['id']}/reveal",
        json={"password": PASSWORD},
        headers=owner_browser,
    )
    assert expired_reveal.status_code == 403
    assert expired_reveal.json()["message"] == "API token is inactive"
    assert auth_client.post("/api/auth/verify/v2", headers=owner_browser).status_code == 200
    assert auth_client.get(BASE, headers=owner_browser).json()["tokens"][0]["status"] == "expired"


async def test_pat_session_operations_and_password_revocation(auth_client: TestClient) -> None:
    browser = browser_headers(auth_client)
    credential = auth_client.post(
        BASE,
        json=token_payload(
            permissions=[
                "auth.sessions.read",
                "auth.sessions.revoke",
                "auth.accounts.password",
            ]
        ),
        headers=browser,
    ).json()
    pat = {"Authorization": f"Bearer {credential['secret']}"}
    sessions = auth_client.get("/api/auth/admin/accounts/owner/sessions", headers=pat)
    assert sessions.status_code == 200
    assert all(not session["isCurrent"] for session in sessions.json()["sessions"])
    others_revoked = auth_client.post(
        "/api/auth/admin/accounts/owner/sessions/revoke-others",
        headers=pat,
    )
    assert others_revoked.status_code == 200
    assert others_revoked.json() == {"currentSessionRevoked": False}
    assert auth_client.post("/api/auth/verify/v2", headers=browser).status_code == 401
    assert (
        auth_client.get("/api/auth/admin/accounts/owner/sessions", headers=pat).json()["sessions"]
        == []
    )
    all_revoked = auth_client.post(
        "/api/auth/admin/accounts/owner/sessions/revoke-all", headers=pat
    )
    assert all_revoked.status_code == 200
    assert all_revoked.json() == {"currentSessionRevoked": False}
    assert auth_client.post("/api/auth/verify/v2", headers=pat).status_code == 200
    changed = auth_client.put(
        "/api/auth/admin/accounts/owner/password",
        json={
            "password": "replacement-password",
        },
        headers=pat,
    )
    assert changed.status_code == 200
    assert auth_client.post("/api/auth/verify/v2", headers=pat).status_code == 401


async def test_deactivation_revokes_tokens_permanently(
    auth_client: TestClient, session: AsyncSession
) -> None:
    session.add(
        UserModel(
            username="moderator",
            password_hash=PasswordHasher().hash(PASSWORD),
            role=RoleEnum.MODERATOR,
            is_active=True,
        )
    )
    await session.commit()
    moderator = browser_headers(auth_client, username="moderator")
    token = auth_client.post(BASE, json=token_payload(), headers=moderator).json()
    owner = browser_headers(auth_client)
    pat = {"Authorization": f"Bearer {token['secret']}"}
    assert (
        auth_client.post("/api/auth/admin/accounts/moderator/deactivate", headers=owner).status_code
        == 200
    )
    assert auth_client.post("/api/auth/verify/v2", headers=pat).status_code == 401
    assert (
        auth_client.post("/api/auth/admin/accounts/moderator/activate", headers=owner).status_code
        == 200
    )
    assert auth_client.post("/api/auth/verify/v2", headers=pat).status_code == 401


def test_v2_session_contract_and_malformed_bearers(auth_client: TestClient) -> None:
    browser = browser_headers(auth_client)
    verified = auth_client.post("/api/auth/verify/v2", headers=browser)
    assert verified.status_code == 200
    data = verified.json()
    assert data["credentialType"] == "session"
    assert data["credentialId"]
    assert data["permissions"] == []
    assert 0 < data["validForSeconds"] <= 900
    assert 0 <= data["cacheTtlSeconds"] <= data["validForSeconds"]
    for value in (
        "Beareralm_pat_invalid",
        "Bearer alm_pat_invalid trailing",
        "Bearer  alm_pat_invalid",
    ):
        response = auth_client.post("/api/auth/verify/v2", headers={"Authorization": value})
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"


def test_password_validation_does_not_return_sensitive_input(auth_client: TestClient) -> None:
    browser = browser_headers(auth_client)
    password = "PRIVATE-PASSWORD-VALUE-" * 100
    response = auth_client.post(
        BASE, json={**token_payload(), "password": password}, headers=browser
    )
    assert response.status_code == 400
    assert "PRIVATE-PASSWORD-VALUE" not in response.text


async def test_expired_browser_credential_remains_401_and_refresh_recovers_creation(
    auth_client: TestClient,
) -> None:
    browser = browser_headers(auth_client)
    session_id = auth_client.post("/api/auth/verify/v2", headers=browser).json()["credentialId"]
    async with auth_client.app.state.dishka_container() as request_container:
        token_handler = await request_container.get(TokenHandler)
    assert isinstance(token_handler, PasetoTokenHandler)
    expired_token = PasetoTokenHandler(
        public_key_pem=token_handler.public_key_pem,
        secret_key_pem=token_handler.secret_key_pem,
        token_expire_seconds=-1,
    ).encode_token(AccessTokenPayload(username="owner", session_id=session_id))
    expired_headers = {**browser, "Authorization": f"Bearer {expired_token.decode()}"}
    expired = auth_client.post(BASE, json=token_payload(), headers=expired_headers)
    assert expired.status_code == 401
    assert expired.headers["cache-control"] == "no-store"
    refreshed = auth_client.post("/api/auth/refresh", headers={"X-CSRF-Guard": "1"})
    assert refreshed.status_code == 200
    fresh_browser = {**browser, "Authorization": f"Bearer {refreshed.json()['accessToken']}"}
    confirmed = auth_client.post(BASE, json=token_payload(), headers=fresh_browser)
    assert confirmed.status_code == 201
    token_id = confirmed.json()["token"]["id"]
    expired_reveal = auth_client.post(
        f"{BASE}/{token_id}/reveal",
        json={"password": PASSWORD},
        headers=expired_headers,
    )
    assert expired_reveal.status_code == 401
    assert (
        auth_client.post(
            f"{BASE}/{token_id}/reveal",
            json={"password": PASSWORD},
            headers=fresh_browser,
        ).status_code
        == 200
    )
    wrong = auth_client.post(
        BASE, json={**token_payload(), "password": "wrong"}, headers=fresh_browser
    )
    assert wrong.status_code == 403
    assert auth_client.post("/api/auth/verify/v2", headers=fresh_browser).status_code == 200
