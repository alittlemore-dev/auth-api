from backend_sdk import Principal
from litestar import Request


def throttle_api_token_password_requests(request: Request) -> bool:
    return (
        request.method == "POST"
        and request.url.path.startswith("/api/auth/account/me/api-tokens")
        and not request.url.path.endswith("/revoke")
    )


def api_token_rate_limit_identifier(request: Request) -> str:
    user = request.scope.get("user")
    if isinstance(user, Principal) and not user.is_anon:
        return f"api-token-password::{user.username}"
    return f"api-token-password::{request.client.host if request.client else 'unknown'}"
