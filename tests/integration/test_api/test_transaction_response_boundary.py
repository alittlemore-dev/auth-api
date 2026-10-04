import json
from collections.abc import Awaitable, Callable
from typing import Any, cast
from unittest.mock import Mock

import pytest
from argon2 import PasswordHasher
from dishka import FromDishka
from dishka.integrations.litestar import DishkaRouter
from litestar import post
from litestar.testing import TestClient
from litestar.types import HTTPRequestEvent, Message, Scope
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.enums import RoleEnum
from core.auth.exceptions import ForbiddenError
from infra.post_commit_actions import PostCommitActions, RollbackActions
from infra.postgresql import meta
from infra.postgresql.models import ApiTokenModel, AuthSessionModel, UserModel
from tests.integration.test_api.test_api_tokens_full_stack import (
    BASE,
    PASSWORD,
    browser_headers,
    token_payload,
)
from tests.integration.test_api.test_auth_full_stack import auth_client as auth_client
from tests.integration.test_api.test_auth_full_stack import telegram_status as telegram_status


async def request_at_response_start(  # noqa: PLR0913
    client: TestClient,
    *,
    method: str,
    path: str,
    observe: Callable[[int], Awaitable[None]],
    data: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any], list[tuple[bytes, bytes]]]:
    body = json.dumps(data).encode() if data is not None else b""
    request_headers = {"content-type": "application/json", **(headers or {})}
    scope = cast(
        "Scope",
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "root_path": "",
            "query_string": b"",
            "headers": [
                (key.lower().encode(), value.encode()) for key, value in request_headers.items()
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver.local", 443),
            "state": {},
        },
    )
    status = 0
    response_headers: list[tuple[bytes, bytes]] = []
    response_body = bytearray()

    async def receive() -> HTTPRequestEvent:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: Message) -> None:
        nonlocal status, response_headers
        if message["type"] == "http.response.start":
            status = message["status"]
            response_headers = list(message["headers"])
            await observe(status)
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    await client.app(scope, receive, send)
    return status, json.loads(response_body), response_headers


async def test_auth_mutations_commit_before_success_response(
    auth_client: TestClient,
) -> None:
    async def login_visible(status: int) -> None:
        assert status == 200
        async with meta.sessionmaker() as observer:
            assert await observer.scalar(select(func.count()).select_from(AuthSessionModel)) == 1

    status, login, _ = await request_at_response_start(
        auth_client,
        method="POST",
        path="/api/auth/login",
        data={"username": "owner", "password": PASSWORD},
        observe=login_visible,
    )
    assert status == 200
    browser = {"Authorization": f"Bearer {login['accessToken']}", "X-CSRF-Guard": "1"}

    async def token_visible(status: int) -> None:
        assert status == 201
        async with meta.sessionmaker() as observer:
            tokens = (await observer.scalars(select(ApiTokenModel))).all()
            assert len(tokens) == 1
            assert tokens[0].revoked_at is None

    _, created, _ = await request_at_response_start(
        auth_client,
        method="POST",
        path=BASE,
        headers=browser,
        data=token_payload(),
        observe=token_visible,
    )
    token_id = created["token"]["id"]

    async def reveal_visible(status: int) -> None:
        assert status == 200
        async with meta.sessionmaker() as observer:
            token = await observer.get(ApiTokenModel, token_id)
            assert token is not None
            assert token.secret.get_secret_value() == created["secret"]

    _, revealed, _ = await request_at_response_start(
        auth_client,
        method="POST",
        path=f"{BASE}/{token_id}/reveal",
        headers=browser,
        data={"password": PASSWORD},
        observe=reveal_visible,
    )
    assert revealed["secret"] == created["secret"]

    async def revocation_visible(status: int) -> None:
        assert status == 200
        async with meta.sessionmaker() as observer:
            token = await observer.get(ApiTokenModel, token_id)
            assert token is not None
            assert token.revoked_at is not None

    await request_at_response_start(
        auth_client,
        method="POST",
        path=f"{BASE}/{token_id}/revoke",
        headers=browser,
        observe=revocation_visible,
    )


