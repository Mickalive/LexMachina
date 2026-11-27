"""Operational resume 40284658455: audit-readiness repair of snapshot 40283048553.

Six consecutive core-product runs produced no audit and no promotion while
unadjudicated producer work piled up on team refs.  This test locks the
resume's diagnosis and repairs fail-closed:

* the full chain 40272586794 -> 40276797027 -> 40277000301 -> 40278204862 ->
  40278460732 -> 40283048553 is recorded in ``state/product.json`` run_history
  with each run's OBSERVED mechanism (quantum expiry after the substantive
  commit; a model-gateway ``unsupported_parameter`` rejection; two zero-delta
  guard exits; another quantum expiry; a producer-minted audit gate caught by
  write-scope enforcement) - none re-diagnosed, none upgraded;
* the producer-minted ``results/audit/product/CYCLE_40278460732_GATE.json``
  is PRESERVED verbatim (append-only evidence) and quarantined NON-PROMOTING
  by a product-owned sidecar whose sha256 pins the committed bytes; nothing
  may cite it as an audit gate, and no /audit ref for 40278460732 exists;
* state attribution is repaired: ``current_cycle_run_id`` names the
  EXECUTING run (40284658455), not the resumed snapshot (40283048553's state
  rewrite had regressed to 40278460732);
* the accepted pointer still satisfies BOTH halves of requirement 4 and the
  posture stays fail-closed (every gate flag FALSE, continue_recommended
  TRUE) while both frozen bars are unmet;
* the resume diagnosis and the raw run/jobs snapshot for 40283048553 exist,
  agree with the state, and the audit-readiness instrument knows this
  failure mode as a first-class ``observed_scope`` mechanism kind.

SUPERSESSION AMENDMENT (run 45921358503): this historical test was written
while 40284658455 was still executing and its gate did not yet exist.  That
cycle was subsequently accepted by both halves, so this test must not pin the
pre-acceptance pointer or assert that its gate is absent.  It now verifies the
canonical pointer dynamically (never below 40284658455, both halves present)
and keeps the real non-promoting claim - no auditor-authored gate for the
minted 40278460732 run or the resumed 40283048553 run.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from product.state_contract import accepted_pointer_evidence  # noqa: E402

EXECUTING_RUN_ID = "40284658455"
RESUMED_RUN_ID = "40283048553"
MINTED_GATE_RUN = "40278460732"
CHAIN = ("40272586794", "40276797027", "40277000301", "40278204862",
         "40278460732", "40283048553")

STATE = ROOT / "state" / "product.json"
DIAG = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json")
RAW = ROOT / "results" / "product" / "orchestration" / (
    f"CYCLE_{RESUMED_RUN_ID}_team_step_raw.json")
QUARANTINE = ROOT / "results" / "product" / "incidents" / (
    f"self_minted_gate_{MINTED_GATE_RUN}_producer_{RESUMED_RUN_ID}"
    ".QUARANTINED.json")
MINTED_GATE = ROOT / "results" / "audit" / "product" / (
    f"CYCLE_{MINTED_GATE_RUN}_GATE.json")
REPORT = ROOT / "reports" / "product" / f"CYCLE_{EXECUTING_RUN_ID}.md"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        check=True).stdout.strip()


def test_chain_runs_are_recorded_with_observed_mechanisms():
    st = _load(STATE)
    hist = {str(h.get("run_id")): h for h in st.get("run_history") or []}
    for run in CHAIN:
        assert run in hist, f"run {run} missing from run_history"
    # 40272586794's history entry is append-only history written by its own
    # cycle (before its post-commit quantum expiry was observable); the
    # expiry itself is sourced from the resume diagnosis, which pins all
    # six mechanisms.
    assert "UNADJUDICATED" in hist["40272586794"]["summary"]
    assert "MODEL_GATEWAY" in hist["40276797027"]["status"]
    assert "ZERO_DURABLE_DELTA" in hist["40277000301"]["status"]
    assert "ZERO_DURABLE_DELTA" in hist["40278204862"]["status"]
    assert "QUANTUM" in hist["40278460732"]["status"]
    assert "SELF_MINTED_GATE" in hist["40283048553"]["status"]
    diag = _load(DIAG)
    mech = {r["run_id"]: r["mechanism"]
            for r in diag["failure_chain_diagnosis"]["runs"]}
    assert mech["40272586794"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["40276797027"] == "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER"
    assert mech["40277000301"] == "AGENT_FINISHED_ZERO_DURABLE_DELTA"
    assert mech["40278204862"] == "AGENT_FINISHED_ZERO_DURABLE_DELTA"
    assert mech["40278460732"] == "OBSERVED_QUANTUM_EXPIRED"
    assert mech["40283048553"] == "OBSERVED_SCOPE_ENFORCEMENT_FAILED"
    # Every chain run stays UNADJUDICATED: no audit ref exists for any of
    # them, so none may be laundered into ACCEPTED by narrative.
    for run in CHAIN:
        gate = str(hist[run].get("audit_gate") or "")
        assert "PASS" not in gate.upper(), (run, gate)


def test_self_minted_gate_is_preserved_and_quarantined_non_promoting():
    assert MINTED_GATE.is_file(), "minted gate must be preserved (append-only)"
    rec = _load(QUARANTINE)
    assert rec["verdict"] == "NON_PROMOTING"
    sha = hashlib.sha256(MINTED_GATE.read_bytes()).hexdigest()
    assert rec["minted_artifact"]["sha256"] == sha
    assert rec["minted_artifact"]["preserved_verbatim"] is True
    assert rec["provenance"]["commit"].startswith("b64e2318")
    assert rec["provenance"]["author"].startswith("producer agent")
    # The minted file must never be presented as an independent audit gate.
    text = json.dumps(rec).lower()
    assert "non_promoting" in text or "non-promoting" in text


def test_no_gate_exists_for_the_resumed_or_minted_run():
    # 40278460732's file exists only as the quarantined producer mint;
    # 40283048553 never reached an auditor.  Neither may acquire an audit
    # ref or an auditor-authored gate merely because later cycles ran.
    for run in (RESUMED_RUN_ID, MINTED_GATE_RUN):
        audit_refs = _git("ls-remote", "--heads", "origin",
                          f"refs/heads/cycle/core/product/{run}/audit")
        assert audit_refs == "", f"unexpected /audit ref for {run}"
    # The resumed run never reached an auditor at all.
    assert not (ROOT / "results" / "audit" / "product" /
                f"CYCLE_{RESUMED_RUN_ID}_GATE.json").exists()
    # The minted file is deliberately preserved in the tree but is NOT an
    # auditor-authored gate; its NON-PROMOTING quarantine is pinned below and
    # in test_self_minted_gate_is_preserved_and_quarantined_non_promoting.
    assert (ROOT / "results" / "audit" / "product" /
            f"CYCLE_{MINTED_GATE_RUN}_GATE.json").is_file()
    # SUPERSESSION AMENDMENT: this run itself was later accepted through both
    # halves, so its gate is now expected rather than forbidden.  Pinning the
    # old "no gate yet" state would make an accepted fact look like a defect.
    gate = _load(ROOT / "results" / "audit" / "product" /
                 f"CYCLE_{EXECUTING_RUN_ID}_GATE.json")
    assert gate["gate"] == "PASS" and gate["safe_to_integrate"] is True
    log = _git("log", "--all", "--oneline",
               f"--grep=^accept product cycle {EXECUTING_RUN_ID}$")
    assert EXECUTING_RUN_ID in log


def test_state_attributes_an_executing_run_not_a_resumed_snapshot():
    st = _load(STATE)
    # This cycle corrected 40278460732 -> 40284658455.  Later cycles may
    # advance the executing run; they must never regress to a resumed one.
    assert int(st["current_cycle_run_id"]) >= int(EXECUTING_RUN_ID)
    blk = st["cycle_40284658455_operational_resume"]
    assert blk["resumed_snapshot"]["run_id"] == int(RESUMED_RUN_ID)
    assert "NON_PROMOTING" in blk["quarantine_verdict"]
    # The minted gate is never cited as an audit gate.
    blob = json.dumps(st)
    assert (f"CYCLE_{MINTED_GATE_RUN}_GATE.json" not in blob
            or "quarantine" in blob.lower())
    diag_ref = blk["diagnosis"]
    assert (ROOT / diag_ref).is_file()


def test_accepted_pointer_satisfies_both_halves_and_posture_stays_fail_closed():
    st = _load(STATE)
    # SUPERSESSION AMENDMENT: the pointer must be at least this cycle and must
    # satisfy both halves of requirement 4.  Literal run-id/commit equality
    # goes stale the moment a later cycle is legitimately accepted.
    pointer = str(st["accepted_run_id"])
    assert pointer.startswith("CYCLE_")
    assert int(pointer.split("_", 1)[1]) >= int(EXECUTING_RUN_ID)
    evidence = accepted_pointer_evidence(st, ROOT)
    assert evidence["problems"] == [], evidence
    assert evidence["gate_ok"] is True and evidence["accept_commit_present"] is True
    gate = _load(ROOT / evidence["gate"])
    assert gate["gate"] == "PASS" and gate["safe_to_integrate"] is True
    head = _git("ls-remote", "--heads", "origin", "refs/heads/lab/product")
    assert head.startswith(st["accepted_commit"]), (head, st["accepted_commit"])
    for key, expected in (
        ("continue_recommended", True),
        ("human_gate_ready", False),
        ("machine_gate_ready", False),
        ("packet_admitted", False),
        ("ready_for_owner_session", False),
        ("direction_version", 68),
    ):
        assert st[key] is expected or st[key] == expected, (key, st[key])


def test_resume_diagnosis_and_raw_snapshot_agree_with_the_workflow_records():
    diag = _load(DIAG)
    assert diag["run_id"] == RESUMED_RUN_ID
    assert diag["predecessor_run_id"] == MINTED_GATE_RUN
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE"
    assert orch["failed_step"] == "Enforce lane write scope"
    assert orch["mechanism"]["status"] == "OBSERVED_SCOPE_ENFORCEMENT_FAILED"
    assert orch["mechanism"]["quantum_expired"] is False
    assert orch["mechanism"]["lane_cycle_step_conclusion"] == "success"
    assert orch["audit"]["gate_file_written"] is False
    assert diag["self_minted_gate"]["verdict"] == "NON_PROMOTING"
    assert len(diag["failure_chain_diagnosis"]["runs"]) == 6

    raw = _load(RAW)
    assert raw["run"]["id"] == int(RESUMED_RUN_ID)
    team = next(j for j in raw["jobs"] if j["name"] == "team")
    steps = {s["name"]: s["conclusion"] for s in team["steps"]}
    assert steps["Run lane cycle"] == "success"
    assert steps["Enforce lane write scope"] == "failure"
    assert team["conclusion"] == "failure"


def test_audit_readiness_instrument_models_this_failure_mode():
    from product import audit_readiness as ar
    prof = ar.select_profile(EXECUTING_RUN_ID)
    assert prof["mechanism_kind"] == "observed_scope"
    assert prof["resumed_run_id"] == RESUMED_RUN_ID
    assert prof["cycle_test"] == "product/tests/test_cycle_40284658455.py"
    # Unknown run ids must still fail closed (no silent default inheritance).
    try:
        ar.select_profile("99999999999")
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("select_profile must fail closed on unknown runs")


def test_report_of_record_names_the_executing_run_and_the_quarantine():
    text = REPORT.read_text(encoding="utf-8")
    assert EXECUTING_RUN_ID in text
    assert RESUMED_RUN_ID in text
    assert "NON-PROMOTING" in text or "NON_PROMOTING" in text
    assert "SELF_MINTED" in text.upper() or "self-minted" in text.lower()
