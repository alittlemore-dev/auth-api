from functools import partial

from core.account.clients import AccountAvatarClient
from infra.config.loggers import log_sanitized_exception
from infra.post_commit_actions import PostCommitActions


def register_account_avatar_cleanup(
    *,
    old_object_name: str | None,
    client: AccountAvatarClient,
    post_commit_actions: PostCommitActions,
) -> None:
    if old_object_name is None:
        return
    post_commit_actions.add(
        action=partial(
            _delete_old_avatar,
            object_name=old_object_name,
            client=client,
        ),
    )


async def _delete_old_avatar(*, object_name: str, client: AccountAvatarClient) -> None:
    try:
        await client.delete(object_name=object_name)
    except Exception as error:  # noqa: BLE001
        log_sanitized_exception(
            event="Post-commit account avatar cleanup failed",
            error=error,
            failed_count=1,
        )
