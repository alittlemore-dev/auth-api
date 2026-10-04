from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_dev_utils.types.datetime import UTCDateTime

from core.api_tokens.schemas import ApiToken
from core.schemas import Secret
from infra.postgresql.models.base import BaseModel
from infra.postgresql.models.mixins.ids import HexUuidIDMixin
from infra.postgresql.types import EncryptedString


class ApiTokenModel(HexUuidIDMixin, BaseModel):
    username: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("auth__user_model.username", ondelete="CASCADE"),
    )
    name: Mapped[str] = mapped_column(String(100))
    permissions: Mapped[list[str]] = mapped_column(JSONB)
    secret_hash: Mapped[str] = mapped_column(String(64))
    secret: Mapped[Secret[str]] = mapped_column(
        EncryptedString[str](serialize=str, deserialize=str)
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("secret_hash", name="api_tokens_secret_hash_uniq"),
        Index("api_tokens_username_idx", "username"),
    )

    @classmethod
    def from_domain_schema(cls, schema: ApiToken) -> ApiTokenModel:
        return cls(
            id=schema.id,
            username=schema.username,
            name=schema.name,
            permissions=sorted(schema.permissions),
            secret_hash=schema.secret_hash,
            secret=schema.secret,
            created_at=schema.created_at,
            expires_at=schema.expires_at,
            last_used_at=schema.last_used_at,
            revoked_at=schema.revoked_at,
        )

    def to_domain_schema(self) -> ApiToken:
        return ApiToken(
            id=self.id,
            username=self.username,
            name=self.name,
            permissions=frozenset(self.permissions),
            secret_hash=self.secret_hash,
            secret=self.secret,
            created_at=self.created_at,
            expires_at=self.expires_at,
            last_used_at=self.last_used_at,
            revoked_at=self.revoked_at,
        )
