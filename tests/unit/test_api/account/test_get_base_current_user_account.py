from httpx import codes

from core.auth.enums import RoleEnum
from core.auth.schemas import JwtUser
from tests.test_cases import ApiTestCase
from tests.unit.mocks.providers.auth import mock_authentication_result


class TestGetBaseCurrentUserAccountAPI(ApiTestCase):
    async def test_get_base_current_user_account(self) -> None:
        response = self.api.get_get_base_current_user_account()
        assert response.status_code == codes.OK
        assert response.json() == {"username": "test", "role": "admin"}

    async def test_get_base_current_user_account_returns_moderator_role(self) -> None:
        authentication_use_case = await self.container.get_auth_use_case()
        authentication_use_case.authenticate.return_value = mock_authentication_result(
            JwtUser(username="moderator", role=RoleEnum.MODERATOR)
        )

        response = self.api.get_get_base_current_user_account()

        assert response.status_code == codes.OK
        assert response.json() == {"username": "moderator", "role": "moderator"}

    async def test_get_base_current_user_account_returns_owner_role(self) -> None:
        authentication_use_case = await self.container.get_auth_use_case()
        authentication_use_case.authenticate.return_value = mock_authentication_result(
            JwtUser(username="owner", role=RoleEnum.OWNER)
        )

        response = self.api.get_get_base_current_user_account()

        assert response.status_code == codes.OK
        assert response.json() == {"username": "owner", "role": "owner"}
