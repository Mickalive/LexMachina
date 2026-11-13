"""Operational resume 43349050225: verify the v68 P0 leg and hand off to audit.

The resumed run 43348787378 persisted a team ref byte-identical to the prior
producer commit (``7cca4708``), so it added no product delta and the chain of
no-audit diagnosis cycles continued.  The substantive v68 P0 work was already
accepted in cycle 40284658455 (gate PASS, accept commit ``7be4480e``); what
was missing is the *verification* that the accepted bytes still satisfy the
ordered-work P0 rule, an enforced check for that rule, and a fresh
audit-readiness dossier keyed to this executing run.

This test pins the resume without re-diagnosing accepted work:

* the resumed snapshot is honestly recorded as ZERO_DURABLE_DELTA with an
  UNOBSERVED mechanism (no public run/jobs snapshot was reachable) and is
  UNADJUDICATED;
* the ordered-work (2) success rule re-derives from the *current* committed
  fixed-path family: 49 bundles / 4900 decisions / 55 verified rows / 0
  verified-and-defective, no D2/D3/D4 defects, the known sound row retained
  and 0 false rejects (REPORTED-ONLY; no frozen bar is scored);
* ``content_family_probe.py --check`` is an *enforced* command: it fails when
  the rule is unmet instead of printing ``met: False`` and exiting 0;
* the end-to-end offline slice still builds a source-linked clickable map plus
  a sourced answer from the cached OpenCaseLaw fixture with no network;
* the accepted pointer is advanced to the latest accept commit (40284658455 /
  ``7be4480e``) and satisfies both halves of requirement 4;
* posture stays fail-closed and the producer wrote no auditor-namespace path.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

EXECUTING_RUN_ID = "43349050225"
RESUMED_RUN_ID = "43348787378"
PREDECESSOR_RUN_ID = "43343006260"
SNAPSHOT_HEAD = "7cca4708da041e2532934a7ebd945bdb02130f56"
ACCEPTED_RUN_ID = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

STATE = ROOT / "state" / "product.json"
ORCH = ROOT / "results" / "product" / "orchestration"
DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
FAMILY = (ROOT / "results" / "product" / "counter_content_family"
          / f"CYCLE_{EXECUTING_RUN_ID}.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"
ACCEPT_GATE = (ROOT / "results" / "audit" / "product"
               / "CYCLE_40284658455_GATE.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_resumed_snapshot_is_zero_delta_unobserved_and_unadjudicated():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == PREDECESSOR_RUN_ID
    # RAW_SNAPSHOT_UNAVAILABLE: no run/jobs snapshot was reachable, so no
    # provider/auth/quantum cause may be invented.
    orch = diag["orchestration"]
    assert orch["classification"] == "RAW_SNAPSHOT_UNAVAILABLE"
    assert orch["mechanism_unobserved"] is True
    assert "mechanism" not in orch
    # The ref exists but is byte-identical to the prior producer commit.
    delta = diag["durable_delta"]
    assert delta["classification"] == "ZERO_DURABLE_DELTA"
    assert delta["changed_files"] == 0
    assert delta["snapshot_head"] == SNAPSHOT_HEAD
    assert delta["predecessor_head"] == SNAPSHOT_HEAD
    # No independent gate and no accept commit for this run.
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False


def test_p0_full_family_rule_holds_on_current_committed_bytes():
    cf = _load(FAMILY)
    totals = cf["fixed_path_family"]["totals"]
    assert totals["n_bundles"] == 49
    assert totals["n_decisions"] == 4900
    assert totals["n_verified"] == 55
    assert totals["n_verified_defective"] == 0
    assert totals["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert cf["false_reject_count"] == 0
    assert cf["confirmed_set"]["decision_id"] == "bstger_SK.2023.49"
    assert cf["confirmed_set"]["still_verified"] is True
    assert cf["ordered_work_2_success_rule"]["met"] is True
    assert cf["ordered_work_2_full_success_rule"]["met"] is True
    prov = cf["frozen_predicate_provenance"]
    assert prov["predicate_source_sha256"]
    assert prov["frozen_hypothesis_sha256"]
    # Historical bundles are preserved evidence, not current-head defects.
    assert cf["historical_population"]["totals"]["n_bundles"] > 0
    assert (
        cf["historical_population"]["totals"]["n_verified_defective"] >= 0
    )


def test_probe_check_flag_enforces_the_success_rule():
    proc = subprocess.run(
        [sys.executable, "product/content_family_probe.py", "--check", "--json"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300, check=False)
    assert proc.returncode == 0, proc.stderr[-2000:]
    record = json.loads(proc.stdout)
    assert record["ordered_work_2_full_success_rule"]["met"] is True


def test_offline_slice_still_delivers_sourced_clickable_map():
    from offline_slice import _geometry, build_bundle  # noqa: E402

    bundle = build_bundle("rent-default", 100, enrich=True)
    rows = bundle["decisions"]
    assert len(rows) == 100
    assert all(r.get("x") is not None and r.get("y") is not None for r in rows)
    assert all(r.get("cluster_id") is not None for r in rows)
    assert all(r.get("canonical_url") for r in rows)
    assert len({r.get("cluster_id") for r in rows}) >= 2
    answer = bundle.get("answer") or {}
    assert answer.get("status") == "ready"
    assert answer.get("cited_decision_ids")
    assert bundle["provenance"]["offline_slice"]["geometry_preserved"] is True
    assert bundle["provenance"]["offline_slice"]["network"] == "none"
    # A rendered point is query-conditioned: coordinates must be finite.
    geo = _geometry(bundle)
    assert len(geo) == 100


def test_accepted_pointer_advanced_to_latest_accept_commit():
    st = _load(STATE)
    assert st["accepted_run_id"] == ACCEPTED_RUN_ID
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    gate = _load(ACCEPT_GATE)
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    assert gate["required_fixes"] == []
    from product.state_contract import accepted_pointer_evidence
    evidence = accepted_pointer_evidence(st, ROOT)
    assert evidence["problems"] == []
    assert evidence["gate_ok"] is True
    assert evidence["accept_commit_present"] is True


def test_posture_fail_closed_and_no_auditor_namespace_writes():
    st = _load(STATE)
    assert st["direction_version"] == 68
    assert st["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert st[flag] is False, f"{flag} must stay fail-closed"
    # POINTER-PIN AMENDMENT (standing convention from cycle 40272586794,
    # re-applied here by operational-resume run 43363900852): later cycles
    # legitimately advance ``current_cycle_run_id``, so the equality pin
    # asserted `43357207555 == 43349050225` and failed on successor cycles
    # with nothing regressed.  What survives is stronger: the pointer must
    # never REGRESS below this cycle's executing run (a hand-rolled-back
    # state fails), and every assertion below still pins this cycle's report,
    # the fail-closed posture and the no-self-minted-gate rule verbatim.
    assert st["current_cycle_run_id"] >= int(EXECUTING_RUN_ID), (
        "current_cycle_run_id regressed below this cycle's executing run",
        st["current_cycle_run_id"], EXECUTING_RUN_ID)
    assert REPORT.is_file()
    # The producer may not mint an audit gate for its own run.
    assert not (ROOT / "results" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}_GATE.json").exists()
    assert not (ROOT / "reports" / "audit" / "product"
                / f"CYCLE_{EXECUTING_RUN_ID}.md").exists()
