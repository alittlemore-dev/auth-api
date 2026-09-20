from dataclasses import dataclass
from functools import partial

from core.account.clients import AccountAvatarClient, AccountAvatarRollbackRegistrar
from infra.post_commit_actions import RollbackActions


@dataclass(frozen=True, slots=True, kw_only=True)
class RequestAccountAvatarRollbackRegistrar(AccountAvatarRollbackRegistrar):
    client: AccountAvatarClient
    rollback_actions: RollbackActions

    def register_new_object(self, *, object_name: str) -> None:
        self.rollback_actions.add(
            action=partial(self.client.delete, object_name=object_name),
        )
