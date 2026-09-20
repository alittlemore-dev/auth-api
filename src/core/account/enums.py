from core.enums import StrEnum


class GenderEnum(StrEnum):
    MALE = "male"
    FEMALE = "female"


class ManagedAccountActionEnum(StrEnum):
    UPDATE_ROLE = "updateRole"
    UPDATE_PASSWORD = "updatePassword"  # noqa: S105  # nosec B105
    MANAGE_SESSIONS = "manageSessions"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    DELETE = "delete"


class AccountLanguageEnum(StrEnum):
    EN = "en"
    RU = "ru"


class AccountThemeEnum(StrEnum):
    LIGHT = "light"
    DARK = "dark"
