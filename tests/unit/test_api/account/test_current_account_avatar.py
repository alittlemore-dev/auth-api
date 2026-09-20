from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import codes

from core.account.avatar_schemas import (
    CurrentAccountAvatarContent,
    CurrentAccountAvatarMutationResult,
)
from core.account.exceptions import AccountAvatarNotFoundError
from core.auth.enums import RoleEnum
from tests.test_cases import ApiTestCase


async def avatar_chunks() -> AsyncIterator[bytes]:
    yield b"webp"
    yield b"-avatar"


class TestCurrentAccountAvatarAPI(ApiTestCase):
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container.get_current_account_use_case()

    def test_replaces_avatar_from_multipart_file(self) -> None:
        account = self.factory.core.current_account(
            username="test",
            role=RoleEnum.ADMIN,
            avatar_object_name="avatars/new.webp",
        )
        self.use_case.replace_avatar.return_value = CurrentAccountAvatarMutationResult(
            account=account,
            old_object_name="avatars/old.webp",
        )

        response = self.api.put_current_account_avatar(
            content=b"png-content",
            mime_type="image/png",
        )

        self.asserts.status(response=response, expected_status=codes.OK)
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json()["hasAvatar"] is True
        call = self.use_case.replace_avatar.call_args
        assert call.kwargs["username"] == "test"
        assert call.kwargs["upload"].content == b"png-content"
        assert call.kwargs["upload"].declared_mime_type == "image/png"

    def test_rejects_file_larger_than_five_mebibytes(self) -> None:
        response = self.api.put_current_account_avatar(
            content=b"x" * (5 * 1024 * 1024 + 1),
            mime_type="image/png",
        )

        assert response.status_code in {codes.BAD_REQUEST, codes.REQUEST_ENTITY_TOO_LARGE}
        self.use_case.replace_avatar.assert_not_called()

    def test_removes_avatar_and_returns_updated_account(self) -> None:
        account = self.factory.core.current_account(avatar_object_name=None)
        self.use_case.remove_avatar.return_value = CurrentAccountAvatarMutationResult(
            account=account,
            old_object_name="avatars/old.webp",
        )

        response = self.api.delete_current_account_avatar()

        self.asserts.status(response=response, expected_status=codes.OK)
        assert response.json()["hasAvatar"] is False

    def test_streams_private_avatar_with_security_headers(self) -> None:
        self.use_case.get_avatar.return_value = CurrentAccountAvatarContent(
            content=avatar_chunks(),
        )

        response = self.api.get_current_account_avatar()

        self.asserts.status(response=response, expected_status=codes.OK)
        assert response.content == b"webp-avatar"
        assert response.headers["Content-Type"].startswith("image/webp")
        assert response.headers["Content-Disposition"] == 'inline; filename="avatar.webp"'
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Cache-Control"] == "no-store"

    def test_avatar_routes_require_authentication(self) -> None:
        response = self.no_auth_api.get_current_account_avatar()

        self.asserts.status(response=response, expected_status=codes.UNAUTHORIZED)

    def test_returns_not_found_when_avatar_is_absent(self) -> None:
        self.use_case.get_avatar.side_effect = AccountAvatarNotFoundError

        response = self.api.get_current_account_avatar()

        self.asserts.status(response=response, expected_status=codes.NOT_FOUND)
