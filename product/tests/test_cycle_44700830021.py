"""Operational resume 44700830021: finish snapshot 44694975109.

Pins the local-evidence diagnosis, the reproduced verification, the state
pointer hygiene and the fail-closed posture. No gate verdict is minted here:
the independent auditor owns results/audit/product/CYCLE_44700830021_GATE.json.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "product")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query import counter_evidence_span as ces  # noqa: E402

RUN = "44700830021"
RESUMED = "44694975109"
SNAPSHOT_SHA = "3928818e7fd6e38ff3eb85206cf3ab9e9faef0bf"

STATE = ROOT / "state" / "product.json"
DIAG = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED}_resume_diagnosis.json")
VERIF = ROOT / "results" / "product" / "answer_sourcing" / (
    f"CYCLE_{RUN}_verification.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{RUN}.md"
GATE = ROOT / "results" / "audit" / "product" / f"CYCLE_{RUN}_GATE.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                          text=True, check=True).stdout.strip()


def test_resume_artifacts_exist_and_agree():
    diag, verif = _load(DIAG), _load(VERIF)
    assert diag["run_id"] == int(RESUMED)
    assert diag["resuming_run_id"] == int(RUN)
    assert diag["verdict"] == "UNADJUDICATED_VALIDATION_ARTIFACTS_ABSENT"
    assert diag["snapshot"]["head_sha256_git"] == SNAPSHOT_SHA
    assert diag["snapshot"]["head_matches_session_HEAD"] is True
    assert diag["failure_mechanism"]["status"] == "NOT_DIRECTLY_OBSERVABLE_IN_THIS_ENVIRONMENT"
    assert diag["resume_actions"]["no_gate_minted"] is True
    assert diag["resume_actions"]["no_frozen_artifact_touched"] is True
    assert verif["run_id"] == RUN
    assert verif["resumed_snapshot_run_id"] == RESUMED
    assert verif["verdict"] == "PASS"
    assert REPORT.is_file() and f"CYCLE_{RUN}" in REPORT.read_text(encoding="utf-8")


def test_verification_checks_are_non_vacuous():
    v = _load(VERIF)
    checks = v["checks"]
    assert len(checks) >= 10 and all(checks.values())
    assert v["bundle"]["n_decisions"] >= 40
    assert v["bundle"]["answer_status"] == "ready"
    assert v["bundle"]["geometry_preserved"] is True
    src = v["writers"]["answer_fixture_source"]
    note = v["writers"]["answer_counter_note"]
    assert src["applied"] is True and src["n_quotes"] >= 1
    assert src["quoted_ids"]
    assert note["applied"] is True and note["n_counter_rows"] >= 1
    assert v["citation_validity"]["n_markers"] >= 1
    assert v["citation_validity"]["n_resolved"] == v["citation_validity"]["n_markers"]
    assert v["citation_validity"]["n_unresolved"] == 0
    assert v["validate_bundle_errors"] == []
    assert v["answer_prose"]["after"] != v["answer_prose"]["before_header"]
    assert all(not r["frozen_defects"]
               for r in v["frozen_content_predicates"]["verified_rows_scanned"])
    assert v["frozen_content_predicates"]["status"] == "REPORTED_ONLY_NOT_EDITED_NOR_REDERIVED"
    assert v["frozen_content_predicates"]["reported_expected_sha256"] == \
        ces.FROZEN_PREDICATE_SOURCE_SHA256


def test_state_attribution_and_resume_block_are_correct():
    """POINTER-PIN AMENDMENT (resume 44711032839).

    Later executing cycles legitimately advance ``current_cycle_run_id`` past
    this cycle's era (the same monotonic guard already exists in
    test_cycle_40284658455.py, test_cycle_40269774540_repair.py and
    test_cycle_40263666190_resume.py).  The durable claim is strengthened:
    the pointer never REGRESSES below this cycle's executing run and this
    cycle's run_history entry and resume block survive verbatim in state.
    """
    st = _load(STATE)
    assert isinstance(st["current_cycle_run_id"], int)
    assert st["current_cycle_run_id"] >= int(RUN), (
        "current_cycle_run_id regressed below this cycle's executing run",
        st["current_cycle_run_id"], RUN)
    assert st["owner_decision_required"] is False
    hist = {str(h.get("run_id")): h for h in st.get("run_history") or []}
    assert RUN in hist
    assert hist[RUN]["status"] == "OPERATIONAL_RESUME_SOURCE_WRITER_VERIFICATION"
    assert hist[RUN]["audit_gate"] == "NONE_YET"
    block = st.get(f"cycle_{RUN}_operational_resume") or {}
    assert block.get("run_id") == int(RUN)
    assert block.get("resumed_snapshot", {}).get("run_id") == int(RESUMED)
    assert block.get("resumed_snapshot", {}).get("team_ref_head") == SNAPSHOT_SHA
    assert block.get("verification_verdict") == "PASS (10/10 checks)"
    assert block.get("no_gate_minted") is True
    assert block.get("no_frozen_artifact_touched") is True
    refs = st.get("evidence_refs") or []
    for needle in (f"CYCLE_{RESUMED}_resume_diagnosis.json",
                   f"CYCLE_{RUN}_verification.json",
                   "test_answer_sourcing.py"):
        assert any(needle in r for r in refs), needle


def test_accepted_pointer_and_posture_unchanged():
    """POINTER-PIN AMENDMENT (resume 44711032839).

    This cycle's test originally pinned the accepted pointer to
    CYCLE_40269774540 / 5adaa66d, which went stale when run 40284658455 was
    accepted (7be4480e).  The durable claim is strengthened: the pointer must
    satisfy BOTH halves of requirement 4 for whatever run it names, and the
    fail-closed posture and the UNADJUDICATED wording are unchanged.
    """
    from product.state_contract import accepted_pointer_evidence
    st = _load(STATE)
    ev = accepted_pointer_evidence(st, ROOT)
    assert ev["problems"] == [], ev
    assert ev["gate_ok"] is True and ev["accept_commit_present"] is True
    # historical pointer values remain readable in git history; nothing was
    # re-labelled, only superseded with disclosure (accepted_run_supersession)
    assert "CYCLE_40269774540" in st["accepted_run_supersession"]
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert st.get(flag) is False, flag
    assert st.get("continue_recommended") is True
    assert "UNADJUDICATED" in st["next_recommendation"]


def test_no_producer_minted_gate_and_snapshot_delta_preserved():
    assert not GATE.exists(), "producer must not author the audit gate"
    team_ref = _git("rev-parse", "origin/cycle/core/product/"
                    f"{RESUMED}/team")
    assert team_ref == SNAPSHOT_SHA
    names = _git("show", "--name-only", "--format=", SNAPSHOT_SHA)
    assert "product/query/answer_sourcing.py" in names
    assert "product/query/pipeline.py" in names
    # the missing acceptance contract is now supplied, not a replacement of
    # the committed writers
    assert (ROOT / "product" / "query" / "answer_sourcing.py").is_file()
    assert (ROOT / "product" / "tests" / "test_answer_sourcing.py").is_file()
