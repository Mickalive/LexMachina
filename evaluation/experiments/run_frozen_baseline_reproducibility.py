#!/usr/bin/env python3
"""
Executes the FROZEN adversarial experiment authored in
evaluation/experiments/FROZEN_cycle_38048232833_baseline_reproducibility.json.

This is a READ-ONLY reproduction attack. It does NOT modify:
  - the frozen spec (thresholds / sample / metric / success rule stay byte-identical)
  - the harness (evaluation/verify_frozen_baseline.py)
  - any accepted peer artifact under /tmp/lex_accepted

It DOES overwrite evaluation/results/174k_tfidf_formal_suite/verification_latest.json
(the harness's designed "latest pointer"), so the pre-existing pointer is copied to
results/evaluation/frozen_baseline_reproducibility/PRE_verification_latest.json first.

Outputs (all inside the evaluation lane namespace):
  results/evaluation/frozen_baseline_reproducibility/
      PRE_verification_latest.json
      run1_verification.json, run1_stdout.log
      run2_verification.json, run2_stdout.log
      provenance.json
      FROZEN_cycle_38048232833_RESULT.json   (the claim-bearing result)
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/home/runner/work/LexMachina/LexMachina")
SPEC = REPO / "evaluation/experiments/FROZEN_cycle_38048232833_baseline_reproducibility.json"
HARNESS = REPO / "evaluation/verify_frozen_baseline.py"
FORMAL_DIR = REPO / "evaluation/results/174k_tfidf_formal_suite"
OUT = REPO / "results/evaluation/frozen_baseline_reproducibility"
TARGET = "cited_decisions_tfidf_outcome_hybrid_0.5"

PEER_METADATA = Path("/tmp/lex_accepted/legal-distance/evaluation/data/174k/metadata_174k.json")
PEER_EMB_DIRS = {
    "tfidf_embeddings": Path("/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map_174k/tfidf_embeddings"),
    "legal_tfidf_embeddings": Path("/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_artifacts() -> dict:
    out = {}
    if PEER_METADATA.exists():
        out["metadata_174k.json"] = {"sha256": sha256(PEER_METADATA), "bytes": PEER_METADATA.stat().st_size}
    emb = {}
    for label, d in PEER_EMB_DIRS.items():
        if not d.exists():
            continue
        for p in sorted(d.glob("*.npy")):
            emb[f"{label}/{p.name}"] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    out["embeddings"] = emb
    return out


def load_latest():
    with open(FORMAL_DIR / "verification_latest.json") as f:
        return json.load(f)


def load_latest_provenance():
    p = FORMAL_DIR / "verification_latest_provenance.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {}


def extract(verif: dict) -> dict:
    row = verif.get(TARGET, {})
    return {
        "target_representation": TARGET,
        "jurist_preference_rate": row.get("jurist_preference_rate"),
        "language_dominance_score": row.get("language_dominance_score"),
        "verdict": row.get("verdict"),
        "both_pass": row.get("both_pass"),
        "all_reps": {
            k: {
                "verdict": v.get("verdict"),
                "jurist_preference_rate": v.get("jurist_preference_rate"),
                "language_dominance_score": v.get("language_dominance_score"),
                "both_pass": v.get("both_pass"),
            }
            for k, v in verif.items()
        },
        "reps_passing_both": sum(1 for v in verif.values() if v.get("both_pass")),
        "reps_tested": len(verif),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(SPEC) as f:
        spec = json.load(f)
    recorded_jp = spec["claim_under_test"]["recorded_jurist_preference_rate"]
    recorded_ld = spec["claim_under_test"]["recorded_language_dominance_score"]
    tol = 0.001

    provenance = {
        "experiment": spec["claim_under_test"],
        "frozen_spec_path": str(SPEC.relative_to(REPO)),
        "frozen_spec_sha256": sha256(SPEC),
        "harness_path": str(HARNESS.relative_to(REPO)),
        "harness_sha256": sha256(HARNESS),
        "harness_v3_sha256": sha256(REPO / "evaluation/evaluation_v3_harness.py"),
        "success_rule": spec["success_rule"],
        "recorded_jp": recorded_jp,
        "recorded_ld": recorded_ld,
        "tolerance": tol,
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version,
        "peer_artifacts": hash_artifacts(),
    }

    # Preserve the pre-run pointer before the harness overwrites it.
    pre_path = FORMAL_DIR / "verification_latest.json"
    pre_out = OUT / "PRE_verification_latest.json"
    if pre_path.exists():
        pre_bytes = pre_path.read_bytes()
        if not pre_out.exists():
            (OUT / "PRE_verification_latest.json").write_bytes(pre_bytes)
        else:
            (OUT / "PRE_verification_latest_rerun.json").write_bytes(pre_bytes)
        provenance["pre_verification_latest_sha256"] = hashlib.sha256(pre_bytes).hexdigest()
        pre_verif = json.loads(pre_bytes)
        provenance["pre_verification_pointer_metrics"] = extract(pre_verif)
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    # Run the frozen harness N=2 times exactly as authored.
    runs = []
    for i in (1, 2):
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, str(HARNESS)],
            cwd=str(REPO), capture_output=True, text=True,
        )
        dt = time.time() - t0
        (OUT / f"run{i}_stdout.log").write_text(proc.stdout + "\n---STDERR---\n" + proc.stderr)
        verif = load_latest()
        (OUT / f"run{i}_verification.json").write_text(json.dumps(verif, indent=2, default=str) + "\n")
        metrics = extract(verif)
        metrics["returncode"] = proc.returncode
        metrics["wall_seconds"] = round(dt, 2)
        metrics["harness_provenance"] = load_latest_provenance()
        runs.append(metrics)

    r1, r2 = runs
    same_between_runs = (
        abs(r1["jurist_preference_rate"] - r2["jurist_preference_rate"]) <= 1e-12
        and abs(r1["language_dominance_score"] - r2["language_dominance_score"]) <= 1e-12
    )
    r1_matches_recorded = (
        abs(r1["jurist_preference_rate"] - recorded_jp) <= tol
        and abs(r1["language_dominance_score"] - recorded_ld) <= tol
    )
    r2_matches_recorded = (
        abs(r2["jurist_preference_rate"] - recorded_jp) <= tol
        and abs(r2["language_dominance_score"] - recorded_ld) <= tol
    )
    reproduced = bool(r1["returncode"] == 0 and r2["returncode"] == 0
                      and same_between_runs and r1_matches_recorded and r2_matches_recorded)

    result = {
        "cycle_run": "operational-resume-38051663272 (snapshot of 38048817288)",
        "lane": "evaluation",
        "direction_version": spec["direction_version"],
        "experiment_frozen_at_utc": spec["frozen_at_utc"],
        "executed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": "REPRODUCED" if reproduced else "NOT_REPRODUCED",
        "success_rule_evaluation": {
            "runs_executed": 2,
            "same_between_runs": same_between_runs,
            "run1_matches_recorded": r1_matches_recorded,
            "run2_matches_recorded": r2_matches_recorded,
            "recorded_jp": recorded_jp,
            "recorded_ld": recorded_ld,
            "tolerance": tol,
        },
        "run1": r1,
        "run2": r2,
        "provenance_ref": "results/evaluation/frozen_baseline_reproducibility/provenance.json",
        "raw_logs": [
            "results/evaluation/frozen_baseline_reproducibility/run1_stdout.log",
            "results/evaluation/frozen_baseline_reproducibility/run2_stdout.log",
        ],
        "raw_verifications": [
            "results/evaluation/frozen_baseline_reproducibility/run1_verification.json",
            "results/evaluation/frozen_baseline_reproducibility/run2_verification.json",
        ],
    }
    (OUT / "FROZEN_cycle_38048232833_RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"verdict": result["verdict"], **result["success_rule_evaluation"],
                      "run1_jp": r1["jurist_preference_rate"], "run1_ld": r1["language_dominance_score"],
                      "run2_jp": r2["jurist_preference_rate"], "run2_ld": r2["language_dominance_score"],
                      "reps_passing_both_run1": r1["reps_passing_both"],
                      "reps_passing_both_run2": r2["reps_passing_both"]}, indent=2))
    return 0 if reproduced else 1


if __name__ == "__main__":
    sys.exit(main())
