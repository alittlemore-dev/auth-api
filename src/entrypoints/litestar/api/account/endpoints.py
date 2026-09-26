from typing import Annotated

from backend_sdk import Principal
from dishka import FromDishka
from dishka.integrations.litestar import DishkaRouter
from litestar import Controller, Request, Response, delete, get, patch, put
from litestar.datastructures import State
from litestar.response import Stream

from core.account.clients import AccountAvatarClient
from core.account.use_cases import CurrentAccountUseCase
from core.auth.exceptions import UnauthorizedError
from core.auth.types import Token
from entrypoints.litestar.api.account.post_commit import register_account_avatar_cleanup
from entrypoints.litestar.api.account.responses import (
    create_current_account_avatar_response,
    create_current_account_response,
)
from entrypoints.litestar.api.account.schemas import (
    AccountAvatarUploadRequestSchema,
    AccountSettingsSchema,
    CurrentAccountResponseSchema,
    CurrentAccountUpdateRequestSchema,
)
from entrypoints.litestar.api.parameters import api_json_body, api_multipart_body
from infra.config.constants import constants
from infra.post_commit_actions import PostCommitActions


class AccountApiController(Controller):
    path = "/account"
    tags = ["account"]

    @get(
        "/me",
        name="current-user-account-api-handler",
        description="Get the authenticated user's private account profile.",
    )
    async def get_current_account(
        self,
        request: Request[Principal, Token | None, State],
        use_case: FromDishka[CurrentAccountUseCase],
    ) -> Response[CurrentAccountResponseSchema]:
        self._ensure_authenticated(request=request)
        account = await use_case.get_account(username=request.user.username)
        return create_current_account_response(account=account)

    @patch(
        "/me",
        name="update-current-user-account-api-handler",
        description="Update supplied fields of the authenticated user's private account profile.",
    )
    async def update_current_account(
        self,
        request: Request[Principal, Token | None, State],
        use_case: FromDishka[CurrentAccountUseCase],
        data: Annotated[
            CurrentAccountUpdateRequestSchema,
            api_json_body(
                title="Current account profile update",
                description="Only supplied fields are changed; explicit null clears a value.",
                examples=({"firstName": "Dmitriy", "gender": "male"},),
            ),
        ],
    ) -> Response[CurrentAccountResponseSchema]:
        self._ensure_authenticated(request=request)
        account = await use_case.update_account(
            username=request.user.username,
            params=data.to_domain_schema(),
        )
        return create_current_account_response(account=account)

    @put("/me/settings", name="replace-current-user-settings-api-handler")
    async def replace_settings(
        self,
        request: Request[Principal, Token | None, State],
        use_case: FromDishka[CurrentAccountUseCase],
        data: Annotated[
            AccountSettingsSchema,
            api_json_body(
                title="Account settings replacement",
                description="Replace all preferences; omitted fields use schema defaults.",
                examples=({"language": "en", "theme": "light", "telegramBots": {}},),
            ),
        ],
    ) -> Response[CurrentAccountResponseSchema]:
        if request.auth is None:
            raise UnauthorizedError
        account = await use_case.update_settings(
            username=request.user.username,
            settings=data.to_domain_schema(),
        )
        return create_current_account_response(account=account)

    @put(
        "/me/avatar",
        name="replace-current-user-account-avatar-api-handler",
        description="Replace the authenticated user's private avatar.",
        request_max_body_size=constants.account_avatar.max_source_bytes,
    )
    async def replace_current_account_avatar(
        self,
        request: Request[Principal, Token | None, State],
        use_case: FromDishka[CurrentAccountUseCase],
        avatar_client: FromDishka[AccountAvatarClient],
        post_commit_actions: FromDishka[PostCommitActions],
        data: Annotated[
            AccountAvatarUploadRequestSchema,
            api_multipart_body(
                title="Account avatar upload",
                description="JPEG, PNG, or WebP avatar up to 5 MiB.",
                examples=({"file": "avatar.png"},),
            ),
        ],
    ) -> Response[CurrentAccountResponseSchema]:
        self._ensure_authenticated(request=request)
        result = await use_case.replace_avatar(
            username=request.user.username,
            upload=await data.to_domain_schema(),
        )
        register_account_avatar_cleanup(
            old_object_name=result.old_object_name,
            client=avatar_client,
            post_commit_actions=post_commit_actions,
        )
        return create_current_account_response(account=result.account)

    @delete(
        "/me/avatar",
        name="delete-current-user-account-avatar-api-handler",
        description="Remove the authenticated user's private avatar.",
        status_code=200,
    )
    async def delete_current_account_avatar(
        self,
        request: Request[Principal, Token | None, State],
        use_case: FromDishka[CurrentAccountUseCase],
        avatar_client: FromDishka[AccountAvatarClient],
        post_commit_actions: FromDishka[PostCommitActions],
    ) -> Response[CurrentAccountResponseSchema]:
        self._ensure_authenticated(request=request)
        result = await use_case.remove_avatar(username=request.user.username)
        register_account_avatar_cleanup(
            old_object_name=result.old_object_name,
            client=avatar_client,
            post_commit_actions=post_commit_actions,
        )
        return create_current_account_response(account=result.account)

    @get(
        "/me/avatar",
        name="get-current-user-account-avatar-api-handler",
        description="Stream the authenticated user's private avatar.",
    )
    async def get_current_account_avatar(
        self,
        request: Request[Principal, Token | None, State],
        use_case: FromDishka[CurrentAccountUseCase],
    ) -> Stream:
        self._ensure_authenticated(request=request)
        return create_current_account_avatar_response(
            result=await use_case.get_avatar(username=request.user.username),
        )

    @staticmethod
    def _ensure_authenticated(
        *,
        request: Request[Principal, Token | None, State],
    ) -> None:
        if request.auth is None:
            raise UnauthorizedError


api_router = DishkaRouter("", route_handlers=[AccountApiController])
