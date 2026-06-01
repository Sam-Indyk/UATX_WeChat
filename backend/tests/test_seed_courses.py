"""Sanity-check the UATX course catalog used by the 0002 seed migration.

The catalog itself isn't exercised by other tests because conftest.py
TRUNCATEs the courses table before each test — but a typo in the seed
data still ships to prod via the migration, so we guard it here.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest


_MIGRATION_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "0002_seed_courses.py"
)


@pytest.fixture(scope="module")
def courses() -> tuple[tuple[str, str], ...]:
    spec = importlib.util.spec_from_file_location("seed_courses_mig", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.COURSES


def test_catalog_is_substantial(courses):
    # If this drops, someone probably mid-edited the seed by accident.
    assert len(courses) >= 150


def test_codes_are_unique(courses):
    codes = [c for c, _ in courses]
    assert len(codes) == len(set(codes))


def test_fields_fit_schema(courses):
    # courses.code is VARCHAR(20), courses.title is VARCHAR(200) per 0001_initial.
    for code, title in courses:
        assert 1 <= len(code) <= 20, f"Bad code length: {code!r}"
        assert 1 <= len(title) <= 200, f"Bad title length for {code}: {title!r}"


def test_all_centers_represented(courses):
    prefixes = {c.split(" ", 1)[0] for c, _ in courses}
    # Intellectual Foundations + 3 Centers + Polaris must all be in the catalog.
    assert {"INF", "ALT", "EPH", "STM", "POL"}.issubset(prefixes)
