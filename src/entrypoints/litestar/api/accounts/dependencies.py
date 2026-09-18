from backend_sdk import Principal
from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Request
from litestar.datastructures import State

from core.account.schemas import ManagedAccountFilters
from core.auth.exceptions import UnauthorizedError
from core.auth.token_handlers import TokenHandler
from core.auth.types import Token
from entrypoints.litestar.api.parameters import PageQuery, PageSizeQuery


def provide_managed_account_filters(
    page: PageQuery,
    page_size: PageSizeQuery,
) -> ManagedAccountFilters:
    return ManagedAccountFilters(page=page, page_size=page_size)


@inject
async def provide_current_session_id(
    request: Request[Principal, Token | None, State],
    token_handler: FromDishka[TokenHandler],
) -> str:
    if request.auth is None:
        raise UnauthorizedError
    return token_handler.decode_token(request.auth).session_id
