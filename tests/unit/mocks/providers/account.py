from unittest.mock import Mock

from dishka import Provider, Scope, provide

from core.account.clients import (
    AccountAvatarClient,
    AccountAvatarProcessor,
    AccountAvatarRollbackRegistrar,
)
from core.account.storages import CurrentAccountStorage, ManagedAccountStorage, UserAccountStorage
from core.account.use_cases import AccountsUseCase, CurrentAccountUseCase


class MockUserAccountProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_account_avatar_client(self) -> AccountAvatarClient:
        return Mock(spec=AccountAvatarClient)

    @provide(scope=Scope.APP)
    async def provide_account_avatar_processor(self) -> AccountAvatarProcessor:
        return Mock(spec=AccountAvatarProcessor)

    @provide(scope=Scope.APP)
    async def provide_account_avatar_rollback_registrar(
        self,
    ) -> AccountAvatarRollbackRegistrar:
        return Mock(spec=AccountAvatarRollbackRegistrar)

    @provide(scope=Scope.APP)
    async def provide_user_storage(self) -> UserAccountStorage:
        return Mock(spec=UserAccountStorage)

    @provide(scope=Scope.APP)
    async def provide_managed_account_storage(self) -> ManagedAccountStorage:
        return Mock(spec=ManagedAccountStorage)

    @provide(scope=Scope.APP)
    async def provide_current_account_storage(self) -> CurrentAccountStorage:
        return Mock(spec=CurrentAccountStorage)

    @provide(scope=Scope.APP)
    async def provide_accounts_use_case(self) -> AccountsUseCase:
        return Mock(spec=AccountsUseCase)

    @provide(scope=Scope.APP)
    async def provide_current_account_use_case(self) -> CurrentAccountUseCase:
        return Mock(spec=CurrentAccountUseCase)
