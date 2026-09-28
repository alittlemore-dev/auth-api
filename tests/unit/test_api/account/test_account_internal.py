from dataclasses import replace
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio

from core.account.enums import AccountLanguageEnum, AccountThemeEnum, TelegramBotId
from core.account.schemas import AccountSettings, TelegramBotSettings
from core.auth.exceptions import UserNotFoundError
from infra.config.settings import SecretStrExtended, settings
from tests.test_cases import ApiTestCase


class TestAccountInternalAPI(ApiTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.use_case = await self.container.get_current_account_use_case()
        monkeypatch.setattr(settings.telegram, "service_secret", SecretStrExtended("test-secret"))
        monkeypatch.setattr(settings.telegram, "available", False)

    def test_reads_full_account_settings_when_telegram_is_unavailable(self) -> None:
        self.use_case.get_account.return_value = replace(
            self.factory.core.current_account(),
            settings=AccountSettings(
                language=AccountLanguageEnum.RU,
                theme=AccountThemeEnum.DARK,
                time_zone=ZoneInfo("Asia/Yerevan"),
                telegram_bots={
                    TelegramBotId.PERSONAL_WORKSPACE: TelegramBotSettings(
                        enabled=True,
                        notify=True,
                    ),
                },
            ),
        )

        response = self.api.client.get(
            "/api/auth/internal/account/anna/settings",
            headers={"X-Internal-Service-Secret": "test-secret"},
        )

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "language": "ru",
            "theme": "dark",
            "timeZone": "Asia/Yerevan",
            "telegramBots": {"personal-workspace": {"enabled": True, "notify": True}},
        }
        self.use_case.get_account.assert_called_once_with(username="anna")

    def test_returns_not_found_for_missing_account(self) -> None:
        self.use_case.get_account.side_effect = UserNotFoundError

        response = self.api.client.get(
            "/api/auth/internal/account/missing/settings",
            headers={"X-Internal-Service-Secret": "test-secret"},
        )

        assert response.status_code == 404
        assert response.headers["cache-control"] == "no-store"

    @pytest.mark.parametrize("header", [{}, {"X-Internal-Service-Secret": "incorrect"}])
    def test_rejects_requests_without_service_secret(self, header: dict[str, str]) -> None:
        response = self.api.client.get(
            "/api/auth/internal/account/anna/settings",
            headers=header,
        )

        assert response.status_code == 403
        self.use_case.get_account.assert_not_called()

    def test_fails_closed_without_configured_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings.telegram, "service_secret", SecretStrExtended(""))

        response = self.api.client.get(
            "/api/auth/internal/account/anna/settings",
            headers={"X-Internal-Service-Secret": "test-secret"},
        )

        assert response.status_code == 403
        self.use_case.get_account.assert_not_called()
