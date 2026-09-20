from datetime import datetime

from dishka.integrations.taskiq import FromDishka, inject

from core.account.use_cases import AvatarOrphanCleanupUseCase
from entrypoints.taskiq.broker import broker
from infra.config.constants import constants
from infra.config.settings import settings


@broker.task(
    constants.taskiq.account_avatar_orphan_prune_task_name,
    schedule=[
        {
            "schedule_id": constants.taskiq.account_avatar_orphan_prune_task_name,
            "interval": settings.taskiq.account_avatar_orphan_prune_interval_seconds,
        },
    ],
)
@inject(patch_module=True)
async def prune_account_avatar_orphans(
    use_case: FromDishka[AvatarOrphanCleanupUseCase],
    current_datetime: FromDishka[datetime],
) -> dict[str, int]:
    return (await use_case.prune(current_datetime=current_datetime)).as_dict()
