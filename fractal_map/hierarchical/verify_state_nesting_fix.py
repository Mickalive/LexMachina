#!/usr/bin/env python3
"""Verify the run-36025207612 state nesting corrections against the honest audit.

Run 36025207612 (operational resume of zero-delta run 36023963893) applied the
REVISE-gate required fixes from the independent audit of run 36018593628 to the
live claim surface `state/fractal-map.json`:

  Fix 1: correct/annotate every nesting_score over-claim in validation_metrics
         (9 ACCEPTED-tier entries) + same-class over-claims in metrics_summary and
         compressed_resolution_ladder, using ONLY values from
         results/fractal_map/evaluation/resume_36014970673_nesting_audit.json
         (reproduced bit-exactly in this run).
  Fix 2: record durable delta (github_run/resume chain + key_findings).

This script independently re-checks that the live state now agrees with the honest
audit artifact and the accepted compressed_resolution_ladder_all_modes.json.
It does NOT modify any file unless --write-artifact is given.

Usage:
    python3 fractal_map/hierarchical/verify_state_nesting_fix.py [--write-artifact]
"""
import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
STATE = BASE / "state" / "fractal-map.json"
AUDIT = BASE / "results" / "fractal_map" / "evaluation" / "resume_36014970673_nesting_audit.json"
LADDER = BASE / "results" / "fractal_map" / "evaluation" / "compressed_resolution_ladder_all_modes.json"

