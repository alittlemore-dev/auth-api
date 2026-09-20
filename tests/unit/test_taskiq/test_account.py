from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import Mock

from core.account.avatar_schemas import AvatarOrphanCleanupResult
from core.account.use_cases import AvatarOrphanCleanupUseCase
from entrypoints.taskiq.account import tasks as account_tasks_module


async def test_account_avatar_orphan_prune_returns_count_only_json() -> None:
    current_datetime = datetime(2026, 9, 20, 12, tzinfo=UTC)
    use_case = Mock(spec=AvatarOrphanCleanupUseCase)
    use_case.prune.return_value = AvatarOrphanCleanupResult(
        scanned_count=8,
        referenced_count=5,
        deleted_count=2,
        failed_count=1,
    )

    injected_func = cast("Any", account_tasks_module.prune_account_avatar_orphans.original_func)
    result = await injected_func.__dishka_orig_func__(
        use_case=use_case,
        current_datetime=current_datetime,
    )

    use_case.prune.assert_awaited_once_with(current_datetime=current_datetime)
    assert result == {
        "scannedCount": 8,
        "referencedCount": 5,
        "deletedCount": 2,
        "failedCount": 1,
    }
    assert "object" not in repr(result).lower()
