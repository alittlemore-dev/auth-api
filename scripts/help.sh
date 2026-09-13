#!/usr/bin/env bash
set -euo pipefail
printf '%-25s %s\n' \
    'install' 'Install Python dependencies.' \
    'tests / tests-fast' 'Run all tests / unit tests.' \
    'test-integration' 'Run PostgreSQL and migration tests.' \
    'tests-coverage' 'Run tests with coverage.' \
    'lint-check / types' 'Check formatting, lint and types.' \
    'security' 'Run Bandit and dependency audit.' \
    'build' 'Build the service image without starting it.' \
    'revision message="..."' 'Generate a migration against the configured database.' \
    'migrate / downgrade' 'Apply / roll back migrations against the configured database.' \
    'Runtime' 'Managed only by the sibling infra repository.'
