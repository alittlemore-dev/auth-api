from collections.abc import Generator

import pytest

from infra.postgresql.utils import downgrade, migrate
from tests.helpers.assertions import AssertsHelper


@pytest.fixture
def migrated_to_0001() -> Generator[None]:
    migrate(revision="0001")
    yield
    downgrade(revision="base")


@pytest.fixture
def migration_asserts() -> AssertsHelper:
    return AssertsHelper()
