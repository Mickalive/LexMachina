#!/usr/bin/env python3
"""
Regression test for audit CYCLE_38051663272 repair round 1 (D-1 and D-2),
executed by operational resume 38053714213 (resume of run 38053276639).

D-1: evaluation/verify_frozen_baseline.py must import `os` so that the
     advertised hard-fail guard (LEX_ENFORCE_METADATA_PIN=1) exits cleanly with
     SystemExit(2) instead of raising NameError ("name 'os' is not defined").
     The D-1 change is behavior-neutral on the main path (JP=0.5925, 6/8 PASS).

D-2: results/evaluation/frozen_baseline_reproducibility/provenance.json must
     point pre_verification_latest_sha256 / pre_verification_pointer_metrics at
     the TRUE pre-repair pointer (PRE_verification_latest.json, sha256
     cff6b19e..., JP=0.659 / LD=0.425775), NOT at the post-run rerun
     (PRE_verification_latest_rerun.json, sha256 6514501d..., JP=0.5925).
     The post-run pointer must be recorded separately (rerun_*).
"""
import ast
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "evaluation/verify_frozen_baseline.py"
RUNNER = REPO / "evaluation/experiments/run_frozen_baseline_reproducibility.py"
OUT = REPO / "results/evaluation/frozen_baseline_reproducibility"
PROV = OUT / "provenance.json"
PRE = OUT / "PRE_verification_latest.json"
RERUN = OUT / "PRE_verification_latest_rerun.json"
RESULT = OUT / "FROZEN_cycle_38048232833_RESULT.json"
METADATA = Path("/tmp/lex_accepted/legal-distance/evaluation/data/174k/metadata_174k.json")

TRUE_PRE_SHA = "cff6b19e722b28810e52989faaec0821dc88c644c8b2986cf75c088069ae7ade"
RERUN_SHA = "6514501d9a8398257ffed4b8d66e91b48d26cf5f0f719ef38371c9ef3e43a828"
TRUE_PRE_JP = 0.659
TRUE_PRE_LD = 0.425775
REPRODUCIBLE_JP = 0.5925
REPRODUCIBLE_LD = 0.348125
TOL = 1e-9

