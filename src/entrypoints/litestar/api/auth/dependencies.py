from litestar import Request

from core.auth.exceptions import ForbiddenError, UnauthorizedError
from core.auth.types import SessionSecret
from infra.config.constants import constants


def provide_refresh_session_secret(request: Request) -> SessionSecret:
    _validate_cookie_request(request)
    session_secret = request.cookies.get(constants.auth.session_cookie_name)
    if session_secret is None:
        raise UnauthorizedError
    return SessionSecret(session_secret)


def provide_logout_session_secret(request: Request) -> SessionSecret | None:
    _validate_cookie_request(request)
    session_secret = request.cookies.get(constants.auth.session_cookie_name)
    if session_secret is None:
        return None
    return SessionSecret(session_secret)


def _validate_cookie_request(request: Request) -> None:
    csrf_guard = request.headers.get(constants.auth.csrf_guard_header_name)
    if csrf_guard != constants.auth.csrf_guard_header_value:
        raise ForbiddenError
    fetch_site = request.headers.get(constants.auth.fetch_metadata_site_header_name)
    if fetch_site == constants.auth.fetch_metadata_cross_site_value:
        raise ForbiddenError
