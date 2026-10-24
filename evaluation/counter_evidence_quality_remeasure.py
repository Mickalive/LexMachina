#!/usr/bin/env python3
"""Item-(4) CONDITIONAL RE-MEASURE of the v66 counter-evidence content-quality
defect classes on the NEW accepted product head.

TRIGGER (v66 evaluation ordered work, item 4): Core Product landed the P0
content-quality filter in product/query/counter_evidence_span.py at accepted
cycle 40064639100 (accept commit 3495c13361ddf40f88d31c1fbb47b00bc06eee63,
PASS gate). This instrument re-runs the FROZEN item-(2) probe protocol - the
D2/D3/D4 predicates imported BY VALUE from the accepted instrument
evaluation/counter_evidence_quality_benchmark.py (accepted cycle 40062917685,
file sha256 pinned below and re-verified at runtime) - over:

  (a) the accepted BASELINE population (the same 15 shipped slice bundles),
      re-probed for stability against the accepted baseline of record
      results/evaluation/counter_evidence_quality_benchmark/40062917685.json;
  (b) the NEW head's shipped slice artifacts (labelled 'new_head'), each
      sha256-pinned at runtime.

It publishes the defect histogram BEFORE/AFTER, a per-class verdict of
CONFIRMED-REPAIRED / STILL-DEFECTIVE / INCONCLUSIVE_NO_CLASS_ROW, the
verified-row yield and abstention context side by side (requirement 26), and
re-runs the frozen controls C1/C2/C3. NO frozen predicate, rubric, bar,
threshold or verdict contract is edited, re-derived or re-tuned. No Product
code is imported; no network is used; the accepted-product mount at
/tmp/lex_accepted/product is read-only input.

Verdict vocabulary (per defect class D in {D2,D3,D4}):
  STILL-DEFECTIVE            new population has >=1 verified row with D
  CONFIRMED-REPAIRED         baseline had >=1 row with D, new population has
                             0 rows with D AND the new population contains at
                             least one verified row that the predicate could
                             have flagged for D had the defect been present
                             (i.e. the class is measurable on the new pop)
  INCONCLUSIVE_NO_CLASS_ROW  baseline had >=1 row with D, new population has 0
                             rows with D but NO row on which the class could
                             have been re-scored -> not evidence of repair

Exit codes:
  0  REPAIR_CONFIRMED (every baseline defect class CONFIRMED-REPAIRED)
  1  REPAIR_NOT_CONFIRMED (any class STILL-DEFECTIVE, or any INCONCLUSIVE
     while a class remains unhandled) -- the honest default given scoping
  2  ENVIRONMENT_OR_VACUOUS (mount missing, hypothesis/instrument digest
     drift, or a frozen control failed)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.counter_evidence_quality_benchmark import (  # noqa: E402
    EXPECTED_HYPOTHESIS_SHA,
    LANGUAGE_MARKER_SETS,
    LETTERHEAD_ZONE_OFFSET_MAX,
    MARKUP_TOKENS,
    MIN_MARKER_HITS,
    MOUNT,
    PRIOR_CYCLE_CONTROL,
    PROBE_BUNDLES,
    SCHEMA as FROZEN_SCHEMA,
    _sha256_file,
    classify_verified_row,
    numeric_environment,
    probe_bundle,
)

SCHEMA = "lex-evaluation-counter-evidence-quality-remeasure/1"

# sha256 of the FROZEN instrument file at freeze time (recorded in the cycle
# freeze record 40068038783). Re-verified at runtime; drift => exit 2.
FROZEN_INSTRUMENT_SHA_EXPECTED = (
    "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"
)
FROZEN_INSTRUMENT = _REPO_ROOT / "evaluation" / "counter_evidence_quality_benchmark.py"

BASELINE_OF_RECORD = (
    _REPO_ROOT / "results/evaluation/counter_evidence_quality_benchmark/40062917685.json"
)

NEW_HEAD = "3495c13361ddf40f88d31c1fbb47b00bc06eee63"
NEW_HEAD_ACCEPT = "40064639100"

# The NEW head's shipped slice artifacts (population change, labelled).
NEW_HEAD_BUNDLES = {
    "offline_accept_40064639100": [
        "results/product/offline_slice/20261024T024341Z/rent-default.bundle.json",
    ],
}

DEFECT_CLASSES = ("D2_letterhead_zone", "D3_markup_residue", "D4_language_marker_mismatch")


def _marker_class_measurable(row_detail: dict, defect: str) -> bool:
    """Could defect D have fired on this row's evidence (class-eligibility)?"""
    if defect == "D2_letterhead_zone":
        return row_detail.get("grounded_in") == "full_text"
    if defect == "D3_markup_residue":
        # any evidence string could carry markup tokens
        return bool(row_detail.get("evidence_len"))
    if defect == "D4_language_marker_mismatch":
        return row_detail.get("marker_language_out_of_scope") is None and bool(
            row_detail.get("evidence_len")
        )
    return False


