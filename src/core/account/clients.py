from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime

from core.account.avatar_schemas import AccountAvatarUpload, ProcessedAccountAvatar

type RollbackAction = Callable[[], Awaitable[None]]


class AccountAvatarProcessor(ABC):
    @abstractmethod
    def process(self, *, upload: AccountAvatarUpload) -> ProcessedAccountAvatar:
        raise NotImplementedError


class AccountAvatarClient(ABC):
    @abstractmethod
    async def upload(self, *, object_name: str, content: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    def stream(self, *, object_name: str) -> AsyncIterator[bytes]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, *, object_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_objects_older_than(self, *, cutoff: datetime) -> tuple[str, ...]:
        raise NotImplementedError


class RollbackActions(ABC):
    @abstractmethod
    def add(self, *, action: RollbackAction) -> None:
        raise NotImplementedError
