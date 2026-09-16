# ruff: noqa: S106
import pytest_asyncio

from core.auth.enums import RoleEnum
from core.auth.exceptions import UnauthorizedError
from core.auth.schemas import AuthAuthenticateParams, AuthVerificationResult
from core.auth.types import Token
from tests.test_cases import ApiTestCase
from tests.unit.mocks.providers.auth import test_current_datetime


class TestVerifyAPI(ApiTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container.get_auth_use_case()

    def test_verify_returns_current_principal_and_shortest_validity(self) -> None:
        self.use_case.verify_access_token.return_value = AuthVerificationResult(
            user=self.factory.core.user(
                username="user",
                password_hash="hash",
                role=RoleEnum.USER,
            ),
            valid_for_seconds=120,
        )

        response = self.api.client.post("/api/auth/verify")

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "username": "user",
            "role": "user",
            "validForSeconds": 120,
        }
        self.use_case.verify_access_token.assert_called_once_with(
            params=AuthAuthenticateParams(
                token=Token(b"token"),
                required_role=RoleEnum.USER,
                current_datetime=test_current_datetime,
            ),
        )

    def test_verify_returns_service_unavailable_when_verification_dependency_fails(self) -> None:
        self.use_case.verify_access_token.side_effect = RuntimeError

        response = self.api.client.post("/api/auth/verify")

        assert response.status_code == 503
        assert response.headers["cache-control"] == "no-store"

    def test_verify_returns_no_store_unauthorized_response(self) -> None:
        self.use_case.verify_access_token.side_effect = UnauthorizedError

        response = self.api.client.post("/api/auth/verify")

        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"
