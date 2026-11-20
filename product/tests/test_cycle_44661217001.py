"""Cycle 44661217001 — accepted-pointer sync (direction v68, item 4).

This cycle did NOT re-derive any discharged v68 finding.  Its whole durable
delta is truthfulness of the accepted pointer plus the regression guards below:

1. ``state/product.json`` points at the true current accepted head
   (CYCLE_40284658455 / 7be4480e), verified from BOTH halves of factory-wide
   requirement 4, with the prior accepted pointer preserved append-only;
2. the fail-closed posture is unchanged (no frozen bar, rubric, threshold or
   bar touched; no serve verdict re-run; no product claim advanced);
3. the v68 P0 rejection/incumbent leg still holds on the committed bundles:
   the four defective decisions are not verified-with-defective-content and the
   one sound decision stays verified/sound;
4. the query->bundle->clickable-map slice is still runnable from a committed
   bundle (decisions carry coordinates, clusters and source links).

No network, no model, no frozen instrument is re-scored here.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query import counter_evidence_span as ces  # noqa: E402

ACCEPTED_RUN = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
PRIOR_RUN = "CYCLE_40269774540"
PRIOR_COMMIT = "5adaa66d4ad2b9702cd023bfd49d743667f9e638"


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _state() -> dict:
    return _load("state/product.json")


# --------------------------------------------------------------------------- #
# 1. accepted pointer sync
# --------------------------------------------------------------------------- #

def test_accepted_pointer_is_the_true_current_head():
    st = _state()
    assert st["accepted_run_id"] == ACCEPTED_RUN
    assert st["accepted_commit"] == ACCEPTED_COMMIT


def test_both_halves_of_requirement_4_are_recorded_and_hold():
    st = _state()
    sync = st["cycle_44661217001_accepted_pointer_sync"]
    assert sync["run_id"] == 44661217001
    assert sync["direction_version"] == 68
    halves = sync["both_halves_verified_this_cycle"]
    gate = halves["half_1_audit_gate"]
    assert gate["path"] == f"results/audit/product/{ACCEPTED_RUN}_GATE.json"
    disk_gate = _load(gate["path"])
    assert (gate["gate"], disk_gate["gate"]) == ("PASS", "PASS")
    assert disk_gate["safe_to_integrate"] is True
    assert disk_gate["required_fixes"] == []
    assert halves["half_2_accept_commit"]["head"] == ACCEPTED_COMMIT
    assert halves["half_2_accept_commit"]["accepted_commit_is_ancestor_of_head"] is True


def test_prior_pointer_is_preserved_append_only():
    st = _state()
    sync = st["cycle_44661217001_accepted_pointer_sync"]
    prior = sync["prior_pointer_preserved_append_only"]
    assert prior["accepted_run_id"] == PRIOR_RUN
    assert prior["accepted_commit"] == PRIOR_COMMIT
    assert prior["still_resolves"] is True
    # the narrative history field still carries the superseded value verbatim
    assert PRIOR_COMMIT in st["accepted_run_supersession"]


def test_no_claim_or_posture_change():
    st = _state()
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, key
    assert st["continue_recommended"] is True
    assert st["direction_version"] == 68
    sync = st["cycle_44661217001_accepted_pointer_sync"]
    assert "no product claim advanced or weakened" in sync["claim_impact"]
    assert sync["ordered_work_v68_status"].startswith("LANDED")


# --------------------------------------------------------------------------- #
# 2. v68 P0 leg still intact on committed bundles
# --------------------------------------------------------------------------- #

DEFECTIVE = [
    ("results/product/offline_slice/20261024T142517Z/rent-default.bundle.json",
     "gr_gerichte_ERZ 2010 25"),
    ("results/product/offline_slice/20261023T121515Z/business-judgment-rule.bundle.json",
     "bge_BGE_110_II_391"),
    ("results/product/offline_slice/20261023T121518Z/petty-theft-dismissal.bundle.json",
     "ge_gerichte_CAPH_107_2004"),
    ("results/product/server_slice/20261023T224255Z/served.bundle.json",
     "bge_BGE_121_III_260"),
]
SOUND = ("results/product/offline_slice/20261023T121512Z/"
         "corporate-criminal-liability.bundle.json", "bstger_SK.2023.49")


def _row(rel: str, did: str) -> dict:
    return next(d for d in _load(rel)["decisions"] if d.get("decision_id") == did)


def test_defective_rows_are_still_not_verified_with_defective_content():
    # The committed bundles carry the pre-apply (BEFORE) state; the shipped
    # path applies the seam at emission time.  Re-run that exact seam and
    # assert no verified row carries a frozen content defect afterwards.
    for rel, did in DEFECTIVE:
        doc = _load(rel)
        out = ces.apply_verified_span_selection(
            copy.deepcopy(doc), qid=(doc.get("provenance") or {}).get("qid"))
        row = next(d for d in out["decisions"] if d.get("decision_id") == did)
        defects = ces.frozen_content_defects(
            str(row.get("counter_evidence") or ""), row)
        assert not (row.get("counter_evidence_verified") is True and defects), (
            did, defects)
        assert row.get("counter_evidence_verified") is False


def test_sound_row_still_verified_and_clean_after_shipped_apply():
    rel, did = SOUND
    doc = _load(rel)
    out = ces.apply_verified_span_selection(
        copy.deepcopy(doc), qid=(doc.get("provenance") or {}).get("qid"))
    after = next(d for d in out["decisions"] if d.get("decision_id") == did)
    assert after.get("counter_evidence_verified") is True
    assert ces.frozen_content_defects(
        str(after.get("counter_evidence") or ""), after) == []


# --------------------------------------------------------------------------- #
# 3. clickable slice still runnable from a committed bundle
# --------------------------------------------------------------------------- #

def test_committed_bundle_has_clickable_map_shape():
    bundle = _load("results/product/offline_slice/20261024T142517Z/"
                   "rent-default.bundle.json")
    decisions = bundle["decisions"]
    assert len(decisions) >= 100
    assert all(d.get("x") is not None and d.get("y") is not None
               for d in decisions)
    assert all(d.get("cluster_id") is not None for d in decisions)
    assert all(d.get("canonical_url") for d in decisions)
