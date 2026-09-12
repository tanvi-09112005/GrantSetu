"""Guardrails for the curated grants CSV.

There is deliberately no CSV in the repo right now. The original one was written
from model memory rather than from a source, and was quarantined on 7 Sep 2026 --
see docs/data-sources.md. These tests skip until a real, sourced CSV replaces it,
then enforce the invariants the loader and the eligibility engine depend on.
"""

from __future__ import annotations

import pytest

from scripts.seed_grants import DEFAULT_CSV, load_rows

VALID_FUNDER_TYPES = {"govt", "csr", "foundation", "international"}

pytestmark = pytest.mark.skipif(
    not DEFAULT_CSV.exists(),
    reason=f"no curated grants CSV at {DEFAULT_CSV} yet -- see docs/data-sources.md",
)


def test_seed_csv_meets_the_week_one_target():
    rows = load_rows(DEFAULT_CSV)
    # Week-1 checklist: 20+ real entries.
    assert len(rows) >= 20, f"only {len(rows)} seed grants"


def test_seed_rows_are_well_formed():
    for row in load_rows(DEFAULT_CSV):
        assert row["title"], "row with no title"
        assert row["funder_name"], f"{row['title']}: no funder"
        assert row["funder_type"] in VALID_FUNDER_TYPES, f"{row['title']}: bad funder_type"
        assert row["sectors"], f"{row['title']}: no sectors -- discovery filters on these"
        assert row["source_url"], f"{row['title']}: no source_url -- needed to verify it"


def test_funder_title_pairs_are_unique():
    """The upsert key. A collision here silently collapses two schemes into one."""
    keys = [(r["funder_name"], r["title"]) for r in load_rows(DEFAULT_CSV)]
    assert len(keys) == len(set(keys)), "duplicate (funder_name, title) in the seed CSV"


def test_every_row_is_marked_verified():
    """A row nobody checked against its source must not reach the eligibility engine.

    The rules engine is deterministic, so an unverified requires_12a flag becomes
    a confidently wrong verdict rather than a soft one.
    """
    unverified = [r["title"] for r in load_rows(DEFAULT_CSV) if not r["verified"]]
    assert not unverified, f"{len(unverified)} unverified rows, e.g. {unverified[:3]}"