REVISE_COMPRESSED = [
    "cited_decisions_tfidf_174k_compressed",
    "cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed",
    "full_text_tfidf_light_174k_compressed",
    "regeste_full_text_hybrid_0.5_174k_compressed",
    "regeste_full_text_hybrid_0.7_174k_compressed",
    "cited_decisions_tfidf_outcome_hybrid_0.5_21k_compressed",
    "regeste_tfidf_21k_compressed",
]
REVISE_BY_CONSTRUCTION = [
    "cited_decisions_tfidf_outcome_hybrid_0.5",
    "cited_decisions_tfidf_outcome_hybrid_0.7",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-artifact", action="store_true",
                    help="write results/fractal_map/evaluation/operational_resume_36025207612_state_nesting_fix.json")
    args = ap.parse_args()

    state = json.loads(STATE.read_text())
    audit = json.loads(AUDIT.read_text())
    ladder = json.loads(LADDER.read_text())

    checks = []  # (name, ok, detail)

    def check(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": str(detail)})

    # --- Fix 1a: 7 compressed-family ACCEPTED entries
    for k in REVISE_COMPRESSED:
        e = state["validation_metrics"][k]
        a = audit["modes"][k]
        check(f"compressed:{k}:nesting_score==honest",
              e["nesting_score"] == a["honest_mean_strict_nesting"],
              f"state={e['nesting_score']} audit={a['honest_mean_strict_nesting']}")
        check(f"compressed:{k}:legacy_preserved",
              e.get("legacy_recorded_nesting_score") == 1.0,
              f"legacy={e.get('legacy_recorded_nesting_score')}")
        check(f"compressed:{k}:defect_note",
              "NESTING_METRIC_DEFECT_v1" in e.get("nesting_metric_note", ""),
              "note present")
        check(f"compressed:{k}:transitions_present",
              len(e.get("honest_strict_nesting_transitions", {})) == 4,
              f"n_trans={len(e.get('honest_strict_nesting_transitions', {}))}")

    # --- Fix 1b: 2 by-construction 1000-scale ACCEPTED entries
    for k in REVISE_BY_CONSTRUCTION:
        e = state["validation_metrics"][k]
        a = audit["modes"][k]
        check(f"byconst:{k}:pair_value_kept",
              e["nesting_score"] == 1.0,
              f"nesting_score={e['nesting_score']}")
        check(f"byconst:{k}:ladder_mean_honest",
              e.get("honest_strict_nesting_ladder_mean") == a["honest_mean_strict_nesting"],
              f"state={e.get('honest_strict_nesting_ladder_mean')} audit={a['honest_mean_strict_nesting']}")
        check(f"byconst:{k}:scope_annotated",
              "by-construction" in e.get("nesting_score_scope", ""),
              "scope present")

    # --- REPRODUCED-tier annotations
    cp = state["validation_metrics"]["center_projected_hierarchical"]
    cpa = audit["reference_dirs"]["hierarchical_map_center_projected"]
    check("center_projected:ladder_mean_honest",
          cp.get("honest_strict_nesting_ladder_mean") == cpa["honest_mean_strict_nesting"],
          f"state={cp.get('honest_strict_nesting_ladder_mean')} audit={cpa['honest_mean_strict_nesting']}")
    check("center_projected:scope_annotated",
          "by-construction" in cp.get("nesting_score_scope", ""), "scope present")
    cl = state["validation_metrics"]["hierarchical_leiden_concat_legacy"]
    check("concat_legacy:scope_annotated",
          "by-construction" in cl.get("nesting_score_scope", ""), "scope present")

    # --- compressed_resolution_ladder.nesting_change corrected vs accepted artifact
    changes = [r["nesting_change"] for r in ladder["results"].values()]
    honest_mean = sum(changes) / len(changes)
    lcr = state["validation_metrics"]["compressed_resolution_ladder"]
    check("ladder:nesting_change==honest_mean",
          abs(lcr["nesting_change"] - honest_mean) < 1e-12,
          f"state={lcr['nesting_change']} computed={honest_mean}")
    check("ladder:range_matches",
          lcr["nesting_change_range"] == [min(changes), max(changes)],
          f"state={lcr['nesting_change_range']} computed={[min(changes), max(changes)]}")
    check("ladder:legacy_preserved",
          lcr.get("legacy_recorded_nesting_change") == 0.0,
          f"legacy={lcr.get('legacy_recorded_nesting_change')}")

    # --- metrics_summary.tfidf_modes_174k_compressed.all_nesting_perfect corrected
    ts = state["metrics_summary"]["tfidf_modes_174k_compressed"]
    check("tfidfsum:all_nesting_perfect==false", ts["all_nesting_perfect"] is False, str(ts["all_nesting_perfect"]))
    check("tfidfsum:legacy_preserved", ts.get("legacy_recorded_all_nesting_perfect") is True,
          str(ts.get("legacy_recorded_all_nesting_perfect")))
    for mode, honest in ts.get("honest_strict_nesting_by_mode", {}).items():
        a = audit["modes"][mode]
        check(f"tfidfsum:{mode}:honest_match",
              honest == a["honest_mean_strict_nesting"],
              f"state={honest} audit={a['honest_mean_strict_nesting']}")

    # --- Fix 2: durable delta recording
    check("delta:github_run", state.get("github_run") == "36025207612", state.get("github_run"))
    check("delta:resume_from", state.get("resume_from_run_id") == "36023963893", state.get("resume_from_run_id"))
    check("delta:key_finding_run", any("RUN 36025207612" in kf for kf in state.get("key_findings", [])), "key_finding present")
    check("delta:key_finding_23963893", any("RUN 36023963893" in kf for kf in state.get("key_findings", [])), "key_finding present")
    check("delta:metric_defect_notes", "NESTING_METRIC_DEFECT_v1" in state.get("metric_defect_notes", {}), "top-level note present")

    n_ok = sum(1 for c in checks if c["ok"])
    output = {
        "run": "36025207612",
        "resume_from_run_id": "36023963893",
        "direction_version": 25,
        "verification": "state/fractal-map.json nesting corrections vs honest audit artifact",
        "checks_total": len(checks),
        "checks_passed": n_ok,
        "checks_failed": len(checks) - n_ok,
        "audit_artifact": str(AUDIT.relative_to(BASE)),
        "ladder_artifact": str(LADDER.relative_to(BASE)),
        "failed_checks": [c for c in checks if not c["ok"]],
        "all_checks": checks,
    }
    print(json.dumps({k: v for k, v in output.items() if k != "all_checks"}, indent=2))

    if args.write_artifact:
        out = BASE / "results" / "fractal_map" / "evaluation" / "operational_resume_36025207612_state_nesting_fix.json"
        out.write_text(json.dumps(output, indent=2) + "\n")
        print(f"wrote {out}")

    return 0 if n_ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())