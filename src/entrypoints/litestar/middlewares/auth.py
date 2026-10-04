from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

from backend_sdk import CredentialTypeEnum, Principal
from backend_sdk import RoleEnum as SdkRoleEnum
from backend_sdk.integrations.litestar import AuthContext, authorize_pat_route
from dishka import AsyncContainer
from litestar.connection import ASGIConnection
from litestar.middleware import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from litestar.types import ASGIApp, Method, Scopes

from core.api_tokens.use_cases import ApiTokensUseCase
from core.auth.enums import RoleEnum
from core.auth.exceptions import UnauthorizedError
from core.auth.schemas import AuthAuthenticateParams
from core.auth.types import Token
from core.auth.use_cases import AuthUseCase
from core.schemas import Secret


class AuthenticationMiddleware(AbstractAuthenticationMiddleware):
    __slots__ = (
        "app",
        "container",
        "exclude",
        "exclude_http_methods",
        "exclude_opt_key",
        "scopes",
        "token_header_name",
        "token_prefix",
    )

    def __init__(  # noqa: PLR0913
        self,
        app: ASGIApp,
        token_header_name: str,
        token_prefix: str,
        container: AsyncContainer,
        exclude: str | list[str] | None,
        exclude_from_auth_key: str,
        exclude_http_methods: Sequence[Method] | None,
        scopes: Scopes | None,
    ) -> None:
        super().__init__(
            app=app,
            exclude=exclude,
            exclude_from_auth_key=exclude_from_auth_key,
            exclude_http_methods=exclude_http_methods,
            scopes=scopes,
        )
        self.token_header_name = token_header_name
        self.token_prefix = token_prefix
        self.container = container

    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        anon_result = AuthenticationResult(user=Principal.anonymous(), auth=None)
        token: str | None = connection.headers.get(self.token_header_name)
        prefix = self.token_prefix + " "
        if not token or not token.startswith(prefix):
            return anon_result
        value = token[len(prefix) :]
        if (
            not value
            or value != value.strip()
            or " " in value
            or not value.isascii()
            or not value.isprintable()
        ):
            return anon_result
        clear_token = Token(value.encode())
        async with self.container() as request_container:
            use_case = await request_container.get(AuthUseCase)
            try:
                now = await request_container.get(datetime)
                if clear_token.startswith(b"alm_pat_"):
                    pat_use_case = await request_container.get(ApiTokensUseCase)
                    verification = await pat_use_case.verify(
                        secret=Secret(clear_token.decode()),
                        now=now,
                    )
                    context = AuthContext(
                        valid_for_seconds=verification.valid_for_seconds,
                        credential_type=CredentialTypeEnum.PAT,
                        credential_id=verification.credential_id,
                        permissions=verification.permissions,
                        cache_ttl_seconds=0,
                    )
                    authorize_pat_route(context, connection.route_handler)
                    cast("dict[str, Any]", connection.scope)["credential_context"] = context
                    return AuthenticationResult(
                        user=Principal(
                            username=verification.user.username,
                            role=SdkRoleEnum(verification.user.role.value),
                        ),
                        auth=clear_token,
                    )
                authentication = await use_case.authenticate(
                    params=AuthAuthenticateParams(
                        token=clear_token,
                        required_role=RoleEnum.USER,
                        current_datetime=now,
                    ),
                )
            except UnauthorizedError:
                return anon_result
        return AuthenticationResult(
            user=Principal(
                username=authentication.user.username,
                role=SdkRoleEnum(authentication.user.role.value),
            ),
            auth=clear_token,
        )
