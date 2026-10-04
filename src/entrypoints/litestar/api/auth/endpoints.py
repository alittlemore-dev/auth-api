from datetime import datetime
from typing import Annotated

from dishka import FromDishka
from dishka.integrations.litestar import DishkaRouter
from litestar import Controller, Response, post, status_codes
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ServiceUnavailableException

from core.api_tokens.use_cases import ApiTokensUseCase
from core.auth.enums import RoleEnum
from core.auth.exceptions import ForbiddenError, UnauthorizedError
from core.auth.schemas import (
    AuthAuthenticateParams,
    AuthLoginParams,
    AuthLogoutParams,
    AuthRefreshAccessTokenParams,
    AuthSessionClientMetadata,
    AuthUseCaseConfig,
)
from core.auth.types import SessionSecret, Token
from core.auth.use_cases import AuthUseCase
from core.schemas import Secret
from entrypoints.litestar.api.auth.dependencies import (
    provide_logout_session_secret,
    provide_refresh_session_secret,
)
from entrypoints.litestar.api.auth.responses import (
    create_login_response,
    create_logout_response,
    create_refresh_response,
    create_verify_response,
)
from entrypoints.litestar.api.auth.schemas import (
    AccessTokenResponseSchema,
    LoginRequestSchema,
    VerifyAccessTokenResponseSchema,
    VerifyCredentialResponseSchema,
)
from entrypoints.litestar.api.openapi import OPENAPI_PASSWORD_EXAMPLE
from entrypoints.litestar.api.parameters import api_json_body
from infra.config.constants import constants


class AuthApiController(Controller):
    path = "/"
    tags = ["auth"]

    @post(
        "/verify",
        security=[{"bearerAuth": []}],
        name="verify-access-token-api-handler",
        description="Verify a browser session access token; personal API tokens are rejected.",
        status_code=status_codes.HTTP_200_OK,
    )
    async def verify_access_token(
        self,
        token: FromDishka[Token],
        use_case: FromDishka[AuthUseCase],
        current_datetime: FromDishka[datetime],
    ) -> Response[VerifyAccessTokenResponseSchema]:
        if token.startswith(b"alm_pat_"):
            raise UnauthorizedError
        try:
            result = await use_case.verify_access_token(
                params=AuthAuthenticateParams(
                    token=token,
                    required_role=RoleEnum.USER,
                    current_datetime=current_datetime,
                ),
            )
        except UnauthorizedError, ForbiddenError:
            raise
        except Exception as exc:
            raise ServiceUnavailableException from exc
        return create_verify_response(result=result)

    @post(
        "/verify/v2",
        status_code=200,
        security=[{"bearerAuth": []}],
        description=(
            "Verify a session or personal API token and return the current role, "
            "credential type, permissions and cache parameters. PAT verification "
            "must not be cached; cacheTtlSeconds is zero."
        ),
    )
    async def verify_credential(
        self,
        token: FromDishka[Token],
        use_case: FromDishka[AuthUseCase],
        pat_use_case: FromDishka[ApiTokensUseCase],
        current_datetime: FromDishka[datetime],
    ) -> Response[VerifyCredentialResponseSchema]:
        try:
            if token.startswith(b"alm_pat_"):
                pat = await pat_use_case.verify(secret=Secret(token.decode()), now=current_datetime)
                schema = VerifyCredentialResponseSchema(
                    username=pat.user.username,
                    role=pat.user.role,
                    valid_for_seconds=pat.valid_for_seconds,
                    credential_type="pat",
                    credential_id=pat.credential_id,
                    permissions=sorted(pat.permissions),
                    cache_ttl_seconds=0,
                )
            else:
                session = await use_case.verify_access_token(
                    params=AuthAuthenticateParams(
                        token=token,
                        required_role=RoleEnum.USER,
                        current_datetime=current_datetime,
                    )
                )
                schema = VerifyCredentialResponseSchema(
                    username=session.user.username,
                    role=session.user.role,
                    valid_for_seconds=session.valid_for_seconds,
                    credential_type="session",
                    credential_id=session.credential_id,
                    permissions=[],
                    cache_ttl_seconds=min(
                        constants.auth.session_verification_cache_seconds, session.valid_for_seconds
                    ),
                )
        except UnauthorizedError, ForbiddenError:
            raise
        except Exception as exc:
            raise ServiceUnavailableException from exc
        return Response(
            content=schema, headers={"Cache-Control": constants.auth.no_store_header_value}
        )

    @post(
        "/login",
        name="login-api-handler",
        description=(
            "Log in to the system. Creates a server-side session cookie and returns a "
            "short-lived PASETO access token."
        ),
        status_code=status_codes.HTTP_200_OK,
    )
    async def login(
        self,
        data: Annotated[
            LoginRequestSchema,
            api_json_body(
                title="Login request",
                description="Username and password used to create a PASETO access token.",
                examples=({"username": "moderator", "password": OPENAPI_PASSWORD_EXAMPLE},),
            ),
        ],
        use_case: FromDishka[AuthUseCase],
        config: FromDishka[AuthUseCaseConfig],
        current_datetime: FromDishka[datetime],
        client_metadata: FromDishka[AuthSessionClientMetadata],
    ) -> Response[AccessTokenResponseSchema]:
        result = await use_case.login(
            config=config,
            params=AuthLoginParams(
                username=data.username,
                password=data.password,
                required_role=RoleEnum.MODERATOR,
                current_datetime=current_datetime,
                client_metadata=client_metadata,
            ),
        )
        return create_login_response(result=result)

    @post(
        "/refresh",
        name="refresh-api-handler",
        description="Refresh the short-lived access token from the server-side session cookie.",
        status_code=status_codes.HTTP_200_OK,
        dependencies={
            "session_secret": Provide(provide_refresh_session_secret, sync_to_thread=False),
        },
    )
    async def refresh(
        self,
        session_secret: NamedDependency[SessionSecret],
        use_case: FromDishka[AuthUseCase],
        config: FromDishka[AuthUseCaseConfig],
        current_datetime: FromDishka[datetime],
    ) -> Response[AccessTokenResponseSchema]:
        result = await use_case.refresh_access_token(
            config=config,
            params=AuthRefreshAccessTokenParams(
                session_secret=session_secret,
                required_role=RoleEnum.MODERATOR,
                current_datetime=current_datetime,
            ),
        )
        return create_refresh_response(result=result)

    @post(
        "/logout",
        name="logout-api-handler",
        description="Log out of the system. Revokes the current session and PASETO access token.",
        status_code=status_codes.HTTP_200_OK,
        dependencies={
            "session_secret": Provide(provide_logout_session_secret, sync_to_thread=False),
        },
    )
    async def logout(
        self,
        session_secret: NamedDependency[SessionSecret | None],
        token: FromDishka[Token],
        use_case: FromDishka[AuthUseCase],
    ) -> Response[None]:
        await use_case.logout(
            params=AuthLogoutParams(
                token=token,
                session_secret=session_secret,
            ),
        )
        return create_logout_response()


api_router = DishkaRouter("", route_handlers=[AuthApiController])
