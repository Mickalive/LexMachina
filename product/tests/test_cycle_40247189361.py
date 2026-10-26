"""Cycle 40247189361: operational resume + fresh P0 verification.

This run resumed the persisted producer snapshot of failed run 40247041354.
The snapshot was byte-identical to ``origin/lab/product`` at dispatch, so the
run carries **zero durable delta**; no public run/jobs snapshot was reachable
from the producer environment, so the orchestration mechanism stays explicitly
unobserved.  The lane deliverable is nevertheless re-verified here on freshly
regenerated fixture bytes: the v68 rejection/incumbent leg downgrades every
defective incumbent counter-evidence row before it can remain verified.

Pinned properties
-----------------
1. The accepted pointer names the latest accepted cycle by BOTH halves of
   factory-wide requirement 4 (independent PASS gate + accept commit).
2. The resume diagnosis classifies zero durable delta and invents no mechanism.
3. All four fresh offline bundles carry the frozen content filter, and every
   downgrade moves ``verified true -> false`` with a frozen D1-D4 defect.
4. No freshly emitted verified row is defective; the known sound row stays
   verified.
5. The full-family probe, map-integrity probe and progressive smoke agree.
6. This producer run minted no audit gate and claims no human/machine gate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import resume_snapshot_diagnosis as rsd   # noqa: E402
from product import state_contract as sc              # noqa: E402

RUN_ID = "40247189361"
RESUMED_RUN_ID = "40247041354"
ACCEPTED_RUN_ID = "40245479781"
ACCEPTED_COMMIT = "2f5147495cf0cd9c77436e4f88904c719302387a"
SLICES = (
    "rent-default",
    "petty-theft-dismissal",
    "corporate-criminal-liability",
    "business-judgment-rule",
)
FRESH_DIR = REPO_ROOT / "results" / "product" / "offline_slice"
FAMILY = REPO_ROOT / "results" / "product" / "counter_content_family" / f"CYCLE_{RUN_ID}.json"
MAP = REPO_ROOT / "results" / "product" / "map_integrity" / f"CYCLE_{RUN_ID}.json"
SMOKE = (REPO_ROOT / "results" / "product" / "progressive_smoke"
         / f"CYCLE_{RUN_ID}_progressive_smoke.json")
DIAG = (REPO_ROOT / "results" / "product" / "orchestration"
        / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json")
STATE = REPO_ROOT / "state" / "product.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle(slug: str) -> dict:
    return _load(FRESH_DIR / f"{RUN_ID}-{slug}" / f"{slug}.bundle.json")


def _verified(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("counter_evidence_verified") is True]


def test_accepted_pointer_has_both_requirement4_halves() -> None:
    state = _load(STATE)
    assert state["accepted_run_id"] == f"CYCLE_{ACCEPTED_RUN_ID}"
    assert state["accepted_commit"] == ACCEPTED_COMMIT
    evidence = sc.accepted_pointer_evidence(state)
    assert evidence["problems"] == []
    assert evidence["gate_ok"] is True
    assert evidence["accept_commit_present"] is True


def test_resume_diagnosis_zero_delta_and_no_invented_mechanism() -> None:
    rec = _load(DIAG)
    assert rec["run_id"] == RESUMED_RUN_ID
    assert rec["predecessor_ref"] == "origin/lab/product"
    assert rec["durable_delta"]["classification"] == "ZERO_DURABLE_DELTA"
    assert rec["orchestration"]["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert rec["orchestration"]["mechanism_unobserved"] is True
    assert rec["adjudication"]["status"] == "UNADJUDICATED"
    assert rec["adjudication"]["product_defect"] is False
    assert rec["adjudication"]["verdict_written"] is False
    # The no-raw instrument records the same honest classification.
    probe = rsd._orchestration_without_raw(None)
    assert probe["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert probe["mechanism_unobserved"] is True


def test_fresh_bundles_carry_frozen_filter_and_downgrade_defects() -> None:
    frozen_sha = None
    n_downgraded = 0
    for slug in SLICES:
        bundle = _bundle(slug)
        span = bundle["provenance"]["counter_evidence_span"]
        cf = span["content_filter"]
        assert cf["predicate_source"] == "evaluation/counter_evidence_quality_benchmark.py"
        assert cf["min_marker_hits"] == 3
        if frozen_sha is None:
            frozen_sha = cf["predicate_source_sha256"]
        assert cf["predicate_source_sha256"] == frozen_sha
        assert (span.get("applied") is True
                or span.get("content_filter_applied") is True)
        for downgrade in span.get("downgrades", []):
            n_downgraded += 1
            assert downgrade["before"]["counter_evidence_verified"] is True
            assert downgrade["after"]["counter_evidence_verified"] is False
            assert downgrade["defects"], downgrade
            assert downgrade["after"]["counter_evidence_unevidenced_reason"]
        ids = {r["decision_id"] for r in bundle["decisions"]}
        for decision_id in span.get("downgraded_ids", []):
            if decision_id in ids:
                row = next(r for r in bundle["decisions"] if r["decision_id"] == decision_id)
                assert row["counter_evidence_verified"] is False
    assert n_downgraded == 3, "rent + petty-theft + business-judgment defective incumbents"


def test_no_fresh_verified_row_is_defective_and_sound_row_survives() -> None:
    family = _load(FAMILY)
    fixed = family["fixed_path_family"]
    assert len(fixed["bundles"]) == 49
    assert sum(b["n_decisions"] for b in fixed["bundles"]) == 4900
    assert sum(b["n_verified"] for b in fixed["bundles"]) == 55
    assert sum(b["n_verified_defective"] for b in fixed["bundles"]) == 0
    assert family["false_reject_count"] == 0
    totals = {"D1_empty_evidence": 0, "D2_letterhead_zone": 0,
              "D3_markup_residue": 0, "D4_language_marker_mismatch": 0}
    for bundle in fixed["bundles"]:
        assert bundle["defect_histogram"] == totals, bundle["path"]
    assert family["ordered_work_2_full_success_rule"]["met"] is True
    assert family["historical_population"]["totals"]["n_verified_defective"] == 75
    for slug in SLICES:
        bundle = _bundle(slug)
        assert not _verified(bundle["decisions"]) or all(
            not r.get("counter_evidence_unevidenced_reason")
            for r in _verified(bundle["decisions"])
        )
    # The guard must not over-reject a sound row.
    bstger = next(
        r for r in _bundle("corporate-criminal-liability")["decisions"]
        if r["decision_id"] == "bstger_SK.2023.49"
    )
    assert bstger["counter_evidence_verified"] is True
    assert not bstger.get("counter_evidence_unevidenced_reason")


def test_map_integrity_and_progressive_smoke_agree() -> None:
    m = _load(MAP)
    assert m["success_met"] is True
    assert m["n_duplicate_identity_groups"] == 0
    assert m["n_decisions"] == 400
    smoke = _load(SMOKE)
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"] == 23


def test_posture_fail_closed_and_no_gate_minted() -> None:
    state = _load(STATE)
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["continue_recommended"] is True
    assert not (REPO_ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN_ID}_GATE.json").exists()
