"""What cycle 39674781875 claims about itself, checked against the artifacts.

Why this exists
---------------
The independent audit of rejected product cycle 39674781875 returned two
required fixes:

* **D1** - ``state/product.json`` did not record the cycle's delivered
  capability, still named the stale test count, and did not state that the
  human-gate session and the live-answer reliability measurement are still
  incomplete;
* **D2** - ``product/live_slice.py``'s docstring attributed 9 manifest-covered
  cache rewrites to the two recorded runs' probes, where the measured
  attribution is 7 (2 of the 9 carry no probe attribution at all).

A claim in the lane state is the lane's own evidence, so it must be checkable
against the artifact it names. This module is that check: the state's numbers
are re-derived from the artifacts, and the posture it publishes is the
fail-closed posture the direction requires.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import cache_rewrite_attribution as attribution  # noqa: E402

STATE_PATH = ROOT / "state" / "product.json"
RUN_ID = 39674781875
DELIVERY_KEY = "cycle_39674781875_vertical_slice_delivery"
ATTRIBUTION_ARTIFACT = (ROOT / "results" / "product" / "cache_attribution"
                        / f"CYCLE_{RUN_ID}_manifest_rewrite_attribution.json")
SERVED_SUMMARY = (ROOT / "results" / "product" / "server_slice"
                  / "20261021T214006Z" / "summary.json")
REPORT_OF_RECORD = ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"

#: The live-slice artifacts that no report cited at the accepted base; this
#: cycle's report of record is their report of record, which is what makes the
#: citation sweep non-vacuous over them.
PREVIOUSLY_UNCITED = (
    "20261020T174538Z.json",
    "20261020T175313Z.json",
    "20261020T175637Z.json",
    "20261020T175732Z.json",
    "20261020T175839Z.json",
    "CYCLE_39452421855_full.json",
    "CYCLE_39452421855_maponly.json",
    "CYCLE_39667945530.json",
    "CYCLE_39667945530_FIX1.json",
)

#: A path-looking token in the state's own evidence strings.
_PATH = re.compile(r"(?:product|results|reports|state|data)/[\w./-]+\.(?:py|json|md)")


def _state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def test_the_state_carries_this_cycles_delivery_record() -> None:
    delivery = _state().get(DELIVERY_KEY)
    assert delivery is not None, f"state/product.json carries no {DELIVERY_KEY}"
    assert delivery["run_id"] == RUN_ID
    assert delivery["repair_round"] == 1
    assert delivery["human_gate_ready"] is False
    assert delivery["machine_gate_ready"] is False
    assert delivery["packet_admitted"] is False
    assert delivery["ready_for_owner_session"] is False
    assert delivery["delivered"], "the delivery record lists nothing"
    assert delivery["not_claimed"], "the delivery record claims no ceiling"
    assert delivery["claim_ceiling"]


def test_the_audit_required_fixes_are_addressed_in_the_state_itself() -> None:
    """D1 and D2 must be visible in the state, not only in the report."""
    state = _state()
    delivery = state[DELIVERY_KEY]
    fixes = delivery["audit_required_fixes_addressed"]
    assert set(fixes) == {"D1", "D2"}

    # D1: the delivered capability, the evidence, the served fixture path and
    # the explicit statement that the human gate and the live-answer
    # reliability measurement are still incomplete.
    joined = " ".join(delivery["delivered"]) + " " + " ".join(delivery["not_claimed"])
    assert "392/392" in joined, "the restored frozen cache is not recorded"
    assert "--tracked-cache" in joined, "the throwaway-default cache rule is not recorded"
    assert "STAGE_DISCLOSURE_AMENDMENT.json" in joined, \
        "the extended stage disclosure is not recorded"
    assert "20261021T214006Z" in joined, "the served fixture-path evidence is not recorded"
    assert "human-gate session has NOT run" in joined
    assert "live-answer reliability measurement has NOT run" in joined
    assert "281 passed" in " ".join(state["evidence_refs"]), \
        "the refreshed evidence references do not carry the recomputed count"
    assert "1 skipped" in " ".join(state["evidence_refs"])


def test_the_posture_is_fail_closed_and_the_accepted_run_pointer_is_intact() -> None:
    state = _state()
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["packet_admitted"] is False
    assert state["ready_for_owner_session"] is False
    assert state["requirement_13_supersession_conditions_met"] is False
    assert state["continue_recommended"] is True
    assert state["accepted_run_id"] == "39660515863", (
        "accepted_run_id names the last ACCEPTED run; cycle 39674781875 is not "
        "accepted, so the pointer must not move")
    assert state["direction_version"] == 61
    assert state["cycle_status"] != "INITIALIZED"


def test_the_recorded_attribution_equals_a_fresh_measurement() -> None:
    """The state's 9 / 7 / 2 is re-derived, never typed."""
    state = _state()
    recorded = state["verification"]["cache_rewrite_attribution_39674781875"]
    fresh = attribution.measure()
    assert recorded["manifest_covered_rewritten"] == \
        int(fresh["attribution"]["counts"]["manifest_covered_rewritten"])
    assert recorded["attributed_to_recorded_probes"] == \
        int(fresh["attribution"]["counts"]["distinct_attributed"])
    assert recorded["without_probe_attribution"] == \
        int(fresh["attribution"]["counts"]["unattributed"])
    assert recorded["unattributed_files"] == fresh["attribution"]["unattributed"]
    assert fresh["current_tree"]["intact"] is True
    assert fresh["current_tree"]["n_entries"] == 392
    assert fresh["current_tree"]["n_mismatch"] == 0
    assert fresh["current_tree"]["n_missing"] == 0


