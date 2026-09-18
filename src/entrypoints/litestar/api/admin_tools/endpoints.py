from datetime import datetime

from backend_sdk import RoleEnum
from backend_sdk.integrations.litestar import RequireRole
from dishka import FromDishka
from dishka.integrations.litestar import DishkaRouter
from litestar import Controller, get, post, status_codes

from core.auth.schemas import AuthSessionCleanupParams, AuthSessionCleanupPolicy
from core.auth.use_cases import AuthSessionCleanupUseCase
from entrypoints.litestar.api.admin_tools.schemas import (
    AuthSessionsPruneResponseSchema,
    AuthSessionsStatusResponseSchema,
)


class AdminToolsApiController(Controller):
    path = "/tools"
    tags = ["admin tools"]
    guards = [RequireRole(RoleEnum.ADMIN)]

    @get(
        "/auth-sessions",
        description="Get expired and soon-expiring auth session counts.",
        name="admin-tools-auth-sessions-status-api-handler",
        status_code=status_codes.HTTP_200_OK,
        cache=False,
    )
    async def get_auth_sessions_status(
        self,
        current_datetime: FromDishka[datetime],
        use_case: FromDishka[AuthSessionCleanupUseCase],
        policy: FromDishka[AuthSessionCleanupPolicy],
    ) -> AuthSessionsStatusResponseSchema:
        status = await use_case.get_cleanup_status(
            policy=policy,
            params=AuthSessionCleanupParams(current_datetime=current_datetime),
        )
        return AuthSessionsStatusResponseSchema.from_domain_schema(schema=status)

    @post(
        "/auth-sessions/prune",
        description="Delete expired auth sessions and return refreshed counts.",
        name="admin-tools-auth-sessions-prune-api-handler",
        status_code=status_codes.HTTP_200_OK,
        cache=False,
    )
    async def prune_auth_sessions(
        self,
        current_datetime: FromDishka[datetime],
        use_case: FromDishka[AuthSessionCleanupUseCase],
        policy: FromDishka[AuthSessionCleanupPolicy],
    ) -> AuthSessionsPruneResponseSchema:
        result = await use_case.prune_expired_sessions(
            policy=policy,
            params=AuthSessionCleanupParams(current_datetime=current_datetime),
        )
        return AuthSessionsPruneResponseSchema.from_domain_schema(schema=result)


admin_router = DishkaRouter("", route_handlers=[AdminToolsApiController])
