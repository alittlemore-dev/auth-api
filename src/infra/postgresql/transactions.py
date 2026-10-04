from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infra.post_commit_actions import PostCommitActions, RollbackActions


@dataclass(slots=True, kw_only=True)
class DatabaseTransactionState:
    rollback_required: bool
    session: AsyncSession | None = None
    post_commit_actions: PostCommitActions | None = None
    rollback_actions: RollbackActions | None = None
    finished: bool = False

    def attach(
        self,
        *,
        session: AsyncSession,
        post_commit_actions: PostCommitActions,
        rollback_actions: RollbackActions,
    ) -> None:
        self.session = session
        self.post_commit_actions = post_commit_actions
        self.rollback_actions = rollback_actions

    async def finish(self, *, request_exception: BaseException | None = None) -> None:
        if self.finished or self.session is None:
            return
        self.finished = True
        if request_exception is not None or self.rollback_required:
            await self.rollback()
            return
        try:
            await self.session.commit()
        except BaseException:
            await self.rollback()
            raise
        if self.post_commit_actions is not None:
            await self.post_commit_actions.run()

    async def rollback(self) -> None:
        try:
            if self.session is not None:
                await self.session.rollback()
        finally:
            if self.rollback_actions is not None:
                await self.rollback_actions.run()
