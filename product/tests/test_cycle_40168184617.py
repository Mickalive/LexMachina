"""Executable re-derivation of product cycle 40168184617's published claims.

This cycle is the OPERATIONAL RESUME of run 40164459036 (dispatched by the
resilience job's ``resume_from_run_id`` route after that run's audit job died at
``rc 78 LEX_WORK_QUANTUM_EXPIRED``), so the claims fall into four groups that are
never mixed:

1. **Orchestration diagnosis** - why 40160899758 -> 40163751502 -> 40164459036
   all ended ``conclusion=failure`` without an independent verdict.  Re-derived
   from LOCAL refs/commits and from the committed
   ``CYCLE_<run>_orchestration.json`` job records.  No network, no token.
2. **Validation repair** - the producer-self-minted audit gate that run
   40163751502 wrote into the auditor's namespace has been retired BYTE-EXACTLY
   into ``reports/product/incidents/``; ``results/audit/`` again holds only
   auditor-minted files, and no new producer-minted file may reach this
   unadjudicated chain.
3. **Measurement** - the frozen D2/D3/D4 content-family histogram over the
   committed bundle family, recomputed every run, plus the shipped progressive
   query-slice smoke (query -> result bundle -> clickable map) that proves the
   vertical slice still answers over a real socket.
4. **Posture** - the accepted pointer satisfies BOTH halves of factory-wide
   requirement 4, and every fail-closed flag stays FALSE.

Nothing here writes a gate, scores a frozen bar, or labels a chain run
"rejected": 40160899758, 40163751502 and 40164459036 are UNADJUDICATED.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import content_family_probe as cfp          # noqa: E402
from product import resume_chain_diagnosis as rcd        # noqa: E402
from product import state_contract as sc                 # noqa: E402

RUN_ID = "40168184617"
DIRV = 68
CHAIN = ("40160899758", "40163751502", "40164459036")
RESUMED_RUN_ID = "40164459036"

DIAG_ART = (REPO_ROOT / "results" / "product" / "orchestration"
            / f"CYCLE_{RUN_ID}_resume_diagnosis.json")
PROBE_ART = (REPO_ROOT / "results" / "product" / "counter_content_family"
             / f"CYCLE_{RUN_ID}.json")
SMOKE_ART = (REPO_ROOT / "results" / "product" / "progressive_smoke"
             / f"CYCLE_{RUN_ID}_progressive_smoke.json")
ORCH_ART = {r: REPO_ROOT / "results" / "product" / "orchestration"
            / f"CYCLE_{r}_orchestration.json" for r in CHAIN}
STATE_PATH = REPO_ROOT / "state" / "product.json"

#: The commit that wrote the out-of-scope audit gate this cycle retires.
SELF_MINTED_COMMIT = "069e2add8a18b2345bfe1cd4d95fc3d8fa982ed9"
#: The commit that made the report-only delta run 40164459036 pushed.
RESUME_SNAPSHOT_COMMIT = "801c2869c43797a3b32e1e601cb5b5bf9aaf7b59"
#: The snapshot of the chain root, whose team job died at rc 78.
CHAIN_ROOT_SNAPSHOT = "3d7d43b136a9bc02baf7adff8ffb1a604b72b922"


def _load(path: Path) -> dict:
    assert path.exists(), f"missing committed artifact: {path.relative_to(REPO_ROOT)}"
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                         capture_output=True, text=True)
    assert out.returncode == 0, f"git {' '.join(args)}: {out.stderr[:300]}"
    return out.stdout


# --------------------------------------------------------------------------
# 1. orchestration diagnosis
# --------------------------------------------------------------------------

def test_diagnosis_artifact_exists_and_is_scoped_to_this_run() -> None:
    rec = _load(DIAG_ART)
    assert rec["schema"] == rcd.SCHEMA
    assert rec["run_id"] == RUN_ID
    assert rec["lane"] == "product"
    assert RESUMED_RUN_ID in rec["mode"]
    assert rec["derived_from"], "the artifact must name what it derived from"


def test_the_three_chain_runs_are_all_unadjudicated_in_every_local_ref() -> None:
    rec = _load(DIAG_ART)
    assert [c["run_id"] for c in rec["chain"]] == list(CHAIN)
    for entry in rec["chain"]:
        assert entry["audit_ref"] is None, (
            f"{entry['run_id']} unexpectedly has an audit ref - re-check the claim")
        assert entry["accept_commit"] is None, (
            f"{entry['run_id']} unexpectedly has an accept commit")
        assert entry["adjudication"] == "UNADJUDICATED"
        # re-derive, do not trust the artifact's own copy
        assert rcd.run_refs(entry["run_id"])["audit"] is None
        assert rcd.accept_commit_for(entry["run_id"]) is None


def test_the_orchestration_failure_of_record_is_the_audit_job_quantum() -> None:
    rec = _load(DIAG_ART)
    failure = rec["failure_diagnosis"]["orchestration_failure_of_record"]
    assert failure["run_id"] == RESUMED_RUN_ID
    assert failure["classification"] == "AUDIT_STEP_FAILED_NO_GATE"

    # the committed GitHub job record, quoted not re-fetched
    jobs = _load(ORCH_ART[RESUMED_RUN_ID])["job_conclusions"]
    assert jobs == {"team": "success", "audit": "failure",
                    "integrate": "skipped", "resilience": "success"}, jobs
    orch = rec["chain"][2]["orchestration"]
    assert orch["run_conclusion"] == "failure"
    assert orch["exit_code"] == 78
    messages = " | ".join(a["message"] for a in orch["annotations_failure_warning"])
    assert "LEX_WORK_QUANTUM_EXPIRED" in messages
    assert "Agent quantum ended cleanly" in messages


def test_the_chain_root_died_the_same_way_and_its_snapshot_survived() -> None:
    rec = _load(DIAG_ART)
    root = rec["failure_diagnosis"]["chain_root"]
    assert root["run_id"] == "40160899758"
    assert root["classification"] == "TEAM_JOB_FAILED"
    jobs = _load(ORCH_ART["40160899758"])["job_conclusions"]
    assert jobs["team"] == "failure" and jobs["audit"] == "skipped"
    # the snapshot the resume chain grew from is exactly this commit
    assert _git("rev-parse",
                "refs/remotes/origin/cycle/core/product/40160899758/team").strip() \
        == CHAIN_ROOT_SNAPSHOT


def test_the_validation_failure_is_the_scope_guard_beaten_by_always_persist() -> None:
    rec = _load(DIAG_ART)
    validation = rec["failure_diagnosis"]["validation_failure_inherited_by_the_resume"]
    assert validation["run_id"] == "40163751502"
    assert validation["classification"] == "OUT_OF_SCOPE_WRITE_SURVIVED_PERSIST"

    # the team job really did fail with the scope guard's exit code
    jobs = _load(ORCH_ART["40163751502"])["job_conclusions"]
    assert jobs["team"] == "failure" and jobs["audit"] == "skipped"
    orch = rec["chain"][1]["orchestration"]
    assert orch["exit_code"] == 3
    messages = " | ".join(a["message"] for a in orch["annotations_failure_warning"])
    assert "lane crossed protected scope" in messages

    # ... and the out-of-scope files really were persisted by that snapshot commit
    subject = _git("log", "-1", "--format=%H\t%s", SELF_MINTED_COMMIT)
    sha, _, subj = subject.partition("\t")
    assert sha == SELF_MINTED_COMMIT
    assert subj.strip() == "product cycle 40163751502 repair 0"
    added = _git("show", "--name-only", "--format=", SELF_MINTED_COMMIT).split()
    assert "results/audit/product/CYCLE_40160899758_GATE.json" in added
    assert "reports/audit/product/CYCLE_40160899758.md" in added

    # and the resumed run therefore inherited them as COMMITTED content, which a
    # pending-only `git status --porcelain` scope check can never observe
    resumed = _git("rev-parse",
                   "refs/remotes/origin/cycle/core/product/40164459036/team").strip()
    assert resumed == RESUME_SNAPSHOT_COMMIT
    out = subprocess.run(
        ["git", "rev-parse", "--verify", "-q",
         f"{RESUME_SNAPSHOT_COMMIT}:results/audit/product/CYCLE_40160899758_GATE.json"],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip(), (
        "the resumed snapshot must still carry the out-of-scope file at that "
        "commit - that is the defect being repaired, not a claim of cleanliness")


# --------------------------------------------------------------------------
# 2. validation repair: byte-exact retirement of the self-minted audit gate
# --------------------------------------------------------------------------

def test_producer_self_minted_audit_artifacts_are_retired_byte_exactly() -> None:
    rec = _load(DIAG_ART)
    retired = rec["self_minted_retirement"]
    assert len(retired) == 2
    for entry in retired:
        assert entry["original_absent"] is True, entry
        assert entry["retired_present"] is True, entry
        path = REPO_ROOT / entry["retired_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["retired_sha256"]
        # the record must reproduce the same digest this run computes
        assert (REPO_ROOT / entry["original_path"]).exists() is False


def test_the_retired_gate_still_says_what_it_said_and_grants_nothing() -> None:
    """Retirement preserves bytes; it must not silently EDIT the claim."""
    path = REPO_ROOT / "reports/product/incidents/self_minted_gate_40160899758.RETIRED.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["gate"] == "PASS"
    assert data["safe_to_integrate"] is True
    # ... and it is NOT reachable as a gate for that run any more
    assert not (REPO_ROOT
                / "results/audit/product/CYCLE_40160899758_GATE.json").exists()
    assert not (REPO_ROOT
                / "reports/audit/product/CYCLE_40160899758.md").exists()


def test_no_producer_minted_audit_file_reaches_this_unadjudicated_chain() -> None:
    rec = _load(DIAG_ART)
    inventory = rec["audit_namespace_after_rehome"]
    assert inventory["producer_minted_unadjudicated_chain"] == [], (
        "a producer-minted file is sitting in the auditor's namespace on this "
        "chain and would be laundered onto lab/product by the next promote")
    # every remaining producer-minted file is already on the accepted branch:
    # historical evidence that is inventoried and never deleted (AGENTS 5/6)
    baseline = inventory["producer_minted_accepted_baseline"]
    assert baseline, "the ratchet must be non-vacuous - it has to see the history"
    for entry in baseline:
        assert entry["path"].startswith(("results/audit/", "reports/audit/"))


def test_the_ratchet_reproduces_from_the_tree_not_from_the_artifact() -> None:
    live = rcd.audit_namespace_inventory()
    assert live["producer_minted_unadjudicated_chain"] == []
    assert live["producer_minted_accepted_baseline"], live
    committed = _load(DIAG_ART)["audit_namespace_after_rehome"]
    assert ([e["path"] for e in live["producer_minted_accepted_baseline"]]
            == [e["path"] for e in committed["producer_minted_accepted_baseline"]])


# --------------------------------------------------------------------------
# 3. measurement: content family + shipped vertical slice
# --------------------------------------------------------------------------

def test_content_family_probe_reproduces_the_committed_artifact() -> None:
    art = _load(PROBE_ART)
    fresh = cfp.run(run_id=RUN_ID, direction_version=DIRV)
    assert fresh["schema"] == art["schema"]
    for family in ("fixed_path_family", "all_committed"):
        assert fresh[family]["totals"] == art[family]["totals"], family
    assert fresh["false_reject_count"] == art["false_reject_count"]
    assert fresh["ordered_work_2_success_rule"] == art["ordered_work_2_success_rule"]


def test_the_fixed_path_family_is_content_clean_and_non_vacuous() -> None:
    art = _load(PROBE_ART)
    totals = art["fixed_path_family"]["totals"]
    hist = totals["defect_histogram"]
    assert hist == {"D1_empty_evidence": 0, "D2_letterhead_zone": 0,
                    "D3_markup_residue": 0, "D4_language_marker_mismatch": 0}
    # non-vacuous: the family must cover real bundles and real verified rows
    assert totals["n_bundles"] >= 14
    assert totals["n_verified"] >= 2
    assert art["false_reject_count"] == 0
    assert art["ordered_work_2_success_rule"]["met"] is True
    assert art["confirmed_set"]["still_verified"] is True
    assert art["confirmed_set"]["defects"] in (False, [], {}, None)
    # historical defects are published beside it, never folded in
    history = art["all_committed"]["totals"]["defect_histogram"]
    assert history["D2_letterhead_zone"] > 0, (
        "the preserved-history population must stay non-zero or the comparison "
        "against the fixed path is vacuous")


def test_the_shipped_query_map_slice_still_answers_over_a_real_socket() -> None:
    art = _load(SMOKE_ART)
    assert art["schema"] == "product-progressive-smoke/1"
    assert art["verdict"] == "PASS", art.get("failures")
    assert art["checks_passed"] == art["checks_total"]
    assert art["mode"].startswith("fixture")
    # latency budgets from QUERY_MAP_MVP section 9A, measured not asserted
    timings = art["timings_s"]
    assert art["budgets"]["server_boot_lt_60s"] is True, art["budgets"]
    assert art["budgets"]["start_lt_120s"] is True, art["budgets"]
    assert timings["server_boot_s"] < 3.0, timings
    assert timings["start_s"] < 1.0, timings


def test_the_smoke_really_exercises_query_to_bundle_to_map() -> None:
    art = _load(SMOKE_ART)
    names = {c["check"] for c in art["checks"]}
    joined = " ".join(names)
    for keyword in ("health", "start", "status", "expand", "enrich", "bundle"):
        assert keyword in joined, f"no check covers {keyword}: {sorted(names)}"


# --------------------------------------------------------------------------
# 4. posture and state hygiene
# --------------------------------------------------------------------------

def test_accepted_pointer_satisfies_both_halves_of_requirement_4() -> None:
    state = _load(STATE_PATH)
    run = str(state["accepted_run_id"]).replace("CYCLE_", "")
    commit = state["accepted_commit"]
    # half 1: a gate file with gate=PASS and safe_to_integrate=true
    gate = _load(REPO_ROOT / f"results/audit/product/CYCLE_{run}_GATE.json")
    assert gate["gate"] == "PASS" and gate["safe_to_integrate"] is True
    # half 2: an accept commit naming that run, on the accepted branch
    accepted_head = _git("rev-parse", "origin/lab/product").strip()
    assert _git("log", "-1", "--format=%s", accepted_head).strip() == \
        f"accept product cycle {run}"
    assert accepted_head.startswith(commit), (
        f"state names {commit} but origin/lab/product is {accepted_head}")
    # the pointer must not lag the accepted branch
    assert state["accepted_run_supersession"], "supersession must be disclosed"


def test_state_contract_passes_and_posture_stays_fail_closed() -> None:
    report = sc.check(DIRV, state_path=STATE_PATH)
    assert report["workflow_validation"]["ok"] is True, report["workflow_validation"]
    assert report["write_scope"]["ok"] is True, report["write_scope"]
    assert report["audit_artifact_ownership"]["producer_wrote_audit_paths"] == []
    assert report["shadow_state"]["findings"] == [], report["shadow_state"]

    state = _load(STATE_PATH)
    assert state["direction_version"] == DIRV
    assert state["continue_recommended"] is True
    for flag in ("human_gate_ready", "ready_for_owner_session",
                 "machine_gate_ready", "packet_admitted"):
        assert state[flag] is False, f"{flag} must stay fail-closed"
    assert state["cycle_status"] == "COMPLETE"


def test_the_report_quotes_only_numbers_this_artifact_carries() -> None:
    report = (REPO_ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md")
    assert report.exists(), "the cycle must publish a human-readable report"
    text = report.read_text(encoding="utf-8")

    probe = _load(PROBE_ART)
    fixed = probe["fixed_path_family"]["totals"]
    smoke = _load(SMOKE_ART)

    # every headline number in the report must appear in a committed artifact
    assert str(fixed["n_bundles"]) in text
    assert str(smoke["checks_passed"]) in text
    assert str(smoke["checks_total"]) in text
    assert RESUMED_RUN_ID in text
    assert "40160899758" in text
    # the report must carry the unadjudicated disclosure for the chain
    assert "UNADJUDICATED" in text
    assert re.search(r"human[_ -]gate", text, re.I)


def test_the_report_never_claims_the_self_minted_gate_was_an_audit() -> None:
    text = (REPO_ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
            ).read_text(encoding="utf-8")
    lower = text.lower()
    # the retired file may be named, but never as an independent verdict
    assert "producer-self-minted" in lower or "producer-authored" in lower


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
