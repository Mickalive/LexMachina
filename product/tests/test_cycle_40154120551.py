"""Executable re-derivation of product cycle 40154120551's published claims.

This cycle is the operational resume of run 40152073380, so the test covers
three kinds of claim and never mixes them:

1. **Diagnosis claims** about the two UNADJUDICATED predecessor runs
   (40147748763, 40152073380) and about the shadow-state validation failure
   that was reproducible on the inherited snapshot.  Everything here is
   re-derived from the LOCAL repository (refs, commits, gate files, the
   snapshot's own bytes).  No network, no token, no GitHub REST - the log
   endpoint is not available to a producer, so the job-log text stays
   recorded-as-unavailable instead of being invented.
2. **Measurement claims** - the frozen D2/D3/D4 content-family histogram and
   the MVP core-suite size - recomputed from the committed bytes every run.
3. **Posture claims** about ``state/product.json``: the accepted pointer, the
   fail-closed flags and the retirement of the shadow copy.

No network, no LLM, no frozen bar scored, no gate file written.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import content_family_probe as cfp  # noqa: E402
from product import state_contract as sc  # noqa: E402

RUN_ID = "40154120551"
RESUMED_RUN_ID = "40152073380"
PRECEDING_RUN_ID = "40147748763"
LAST_ACCEPTED_RUN_ID = "40139832004"
DIRV = 68

#: The commit that persisted the producer snapshot this cycle resumes from.
SNAPSHOT_COMMIT = "a1de800b4d4248f2f3b17320611b06cc36fbd724"
#: The commit that REINTRODUCED the shadow state file.
SHADOW_REINTRODUCED_BY = "122bf6af646098445d8b95d8bfb778b2bff1f220"
#: The commit of the last cycle that had already retired the shadow file.
SHADOW_ALREADY_RETIRED_AT = "81a9dfa152aa309b31424c9b85d1c4c55608178a"

PROBE_ART = (REPO_ROOT / "results" / "product" / "counter_content_family"
             / f"CYCLE_{RUN_ID}.json")
DIAG_ART = (REPO_ROOT / "results" / "product" / "orchestration"
            / f"CYCLE_{RUN_ID}_resume_diagnosis.json")
REPORT = REPO_ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
STATE_PATH = REPO_ROOT / "state" / "product.json"
SHADOW_PATH = REPO_ROOT / "product" / "state" / "product.json"

#: The nine files whose 170 collected tests are the "MVP core suite" figure.
MVP_CORE_SUITE = (
    "product/tests/test_query_map_mvp.py",
    "product/tests/test_server_query_api.py",
    "product/tests/test_offline_slice.py",
    "product/tests/test_progressive_smoke.py",
    "product/tests/test_adversarial_retrieval.py",
    "product/tests/test_counter_evidence_span.py",
    "product/tests/test_counter_content_rejection_v68.py",
    "product/tests/test_state_contract.py",
    "product/tests/test_progressive_query.py",
)
MVP_CORE_SUITE_COLLECTED = 170


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True,
        timeout=60, check=False,
    )


# --------------------------------------------------------------------------- #
# 1. diagnosis claims
# --------------------------------------------------------------------------- #

def test_diagnosis_artifact_exists_and_is_scoped_to_this_run() -> None:
    rec = _load(DIAG_ART)
    assert rec["schema"] == "product-resume-diagnosis/2"
    assert rec["run_id"] == RUN_ID
    assert rec["lane"] == "product"
    assert rec["direction_version"] == DIRV
    assert RESUMED_RUN_ID in rec["mode"]
    snap = rec["observed_snapshot"]
    assert snap["team_commit"] == SNAPSHOT_COMMIT
    assert snap["resumed_from_run"] == RESUMED_RUN_ID
    assert snap["last_accepted_cycle"]["run_id"] == LAST_ACCEPTED_RUN_ID
    assert rec["continue_recommended"] is True
    assert rec["human_gate_ready"] is False
    assert rec["ready_for_owner_session"] is False


def test_the_snapshot_commit_really_is_the_persisted_producer_head() -> None:
    out = _git("show", "-s", "--format=%H %s", SNAPSHOT_COMMIT)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split()[0] == SNAPSHOT_COMMIT
    assert f"product cycle {RESUMED_RUN_ID}" in out.stdout
    # the predecessor run really did add the shadow file we removed
    out = _git("show", "--stat", "--format=", SHADOW_REINTRODUCED_BY)
    assert out.returncode == 0, out.stderr
    assert "product/state/product.json" in out.stdout


def test_both_predecessor_runs_are_unadjudicated_in_every_local_ref() -> None:
    """No gate file and no accept commit exists for either resumed run."""
    for run in (PRECEDING_RUN_ID, RESUMED_RUN_ID):
        gate = _git("log", "--all", "--oneline", "--",
                    f"results/audit/product/CYCLE_{run}_GATE.json")
        assert gate.stdout.strip() == "", f"gate file appeared for {run}"
        rep = _git("log", "--all", "--oneline", "--",
                   f"reports/audit/product/CYCLE_{run}.md")
        assert rep.stdout.strip() == "", f"audit report appeared for {run}"
        acc = _git("log", "--all", "--oneline",
                   f"--grep=^accept product cycle {run}$")
        assert acc.stdout.strip() == "", f"accept commit appeared for {run}"


def test_no_audit_ref_for_the_resumed_runs() -> None:
    """Optional network check: never asserted offline, skipped when absent.

    The offline half of the same claim (no gate file, no audit report and no
    accept commit in any locally-known ref) is asserted unconditionally by
    ``test_both_predecessor_runs_are_unadjudicated_in_every_local_ref``.
    """
    for run in (PRECEDING_RUN_ID, RESUMED_RUN_ID):
        out = _git("ls-remote", "origin",
                   f"refs/heads/cycle/core/product/{run}/audit")
        if out.returncode != 0:
            pytest.skip(f"origin unreachable: {out.stderr.strip()[:200]}")
        assert out.stdout.strip() == "", f"audit ref appeared for {run}"


def test_diagnosis_records_unavailable_evidence_as_unavailable() -> None:
    """A job-log we cannot read is recorded unavailable, never invented."""
    rec = _load(DIAG_ART)
    ofr = rec["failure_diagnosis"]["orchestration_failure_of_record"]
    assert ofr["exact_job_log_text_available"] is False
    assert "unavailable" in ofr["why_unavailable"]
    assert "403" in ofr["why_unavailable"]
    assert "UNADJUDICATED" in ofr["consequence"]
    # no gate verdict is claimed anywhere in the failure diagnosis
    assert '"gate"' not in json.dumps(rec["failure_diagnosis"])
    # the only PASS named is the accepted cycle's own gate
    assert rec["observed_snapshot"]["last_accepted_cycle"]["gate"] == "PASS"


def test_the_snapshot_shadow_diverged_and_the_contract_now_passes() -> None:
    # the shadow's own bytes are still reachable from the snapshot commit,
    # so the diagnosis can be re-derived without re-creating the file
    show = _git("show", f"{SNAPSHOT_COMMIT}:product/state/product.json")
    assert show.returncode == 0, show.stderr
    shadow = json.loads(show.stdout)
    canonical = _load(STATE_PATH)
    assert shadow["accepted_run_id"] == PRECEDING_RUN_ID
    assert shadow["human_gate_ready"] is True
    assert shadow != canonical
    # after the repair no shadow exists and the contract check is green
    assert not SHADOW_PATH.exists()
    assert sc.shadow_state_findings() == []
    ok, _msg = sc.workflow_validation(DIRV, STATE_PATH)
    assert ok
    report = sc.check(DIRV)
    assert report["ok"] is True, json.dumps(report, indent=1)[:2000]
    assert report["write_scope"]["ok"] is True
    assert report["audit_artifact_ownership"]["producer_wrote_audit_paths"] == []
    # the producer never mints its own gate file
    assert not (REPO_ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN_ID}_GATE.json").exists()


# --------------------------------------------------------------------------- #
# 2. measurement claims
# --------------------------------------------------------------------------- #

def test_content_family_probe_reproduces_the_committed_artifact() -> None:
    fresh = cfp.run(run_id=RUN_ID, direction_version=DIRV)
    committed = _load(PROBE_ART)
    for rec, label in ((fresh, "fresh"), (committed, "committed")):
        totals = rec["fixed_path_family"]["totals"]
        hist = totals["defect_histogram"]
        assert hist["D2_letterhead_zone"] == 0, (label, hist)
        assert hist["D3_markup_residue"] == 0, (label, hist)
        assert hist["D4_language_marker_mismatch"] == 0, (label, hist)
        assert hist["D1_empty_evidence"] == 0, (label, hist)
        assert rec["false_reject_count"] == 0, label
        assert rec["ordered_work_2_success_rule"]["met"] is True, label
        assert rec["ordered_work_2_success_rule"]["confirmed_sound_row_still_verified"] is True
        assert totals["n_bundles"] >= 14, (label, totals)
        assert totals["n_decisions"] == totals["n_bundles"] * 100
    # the two records agree on every number we quote
    assert (fresh["fixed_path_family"]["totals"]
            == committed["fixed_path_family"]["totals"])
    assert (fresh["all_committed"]["totals"]["defect_histogram"]
            == committed["all_committed"]["totals"]["defect_histogram"])


def test_historical_defects_are_published_beside_the_fixed_path_family() -> None:
    rec = _load(PROBE_ART)
    hist = rec["all_committed"]["totals"]["defect_histogram"]
    assert hist["D2_letterhead_zone"] > 0  # preserved evidence, not zeroed
    assert rec["all_committed"]["totals"]["n_bundles"] >= 100
    assert rec["all_committed"]["totals"]["n_bundles"] > \
        rec["fixed_path_family"]["totals"]["n_bundles"]
    # the fixed-path family is a strict subset population, never a rewrite of
    # the historical one: the historical histogram stays non-zero and intact
    assert rec["all_committed"]["totals"]["defect_histogram"] != \
        rec["fixed_path_family"]["totals"]["defect_histogram"]


def test_the_resumed_snapshot_bundle_is_still_clickable() -> None:
    """The inherited deliverable is verified, not merely present."""
    bundle = (REPO_ROOT / "results" / "product" / "offline_slice"
              / "20261025T015155Z" / "rent-default.bundle.json")
    summary_path = bundle.parent / "summary.json"
    assert bundle.is_file() and summary_path.is_file()
    summary = _load(summary_path)
    assert summary["verified"] is True
    assert summary["page_contract"] is True
    assert summary["page_contract_detail"] == "PASS 68 assertions"
    stats = summary["stats"]
    assert stats["n_decisions"] == 100
    assert stats["n_clusters"] == 8
    assert stats["rows_with_xy"] == 100
    assert stats["rows_with_cluster_id"] == 100
    assert stats["rows_with_source_url"] == 100
    assert stats["answer_status"] == "ready"
    assert stats["cited_decision_ids"] == 4
    assert stats["fixture_replay"]["network"] == "none"
    # the summary must be reachable from the diagnosis artifact we publish
    diag = _load(DIAG_ART)
    published = diag["runnable_verification_this_cycle"][
        "resumed_snapshot_slice_summary"]
    assert published["stats"] == stats
    if shutil.which("node") is None:
        pytest.skip("node unavailable; summary assertions above still ran")
    proc = subprocess.run(
        ["node", str(PRODUCT_ROOT / "verify_query_page.js"), str(bundle)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "PASS 68 assertions" in proc.stdout
    assert "FAIL" not in proc.stdout


def test_test_delta_attribution_is_quoted_verbatim_by_this_report() -> None:
    """cycle_verify's (test_delta) leg must find its citing report."""
    art = (REPO_ROOT / "results" / "product" / "regression"
           / f"CYCLE_{RUN_ID}_test_delta_attribution.json")
    assert art.is_file()
    data = _load(art)
    assert str(data["run_id"]) == RUN_ID
    assert data["base"]["commit"].startswith(SNAPSHOT_COMMIT[:7])
    # the committed head decomposition is self-consistent and quoted verbatim
    line = data["decomposition_line"]
    assert line == (f"collected-test delta {SNAPSHOT_COMMIT[:7]} -> head "
                    "= +0 = +0  ()")
    tree = data["working_tree"]
    assert tree["reconciles"] is True
    mods = {u["module"]: u["delta"] for u in tree["uncommitted_test_modules"]}
    assert set(mods) == {f"test_cycle_{RUN_ID}.py"}
    assert tree["attributed_delta"] == sum(mods.values())
    assert tree["collected_total"] == (
        tree["head_collected_total"] + tree["attributed_delta"])
    text = REPORT.read_text(encoding="utf-8")
    assert art.name in text, "the report must cite the artifact by name"
    assert line in text, "the report must quote the decomposition verbatim"
    assert tree["decomposition_line"] in text, \
        "the report must quote the working-tree decomposition verbatim"
    # and the number the prose states next to it is the measured one
    assert f"+{tree['attributed_delta']}" in text
    if data["steps"]:
        assert sum(s["collected_delta_vs_previous_step"]
                   for s in data["steps"]) == data["observed_collected_delta"]
    else:
        assert data["observed_collected_delta"] == 0


