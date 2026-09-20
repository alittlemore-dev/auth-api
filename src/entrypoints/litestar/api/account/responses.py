from litestar import Response
from litestar.response import Stream

from core.account.avatar_schemas import CurrentAccountAvatarContent
from core.account.schemas import CurrentAccount
from entrypoints.litestar.api.account.schemas import CurrentAccountResponseSchema
from infra.config.constants import constants


def create_current_account_response(
    *,
    account: CurrentAccount,
) -> Response[CurrentAccountResponseSchema]:
    return Response(
        content=CurrentAccountResponseSchema.from_domain_schema(schema=account),
        headers={"Cache-Control": constants.auth.no_store_header_value},
    )


def create_current_account_avatar_response(*, result: CurrentAccountAvatarContent) -> Stream:
    return Stream(
        result.content,
        media_type=result.mime_type,
        headers={
            "Content-Disposition": 'inline; filename="avatar.webp"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": constants.auth.no_store_header_value,
        },
    )
