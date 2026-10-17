"""Adoption seam for the accepted query-conditioned geometry variant (v50 obligation 4).

The Frontier component ``frontier-query-conditioned-map-geometry`` was
independently accepted (audit ``CYCLE_38973386164_GATE.json`` PASS,
``safe_to_integrate=true``, accept commit ``be5eba7f``) with
``relevance_ordered`` the promoted, adoptable variant (22/33 frozen criteria,
zero regressions against the incumbent 16/33).  Its integration contract asks
Core Product to expose it behind the bundle seam behind a config flag.

These tests pin:
  * the flag parses (empty/incumbent/off -> incumbent; unknown -> error);
  * the variant is OFF by default, so the shipped map is unchanged;
  * when on, the variant rewrites ``x``/``y``/``cluster_id`` in the same shape
    ``qmap.build_map`` emits, validates as a bundle, and marks un-hydrated rows
    with the negative cluster ids that the renderer fix now paints neutral;
  * the metadata is recorded in provenance, never silently.

They are seam/shape assertions, never a map-quality or bar claim.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query import pipeline  # noqa: E402
from product.query.bundle import validate_bundle  # noqa: E402
from product.query.qmap_variants import (  # noqa: E402
    ADOPTABLE_VARIANT,
    GEOMETRY_VARIANT_ENV,
    apply_geometry_variant,
    selected_variant,
)

SERVE_PACKET = REPO_ROOT / "results" / "product" / "gate_packet" / "38839347028"
BUNDLE = SERVE_PACKET / "questions" / "de-kapitalverletzung.bundle.json"
pytestmark = pytest.mark.skipif(not BUNDLE.is_file(),
                                reason="served gate packet 38839347028 not present")


def _served() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def _product_bundle() -> dict:
    b = _served()
    return {"query": b["query"], "query_variants": b.get("query_variants") or [],
            "decisions": b["decisions"], "provenance": {}}


@pytest.mark.parametrize("value,expected", [
    ("", ""), ("incumbent", ""), ("off", ""), ("none", ""),
    ("relevance_ordered", "relevance_ordered"),
    ("hydrate_then_cluster", "hydrate_then_cluster"),
])
def test_selected_variant_parses(value, expected):
    assert selected_variant({GEOMETRY_VARIANT_ENV: value}) == expected


def test_unknown_variant_is_rejected_not_silently_ignored():
    with pytest.raises(ValueError):
        selected_variant({GEOMETRY_VARIANT_ENV: "made_up_geometry"})


def test_adoptable_variant_is_the_frontier_promoted_one():
    assert ADOPTABLE_VARIANT == "relevance_ordered"


def test_variant_is_off_by_default_and_map_component_stays_incumbent(monkeypatch):
    monkeypatch.delenv(GEOMETRY_VARIANT_ENV, raising=False)
    out = pipeline._map_bundle(_product_bundle(), 0.0, candidates=[])
    assert out["provenance"]["geometry_variant"] == "incumbent"
    assert out["provenance"]["map_component"] == "query-conditioned-tfidf-v45"
    assert validate_bundle(out) == []


def test_variant_rewrites_geometry_in_the_incumbent_shape(monkeypatch):
    monkeypatch.setenv(GEOMETRY_VARIANT_ENV, ADOPTABLE_VARIANT)
    out = pipeline._map_bundle(_product_bundle(), 0.0, candidates=[])
    assert validate_bundle(out) == []
    src = _served()
    assert len(out["decisions"]) == len(src["decisions"])
    assert out["provenance"]["geometry_variant"] == ADOPTABLE_VARIANT
    assert out["provenance"]["map_component"].endswith(ADOPTABLE_VARIANT)
    for d in out["decisions"]:
        assert isinstance(d["x"], float) and isinstance(d["y"], float)
        assert isinstance(d["cluster_id"], int)
        assert "is_outlier" in d
    # cluster records stay non-negative and contiguous-from-0 (legend safety)
    ids = sorted(c["cluster_id"] for c in out["clusters"])
    assert ids == list(range(len(ids)))
    for c in out["clusters"]:
        assert c["member_ids"] and len(c["member_ids"]) <= 50
        assert c["size"] >= len(c["member_ids"])


def test_variant_marks_unhydrated_rows_with_negative_ids():
    src = _served()
    decisions, clusters, meta = apply_geometry_variant(
        src["decisions"], src["clusters"], src["query"], ADOPTABLE_VARIANT,
        query_language="de")
    assert meta["name"] == ADOPTABLE_VARIANT
    assert meta["query_language"] == "de"
    negative = [d for d in decisions if d["cluster_id"] < 0]
    assert negative, "the relevance_ordered variant must expose unclustered context rows"
    for d in negative:
        assert d["unclustered"] is True
    # every negative id is unique (the frozen scorer's singleton-group contract)
    neg_ids = [d["cluster_id"] for d in negative]
    assert len(set(neg_ids)) == len(neg_ids)


def test_incumbent_request_returns_inputs_untouched():
    src = _served()
    decisions, clusters, meta = apply_geometry_variant(
        src["decisions"], src["clusters"], src["query"], "")
    assert meta == {"name": "incumbent"}
    assert decisions is src["decisions"] and clusters is src["clusters"]


def test_vendored_component_matches_its_recorded_provenance_hashes():
    """Tamper detection: the vendored bytes must match PROVENANCE.json.

    Byte-identity to the accepted mount was proven when the files were vendored;
    this test re-hashes the committed bytes so a later edit cannot silently
    change the component the frozen scores were computed on.
    """
    import hashlib

    root = REPO_ROOT / "product" / "vendored" / "qmap_geometry"
    meta = json.loads((root / "PROVENANCE.json").read_text(encoding="utf-8"))
    assert meta["promoted_variant"] == ADOPTABLE_VARIANT
    assert meta["frozen_geometry_rules_sha256"].startswith("a7452748")
    for rel, rec in meta["vendored_files"].items():
        digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        assert digest == rec["sha256"], f"vendored {rel} drifted from provenance"
        assert rec["matches_accepted_source"] is True