def test_mvp_core_suite_collects_the_published_number_of_tests() -> None:
    for rel in MVP_CORE_SUITE:
        assert (REPO_ROOT / rel).is_file(), rel
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         *MVP_CORE_SUITE],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout[-3000:]
    collected = [ln.strip() for ln in proc.stdout.splitlines()
                 if re.match(r"^\d+ tests? collected\b", ln.strip())]
    assert collected, proc.stdout[-3000:]
    n = int(collected[-1].split()[0])
    assert n == MVP_CORE_SUITE_COLLECTED, n
    for needle in (f"{MVP_CORE_SUITE_COLLECTED} passed",):
        assert needle in _load(DIAG_ART)["runnable_verification_this_cycle"][
            "mvp_core_suite"], "diagnosis quotes the suite size"
        assert needle in REPORT.read_text(encoding="utf-8"), \
            "report quotes the suite size"


# --------------------------------------------------------------------------- #
# 3. posture claims
# --------------------------------------------------------------------------- #

def test_accepted_pointer_is_the_only_cycle_with_both_halves() -> None:
    st = _load(STATE_PATH)
    assert st["accepted_run_id"] == f"CYCLE_{LAST_ACCEPTED_RUN_ID}"
    assert st["accepted_commit"] == "e53662be8"
    assert st["direction_version"] == DIRV
    assert (REPO_ROOT / "results" / "audit" / "product"
            / f"CYCLE_{LAST_ACCEPTED_RUN_ID}_GATE.json").is_file()
    gate = _load(REPO_ROOT / "results" / "audit" / "product"
                 / f"CYCLE_{LAST_ACCEPTED_RUN_ID}_GATE.json")
    assert gate["gate"] == "PASS"
    assert gate["safe_to_integrate"] is True
    acc = _git("log", "--all", "--oneline", "--grep=^accept product cycle "
               f"{LAST_ACCEPTED_RUN_ID}$")
    assert LAST_ACCEPTED_RUN_ID in acc.stdout


