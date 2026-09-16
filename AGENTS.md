# Auth API

## Ownership and scope

- This repository owns the authentication/account service extracted from competency-trainer.
- Keep core/auth and core/account, PostgreSQL users/sessions, Valkey revocations, and TaskIQ session cleanup here.
- Application-specific data, frontend, public edge, and integrated deployment belong to their owning repositories.
- Do not change sibling repositories or migrate existing user data without an explicit request.

## Architecture and security

- Preserve Python 3.14, uv, Litestar, Dishka, SQLAlchemy/Alembic, PostgreSQL, Valkey, and TaskIQ.
- Preserve PASETO bearer access tokens, Argon2 password hashing, session renewal/revocation,
  Secure/HttpOnly/SameSite refresh cookies, CSRF headers and Fetch Metadata checks.
- Keep existing role and owner protections. Changes to eligibility or app-specific authorization
  require an explicit policy decision; extraction alone must not change them.
- Keep auth/account and session responses uncached. Never log credentials, hashes, keys, or tokens.
- The complete public service namespace is `/api/auth`: authentication lives directly under it,
  account endpoints under `/api/auth/account/*`, administrative controls under
  `/api/auth/admin/*`, health under `/api/auth/healthcheck*`, and docs under `/api/auth/docs`.
- Configuration comes from environment-backed settings. Never commit real secrets.
  Dedicated deterministic test credentials must remain test-only.
- Runtime, dev/production environment, secrets, network exposure and deployments are owned only by
  the sibling infra repository. Do not add a standalone service Compose or local server launcher here.
- Keep the Python application at repository root (src/, tests/, scripts/, pyproject.toml, Dockerfile).
  A Compose file in this repository may start only isolated test dependencies.
- Keep READMEs short: purpose, technology list, essential commands and a link to infra.

## Working agreements

- Prefer copying and adapting existing code over reimplementing behavior.
- Do not perform mutating git actions unless explicitly requested.
- Use a concise conversational plan for multi-step changes; do not create workflow-only documents.
- Use Make targets for installation, tests, lint, builds, migrations, and local runs. Keep Makefiles
  thin; put command logic in the owning scripts directory.
- Test commands must prepare dependencies and isolated test services, and clean up only owned resources.
- Verify changed behavior with focused tests, broaden checks for cross-cutting changes, and report
  actual results and blocked checks. Do not change unrelated dependencies to remove existing warnings.
- Generate Alembic revisions through the Make autogeneration target before refining them.
- Keep core pure Python; follow nested instructions for core, PostgreSQL, and tests.
- Keep AGENTS.md in English and obtain explicit approval before changing agent guidance.
- TODOs contain only finite actions; durable rules belong in AGENTS.md. Do not expand existing TODO scope.
- Change lockfiles only for intentional dependency changes and update retained version badges accordingly.
- Use official documentation when library behavior is uncertain or version-sensitive.
## Application Code

## Code Style

- Use `pyproject.toml` as the source for formatting, lint, and typing configuration.
- No docstrings unless interface is non-obvious from types
- Comments: only for non-obvious WHY, never WHAT
- No Python class name may start with a leading underscore anywhere in this repository, including
  production code, tests, migrations, scripts, and performance tooling; there are no exceptions.
  Give every class a clear public name and control module exports through import/export boundaries
  rather than private class naming.
- Keep environment/configuration values, shared operational limits, and configurable policy values
  in `src/infra/config/constants.py`. Domain invariants, parser-specific rules, adapter-local
  mappings, and other implementation constants belong with the domain, parser, or adapter that owns
  them. Core code must receive infrastructure-owned configuration through schemas, constructor
  parameters, or IOC wiring, while infra and entrypoint code may import `constants` directly when
  that layer owns the wiring.

## Layers

| Layer | Path | Responsibility |
|---|---|---|
| Domain | `src/core/` | Business logic. Pure Python only. |
| Persistence | `src/infra/postgresql/` | SQLAlchemy models + concrete storage implementations |
| Interface | `src/entrypoints/litestar/` | HTTP handlers, API endpoints, auth middleware |
| DI | `src/infra/ioc/` | Dishka providers. Wiring only, no logic |
| Config | `src/infra/config/` | Pydantic settings, logging setup |

## Tooling Boundaries

- Keep test-only helpers under `tests/`, not application source.

## Operation Boundaries

- Do not model entity mutation methods as `upsert` when the behavior can create, update,
  delete, or otherwise mutate different state. Use explicit operation-specific names and methods
  such as `create_*`, `update_*`, `delete_*`, `publish_*`, or `set_*` so callers cannot
  accidentally trigger broader behavior than intended.

## Business Logic Boundaries

- Business-operation orchestration and flows that coordinate multiple storages belong in domain use
  cases under `src/core/**/use_cases.py`. Invariants and behavior owned by one entity or
  value object belong on that domain object. Shared cross-use-case domain behavior belongs in an
  explicit core domain service.
