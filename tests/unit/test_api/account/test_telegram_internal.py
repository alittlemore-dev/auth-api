import pytest
from litestar.testing import TestClient

from infra.config.settings import SecretStrExtended, settings


def test_internal_settings_rejects_requests_without_service_credential(
    no_auth_client: TestClient,
) -> None:
    response = no_auth_client.get(
        "/api/auth/internal/telegram/personal-workspace/settings",
        params={"ownerUsername": "anna"},
    )

    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"


def test_internal_settings_rejects_wrong_service_credential(no_auth_client: TestClient) -> None:
    response = no_auth_client.get(
        "/api/auth/internal/telegram/personal-workspace/settings",
        params={"ownerUsername": "anna"},
        headers={"X-Telegram-Service-Secret": "wrong"},
    )

    assert response.status_code == 403


def test_internal_settings_fails_closed_when_service_secret_is_unconfigured(
    no_auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings.telegram, "service_secret", SecretStrExtended(""))
    response = no_auth_client.get(
        "/api/auth/internal/telegram/personal-workspace/settings",
        params={"ownerUsername": "anna"},
    )

    assert response.status_code == 403


def test_internal_settings_rejects_unknown_bot_id(
    no_auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings.telegram, "service_secret", SecretStrExtended("test-secret"))
    response = no_auth_client.get(
        "/api/auth/internal/telegram/unknown-bot/settings",
        params={"ownerUsername": "anna"},
        headers={"X-Telegram-Service-Secret": "test-secret"},
    )

    assert response.status_code == 400
    assert response.headers["cache-control"] == "no-store"


def test_unauthenticated_user_cannot_manage_telegram_settings(
    no_auth_client: TestClient,
) -> None:
    response = no_auth_client.put(
        "/api/auth/account/me/settings",
        json={"telegramBots": {"personal-workspace": {"enabled": True}}},
    )

    assert response.status_code in (401, 403)
