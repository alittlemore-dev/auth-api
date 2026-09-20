from unittest.mock import Mock

import pytest_asyncio

from core.account.clients import AccountAvatarClient, AccountAvatarProcessor
from core.account.enums import GenderEnum
from core.account.schemas import CurrentAccountUpdateParams
from core.account.storages import CurrentAccountStorage
from core.account.use_cases import CurrentAccountUseCase
from core.generators import HexUuidIdGenerator
from core.schemas import UNSET, Secret
from tests.test_cases import TestCase


class TestCurrentAccountUseCase(TestCase):
    @pytest_asyncio.fixture(autouse=True, loop_scope="session")
    async def setup(self) -> None:
        self.storage = Mock(spec=CurrentAccountStorage)
        self.use_case = CurrentAccountUseCase(
            storage=self.storage,
            avatar_client=Mock(spec=AccountAvatarClient),
            avatar_processor=Mock(spec=AccountAvatarProcessor),
            id_generator=HexUuidIdGenerator(generator=lambda: "a" * 32),
        )

    async def test_gets_account_by_authenticated_username(self) -> None:
        expected = self.factory.core.current_account(username="Admin")
        self.storage.get_current_account.return_value = expected

        result = await self.use_case.get_account(username="Admin")

        assert result == expected
        self.storage.get_current_account.assert_called_once_with(username="Admin")

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
