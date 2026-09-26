from entrypoints.litestar.api.schemas import CamelCaseSchema


class TelegramSettingsResponse(CamelCaseSchema):
    available: bool
    enabled: bool
