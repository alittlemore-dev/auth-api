from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from core.account.avatar_schemas import (
    AccountAvatarUpload,
    CurrentAccountAvatarMutationResult,
    ProcessedAccountAvatar,
)
from core.account.clients import (
    AccountAvatarClient,
    AccountAvatarProcessor,
    AccountAvatarRollbackRegistrar,
)
from core.account.exceptions import AccountAvatarNotFoundError
from core.account.storages import CurrentAccountStorage
from core.account.use_cases import CurrentAccountUseCase
from core.generators import HexUuidIdGenerator
from tests.test_cases import TestCase


class TestCurrentAccountAvatarUseCase(TestCase):
    @pytest_asyncio.fixture(autouse=True, loop_scope="session")
    async def setup(self) -> None:
        self.events: list[str] = []
        self.storage = Mock(spec=CurrentAccountStorage)
        self.client = Mock(spec=AccountAvatarClient)
        self.processor = Mock(spec=AccountAvatarProcessor)
        self.rollback_registrar = Mock(spec=AccountAvatarRollbackRegistrar)
        self.id_generator = HexUuidIdGenerator(generator=lambda: "a" * 32)
        self.use_case = CurrentAccountUseCase(
            storage=self.storage,
            avatar_client=self.client,
            avatar_processor=self.processor,
            id_generator=self.id_generator,
        )

    async def test_replaces_avatar_transactionally(self) -> None:
        old_account = self.factory.core.current_account(avatar_object_name="avatars/old.webp")
        new_account = self.factory.core.current_account(
            avatar_object_name=f"avatars/{'a' * 32}.webp"
        )
        self.storage.get_current_account.return_value = old_account
        self.processor.process.return_value = ProcessedAccountAvatar(content=b"processed")
        self.client.upload = AsyncMock(side_effect=lambda **_kwargs: self.events.append("upload"))
        self.rollback_registrar.register_new_object.side_effect = lambda **_kwargs: (
            self.events.append("rollback_registered")
        )

        def update_avatar(**_kwargs: object) -> object:
            self.events.append("row_updated")
            return new_account

        self.storage.update_avatar_object_name.side_effect = update_avatar

        result = await self.use_case.replace_avatar(
            username="test",
            upload=AccountAvatarUpload(content=b"source", declared_mime_type="image/png"),
            rollback_registrar=self.rollback_registrar,
        )

        object_name = f"avatars/{'a' * 32}.webp"
        assert result == CurrentAccountAvatarMutationResult(
            account=new_account,
            old_object_name="avatars/old.webp",
        )
        assert self.events == ["upload", "rollback_registered", "row_updated"]
        self.client.upload.assert_awaited_once_with(
            object_name=object_name,
            content=b"processed",
        )
        self.rollback_registrar.register_new_object.assert_called_once_with(
            object_name=object_name,
        )
        self.storage.update_avatar_object_name.assert_awaited_once_with(
            username="test",
            object_name=object_name,
        )

    async def test_remove_avatar_is_idempotent(self) -> None:
        account = self.factory.core.current_account(avatar_object_name=None)
        self.storage.get_current_account.return_value = account

        result = await self.use_case.remove_avatar(username="test")

        assert result == CurrentAccountAvatarMutationResult(
            account=account,
            old_object_name=None,
        )
        self.storage.update_avatar_object_name.assert_not_awaited()

    async def test_removes_avatar_from_row_before_post_commit_cleanup(self) -> None:
        old_account = self.factory.core.current_account(avatar_object_name="avatars/old.webp")
        updated = self.factory.core.current_account(avatar_object_name=None)
        self.storage.get_current_account.return_value = old_account
        self.storage.update_avatar_object_name.return_value = updated

        result = await self.use_case.remove_avatar(username="test")

        assert result == CurrentAccountAvatarMutationResult(
            account=updated,
            old_object_name="avatars/old.webp",
        )

    async def test_get_avatar_stream_is_scoped_to_current_username(self) -> None:
        account = self.factory.core.current_account(avatar_object_name="avatars/current.webp")
        self.storage.get_current_account.return_value = account

        result = await self.use_case.get_avatar(username="test")

        self.storage.get_current_account.assert_awaited_once_with(username="test")
        self.client.stream.assert_called_once_with(object_name="avatars/current.webp")
        assert result.content is self.client.stream.return_value

    async def test_get_avatar_raises_not_found_when_absent(self) -> None:
        self.storage.get_current_account.return_value = self.factory.core.current_account()

        with pytest.raises(AccountAvatarNotFoundError):
            await self.use_case.get_avatar(username="test")