async def test_account_credentials_revoke_before_success_response(
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

    browser = browser_headers(auth_client)
    moderator_browser = auth_client.post(
        "/api/auth/login",
        json={"username": "moderator", "password": PASSWORD},
    ).json()["accessToken"]
    moderator_headers = {"Authorization": f"Bearer {moderator_browser}", "X-CSRF-Guard": "1"}
    auth_client.post(BASE, json=token_payload(), headers=moderator_headers).raise_for_status()

    async def deactivation_visible(status: int) -> None:
        assert status == 200
        async with meta.sessionmaker() as observer:
            user = await observer.get(UserModel, "moderator")
            assert user is not None
            assert not user.is_active
            tokens = (
                await observer.scalars(
                    select(ApiTokenModel).where(ApiTokenModel.username == "moderator")
                )
            ).all()
            assert tokens
            assert all(token.revoked_at is not None for token in tokens)
            sessions = (
                await observer.scalars(
                    select(AuthSessionModel).where(AuthSessionModel.username == "moderator")
                )
            ).all()
            assert sessions
            assert all(item.is_revoked for item in sessions)

    await request_at_response_start(
        auth_client,
        method="POST",
        path="/api/auth/admin/accounts/moderator/deactivate",
        headers=browser,
        observe=deactivation_visible,
    )
    auth_client.post(
        "/api/auth/admin/accounts/moderator/activate",
        headers=browser,
    ).raise_for_status()
    moderator_headers["Authorization"] = (
        "Bearer "
        + auth_client.post(
            "/api/auth/login",
            json={"username": "moderator", "password": PASSWORD},
        ).json()["accessToken"]
    )
    auth_client.post(BASE, json=token_payload(), headers=moderator_headers).raise_for_status()
    replacement = "test-replacement-password"

    async def password_visible(status: int) -> None:
        assert status == 200
        async with meta.sessionmaker() as observer:
            user = await observer.get(UserModel, "moderator")
            assert user is not None
            assert PasswordHasher().verify(user.password_hash, replacement)
            tokens = (
                await observer.scalars(
                    select(ApiTokenModel).where(ApiTokenModel.username == "moderator")
                )
            ).all()
            assert tokens
            assert all(token.revoked_at is not None for token in tokens)
            sessions = (
                await observer.scalars(
                    select(AuthSessionModel).where(AuthSessionModel.username == "moderator")
                )
            ).all()
            assert sessions
            assert all(item.is_revoked for item in sessions)

    await request_at_response_start(
        auth_client,
        method="PUT",
        path="/api/auth/admin/accounts/moderator/password",
        headers=browser,
        data={"password": replacement},
        observe=password_visible,
    )


@pytest.mark.parametrize("mutation", ["login", "create"])
async def test_commit_failure_never_emits_success_credentials(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    browser: dict[str, str] = {}
    if mutation == "create":
        login = auth_client.post(
            "/api/auth/login",
            json={"username": "owner", "password": PASSWORD},
        ).json()
        browser = {"Authorization": f"Bearer {login['accessToken']}", "X-CSRF-Guard": "1"}
    original_commit = AsyncSession.commit
    sentinel = "PRIVATE-DB-PARAMETER"
    commit_calls = 0

    async def fail_response_commit(db: AsyncSession) -> None:
        nonlocal commit_calls
        commit_calls += 1
        # The authenticated request first completes a separate read-only auth transaction.
        if commit_calls == (2 if mutation == "create" else 1):
            raise RuntimeError(sentinel)
        await original_commit(db)

    monkeypatch.setattr(AsyncSession, "commit", fail_response_commit)
    log = Mock()
    monkeypatch.setattr("infra.config.loggers.logger", log)

    async def rolled_back(status: int) -> None:
        assert status == 500
        async with meta.sessionmaker() as observer:
            assert await observer.scalar(select(func.count()).select_from(ApiTokenModel)) == 0
            count = await observer.scalar(select(func.count()).select_from(AuthSessionModel))
            assert count == (1 if mutation == "create" else 0)

    status, response, headers = await request_at_response_start(
        auth_client,
        method="POST",
        path=BASE if mutation == "create" else "/api/auth/login",
        headers=browser,
        data=token_payload()
        if mutation == "create"
        else {"username": "owner", "password": PASSWORD},
        observe=rolled_back,
    )
    assert status == 500
    assert response == {"message": "Internal server error"}
    assert (b"cache-control", b"no-store") in headers
    assert not any(key == b"set-cookie" for key, _ in headers)
    assert sentinel not in json.dumps(response)
    assert sentinel not in repr(log.error.call_args)
    log.error.assert_called_once_with(
        "database_transaction_completion_failed", exception_type="RuntimeError"
    )


@pytest.mark.parametrize("fail", [False, True])
async def test_response_finalizes_once_and_handled_errors_roll_back(
    auth_client: TestClient,
    fail: bool,
) -> None:
    events: list[str] = []

    async def committed() -> None:
        events.append("post_commit")

    async def rolled_back() -> None:
        events.append("rollback")

    @post("/api/auth/transaction-probe", exclude_from_auth=True, status_code=200)
    async def mutate(
        db: FromDishka[AsyncSession],
        post_commit_actions: FromDishka[PostCommitActions],
        rollback_actions: FromDishka[RollbackActions],
    ) -> dict[str, str]:
        await db.execute(
            update(UserModel).where(UserModel.username == "owner").values(is_active=False)
        )
        post_commit_actions.add(action=committed)
        rollback_actions.add(action=rolled_back)
        if fail:
            raise ForbiddenError
        return {"message": "updated"}

    auth_client.app.register(DishkaRouter("", route_handlers=[mutate]))

    async def observe(status: int) -> None:
        assert status == (403 if fail else 200)
        async with meta.sessionmaker() as observer:
            user = await observer.get(UserModel, "owner")
            assert user is not None
            assert user.is_active is fail
        assert events == (["rollback"] if fail else ["post_commit"])
        events.append("response.start")

    await request_at_response_start(
        auth_client,
        method="POST",
        path="/api/auth/transaction-probe",
        observe=observe,
    )
    assert events == (["rollback", "response.start"] if fail else ["post_commit", "response.start"])
