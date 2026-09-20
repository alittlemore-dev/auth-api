from abc import ABC, abstractmethod

from core.account.schemas import (
    AccountSettings,
    CurrentAccount,
    CurrentAccountUpdateParams,
    ManagedAccount,
    ManagedAccountFilters,
)
from core.auth.enums import RoleEnum
from core.auth.schemas import User


class GetUserByUsernameStorage(ABC):
    @abstractmethod
    async def get_user_by_username(self, username: str) -> User:
        raise NotImplementedError


class UserAccountStorage(GetUserByUsernameStorage, ABC):
    pass


class CurrentAccountStorage(ABC):
    @abstractmethod
    async def get_current_account(self, *, username: str) -> CurrentAccount:
        raise NotImplementedError

    @abstractmethod
    async def update_current_account(
        self,
        *,
        username: str,
        params: CurrentAccountUpdateParams,
    ) -> CurrentAccount:
        raise NotImplementedError

    @abstractmethod
    async def update_settings(self, *, username: str, settings: AccountSettings) -> CurrentAccount:
        raise NotImplementedError

    @abstractmethod
    async def update_avatar_object_name(
        self,
        *,
        username: str,
        object_name: str | None,
    ) -> CurrentAccount:
        raise NotImplementedError

    @abstractmethod
    async def list_avatar_object_names(self) -> frozenset[str]:
        raise NotImplementedError


class ManagedAccountStorage(UserAccountStorage, ABC):
    @abstractmethod
    async def list_managed_accounts(
        self,
        *,
        filters: ManagedAccountFilters,
    ) -> tuple[list[ManagedAccount], int]:
        raise NotImplementedError

    @abstractmethod
    async def get_managed_account(self, *, username: str) -> ManagedAccount:
        raise NotImplementedError

    @abstractmethod
    async def create_managed_account(
        self,
        *,
        username: str,
        role: RoleEnum,
        password_hash: str,
        is_active: bool,
    ) -> ManagedAccount:
        raise NotImplementedError

    @abstractmethod
    async def update_managed_account_role(
        self,
        *,
        username: str,
        role: RoleEnum,
    ) -> ManagedAccount:
        raise NotImplementedError

    @abstractmethod
    async def update_managed_account_password(
        self,
        *,
        username: str,
        password_hash: str,
    ) -> ManagedAccount:
        raise NotImplementedError

    @abstractmethod
    async def activate_managed_account(self, *, username: str) -> ManagedAccount:
        raise NotImplementedError

    @abstractmethod
    async def deactivate_managed_account(self, *, username: str) -> ManagedAccount:
        raise NotImplementedError

    @abstractmethod
    async def delete_managed_account(self, *, username: str) -> None:
        raise NotImplementedError
