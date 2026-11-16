from __future__ import annotations

import pytest

from crossview import registry


@pytest.fixture(autouse=True)
def clean_registry():
    registry.clear()
    yield
    registry.clear()


def test_register_and_build():
    @registry.register("matcher", "dummy")
    class Dummy:
        def __init__(self, value=1):
            self.value = value

    assert registry.available("matcher") == ["dummy"]
    assert registry.build("matcher", "dummy", value=7).value == 7


def test_duplicate_registration_is_rejected():
    @registry.register("matcher", "dummy")
    class Dummy:
        pass

    with pytest.raises(ValueError):

        @registry.register("matcher", "dummy")
        class Another:
            pass


def test_unknown_name_lists_available():
    with pytest.raises(KeyError, match="未注册"):
        registry.get("matcher", "missing")
