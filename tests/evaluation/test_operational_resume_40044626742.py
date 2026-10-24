"""Guard suite for evaluation operational-resume run 40044626742.

Every test re-derives a claim made in
results/evaluation/orchestration/40044626742_verification_of_40040574595.json
and reports/evaluation/OPERATIONAL_RESUME_40044626742.md from committed bytes.
Executed under evaluation/no_pytest_runner.py (pytest is ABSENT in the producer
image); UNSUPPORTED is counted not-run, never passed.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOUNT = Path("/tmp/lex_accepted/product")
RUN = "40044626742"
PROD = "40040574595"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip(o):
    if isinstance(o, dict):
        return {
            k: _strip(v)
            for k, v in o.items()
            if k not in ("run_id", "generated_at_utc", "generated_at", "elapsed",
                         "elapsed_s", "out_path", "report_path", "result_file",
                         "report_file", "engine_record_path", "wrapper_record_path",
                         "out", "report")
            and not (isinstance(v, str) and (f"/{PROD}" in v or f"/{RUN}" in v))
        }
    if isinstance(o, list):
        return [_strip(v) for v in o]
    if isinstance(o, str):
        return o.replace(RUN, "RUNID").replace(PROD, "RUNID")
    return o


def test_producer_snapshot_commits_are_the_history_base():
    out = subprocess.run(
        ["git", "log", "--format=%H %s", "-4"], cwd=ROOT,
        capture_output=True, text=True, check=True).stdout
    assert "e9f3f37924d9f7aad90a902bcc8c0f0b73effd01" in out  # producer results commit
    assert "d264936094987d99f222a85159ad08a5a0306cbd" in out  # producer freeze commit
    assert "23459653" in out  # this run's freeze commit


def test_producer_result_bytes_untouched():
    committed = subprocess.run(
        ["git", "show", f"e9f3f379:results/evaluation/v65_head_advance_crosscheck/{PROD}.json"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout
    on_disk = (ROOT / f"results/evaluation/v65_head_advance_crosscheck/{PROD}.json").read_text()
    assert committed == on_disk


def test_instrument_and_runner_shas_unchanged():
    assert _sha(ROOT / "evaluation/v65_head_advance_crosscheck_v2.py") == \
        "8a7e19c9f1c31bbc38ebc4c921bf7bb9e0a436aae8738268cc21b1bbd6671eeb"
    assert _sha(ROOT / "evaluation/no_pytest_runner.py") == \
        "c12097da9d910574380b32c5dafa371a3b24ec14ef2551d92bb9453b8ed57584"


def test_resume_reexecution_normalized_identical_to_producer():
    a = json.loads((ROOT / f"results/evaluation/v65_head_advance_crosscheck/{PROD}.json").read_text())
    b = json.loads((ROOT / f"results/evaluation/v65_head_advance_crosscheck/{RUN}.json").read_text())
    assert _strip(a) == _strip(b)


def test_resume_headlines_match_pre_registered_targets():
    b = json.loads((ROOT / f"results/evaluation/v65_head_advance_crosscheck/{RUN}.json").read_text())
    assert b["verdict"] == "PASS_NO_FALSIFICATION" and b["exit_code"] == 0
    cur = b["currency_crosscheck"]
    assert cur["n_confirmed"] == 36 and cur["n_divergent"] == 0
    probe = b["shipped_slice_counter_evidence_probe"]
    assert probe["H2_verdict"] == "H2_FALSIFIED"
    assert probe["n_verified_rows_total"] == 14
    assert probe["n_verified_rows_with_defects"] == 14
    assert probe["defect_histogram"] == {
        "D2_letterhead_zone": 10, "D3_markup_residue": 4,
        "D4_language_marker_mismatch": 4}
    assert b["falsification_rerun"]["verdict"] == "PRODUCT_FALSIFIED"
    assert b["falsification_rerun"]["input_drift"] == []
    assert b["requirement_4_lineage"]["all_accepted"] is True
    assert all(v["passed"] for v in b["controls"].values())


def test_attempt1_preserved_and_lineage_only_failure():
    p = ROOT / ("results/evaluation/v65_head_advance_crosscheck/"
                f"{RUN}_attempt1_shallow_mount_lineage_vacuous.json")
    a1 = json.loads(p.read_text())
    assert a1["verdict"] == "NOT_MEASURED_VACUOUS" and a1["exit_code"] == 2
    assert a1["requirement_4_lineage"]["all_accepted"] is False
    # every measurement leg identical to the measurement of record
    a1c = dict(a1["currency_crosscheck"])
    b = json.loads((ROOT / f"results/evaluation/v65_head_advance_crosscheck/{RUN}.json").read_text())
    assert a1c["n_confirmed"] == b["currency_crosscheck"]["n_confirmed"] == 36
    assert a1["shipped_slice_counter_evidence_probe"]["H2_verdict"] == "H2_FALSIFIED"
    assert a1["falsification_rerun"]["verdict"] == "PRODUCT_FALSIFIED"


def test_shim_records_match_claims():
    self_ = json.loads((ROOT / f"results/evaluation/orchestration/{RUN}_self_suite_pytest_shim.json").read_text())
    assert (self_["n_passed"], self_["n_failed"], self_["n_unsupported"]) == (12, 0, 0)
    ml = json.loads((ROOT / f"results/evaluation/orchestration/{RUN}_multiling_prov_pytest_shim.json").read_text())
    assert (ml["n_passed"], ml["n_failed"], ml["n_unsupported"]) == (73, 0, 0)
    ff = json.loads((ROOT / f"results/evaluation/orchestration/{RUN}_falsification_family_pytest_shim.json").read_text())
    assert (ff["n_passed"], ff["n_failed"], ff["n_unsupported"]) == (51, 0, 21)


def test_freeze_record_pins_rehash():
    rec = json.loads((ROOT / "evaluation/V65_HEAD_ADVANCE_CROSSCHECK_FREEZE_RECORD_V2.json").read_text())
    assert _sha(ROOT / "evaluation/V65_HEAD_ADVANCE_CROSSCHECK_FREEZE_RECORD_V2.json") == \
        "c954f62cfab2b5c31b228c59268ad63f5f3536b00c9cf8be9f5551c28155b586"
    ok = 0
    for label, expected in rec["frozen_pins"].items():
        if label.startswith("repo:"):
            path = ROOT / label[len("repo:"):]
        else:
            path = MOUNT / label[len("mount:"):]
        assert path.exists(), label
        assert _sha(path) == expected, label
        ok += 1
    assert ok == 23


def test_state_run_identity_and_accepted_run_id():
    s = json.loads((ROOT / "state/evaluation.json").read_text())
    assert s["direction_version"] == 65
    assert s["cycle_status"] == "COMPLETE"
    assert s["github_run"] == RUN and s["proposed_run_id"] == RUN
    assert s["accepted_run_id"] == "40034814235"
    assert s["accepted_run_id_advance"]["from"] == "39986080045"
    sup = s["accepted_run_id_advance"]["superseded_advance"]
    assert sup["from"] == "39927760701" and sup["to"] == "39986080045"
    # exactly one wrap - no deeper nesting of correction blocks
    assert "superseded_advance" not in sup


def test_no_accept_commit_exists_for_39986080045():
    out = subprocess.run(
        ["git", "log", "--all", "--format=%s"], cwd=ROOT,
        capture_output=True, text=True, check=True).stdout
    assert "accept evaluation cycle 39986080045" not in out
    assert "accept evaluation cycle 40034814235" in out
    assert "accept evaluation cycle 40012474431" in out
    assert "accept evaluation cycle 40002636192" in out


def test_evidence_index_resolves_and_counts():
    s = json.loads((ROOT / "state/evaluation.json").read_text())
    refs = s["evidence_refs"]
    assert s["evidence_refs_n"] == len(refs)
    missing = [r for r in refs if not (ROOT / r).exists()]
    assert missing == []
    # the producer-removed dangling ref stays removed
    assert "results/evaluation/orchestration/40011795717/producer_work_state_and_next_move.txt" not in refs


def test_posture_flags_stay_fail_closed():
    s = json.loads((ROOT / "state/evaluation.json").read_text())
    for k in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
              "ready_for_owner_session", "owner_decision_required"):
        assert s[k] is False, k
    assert s["continue_recommended"] is True
    assert s["lane"] == "evaluation"
    assert "accepted_run_id" in s and "evidence_refs" in s
    assert "next_recommendation" in s and s["next_recommendation"]


def test_resume_block_and_verification_verdict():
    s = json.loads((ROOT / "state/evaluation.json").read_text())
    blk = s["operational_resume_40044626742"]
    assert blk["resumed_from_run"] == PROD
    assert blk["verdict"] == "RESUME_VERIFIED_AND_AUDIT_READY"
    v = json.loads((ROOT / "results/evaluation/orchestration/40044626742_verification_of_40040574595.json").read_text())
    assert v["VERDICT"] == "PRODUCER_SNAPSHOT_VERIFIED_AND_AUDIT_READY"
    assert v["V1_full_instrument_reexecution"]["normalized_comparison_vs_40040574595"]["total_diffs"] == 0


def test_no_frozen_rubric_or_packet_bytes_edited_by_resume():
    s = json.loads((ROOT / "state/evaluation.json").read_text())
    # frozen rubric pins still the accepted digests
    assert s["benchmark_result"]["frozen_label_rubric_sha256"] == \
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    label = ROOT / "evaluation/frozen_bars/RULES_LABEL.json"
    geom = ROOT / "evaluation/frozen_bars/RULES_GEOMETRY.json"
    assert _sha(label) == "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    assert _sha(geom) == "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
    packet = MOUNT / "results/product/gate_packet/39319405429/packet.json"
    assert _sha(packet) == "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"
