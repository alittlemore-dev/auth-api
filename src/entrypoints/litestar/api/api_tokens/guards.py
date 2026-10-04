from backend_sdk import Principal
from litestar.connection import ASGIConnection
from litestar.handlers import BaseRouteHandler

from core.auth.exceptions import ForbiddenError, UnauthorizedError
from infra.config.constants import constants


class ApiTokenManagementGuard:
    def __call__(self, connection: ASGIConnection, _: BaseRouteHandler) -> None:
        if not isinstance(connection.user, Principal) or connection.user.is_anon:
            raise UnauthorizedError
        if connection.scope.get("method") in {"GET", "HEAD", "OPTIONS"}:
            return
        if (
            connection.headers.get(constants.auth.csrf_guard_header_name)
            != constants.auth.csrf_guard_header_value
            or connection.headers.get(constants.auth.fetch_metadata_site_header_name)
            == constants.auth.fetch_metadata_cross_site_value
        ):
            raise ForbiddenError
