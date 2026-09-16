from litestar import Response
from litestar.datastructures import MutableScopeHeaders
from litestar.types import Message, Scope

from core.auth.schemas import (
    AccessTokenResult,
    AuthLoginResult,
    AuthRefreshAccessTokenResult,
    AuthSessionCredentials,
    AuthVerificationResult,
)
from entrypoints.litestar.api.auth.schemas import (
    AccessTokenResponseSchema,
    VerifyAccessTokenResponseSchema,
)
from infra.config.constants import constants


async def set_verify_response_no_store(message: Message, scope: Scope) -> None:
    if message["type"] != "http.response.start" or scope.get("path") != "/api/auth/verify":
        return
    MutableScopeHeaders.from_message(message)["Cache-Control"] = (
        constants.auth.no_store_header_value
    )


def create_verify_response(
    *,
    result: AuthVerificationResult,
) -> Response[VerifyAccessTokenResponseSchema]:
    return Response(
        content=VerifyAccessTokenResponseSchema.from_domain_schema(schema=result),
        headers={"Cache-Control": constants.auth.no_store_header_value},
    )


def create_login_response(*, result: AuthLoginResult) -> Response[AccessTokenResponseSchema]:
    response = _create_access_token_response(result=result.access_token)
    _set_session_cookie(response=response, session=result.session)
    return response


def create_refresh_response(
    *,
    result: AuthRefreshAccessTokenResult,
) -> Response[AccessTokenResponseSchema]:
    response = _create_access_token_response(result=result.access_token)
    _set_session_cookie(response=response, session=result.session)
    return response


def create_logout_response() -> Response[None]:
    response = Response(
        content=None,
        headers={"Cache-Control": constants.auth.no_store_header_value},
    )
    response.delete_cookie(
        key=constants.auth.session_cookie_name,
        path=constants.auth.session_cookie_path,
    )
    return response


def _create_access_token_response(
    *,
    result: AccessTokenResult,
) -> Response[AccessTokenResponseSchema]:
    return Response(
        content=AccessTokenResponseSchema.from_domain_schema(schema=result),
        headers={"Cache-Control": constants.auth.no_store_header_value},
    )


def _set_session_cookie(
    *,
    response: Response[AccessTokenResponseSchema],
    session: AuthSessionCredentials,
) -> None:
    response.set_cookie(
        key=constants.auth.session_cookie_name,
        value=session.secret,
        max_age=session.expires_in_seconds,
        path=constants.auth.session_cookie_path,
        secure=True,
        httponly=True,
        samesite="lax",
    )
