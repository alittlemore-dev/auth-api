from litestar import Router

from entrypoints.litestar.api.account.endpoints import api_router as account_router
from entrypoints.litestar.api.accounts.endpoints import admin_router as accounts_admin_router
from entrypoints.litestar.api.admin_tools.endpoints import admin_router as admin_tools_router
from entrypoints.litestar.api.auth.endpoints import api_router as auth_router
from entrypoints.litestar.api.healthcheck.endpoints import api_router as healthcheck_router

admin_api_router = Router(
    "/admin",
    route_handlers=[
        accounts_admin_router,
        admin_tools_router,
    ],
    tags=["admin api"],
    include_in_schema=False,
)

api_router = Router(
    "/api/auth",
    route_handlers=[
        healthcheck_router,
        auth_router,
        account_router,
        admin_api_router,
    ],
    tags=["api"],
)
