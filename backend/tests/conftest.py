from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.config.settings import clear_settings_cache


@pytest.fixture(autouse=True)
def clear_settings_between_tests() -> Iterator[None]:
    clear_settings_cache()
    yield
    clear_settings_cache()
