from litestar.datastructures import MutableScopeHeaders
from litestar.types import Message, Scope


async def set_telegram_response_no_store(message: Message, scope: Scope) -> None:
    if message["type"] != "http.response.start":
        return
    path = scope.get("path", "")
    prefix = "/api/auth/internal/telegram/"
    if not (path.startswith(prefix) and path.endswith("/settings")):
        return
    MutableScopeHeaders.from_message(message)["Cache-Control"] = "no-store"
