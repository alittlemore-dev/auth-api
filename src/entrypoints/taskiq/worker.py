from dishka.integrations.taskiq import setup_dishka
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from entrypoints.taskiq.auth import tasks as auth_tasks  # noqa: F401
from entrypoints.taskiq.broker import broker
from infra.ioc.container import container

setup_dishka(container=container, broker=broker)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

__all__ = ["broker", "scheduler"]
