from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from core.account.schemas import CurrentAccount


@dataclass(frozen=True, slots=True, kw_only=True)
class AvatarOrphanCleanupUseCaseConfig:
    retention_seconds: int


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountAvatarUpload:
    content: bytes
    declared_mime_type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessedAccountAvatar:
    content: bytes
    mime_type: Literal["image/webp"] = "image/webp"


@dataclass(frozen=True, slots=True, kw_only=True)
class CurrentAccountAvatarMutationResult:
    account: CurrentAccount
    old_object_name: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class CurrentAccountAvatarContent:
    content: AsyncIterator[bytes]
    mime_type: Literal["image/webp"] = "image/webp"


@dataclass(frozen=True, slots=True, kw_only=True)
class AvatarOrphanCleanupResult:
    scanned_count: int
    referenced_count: int
    deleted_count: int
    failed_count: int

    def as_dict(self) -> dict[str, int]:
        return {
            "scannedCount": self.scanned_count,
            "referencedCount": self.referenced_count,
            "deletedCount": self.deleted_count,
            "failedCount": self.failed_count,
        }
