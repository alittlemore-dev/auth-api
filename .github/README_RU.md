# auth-api

API авторизации и управления аккаунтами: PASETO-токены, сессии, роли и отзыв доступа.

## Технологии

Python 3.14 · uv · Litestar · Dishka · PostgreSQL · SQLAlchemy/Alembic · Valkey · TaskIQ · Argon2

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

[English](README.md)
