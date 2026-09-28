from dataclasses import replace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest_asyncio

from core.account.clients import (
    AccountAvatarClient,
    AccountAvatarProcessor,
)
from core.account.enums import AccountLanguageEnum, GenderEnum
from core.account.schemas import AccountSettings, CurrentAccountUpdateParams
from core.account.storages import CurrentAccountStorage
from core.account.use_cases import CurrentAccountUseCase
from core.schemas import UNSET, Secret
from infra.post_commit_actions import RollbackActions
from tests.test_cases import TestCase


class TestCurrentAccountUseCase(TestCase):
    @pytest_asyncio.fixture(autouse=True, loop_scope="session")
    async def setup(self) -> None:
        self.storage = Mock(spec=CurrentAccountStorage)
        self.use_case = CurrentAccountUseCase(
            storage=self.storage,
            avatar_client=Mock(spec=AccountAvatarClient),
            avatar_processor=Mock(spec=AccountAvatarProcessor),
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

    async def test_explicit_utc_replaces_current_zone_without_preliminary_read(self) -> None:
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
        self.storage.get_current_account.assert_not_called()
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
