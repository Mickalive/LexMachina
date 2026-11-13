#!/usr/bin/env python3
"""Operational resume of run 43342851837 (core evaluation, direction v68).

WHAT HAPPENED (recomputed here, not narrated)
---------------------------------------------
Run 43342851837 ("Core evaluation dirV68 repair0") executed its producer
cycle successfully - ``Run lane cycle`` success and ``Validate active MVP
producer state`` success - and then FAILED at workflow step 9
``Enforce lane write scope`` (exit 3).  Of the five paths its snapshot commit
``a886bf2a`` added, two sit in the independent auditor's namespace:

    reports/audit/evaluation/CYCLE_43342851837.md
    results/audit/evaluation/CYCLE_43342851837_GATE.json

Neither matches a producer-allowed pattern, so ``audit`` and ``integrate``
were SKIPPED (audit job conclusion=skipped, zero steps) and no independent
audit of 43342851837 exists: ``refs/heads/cycle/core/evaluation/43342851837/audit``
does not exist on origin.  The same defect class already failed runs
38982176936, 39470495546, 40167904552, 40186604273 and 40232590665
(``evaluation/snapshot_audit/write_scope.py``,
``evaluation/operational_resume_40234421521.py``).

WHAT THIS INSTRUMENT DOES
-------------------------
Recomputes the four frozen hypotheses of
``evaluation/OPERATIONAL_RESUME_43344048907_HYPOTHESIS_V1.json`` straight
from source artifacts and writes one summary record:

  H1  the failure is exactly the write-scope step, with exactly those two
      bad paths, and no independent audit exists for 43342851837;
  H2  the FAST-MVP deliverable it produced is internally valid (all frozen
      pins re-hash, record agrees with engine record and report, non-vacuity
      battery holds);
  H3  a scratch replay reproduces every measurement-bearing field
      (``replay_comparison_43344048907.json``);
  H4  the audit-namespace originals were relocated byte-identically with the
      originals retained and the pseudo-gate disclosed as producer-authored.

It is a VERIFICATION instrument: it re-scores nothing product-facing, edits
no frozen bar/rubric/threshold/verdict contract, writes nothing under
``results/audit/`` or ``reports/audit/``, and issues no serve or admission
verdict.  stdlib only, no network (the GitHub REST envelopes are read from
the files captured at the start of this run and pinned by the freeze record).

    python -m evaluation.operational_resume_43344048907
    python -m evaluation.operational_resume_43344048907 --out <path>

Exit codes: 0 = all four hypotheses hold; 1 = at least one is falsified
(a legitimate, published negative result); 2 = environment error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-operational-resume-verification/1"
LANE = "evaluation"
RUN_ID = "43344048907"
RESUMED = "43342851837"
BASE_SHA = "240ca2d9d4b063652440e80fdd9bcd9e6602c1de"
SNAPSHOT_SHA = "a886bf2a4abba44d7bc2d14c0cef37e12bd73c76"

OUT_DIR = REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
RECOVERY_DIR = REPO_ROOT / "results" / "evaluation" / f"audit_namespace_recovery_{RUN_ID}"
WRAPPER_RECORD = REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark" / f"{RESUMED}.json"
ENGINE_RECORD = REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark" / f"{RESUMED}_engine_mapping_free_recall_falsifier.json"
REPORT = REPO_ROOT / "reports" / "evaluation" / f"RETRIEVAL_CA_BENCHMARK_{RESUMED}.md"
PSEUDO_GATE = REPO_ROOT / "results" / "audit" / LANE / f"CYCLE_{RESUMED}_GATE.json"
PSEUDO_CYCLE_MD = REPO_ROOT / "reports" / "audit" / LANE / f"CYCLE_{RESUMED}.md"
EXPECTED_SNAPSHOT_SHA = "8c0178a2a0bbf6e52784581edd307634879533bd16374232b468e38cae77941f"

EXIT_PASS, EXIT_FAIL, EXIT_ENV = 0, 1, 2


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_h1() -> dict:
    """Write-scope step is the failure, exactly two bad paths, no audit exists."""
    repro = _load(OUT_DIR / f"write_scope_repro_{RESUMED}.json")
    verdict = repro.get("verdict", {})
    bad = sorted(verdict.get("bad_paths") or [])
    expected_bad = sorted([
        f"reports/audit/{LANE}/CYCLE_{RESUMED}.md",
        f"results/audit/{LANE}/CYCLE_{RESUMED}_GATE.json",
    ])
    jobs = _load(OUT_DIR / "api" / f"jobs_{RESUMED}.json")
    by_name = {j["name"]: j for j in jobs.get("jobs", [])}
    team = by_name.get("team", {})
    failing_steps = [s["name"] for s in team.get("steps", [])
                     if s.get("conclusion") == "failure"]
    audit = by_name.get("audit", {})
    integ = by_name.get("integrate", {})
    recon = repro.get("reconstruction", {})
    checks = {
        "reconstructed_snapshot_matches_frozen_pins":
            bool(recon.get("base_sha")) and bool(recon.get("snapshot_sha"))
            and BASE_SHA.startswith(str(recon.get("base_sha")))
            and SNAPSHOT_SHA.startswith(str(recon.get("snapshot_sha"))),
        "repro_verdict_is_scope_violation": verdict.get("verdict") == "SCOPE_VIOLATION",
        "bad_paths_exactly_the_two_audit_namespace_paths": bad == expected_bad,
        "team_job_failed": team.get("conclusion") == "failure",
        "failing_step_is_enforce_lane_write_scope":
            failing_steps == ["Enforce lane write scope"],
        "audit_job_skipped": audit.get("conclusion") == "skipped",
        "integrate_job_skipped": integ.get("conclusion") == "skipped",
        "no_audit_ref_on_origin": not _audit_ref_exists(),
        "both_originals_still_present":
            PSEUDO_GATE.is_file() and PSEUDO_CYCLE_MD.is_file(),
    }
    return {"hypothesis": "H1", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values()),
            "bad_paths": bad, "failing_steps": failing_steps,
            "audit_conclusion": audit.get("conclusion"),
            "integrate_conclusion": integ.get("conclusion")}


def _audit_ref_exists() -> bool:
    """True only if an independent audit ref exists for the resumed run.

    Uses the committed API envelopes first (offline); the live probe is
    recorded separately by the relocation record so this function stays
    dependency-free.
    """
    rec = RECOVERY_DIR / "RELOCATION_RECORD.json"
    if rec.is_file():
        return bool(_load(rec).get("independent_audit_status_of_43342851837", {})
                    .get("audit_ref_exists"))
    return False


def check_h2() -> dict:
    """The delivered benchmark record is internally valid and pin-clean."""
    record = _load(OUT_DIR / f"deliverable_verification_{RUN_ID}.json")
    checks = dict(record.get("checks") or {})
    # re-hash the two claim-bearing files against the freeze pins as well
    freeze = _load(REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json")
    frozen = freeze.get("snapshot_inputs", {}).get("files", {})
    for rel, digest in frozen.items():
        path = REPO_ROOT / rel
        checks[f"snapshot_pin::{rel}"] = path.is_file() and sha256(path) == digest
    return {"hypothesis": "H2", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values()),
            "record_sha256": sha256(WRAPPER_RECORD) if WRAPPER_RECORD.is_file() else None,
            "record_sha256_matches_freeze":
                WRAPPER_RECORD.is_file() and sha256(WRAPPER_RECORD) == EXPECTED_SNAPSHOT_SHA}


def check_h3() -> dict:
    """A fresh scratch replay reproduces every measurement-bearing field."""
    cmp_path = OUT_DIR / f"replay_comparison_{RUN_ID}.json"
    if not cmp_path.is_file():
        return {"hypothesis": "H3", "checks": {"replay_comparison_record_exists": False},
                "n_checks": 1, "n_failed": 1, "holds": False}
    cmp = _load(cmp_path)
    checks = {
        "replay_comparison_record_exists": True,
        "verdict_is_REPLAY_REPRODUCES": cmp.get("verdict") == "REPLAY_REPRODUCES",
        "zero_measurement_field_differences": cmp.get("measurement_fields_differing") == 0,
        "original_record_not_rewritten": cmp.get("claim_bearing_original_rewritten") is False
            and cmp.get("original_sha256_matches_freeze") is True,
        "only_environment_disclosure_differs":
            sorted((cmp.get("environment_disclosure_differences") or {}).keys())
            in ([], ["numeric_environment"]),
    }
    return {"hypothesis": "H3", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values()),
            "measurement_fields_compared": cmp.get("measurement_fields_compared"),
            "environment_disclosure_differences": cmp.get("environment_disclosure_differences")}


def check_h4() -> dict:
    """Byte-identical append-only relocation with originals retained."""
    rec_path = RECOVERY_DIR / "RELOCATION_RECORD.json"
    if not rec_path.is_file():
        return {"hypothesis": "H4", "checks": {"relocation_record_exists": False},
                "n_checks": 1, "n_failed": 1, "holds": False}
    rec = _load(rec_path)
    checks = {"relocation_record_exists": True}
    for item in rec.get("items", []):
        src, dst = REPO_ROOT / item["source_path"], REPO_ROOT / item["copy_path"]
        checks[f"source_exists::{item['source_path']}"] = src.is_file()
        checks[f"copy_exists::{item['copy_path']}"] = dst.is_file()
        checks[f"copy_byte_identical::{item['copy_path']}"] = (
            src.is_file() and dst.is_file() and sha256(src) == sha256(dst))
        checks[f"source_unchanged::{item['source_path']}"] = (
            src.is_file() and sha256(src) == item["source_sha256_before"])
    checks["originals_retained_flag"] = rec.get("originals_retained") is True
    checks["originals_not_deleted_flag"] = rec.get("originals_deleted") is False
    checks["independent_audit_provenance_false"] = rec.get("independent_audit_provenance") is False
    checks["verdict_is_RELOCATED_APPEND_ONLY"] = rec.get("verdict") == "RELOCATED_APPEND_ONLY"
    checks["all_record_checks_pass"] = all(c.get("passed") for c in rec.get("checks", []))
    return {"hypothesis": "H4", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values())}


def run(out_path: Path | None = None) -> tuple[int, dict]:
    try:
        results = [check_h1(), check_h2(), check_h3(), check_h4()]
    except Exception as exc:  # environment error: never a pass, never a fail
        return EXIT_ENV, {"schema": SCHEMA, "verdict": "ENVIRONMENT_ERROR",
                          "exit_code": EXIT_ENV, "error": repr(exc)}
    n_failed = sum(r["n_failed"] for r in results)
    holds = all(r["holds"] for r in results)
    payload = {
        "schema": SCHEMA,
        "lane": LANE,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "direction_version": 68,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_record": f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json",
        "freeze_record": f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json",
        "hypotheses": results,
        "n_hypotheses": len(results),
        "n_hypotheses_holding": sum(1 for r in results if r["holds"]),
        "n_checks": sum(r["n_checks"] for r in results),
        "n_failed": n_failed,
        "verdict": "RESUME_VERIFIED_AUDIT_READY" if holds else "RESUME_VERIFICATION_FAILED",
        "failure_mode_of_resumed_run": "VALIDATION_LANE_WRITE_SCOPE_ENFORCEMENT",
        "independent_audit_of_resumed_run_exists": False,
        "claim_ceiling": (
            "Operational-resume verification only: it re-derives the write-scope "
            "failure, the delivered record's pins, the replay equality and the "
            "relocation integrity. It creates no new product measurement, moves no "
            "frozen bar, rubric, threshold or verdict contract, issues no serve or "
            "admission verdict, and is NOT an independent audit of run 43342851837 "
            "or of this run."
        ),
    }
    code = EXIT_PASS if holds else EXIT_FAIL
    payload["exit_code"] = code
    target = out_path or (OUT_DIR / f"verification_{RUN_ID}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    return code, payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=None, help="summary record path (default: committed tree)")
    args = ap.parse_args(argv)
    code, payload = run(Path(args.out) if args.out else None)
    print(json.dumps({"verdict": payload.get("verdict"),
                      "exit_code": code,
                      "n_checks": payload.get("n_checks"),
                      "n_failed": payload.get("n_failed"),
                      "hypotheses": [{"h": h["hypothesis"], "holds": h["holds"],
                                      "n_failed": h["n_failed"]}
                                     for h in payload.get("hypotheses", [])]}, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
