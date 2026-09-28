from litestar.datastructures import MutableScopeHeaders
from litestar.types import Message, Scope


async def set_account_settings_response_no_store(message: Message, scope: Scope) -> None:
    if message["type"] != "http.response.start":
        return
    path = scope.get("path", "")
    if not (path.startswith("/api/auth/internal/account/") and path.endswith("/settings")):
        return
    MutableScopeHeaders.from_message(message)["Cache-Control"] = "no-store"
