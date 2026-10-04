from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from core.api_tokens.generators import ApiTokenSecretGenerator
from core.api_tokens.services import ApiPermissionRegistry
from core.api_tokens.storages import ApiTokenStorage
from core.api_tokens.use_cases import ApiTokensUseCase
from core.auth.password_hashers import PasswordHasher
from infra.postgresql.storages.api_tokens import ApiTokenDatabaseStorage


class ApiTokensProvider(Provider):
    @provide(scope=Scope.APP)
    def registry(self) -> ApiPermissionRegistry:
        return ApiPermissionRegistry()

    @provide(scope=Scope.APP)
    def generator(self) -> ApiTokenSecretGenerator:
        return ApiTokenSecretGenerator()

    @provide(scope=Scope.REQUEST)
    def storage(self, session: AsyncSession) -> ApiTokenStorage:
        return ApiTokenDatabaseStorage(session=session)

    @provide(scope=Scope.REQUEST)
    def use_case(
        self,
        storage: ApiTokenStorage,
        hasher: PasswordHasher,
        generator: ApiTokenSecretGenerator,
        registry: ApiPermissionRegistry,
    ) -> ApiTokensUseCase:
        return ApiTokensUseCase(
            storage=storage, hasher=hasher, generator=generator, registry=registry
        )
