from base64 import urlsafe_b64encode
from collections.abc import Callable

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator

from core.schemas import Secret
from infra.config.settings import settings
from infra.postgresql.exceptions import EncryptedValueError

_INVALID_DATABASE_VALUE_MESSAGE = "Encrypted database value is invalid"
_INVALID_BOUND_VALUE_MESSAGE = "EncryptedString accepts Secret values only"


class EncryptedString[T](TypeDecorator[Secret[T]]):
    impl = Text
    cache_ok = True
    _fernet = Fernet(
        urlsafe_b64encode(settings.app.secret_key.to_domain_secret().sha256_digest()),
    )

    def __init__(
        self,
        *,
        serialize: Callable[[T], str],
        deserialize: Callable[[str], T],
    ) -> None:
        super().__init__()
        self._serialize = serialize
        self._deserialize = deserialize

    def process_bind_param(
        self,
        value: Secret[T] | None,
        dialect: Dialect,
    ) -> str | None:
        del dialect
        if value is None:
            return None
        if not isinstance(value, Secret):
            raise TypeError(_INVALID_BOUND_VALUE_MESSAGE)
        try:
            serialized = self._serialize(value.get_secret_value()).encode()
            return self._fernet.encrypt(serialized).decode()
        except (TypeError, ValueError, UnicodeError) as error:
            raise EncryptedValueError(_INVALID_DATABASE_VALUE_MESSAGE) from error

    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> Secret[T] | None:
        del dialect
        if value is None:
            return None
        try:
            serialized = self._fernet.decrypt(value.encode()).decode()
            return Secret(self._deserialize(serialized))
        except (InvalidToken, TypeError, ValueError, UnicodeError) as error:
            raise EncryptedValueError(_INVALID_DATABASE_VALUE_MESSAGE) from error
