from dataclasses import replace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio

from core.account.clients import (
    AccountAvatarClient,
    AccountAvatarProcessor,
    TelegramBotStatusClient,
)
from core.account.enums import AccountLanguageEnum, GenderEnum, TelegramBotId
from core.account.exceptions import TelegramBotUnavailableError
from core.account.schemas import AccountSettings, CurrentAccountUpdateParams, TelegramBotSettings
from core.account.storages import CurrentAccountStorage
from core.account.use_cases import CurrentAccountUseCase
from core.schemas import UNSET, Secret
from infra.post_commit_actions import RollbackActions
from tests.test_cases import TestCase


class TestCurrentAccountUseCase(TestCase):
    @pytest_asyncio.fixture(autouse=True, loop_scope="session")
    async def setup(self) -> None:
        self.storage = Mock(spec=CurrentAccountStorage)
        self.storage.get_current_account.return_value = self.factory.core.current_account()
        self.telegram_status = Mock(spec=TelegramBotStatusClient)
        self.use_case = CurrentAccountUseCase(
            storage=self.storage,
            avatar_client=Mock(spec=AccountAvatarClient),
            avatar_processor=Mock(spec=AccountAvatarProcessor),
            telegram_status_client=self.telegram_status,
            rollback_actions=RollbackActions(actions=[]),
        )

    async def test_gets_account_by_authenticated_username(self) -> None:
        expected = self.factory.core.current_account(username="Admin")
        self.storage.get_current_account.return_value = expected

        result = await self.use_case.get_account(username="Admin")

        assert result == expected
        self.storage.get_current_account.assert_called_once_with(username="Admin")

    async def test_omitted_time_zone_preserves_current_non_utc_zone(self) -> None:
        current = replace(
            self.factory.core.current_account(username="test"),
            settings=AccountSettings(time_zone=ZoneInfo("Asia/Yerevan")),
        )
        self.storage.get_current_account.return_value = current
        requested = AccountSettings(
            time_zone=ZoneInfo("UTC"),
            language=AccountLanguageEnum.RU,
        )
        expected = replace(requested, time_zone=ZoneInfo("Asia/Yerevan"))
        self.storage.update_settings.return_value = replace(current, settings=expected)

        result = await self.use_case.update_settings(
            username="test",
            settings=requested,
            preserve_existing_time_zone=True,
        )

        assert result.settings == expected
        self.storage.get_current_account.assert_called_once_with(username="test")
        self.storage.update_settings.assert_called_once_with(username="test", settings=expected)

    async def test_explicit_utc_replaces_current_zone(self) -> None:
        requested = AccountSettings(time_zone=ZoneInfo("UTC"))
        self.storage.update_settings.return_value = replace(
            self.factory.core.current_account(username="test"),
            settings=requested,
        )

        result = await self.use_case.update_settings(
            username="test",
            settings=requested,
            preserve_existing_time_zone=False,
        )

        assert result.settings.time_zone == ZoneInfo("UTC")
        self.storage.get_current_account.assert_called_once_with(username="test")
        self.storage.update_settings.assert_called_once_with(username="test", settings=requested)

    async def test_updates_only_explicit_fields_and_normalizes_names(self) -> None:
        expected = self.factory.core.current_account(
            first_name="Dmitriy",
            last_name=None,
            middle_name="Lunevich",
            gender=GenderEnum.MALE,
        )
        self.storage.update_current_account.return_value = expected

        result = await self.use_case.update_account(
            username="test",
            params=CurrentAccountUpdateParams(
                first_name=Secret("  Dmitriy  "),
                last_name=Secret("   "),
                middle_name=Secret(" Lunevich "),
                gender=Secret(GenderEnum.MALE),
            ),
        )

        assert result == expected
        self.storage.update_current_account.assert_called_once_with(
            username="test",
            params=CurrentAccountUpdateParams(
                first_name=Secret("Dmitriy"),
                last_name=None,
                middle_name=Secret("Lunevich"),
                gender=Secret(GenderEnum.MALE),
            ),
        )

    async def test_omitted_fields_are_not_changed(self) -> None:
        expected = self.factory.core.current_account(first_name="Dmitriy")
        self.storage.update_current_account.return_value = expected

        await self.use_case.update_account(
            username="test",
            params=CurrentAccountUpdateParams(
                first_name=Secret("Dmitriy"),
            ),
        )

        params = self.storage.update_current_account.call_args.kwargs["params"]
        assert params.first_name == Secret("Dmitriy")
        assert params.last_name is UNSET
        assert params.middle_name is UNSET
        assert params.gender is UNSET

    @pytest.mark.parametrize(
        ("current_bots", "requested_bots"),
        [
            ({}, {TelegramBotId.PERSONAL_WORKSPACE: TelegramBotSettings(enabled=True)}),
            ({TelegramBotId.PERSONAL_WORKSPACE: TelegramBotSettings(enabled=True)}, {}),
            (
                {TelegramBotId.PERSONAL_WORKSPACE: TelegramBotSettings(enabled=True)},
                {TelegramBotId.PERSONAL_WORKSPACE: TelegramBotSettings(enabled=True, notify=True)},
            ),
        ],
    )
    async def test_unready_bot_preference_changes_do_not_persist(
        self,
        current_bots: dict[TelegramBotId, TelegramBotSettings],
        requested_bots: dict[TelegramBotId, TelegramBotSettings],
    ) -> None:
        self.storage.get_current_account.return_value = replace(
            self.factory.core.current_account(),
            settings=AccountSettings(time_zone=ZoneInfo("UTC"), telegram_bots=current_bots),
        )
        self.telegram_status.is_ready.return_value = False

        with pytest.raises(TelegramBotUnavailableError):
            await self.use_case.update_settings(
                username="test",
                settings=AccountSettings(time_zone=ZoneInfo("UTC"), telegram_bots=requested_bots),
                preserve_existing_time_zone=False,
            )

        self.telegram_status.is_ready.assert_awaited_once_with()
        self.storage.update_settings.assert_not_awaited()

    async def test_unchanged_bot_preferences_save_during_outage(self) -> None:
        bots = {TelegramBotId.PERSONAL_WORKSPACE: TelegramBotSettings(enabled=True, notify=True)}
        self.storage.get_current_account.return_value = replace(
            self.factory.core.current_account(),
            settings=AccountSettings(time_zone=ZoneInfo("UTC"), telegram_bots=bots),
        )
        self.telegram_status.is_ready.return_value = False
        requested = AccountSettings(
            time_zone=ZoneInfo("Asia/Yerevan"),
            language=AccountLanguageEnum.RU,
            telegram_bots=bots,
        )

        await self.use_case.update_settings(
            username="test",
            settings=requested,
            preserve_existing_time_zone=False,
        )

        self.telegram_status.is_ready.assert_not_awaited()
        self.storage.update_settings.assert_awaited_once_with(username="test", settings=requested)

    async def test_ready_bot_preference_change_persists(self) -> None:
        self.telegram_status.is_ready.return_value = True
        requested = AccountSettings(
            time_zone=ZoneInfo("UTC"),
            telegram_bots={TelegramBotId.PERSONAL_WORKSPACE: TelegramBotSettings(enabled=True)},
        )

        await self.use_case.update_settings(
            username="test",
            settings=requested,
            preserve_existing_time_zone=False,
        )

        self.telegram_status.is_ready.assert_awaited_once_with()
        self.storage.update_settings.assert_awaited_once_with(username="test", settings=requested)
