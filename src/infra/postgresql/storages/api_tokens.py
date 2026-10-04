from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.api_tokens.exceptions import ApiTokenNotFoundError
from core.api_tokens.schemas import ApiToken
from core.api_tokens.storages import ApiTokenStorage
from core.auth.exceptions import UserNotFoundError
from core.auth.schemas import User
from infra.postgresql.models import UserModel
from infra.postgresql.models.api_tokens import ApiTokenModel


@dataclass(kw_only=True)
class ApiTokenDatabaseStorage(ApiTokenStorage):
    session: AsyncSession

    async def get_user(self, *, username: str, lock: bool = False) -> User:
        statement = select(UserModel).where(func.lower(UserModel.username) == username.lower())
        if lock:
            statement = statement.with_for_update()
        user = await self.session.scalar(statement.execution_options(populate_existing=True))
        if user is None:
            raise UserNotFoundError
        return user.to_domain_schema()

    async def create_token(self, *, token: ApiToken) -> ApiToken:
        model = ApiTokenModel.from_domain_schema(token)
        self.session.add(model)
        await self.session.flush()
        return model.to_domain_schema()

    async def list_tokens(self, *, username: str) -> list[ApiToken]:
        models = await self.session.scalars(
            select(ApiTokenModel)
            .where(
                ApiTokenModel.username == username,
            )
            .order_by(ApiTokenModel.created_at.desc(), ApiTokenModel.id)
        )
        return [model.to_domain_schema() for model in models]

    async def get_token(self, *, token_id: str, username: str) -> ApiToken:
        model = await self.session.scalar(
            select(ApiTokenModel).where(
                ApiTokenModel.id == token_id,
                ApiTokenModel.username == username,
            )
        )
        if model is None:
            raise ApiTokenNotFoundError
        return model.to_domain_schema()

    async def get_token_by_hash(self, *, secret_hash: str) -> ApiToken:
        model = await self.session.scalar(
            select(ApiTokenModel).where(
                ApiTokenModel.secret_hash == secret_hash,
            )
        )
        if model is None:
            raise ApiTokenNotFoundError
        return model.to_domain_schema()

    async def touch_token(self, *, token_id: str, now: datetime) -> None:
        await self.session.execute(
            update(ApiTokenModel)
            .where(
                ApiTokenModel.id == token_id,
            )
            .values(last_used_at=now)
        )

    async def revoke_token(self, *, token_id: str, username: str, now: datetime) -> ApiToken:
        model = await self.session.scalar(
            update(ApiTokenModel)
            .where(
                ApiTokenModel.id == token_id,
                ApiTokenModel.username == username,
            )
            .values(revoked_at=func.coalesce(ApiTokenModel.revoked_at, now))
            .returning(ApiTokenModel)
        )
        if model is None:
            raise ApiTokenNotFoundError
        return model.to_domain_schema()

    async def revoke_user_tokens(self, *, username: str, now: datetime) -> None:
        await self.session.execute(
            update(ApiTokenModel)
            .where(
                ApiTokenModel.username == username,
                ApiTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
