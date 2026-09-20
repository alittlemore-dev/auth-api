import uuid
from dataclasses import dataclass
from typing import cast
from unittest.mock import Mock

from dishka import AsyncContainer

from core.account.storages import UserAccountStorage
from core.account.use_cases import AccountsUseCase, CurrentAccountUseCase
from core.auth.password_hashers import PasswordHasher
from core.auth.storages import AuthSessionStorage, AuthStorage
from core.auth.token_handlers import TokenHandler
from core.auth.use_cases import AuthSessionCleanupUseCase, AuthUseCase
from core.types import IntId
from infra.healthcheck import ReadinessChecker


@dataclass(kw_only=True)
class IocContainerHelper:
    container: AsyncContainer

    # COMMON
    async def get_random_uuid(self) -> uuid.UUID:
        return await self.container.get(uuid.UUID)

    async def get_random_int(self) -> IntId:
        return await self.container.get(IntId)

    async def get_hasher(self) -> Mock:
        hasher = await self.container.get(PasswordHasher)
        return cast("Mock", hasher)

    async def get_token_handler(self) -> Mock:
        handler = await self.container.get(TokenHandler)
        return cast("Mock", handler)

    async def get_auth_storage(self) -> Mock:
        storage = await self.container.get(AuthStorage)
        return cast("Mock", storage)

    async def get_auth_session_storage(self) -> Mock:
        storage = await self.container.get(AuthSessionStorage)
        return cast("Mock", storage)

    async def get_auth_use_case(self) -> Mock:
        use_case = await self.container.get(AuthUseCase)
        return cast("Mock", use_case)

    async def get_auth_session_cleanup_use_case(self) -> Mock:
        use_case = await self.container.get(AuthSessionCleanupUseCase)
        return cast("Mock", use_case)

    async def get_user_storage(self) -> Mock:
        storage = await self.container.get(UserAccountStorage)
        return cast("Mock", storage)

    async def get_accounts_use_case(self) -> Mock:
        use_case = await self.container.get(AccountsUseCase)
        return cast("Mock", use_case)

    async def get_current_account_use_case(self) -> Mock:
        use_case = await self.container.get(CurrentAccountUseCase)
        return cast("Mock", use_case)

    async def get_readiness_checker(self) -> Mock:
        checker = await self.container.get(ReadinessChecker)
        return cast("Mock", checker)
