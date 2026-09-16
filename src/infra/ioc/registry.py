from collections.abc import Iterable

from dishka import Provider
from dishka.integrations.litestar import LitestarProvider

from infra.ioc.prodivers.account_provider import UserAccountProvider
from infra.ioc.prodivers.auth_provider import AuthProvider
from infra.ioc.prodivers.database_provider import DatabaseProvider
from infra.ioc.prodivers.general_provider import GeneralProvider
from infra.ioc.prodivers.healthcheck_provider import HealthcheckProvider


def get_providers() -> Iterable[Provider]:
    return (
        GeneralProvider(),
        DatabaseProvider(),
        LitestarProvider(),
        UserAccountProvider(),
        AuthProvider(),
        HealthcheckProvider(),
    )
