from infra.config.constants import constants


def validate_time_zone_identifier(value: object) -> object:
    if (
        isinstance(value, str)
        and len(value) > constants.account_time_zone.max_iana_time_zone_length
    ):
        raise ValueError(constants.account_time_zone.invalid_iana_time_zone_message)
    return value
