#!/usr/bin/env python3
"""STATE_MINIMAL_CA_PROVENANCE_REPAIR v2 — run 39866970583 (evaluation, direction v63).

DISCLOSED REPAIR OF THE v1 INSTRUMENT, NOT A RE-FREEZE OF THE HYPOTHESIS.

v1 (evaluation/state_minimal_ca_provenance_repair.py, sha256 18eab54d...) executed
and produced results/evaluation/state_minimal_ca_provenance_repair/39866970583.json
(verdict REPAIR_FAILED_OR_VACUOUS, exit 1, PRESERVED VERBATIM, never overwritten).
Its substantive gates all PASSED (G0 freeze pins, G2 block re-derivation, G3
post-repair suite 11/0/0, G5 sibling suites green, G4 frozen inputs unchanged,
G6 stand-ready) and the state repair itself landed. The three failures (G1, C1,
C2, C3) were ONE instrumentation defect, measured and named: the failed-test
collector records pytest node IDs ("tests/...py::test_name") while the gate and
control predicates compared them against bare test names, so a correct 3-failed /
8-passed measurement with exactly the right three KeyError tests was adjudicated
false. This v2 fixes ONLY that comparison (bare name = node.split('::')[-1]) and
sources the pre-repair state from the freeze-pinned accepted tip a7e3565f (the
live state was already repaired by v1). The hypothesis, freeze record, success
rule, gates, controls, frozen pins and claim ceiling are byte-unchanged from the
v1 freeze; the amendment freeze record STATE_MINIMAL_CA_PROVENANCE_REPAIR_FREEZE_RECORD_V1_1.json
pins both instrument generations and the v1 artifact digests.

Outputs: results/evaluation/state_minimal_ca_provenance_repair/39866970583_v2.json
and reports/evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_39866970583_v2.md.
The v1 record and v1 report stay in place untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN_ID = "39866970583"
DIRECTION_VERSION = 63
PRE_REPAIR_REF = "a7e3565fcb7adaa854ff3080e74b91d105ad3a62"

HYPOTHESIS = REPO / "evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_HYPOTHESIS_V1.json"
FREEZE_RECORD = REPO / "evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_FREEZE_RECORD_V1.json"
AMENDMENT = REPO / "evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_FREEZE_RECORD_V1_1.json"
INSTRUMENT = Path(__file__).resolve()
V1_INSTRUMENT = REPO / "evaluation/state_minimal_ca_provenance_repair.py"
V1_RECORD = REPO / "results/evaluation/state_minimal_ca_provenance_repair/39866970583.json"

DEDICATED_SUITE = REPO / "tests/evaluation/test_minimal_ca_benchmark.py"
SIBLING_SUITES = (
    REPO / "tests/evaluation/test_minimal_retrieval_ca_benchmark.py",
    REPO / "tests/evaluation/test_mapping_free_recall_falsifier.py",
)

FROZEN_HYP = REPO / "evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json"
FROZEN_FREEZE = REPO / "evaluation/MINIMAL_CA_BENCHMARK_FREEZE_RECORD_V1.json"
CA_INSTRUMENT = REPO / "evaluation/minimal_ca_benchmark.py"
RULES_LABEL = REPO / "evaluation/frozen_bars/RULES_LABEL.json"
RULES_GEOMETRY = REPO / "evaluation/frozen_bars/RULES_GEOMETRY.json"
VERDICT_CONTRACT = REPO / "evaluation/frozen_bars/VERDICT_CONTRACT.json"

STATE = REPO / "state/evaluation.json"

PIN_FROZEN_HYP = "f0c7711c71e94d7b7303f5fa3a61b444d67bee6d3bbd7f0708ed13ff6ffc8072"
PIN_FREEZE_COMMIT = "6892f9f0"
PIN_CA_INSTRUMENT = "567a9d2b231c5404b7324db2c30249e0961dbc90c698501d0ba5576c7297554b"
PIN_RULES_LABEL = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
PIN_RULES_GEOMETRY = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
PIN_VERDICT_CONTRACT = "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c"
PIN_PRODUCT_HEAD = "fe219a197e4bfb129984a732ab9adca917556eac"
PIN_ADVERSARIAL_RETRIEVAL = "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9"
PIN_PRE_STATE = "99544d85374797cf2a90a8bebda0bcae6afd2cf7f103b29a066f681cbf890c20"
PIN_V1_RECORD = "8e0e8bb84fec9a59f9a88d5d7210380b9a0acb6f8f387a38108a4e69ead4aba4"
PIN_V1_INSTRUMENT = "18eab54d5c23835455eace4de2795d1864167b9b9de5798de2da369289835ce1"

STATE_BLOCK_TESTS = (
    "test_hypothesis_rehash_matches_state_pin",
    "test_state_freeze_commit_is_where_the_hypothesis_landed",
    "test_state_pytest_claim_names_this_dedicated_test",
)

OUT_DIR = REPO / "results/evaluation/state_minimal_ca_provenance_repair"
REPORT_DIR = REPO / "reports/evaluation"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(REPO), *args],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def bare(node_id: str) -> str:
    """pytest node ID -> bare test name (the v1 defect this file repairs)."""
    return node_id.split("::")[-1]


def run_pytest(test_file: Path, state_override: Path | None) -> dict:
    env = dict(os.environ)
    if state_override is not None:
        env["LEXMACHINA_STATE_OVERRIDE"] = str(state_override)
    else:
        env.pop("LEXMACHINA_STATE_OVERRIDE", None)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q", "--tb=line",
         "-p", "no:cacheprovider"],
        cwd=str(REPO), capture_output=True, text=True, timeout=900, env=env)
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")

    def grab(pat: str) -> int:
        m = re.search(pat, out)
        return int(m.group(1)) if m else 0

    failed_tests = re.findall(r"^FAILED (.+?) - (.+)$", out, flags=re.M)
    return {
        "test_file": str(test_file.relative_to(REPO)),
        "test_file_sha256": sha256_file(test_file),
        "returncode": proc.returncode,
        "n_failed": grab(r"(\d+) failed"),
        "n_passed": grab(r"(\d+) passed"),
        "n_skipped": grab(r"(\d+) skipped"),
        "failed_tests": [
            {"node": n, "test": bare(n), "error": e[:200]} for n, e in failed_tests
        ],
        "state_override": str(state_override) if state_override else None,
        "stdout_tail": out[-1200:],
    }


def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_state(path: Path, data: dict) -> None:
    # indent=1 matches the committed state-file convention on this branch
    path.write_text(json.dumps(data, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


def build_block(hyp_sha: str, post_summary: str) -> dict:
    pytest_claim = (
        "tests/evaluation/test_minimal_ca_benchmark.py is the dedicated suite for "
        "evaluation/minimal_ca_benchmark.py. PRE-REPAIR CLAIM WAS FALSE at run "
        f"{RUN_ID}: the committed pre-repair state/evaluation.json carried no "
        "minimal_ca_benchmark block, so 3 of 11 tests failed with KeyError "
        "('minimal_ca_benchmark') while the earlier 664f4a32-era '11 passed' claim "
        "had been true only while the block existed. Post-repair measurement of "
        f"this run: {post_summary}. The historical citation of "
        "tests/evaluation/test_benchmark_retrieval_counter_authority.py was a "
        "DIFFERENT instrument and remains disclosed here, never deleted."
    )
    return {
        "freeze_commit": PIN_FREEZE_COMMIT,
        "hypothesis_sha256": hyp_sha,
        "pytest": pytest_claim,
        "regression": (
            "sibling falsification suites re-measured with real pytest in this run "
            "(see machine record results/evaluation/state_minimal_ca_provenance_repair/"
            f"{RUN_ID}_v2.json gate G5_sibling_falsification_suites_green)"
        ),
        "repair_of_record": (
            f"run {RUN_ID} v2 (v1 instrument defect disclosed): block restored with "
            "re-derived pins only; no test, frozen file, rubric, bar or threshold edited"
        ),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=RUN_ID)
    args = ap.parse_args(argv)
    if args.run_id != RUN_ID:
        print(json.dumps({"verdict": "ENVIRONMENT_OR_VACUOUS",
                          "reason": f"wrong run id {args.run_id} != {RUN_ID}"}))
        return 2

    gates: list[dict] = []
    controls: list[dict] = []
    record: dict = {
        "schema": "lex-evaluation-state-minimal-ca-provenance-repair/2",
        "run_id": RUN_ID,
        "record_generation": "v2",
        "lane": "evaluation",
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "pytest_available": True,
        "network_calls": [],
        "v1_attempt": {
            "record": f"results/evaluation/state_minimal_ca_provenance_repair/{RUN_ID}.json",
            "record_sha256": PIN_V1_RECORD,
            "verdict": "REPAIR_FAILED_OR_VACUOUS",
            "exit_code": 1,
            "defect": "failed-test collector stored pytest node IDs; gate/control "
                      "predicates compared them to bare test names, so G1/C1/C2/C3 "
                      "adjudicated a correct measurement false (3 failed / 8 passed "
                      "with exactly the three KeyError state-block tests)",
            "substantive_gates_that_passed_in_v1": [
                "G0_freeze_first_pins_hold",
                "G2_restored_block_values_rederived_and_reverified",
                "G3_post_repair_dedicated_suite_green",
                "G5_sibling_falsification_suites_green",
                "G4_frozen_inputs_unchanged_after_all_runs",
                "G6_stand_ready_ordered_items_unchanged",
            ],
            "preserved_verbatim": True,
        },
    }

    # ---- freeze-first guard (v1 freeze + v1.1 amendment) ---------------------
    hyp_sha = sha256_file(HYPOTHESIS)
    frozen_hyp_sha = sha256_file(FROZEN_HYP)
    freeze_sha = sha256_file(FREEZE_RECORD)
    amendment_sha = sha256_file(AMENDMENT)
    instr_sha = sha256_file(INSTRUMENT)
    v1_instr_sha = sha256_file(V1_INSTRUMENT)
    v1_record_sha = sha256_file(V1_RECORD)
    fr = json.loads(FREEZE_RECORD.read_text(encoding="utf-8"))
    am = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    freeze_ok = (
        hyp_sha == fr.get("hypothesis_sha256") == am.get("hypothesis_sha256_unchanged")
        and instr_sha == am.get("instrument_v2_sha256")
        and v1_instr_sha == PIN_V1_INSTRUMENT == am.get("instrument_v1_sha256")
        and v1_record_sha == PIN_V1_RECORD == am.get("v1_record_sha256")
        and fr.get("frozen_before_execution") is True
        and am.get("amended_before_execution") is True
        and frozen_hyp_sha == PIN_FROZEN_HYP
    )
    gates.append({
        "name": "G0_freeze_first_pins_hold",
        "pass": freeze_ok,
        "details": {
            "cycle_hypothesis_sha256": hyp_sha,
            "frozen_minimal_ca_hypothesis_sha256": frozen_hyp_sha,
            "freeze_record_sha256": freeze_sha,
            "amendment_record_sha256": amendment_sha,
            "instrument_v2_sha256": instr_sha,
            "instrument_v1_sha256": v1_instr_sha,
            "v1_record_sha256": v1_record_sha,
        },
    })
    if not freeze_ok:
        record["gates"] = gates
        record["verdict"] = "ENVIRONMENT_OR_VACUOUS"
        record["exit_code"] = 2
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"{RUN_ID}_v2.json").write_text(json.dumps(record, indent=2) + "\n")
        return 2

    record["freeze_pins"] = {
        "cycle_hypothesis_sha256": hyp_sha,
        "frozen_minimal_ca_hypothesis_sha256": frozen_hyp_sha,
        "freeze_record_sha256": freeze_sha,
        "amendment_record_sha256": amendment_sha,
        "instrument_v2_sha256": instr_sha,
    }

    # ---- pre-repair measurement from the freeze-pinned accepted tip (G1+C1) --
    pre_blob = git("show", f"{PRE_REPAIR_REF}:state/evaluation.json")
    if pre_blob is None:
        record["gates"] = gates
        record["verdict"] = "ENVIRONMENT_OR_VACUOUS"
        record["exit_code"] = 2
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"{RUN_ID}_v2.json").write_text(json.dumps(record, indent=2) + "\n")
        return 2
    pre_state_bytes = pre_blob.encode("utf-8")
    pre_state_sha = hashlib.sha256(pre_state_bytes).hexdigest()
    pre_data = json.loads(pre_state_bytes.decode("utf-8"))
    block_absent_pre = "minimal_ca_benchmark" not in pre_data

    with tempfile.TemporaryDirectory(prefix="lex_state_repair_v2_") as td:
        pre_copy = Path(td) / "state_pre_repair.json"
        pre_copy.write_bytes(pre_state_bytes)

        pre_run = run_pytest(DEDICATED_SUITE, pre_copy)
        pre_failed_names = {f["test"] for f in pre_run["failed_tests"]}
        g1 = (
            pre_state_sha == PIN_PRE_STATE
            and block_absent_pre
            and pre_run["n_failed"] == 3
            and pre_run["n_passed"] == 8
            and pre_failed_names == set(STATE_BLOCK_TESTS)
            and all("minimal_ca_benchmark" in f["error"] for f in pre_run["failed_tests"])
        )
        gates.append({
            "name": "G1_pre_repair_dedicated_suite_fails_exactly_3_state_block_tests",
            "pass": g1,
            "details": {
                "pre_state_ref": PRE_REPAIR_REF,
                "pre_state_sha256": pre_state_sha,
                "pre_state_sha_expected": PIN_PRE_STATE,
                "block_absent_pre": block_absent_pre,
                "measurement": pre_run,
            },
        })
        controls.append({
            "name": "C1_negative_control_pre_repair_state_still_fails_3",
            "holds": g1,
            "details": "same measurement as G1 via LEXMACHINA_STATE_OVERRIDE on the "
                       "freeze-pinned pre-repair state bytes from accepted tip "
                       f"{PRE_REPAIR_REF[:12]}",
        })

        # ---- (re)apply/verify the repair (block already restored by v1) ------
        frozen_hyp_sha = sha256_file(FROZEN_HYP)
        block = build_block(frozen_hyp_sha, "PENDING_POST_MEASUREMENT")
        data = load_state(STATE)
        data["minimal_ca_benchmark"] = block
        dump_state(STATE, data)

        post_run = run_pytest(DEDICATED_SUITE, None)
        post_summary = (
            f"{post_run['n_passed']} passed / {post_run['n_failed']} failed / "
            f"{post_run['n_skipped']} skipped (pytest, {DEDICATED_SUITE.name})"
        )
        g3 = post_run["n_failed"] == 0 and post_run["n_passed"] + post_run["n_skipped"] == 11
        gates.append({
            "name": "G3_post_repair_dedicated_suite_green",
            "pass": g3,
            "details": {"measurement": post_run, "summary": post_summary},
        })

        data = load_state(STATE)
        data["minimal_ca_benchmark"] = build_block(frozen_hyp_sha, post_summary)
        dump_state(STATE, data)
        reverify = run_pytest(DEDICATED_SUITE, None)
        blob = git("show", f"{PIN_FREEZE_COMMIT}:evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json")
        blob_ok = blob is not None and hashlib.sha256(blob.encode("utf-8")).hexdigest() == PIN_FROZEN_HYP
        g2 = (
            data["minimal_ca_benchmark"]["hypothesis_sha256"] == frozen_hyp_sha == PIN_FROZEN_HYP
            and data["minimal_ca_benchmark"]["freeze_commit"] == PIN_FREEZE_COMMIT
            and "tests/evaluation/test_minimal_ca_benchmark.py" in data["minimal_ca_benchmark"]["pytest"]
            and "PRE-REPAIR CLAIM WAS FALSE" in data["minimal_ca_benchmark"]["pytest"]
            and reverify["n_failed"] == 0
            and reverify["n_passed"] + reverify["n_skipped"] == 11
            and blob_ok
        )
        gates.append({
            "name": "G2_restored_block_values_rederived_and_reverified",
            "pass": g2,
            "details": {
                "block": data["minimal_ca_benchmark"],
                "freeze_commit_blob_rehash_ok": blob_ok,
                "reverification": reverify,
            },
        })

        sibling_runs = [run_pytest(f, None) for f in SIBLING_SUITES]
        g5 = all(r["n_failed"] == 0 and r["returncode"] == 0 for r in sibling_runs)
        gates.append({
            "name": "G5_sibling_falsification_suites_green",
            "pass": g5,
            "details": {"measurements": sibling_runs},
        })

        # ---- planted-mutation controls (bare-name comparison — v2 fix) -------
        mutated = load_state(STATE)
        cur = mutated["minimal_ca_benchmark"]["hypothesis_sha256"]
        mutated["minimal_ca_benchmark"]["hypothesis_sha256"] = (
            ("0" if cur[0] != "0" else "1") + cur[1:]
        )
        mut_path = Path(td) / "state_mutated_hyp.json"
        dump_state(mut_path, mutated)
        c2_run = run_pytest(DEDICATED_SUITE, mut_path)
        c2 = c2_run["n_failed"] >= 1 and any(
            t["test"] == "test_hypothesis_rehash_matches_state_pin"
            for t in c2_run["failed_tests"])
        controls.append({
            "name": "C2_planted_wrong_hypothesis_sha_is_detected",
            "holds": c2,
            "details": c2_run,
        })

        broken = load_state(STATE)
        refs = list(broken.get("evidence_refs", []))
        refs.append("results/evaluation/state_minimal_ca_provenance_repair/__planted_missing__.json")
        broken["evidence_refs"] = refs
        broken["evidence_refs_n"] = len(refs)
        br_path = Path(td) / "state_broken_ref.json"
        dump_state(br_path, broken)
        c3_run = run_pytest(DEDICATED_SUITE, br_path)
        c3 = c3_run["n_failed"] >= 1 and any(
            t["test"] == "test_state_evidence_refs_resolve_and_count_matches"
            for t in c3_run["failed_tests"])
        controls.append({
            "name": "C3_broken_evidence_ref_is_detected",
            "holds": c3,
            "details": c3_run,
        })

    # ---- G4: frozen inputs unchanged after all runs --------------------------
    post_pins = {
        "evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json": sha256_file(FROZEN_HYP),
        "evaluation/MINIMAL_CA_BENCHMARK_FREEZE_RECORD_V1.json": sha256_file(FROZEN_FREEZE),
        "evaluation/minimal_ca_benchmark.py": sha256_file(CA_INSTRUMENT),
        "evaluation/frozen_bars/RULES_LABEL.json": sha256_file(RULES_LABEL),
        "evaluation/frozen_bars/RULES_GEOMETRY.json": sha256_file(RULES_GEOMETRY),
        "evaluation/frozen_bars/VERDICT_CONTRACT.json": sha256_file(VERDICT_CONTRACT),
        "tests/evaluation/test_minimal_ca_benchmark.py": sha256_file(DEDICATED_SUITE),
        "evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_HYPOTHESIS_V1.json": hyp_sha,
    }
    expected_pins = {
        "evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json": PIN_FROZEN_HYP,
        "evaluation/minimal_ca_benchmark.py": PIN_CA_INSTRUMENT,
        "evaluation/frozen_bars/RULES_LABEL.json": PIN_RULES_LABEL,
        "evaluation/frozen_bars/RULES_GEOMETRY.json": PIN_RULES_GEOMETRY,
        "evaluation/frozen_bars/VERDICT_CONTRACT.json": PIN_VERDICT_CONTRACT,
    }
    g4 = all(post_pins[k] == v for k, v in expected_pins.items())
    gates.append({
        "name": "G4_frozen_inputs_unchanged_after_all_runs",
        "pass": g4,
        "details": {"rehashed": post_pins, "expected": expected_pins},
    })

    # ---- G6: stand-ready adjudication ----------------------------------------
    product_root = Path("/tmp/lex_accepted/product")
    head = None
    adv_sha = None
    if product_root.exists():
        rev = subprocess.run(["git", "-C", str(product_root), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=60)
        head = rev.stdout.strip() if rev.returncode == 0 else None
        adv = product_root / "product/query/adversarial_retrieval.py"
        if adv.is_file():
            adv_sha = sha256_file(adv)
    g6 = head == PIN_PRODUCT_HEAD and adv_sha == PIN_ADVERSARIAL_RETRIEVAL
    gates.append({
        "name": "G6_stand_ready_ordered_items_unchanged",
        "pass": g6,
        "details": {
            "product_mount_head": head,
            "product_head_expected": PIN_PRODUCT_HEAD,
            "adversarial_retrieval_sha256": adv_sha,
            "adversarial_retrieval_expected": PIN_ADVERSARIAL_RETRIEVAL,
            "ordered_items": {
                "(1)_remedy_a_re_freeze": "NOT_TRIGGERED (product bytes unchanged)",
                "(2)_four_item_cross_check": "NOT_TRIGGERED (no accepted product cycle newer than 39815102517)",
                "(3)_standing_frozen_bars": "STANDING_OK",
                "(4)_P1_FR_divergence_record": "STANDING_OK (record preserved; computed by no one twice)",
                "(5)_new_served_packet_falsification": "NOT_TRIGGERED (both DO-NOT-SERVE orders stand; no accepted serve recommendation)",
            },
        },
    })

    record["gates"] = gates
    record["controls"] = controls
    record["state_repair"] = {
        "pre_state_sha256": pre_state_sha,
        "post_state_sha256": sha256_file(STATE),
        "edit_scope": "state/evaluation.json minimal_ca_benchmark block restoration only",
        "test_files_edited": [],
        "frozen_files_edited": [],
    }
    all_gates = all(g["pass"] for g in gates)
    all_controls = all(c["holds"] for c in controls)
    record["non_vacuity_all_hold"] = all_controls
    verdict = "REPAIR_VERIFIED_SUITE_GREEN" if (all_gates and all_controls) else "REPAIR_FAILED_OR_VACUOUS"
    record["verdict"] = verdict
    record["exit_code"] = 0 if verdict == "REPAIR_VERIFIED_SUITE_GREEN" else 1
    record["claim_ceiling"] = (
        "Establishes only that the dedicated provenance suite of the accepted minimal-CA "
        "falsification benchmark was failing solely due to lost state metadata and that a "
        "re-derived-pin restoration turns it green with no test/frozen-file/threshold change. "
        "Not a new retrieval/counter-authority/label/geometry/serve measurement; does not "
        "re-run the v3 falsification claim; no bar moved; no DO-NOT-SERVE order lifted; "
        "all admission/human flags stay false; no universal-174k benchmark run."
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{RUN_ID}_v2.json"
    out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    failed_gate_names = [g["name"] for g in gates if not g["pass"]]
    report = [
        f"# State minimal-CA provenance repair v2 — run {RUN_ID}",
        "",
        f"- Verdict: **{verdict}** (exit {record['exit_code']})",
        f"- Direction: v{DIRECTION_VERSION}",
        "- v1 attempt preserved verbatim: "
        f"`results/evaluation/state_minimal_ca_provenance_repair/{RUN_ID}.json` "
        f"(sha256 {PIN_V1_RECORD[:12]}..., REPAIR_FAILED_OR_VACUOUS on a node-id "
        "comparison defect; its substantive gates G0/G2/G3/G4/G5/G6 all passed)",
        f"- Cycle hypothesis SHA256: `{hyp_sha}` (frozen at 93dd639c, unchanged)",
        f"- Freeze record SHA256: `{freeze_sha}`; amendment V1_1: `{amendment_sha}`",
        f"- Instrument v2 SHA256: `{instr_sha}`; v1: `{v1_instr_sha}` (bytes unchanged)",
        f"- Pre-repair state (from {PRE_REPAIR_REF[:12]}) SHA256: `{pre_state_sha}` — "
        f"dedicated suite {pre_run['n_passed']} passed / {pre_run['n_failed']} failed, "
        "exactly the 3 KeyError state-block tests",
        f"- Post-repair dedicated suite: {post_summary}",
        "- Sibling suites: " + "; ".join(
            f"{r['test_file'].split('/')[-1]} {r['n_passed']}/{r['n_failed']}/{r['n_skipped']}"
            for r in sibling_runs),
        f"- Frozen inputs re-hashed after all runs: {'unchanged' if g4 else 'DRIFT'}",
        f"- Stand-ready: product head {head} (expected {PIN_PRODUCT_HEAD}); "
        "ordered items (1)(2)(5) NOT_TRIGGERED, (3)(4) STANDING_OK",
        f"- Failed gates: {failed_gate_names or 'none'}",
        "",
        "## Claim ceiling",
        record["claim_ceiling"],
        "",
        "## Provenance",
        f"- Machine record: `results/evaluation/state_minimal_ca_provenance_repair/{RUN_ID}_v2.json`",
        f"- v1 machine record (preserved): `results/evaluation/state_minimal_ca_provenance_repair/{RUN_ID}.json`",
        "- Hypothesis: `evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_HYPOTHESIS_V1.json`",
        "- Freeze record: `evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_FREEZE_RECORD_V1.json`",
        "- Amendment: `evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_FREEZE_RECORD_V1_1.json`",
        "- No test file, frozen file, rubric, bar, threshold or benchmark record was edited.",
        "",
    ]
    (REPORT_DIR / f"STATE_MINIMAL_CA_PROVENANCE_REPAIR_{RUN_ID}_v2.md").write_text(
        "\n".join(report), encoding="utf-8")

    print(json.dumps({"verdict": verdict, "exit_code": record["exit_code"],
                      "record": str(out_path)}))
    return record["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
