from typing import Protocol

from dishka import AsyncContainer
from dishka.integrations import taskiq as dishka_taskiq
from dishka.integrations.base import is_dishka_injected
from taskiq_redis import RedisAsyncResultBackend

from entrypoints.taskiq import broker as taskiq_broker_module
from entrypoints.taskiq import worker as taskiq_worker_module
from entrypoints.taskiq.account import tasks as account_tasks_module
from entrypoints.taskiq.auth import tasks as auth_tasks_module
from infra.config.constants import constants
from infra.config.settings import settings


class InjectedTaskCallable(Protocol):
    async def __call__(self, *, dishka_container: AsyncContainer) -> dict[str, int]: ...


class TestTaskiqBrokerConfiguration:
    def test_taskiq_uses_dedicated_valkey_databases(self) -> None:
        result_backend = taskiq_broker_module.broker.result_backend

        assert constants.valkey.databases.taskiq_broker == 3
        assert constants.valkey.databases.taskiq_results == 4
        assert (
            taskiq_broker_module.broker.connection_pool.connection_kwargs["db"]
            == constants.valkey.databases.taskiq_broker
        )
        assert isinstance(result_backend, RedisAsyncResultBackend)
        assert (
            result_backend.redis_pool.connection_kwargs["db"]
            == constants.valkey.databases.taskiq_results
        )

    def test_result_backend_uses_explicit_expiration_and_prefix(self) -> None:
        result_backend = taskiq_broker_module.broker.result_backend

        assert isinstance(result_backend, RedisAsyncResultBackend)
        assert result_backend.keep_results is True
        assert result_backend.result_ex_time == settings.taskiq.result_expire_seconds
        assert result_backend.prefix_str == constants.taskiq.result_prefix

    def test_broker_uses_expected_queue_and_consumer_group(self) -> None:
        assert taskiq_broker_module.broker.queue_name == constants.taskiq.queue_name
        assert (
            taskiq_broker_module.broker.consumer_group_name == constants.taskiq.consumer_group_name
        )
        assert taskiq_broker_module.broker.result_backend is not None


class TestTaskiqScheduleConfiguration:
    def test_account_avatar_orphan_prune_uses_daily_interval(self) -> None:
        schedule = account_tasks_module.prune_account_avatar_orphans.labels["schedule"]

        assert schedule == [
            {
                "schedule_id": "account_avatar_orphan_prune",
                "interval": settings.taskiq.account_avatar_orphan_prune_interval_seconds,
            },
        ]
        assert "cron" not in schedule[0]

    def test_auth_session_prune_uses_interval_schedule_without_cron(self) -> None:
        schedule = auth_tasks_module.prune_expired_auth_sessions.labels["schedule"]

        assert schedule == [
            {
                "schedule_id": "auth_session_prune",
                "interval": settings.taskiq.auth_session_prune_interval_seconds,
            },
        ]
        assert "cron" not in schedule[0]

    def test_tasks_use_dishka_taskiq_middleware(self) -> None:
        assert any(
            isinstance(middleware, dishka_taskiq.ContainerMiddleware)
            for middleware in taskiq_broker_module.broker.middlewares
        )
        assert is_dishka_injected(auth_tasks_module.prune_expired_auth_sessions.original_func)
        assert is_dishka_injected(account_tasks_module.prune_account_avatar_orphans.original_func)

    def test_worker_module_is_the_taskiq_registry_entrypoint(self) -> None:
        assert taskiq_worker_module.broker is taskiq_broker_module.broker
        assert taskiq_worker_module.scheduler.broker is taskiq_broker_module.broker

        assert (
            taskiq_worker_module.broker.find_task(constants.taskiq.auth_session_prune_task_name)
            is auth_tasks_module.prune_expired_auth_sessions
        )
        assert (
            taskiq_worker_module.broker.find_task(
                constants.taskiq.account_avatar_orphan_prune_task_name
            )
            is account_tasks_module.prune_account_avatar_orphans
        )
