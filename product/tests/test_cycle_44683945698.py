"""Cycle 44683945698 — operational resume of the failed run 44683121773.

Re-derives, from committed bytes and git refs only, every number published in
``reports/product/CYCLE_44683945698.md`` and in the ``cycle_44683945698_
operational_resume`` block of ``state/product.json``:

1. the six-run chain diagnosis (three audit quantum expiries, two zero-delta
   team exits, one write-scope exit 3 whose unique violation is the
   producer-minted gate) and the UNADJUDICATED status of every run;
2. the quarantine sidecar: the minted gate is preserved verbatim, its bytes
   hash to the recorded sha256, and it is marked NON_PROMOTING;
3. the resumed snapshot's 23-file committed delta and its failed step;
4. the query-specific vertical slice, re-counted from the bundle bytes the
   state now publishes (live OpenCaseLaw run + the genuinely local offline
   path + the real-socket progressive smoke);
5. the fail-closed state posture: accepted pointer unchanged, no gate minted,
   the minted gate relabelled, and no producer write into the auditor
   namespace.

No network, no model, no paid dependency, no frozen bar re-scored here.
"""
from __future__ import annotations

import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUN = "44683945698"
RESUMED = "44683121773"
SNAPSHOT = "0765fc3546e19710f4911c30ed56a9ee5ace3a88"
PREDECESSOR = "89ed3bc95fe5c6324714b4af172a2098ca43458c"
ACCEPTED_RUN = "CYCLE_40284658455"
ACCEPTED_COMMIT = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
MINTED = "results/audit/product/CYCLE_44675979766_GATE.json"
QUARANTINE = ("results/product/incidents/"
              "self_minted_gate_44675979766_producer_44683121773."
              "QUARANTINED.json")
LIVE_BUNDLE = "results/product/live_slice/44683945698_bundle.json"
LIVE_SLICE = "results/product/live_slice/44683945698.json"
OFFLINE_DIR = "results/product/offline_slice/20261120T060613Z"
SMOKE = ("results/product/progressive_smoke/"
         f"CYCLE_{RUN}_progressive_smoke.json")
COUNTER_ROLES = {"candidate-limiting", "candidate-contrary",
                 "abstained_unevidenced"}


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), check=True,
                          capture_output=True, text=True).stdout


def _sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# 1. chain diagnosis
# --------------------------------------------------------------------------- #

def test_chain_diagnoses_six_runs_all_unadjudicated():
    diag = _load(f"results/product/orchestration/CYCLE_{RUN}_chain_diagnosis.json")
    summary = diag["summary"]
    assert diag["accepted_ref"] == "origin/lab/product"
    assert diag["accepted_ref_sha"].startswith(ACCEPTED_COMMIT[:8])
    assert summary["runs_diagnosed"] == 6
    assert summary["accepted"] == []
    assert summary["unadjudicated"] == [
        "44661217001", "44669305676", "44675979766",
        "44682634688", "44682877714", RESUMED]
    assert summary["runs_whose_audit_hit_work_quantum"] == [
        "44661217001", "44669305676", "44675979766"]
    assert summary["all_runs_have_public_run_jobs_evidence"] is True


def test_write_scope_violation_is_unique_and_named():
    diag = _load(f"results/product/orchestration/CYCLE_{RUN}_chain_diagnosis.json")
    failing = diag["summary"]["runs_failing_write_scope"]
    assert [f["run_id"] for f in failing] == [RESUMED]
    assert failing[0]["violations"] == [MINTED]
    entry = next(e for e in diag["runs"] if e["run_id"] == RESUMED)
    assert entry["write_scope_exit_would_be"] == 3
    assert entry["audit_namespace_writes"] == [MINTED]
    assert entry["delta_path_count"] == 23
    assert entry["audit_ref_exists"] is False
    assert entry["accept_commit_on_accepted_ref"] is False
    assert entry["adjudication"] == "UNADJUDICATED"


