from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.schemas import User
from infra.postgresql.models import UserModel


@dataclass(kw_only=True)
class StorageHelper:
    session: AsyncSession

    async def create_user(self, user: User) -> UserModel:
        model = UserModel.from_domain_schema(schema=user)
        await self.session.merge(model)
        await self.session.flush()
        return model

    async def create_users(self, users: list[User]) -> list[UserModel]:
        db_users = [UserModel.from_domain_schema(schema=user) for user in users]
        self.session.add_all(db_users)
        await self.session.flush()
        return db_users
