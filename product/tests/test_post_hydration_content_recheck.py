"""Post-hydration content recheck — residual of the v68 rejection/incumbent leg.

Gap this file pins
------------------
Stage 1 selects a verbatim span BEFORE the pool counter-surface scan hydrates
``full_text``.  Frozen grounding searches ``full_text`` first, so hydration can
move the same quote from ``snippet`` into the letterhead zone, turning a
content-sound verified row into a D2 defect that stage 1 could not observe.
``_content_rejection_sweep`` skips rows carrying a ``counter_evidence_span``
record, and stage 2 previously never re-filtered at all, so the defective row
survived with ``counter_evidence_verified=True`` on the shipped offline/server
path.  The fix re-applies the UNCHANGED frozen D1-D4 predicates after stage 2
to every still-verified row, including span-owned ones.

No frozen gate, rubric, threshold or bar is edited by this module.
"""
from __future__ import annotations

import copy
import glob
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_evidence_span as ces  # noqa: E402


QUOTE = "Tribunal fédéral, consideration de bail et d'entretien"
SOUND_BUNDLE = (
    "results/product/offline_slice/20261023T121512Z/"
    "corporate-criminal-liability.bundle.json"
)
SOUND_ID = "bstger_SK.2023.49"


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _clean_snippet_row() -> dict:
    return {
        "decision_id": "synthetic-hydration-recheck",
        "query": "bail entretien",
        "language": "fr",
        "counter_status": "candidate-limiting",
        "counter_evidence": QUOTE,
        "counter_evidence_verified": True,
        "snippet": QUOTE,
        "full_text": "",
        "adversarial_retrieval_signal": True,
        "x": 0.25,
        "y": -0.5,
        "cluster_id": 3,
        "rank": 7,
    }


def _stage1_with_clean_incumbent() -> dict:
    row = _clean_snippet_row()
    out = ces.apply_verified_span_selection(
        {"query": "bail entretien", "decisions": [row], "provenance": {}},
        mode="select",
    )
    result = out["decisions"][0]
    # Precondition: stage 1 saw a content-sound, snippet-grounded incumbent.
    assert result["counter_evidence_verified"] is True
    assert ces.frozen_content_defects(result["counter_evidence"], result) == []
    assert result.get("counter_evidence_span")
    return out


def _hydrate_into_letterhead(bundle: dict) -> dict:
    out = copy.deepcopy(bundle)
    row = out["decisions"][0]
    row["full_text"] = f"Cour d'appel\n{QUOTE}\nConsidérant"
    row["counter_surface_signal"] = {"heuristic_status": "candidate-limiting"}
    return out


def _recheck_prov(bundle: dict) -> dict:
    return (bundle.get("provenance") or {}).get("counter_evidence_content_recheck") or {}


# ---------------------------------------------------------------------------
# 1. the reproduced residual is closed
# ---------------------------------------------------------------------------

def test_hydration_d2_defect_is_downgraded_after_stage2():
    hydrated = _hydrate_into_letterhead(_stage1_with_clean_incumbent())
    before = hydrated["decisions"][0]
    assert ces.frozen_content_defects(before["counter_evidence"], before) == [
        "D2_letterhead_zone"
    ]
    assert before["counter_evidence_verified"] is True  # stage 1 could not see it

    out = ces.apply_surface_span_confirmation(hydrated, mode="select")
    row = out["decisions"][0]
    assert row["counter_evidence_verified"] is False
    assert row["counter_evidence_unevidenced"] is True
    assert row["counter_evidence_unevidenced_reason"] == "d2_letterhead_zone"
    assert row["counter_evidence"] == QUOTE  # kept verbatim for audit
    p = _recheck_prov(out)
    assert p["version"] == ces.CONTENT_RECHECK_VERSION
    assert p["n_verified_checked"] == 1
    assert p["n_downgraded"] == 1
    assert p["downgraded_ids"] == ["synthetic-hydration-recheck"]
    entry = p["downgrades"][0]
    assert entry["leg"] == "post_hydration_recheck"
    assert entry["source_stage"] == 1
    assert entry["defects"] == ["D2_letterhead_zone"]
    assert entry["grounded_field"] == "full_text"
    assert entry["grounded_offset"] < ces.LETTERHEAD_ZONE_OFFSET_MAX
    assert entry["before"]["counter_evidence_verified"] is True
    assert entry["after"]["counter_evidence_verified"] is False


