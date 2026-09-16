from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from valkey.asyncio import Valkey

from infra.healthcheck import ReadinessChecker, ReadinessCheckError


class TestReadinessChecker:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.session = AsyncMock(spec=AsyncSession)
        self.valkey = AsyncMock(spec=Valkey)
        self.valkey.ping = AsyncMock()
        self.checker = ReadinessChecker(session=self.session, valkey=self.valkey)

    async def test_check_requires_postgres_and_valkey(self) -> None:
        await self.checker.check()
        self.session.execute.assert_awaited_once()
        self.valkey.ping.assert_awaited_once()

    @pytest.mark.parametrize("dependency", ["postgres", "valkey"])
    async def test_unavailable_dependency_fails_readiness(self, dependency: str) -> None:
        operation = self.session.execute if dependency == "postgres" else self.valkey.ping
        operation.side_effect = RuntimeError("Dependency unavailable")
        with pytest.raises(ReadinessCheckError):
            await self.checker.check()
