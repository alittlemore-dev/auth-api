from datetime import datetime
from typing import Annotated

from dishka import FromDishka
from dishka.integrations.litestar import DishkaRouter
from litestar import Controller, Response, post, status_codes
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ServiceUnavailableException

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
)
from entrypoints.litestar.api.openapi import OPENAPI_PASSWORD_EXAMPLE
from entrypoints.litestar.api.parameters import api_json_body


class AuthApiController(Controller):
    path = "/"
    tags = ["auth"]

    @post(
        "/verify",
        name="verify-access-token-api-handler",
        description="Verify a bearer access token for a backend service.",
        status_code=status_codes.HTTP_200_OK,
    )
    async def verify_access_token(
        self,
        token: FromDishka[Token],
        use_case: FromDishka[AuthUseCase],
        current_datetime: FromDishka[datetime],
    ) -> Response[VerifyAccessTokenResponseSchema]:
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
