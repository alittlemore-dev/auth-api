from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime

from core.account.avatar_schemas import AccountAvatarUpload, ProcessedAccountAvatar


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


class AccountAvatarRollbackRegistrar(ABC):
    @abstractmethod
    def register_new_object(self, *, object_name: str) -> None:
        raise NotImplementedError
