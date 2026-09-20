from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from core.account.clients import (
    RollbackAction,
)
from core.account.clients import (
    RollbackActions as AbstractRollbackActions,
)

type PostCommitAction = Callable[[], Awaitable[None]]


@dataclass(kw_only=True, slots=True)
class PostCommitActions:
    actions: list[PostCommitAction]

    def add(self, *, action: PostCommitAction) -> None:
        self.actions.append(action)

    async def run(self) -> None:
        for action in self.actions:
            await action()


@dataclass(kw_only=True, slots=True)
class RollbackActions(AbstractRollbackActions):
    actions: list[RollbackAction]

    def add(self, *, action: RollbackAction) -> None:
        self.actions.append(action)

    async def run(self) -> None:
        for action in self.actions:
            await action()
