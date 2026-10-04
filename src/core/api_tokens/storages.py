from abc import ABC, abstractmethod
from datetime import datetime

from core.api_tokens.schemas import ApiToken
from core.auth.schemas import User


class ApiTokenStorage(ABC):
    @abstractmethod
    async def get_user(self, *, username: str, lock: bool = False) -> User:
        raise NotImplementedError

    @abstractmethod
    async def create_token(self, *, token: ApiToken) -> ApiToken:
        raise NotImplementedError

    @abstractmethod
    async def list_tokens(self, *, username: str) -> list[ApiToken]:
        raise NotImplementedError

    @abstractmethod
    async def get_token(self, *, token_id: str, username: str) -> ApiToken:
        raise NotImplementedError

    @abstractmethod
    async def get_token_by_hash(self, *, secret_hash: str) -> ApiToken:
        raise NotImplementedError

    @abstractmethod
    async def touch_token(self, *, token_id: str, now: datetime) -> None:
        raise NotImplementedError

    @abstractmethod
    async def revoke_token(self, *, token_id: str, username: str, now: datetime) -> ApiToken:
        raise NotImplementedError

    @abstractmethod
    async def revoke_user_tokens(self, *, username: str, now: datetime) -> None:
        raise NotImplementedError
