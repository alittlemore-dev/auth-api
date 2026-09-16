# auth-api

Authentication and account management API: PASETO tokens, sessions, roles and access revocation.

[Russian version](./README_RU.md)

| Category | Technologies |
| --- | --- |
| Coverage | ![coverage-backend](./badges/coverage-backend.svg) |
| Backend | ![python](./badges/python.svg) ![litestar](./badges/litestar.svg) ![async](./badges/async.svg) ![pydantic](./badges/pydantic.svg) ![dishka](./badges/dishka.svg) ![taskiq](./badges/taskiq.svg) ![paseto](./badges/paseto.svg) ![argon2](./badges/argon2.svg) |
| Database | ![postgresql](./badges/postgresql.svg) ![sqlalchemy](./badges/sqlalchemy.svg) ![alembic](./badges/alembic.svg) |
| Cache | ![valkey](./badges/valkey.svg) |
| Testing | ![pytest](./badges/pytest.svg) |
| DevOps | ![docker](./badges/docker.svg) ![nginx](./badges/nginx.svg) ![docker-compose](./badges/docker-compose.svg) |
| Quality | ![ruff](./badges/ruff.svg) ![mypy](./badges/mypy.svg) ![bandit](./badges/bandit.svg) ![pip-audit](./badges/pip-audit.svg) ![trivy](./badges/trivy.svg) ![hadolint](./badges/hadolint.svg) ![dockle](./badges/dockle.svg) ![vulture](./badges/vulture.svg) |
| Logging | ![structlog](./badges/structlog.svg) ![ecs-logging](./badges/ecs-logging.svg) ![sentry](./badges/sentry.svg) |
| Architecture | ![clean-architecture](./badges/clean-architecture.svg) ![type-safe](./badges/type-safe.svg) |
| Tools | ![uv](./badges/uv.svg) ![granian](./badges/granian.svg) |
| CI/CD | ![github-actions](./badges/github-actions.svg) ![dependabot](./badges/dependabot.svg) |

## Commands

```sh
make install
make tests-fast          # unit tests
make tests               # all tests; test PostgreSQL starts automatically
make tests-coverage
make lint-check types
make security
make build               # image only; does not start the service
make revision message="describe change"
```

Runtime, environment configuration, secrets and migrations are managed by the separate
[infra repository](https://github.com/alittlemore-dev/infra). This repository contains only a test Compose.
Container interface: port 8080, `/api/auth/healthcheck/ready`, `start_application.sh`
with `init`, `run`, `taskiq-worker` and `taskiq-scheduler`.
CI publishes the checked main-branch image to `ghcr.io/alittlemore-dev/auth-api` with SHA and `latest` tags.
