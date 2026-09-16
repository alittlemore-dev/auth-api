.DEFAULT_GOAL := help

TEST_ENV_FILE ?= .env.test
TEST_ENV_OVERRIDES ?=

.PHONY: install
install:
	bash scripts/install.sh install

.PHONY: revision
revision:
	bash scripts/alembic.sh revision "$(message)"

.PHONY: migrate
migrate:
	bash scripts/alembic.sh migrate

.PHONY: downgrade
downgrade:
	bash scripts/alembic.sh downgrade

.PHONY: clean
clean:
	bash scripts/quality.sh clean

.PHONY: types
types:
	bash scripts/quality.sh types

.PHONY: bandit
bandit:
	bash scripts/quality.sh bandit

.PHONY: security-bandit
security-bandit:
	bash scripts/security.sh bandit

.PHONY: security-pip-audit
security-pip-audit:
	bash scripts/security.sh pip-audit

.PHONY: security
security:
	bash scripts/security.sh security

.PHONY: vulture
vulture:
	bash scripts/quality.sh vulture

.PHONY: fix
fix:
	bash scripts/quality.sh fix

.PHONY: format
format:
	bash scripts/quality.sh format

.PHONY: format-check
format-check:
	bash scripts/quality.sh format-check

# Usage: make lint-file file=src/core/auth/use_cases.py
.PHONY: lint-file
lint-file:
	bash scripts/quality.sh lint-file "$(file)"

.PHONY: ruff-check
ruff-check:
	bash scripts/quality.sh ruff-check

.PHONY: ruff-lint-check
ruff-lint-check:
	bash scripts/quality.sh ruff-lint-check

.PHONY: lint-check
lint-check:
	bash scripts/quality.sh lint-check

.PHONY: test
test:
	bash scripts/test.sh test "$(TEST_ENV_FILE)" "$(TEST_ENV_OVERRIDES)"

.PHONY: test-unit
test-unit:
	bash scripts/test.sh test-unit "$(TEST_ENV_FILE)" "$(TEST_ENV_OVERRIDES)"

.PHONY: test-integration
test-integration:
	bash scripts/test.sh test-integration "$(TEST_ENV_FILE)" "$(TEST_ENV_OVERRIDES)"

.PHONY: tests-coverage
tests-coverage:
	bash scripts/test.sh tests-coverage "$(TEST_ENV_FILE)" "$(TEST_ENV_OVERRIDES)"

.PHONY: quality
quality:
	bash scripts/quality.sh quality "$(TEST_ENV_FILE)" "$(TEST_ENV_OVERRIDES)"

.PHONY: lock
lock:
	bash scripts/install.sh lock



.PHONY: help
help:
	bash scripts/help.sh

.PHONY: tests tests-fast
tests: test
tests-fast: test-unit

.PHONY: test-env-up test-env-down
test-env-up:
	bash scripts/test_env.sh up
test-env-down:
	bash scripts/test_env.sh down

.PHONY: build
build:
	bash scripts/build.sh

.PHONY: lint-dockerfiles security-trivy-config security-docker-image publish-image
lint-dockerfiles:
	bash scripts/docker_lint.sh hadolint
security-trivy-config:
	bash scripts/trivy_scan.sh config "$(TRIVY_IMAGE)"
security-docker-image:
	bash scripts/docker_image_security.sh auth-api "$(IMAGE_TAG)" Dockerfile . "$(TRIVY_IMAGE)" "$(IMAGE_EXPORT_PATH)"
publish-image:
	bash scripts/publish_image.sh "$(LOCAL_IMAGE)" "$(IMAGE_NAME)" "$(IMAGE_TAG)"

TRIVY_IMAGE := docker.io/aquasec/trivy:0.70.0@sha256:be1190afcb28352bfddc4ddeb71470835d16462af68d310f9f4bca710961a41e
