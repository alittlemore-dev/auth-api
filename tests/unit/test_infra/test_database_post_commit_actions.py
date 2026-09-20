from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.account.clients import AccountAvatarClient
from core.account.exceptions import AccountAvatarStorageError
from entrypoints.litestar.api.account import post_commit as account_post_commit
from entrypoints.litestar.api.account.post_commit import register_account_avatar_cleanup
from infra.account_avatar_actions import RequestAccountAvatarRollbackRegistrar
from infra.ioc.prodivers.database_provider import DatabaseProvider
from infra.post_commit_actions import PostCommitActions, RollbackActions
from infra.postgresql import meta
from infra.postgresql.transactions import DatabaseTransactionState


class SessionContextManager:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *_args: object) -> None:
        return None


class SessionFactory:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    def __call__(self) -> SessionContextManager:
        return SessionContextManager(session=self.session)


class TestDatabasePostCommitActions:
    async def test_avatar_upload_is_deleted_when_commit_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = AsyncMock(spec=AsyncSession)
        session.commit.side_effect = RuntimeError("commit failed")
        session_factory = cast(
            "async_sessionmaker[AsyncSession]",
            SessionFactory(session=session),
        )
        monkeypatch.setattr(meta, "sessionmaker", session_factory)
        client = Mock(spec=AccountAvatarClient)
        registrar = RequestAccountAvatarRollbackRegistrar(
            client=client,
            rollback_actions=RollbackActions(actions=[]),
        )
        registrar.register_new_object(object_name="avatars/new-private-name.webp")
        provider = DatabaseProvider()
        generator = provider.provide_async_session(
            transaction_state=DatabaseTransactionState(rollback_required=False),
            post_commit_actions=PostCommitActions(actions=[]),
            rollback_actions=registrar.rollback_actions,
        )

        assert await anext(generator) is session
        with pytest.raises(RuntimeError, match="commit failed"):
            await generator.asend(None)

        client.delete.assert_awaited_once_with(object_name="avatars/new-private-name.webp")

    async def test_failed_post_commit_avatar_delete_is_sanitized_and_suppressed(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        client = Mock(spec=AccountAvatarClient)
        client.delete.side_effect = AccountAvatarStorageError
        logger = Mock()
        monkeypatch.setattr(account_post_commit, "log_sanitized_exception", logger)
        actions = PostCommitActions(actions=[])
        register_account_avatar_cleanup(
            old_object_name="avatars/old-private-name.webp",
            client=client,
            post_commit_actions=actions,
        )

        await actions.run()

        logger.assert_called_once()
        logged = repr(logger.call_args)
        assert "old-private-name" not in logged
        assert logger.call_args.kwargs["failed_count"] == 1

    async def test_runs_actions_after_successful_commit(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        events: list[str] = []
        session = AsyncMock(spec=AsyncSession)
        session.commit.side_effect = lambda: events.append("commit")
        session_factory = cast(
            "async_sessionmaker[AsyncSession]",
            SessionFactory(session=session),
        )
        monkeypatch.setattr(meta, "sessionmaker", session_factory)
        action = AsyncMock(side_effect=lambda: events.append("post_commit"))
        rollback_action = AsyncMock()
        post_commit_actions = PostCommitActions(actions=[action])
        provider = DatabaseProvider()
        generator = provider.provide_async_session(
            transaction_state=DatabaseTransactionState(rollback_required=False),
            post_commit_actions=post_commit_actions,
            rollback_actions=RollbackActions(actions=[rollback_action]),
        )

        assert await anext(generator) is session
        with pytest.raises(StopAsyncIteration):
            await generator.asend(None)

        assert events == ["commit", "post_commit"]
        action.assert_awaited_once_with()
        rollback_action.assert_not_awaited()

    async def test_skips_actions_after_rollback(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = AsyncMock(spec=AsyncSession)
        session_factory = cast(
            "async_sessionmaker[AsyncSession]",
            SessionFactory(session=session),
        )
        monkeypatch.setattr(meta, "sessionmaker", session_factory)
        action = AsyncMock()
        provider = DatabaseProvider()
        generator = provider.provide_async_session(
            transaction_state=DatabaseTransactionState(rollback_required=True),
            post_commit_actions=PostCommitActions(actions=[action]),
            rollback_actions=RollbackActions(actions=[]),
        )

        assert await anext(generator) is session
        with pytest.raises(StopAsyncIteration):
            await generator.asend(None)

        session.rollback.assert_awaited_once_with()
        session.commit.assert_not_awaited()
        action.assert_not_awaited()

    async def test_skips_actions_when_commit_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        error_message = "commit failed"
        session = AsyncMock(spec=AsyncSession)
        session.commit.side_effect = RuntimeError(error_message)
        session_factory = cast(
            "async_sessionmaker[AsyncSession]",
            SessionFactory(session=session),
        )
        monkeypatch.setattr(meta, "sessionmaker", session_factory)
        action = AsyncMock()
        provider = DatabaseProvider()
        generator = provider.provide_async_session(
            transaction_state=DatabaseTransactionState(rollback_required=False),
            post_commit_actions=PostCommitActions(actions=[action]),
            rollback_actions=RollbackActions(actions=[]),
        )

        assert await anext(generator) is session
        with pytest.raises(RuntimeError, match=error_message):
            await generator.asend(None)

        action.assert_not_awaited()

    @pytest.mark.parametrize("rollback_required", [False, True])
    async def test_runs_rollback_actions_for_request_failure_or_marked_rollback(
        self,
        monkeypatch: pytest.MonkeyPatch,
        rollback_required: bool,
    ) -> None:
        session = AsyncMock(spec=AsyncSession)
        session_factory = cast(
            "async_sessionmaker[AsyncSession]",
            SessionFactory(session=session),
        )
        monkeypatch.setattr(meta, "sessionmaker", session_factory)
        action = AsyncMock()
        provider = DatabaseProvider()
        generator = provider.provide_async_session(
            transaction_state=DatabaseTransactionState(
                rollback_required=rollback_required,
            ),
            post_commit_actions=PostCommitActions(actions=[]),
            rollback_actions=RollbackActions(actions=[action]),
        )

        assert await anext(generator) is session
        sent_value = None if rollback_required else RuntimeError("request failed")
        with pytest.raises(StopAsyncIteration):
            await generator.asend(sent_value)

        session.rollback.assert_awaited_once_with()
        action.assert_awaited_once_with()

    async def test_runs_rollback_actions_when_commit_fails_and_preserves_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        error_message = "commit failed"
        session = AsyncMock(spec=AsyncSession)
        session.commit.side_effect = RuntimeError(error_message)
        session_factory = cast(
            "async_sessionmaker[AsyncSession]",
            SessionFactory(session=session),
        )
        monkeypatch.setattr(meta, "sessionmaker", session_factory)
        action = AsyncMock()
        provider = DatabaseProvider()
        generator = provider.provide_async_session(
            transaction_state=DatabaseTransactionState(rollback_required=False),
            post_commit_actions=PostCommitActions(actions=[]),
            rollback_actions=RollbackActions(actions=[action]),
        )

        assert await anext(generator) is session
        with pytest.raises(RuntimeError, match=error_message):
            await generator.asend(None)

        session.rollback.assert_awaited_once_with()
        action.assert_awaited_once_with()
