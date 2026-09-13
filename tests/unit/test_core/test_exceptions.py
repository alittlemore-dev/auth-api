from collections.abc import Iterable

import pytest
from verbose_http_exceptions.exc.base import BaseVerboseHTTPException

from core.auth.exceptions import ForbiddenError, UnauthorizedError, UserNotFoundError
from core.exceptions import EntryNotFoundError


def core_exception_classes() -> Iterable[type[Exception]]:
    return (
        EntryNotFoundError,
        UnauthorizedError,
        ForbiddenError,
        UserNotFoundError,
    )


@pytest.mark.parametrize("exception_class", core_exception_classes())
def test_core_exception_does_not_inherit_verbose_http_exception(
    exception_class: type[Exception],
) -> None:
    assert not issubclass(exception_class, BaseVerboseHTTPException)