def _histogram(bundles: list[dict]) -> tuple[int, int, dict, set]:
    n_verified = 0
    n_defective = 0
    hist: dict[str, int] = {}
    ids: set[str] = set()
    for b in bundles:
        for r in b.get("verified_rows", []):
            n_verified += 1
            if r["defects"]:
                n_defective += 1
                ids.add(r["decision_id"])
            for d in r["defects"]:
                hist[d] = hist.get(d, 0) + 1
    return n_verified, n_defective, hist, ids


def _controls() -> dict:
    """Re-run the frozen C1/C2/C3 controls verbatim (same planted rows as the
    accepted instrument; predicates imported by value)."""
    base_ft = ("Kantonsgericht von Graubünden\nDretgira chantunala dal Grischun\n" +
               ("_" * 120) + "\nRef.:\n" + ("x" * 500) +
               "\nGericht hat in Erwägung gesetzt, dass die Kündigung des Mietvertrags "
               "unwirksam ist.\n")
    letterhead_row = {"decision_id": "planted_letterhead", "language": "de",
                      "counter_status": "candidate-limiting", "counter_evidence_verified": True,
                      "counter_evidence": base_ft[:120], "full_text": base_ft,
                      "snippet": "", "regeste": "", "full_text_status": "hydrated"}
    mid_row = {"decision_id": "planted_mid", "language": "de",
               "counter_status": "candidate-limiting", "counter_evidence_verified": True,
               "counter_evidence": "Gericht hat in Erwägung gesetzt, dass die Kündigung des Mietvertrags unwirksam ist.",
               "full_text": base_ft, "snippet": "", "regeste": "", "full_text_status": "hydrated"}
    markup_row = {"decision_id": "planted_markup", "language": "de",
                  "counter_status": "candidate-limiting", "counter_evidence_verified": True,
                  "counter_evidence": "Regeste <mark>Mietvertrag</mark> Anfechtung der Kündigung",
                  "full_text": base_ft, "snippet": "", "regeste": "",
                  "full_text_status": "hydrated"}
    c_letterhead = classify_verified_row(letterhead_row)
    c_mid = classify_verified_row(mid_row)
    c_markup = classify_verified_row(markup_row)
    c1_passed = ("D2_letterhead_zone" in c_letterhead["defects"]
                 and "D2_letterhead_zone" not in c_mid["defects"]
                 and "D3_markup_residue" in c_markup["defects"])
    c1 = {"control": "C1_probe_classifies_planted_letterhead_mid_and_markup",
          "letterhead_defects": c_letterhead["defects"],
          "mid_document_defects": c_mid["defects"],
          "markup_defects": c_markup["defects"],
          "passed": c1_passed}
    lang_row = {"decision_id": "planted_lang", "language": "it",
                "counter_status": "candidate-limiting", "counter_evidence_verified": True,
                "counter_evidence": "Regeste Resolutiv bedingter Mietvertrag; Anfeuchtung der Kündigung; Erstreckung",
                "full_text": "y" * 900 + "Regeste Resolutiv bedingter Mietvertrag; Anfeuchtung der Kündigung; Erstreckung",
                "snippet": "", "regeste": "", "full_text_status": "lazy"}
    c_lang = classify_verified_row(lang_row)
    c2_passed = "D4_language_marker_mismatch" in c_lang["defects"]
    c2 = {"control": "C2_probe_detects_language_marker_mismatch",
          "defects": c_lang["defects"], "passed": c2_passed}
    rules_label_sha = _sha256_file(_REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json")
    rules_geometry_sha = _sha256_file(_REPO_ROOT / "evaluation/frozen_bars/RULES_GEOMETRY.json")
    c3_passed = (rules_label_sha ==
                 "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
                 and rules_geometry_sha ==
                 "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633")
    c3 = {"control": "C3_frozen_rules_rehash_holds_reported_only",
          "rules_label_sha256": rules_label_sha,
          "rules_geometry_sha256": rules_geometry_sha,
          "matches_expected": c3_passed, "passed": c3_passed,
          "note": "re-hashed REPORTED-ONLY; never applied, edited or re-derived"}
    # C4 (this cycle's addition, mechanical only): frozen instrument digest
    inst_sha = _sha256_file(FROZEN_INSTRUMENT)
    c4_passed = inst_sha == FROZEN_INSTRUMENT_SHA_EXPECTED
    c4 = {"control": "C4_frozen_instrument_digest_unchanged",
          "instrument_sha256": inst_sha,
          "expected": FROZEN_INSTRUMENT_SHA_EXPECTED,
          "passed": c4_passed,
          "note": "proves the imported D2/D3/D4 predicate file is byte-identical "
                  "to the frozen accepted instrument; the predicates themselves "
                  "are never re-derived here"}
    return {"C1": c1, "C2": c2, "C3": c3, "C4": c4}


def run(run_id: str, out_dir: Path, report_dir: Path) -> tuple[int, dict]:
    t0 = time.time()
    if not MOUNT.exists():
        return 2, {"schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_ERROR",
                   "detail": f"mount missing: {MOUNT}"}

    hyp_path = _REPO_ROOT / "evaluation" / "V65_HEAD_ADVANCE_CROSSCHECK_HYPOTHESIS_V2.json"
    hyp_sha = _sha256_file(hyp_path)
    if hyp_sha != EXPECTED_HYPOTHESIS_SHA:
        return 2, {"schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_ERROR",
                   "detail": f"hypothesis digest drift: {hyp_sha}"}

    controls = _controls()
    if not all(c["passed"] for c in controls.values()):
        return 2, {"schema": SCHEMA, "run_id": run_id,
                   "verdict": "ENVIRONMENT_OR_VACUOUS",
                   "detail": "one or more frozen controls failed", "controls": controls}

    # mount head
    import subprocess
    try:
        mount_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=MOUNT,
                                    capture_output=True, text=True, timeout=30,
                                    check=True).stdout.strip()
    except Exception:
        mount_head = "UNAVAILABLE"

    # ---- BEFORE: baseline population re-probe ----------------------------
    baseline_bundles = []
    for family, rels in PROBE_BUNDLES.items():
        for rel in rels:
            baseline_bundles.append(probe_bundle(MOUNT, rel, family))
    baseline_bundles.append(probe_bundle(MOUNT, PRIOR_CYCLE_CONTROL, "prior_cycle_control"))
    b_verified, b_defective, b_hist, b_ids = _histogram(baseline_bundles)

    # stability check vs accepted baseline of record
    stability = {"compared": False}
    if BASELINE_OF_RECORD.is_file():
        rec0 = json.loads(BASELINE_OF_RECORD.read_text())
        stability = {
            "compared": True,
            "baseline_of_record_run": rec0.get("run_id"),
            "record_n_verified": rec0.get("n_verified_rows_total"),
            "record_n_defective": rec0.get("n_verified_rows_with_defects"),
            "record_histogram": rec0.get("defect_histogram"),
            "reprobe_n_verified": b_verified,
            "reprobe_n_defective": b_defective,
            "reprobe_histogram": b_hist,
            "normalized_identical": (
                rec0.get("n_verified_rows_total") == b_verified
                and rec0.get("n_verified_rows_with_defects") == b_defective
                and rec0.get("defect_histogram") == b_hist
            ),
        }

    # ---- AFTER: new-head population --------------------------------------
    new_bundles = []
    for family, rels in NEW_HEAD_BUNDLES.items():
        for rel in rels:
            new_bundles.append(probe_bundle(MOUNT, rel, family))
    n_verified, n_defective, n_hist, n_ids = _histogram(new_bundles)

    # class-eligibility on the new population (for INCONCLUSIVE detection)
    eligible: dict[str, int] = {d: 0 for d in DEFECT_CLASSES}
    for b in new_bundles:
        for r in b.get("verified_rows", []):
            for d in DEFECT_CLASSES:
                if _marker_class_measurable(r.get("detail", {}), d):
                    eligible[d] += 1

    # ---- per-class verdict table -----------------------------------------
    per_class = {}
    for d in DEFECT_CLASSES:
        base_n = b_hist.get(d, 0)
        new_n = n_hist.get(d, 0)
        elig = eligible.get(d, 0)
        if new_n > 0:
            verdict = "STILL-DEFECTIVE"
        elif base_n > 0 and elig > 0:
            verdict = "CONFIRMED-REPAIRED"
        elif base_n > 0:
            verdict = "INCONCLUSIVE_NO_CLASS_ROW"
        else:
            verdict = "NO_BASELINE_DEFECT"
        per_class[d] = {"baseline_count": base_n, "new_head_count": new_n,
                        "new_head_class_eligible_rows": elig, "verdict": verdict}

    any_still = any(v["verdict"] == "STILL-DEFECTIVE" for v in per_class.values())
    any_inconclusive = any(v["verdict"] == "INCONCLUSIVE_NO_CLASS_ROW"
                           for v in per_class.values())
    if any_still or any_inconclusive:
        verdict = "REPAIR_NOT_CONFIRMED"
        exit_code = 1
    else:
        verdict = "REPAIR_CONFIRMED"
        exit_code = 0

    # yield context (requirement 26: numbers published together)
    yield_context = {
        "baseline": {
            "n_bundles": len(baseline_bundles),
            "n_verified_rows": b_verified,
            "n_verified_rows_with_defects": b_defective,
            "verified_rows_per_bundle": round(b_verified / len(baseline_bundles), 4),
        },
        "new_head": {
            "n_bundles": len(new_bundles),
            "n_verified_rows": n_verified,
            "n_verified_rows_with_defects": n_defective,
            "verified_rows_per_bundle": round(n_verified / len(new_bundles), 4),
            "note": ("the re-measure population is the NEW head's own shipped "
                     "slice artifacts; a lower verified-row count reflects the "
                     "shipped pipeline's emission behaviour on this slice "
                     "generation and is NOT an abstention measurement by this "
                     "instrument (abstention accounting lives in the product "
                     "harness and is measured in the sibling item-(3) "
                     "reconciliation artifact)"),
        },
    }

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction_version": 66,
        "ordered_work_item": "v66 evaluation ordered work item (4) CONDITIONAL RE-MEASURE",
        "trigger": {
            "product_accept_commit": NEW_HEAD,
            "product_accept_cycle": NEW_HEAD_ACCEPT,
            "trigger_rule": ("v66 item (4): execute ONLY IF Core Product lands the "
                             "content-quality filter in its P0; re-run the frozen "
                             "item-(2) probe protocol on the NEW product head and "
                             "publish BEFORE/AFTER histograms with no bar movement"),
        },
        "frozen_protocol": {
            "instrument": "evaluation/counter_evidence_quality_benchmark.py",
            "instrument_sha256_expected": FROZEN_INSTRUMENT_SHA_EXPECTED,
            "instrument_sha256_actual": _sha256_file(FROZEN_INSTRUMENT),
            "hypothesis_sha256": hyp_sha,
            "predicates": {
                "LETTERHEAD_ZONE_OFFSET_MAX": LETTERHEAD_ZONE_OFFSET_MAX,
                "MARKUP_TOKENS": MARKUP_TOKENS,
                "MIN_MARKER_HITS": MIN_MARKER_HITS,
                "LANGUAGE_MARKER_SETS": LANGUAGE_MARKER_SETS,
            },
            "frozen_schemas_reference": FROZEN_SCHEMA,
            "no_predicate_edit": True,
        },
        "mount": str(MOUNT),
        "mount_head": mount_head,
        "expected_mount_head": NEW_HEAD,
        "baseline_population": {
            "families": {k: v for k, v in PROBE_BUNDLES.items()},
            "prior_cycle_control": PRIOR_CYCLE_CONTROL,
            "stability_vs_accepted_baseline_of_record": stability,
            "bundles": baseline_bundles,
        },
        "new_head_population": {
            "families": NEW_HEAD_BUNDLES,
            "bundles": new_bundles,
            "bundle_sha256": {
                rel: (_sha256_file(MOUNT / rel) if (MOUNT / rel).is_file() else None)
                for rels in NEW_HEAD_BUNDLES.values() for rel in rels
            },
        },
        "before_histogram": b_hist,
        "after_histogram": n_hist,
        "before_defective_decision_ids": sorted(b_ids),
        "after_defective_decision_ids": sorted(n_ids),
        "per_class_verdicts": per_class,
        "yield_context": yield_context,
        "controls": controls,
        "verdict": verdict,
        "exit_code": exit_code,
        "claim_ceiling": (
            "Re-measurement of the FROZEN D2/D3/D4 content-quality predicates on "
            "the new head's own shipped slice artifacts versus the accepted "
            "baseline population; scores no frozen bar, edits no rubric, "
            "classifies no decision as supporting/contrary under the frozen "
            "rubric and changes no serve verdict. Both DO-NOT-SERVE orders "
            "stand; admission stays fail-closed; the comparative "
            "map-versus-ranked-list half is NOT scored while emission on a "
            "serviceable packet stays zero."),
        "no_obsolete_174k_benchmark_rerun": True,
        "elapsed_s": round(time.time() - t0, 3),
        "numeric_environment": numeric_environment(),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        f"# Counter-Evidence Content-Quality RE-MEASURE (item 4) — run {run_id}",
        "",
        f"- Trigger: product accept `{NEW_HEAD[:12]}` (cycle {NEW_HEAD_ACCEPT}) landed the P0 filter",
        f"- Frozen protocol instrument sha256: `{record['frozen_protocol']['instrument_sha256_actual'][:16]}...` (expected match: {record['frozen_protocol']['instrument_sha256_actual'] == FROZEN_INSTRUMENT_SHA_EXPECTED})",
        f"- BEFORE histogram (accepted baseline population re-probe): {b_hist} ({b_defective}/{b_verified} defective)",
        f"- AFTER histogram (new head shipped slice): {n_hist} ({n_defective}/{n_verified} defective)",
        f"- Verdict: **{verdict}** (exit {exit_code})",
        "",
        "## Per-class verdicts",
        "",
        "| class | baseline | new head | eligible rows (new) | verdict |",
        "|---|---|---|---|---|",
    ]
    for d, v in per_class.items():
        lines.append(f"| {d} | {v['baseline_count']} | {v['new_head_count']} | "
                     f"{v['new_head_class_eligible_rows']} | {v['verdict']} |")
    lines += ["", "## Controls", ""]
    for c in controls.values():
        lines.append(f"- `{c['control']}`: {'PASS' if c['passed'] else 'FAIL'}")
    if stability.get("compared"):
        lines += ["", "## Baseline stability",
                  "",
                  f"- normalized-identical to accepted baseline of record "
                  f"{stability['baseline_of_record_run']}: "
                  f"**{stability['normalized_identical']}**"]
    lines += ["", "## Reason", "",
              (f"Per-class: " +
               "; ".join(f"{d} -> {v['verdict']}" for d, v in per_class.items()) +
               f". Overall {verdict}."),
              "", "## Claim ceiling", "", record["claim_ceiling"]]
    (report_dir / f"COUNTER_EVIDENCE_QUALITY_REMEASURE_{run_id}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    return exit_code, record


DEFAULT_OUT_DIR = _REPO_ROOT / "results/evaluation/counter_evidence_quality_remeasure"
DEFAULT_REPORT_DIR = _REPO_ROOT / "reports/evaluation"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--report-dir", default=None)
    args = ap.parse_args(argv)
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR
    code, record = run(run_id, out_dir, report_dir)
    print(json.dumps({"verdict": record.get("verdict"), "exit_code": code,
                      "per_class": record.get("per_class_verdicts"),
                      "before": record.get("before_histogram"),
                      "after": record.get("after_histogram")}, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
