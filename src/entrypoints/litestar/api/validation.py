import re
from typing import Annotated

from pydantic import AfterValidator, Field

from infra.config.constants import constants


def trim_required(value: str) -> str:
    trimmed_value = value.strip()
    if not trimmed_value:
        msg = "value must not be blank"
        raise ValueError(msg)
    return trimmed_value


def validate_account_username(value: str) -> str:
    trimmed_value = trim_required(value)
    if re.fullmatch(constants.admin_validation.account_username_pattern, trimmed_value) is None:
        msg = "value must contain Latin letters, digits, dots, or underscores only"
        raise ValueError(msg)
    return trimmed_value


AccountUsernameString = Annotated[
    str,
    Field(
        min_length=constants.admin_validation.account_username_min_length,
        max_length=constants.admin_validation.short_text_max_length,
    ),
    AfterValidator(validate_account_username),
]
AccountPasswordString = Annotated[
    str,
    Field(
        min_length=constants.admin_validation.account_password_min_length,
        max_length=constants.admin_validation.short_text_max_length,
    ),
]