def test_the_attribution_artifact_on_disk_agrees_with_the_measurement() -> None:
    artifact = json.loads(ATTRIBUTION_ARTIFACT.read_text(encoding="utf-8"))
    assert artifact["run_id"] == RUN_ID
    assert artifact["attribution"]["counts"] == {
        "manifest_covered_rewritten": 9,
        "distinct_attributed": 7,
        "unattributed": 2,
    }
    assert artifact["current_tree"]["intact"] is True


def test_the_recorded_served_slice_equals_the_served_summary() -> None:
    state = _state()
    recorded = state["verification"]["served_slice_20261021T214006Z"]
    summary = json.loads(SERVED_SUMMARY.read_text(encoding="utf-8"))
    counts = summary["counts"]
    assert summary["verdict"] == "PASS"
    assert len(summary["checks"]) == 10
    assert all(row["status"] == "PASS" for row in summary["checks"])
    assert recorded["page_contract_assertions"] == counts["page_contract_assertions"]
    assert recorded["n_cited"] == counts["n_cited"]
    assert recorded["counter_authorities"] == counts["counter_authorities"]
    assert recorded["counter_status_bearing_rows"] == counts["counter_status_bearing_rows"]
    assert recorded["n_final"] == counts["n_final"]
    assert recorded["n_clusters"] == counts["n_clusters_final"]
    assert recorded["verdict"] == summary["verdict"]
    assert recorded["checks_passed"] == "10/10"


def test_the_bger_deep_link_count_is_measured_not_assumed() -> None:
    """The served slice's own field name is 'rows_with_source_url' but it counts
    the OpenCaseLaw canonical link. The state must name both counts."""
    state = _state()
    status = state["vertical_slice_status"]
    bundle = json.loads(
        (SERVED_SUMMARY.parent / "served.bundle.json").read_text(encoding="utf-8"))
    rows = bundle["decisions"]
    canonical = sum(1 for row in rows
                    if str(row.get("canonical_url") or "").startswith(
                        "https://mcp.opencaselaw.ch/"))
    bger = sum(1 for row in rows if row.get("source_url"))
    assert status["rows_with_opencaselaw_canonical_link"] == canonical
    assert status["rows_with_bger_source_url_deep_link"] == bger
    assert "rows_with_source_url" in status["rows_with_bger_source_url_note"]


def test_the_mvp_test_evidence_is_internally_consistent() -> None:
    """Every named file exists and the per-file counts add up to the total."""
    state = _state()
    register = state["verification"]
    files = register["mvp_test_files"]
    assert len(files) == 20, "the MVP set is 20 files"
    total = 0
    skipped = 0
    for entry in files:
        path, _, tail = entry.partition(" (")
        assert (ROOT / path).is_file(), f"the state names a file that does not exist: {path}"
        numbers = re.findall(r"(\d+) (passed|skipped)", tail)
        for value, kind in numbers:
            if kind == "passed":
                total += int(value)
            else:
                skipped += int(value)
    assert total == register["mvp_tests_passed"]
    assert skipped == register["mvp_tests_skipped"]
    assert register["mvp_tests_failed"] == 0


def test_every_artifact_the_state_names_exists() -> None:
    """No evidence pointer may name a file that is not on disk."""
    state = _state()
    blobs: list[str] = []
    blobs.extend(state["evidence_refs"])
    blobs.extend(state["verification"]["mvp_test_files"])
    blobs.extend(json.dumps(state[DELIVERY_KEY], ensure_ascii=False))
    missing = []
    for blob in blobs:
        for candidate in _PATH.findall(blob):
            if not (ROOT / candidate).exists():
                missing.append(candidate)
    assert not missing, f"the state names artifacts that do not exist: {sorted(set(missing))}"


def test_the_live_slice_docstring_carries_the_measured_attribution() -> None:
    """D2: the prose states the measurement, not the superseded claim."""
    source = (ROOT / "product" / "live_slice.py").read_text(encoding="utf-8")
    attribution = re.search(
        r"manifest-covered entries rewritten by commit 3f94e0e\s*=\s*9;\s*"
        r"attributed to the\s+two recorded runs' own probes\s*=\s*7;\s*"
        r"carrying no probe attribution\s*=\s*2", source)
    assert attribution, (
        "the docstring must state the measured attribution (9 rewritten, 7 "
        "attributed, 2 unattributed), not the superseded 9")
    assert "9 more" not in source, "the superseded 'turned 9 more' wording is back"
    assert "11c69a8b8d6957fcb1348469a840098bf523ea1d558853b7ab008e978d714927.json" in source
    assert "88a3a731a6829455f6911b8931a1f4c3e9235d5d7a64519018e16563a3e33598.json" in source


def test_the_report_of_record_cites_the_previously_uncited_artifacts() -> None:
    """The report of record is what makes the citation sweep non-vacuous."""
    assert REPORT_OF_RECORD.exists(), "the report of record is missing"
    text = REPORT_OF_RECORD.read_text(encoding="utf-8")
    for name in PREVIOUSLY_UNCITED:
        assert name in text, f"the report of record does not cite {name}"


def test_the_report_of_record_states_the_fail_closed_posture() -> None:
    text = REPORT_OF_RECORD.read_text(encoding="utf-8")
    for needle in ("human_gate_ready", "packet_admitted", "BOUNDED-NEGATIVE"):
        assert needle in text, f"the report of record never mentions {needle}"