WRONG_PIN = "f0e4d2c8b9a15f6e7d3c1a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test():
    errors = []

    # ---- D-1: import os present and hard-fail guard works ----
    src = HARNESS.read_text()
    tree = ast.parse(src)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imports |= {a.name for a in node.names}
    if "os" not in imports:
        errors.append("D-1: harness does not import os")
    if "os.environ" not in src:
        errors.append("D-1: harness no longer uses the LEX_ENFORCE_METADATA_PIN guard")

    if METADATA.exists():
        # Functional hard-fail path check: a metadata pin mismatch with
        # LEX_ENFORCE_METADATA_PIN=1 must exit cleanly with code 2 (SystemExit(2)),
        # and must NOT raise NameError.
        with tempfile.TemporaryDirectory() as td:
            tmp_harness = Path(td) / "verify_frozen_baseline_wrongpin.py"
            patched = re.sub(
                r'PINNED_METADATA_SHA256 = "[0-9a-f]{64}"',
                f'PINNED_METADATA_SHA256 = "{WRONG_PIN}"',
                src,
            )
            tmp_harness.write_text(patched)
            env = dict(__import__("os").environ)
            env["LEX_ENFORCE_METADATA_PIN"] = "1"
            proc = subprocess.run(
                [sys.executable, str(tmp_harness)],
                capture_output=True, text=True, env=env, timeout=300,
            )
            if proc.returncode != 2:
                errors.append(
                    f"D-1: hard-fail path exit={proc.returncode} (want 2); stderr tail: "
                    f"{proc.stderr[-500:]}"
                )
            if "NameError" in proc.stderr + proc.stdout:
                errors.append("D-1: hard-fail path still raises NameError")
    else:
        errors.append("D-1 functional check skipped: accepted metadata mount absent")

    # ---- D-2: provenance pre_* points at the true pre-repair pointer ----
    prov = json.loads(PROV.read_text())
    pre_sha = prov.get("pre_verification_latest_sha256")
    if pre_sha != TRUE_PRE_SHA:
        errors.append(f"D-2: pre_verification_latest_sha256={pre_sha} != {TRUE_PRE_SHA}")
    pre_m = prov.get("pre_verification_pointer_metrics", {})
    if abs(pre_m.get("jurist_preference_rate", -1) - TRUE_PRE_JP) > TOL:
        errors.append(
            f"D-2: pre pointer JP={pre_m.get('jurist_preference_rate')} != {TRUE_PRE_JP}"
        )
    if abs(pre_m.get("language_dominance_score", -1) - TRUE_PRE_LD) > TOL:
        errors.append(
            f"D-2: pre pointer LD={pre_m.get('language_dominance_score')} != {TRUE_PRE_LD}"
        )
    if pre_m.get("source_file") != "PRE_verification_latest.json":
        errors.append("D-2: pre pointer source_file not documented")

    # Post-run pointer recorded separately and preserved
    rerun_sha = prov.get("rerun_verification_latest_sha256")
    if rerun_sha != RERUN_SHA:
        errors.append(f"D-2: rerun_verification_latest_sha256={rerun_sha} != {RERUN_SHA}")
    rerun_m = prov.get("rerun_verification_pointer_metrics", {})
    if abs(rerun_m.get("jurist_preference_rate", -1) - REPRODUCIBLE_JP) > TOL:
        errors.append("D-2: rerun pointer JP mismatch")

    # Artifacts on disk must agree with the provenance record
    if PRE.exists():
        if sha256_bytes(PRE.read_bytes()) != TRUE_PRE_SHA:
            errors.append("D-2: PRE_verification_latest.json hash != cff6b19e...")
        pre_verif = json.loads(PRE.read_text())
        row = pre_verif["cited_decisions_tfidf_outcome_hybrid_0.5"]
        if abs(row["jurist_preference_rate"] - TRUE_PRE_JP) > TOL:
            errors.append("D-2: PRE file JP != 0.659")
    else:
        errors.append("D-2: PRE_verification_latest.json missing")
    if not RERUN.exists():
        errors.append("D-2: PRE_verification_latest_rerun.json missing")

    # Harness hash in provenance matches the shipped file
    if sha256_bytes(HARNESS.read_bytes()) != prov.get("harness_sha256"):
        errors.append("D-2: provenance harness_sha256 does not match shipped harness")

    # D-2 root-cause hardening: the runner must preserve pre_* on re-runs
    runner_src = RUNNER.read_text()
    if "existing_pre_sha" not in runner_src or 'prov_path.exists()' not in runner_src:
        errors.append("D-2: runner is not hardened against pre_* clobbering")
    if '"rerun_verification_latest_sha256"' not in runner_src:
        errors.append("D-2: runner does not record rerun_* pointers")

    # ---- Frozen experiment result still NOT_REPRODUCED with 0.5925 ----
    if RESULT.exists():
        res = json.loads(RESULT.read_text())
        if res.get("verdict") != "NOT_REPRODUCED":
            errors.append("frozen result verdict != NOT_REPRODUCED")
        jps = {res.get("run1", {}).get("jurist_preference_rate"),
               res.get("run2", {}).get("jurist_preference_rate")}
        if jps != {REPRODUCIBLE_JP}:
            errors.append(f"frozen result JP values {jps} != {REPRODUCIBLE_JP}")
        if res.get("success_rule_evaluation", {}).get("same_between_runs") is not True:
            errors.append("frozen result run1 != run2")
    else:
        errors.append("frozen result artifact missing")

    if errors:
        print("FAILED:")
        for e in errors:
            print("  -", e)
        return False
    print("PASSED: D-1 (import os hard-fail) and D-2 (provenance pre_* repoint) verified.")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if test() else 1)