import hashlib
from base64 import urlsafe_b64encode
from collections.abc import Callable
from typing import cast

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.dialects import postgresql

from core.enums import StrEnum
from core.schemas import Secret
from infra.postgresql.exceptions import EncryptedValueError
from infra.postgresql.types.encrypted_string import EncryptedString

APP_SECRET_KEY = "permanent-app-secret"  # noqa: S105  # nosec B105


class LocalGenderEnum(StrEnum):
    MALE = "male"
    FEMALE = "female"


def create_encrypted_string[T](
    *,
    serialize: Callable[[T], str] | None = None,
    deserialize: Callable[[str], T] | None = None,
) -> EncryptedString[T]:
    return EncryptedString[T](
        secret_key=Secret(APP_SECRET_KEY),
        serialize=serialize or cast("Callable[[T], str]", str),
        deserialize=deserialize or cast("Callable[[str], T]", str),
    )


def create_reference_fernet() -> Fernet:
    digest = hashlib.sha256(APP_SECRET_KEY.encode()).digest()
    return Fernet(urlsafe_b64encode(digest))


class TestEncryptedString:
    dialect = postgresql.dialect()

    def test_none_passes_through_both_boundaries(self) -> None:
        encrypted: EncryptedString[str] = create_encrypted_string()

        assert encrypted.process_bind_param(None, self.dialect) is None
        assert encrypted.process_result_value(None, self.dialect) is None

    def test_round_trip_returns_secret_instead_of_plain_value(self) -> None:
        encrypted: EncryptedString[str] = create_encrypted_string()

        ciphertext = encrypted.process_bind_param(Secret("Dmitriy"), self.dialect)
        restored = encrypted.process_result_value(ciphertext, self.dialect)

        assert isinstance(restored, Secret)
        assert restored.get_secret_value() == "Dmitriy"
        assert ciphertext != "Dmitriy"

    def test_repeated_plaintext_uses_distinct_fernet_tokens(self) -> None:
        encrypted: EncryptedString[str] = create_encrypted_string()

        first = encrypted.process_bind_param(Secret("Dmitriy"), self.dialect)
        second = encrypted.process_bind_param(Secret("Dmitriy"), self.dialect)

        assert first != second

    def test_key_derivation_matches_sha256_urlsafe_base64_contract(self) -> None:
        encrypted: EncryptedString[str] = create_encrypted_string()
        reference = create_reference_fernet()
        reference_token = reference.encrypt(b"Dmitriy").decode()

        restored = encrypted.process_result_value(reference_token, self.dialect)
        generated_token = encrypted.process_bind_param(Secret("Lunev"), self.dialect)

        assert restored is not None
        assert restored.get_secret_value() == "Dmitriy"
        assert generated_token is not None
        assert reference.decrypt(generated_token.encode()) == b"Lunev"

    def test_enum_codec_returns_secret_wrapped_enum(self) -> None:
        encrypted = create_encrypted_string(
            serialize=lambda value: value.value,
            deserialize=LocalGenderEnum.from_value,
        )

        ciphertext = encrypted.process_bind_param(Secret(LocalGenderEnum.FEMALE), self.dialect)
        restored = encrypted.process_result_value(ciphertext, self.dialect)

        assert restored is not None
        assert restored.get_secret_value() is LocalGenderEnum.FEMALE

    def test_bare_value_is_rejected_without_echoing_it(self) -> None:
        encrypted: EncryptedString[str] = create_encrypted_string()

        with pytest.raises(TypeError) as exc_info:
            encrypted.process_bind_param(cast("Secret[str]", "plaintext"), self.dialect)

        assert str(exc_info.value) == "EncryptedString accepts Secret values only"
        assert "plaintext" not in str(exc_info.value)

    @pytest.mark.parametrize(
        "database_value",
        [
            "not-a-fernet-token",
            create_reference_fernet().encrypt(b"\xff").decode(),
        ],
        ids=["invalid-token", "invalid-utf8"],
    )
    def test_invalid_database_value_raises_sanitized_error(self, database_value: str) -> None:
        encrypted: EncryptedString[str] = create_encrypted_string()

        with pytest.raises(EncryptedValueError) as exc_info:
            encrypted.process_result_value(database_value, self.dialect)

        assert str(exc_info.value) == "Encrypted database value is invalid"
        assert database_value not in str(exc_info.value)

    def test_invalid_enum_value_raises_sanitized_error(self) -> None:
        encrypted = create_encrypted_string(
            serialize=lambda value: value.value,
            deserialize=LocalGenderEnum.from_value,
        )
        database_value = create_reference_fernet().encrypt(b"other").decode()

        with pytest.raises(EncryptedValueError, match="Encrypted database value is invalid"):
            encrypted.process_result_value(database_value, self.dialect)

    def test_repr_does_not_contain_secret_or_codec_details(self) -> None:
        encrypted: EncryptedString[str] = create_encrypted_string()

        representation = repr(encrypted)

        assert APP_SECRET_KEY not in representation
        assert "serialize" not in representation
        assert "deserialize" not in representation
