#!/usr/bin/env python3
"""
Regression test for the frozen-baseline reproducibility repair.

Operational resume 38051663272 (snapshot of 38048817288) executed the frozen
adversarial experiment FROZEN_cycle_38048232833_baseline_reproducibility.json.
Verdict: NOT_REPRODUCED. The accepted state recorded JP=0.659/LD=0.4258, but
three identical fresh runs (pinned env python 3.12.3 / numpy 2.5.3 /
sklearn 1.9.1) give JP=0.5925/LD=0.348125.

This test (cheap, no heavy computation) locks in:
  1. state/evaluation.json carries the reproducible value, not the archived one.
  2. the archived value is preserved (provenance, not deleted).
  3. the metadata content hash is pinned in the harness.
  4. the frozen result artifact records NOT_REPRODUCED with matching numbers.
"""
import json
import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / "state/evaluation.json"
HARNESS = REPO / "evaluation/verify_frozen_baseline.py"
RESULT = REPO / "results/evaluation/frozen_baseline_reproducibility/FROZEN_cycle_38048232833_RESULT.json"
DIAGNOSIS = REPO / "results/evaluation/OPERATIONAL_RESUME_38051663272_DIAGNOSIS.json"
METADATA = Path("/tmp/lex_accepted/legal-distance/evaluation/data/174k/metadata_174k.json")

EXPECTED_METADATA_SHA256 = "34a0d4677c14c7f01b8b918bf87f5c330635dd3b620d83a75ba8b50e9fe59469"
REPRODUCIBLE_JP = 0.5925
REPRODUCIBLE_LD = 0.348125
ARCHIVED_JP = 0.659
ARCHIVED_LD = 0.4258
TOL = 1e-9


def test():
    errors = []
    state = json.loads(STATE.read_text())
    fb = state["frozen_production_baseline"]

    # 1. state carries the reproducible value
    if abs(fb["jurist_preference_rate"] - REPRODUCIBLE_JP) > TOL:
        errors.append(f"state JP={fb['jurist_preference_rate']} != reproducible {REPRODUCIBLE_JP}")
    if abs(fb["language_dominance_score"] - REPRODUCIBLE_LD) > TOL:
        errors.append(f"state LD={fb['language_dominance_score']} != reproducible {REPRODUCIBLE_LD}")
    if fb.get("verification_config_hash") != "a31c443a9b0e992e":
        errors.append("state config hash is not the pinned reproducible hash a31c443a9b0e992e")

    # 2. archived value preserved
    arch = state.get("baseline_reproducibility_repair", {}).get("recorded_value_archived", {})
    if abs(arch.get("jurist_preference_rate", -1) - ARCHIVED_JP) > TOL:
        errors.append("archived JP not preserved")
    if abs(arch.get("language_dominance_score", -1) - ARCHIVED_LD) > TOL:
        errors.append("archived LD not preserved")
    if state.get("baseline_reproducibility_repair", {}).get("verdict") != "NOT_REPRODUCED":
        errors.append("state repair verdict is not NOT_REPRODUCED")
    if state.get("meta_stability", {}).get("status") != "META_UNSTABLE_ACROSS_ENVIRONMENTS":
        errors.append("meta_stability flag missing/incorrect")

    # 3. metadata pin present in harness and consistent
    harness_src = HARNESS.read_text()
    m = re.search(r'PINNED_METADATA_SHA256\s*=\s*"([0-9a-f]{64})"', harness_src)
    if not m:
        errors.append("harness does not define PINNED_METADATA_SHA256")
    elif m.group(1) != EXPECTED_METADATA_SHA256:
        errors.append("harness metadata pin != expected")
    if METADATA.exists():
        actual = hashlib.sha256(METADATA.read_bytes()).hexdigest()
        if actual != EXPECTED_METADATA_SHA256:
            errors.append(f"mounted metadata sha256 {actual} != pinned {EXPECTED_METADATA_SHA256}")

    # 4. frozen result artifact
    if RESULT.exists():
        res = json.loads(RESULT.read_text())
        if res.get("verdict") != "NOT_REPRODUCED":
            errors.append("result verdict != NOT_REPRODUCED")
        r1 = res.get("run1", {})
        if abs(r1.get("jurist_preference_rate", -1) - REPRODUCIBLE_JP) > TOL:
            errors.append("result run1 JP mismatch")
        if abs(r1.get("language_dominance_score", -1) - REPRODUCIBLE_LD) > TOL:
            errors.append("result run1 LD mismatch")
    else:
        errors.append("frozen result artifact missing")

    if DIAGNOSIS.exists():
        d = json.loads(DIAGNOSIS.read_text())
        if d.get("frozen_experiment_outcome", {}).get("verdict") != "NOT_REPRODUCED":
            errors.append("diagnosis outcome verdict mismatch")
        if not d.get("audit_ready"):
            errors.append("diagnosis audit_ready flag false")
    else:
        errors.append("diagnosis artifact missing")

    if errors:
        print("FAILED:")
        for e in errors:
            print("  -", e)
        return False
    print("PASSED: baseline reproducibility repair is internally consistent and evidence-backed.")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if test() else 1)
