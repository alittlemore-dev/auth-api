# auth-api

API авторизации и управления аккаунтами: PASETO-токены, сессии, роли и отзыв доступа.

[English version](./README.md)

| Категория | Технологии |
| --- | --- |
| Покрытие | ![coverage-backend](./badges/coverage-backend.svg) |
| Backend | ![python](./badges/python.svg) ![litestar](./badges/litestar.svg) ![async](./badges/async.svg) ![pydantic](./badges/pydantic.svg) ![dishka](./badges/dishka.svg) ![taskiq](./badges/taskiq.svg) ![paseto](./badges/paseto.svg) ![argon2](./badges/argon2.svg) |
| База данных | ![postgresql](./badges/postgresql.svg) ![sqlalchemy](./badges/sqlalchemy.svg) ![alembic](./badges/alembic.svg) |
| Кэш | ![valkey](./badges/valkey.svg) |
| Тестирование | ![pytest](./badges/pytest.svg) |
| DevOps | ![docker](./badges/docker.svg) ![nginx](./badges/nginx.svg) ![docker-compose](./badges/docker-compose.svg) |
| Качество | ![ruff](./badges/ruff.svg) ![mypy](./badges/mypy.svg) ![bandit](./badges/bandit.svg) ![pip-audit](./badges/pip-audit.svg) ![trivy](./badges/trivy.svg) ![hadolint](./badges/hadolint.svg) ![dockle](./badges/dockle.svg) ![vulture](./badges/vulture.svg) |
| Логирование | ![structlog](./badges/structlog.svg) ![ecs-logging](./badges/ecs-logging.svg) ![sentry](./badges/sentry.svg) |
| Архитектура | ![clean-architecture](./badges/clean-architecture.svg) ![type-safe](./badges/type-safe.svg) |
| Инструменты | ![uv](./badges/uv.svg) ![granian](./badges/granian.svg) |
| CI/CD | ![github-actions](./badges/github-actions.svg) ![dependabot](./badges/dependabot.svg) |

## Команды

```sh
make install
make tests-fast          # unit-тесты
make tests               # все тесты; тестовая PostgreSQL запускается автоматически
make tests-coverage
make lint-check types
make security
make build               # только сборка образа, без запуска сервиса
make revision message="описание изменения"
```

Запуск, окружение, секреты и миграции управляются отдельным
[репозиторием infra](https://github.com/alittlemore-dev/infra). Здесь оставлен только тестовый Compose.
Контракт контейнера: порт 8080, `/api/auth/healthcheck/ready`, `start_application.sh`
с командами `init`, `run`, `taskiq-worker`, `taskiq-scheduler`.
CI публикует проверенный образ основной ветки в `ghcr.io/alittlemore-dev/auth-api` с тегами SHA и `latest`.
