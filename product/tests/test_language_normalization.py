"""Language-field normalization on the product decision row.

Regression tests for D1 of the accepted audit record
``results/audit/product/CYCLE_39909013473_GATE.json``:

    Default decision.language to 'und' when null (5 decisions in fixture
    bundle have null language; breaks langFilter UI)

The defect was real on the audit's own reproduction path: the fixture replay
used by ``/api/query/start`` returned five rows whose upstream ``language`` was
``null``.  ``product/static/query.html`` filters with
``d.language !== langFilter``, so a null row can never be selected by any
specific language while it silently disappears from every filtered view.

These tests are offline and deterministic.  They assert the normalization at
the two levels that matter: the pure row assembler, and the bundle the shipped
fixture-mode pipeline actually returns.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
sys.path.insert(0, str(PRODUCT))
sys.path.insert(0, str(ROOT))

from query.bundle import validate_bundle
from query.pipeline import _candidate_to_product, run_query_initial

QUERY = "Kündigung Mietvertrag Mietrecht"


def _bundle(*languages):
    return {
        "query": "language fixture",
        "candidates": [
            {"decision_id": f"row_{i}", "language": language}
            for i, language in enumerate(languages)
        ],
    }


def test_null_and_empty_language_become_und():
    out = _candidate_to_product(_bundle(None, "", "   "))
    assert [d["language"] for d in out["decisions"]] == ["und", "und", "und"]


def test_known_language_is_lowercased_not_invented():
    out = _candidate_to_product(_bundle("FR", "de", "It"))
    assert [d["language"] for d in out["decisions"]] == ["fr", "de", "it"]


def test_other_valid_iso_code_survives_and_junk_becomes_und():
    out = _candidate_to_product(_bundle("rm", 123, None, "not-a-language"))
    assert [d["language"] for d in out["decisions"]] == ["rm", "und", "und", "und"]


def test_fixture_map_has_no_null_languages_and_stays_renderable():
    bundle = run_query_initial(QUERY, top_n=100, retrieval_mode="fixture")
    assert validate_bundle(bundle) == []
    assert bundle["decisions"]
    assert all(isinstance(d.get("language"), str) and d["language"] for d in bundle["decisions"])
    assert all(d["language"] in {"de", "fr", "it", "und"} for d in bundle["decisions"])
    # The audit's observed case: this fixture has undetermined rows.  They must
    # now carry the honest sentinel rather than None.
    assert any(d["language"] == "und" for d in bundle["decisions"])


def test_language_filter_offers_the_undetermined_bucket():
    html = (PRODUCT / "static" / "query.html").read_text(encoding="utf-8")
    assert 'id="langFilter"' in html
    assert '<option value="und">' in html
