from typing import Annotated

from dishka import FromDishka
from dishka.integrations.litestar import DishkaRouter
from litestar import Controller, get
from litestar.params import PathParameter

from core.account.use_cases import CurrentAccountUseCase
from entrypoints.litestar.api.account.internal.guards import require_internal_service_secret
from entrypoints.litestar.api.account.schemas import AccountSettingsSchema


class AccountInternalController(Controller):
    path = "/internal/account"
    include_in_schema = False
    response_headers = {"Cache-Control": "no-store"}
    guards = [require_internal_service_secret]

    @get("/{username:str}/settings", name="internal-account-settings", status_code=200)
    async def get_settings(
        self,
        username: Annotated[str, PathParameter(min_length=1, max_length=255)],
        use_case: FromDishka[CurrentAccountUseCase],
    ) -> AccountSettingsSchema:
        account = await use_case.get_account(username=username)
        return AccountSettingsSchema.from_domain_schema(account.settings)


api_router = DishkaRouter(path="", route_handlers=[AccountInternalController])
