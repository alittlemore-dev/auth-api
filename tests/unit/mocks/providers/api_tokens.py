from unittest.mock import Mock

from dishka import Provider, Scope, provide

from core.api_tokens.services import ApiPermissionRegistry
from core.api_tokens.use_cases import ApiTokensUseCase


class MockApiTokensProvider(Provider):
    @provide(scope=Scope.APP)
    def registry(self) -> ApiPermissionRegistry:
        return ApiPermissionRegistry()

    @provide(scope=Scope.APP)
    def use_case(self) -> ApiTokensUseCase:
        return Mock(spec=ApiTokensUseCase)
