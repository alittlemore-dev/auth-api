from http import HTTPStatus

from dishka import AsyncContainer
from litestar import Request
from litestar.enums import ScopeType
from litestar.middleware import ASGIMiddleware
from litestar.types import ASGIApp, Message, Receive, Scope, Send

from infra.config.loggers import log_sanitized_exception
from infra.postgresql.transactions import DatabaseTransactionState

TRANSACTION_FAILURE_BODY = b'{"message":"Internal server error"}'


class DatabaseTransactionMiddleware(ASGIMiddleware):
    scopes = (ScopeType.HTTP,)

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        container: AsyncContainer = Request(scope).state.dishka_container
        transaction = await container.get(DatabaseTransactionState)
        transaction_failed = False
        failure_body_sent = False

        async def send_after_transaction(message: Message) -> None:
            nonlocal transaction_failed, failure_body_sent
            if message["type"] == "http.response.start":
                if message["status"] >= HTTPStatus.BAD_REQUEST:
                    transaction.rollback_required = True
                try:
                    await transaction.finish()
                except Exception as exc:  # noqa: BLE001
                    log_sanitized_exception(
                        event="database_transaction_completion_failed", error=exc
                    )
                    transaction_failed = True
                    message = {
                        "type": "http.response.start",
                        "status": HTTPStatus.INTERNAL_SERVER_ERROR,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"cache-control", b"no-store"),
                            (b"content-length", str(len(TRANSACTION_FAILURE_BODY)).encode()),
                        ],
                    }
            elif transaction_failed and message["type"] == "http.response.body":
                if failure_body_sent:
                    return
                failure_body_sent = True
                message = {
                    "type": "http.response.body",
                    "body": TRANSACTION_FAILURE_BODY,
                    "more_body": False,
                }
            await send(message)

        try:
            await next_app(scope, receive, send_after_transaction)
        except BaseException as exc:
            await transaction.finish(request_exception=exc)
            raise