def test_chain_reproduces_from_git_refs():
    paths = _git("diff", "--name-only", PREDECESSOR, SNAPSHOT).splitlines()
    assert len(paths) == 23
    assert paths.count(MINTED) == 1
    # applying the workflow's own scope predicate to the delta
    from product import state_contract as sc  # noqa: WPS433
    assert sc.scope_violations(paths) == [MINTED]
    assert sc.audit_artifact_violations(paths) == [MINTED]


def test_zero_delta_runs_really_share_one_head():
    diag = _load(f"results/product/orchestration/CYCLE_{RUN}_chain_diagnosis.json")
    by_id = {e["run_id"]: e for e in diag["runs"]}
    for run in ("44682634688", "44682877714"):
        assert by_id[run]["delta_path_count"] == 0
        assert by_id[run]["team_sha"] == by_id["44675979766"]["team_sha"]
        assert by_id[run]["orchestration"]["failed_team_step"] == "Run lane cycle"
    assert by_id["44675979766"]["orchestration"]["quantum_expired"] is True
    assert by_id["44675979766"]["orchestration"]["quantum_seconds"] == 2700
    assert by_id["44675979766"]["orchestration"]["failed_audit_step"] == (
        "Independent audit")


def test_no_audit_ref_exists_for_any_diagnosed_run():
    for run in ("44661217001", "44669305676", "44675979766",
                "44682634688", "44682877714", RESUMED):
        ref = f"origin/cycle/core/product/{run}/audit"
        assert subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref],
                              cwd=str(ROOT)).returncode != 0, ref
    assert not (ROOT / "reports/audit/product/CYCLE_44675979766.md").exists()


# --------------------------------------------------------------------------- #
# 2. quarantine of the producer-minted gate
# --------------------------------------------------------------------------- #

def test_minted_gate_is_preserved_and_hashed_by_the_sidecar():
    side = _load(QUARANTINE)
    assert side["class"] == "PRODUCER_MINTED_AUDIT_GATE"
    assert side["verdict"] == "NON_PROMOTING"
    assert side["recorded_by_run_id"] == RUN
    art = side["minted_artifact"]
    assert art["path"] == MINTED
    assert art["preserved_verbatim"] is True
    assert (ROOT / MINTED).is_file(), "the minted file must never be deleted"
    assert _sha256(MINTED) == art["sha256"]
    assert (ROOT / MINTED).stat().st_size == art["bytes"]
    # the committed content is quoted, not paraphrased
    live = json.loads((ROOT / MINTED).read_text(encoding="utf-8"))
    assert art["content_as_committed"]["gate"] == live["gate"] == "PASS"
    assert art["content_as_committed"]["safe_to_integrate"] is True
    assert "Cited decisions: 0" in live["evidence_summary"]
    assert "7 cited decisions" in live["claim_ceiling"]


def test_minted_gate_was_added_by_the_resumed_producer_only():
    out = _git("log", "--diff-filter=A", "--format=%H %s", "--", MINTED)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1
    sha, subject = lines[0].split(" ", 1)
    assert sha == SNAPSHOT
    assert subject == f"product cycle {RESUMED} repair 0"


def test_no_gate_was_minted_for_this_run():
    assert not (ROOT / f"results/audit/product/CYCLE_{RUN}_GATE.json").exists()
    assert not (ROOT / f"reports/audit/product/CYCLE_{RUN}.md").exists()


# --------------------------------------------------------------------------- #
# 3. resumed snapshot diagnosis
# --------------------------------------------------------------------------- #

