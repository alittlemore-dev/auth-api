from datetime import datetime
from typing import Annotated

from backend_sdk import Principal
from dishka import FromDishka
from dishka.integrations.litestar import DishkaRouter
from litestar import Controller, Request, get, post
from litestar.datastructures import State

from core.api_tokens.services import ApiPermissionRegistry
from core.api_tokens.use_cases import ApiTokensUseCase
from core.auth.enums import RoleEnum
from core.auth.schemas import BaseUser
from core.auth.types import Token
from core.schemas import Secret
from entrypoints.litestar.api.api_tokens.guards import ApiTokenManagementGuard
from entrypoints.litestar.api.api_tokens.schemas import (
    ApiPermissionSchema,
    ApiPermissionsSchema,
    ApiTokenCreatedSchema,
    ApiTokenCreateSchema,
    ApiTokenListSchema,
    ApiTokenMetadataSchema,
    ApiTokenPasswordSchema,
    ApiTokenSecretSchema,
)
from entrypoints.litestar.api.openapi import OPENAPI_PASSWORD_EXAMPLE
from entrypoints.litestar.api.parameters import ApiTokenIdPath, api_json_body


class ApiTokensController(Controller):
    path = "/account/me/api-tokens"
    tags = ["API tokens"]
    guards = [ApiTokenManagementGuard()]
    opt = {"pat_session_only": True}
    cache = False
    description = "Browser session only; personal API tokens cannot manage API tokens."
    security = [{"bearerAuth": []}]

    @get(
        "/permissions",
        description=(
            "List permissions available to the current role. Browser session only; personal API "
            "tokens cannot manage API tokens. Response is no-store."
        ),
    )
    async def permissions(
        self,
        request: Request[Principal, Token | None, State],
        registry: FromDishka[ApiPermissionRegistry],
    ) -> ApiPermissionsSchema:
        return ApiPermissionsSchema(
            permissions=[
                ApiPermissionSchema.from_domain_schema(permission)
                for permission in registry.allowed_for(
                    user=BaseUser(
                        username=request.user.username,
                        role=RoleEnum.from_value(request.user.role.value),
                    )
                )
            ]
        )

    @get(
        "",
        description=(
            "List owned token metadata without secrets. Browser session only; personal API "
            "tokens cannot manage API tokens. Response is no-store."
        ),
    )
    async def list_tokens(
        self,
        request: Request[Principal, Token | None, State],
        use_case: FromDishka[ApiTokensUseCase],
        now: FromDishka[datetime],
    ) -> ApiTokenListSchema:
        tokens = await use_case.list_tokens(username=request.user.username)
        return ApiTokenListSchema(
            tokens=[
                ApiTokenMetadataSchema.from_domain_schema(schema=token, now=now) for token in tokens
            ]
        )

    @post(
        "",
        status_code=201,
        description=(
            "Create a personal API token after current-password confirmation. Permissions and "
            "expiration are immutable. Browser session only; personal API tokens cannot manage "
            "API tokens. The issued secret response is no-store."
        ),
    )
    async def create_token(
        self,
        request: Request[Principal, Token | None, State],
        data: Annotated[
            ApiTokenCreateSchema,
            api_json_body(
                title="Create personal API token",
                description="Confirm the current password and select scopes and expiration.",
                examples=(
                    {
                        "name": "CLI",
                        "password": OPENAPI_PASSWORD_EXAMPLE,
                        "permissions": ["workspace.resumes.read"],
                        "expiresAt": "2026-10-05T00:00:00Z",
                    },
                ),
            ),
        ],
        use_case: FromDishka[ApiTokensUseCase],
        now: FromDishka[datetime],
    ) -> ApiTokenCreatedSchema:
        token = await use_case.create_token(
            username=request.user.username,
            password=Secret(data.password.get_secret_value()),
            params=data.to_domain_schema(),
            now=now,
        )
        return ApiTokenCreatedSchema(
            token=ApiTokenMetadataSchema.from_domain_schema(schema=token, now=now),
            secret=token.secret.get_secret_value(),
        )

    @post(
        "/{token_id:str}/reveal",
        status_code=200,
        description=(
            "Reveal the same active secret after current-password confirmation for each request. "
            "Browser session only; personal API tokens cannot manage API tokens. Response is "
            "no-store; expired or revoked tokens cannot be revealed."
        ),
    )
    async def reveal_token(
        self,
        request: Request[Principal, Token | None, State],
        token_id: ApiTokenIdPath,
        data: Annotated[
            ApiTokenPasswordSchema,
            api_json_body(
                title="Reveal personal API token",
                description="Confirm the current password for each reveal or copy operation.",
                examples=({"password": OPENAPI_PASSWORD_EXAMPLE},),
            ),
        ],
        use_case: FromDishka[ApiTokensUseCase],
        now: FromDishka[datetime],
    ) -> ApiTokenSecretSchema:
        secret = await use_case.reveal_token(
            username=request.user.username,
            token_id=token_id,
            password=Secret(data.password.get_secret_value()),
            now=now,
        )
        return ApiTokenSecretSchema(secret=secret.get_secret_value())

    @post(
        "/{token_id:str}/revoke",
        status_code=200,
        description=(
            "Permanently revoke an owned token; repeated revocation is idempotent. Browser session "
            "only; personal API tokens cannot manage API tokens. Response is no-store."
        ),
    )
    async def revoke_token(
        self,
        request: Request[Principal, Token | None, State],
        token_id: ApiTokenIdPath,
        use_case: FromDishka[ApiTokensUseCase],
        now: FromDishka[datetime],
    ) -> ApiTokenMetadataSchema:
        token = await use_case.revoke_token(
            username=request.user.username, token_id=token_id, now=now
        )
        return ApiTokenMetadataSchema.from_domain_schema(schema=token, now=now)


api_router = DishkaRouter("", route_handlers=[ApiTokensController])
