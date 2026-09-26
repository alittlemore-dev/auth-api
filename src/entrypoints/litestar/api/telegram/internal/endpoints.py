from contextlib import suppress
from typing import Annotated

from dishka import FromDishka
from dishka.integrations.litestar import DishkaRouter
from litestar import Controller, get
from litestar.params import PathParameter, QueryParameter

from core.account.enums import TelegramBotId
from core.account.use_cases import CurrentAccountUseCase
from core.auth.exceptions import UserNotFoundError
from entrypoints.litestar.api.telegram.internal.guards import require_telegram_service_secret
from entrypoints.litestar.api.telegram.internal.schemas import TelegramSettingsResponse
from infra.config.settings import settings


class TelegramInternalController(Controller):
    path = "/internal/telegram"
    include_in_schema = False
    response_headers = {"Cache-Control": "no-store"}
    guards = [require_telegram_service_secret]

    @get("/{telegram_bot_id:str}/settings", name="telegram-bot-settings", status_code=200)
    async def get_settings(
        self,
        telegram_bot_id: Annotated[TelegramBotId, PathParameter()],
        owner_username: Annotated[
            str, QueryParameter(name="ownerUsername", min_length=1, max_length=255)
        ],
        use_case: FromDishka[CurrentAccountUseCase],
    ) -> TelegramSettingsResponse:
        enabled = False
        with suppress(UserNotFoundError):
            account = await use_case.get_account(username=owner_username)
            bot_settings = account.settings.telegram_bots.get(telegram_bot_id)
            enabled = bot_settings.enabled if bot_settings is not None else False
        return TelegramSettingsResponse(
            available=settings.telegram.is_available_for(telegram_bot_id),
            enabled=enabled,
        )


api_router = DishkaRouter(
    path="",
    route_handlers=[TelegramInternalController],
)
