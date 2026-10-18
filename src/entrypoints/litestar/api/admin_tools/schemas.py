from typing import Annotated

from pydantic import Field

from core.auth.schemas import AuthSessionCleanupResult, AuthSessionCleanupStatus
from entrypoints.litestar.api.schemas import CamelCaseSchema


class AuthSessionsStatusResponseSchema(CamelCaseSchema):
    expired_count: Annotated[
        int,
        Field(
            title="Expired session count",
            description="Sessions already expired at the observation time.",
            examples=[12],
        ),
    ]
    expiring_soon_count: Annotated[
        int,
        Field(
            title="Expiring soon session count",
            description="Sessions expiring within the reported upcoming window.",
            examples=[4],
        ),
    ]
    expiring_soon_days: Annotated[
        int,
        Field(
            title="Expiring soon window in days",
            description="Configured upcoming-expiration observation window in days.",
            examples=[7],
        ),
    ]
    scheduled_prune_interval_seconds: Annotated[
        int,
        Field(
            title="Scheduled prune interval in seconds",
            description="Configured background session cleanup interval in seconds.",
            examples=[3600],
        ),
    ]

    @classmethod
    def from_domain_schema(
        cls,
        *,
        schema: AuthSessionCleanupStatus,
    ) -> AuthSessionsStatusResponseSchema:
        return cls.model_construct(
            expired_count=schema.expired_count,
            expiring_soon_count=schema.expiring_soon_count,
            expiring_soon_days=schema.expiring_soon_days,
            scheduled_prune_interval_seconds=schema.scheduled_prune_interval_seconds,
        )


class AuthSessionsPruneResponseSchema(CamelCaseSchema):
    deleted_count: Annotated[
        int,
        Field(
            title="Deleted session count",
            description="Expired sessions removed by this operation.",
            examples=[12],
        ),
    ]
    expired_count: Annotated[
        int,
        Field(
            title="Expired session count",
            description="Sessions already expired at the observation time.",
            examples=[12],
        ),
    ]
    expiring_soon_count: Annotated[
        int,
        Field(
            title="Expiring soon session count",
            description="Sessions expiring within the reported upcoming window.",
            examples=[4],
        ),
    ]
    expiring_soon_days: Annotated[
        int,
        Field(
            title="Expiring soon window in days",
            description="Configured upcoming-expiration observation window in days.",
            examples=[7],
        ),
    ]
    scheduled_prune_interval_seconds: Annotated[
        int,
        Field(
            title="Scheduled prune interval in seconds",
            description="Configured background session cleanup interval in seconds.",
            examples=[3600],
        ),
    ]

    @classmethod
    def from_domain_schema(
        cls,
        *,
        schema: AuthSessionCleanupResult,
    ) -> AuthSessionsPruneResponseSchema:
        return cls.model_construct(
            deleted_count=schema.deleted_count,
            expired_count=schema.expired_count,
            expiring_soon_count=schema.expiring_soon_count,
            expiring_soon_days=schema.expiring_soon_days,
            scheduled_prune_interval_seconds=schema.scheduled_prune_interval_seconds,
        )
