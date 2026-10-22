#!/usr/bin/env python3
"""STATE_MINIMAL_CA_PROVENANCE_REPAIR — run 39866970583 (evaluation lane, direction v63).

Closes the one open audit caveat against the lane's smallest executable
retrieval/counter-authority falsification benchmark: the dedicated provenance
suite ``tests/evaluation/test_minimal_ca_benchmark.py`` was failing 3/11 tests
solely because ``state/evaluation.json`` lost its ``minimal_ca_benchmark``
provenance block between accepted cycles 39806933576 (block present) and the
accepted tip (block absent; the 39854748616 audit gate recorded the resulting
SHIM_FAIL as "infrastructure issue only").

What this instrument does, in order:

1. Freeze-first guard: re-hash the frozen hypothesis, its freeze record and
   this instrument's own committed bytes; exit 2 on any drift.
2. G1/C1: run the dedicated suite with ``LEXMACHINA_STATE_OVERRIDE`` pointed at
   an untouched copy of the committed PRE-REPAIR state; expect exactly the 3
   state-block tests failing with ``KeyError: 'minimal_ca_benchmark'``.
3. G2: surgically restore the ``minimal_ca_benchmark`` block into
   ``state/evaluation.json`` using ONLY re-derived values (live re-hash of the
   frozen hypothesis; freeze commit 6892f9f0 blob re-hash; honest claim text
   carrying the PRE-REPAIR CLAIM WAS FALSE disclosure).
4. G3: run the dedicated suite against the repaired state; expect zero failures.
5. G5: run the two sibling falsification suites (minimal_retrieval_ca_benchmark,
   mapping_free_recall_falsifier); expect zero failures.
6. C2/C3: planted-mutation controls must be detected.
7. G4: re-hash every frozen input again after all runs; must be unchanged.
8. G6: stand-ready adjudication of the v63 ordered items against the accepted
   product mount (fe219a19 / planner 9764a37e...).
9. Write the machine record and the lane report; exit 0 only if every gate and
   control holds.

No test file, frozen file, rubric, bar, threshold or benchmark record is
edited. The only content edit is the lane-owned state block restoration plus
this run's state reconciliation fields (applied by the lane after execution).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN_ID = "39866970583"
DIRECTION_VERSION = 63

HYPOTHESIS = REPO / "evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_HYPOTHESIS_V1.json"
FREEZE_RECORD = REPO / "evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_FREEZE_RECORD_V1.json"
INSTRUMENT = Path(__file__).resolve()

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

# re-derived pins (values confirmed by live re-hash at freeze time)
PIN_FROZEN_HYP = "f0c7711c71e94d7b7303f5fa3a61b444d67bee6d3bbd7f0708ed13ff6ffc8072"
PIN_FREEZE_COMMIT = "6892f9f0"
PIN_CA_INSTRUMENT = "567a9d2b231c5404b7324db2c30249e0961dbc90c698501d0ba5576c7297554b"
PIN_RULES_LABEL = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
PIN_RULES_GEOMETRY = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
PIN_VERDICT_CONTRACT = "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c"

PIN_PRODUCT_HEAD = "fe219a197e4bfb129984a732ab9adca917556eac"
PIN_ADVERSARIAL_RETRIEVAL = "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9"

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


def run_pytest(test_file: Path, state_override: Path | None) -> dict:
    """Run one test file with pytest; parse the summary honestly."""
    env = dict(os.environ)
    if state_override is not None:
        env["LEXMACHINA_STATE_OVERRIDE"] = str(state_override)
    else:
        env.pop("LEXMACHINA_STATE_OVERRIDE", None)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q", "--tb=line", "-p", "no:cacheprovider"],
        cwd=str(REPO), capture_output=True, text=True, timeout=900, env=env)
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    def grab(pat: str) -> int:
        m = re.search(pat, out)
        return int(m.group(1)) if m else 0
    failed = grab(r"(\d+) failed")
    passed = grab(r"(\d+) passed")
    skipped = grab(r"(\d+) skipped")
    failed_tests = re.findall(r"^FAILED (.+?) - (.+)$", out, flags=re.M)
    return {
        "test_file": str(test_file.relative_to(REPO)),
        "test_file_sha256": sha256_file(test_file),
        "returncode": proc.returncode,
        "n_failed": failed,
        "n_passed": passed,
        "n_skipped": skipped,
        "failed_tests": [{"test": t, "error": e[:200]} for t, e in failed_tests],
        "state_override": str(state_override) if state_override else None,
        "stdout_tail": out[-1200:],
    }


def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_state(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


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
            f"{RUN_ID}.json gate G5_sibling_falsification_suites_green)"
        ),
        "repair_of_record": (
            f"run {RUN_ID}: block restored with re-derived pins only; no test, "
            "frozen file, rubric, bar or threshold edited"
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
        "schema": "lex-evaluation-state-minimal-ca-provenance-repair/1",
        "run_id": RUN_ID,
        "lane": "evaluation",
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "pytest_available": True,
        "network_calls": [],
    }

    # ---- freeze-first guard -------------------------------------------------
    # hyp_sha: this cycle's NEW hypothesis (pinned by the freeze record).
    # frozen_hyp_sha: the ACCEPTED minimal-CA hypothesis whose digest the
    # dedicated suite pins into state (PIN_FROZEN_HYP); re-hashed, never copied.
    hyp_sha = sha256_file(HYPOTHESIS)
    frozen_hyp_sha = sha256_file(FROZEN_HYP)
    freeze_sha = sha256_file(FREEZE_RECORD)
    instr_sha = sha256_file(INSTRUMENT)
    fr = json.loads(FREEZE_RECORD.read_text(encoding="utf-8"))
    freeze_ok = (
        hyp_sha == fr.get("hypothesis_sha256")
        and instr_sha == fr.get("instrument_sha256")
        and fr.get("frozen_before_execution") is True
        and frozen_hyp_sha == PIN_FROZEN_HYP
    )
    gates.append({
        "name": "G0_freeze_first_pins_hold",
        "pass": freeze_ok,
        "details": {
            "cycle_hypothesis_sha256": hyp_sha,
            "frozen_minimal_ca_hypothesis_sha256": frozen_hyp_sha,
            "frozen_minimal_ca_hypothesis_expected": PIN_FROZEN_HYP,
            "freeze_record_sha256": freeze_sha,
            "instrument_sha256": instr_sha,
        },
    })
    if not freeze_ok:
        record["gates"] = gates
        record["verdict"] = "ENVIRONMENT_OR_VACUOUS"
        record["exit_code"] = 2
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"{RUN_ID}.json").write_text(json.dumps(record, indent=2) + "\n")
        return 2

    record["freeze_pins"] = {
        "cycle_hypothesis_sha256": hyp_sha,
        "frozen_minimal_ca_hypothesis_sha256": frozen_hyp_sha,
        "freeze_record_sha256": freeze_sha,
        "instrument_sha256": instr_sha,
    }

    # ---- pre-repair measurement (G1 + C1) -----------------------------------
    pre_state_bytes = STATE.read_bytes()
    pre_state_sha = hashlib.sha256(pre_state_bytes).hexdigest()
    pre_data = json.loads(pre_state_bytes.decode("utf-8"))
    block_absent_pre = "minimal_ca_benchmark" not in pre_data

    with tempfile.TemporaryDirectory(prefix="lex_state_repair_") as td:
        pre_copy = Path(td) / "state_pre_repair.json"
        pre_copy.write_bytes(pre_state_bytes)

        pre_run = run_pytest(DEDICATED_SUITE, pre_copy)
        pre_failed_names = {f["test"] for f in pre_run["failed_tests"]}
        g1 = (
            block_absent_pre
            and pre_run["n_failed"] == 3
            and pre_run["n_passed"] == 8
            and pre_failed_names == set(STATE_BLOCK_TESTS)
            and all("minimal_ca_benchmark" in f["error"] for f in pre_run["failed_tests"])
        )
        gates.append({
            "name": "G1_pre_repair_dedicated_suite_fails_exactly_3_state_block_tests",
            "pass": g1,
            "details": {
                "pre_state_sha256": pre_state_sha,
                "block_absent_pre": block_absent_pre,
                "measurement": pre_run,
            },
        })
        controls.append({
            "name": "C1_negative_control_pre_repair_state_still_fails_3",
            "holds": g1,
            "details": "same measurement as G1, run via LEXMACHINA_STATE_OVERRIDE on an "
                       "untouched copy of the committed pre-repair state",
        })

        # ---- apply the repair (surgical block restore, re-derived values) ----
        # NOTE: the restored block's hypothesis_sha256 is the digest of the FROZEN
        # minimal-CA hypothesis (what test_minimal_ca_benchmark.py pins), not this
        # cycle's hypothesis; both are re-hashed here, never copied blindly.
        frozen_hyp_sha = sha256_file(FROZEN_HYP)
        post_summary_placeholder = "PENDING_POST_MEASUREMENT"
        block = build_block(frozen_hyp_sha, post_summary_placeholder)
        data = load_state(STATE)
        new_data = {}
        inserted = False
        for key, value in data.items():
            if key == "new_benchmark_result" and not inserted:
                new_data["minimal_ca_benchmark"] = block
                inserted = True
            new_data[key] = value
        if not inserted:
            new_data["minimal_ca_benchmark"] = block
        dump_state(STATE, new_data)
        post_state_sha = sha256_file(STATE)

        # ---- post-repair dedicated suite (G3) --------------------------------
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

        # ---- finalize the claim text with the measured summary, re-verify ----
        data = load_state(STATE)
        data["minimal_ca_benchmark"] = build_block(frozen_hyp_sha, post_summary)
        dump_state(STATE, data)
        reverify = run_pytest(DEDICATED_SUITE, None)
        g2 = (
            data["minimal_ca_benchmark"]["hypothesis_sha256"] == frozen_hyp_sha == PIN_FROZEN_HYP
            and data["minimal_ca_benchmark"]["freeze_commit"] == PIN_FREEZE_COMMIT
            and "tests/evaluation/test_minimal_ca_benchmark.py" in data["minimal_ca_benchmark"]["pytest"]
            and "PRE-REPAIR CLAIM WAS FALSE" in data["minimal_ca_benchmark"]["pytest"]
            and reverify["n_failed"] == 0
            and reverify["n_passed"] + reverify["n_skipped"] == 11
        )
        # freeze-commit blob re-hash (R2 of the dedicated suite, re-derived here too)
        blob = git("show", f"{PIN_FREEZE_COMMIT}:evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json")
        blob_ok = blob is not None and hashlib.sha256(blob.encode("utf-8")).hexdigest() == PIN_FROZEN_HYP
        gates.append({
            "name": "G2_restored_block_values_rederived_and_reverified",
            "pass": g2 and blob_ok,
            "details": {
                "block": data["minimal_ca_benchmark"],
                "freeze_commit_blob_rehash_ok": blob_ok,
                "reverification": reverify,
            },
        })

        # ---- sibling falsification suites (G5) -------------------------------
        sibling_runs = [run_pytest(f, None) for f in SIBLING_SUITES]
        g5 = all(r["n_failed"] == 0 and r["returncode"] == 0 for r in sibling_runs)
        gates.append({
            "name": "G5_sibling_falsification_suites_green",
            "pass": g5,
            "details": {"measurements": sibling_runs},
        })

        # ---- planted-mutation controls (C2, C3) ------------------------------
        mutated = load_state(STATE)
        mutated["minimal_ca_benchmark"]["hypothesis_sha256"] = (
            "0" + PIN_FROZEN_HYP[1:] if PIN_FROZEN_HYP[0] != "0" else "1" + PIN_FROZEN_HYP[1:]
        )
        mut_path = Path(td) / "state_mutated_hyp.json"
        dump_state(mut_path, mutated)
        c2_run = run_pytest(DEDICATED_SUITE, mut_path)
        c2 = c2_run["n_failed"] >= 1 and any(
            t["test"] == "test_hypothesis_rehash_matches_state_pin" for t in c2_run["failed_tests"])
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
    }
    expected_pins = {
        "evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json": PIN_FROZEN_HYP,
        "evaluation/minimal_ca_benchmark.py": PIN_CA_INSTRUMENT,
        "evaluation/frozen_bars/RULES_LABEL.json": PIN_RULES_LABEL,
        "evaluation/frozen_bars/RULES_GEOMETRY.json": PIN_RULES_GEOMETRY,
        "evaluation/frozen_bars/VERDICT_CONTRACT.json": PIN_VERDICT_CONTRACT,
    }
    g4 = all(post_pins[k] == v for k, v in expected_pins.items())
    record["frozen_input_pins_after"] = post_pins
    gates.append({
        "name": "G4_frozen_inputs_unchanged_after_all_runs",
        "pass": g4,
        "details": {"rehashed": post_pins, "expected": expected_pins},
    })

    # ---- G6: stand-ready adjudication (re-pinned, not re-measured) -----------
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
        "edit_scope": "state/evaluation.json minimal_ca_benchmark block restoration only "
                      "(plus pre-existing per-cycle fields untouched by this instrument)",
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
    out_path = OUT_DIR / f"{RUN_ID}.json"
    out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    # report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    failed_gate_names = [g["name"] for g in gates if not g["pass"]]
    report = [
        f"# State minimal-CA provenance repair — run {RUN_ID}",
        "",
        f"- Verdict: **{verdict}** (exit {record['exit_code']})",
        f"- Direction: v{DIRECTION_VERSION}",
        f"- Hypothesis SHA256: `{hyp_sha}` (frozen, re-verified G0)",
        f"- Freeze record SHA256: `{freeze_sha}`",
        f"- Instrument SHA256: `{instr_sha}`",
        f"- Pre-repair state SHA256: `{pre_state_sha}` (block absent; dedicated suite "
        f"{pre_run['n_passed']} passed / {pre_run['n_failed']} failed — the 3 KeyError state-block tests)",
        f"- Post-repair dedicated suite: {post_summary}",
        f"- Sibling suites: " + "; ".join(
            f"{r['test_file'].split('/')[-1]} {r['n_passed']}/{r['n_failed']}/{r['n_skipped']}"
            for r in sibling_runs),
        f"- Frozen inputs re-hashed after all runs: {'unchanged' if g4 else 'DRIFT'} "
        f"(RULES_LABEL {PIN_RULES_LABEL[:12]}..., RULES_GEOMETRY {PIN_RULES_GEOMETRY[:12]}..., "
        f"VERDICT_CONTRACT {PIN_VERDICT_CONTRACT[:12]}...)",
        f"- Stand-ready: product head {head} (expected {PIN_PRODUCT_HEAD}); "
        "ordered items (1)(2)(5) NOT_TRIGGERED, (3)(4) STANDING_OK",
        f"- Failed gates: {failed_gate_names or 'none'}",
        "",
        "## Claim ceiling",
        record["claim_ceiling"],
        "",
        "## Provenance",
        f"- Machine record: `results/evaluation/state_minimal_ca_provenance_repair/{RUN_ID}.json`",
        "- Hypothesis: `evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_HYPOTHESIS_V1.json`",
        "- Freeze record: `evaluation/STATE_MINIMAL_CA_PROVENANCE_REPAIR_FREEZE_RECORD_V1.json`",
        "- No test file, frozen file, rubric, bar, threshold or benchmark record was edited.",
        "",
    ]
    (REPORT_DIR / f"STATE_MINIMAL_CA_PROVENANCE_REPAIR_{RUN_ID}.md").write_text(
        "\n".join(report), encoding="utf-8")

    print(json.dumps({"verdict": verdict, "exit_code": record["exit_code"],
                      "record": str(out_path)}))
    return record["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
