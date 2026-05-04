"""Test-suite-wide fixtures.

The Django ``locmem`` cache backend is process-local, so values written by
one test linger into the next. ``_download_series`` (cached for one hour
in production) and ``_csv_preview`` would otherwise see stale values when
two tests use the same ``dataset.pk`` / ``DataFile.pk``. Wipe between
tests so each starts from a cold cache.
"""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()
