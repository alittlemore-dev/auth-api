# auth-api

Authentication and account management API: PASETO tokens, sessions, roles and access revocation.

## Stack

Python 3.14 · uv · Litestar · Dishka · PostgreSQL · SQLAlchemy/Alembic · Valkey · TaskIQ · Argon2

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

[Русский](README_RU.md)
