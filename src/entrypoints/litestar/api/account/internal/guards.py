import hmac

from litestar.connection import ASGIConnection
from litestar.exceptions import HTTPException
from litestar.handlers import BaseRouteHandler

from infra.config.settings import settings


def require_internal_service_secret(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    expected = settings.telegram.service_secret.get_secret_value()
    supplied = connection.headers.get("X-Internal-Service-Secret", "")
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=403)