def test_recheck_is_independent_of_the_stage2_kill_switch():
    hydrated = _hydrate_into_letterhead(_stage1_with_clean_incumbent())
    out = ces.apply_surface_span_confirmation(
        hydrated, mode="select", env={ces.SURFACE_SPAN_ENV: "off"}
    )
    assert (out["provenance"]["counter_evidence_span_surface"] or {})["applied"] is False
    assert out["decisions"][0]["counter_evidence_verified"] is False
    assert _recheck_prov(out)["n_downgraded"] == 1


def test_recheck_does_not_touch_geometry_or_drop_rows():
    hydrated = _hydrate_into_letterhead(_stage1_with_clean_incumbent())
    before_geo = {
        d["decision_id"]: (d["x"], d["y"], d["cluster_id"], d["rank"])
        for d in hydrated["decisions"]
    }
    out = ces.apply_surface_span_confirmation(hydrated, mode="select")
    assert {
        d["decision_id"]: (d["x"], d["y"], d["cluster_id"], d["rank"])
        for d in out["decisions"]
    } == before_geo
    assert len(out["decisions"]) == len(hydrated["decisions"])
    assert _recheck_prov(out)["geometry_touched"] is False


def test_recheck_is_idempotent_and_byte_stable_on_a_second_pass():
    hydrated = _hydrate_into_letterhead(_stage1_with_clean_incumbent())
    once = ces.apply_surface_span_confirmation(hydrated, mode="select")
    twice = ces.apply_surface_span_confirmation(once, mode="select")
    assert twice["decisions"][0]["counter_evidence_verified"] is False
    assert _recheck_prov(twice) == _recheck_prov(once)
    scored = lambda b: {  # noqa: E731
        d["decision_id"]: (d.get("counter_status"), d.get("counter_evidence"),
                           d.get("counter_evidence_verified"))
        for d in b["decisions"]
    }
    assert scored(twice) == scored(once)


# ---------------------------------------------------------------------------
# 2. no false rejection of a sound row
# ---------------------------------------------------------------------------

def test_known_sound_row_stays_verified_after_the_recheck():
    bundle = _load(SOUND_BUNDLE)
    out = ces.apply_surface_span_confirmation(bundle, mode="select")
    row = next(d for d in out["decisions"] if d["decision_id"] == SOUND_ID)
    assert row["counter_evidence_verified"] is True
    assert ces.frozen_content_defects(row["counter_evidence"], row) == []
    assert SOUND_ID not in _recheck_prov(out)["downgraded_ids"]


def test_fixed_path_family_has_zero_false_rejects_under_the_recheck():
    paths = sorted(
        glob.glob(str(ROOT / "results/product/offline_slice/*/*.bundle.json"))
        + glob.glob(str(ROOT / "results/product/server_slice/*/*.bundle.json"))
    )
    fixed = [
        p for p in paths
        if (json.loads(Path(p).read_text(encoding="utf-8"))
            .get("provenance", {}).get("counter_evidence_span", {})
            .get("content_filter"))
    ]
    assert fixed, "no fixed-path bundles found; probe population moved"
    for path in fixed:
        out = ces.apply_surface_span_confirmation(_load(str(Path(path).relative_to(ROOT))),
                                                  mode="select")
        p = _recheck_prov(out)
        assert p["n_downgraded"] == 0, (path, p["downgraded_ids"])


def test_markup_incumbent_with_span_record_is_also_downgraded():
    """D3 does not depend on hydration; the old sweep's span skip covered it."""
    bundle = _stage1_with_clean_incumbent()
    row = bundle["decisions"][0]
    row["counter_evidence"] = f"<mark>{QUOTE}</mark>"
    row["snippet"] = row["counter_evidence"]
    row["full_text"] = ""
    out = ces.apply_surface_span_confirmation(bundle, mode="select")
    result = out["decisions"][0]
    assert result["counter_evidence_verified"] is False
    assert result["counter_evidence_unevidenced_reason"] == "d3_markup_residue"
    assert _recheck_prov(out)["downgrades"][0]["defects"] == ["D3_markup_residue"]


def test_recheck_provenance_rehashes_the_frozen_predicates():
    out = ces.apply_surface_span_confirmation(
        _stage1_with_clean_incumbent(), mode="select")
    p = _recheck_prov(out)
    assert p["content_filter"] == ces.content_filter_provenance()
    assert p["content_filter"]["predicate_source_sha256"] == (
        ces.FROZEN_PREDICATE_SOURCE_SHA256
    )
