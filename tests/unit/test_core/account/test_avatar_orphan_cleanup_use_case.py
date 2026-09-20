from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, call

from core.account.avatar_schemas import (
    AvatarOrphanCleanupResult,
    AvatarOrphanCleanupUseCaseConfig,
)
from core.account.clients import AccountAvatarClient
from core.account.exceptions import AccountAvatarStorageError
from core.account.storages import CurrentAccountStorage
from core.account.use_cases import AvatarOrphanCleanupUseCase
from tests.test_cases import TestCase


class TestAvatarOrphanCleanupUseCase(TestCase):
    async def test_prunes_only_old_unreferenced_objects_and_reports_counts(self) -> None:
        now = datetime(2026, 9, 20, 12, tzinfo=UTC)
        storage = Mock(spec=CurrentAccountStorage)
        client = Mock(spec=AccountAvatarClient)
        storage.list_avatar_object_names.return_value = frozenset(
            {"avatars/referenced.webp", "avatars/current-but-new.webp"}
        )
        client.list_objects_older_than.return_value = (
            "avatars/referenced.webp",
            "avatars/orphan-1.webp",
            "avatars/orphan-2.webp",
        )
        client.delete.side_effect = [None, AccountAvatarStorageError]
        use_case = AvatarOrphanCleanupUseCase(
            storage=storage,
            client=client,
            config=AvatarOrphanCleanupUseCaseConfig(retention_seconds=6 * 60 * 60),
        )

        result = await use_case.prune(current_datetime=now)

        client.list_objects_older_than.assert_awaited_once_with(
            cutoff=now - timedelta(hours=6),
        )
        assert client.delete.await_args_list == [
            call(object_name="avatars/orphan-1.webp"),
            call(object_name="avatars/orphan-2.webp"),
        ]
        assert result == AvatarOrphanCleanupResult(
            scanned_count=3,
            referenced_count=1,
            deleted_count=1,
            failed_count=1,
        )
        assert result.as_dict() == {
            "scannedCount": 3,
            "referencedCount": 1,
            "deletedCount": 1,
            "failedCount": 1,
        }