- When an existing use-case operation already represents the business action, reuse it with
  explicit parameters that model transport/auth/quota differences instead of adding a parallel
  use-case method for the same action. Do not use sentinel values such as arbitrarily large quotas;
  make the variation explicit in the parameter contract.
- API controllers, Litestar handlers, API schemas, Dishka providers, storages, ORM models, settings,
  event dispatchers, and infrastructure adapters must not own business decisions. They may validate
  transport shape, map data, wire dependencies, persist/load data, or call a use case.
- Request-level access checks and input checks that can be decided before entering a use case should
  live at the Litestar boundary, preferably as guards or `Provide` dependencies. Do not hide those
  checks in controller helper functions.
- Do not add private module-level helper functions in backend source to hold business behavior.
  Put the behavior on the real owning class or use case instead.
- Do not create classes that exist only to wrap one or more `@classmethod` helpers. A class must
  represent a real domain concept, interface, adapter, provider, guard, schema, model, or service.
- Put reusable domain parsers in the domain `parsers.py`, reader interfaces in `readers.py`,
  parser/request DTOs and rule objects in `schemas.py`, and parser/domain errors in
  `exceptions.py`. Do not name domain files after one narrow feature when an existing standard
  file type fits the object.
- Top-level functions are acceptable when the framework or tool naturally requires them or when a
  callable class would add ceremony without improving ownership: app factories, Litestar lifespan
  hooks, CLI commands, Alembic migration functions, and small pure infrastructure entrypoints.
- When choosing between a function and a method, prefer the shape that expresses real ownership.
  Do not move code into a class solely to satisfy a stylistic ban on functions.
- Prefer moving meaningful multi-parameter object creation into methods on the object that owns
  that creation logic, or into the owning use case when the object is an aggregate/read model.
  Do not extract creation solely for tiny objects with too few fields to justify the extra method.
- Storage adapters may filter, group, paginate, count, and otherwise aggregate data when those
  operations are part of the database query shape. They should return persisted entities or narrow
  row/query results. Product-facing composition, cross-storage assembly, and business decisions must
  remain in core use cases or on the owning core object. Simple containers such as
  `Tags(values=...)` and `ExternalResources(values=...)` may remain at storage boundaries when they
  only wrap loaded values.

## HTTP and Schemas

- Controllers must receive dependencies through `FromDishka[...]`, typed as the concrete use case
  class registered in Dishka.
- Endpoint/controller modules must not define `@staticmethod`, `@classmethod`, or private helper
  methods for request-derived values or parameter assembly when a Litestar `Provide` dependency can
  own that logic. Put those dependencies in a neighboring `dependencies.py` module.
- Assemble query/path/header/cookie parameter objects in neighboring `dependencies.py` Litestar
  `Provide` dependencies when this keeps handlers focused on their HTTP contract.
- API schemas must inherit from the shared schema bases and map explicitly between API, ORM, and
  core representations. Use `to_domain_schema` for conversion to the same core concept and
  `from_domain_schema` for conversion from it when the method signature identifies the exact
  source/target type. Use a specific semantic conversion name only when the conversion changes the
  concept, such as attached resource -> plain external resource.
- Do not use `cast("Self", ...)` to suppress classmethod return-type errors. Use an accurately typed
  constructor or an explicit concrete return type.
- Do not pass Pydantic API schemas, SQLAlchemy models, or Litestar types into the core layer.

## Response Caching

- Auth, account, and session responses must remain uncached.

## Background Tasks

- TaskIQ entrypoints live under `src/entrypoints/taskiq/`.
- Keep `src/entrypoints/taskiq/broker.py` as the shared broker and
  `src/entrypoints/taskiq/worker.py` as the worker/scheduler registry entrypoint.
- Put domain task wrappers in domain packages such as
  `src/entrypoints/taskiq/auth/tasks.py`; do not collect unrelated tasks in a
  top-level `tasks.py`.
- Background tasks are internal worker/scheduler processes, not HTTP handlers.
- Run exactly one TaskIQ scheduler process in deployment. Scale TaskIQ workers when more background
  execution capacity is needed.
- TaskIQ result metadata is operational and ephemeral in Valkey unless a future durable task
  history/auditing design explicitly chooses another backend.

## Persistence

- SQLAlchemy models and database storages live only under `src/infra/postgresql/`.
- Database storages return domain schemas, not ORM models.
- Storages may `flush`, but must not `commit`; transaction ownership belongs to the DI/session provider.
- Every DB model change must include a matching Alembic migration.

## Dependency Injection

- Dishka providers are wiring only: no business logic, DB queries, or external side effects.
- Use `Scope.APP` only for stateless singleton-safe dependencies; use `Scope.REQUEST` for sessions, storages, and use cases.
