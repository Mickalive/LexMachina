#!/usr/bin/env python3
"""Executable verifier for REPAIR ROUND 1 of rejected evaluation cycle 39402114706.

WHAT IT IS FOR
--------------
Independent audit ``CYCLE_39402114706`` returned gate=REVISE with three required
fixes, all of them metadata defects in ``state/evaluation.json``:

  R1  ``minimal_ca_benchmark.hypothesis_sha256`` must be
      f0c7711c71e94d7b7303f5fa3a61b444d67bee6d3bbd7f0708ed13ff6ffc8072
  R2  ``minimal_ca_benchmark.freeze_commit`` must be 6892f9f0
  R3  the ``pytest`` claim must reflect actual test status (no dedicated test for
      ``minimal_ca_benchmark`` existed when the claim was written)

Rather than asserting in prose that the three fixes landed, this module RE-MEASURES
every repaired pin plus the surrounding evidence chain and writes a machine record.
The pytest claim is verified by running the dedicated test file and comparing the
measured counts with the counts published in the state file, so a stale or invented
number fails the verifier.

NON-WEAKENING CONTRACT
----------------------
* Frozen inputs are only RE-HASHED: RULES_LABEL.json, RULES_GEOMETRY.json,
  VERDICT_CONTRACT.json, the frozen hypothesis, the freeze record and the three V3
  packet bundles. No rubric, threshold, incumbent, predicate or success rule is
  regenerated, re-tuned or edited here.
* Every expectation compared against is the frozen hypothesis' own
  ``expected_leg_outcomes`` / ``combined_verdict`` rule (committed at 6892f9f0,
  before the claim-bearing run).
* The end-to-end reproduction writes into a temporary directory only; no committed
  claim-bearing artifact is rewritten by this module.
* No universal-174k benchmark is executed.

SCRATCH-RUN OBLIGATION: the DEFAULT output path is a NEW run-scoped filename under
results/evaluation/repair_39402114706/ so an ad-hoc invocation can never rewrite the
committed record of run 39406033825 (F-3B binding convention; F1 of audit
CYCLE_39413028463).  If you need a different path, still pass ``--out`` explicitly.

F3 HARDENING (audit CYCLE_39413028463): mount-absent and caller-skipped observations
are recorded with status="skipped" and NEVER count as a pass of overall_pass.
overall_pass requires n_failed==0 AND n_skipped==0.  The claim_ceiling is derived
from the checks that actually executed and names the skip count.

Exit codes: 0 = every check passed, 1 = at least one check failed, 2 = environment
error (never a pass).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA = "lex-evaluation-repair-verification/2"
CYCLE_ID = "39402114706"
#: Default output is ALWAYS a NEW run-scoped file so an ad-hoc invocation can never
#: rewrite the committed record of run 39406033825 (F-3B binding convention).
DEFAULT_RUN_ID = "39422312905"
DEFAULT_OUT = (_REPO_ROOT / "results/evaluation/repair_39402114706"
               / f"{DEFAULT_RUN_ID}_disposition_verification.json")

FROZEN_HYPOTHESIS_SHA256 = (
    "f0c7711c71e94d7b7303f5fa3a61b444d67bee6d3bbd7f0708ed13ff6ffc8072")
FREEZE_COMMIT = "6892f9f0"
CLAIM_BEARING_COMMIT = "d4c88b3a"
PRE_FIX_INSTRUMENT_SHA256 = (
    "2d40d2e795d9396542bbbc7a811e6cf26da91f3b19220e70199aad8f5f02c84c")
EXECUTED_INSTRUMENT_SHA256 = (
    "567a9d2b231c5404b7324db2c30249e0961dbc90c698501d0ba5576c7297554b")

STATE_PATH = _REPO_ROOT / "state/evaluation.json"
HYPOTHESIS_PATH = _REPO_ROOT / "evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json"
FREEZE_RECORD_PATH = _REPO_ROOT / "evaluation/MINIMAL_CA_BENCHMARK_FREEZE_RECORD_V1.json"
INSTRUMENT_PATH = _REPO_ROOT / "evaluation/minimal_ca_benchmark.py"
DEDICATED_TEST = "tests/evaluation/test_minimal_ca_benchmark.py"
COMBINED_RECORD = (
    _REPO_ROOT / "results/evaluation/retrieval_counter_authority_benchmark/39396488491.json")

#: The accepted instrument tests named by state minimal_ca_benchmark.regression.
REGRESSION_TESTS = [
    "tests/evaluation/test_frozen_bar_gates.py",
    "tests/evaluation/test_bar_gate_verdict_contract.py",
    "tests/evaluation/test_mapping_free_recall_falsifier.py",
    "tests/evaluation/test_benchmark_retrieval_counter_authority.py",
    "tests/evaluation/test_benchmark_v3_packet_of_record.py",
]

#: Paths this lane may write (write-scope check; .github/** is control-plane scope).
IN_SCOPE_PREFIXES = (
    "evaluation/", "tests/evaluation/", "results/evaluation/",
    "reports/evaluation/", "state/evaluation.json",
)

V3_PACKET_DIR = Path(
    "/tmp/lex_accepted/product/results/product/gate_packet/39319405429/questions")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git(*args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(_REPO_ROOT), *args],
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _check(results: list, check_id: str, ok: bool, expected, observed,
           evidence: str = "", status: str | None = None) -> bool:
    """Record one check. ``status`` may be ``pass``/``fail``/``skipped``.

    F3 HARDENING (audit CYCLE_39413028463): a mount-absent / explicitly-skipped
    observation MUST carry ``status="skipped"`` and MUST NOT count as a pass of
    ``overall_pass``.  ``status=None`` derives pass/fail from ``ok`` as before.
    """
    if status is None:
        status = "pass" if ok else "fail"
    if status == "skipped":
        # a skip is never a pass, whatever ``ok`` says
        passed = False
        skipped = True
    else:
        passed = bool(ok) and status == "pass"
        skipped = False
    results.append({
        "check": check_id,
        "status": status,
        "pass": passed,
        "skipped": skipped,
        "expected": expected,
        "observed": observed,
        "evidence": evidence,
    })
    return passed


def _run_pytest(targets: list[str], timeout: int = 1800) -> dict:
    """Run pytest on the given targets and parse the summary counts."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *targets, "-p", "no:cacheprovider"],
        cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=timeout)
    tail = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip().splitlines()[-1:]
    tail = tail[0] if tail else ""
    counts = {}
    for word in ("passed", "failed", "skipped", "error", "errors"):
        m = re.search(rf"(\d+) {word}", tail)
        if m:
            counts[word] = int(m.group(1))
    return {
        "targets": targets,
        "returncode": proc.returncode,
        "counts": counts,
        "summary_line": tail,
        "passed": counts.get("passed", 0),
        "failed": counts.get("failed", 0),
        "skipped": counts.get("skipped", 0),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="machine record path (default: a NEW run-scoped disposition "
                         "file; the committed record of run 39406033825 is never the "
                         "default target)")
    ap.add_argument("--run-id", default=DEFAULT_RUN_ID)
    ap.add_argument("--skip-regression", action="store_true",
                    help="skip the 5-file accepted-instrument regression suite "
                         "(records skipped=true, never a pass)")
    args = ap.parse_args(argv)
    t0 = time.time()
    out_path = Path(args.out)
    checks: list[dict] = []

    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    hyp = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    fr = json.loads(FREEZE_RECORD_PATH.read_text(encoding="utf-8"))
    mcb = state.get("minimal_ca_benchmark", {})

    # ------------------------------------------------------------------ R1
    hyp_sha = _sha256(HYPOTHESIS_PATH)
    _check(checks, "R1 hypothesis file re-hashes to the required value",
           hyp_sha == FROZEN_HYPOTHESIS_SHA256, FROZEN_HYPOTHESIS_SHA256, hyp_sha,
           "sha256 evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json")
    _check(checks, "R1 state hypothesis_sha256 matches the file bytes",
           mcb.get("hypothesis_sha256") == hyp_sha, hyp_sha,
           mcb.get("hypothesis_sha256"),
           "state/evaluation.json minimal_ca_benchmark.hypothesis_sha256")
    _check(checks, "R1 rejected (wrong) digest is gone from the minimal_ca block",
           mcb.get("hypothesis_sha256") != "1f7cdb05969ebc365934b3a7612d5b6abf1115f5f0b57d3138a732560fd982a6",
           "not the V3-recall-benchmark digest", mcb.get("hypothesis_sha256"),
           "1f7cdb05... belongs to V3_PACKET_OF_RECORD_RECALL_BENCHMARK_HYPOTHESIS_V1.json "
           "and is still correctly recorded in state v3_packet_of_record_recall_benchmark")

    # ------------------------------------------------------------------ R2
    _check(checks, "R2 state freeze_commit == 6892f9f0",
           mcb.get("freeze_commit") == FREEZE_COMMIT, FREEZE_COMMIT,
           mcb.get("freeze_commit"), "state/evaluation.json minimal_ca_benchmark.freeze_commit")
    added = _git("log", "--diff-filter=A", "--format=%h", "--",
                 "evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json")
    first_added = (added or "").split()
    _check(checks, "R2 the hypothesis was first committed at 6892f9f0",
           FREEZE_COMMIT in first_added, [FREEZE_COMMIT], first_added or None,
           "git log --diff-filter=A on the hypothesis file")
    blob = _git("show", f"{FREEZE_COMMIT}:evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json")
    _check(checks, "R2 hypothesis bytes at the freeze commit re-hash to the frozen digest",
           blob is not None and _sha256_text(blob) == FROZEN_HYPOTHESIS_SHA256,
           FROZEN_HYPOTHESIS_SHA256,
           _sha256_text(blob) if blob else None,
           "git show 6892f9f0:evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json")
    added_result = _git("log", "--diff-filter=A", "--format=%h %ct", "--",
                        "results/evaluation/retrieval_counter_authority_benchmark/"
                        "39396488491.json")
    freeze_ct = _git("log", "-1", "--format=%ct", FREEZE_COMMIT)
    ok_order, observed_order = False, added_result
    if added_result and freeze_ct:
        res_commit, res_ct = added_result.split()[0], int(added_result.split()[1])
        ok_order = (res_commit == CLAIM_BEARING_COMMIT and int(freeze_ct) < res_ct)
        observed_order = {"freeze_commit": FREEZE_COMMIT, "freeze_epoch": int(freeze_ct),
                          "claim_bearing_commit": res_commit,
                          "claim_bearing_epoch": res_ct}
    _check(checks, "R2 freeze-first ordering: freeze commit predates the claim-bearing record",
           ok_order, f"{FREEZE_COMMIT} epoch < {CLAIM_BEARING_COMMIT} epoch", observed_order,
           "git log --diff-filter=A on the committed benchmark record")

    # ------------------------------------------------------------------ R3
    claim = mcb.get("pytest", "")
    dedicated_exists = (_REPO_ROOT / DEDICATED_TEST).is_file()
    _check(checks, "R3 state pytest claim cites the dedicated test file",
           dedicated_exists and DEDICATED_TEST in claim, DEDICATED_TEST,
           claim[:300], "state/evaluation.json minimal_ca_benchmark.pytest")
    _check(checks, "R3 state pytest claim discloses the false pre-repair claim",
           "PRE-REPAIR CLAIM WAS FALSE" in claim and "DIFFERENT instrument" in claim,
           "PRE-REPAIR CLAIM WAS FALSE + DIFFERENT instrument",
           "present" if "PRE-REPAIR CLAIM WAS FALSE" in claim else "absent",
           "the rejected claim is corrected beside its replacement, never deleted")
    _check(checks, "R3 no MEASURE_COUNTS_PENDING placeholder left in the claim",
           "MEASURE_COUNTS_PENDING" not in claim, "counts published", claim[:120],
           "counts must be measured before they are published")
    dedicated_run = _run_pytest([DEDICATED_TEST])
    measured = (f"{dedicated_run['passed']} passed / {dedicated_run['failed']} failed / "
                f"{dedicated_run['skipped']} skipped")
    m = re.match(r"(\d+) passed / (\d+) failed / (\d+) skipped", claim)
    published = (f"{m.group(1)} passed / {m.group(2)} failed / {m.group(3)} skipped"
                 if m else None)
    _check(checks, "R3 published pytest counts equal the fresh measurement",
           published == measured and dedicated_run["failed"] == 0,
           measured, published,
           f"pytest {DEDICATED_TEST} -> {dedicated_run['summary_line']}")

    # ------------------------------------- R3 negative control (guards must bite)
    # Re-inject the exact pre-repair state values and prove the dedicated test
    # FAILS on them, so the new guards are shown non-vacuous rather than decorative.
    injected_state = json.loads(json.dumps(state))
    injected_mcb = injected_state["minimal_ca_benchmark"]
    injected_mcb["hypothesis_sha256"] = (
        "1f7cdb05969ebc365934b3a7612d5b6abf1115f5f0b57d3138a732560fd982a6")
    injected_mcb["freeze_commit"] = "a6943ef7"
    injected_mcb["pytest"] = (
        "6 passed / 0 failed / 0 skipped "
        "(tests/evaluation/test_benchmark_retrieval_counter_authority.py, pytest 9.1.1)")
    injected_state["evidence_refs_n"] = 999
    negctl: dict
    with tempfile.TemporaryDirectory(prefix="repair3940_negctl_") as td:
        injected_path = Path(td) / "state_evaluation_pre_repair.json"
        injected_path.write_text(json.dumps(injected_state, indent=1), encoding="utf-8")
        env = dict(**{k: v for k, v in __import__("os").environ.items()})
        env["LEXMACHINA_STATE_OVERRIDE"] = str(injected_path)
        proc_neg = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", DEDICATED_TEST,
             "-p", "no:cacheprovider", "--tb=no"],
            cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=900, env=env)
    failed_tests = sorted({
        line.split("::")[-1].split(" ")[0]
        for line in (proc_neg.stdout or "").splitlines()
        if line.startswith("FAILED ")})
    expected_biting = {
        "test_hypothesis_rehash_matches_state_pin",
        "test_state_freeze_commit_is_where_the_hypothesis_landed",
        "test_state_pytest_claim_names_this_dedicated_test",
        "test_state_evidence_refs_resolve_and_count_matches",
    }
    negctl = {"failed_tests": failed_tests,
              "returncode": proc_neg.returncode,
              "summary_line": (proc_neg.stdout or "").strip().splitlines()[-1]
              if (proc_neg.stdout or "").strip() else ""}
    _check(checks, "negative control: re-injected pre-repair state fails the dedicated test",
           expected_biting <= set(failed_tests),
           sorted(expected_biting), failed_tests,
           "the three required-fix guards plus the evidence_refs_n guard must bite on "
           "the exact defective values recorded by audit CYCLE_39402114706")

    # ------------------------------------------------------- state/ref hygiene
    refs = state.get("evidence_refs", [])
    unresolved = []
    for r in refs:
        rel = r.split(" ")[0].rstrip(",")
        path = _REPO_ROOT / rel
        # the record this very run is writing is allowed to be "about to exist"
        if path.exists() or path.resolve() == out_path.resolve():
            continue
        unresolved.append(rel)
    _check(checks, "state evidence_refs all resolve on disk",
           not unresolved, [], unresolved,
           "filesystem existence check; the output record of this run counts as "
           "existing because this module writes it before returning")
    _check(checks, "state evidence_refs_n equals len(evidence_refs)",
           state.get("evidence_refs_n") == len(refs), len(refs),
           state.get("evidence_refs_n"),
           "repair round 0 set n=52 while len=48; n is now recomputed after this "
           "cycle appended 4 refs (52 after append — the numeric coincidence with the "
           "old wrong 52 is disclosed, not hidden)")

    # ------------------------------------------------------------ frozen inputs
    for name, pinned in hyp["frozen_bars_shas"].items():
        actual = _sha256(_REPO_ROOT / "evaluation/frozen_bars" / name)
        _check(checks, f"frozen pin re-hash unchanged: {name}",
               actual == pinned, pinned, actual, "re-hash only; never re-derived")
    _check(checks, "freeze record frozen_bars_shas identical to the hypothesis",
           fr.get("frozen_bars_shas") == hyp["frozen_bars_shas"],
           hyp["frozen_bars_shas"], fr.get("frozen_bars_shas"),
           "both files re-hashed, neither edited")

    # ------------------------------------------------------------ V3 packet bytes
    v3_ok, v3_observed = True, {}
    if V3_PACKET_DIR.exists():
        for fname, pinned in hyp["v3_packet_shas"].items():
            actual = _sha256(V3_PACKET_DIR / fname)
            v3_observed[fname] = actual
            v3_ok = v3_ok and actual == pinned
        _check(checks, "V3 packet bundles re-hash to the frozen hypothesis pins",
               v3_ok, hyp["v3_packet_shas"], v3_observed, str(V3_PACKET_DIR))
    else:
        _check(checks, "V3 packet bundles re-hash to the frozen hypothesis pins",
               False, hyp["v3_packet_shas"], f"SKIPPED: mount absent ({V3_PACKET_DIR})",
               "skipped with reason is recorded, NEVER counted as a pass of the pins "
               "(F3 hardening of audit CYCLE_39413028463)",
               status="skipped")

    # --------------------------------------------------- committed record of record
    rec = json.loads(COMBINED_RECORD.read_text(encoding="utf-8"))
    legs = {lg["leg"]: lg for lg in rec.get("legs", [])}
    _check(checks, "committed record verdict/exit/falsification_proven",
           rec.get("verdict") == "BENCHMARK_VALID_NO_FALSIFICATION"
           and rec.get("exit_code") == 0 and rec.get("falsification_proven") is True,
           {"verdict": "BENCHMARK_VALID_NO_FALSIFICATION", "exit_code": 0,
            "falsification_proven": True},
           {"verdict": rec.get("verdict"), "exit_code": rec.get("exit_code"),
            "falsification_proven": rec.get("falsification_proven")},
           str(COMBINED_RECORD.relative_to(_REPO_ROOT)))
    leg_observed = {}
    leg_ok = True
    for leg_id, exp in hyp["expected_leg_outcomes"].items():
        got = legs.get(leg_id, {})
        leg_observed[leg_id] = {"exit_code": got.get("exit_code"),
                                "verdict": got.get("verdict")}
        leg_ok = leg_ok and got.get("exit_code") == exp["expected_exit_code"] \
            and got.get("verdict") == exp["expected_verdict"]
    _check(checks, "committed legs match the frozen expected_leg_outcomes", leg_ok,
           {k: {"exit_code": v["expected_exit_code"], "verdict": v["expected_verdict"]}
            for k, v in hyp["expected_leg_outcomes"].items()},
           leg_observed, "expectations are the hypothesis' own, frozen before execution")
    expected_bundles = {qid: hyp["v3_packet_shas"][f"{qid}.bundle.json"]
                        for qid in ("de-kapitalverletzung", "fr-bail-entretien",
                                    "it-responsabilita-medica")}
    _check(checks, "committed record scored the frozen V3 bundles",
           rec.get("v3_bundle_sha256") == expected_bundles, expected_bundles,
           rec.get("v3_bundle_sha256"), "record.v3_bundle_sha256 vs hypothesis pins")

    # -------------------------------------------------- instrument provenance pins
    _check(checks, "freeze record still discloses the PRE-FIX instrument digest",
           fr.get("instrument_sha256") == PRE_FIX_INSTRUMENT_SHA256
           and "pre-fix" in fr.get("frozen_at_commit", ""),
           {"instrument_sha256": PRE_FIX_INSTRUMENT_SHA256, "frozen_at_commit": "7efbd60e (pre-fix...)"},
           {"instrument_sha256": fr.get("instrument_sha256"),
            "frozen_at_commit": fr.get("frozen_at_commit")},
           "the freeze record's own pre-fix disclosure is preserved verbatim, not corrected away")
    _check(checks, "executed instrument bytes unchanged since freeze commit",
           _sha256(INSTRUMENT_PATH) == EXECUTED_INSTRUMENT_SHA256,
           EXECUTED_INSTRUMENT_SHA256, _sha256(INSTRUMENT_PATH),
           "git HEAD == 6892f9f0 for evaluation/minimal_ca_benchmark.py")
    at_freeze = _git("show", f"{FREEZE_COMMIT}:evaluation/minimal_ca_benchmark.py")
    _check(checks, "instrument bytes at the freeze commit are the executed bytes",
           at_freeze is not None and _sha256_text(at_freeze) == EXECUTED_INSTRUMENT_SHA256,
           EXECUTED_INSTRUMENT_SHA256,
           _sha256_text(at_freeze) if at_freeze else None, "git show")
    pre_fix = _git("show", "7efbd60e:evaluation/minimal_ca_benchmark.py")
    _check(checks, "pre-fix instrument bytes re-hash to the frozen hypothesis pin",
           pre_fix is not None and _sha256_text(pre_fix) == PRE_FIX_INSTRUMENT_SHA256,
           PRE_FIX_INSTRUMENT_SHA256,
           _sha256_text(pre_fix) if pre_fix else None, "git show")

    # ------------------------------------------------------ live reproduction (mount)
    e2e: dict
    if V3_PACKET_DIR.exists():
        with tempfile.TemporaryDirectory(prefix="repair3940_e2e_") as td:
            td_path = Path(td)
            proc = subprocess.run(
                [sys.executable, "-m", "evaluation.minimal_ca_benchmark",
                 "--run-id", f"repair3940_{args.run_id}",
                 "--out-dir", str(td_path / "results"),
                 "--report-dir", str(td_path / "reports")],
                cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=900)
            try:
                parsed = json.loads(proc.stdout)
            except json.JSONDecodeError:
                parsed = {}
            e2e = {"returncode": proc.returncode,
                   "verdict": parsed.get("verdict"),
                   "falsification_proven": parsed.get("falsification_proven"),
                   "legs": [{"leg": lg.get("leg"), "exit_code": lg.get("exit_code"),
                             "verdict": lg.get("verdict")}
                            for lg in parsed.get("legs", [])],
                   "elapsed_s": parsed.get("elapsed_s"),
                   "stderr_tail": (proc.stderr or "")[-300:]}
        e2e_ok = (proc.returncode == 0
                  and e2e["verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
                  and e2e["falsification_proven"] is True)
        for leg in e2e["legs"]:
            exp = hyp["expected_leg_outcomes"].get(leg["leg"], {})
            e2e_ok = e2e_ok and leg["exit_code"] == exp.get("expected_exit_code") \
                and leg["verdict"] == exp.get("expected_verdict")
        _check(checks, "live re-execution reproduces the frozen verdict on run " + args.run_id,
               e2e_ok, {"verdict": "BENCHMARK_VALID_NO_FALSIFICATION",
                        "legs": "frozen expected_leg_outcomes"}, e2e,
               "outputs redirected to a temp dir; no committed artifact rewritten")
    else:
        e2e = {"skipped": f"V3 packet mount absent ({V3_PACKET_DIR})"}
        _check(checks, "live re-execution reproduces the frozen verdict on run " + args.run_id,
               False, {"verdict": "BENCHMARK_VALID_NO_FALSIFICATION"},
               {"skipped": f"V3 packet mount absent ({V3_PACKET_DIR})"},
               "SKIP recorded with reason; NEVER a pass of the frozen verdict "
               "(F3 hardening of audit CYCLE_39413028463). The offline record checks "
               "still apply and still count toward overall_pass.",
               status="skipped")

    # -------------------------------------------------- accepted regression suite
    if args.skip_regression:
        regression = {"skipped": "--skip-regression"}
        reg_ok, reg_note = True, "explicitly skipped by the caller (recorded, not a pass)"
        _check(checks, "accepted 5-file regression suite still matches the state claim",
               True, "state minimal_ca_benchmark.regression counts", reg_note,
               "pytest " + " ".join(REGRESSION_TESTS) + " — SKIPPED by caller; never a pass",
               status="skipped")
    else:
        regression = _run_pytest(REGRESSION_TESTS)
        reg_claim = mcb.get("regression", "")
        # Dual-attribution format (F2): the claim carries BOTH environment-qualified
        # measurements.  The FRESH measurement on THIS host must match the branch
        # whose environment matches the V3 mount presence on this host.
        m_reg = re.search(
            r"with-mount\s+(\d+) passed / (\d+) failed.*?"
            r"mountless\s+(\d+) passed / (\d+) failed / (\d+) skipped",
            reg_claim, re.S)
        if m_reg is None:
            # single-claim fallback (pre-F2 format)
            m_reg_single = re.match(r"(\d+) passed / (\d+) failed", reg_claim)
            reg_published = (f"{regression['passed']} passed / {regression['failed']} failed")
            reg_ok = (regression["failed"] == 0
                      and m_reg_single is not None
                      and f"{m_reg_single.group(1)} passed / {m_reg_single.group(2)} failed"
                          == reg_published)
            reg_note = {"published": reg_claim[:200], "measured": reg_published,
                        "summary_line": regression["summary_line"],
                        "format": "single-claim (pre-F2)"}
        else:
            wm_p, wm_f = int(m_reg.group(1)), int(m_reg.group(2))
            ml_p, ml_f, ml_s = (int(m_reg.group(3)), int(m_reg.group(4)),
                                int(m_reg.group(5)))
            if V3_PACKET_DIR.exists():
                expected_p, expected_f = wm_p, wm_f
                env = "with-mount (run 39406033825 measurement)"
            else:
                expected_p, expected_f = ml_p, ml_f
                env = "mountless (run 39413028463 measurement)"
            reg_ok = (regression["failed"] == expected_f
                      and regression["passed"] == expected_p)
            reg_note = {"published_dual": {"with-mount_39406033825": f"{wm_p} passed / {wm_f} failed",
                                           "mountless_39413028463": f"{ml_p} passed / {ml_f} failed / {ml_s} skipped"},
                        "measured": f"{regression['passed']} passed / {regression['failed']} failed / {regression['skipped']} skipped",
                        "environment_matched": env,
                        "summary_line": regression["summary_line"],
                        "format": "dual-attribution (F2)"}
        _check(checks, "accepted 5-file regression suite still matches the state claim",
               reg_ok, "state minimal_ca_benchmark.regression counts (environment-qualified)",
               reg_note,
               "pytest " + " ".join(REGRESSION_TESTS)
               + ("; dual claim matched against the environment-branch that describes THIS host"
                  if m_reg else ""))

    # -------------------------------------------------------------- write scope
    status = (_git("status", "--porcelain") or "").splitlines()
    out_of_scope = []
    for line in status:
        # porcelain line = XY<space>path; _git() strips the whole output, so the
        # leading space of an unstaged entry can be gone — parse on the first
        # whitespace run instead of a fixed offset (offset parsing once produced
        # 'tate/evaluation.json', a false out-of-scope hit recorded in run
        # 39406033825 pre-final and fixed in this same cycle).
        parts = line.strip().split(maxsplit=1)
        if len(parts) < 2:
            continue
        path = parts[1].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if not path.startswith(IN_SCOPE_PREFIXES):
            out_of_scope.append(path)
    _check(checks, "write scope: every modified/untracked path is evaluation-lane scope",
           not out_of_scope, [], out_of_scope,
           "allowed: evaluation/, tests/evaluation/, results/evaluation/, "
           "reports/evaluation/, state/evaluation.json (no .github/**, no product/)")

    # ----------------------------------------------------------- gate/ceiling flags
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required"):
        _check(checks, f"fail-closed flag unchanged: {flag}==false",
               state.get(flag) is False, False, state.get(flag),
               "repair touches metadata only; admission stays fail-closed")

    # ------------------------------------------------- F1 disposition self-checks
    # Restore proof: the restored 39406033825 artifact must re-hash to the original
    # pre-overwrite digest when present on disk.
    RESTORED_PATH = (_REPO_ROOT
                     / "results/evaluation/repair_39402114706"
                     / "39406033825_repair1_verification.json")
    REHOMED_PATH = (_REPO_ROOT
                    / "results/evaluation/repair_39402114706"
                    / "39413028463_repair2_verification.json")
    ORIGINAL_SHA = ("ddf7cbac7352a1fee57596f9bd0074d30ef8caeca236a7d255ef1e936c043a5f")
    if RESTORED_PATH.is_file():
        restored_sha = _sha256(RESTORED_PATH)
        _check(checks, "F1: 39406033825 artifact restored to pre-overwrite digest",
               restored_sha == ORIGINAL_SHA, ORIGINAL_SHA, restored_sha,
               "git show 21166ff8 re-hash; AGENTS.md item 6 / F-3B convention")
    else:
        _check(checks, "F1: 39406033825 artifact restored to pre-overwrite digest",
               False, ORIGINAL_SHA, "FILE ABSENT",
               "restore is part of the ordered F1 disposition; absence is a FAIL, "
               "never a skip-pass", status="fail")
    if REHOMED_PATH.is_file():
        try:
            rehomed = json.loads(REHOMED_PATH.read_text(encoding="utf-8"))
            rehome_ok = (rehomed.get("run_id") == "39413028463"
                         and rehomed.get("repair_round") == 2
                         and "rehome_provenance" in rehomed
                         and (rehomed.get("rehome_provenance", {}).get("overwriting_commit")
                              == "27c30acd"))
            _check(checks, "F1: mountless measurement re-homed under 39413028463 filename",
                   rehome_ok,
                   {"run_id": "39413028463", "repair_round": 2,
                    "overwriting_commit": "27c30acd"},
                   {"run_id": rehomed.get("run_id"),
                    "repair_round": rehomed.get("repair_round"),
                    "has_provenance": "rehome_provenance" in rehomed},
                   "a file named for run X holds run X's measurement")
        except json.JSONDecodeError as exc:
            _check(checks, "F1: mountless measurement re-homed under 39413028463 filename",
                   False, "valid JSON", f"JSONDecodeError: {exc}",
                   "re-homed artifact unreadable", status="fail")
    else:
        _check(checks, "F1: mountless measurement re-homed under 39413028463 filename",
               False, "re-homed file present", "FILE ABSENT",
               "re-home is part of the ordered F1 disposition; absence is a FAIL",
               status="fail")

    # -------------------------------------------------------------- overall_pass
    # F3 HARDENING: overall_pass is true only when EVERY non-skipped check passed.
    # Skipped checks are published with status="skipped" and NEVER contribute a pass.
    n_passed = sum(1 for c in checks if c.get("status") == "pass")
    n_failed = sum(1 for c in checks if c.get("status") == "fail")
    n_skipped = sum(1 for c in checks if c.get("status") == "skipped")
    overall_pass = (n_failed == 0 and n_skipped == 0 and n_passed == len(checks))
    executed = [c for c in checks if c.get("status") != "skipped"]
    executed_pass = all(c.get("status") == "pass" for c in executed)
    claim_ceiling = (
        "This artifact proves only that the required disposition fixes of audits "
        "CYCLE_39402114706 / CYCLE_39406033825 / CYCLE_39413028463 are present and "
        "re-measurable on the checks that actually executed"
        + (f" ({n_passed}/{len(executed)} executed checks passed, {n_skipped} skipped)"
           if n_skipped else f" ({n_passed}/{len(checks)} checks passed, 0 skipped)")
        + ", that the frozen pins re-hash unchanged, and (when the V3 packet mount "
        "is present) that the minimal_ca_benchmark still reproduces "
        "BENCHMARK_VALID_NO_FALSIFICATION on the packet-of-record V3 bytes. When the "
        "mount is absent the live-reproduction check is SKIPPED and is NOT a pass of "
        "the frozen verdict. It does NOT prove jurist usefulness, does NOT meet the "
        "absolute LABEL_SOUND / GEOMETRY_SOUND bars and does NOT unblock the human "
        "gate (standing accepted DO-NOT-SERVE orders). NOT_APPLICABLE is never a pass."
    )

    record = {
        "schema": SCHEMA,
        "run_id": args.run_id,
        "cycle_id": CYCLE_ID,
        "repair_round": 2,
        "disposition_of_blocked_gate": "CYCLE_39413028463",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction_version": state.get("direction_version"),
        "python": sys.version.split()[0],
        "pytest_installed": bool(shutil.which("pytest") or _pytest_version()),
        "pytest_version": _pytest_version(),
        "hypothesis_sha256": hyp_sha,
        "freeze_commit": FREEZE_COMMIT,
        "instrument_sha256_executed": _sha256(Path(__file__).resolve()),
        "instrument_sha256_pre_fix_pinned": PRE_FIX_INSTRUMENT_SHA256,
        "dedicated_test": DEDICATED_TEST,
        "dedicated_test_measurement": dedicated_run,
        "negative_control_measurement": negctl,
        "regression_measurement": regression,
        "live_reproduction": e2e,
        "n_checks": len(checks),
        "n_passed": n_passed,
        "n_failed": n_failed,
        "n_skipped": n_skipped,
        "executed_checks_pass": executed_pass,
        "checks": checks,
        "overall_pass": overall_pass,
        "claim_ceiling": claim_ceiling,
        "f3_hardening": {
            "rule": "mount-absent and caller-skipped checks carry status=skipped and "
                    "never contribute a pass to overall_pass",
            "overall_pass_requires": "n_failed==0 AND n_skipped==0 AND n_passed==n_checks",
            "auditor_finding_addressed": "CYCLE_39413028463 F3",
        },
        "elapsed_s": round(time.time() - t0, 3),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "overall_pass": overall_pass,
        "n_checks": record["n_checks"],
        "n_passed": n_passed,
        "n_failed": n_failed,
        "n_skipped": n_skipped,
        "failed_checks": [c["check"] for c in checks if c.get("status") == "fail"],
        "skipped_checks": [c["check"] for c in checks if c.get("status") == "skipped"],
        "dedicated_test": record["dedicated_test_measurement"]["summary_line"],
        "regression": (regression.get("summary_line")
                       if isinstance(regression, dict) else None),
        "out": str(out_path),
    }, indent=1))
    # Exit 2 only when the environment is broken AND nothing executed cleanly;
    # a disposition with fails exits 1; a clean disposition exits 0.
    if not V3_PACKET_DIR.exists() and n_failed > 0 and n_passed == 0:
        return 2
    return 0 if overall_pass else 1


def _pytest_version() -> str | None:
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "--version"],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    m = re.search(r"pytest\s+([\d.]+)", (proc.stdout or "") + (proc.stderr or ""))
    return m.group(1) if m else "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
