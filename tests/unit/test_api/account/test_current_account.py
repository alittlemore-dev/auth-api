import pytest_asyncio
from httpx import codes

from core import schemas as core_schemas
from core.account.enums import GenderEnum
from core.account.schemas import CurrentAccountUpdateParams
from core.auth.enums import RoleEnum
from core.schemas import Secret
from entrypoints.litestar.api.account.schemas import CurrentAccountUpdateRequestSchema
from entrypoints.litestar.api.accounts.schemas import ManagedAccountResponseSchema
from tests.test_cases import ApiTestCase


class TestCurrentAccountAPI(ApiTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container.get_current_account_use_case()

    def test_gets_private_current_account(self) -> None:
        self.use_case.get_account.return_value = self.factory.core.current_account(
            username="test",
            role=RoleEnum.ADMIN,
            first_name="Dmitriy",
            last_name="Lunev",
            middle_name=None,
            gender=GenderEnum.MALE,
            avatar_object_name="test/avatar.webp",
        )

        response = self.api.get_current_account()

        self.asserts.status(response=response, expected_status=codes.OK)
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json() == {
            "username": "test",
            "role": "admin",
            "firstName": "Dmitriy",
            "lastName": "Lunev",
            "middleName": None,
            "gender": "male",
            "hasAvatar": True,
            "settings": {"language": "en", "theme": "light"},
        }
        self.use_case.get_account.assert_called_once_with(username="test")

    def test_patches_exactly_supplied_fields(self) -> None:
        self.use_case.update_account.return_value = self.factory.core.current_account(
            username="test",
            role=RoleEnum.ADMIN,
            first_name="Dmitriy",
            last_name=None,
        )
        response = self.api.patch_current_account(
            data={"firstName": "  Dmitriy  ", "lastName": None},
        )

        self.asserts.status(response=response, expected_status=codes.OK)
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json()["firstName"] == "Dmitriy"
        self.use_case.update_account.assert_called_once_with(
            username="test",
            params=CurrentAccountUpdateParams(
                first_name=Secret("Dmitriy"),
                last_name=None,
            ),
        )

    def test_uses_unset_for_omitted_patch_fields(self) -> None:
        params = CurrentAccountUpdateRequestSchema.model_validate(
            {"firstName": "Dmitriy", "lastName": None},
        ).to_domain_schema()

        assert params.first_name == Secret("Dmitriy")
        assert params.last_name is None
        assert params.middle_name is core_schemas.UNSET
        assert params.gender is core_schemas.UNSET
        assert not hasattr(params, "fields")

    def test_accepts_one_hundred_characters_after_trimming(self) -> None:
        name = "x" * 100
        self.use_case.update_account.return_value = self.factory.core.current_account(
            first_name=name,
        )

        response = self.api.patch_current_account(data={"firstName": f" {name} "})

        self.asserts.status(response=response, expected_status=codes.OK)

    def test_rejects_invalid_gender(self) -> None:
        response = self.api.patch_current_account(data={"gender": "unknown"})

        self.asserts.status(response=response, expected_status=codes.BAD_REQUEST)
        self.use_case.update_account.assert_not_called()

    def test_rejects_overlong_name(self) -> None:
        response = self.api.patch_current_account(data={"firstName": "x" * 101})

        self.asserts.status(response=response, expected_status=codes.BAD_REQUEST)
        self.use_case.update_account.assert_not_called()

    def test_requires_authentication(self) -> None:
        response = self.no_auth_api.get_current_account()

        self.asserts.status(response=response, expected_status=codes.UNAUTHORIZED)

    def test_legacy_base_endpoint_is_removed(self) -> None:
        response = self.api.client.get("/api/auth/account/base")

        self.asserts.status(response=response, expected_status=codes.NOT_FOUND)

    def test_managed_account_contract_does_not_expose_profile_fields(self) -> None:
        assert set(ManagedAccountResponseSchema.model_fields) == {"username", "role", "is_active"}

    def test_replaces_settings(self) -> None:
        self.use_case.update_settings.return_value = self.factory.core.current_account()
        response = self.api.client.put(
            "/api/auth/account/me/settings",
            json={"language": "ru", "theme": "dark"},
        )
        assert response.status_code == codes.OK
        assert response.headers["Cache-Control"] == "no-store"
        params = self.use_case.update_settings.call_args.kwargs
        assert params["username"] == "test"
        assert params["settings"].language == "ru"
        assert params["settings"].theme == "dark"

    def test_settings_requires_authentication(self) -> None:
        response = self.no_auth_api.client.put("/api/auth/account/me/settings", json={})
        assert response.status_code == codes.UNAUTHORIZED

    def test_settings_rejects_null(self) -> None:
        response = self.api.client.put("/api/auth/account/me/settings", json={"theme": None})
        assert response.status_code == codes.BAD_REQUEST

    def test_settings_omitted_fields_use_defaults(self) -> None:
        self.use_case.update_settings.return_value = self.factory.core.current_account()
        response = self.api.client.put("/api/auth/account/me/settings", json={"theme": "dark"})
        assert response.status_code == codes.OK
        settings = self.use_case.update_settings.call_args.kwargs["settings"]
        assert settings.language == "en"
        assert settings.theme == "dark"

    def test_settings_rejects_invalid_values(self) -> None:
        for data in (
            {"language": "fr"},
            {"theme": "system"},
            {"language": None},
            {"unknown": True},
        ):
            response = self.api.client.put("/api/auth/account/me/settings", json=data)
            assert response.status_code == codes.BAD_REQUEST
        self.use_case.update_settings.assert_not_called()