def test_resumed_snapshot_has_a_committed_delta_and_no_adjudication():
    diag = _load(f"results/product/orchestration/CYCLE_{RUN}_resume_diagnosis.json")
    assert diag["run_id"] == RESUMED
    assert diag["predecessor_run_id"] == "44675979766"
    orch = diag["orchestration"]
    assert orch["classification"] == "TEAM_JOB_FAILED_OTHER_STEP"
    assert orch["team"]["failed_step"] == "Enforce lane write scope"
    assert orch["team"]["write_scope_step_conclusion"] == "failure"
    assert orch["team"]["team_snapshot_persisted_after_failed_team_job"] is True
    assert orch["audit"]["conclusion"] == "skipped"
    assert orch["audit"]["gate_file_written"] is False
    assert orch["mechanism"]["exit_code"] == 3
    assert orch["mechanism"]["logs_endpoint_status"] == 403
    assert orch["mechanism"]["quantum_expired"] is False
    assert "lane crossed protected scope:" in orch["observed_failure"]["messages"]
    delta = diag["durable_delta"]
    assert delta["classification"] == "COMMITTED_DELTA"
    assert delta["snapshot_head"] == SNAPSHOT
    assert delta["predecessor_head"] == PREDECESSOR
    assert delta["changed_files"] == 23
    assert diag["adjudication"]["status"] == "UNADJUDICATED"
    assert diag["adjudication"]["accepted"] is False
    minted = diag["audit_namespace"]["producer_minted_unadjudicated_chain"]
    assert [m["path"] for m in minted] == [MINTED]


# --------------------------------------------------------------------------- #
# 4. the vertical slice, re-counted from bundle bytes
# --------------------------------------------------------------------------- #

def test_live_bundle_bytes_match_the_published_state_numbers():
    doc = _load(LIVE_BUNDLE)
    st = _load("state/product.json")["vertical_slice_verification"]
    assert st["run_id"] == int(RUN)
    dec = doc["decisions"]
    statuses = collections.Counter(r.get("counter_status", "none") for r in dec)
    m = st["measurements"]
    assert m["n_decisions"] == len(dec) == 158
    assert m["n_clusters"] == len(doc["clusters"]) == 8
    assert m["n_cited_decisions"] == len(doc["answer"]["cited_decision_ids"]) == 6
    assert m["n_counter_authorities"] == sum(
        v for k, v in statuses.items() if k in COUNTER_ROLES) == 10
    assert m["n_counter_status_bearing_rows"] == sum(
        v for k, v in statuses.items() if k != "none") == 16
    assert m["counter_status_distribution"] == dict(sorted(statuses.items()))
    assert m["answer_status"] == doc["answer"]["status"] == "ready"
    assert m["rows_with_xy"] == len(dec)
    assert m["rows_with_source_url"] == len(dec)
    assert m["rows_with_cluster_id"] == len(dec)
    assert m["coordinates_bounded_in_unit_square"] is True
    assert all(-1.0 <= r["x"] <= 1.0 and -1.0 <= r["y"] <= 1.0 for r in dec)
    assert doc["query"] == st["primary_evidence"]["query"]


def test_live_run_proved_fresh_opencaselaw_retrieval():
    art = _load(LIVE_SLICE)
    assert art["run_id"] == RUN
    assert art["verdict"] == "PASS"
    assert art["n_failed_checks"] == []
    assert len(art["checks"]) == 11
    assert all(art["checks"].values())
    fresh = art["freshness"]
    assert fresh["adapter_cache_hits"] == 0
    assert fresh["adapter_network_calls"] == 8
    assert art["checks"]["independent_probe_saw_the_network"] is True
    assert fresh["independent_cache_probe"]["files_added"], "the independent probe recorded the files it saw appear"
    assert art["retrieval_mode_served"] == "refresh"
    assert art["page_contract"]["ok"] is True
    assert art["posture"]["human_gate_ready"] is False
    assert art["posture"]["machine_gate_ready"] is False


def test_local_offline_path_is_fast_and_network_free():
    summary = _load(f"{OFFLINE_DIR}/summary.json")
    doc = _load(f"{OFFLINE_DIR}/rent-default.bundle.json")
    assert summary["verified"] is True
    assert summary["stats"]["n_decisions"] == len(doc["decisions"]) == 100
    assert summary["stats"]["n_clusters"] == len(doc["clusters"]) == 8
    assert summary["stats"]["rows_with_xy"] == 100
    assert summary["stats"]["rows_with_source_link"] == 100
    assert summary["stats"]["fixture_replay_cache_misses"] == 0
    assert doc["answer"]["status"] == "ready"
    assert len(doc["answer"]["cited_decision_ids"]) == 4
    st = _load("state/product.json")["vertical_slice_verification"]
    local = st["local_offline_path"]
    assert local["n_decisions"] == 100
    assert local["n_cited_decisions"] == 4
    assert local["seconds"] == 1.998


