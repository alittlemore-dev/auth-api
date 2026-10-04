from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from infra.post_commit_actions import PostCommitActions, RollbackActions
from infra.postgresql import meta
from infra.postgresql.transactions import DatabaseTransactionState


class DatabaseProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_transaction_state(self) -> DatabaseTransactionState:
        return DatabaseTransactionState(rollback_required=False)

    @provide(scope=Scope.REQUEST)
    def provide_post_commit_actions(self) -> PostCommitActions:
        return PostCommitActions(actions=[])

    @provide(scope=Scope.REQUEST)
    def provide_rollback_actions(self) -> RollbackActions:
        return RollbackActions(actions=[])

    @provide(scope=Scope.REQUEST)
    async def provide_async_session(
        self,
        transaction_state: DatabaseTransactionState,
        post_commit_actions: PostCommitActions,
        rollback_actions: RollbackActions,
    ) -> AsyncGenerator[AsyncSession, BaseException | None]:
        async with meta.sessionmaker() as session:
            transaction_state.attach(
                session=session,
                post_commit_actions=post_commit_actions,
                rollback_actions=rollback_actions,
            )
            request_exception = yield session
            await transaction_state.finish(request_exception=request_exception)