def test_posture_stays_fail_closed_and_the_shadow_is_named_as_removed() -> None:
    st = _load(STATE_PATH)
    for flag in ("machine_gate_ready", "human_gate_ready", "packet_admitted",
                 "ready_for_owner_session"):
        assert st[flag] is False, flag
    assert st["continue_recommended"] is True
    rec = st["cycle_40154120551_operational_resume"]
    assert rec["direction_version"] == DIRV
    assert f"CYCLE_{RUN_ID}_resume_diagnosis.json" in rec["diagnosis_artifact"]
    assert f"CYCLE_{RUN_ID}.md" in rec["report_of_record"]
    assert "shadow state copy" in rec["failure_of_record"]
    assert "exited 3" in rec["failure_of_record"]
    diag = _load(DIAG_ART)
    before = diag["failure_diagnosis"]["validation_failure_reproducible_on_the_snapshot"]
    assert before["before_repair"]["exit_code"] == 3
    assert "exit code 3" in before["before_repair"]["pytest"] or \
        "3 failed, 26 passed" in before["before_repair"]["pytest"]
    assert before["after_repair"]["exit_code"] == 0
    assert "29 passed" in before["after_repair"]["pytest"]
    assert rec["continue_recommended"] is True
    # the rescued capability map survived the deletion
    assert st["capabilities"]["clickable_map"] is True
    assert st["capabilities"]["rejection_incumbent_leg"] is True
    assert "40154120551" in st["capabilities"]["source"]
    # ordered-work pointers stay honest
    assert "DEFERRED" in st["next_recommendation"]
    assert "UNADJUDICATED" in st["next_recommendation"]
    assert "CYCLE_40139832004" in st["next_recommendation"]


def test_the_producer_never_writes_an_audit_gate_path() -> None:
    bad = sc.audit_artifact_violations([
        f"results/audit/product/CYCLE_{RUN_ID}_GATE.json",
        f"reports/audit/product/CYCLE_{RUN_ID}.md",
    ])
    assert bad == [
        f"results/audit/product/CYCLE_{RUN_ID}_GATE.json",
        f"reports/audit/product/CYCLE_{RUN_ID}.md",
    ]
    assert sc.check(DIRV, paths=list(MVP_CORE_SUITE))["ok"] is True


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