def test_progressive_smoke_passed_over_a_real_socket():
    smoke = _load(SMOKE)
    assert smoke["run_id"] == RUN
    assert smoke["verdict"] == "PASS"
    assert smoke["checks_passed"] == smoke["checks_total"] == 23
    assert smoke["failures"] == []
    assert smoke["timings_s"]["server_boot_s"] < 60


# --------------------------------------------------------------------------- #
# 5. state posture, corrections and scope
# --------------------------------------------------------------------------- #

def test_posture_and_accepted_pointer_unchanged():
    st = _load("state/product.json")
    assert st["direction_version"] == 68
    assert st["cycle_status"] == "COMPLETE"
    assert st["accepted_run_id"] == ACCEPTED_RUN
    assert st["accepted_commit"] == ACCEPTED_COMMIT
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session"):
        assert st[key] is False, key
    assert st["continue_recommended"] is True


def test_false_audit_claims_were_retracted_not_deleted():
    st = _load("state/product.json")
    v = st["vertical_slice_verification"]
    assert v["gate_status"] == "ABSENT_UNADJUDICATED"
    assert v["audit_gate"] is None
    assert v["safe_to_integrate"] is False
    assert v["supersedes"]["cycle_id"] == "CYCLE_44675979766"
    entry = next(r for r in st["evidence_refs"]
                 if isinstance(r, dict) and r["ref"] == "CYCLE_44675979766_GATE.json")
    assert entry["type"] == "producer_minted_gate_quarantined"
    assert entry["status"] == "NON_PROMOTING"
    assert entry["quarantine"] == QUARANTINE
    assert entry["corrected_by_run"] == int(RUN)


def test_state_block_records_the_chain_and_the_corrections():
    block = _load("state/product.json")["cycle_44683945698_operational_resume"]
    assert block["resumed_run_id"] == int(RESUMED)
    assert block["current_run_id"] == int(RUN)
    assert block["direction_version"] == 68
    chain = block["chain_diagnosis"]
    assert chain["runs"] == 6
    assert chain["accepted"] == []
    assert chain["audit_quantum_expiries"] == [
        44661217001, 44669305676, 44675979766]
    assert chain["zero_durable_delta"] == [44682634688, 44682877714]
    assert chain["write_scope_failure"]["unique_violation"] == MINTED
    assert block["quarantine"]["verdict"] == "NON_PROMOTING"
    assert block["quarantine"]["sha256"] == _sha256(MINTED)
    assert [c["field"] for c in block["state_corrections"]] == [
        "vertical_slice_verification",
        "evidence_refs[CYCLE_44675979766_GATE.json]",
        "cycle_status"]
    assert block["claim_impact"].startswith("none:")
    assert block["continue_recommended"] is True


def test_this_cycle_never_wrote_the_auditor_namespace():
    # every path this run touched must satisfy the workflow's own predicate
    out = _git("status", "--porcelain", "-uall")
    paths = [ln[3:] for ln in out.splitlines() if len(ln) > 3]
    from product import state_contract as sc  # noqa: WPS433
    assert sc.scope_violations(paths) == [], paths
    assert sc.audit_artifact_violations(paths) == [], paths
    committed = sc._committed_audit_artifacts()
    assert MINTED in committed, "the historical minted file stays visible"
    assert f"results/audit/product/CYCLE_{RUN}_GATE.json" not in committed


def test_claim_ceiling_of_every_new_artifact_disclaims_a_verdict():
    chain = _load(f"results/product/orchestration/CYCLE_{RUN}_chain_diagnosis.json")
    assert "never writes" in chain["claim_ceiling"] or "no audit gate" in chain["claim_ceiling"]
    side = _load(QUARANTINE)
    assert side["verdict"] == "NON_PROMOTING"
    st = _load("state/product.json")["vertical_slice_verification"]
    assert "no independent audit gate exists" in st["note"].lower()
