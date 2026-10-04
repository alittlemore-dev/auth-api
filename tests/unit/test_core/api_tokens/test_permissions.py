from core.api_tokens.services import ApiPermissionRegistry
from core.auth.enums import RoleEnum
from core.auth.schemas import BaseUser


def test_public_interaction_scopes_do_not_grant_editorial_permissions() -> None:
    registry = ApiPermissionRegistry()
    user_codes = registry.codes_for(user=BaseUser(username="user", role=RoleEnum.USER))
    assert {"competency.articles.record_view", "competency.matrix.suggest"} <= user_codes
    assert "competency.articles.create" not in user_codes
    assert "competency.matrix.create" not in user_codes
    assert "auth.accounts.password" not in user_codes
    assert "workspace.telegram.create" in user_codes
    assert "workspace.tools.manage" not in user_codes
    moderator_codes = registry.codes_for(
        user=BaseUser(username="moderator", role=RoleEnum.MODERATOR)
    )
    assert {"competency.articles.create", "competency.matrix.publish"} <= moderator_codes
    assert "competency.tools.manage" not in moderator_codes
    assert (
        registry.codes_for(user=BaseUser(username="anonymous", role=RoleEnum.ANON)) == frozenset()
    )
