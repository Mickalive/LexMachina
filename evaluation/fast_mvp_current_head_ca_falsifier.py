#!/usr/bin/env python3
"""FAST-MVP current-head served-slice retrieval/counter-authority falsifier.

NEW BYTES, NEW PRE-REGISTERED INSTRUMENT
----------------------------------------
This is NOT the benchmark of record and it does not re-run, replace or move it.
The benchmark of record (PRODUCT_FALSIFIED on packet-of-record 39319405429) stays
exactly as accepted. This instrument scores the NEWEST committed offline/server
slice bundles at the CURRENT accepted product head, i.e. bytes that did not
exist when the packet-of-record benchmark was frozen. v67 evaluation ordered-work
item (3) explicitly permits a NEW pre-registered falsification on NEW bytes with
its own freeze-first record; this file is the executable half of that record.

WHAT IT MEASURES
----------------
The smallest executable question the FAST-MVP directive asks: on the product's
own emitted bundles, does the frozen counter-authority SURFACE gate pass only
because a scored row carries a non-empty evidence string, while that string is a
frozen D1-D4 content defect (letterhead header / markup residue / language
marker mismatch / empty) rather than counter reasoning?

REUSE-FIRST (no re-implementation)
----------------------------------
* ``evaluation.mapping_free_recall_falsifier.source_validity``
* ``evaluation.mapping_free_recall_falsifier.duplicate_suppression``
* ``evaluation.mapping_free_recall_falsifier.counter_authority_surface``
* ``evaluation.mapping_free_recall_falsifier.language_robustness``
* ``evaluation.counter_evidence_quality_benchmark.classify_verified_row``
* the frozen ``scored_statuses`` vocabulary from RULES_LABEL.json

No threshold, predicate, rubric, tokeniser, stoplist or verdict contract is
defined here. The instrument adds only population selection, controls, an
aggregation table and a new capability verdict whose rule is frozen in the
hypothesis file BEFORE execution.

Exit codes:
  0  SOUND_COUNTER_ROW_PRESENT / PARTIAL_OR_UNEXPECTED
  1  CAPABILITY_FALSIFIED_CONTENT_DEFECTIVE
  2  NOT_MEASURED_VACUOUS (pin drift, control failure, or no scored row)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from evaluation import counter_evidence_quality_benchmark as CQ  # noqa: E402
from evaluation import mapping_free_recall_falsifier as MF  # noqa: E402

SCHEMA = "lex-evaluation-fast-mvp-current-head-ca-falsifier/1"
HYPOTHESIS_RELPATH = (
    "evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124_HYPOTHESIS_V1.json")
FREEZE_RELPATH = (
    "evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124_FREEZE_V1.json")
RULES_LABEL_RELPATH = "evaluation/frozen_bars/RULES_LABEL.json"
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/fast_mvp_current_head_ca_falsifier"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports/evaluation"

EXIT_NOT_VACUOUS = 0
EXIT_FALSIFIED = 1
EXIT_VACUOUS = 2


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mount_head(mount: Path) -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        return p.stdout.strip() or None
    except Exception:
        return None


def numeric_environment() -> dict:
    env = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = "NOT_IMPORTABLE"
    env["thread_env"] = {k: os.environ.get(k) for k in
                         ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}
    return env


def load_frozen() -> tuple[dict, dict, list[str]]:
    hyp = json.loads((REPO_ROOT / HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    freeze = json.loads((REPO_ROOT / FREEZE_RELPATH).read_text(encoding="utf-8"))
    rules = json.loads((REPO_ROOT / RULES_LABEL_RELPATH).read_text(encoding="utf-8"))
    scored = list(((rules.get("rubric") or {}).get("scored_statuses")) or [])
    return hyp, freeze, scored


def verify_pins(hyp: dict, freeze: dict) -> dict:
    """Re-hash every frozen input and bundle. Any mismatch invalidates the run."""
    rows = []
    ok = True

    def check(label: str, path: Path, expected: str) -> None:
        nonlocal ok
        actual = sha256_file(path) if path.is_file() else None
        match = actual == expected
        ok = ok and match
        rows.append({"input": label, "path": str(path), "expected": expected,
                     "actual": actual, "match": match})

    for rel, expected in (hyp.get("frozen_inputs_REPORTED_ONLY") or {}).items():
        check(f"repo:{rel}", REPO_ROOT / rel, expected)

    pop = hyp["population_FROZEN"]
    mount = Path(pop["product_mount"])
    head = mount_head(mount)
    head_ok = head == pop["expected_product_mount_head"]
    ok = ok and head_ok
    rows.append({"input": "mount_head", "path": str(mount),
                 "expected": pop["expected_product_mount_head"],
                 "actual": head, "match": head_ok})

    for b in pop["bundles"]:
        check(f"bundle:{b['label']}", mount / b["path"], b["sha256"])

    return {"all_match": ok, "checks": rows}


def controls(scored: list[str], classification_sha: str) -> dict:
    """Pre-registered C1-C4 controls. Synthetic control rows are NEVER product data."""
    c1_expected = "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"
    c1 = {"control": "C1_frozen_predicate_instrument_sha",
          "holds": classification_sha == c1_expected,
          "measured": {"expected": c1_expected, "actual": classification_sha}}

    clean_evidence = (
        "Considérant que la résiliation du bail et le recours du locataire "
        "supposent le respect de l'art. 257d CO ; la jurisprudence limite "
        "néanmoins cette règle lorsque le bailleur accepte un paiement tardif.")
    clean_row = {
        "decision_id": "SYNTHETIC_CONTROL_CLEAN",
        "counter_evidence": clean_evidence,
        "full_text": ("x" * 1000) + clean_evidence,
        "language": "fr",
        "counter_evidence_verified": True,
    }
    clean = CQ.classify_verified_row(clean_row)
    c2 = {"control": "C2_clean_synthetic_row_must_pass",
          "holds": clean["class"] == "COUNTER_REASONING" and not clean["defects"],
          "measured": {"class": clean["class"], "defects": clean["defects"],
                       "grounded_in": clean["detail"].get("grounded_in"),
                       "first_offset": clean["detail"].get("first_offset")}}

    blank = CQ.classify_verified_row({
        "decision_id": "SYNTHETIC_CONTROL_BLANK", "counter_evidence": "",
        "language": "de", "counter_evidence_verified": True})
    c3 = {"control": "C3_blanked_synthetic_row_must_fail",
          "holds": "D1_empty_evidence" in blank["defects"],
          "measured": {"class": blank["class"], "defects": blank["defects"]}}

    empty_surface = MF.counter_authority_surface({"decisions": []}, scored)
    c4 = {"control": "C4_empty_bundle_must_have_zero_issued",
          "holds": empty_surface["n_issued"] == 0,
          "measured": empty_surface}

    battery = [c1, c2, c3, c4]
    return {"all_hold": all(c["holds"] for c in battery), "battery": battery}


def score_bundle(mount: Path, entry: dict, scored: list[str]) -> dict:
    path = mount / entry["path"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    decisions = doc.get("decisions") or []

    surface = MF.counter_authority_surface(doc, scored)
    src = MF.source_validity(doc)
    dup = MF.duplicate_suppression(doc)
    lang = MF.language_robustness(doc)

    scored_rows = [
        r for r in decisions
        if str(r.get("counter_status") or "").strip().lower()
        in {str(s).strip().lower() for s in scored}
    ]
    verified_scored = [r for r in scored_rows if r.get("counter_evidence_verified") is True]
    classified = []
    for r in verified_scored:
        cl = CQ.classify_verified_row(r)
        classified.append({
            "decision_id": r.get("decision_id"),
            "counter_status": r.get("counter_status"),
            "counter_uncertainty": r.get("counter_uncertainty"),
            "language": r.get("language"),
            "class": cl["class"],
            "defects": cl["defects"],
            "evidence_head": cl["evidence_head"],
            "grounded_in": cl["detail"].get("grounded_in"),
            "first_offset": cl["detail"].get("first_offset"),
        })

    n_verified = len(classified)
    n_defective = sum(1 for c in classified if c["defects"])
    n_sound = sum(1 for c in classified if not c["defects"])

    return {
        "label": entry["label"],
        "path": entry["path"],
        "sha256": entry["sha256"],
        "family": entry["family"],
        "enriched": entry["enriched"],
        "role": entry["role"],
        "n_decisions": len(decisions),
        "n_scored_rows": len(scored_rows),
        "n_counter_evidence_verified_scored_rows": n_verified,
        "n_defective_verified_scored_rows": n_defective,
        "n_sound_verified_scored_rows": n_sound,
        "frozen_surface_gate": {
            "n_issued": surface["n_issued"],
            "n_with_empty_evidence": surface["n_with_empty_evidence"],
            "statuses_seen": surface["statuses_seen"],
            "would_pass": surface["n_issued"] >= 1 and surface["n_with_empty_evidence"] == 0,
        },
        "source_validity": src,
        "duplicate_suppression": dup,
        "language_robustness": lang,
        "verified_scored_rows": classified,
    }


def evaluate(run_id: str) -> dict:
    hyp, freeze, scored = load_frozen()
    hpath = REPO_ROOT / HYPOTHESIS_RELPATH
    fpath = REPO_ROOT / FREEZE_RELPATH
    hyp_sha = sha256_file(hpath)
    freeze_sha = sha256_file(fpath)
    mount = Path(hyp["population_FROZEN"]["product_mount"])
    classification_sha = CQ.__file__ and sha256_file(Path(CQ.__file__))
    relation_sha = sha256_file(Path(MF.__file__))

    consistency = {
        "hypothesis_sha_matches_freeze_record": (
            hyp_sha == freeze.get("hypothesis_sha256_at_freeze")),
        "frozen_predicate_sha_matches_hypothesis": (
            classification_sha == hyp["frozen_inputs_REPORTED_ONLY"][
                "evaluation/counter_evidence_quality_benchmark.py"]),
        "frozen_engine_sha_matches_hypothesis": (
            relation_sha == hyp["frozen_inputs_REPORTED_ONLY"][
                "evaluation/mapping_free_recall_falsifier.py"]),
    }

    pins_before = verify_pins(hyp, freeze)
    ctrl = controls(scored, classification_sha)

    bundles = [score_bundle(mount, b, scored) for b in hyp["population_FROZEN"]["bundles"]]
    pins_after = verify_pins(hyp, freeze)

    enriched = [b for b in bundles if b["enriched"]]
    not_enriched = [b for b in bundles if not b["enriched"]]

    h1_holds = all(
        b["frozen_surface_gate"]["n_issued"] == 1
        and b["frozen_surface_gate"]["n_with_empty_evidence"] == 0
        and b["source_validity"]["n_rows_missing_id_or_url"] == 0
        and b["duplicate_suppression"]["duplicates"] == 0
        for b in enriched
    )
    h2_holds = all(
        b["n_counter_evidence_verified_scored_rows"] >= 1
        and b["n_defective_verified_scored_rows"]
        == b["n_counter_evidence_verified_scored_rows"]
        for b in enriched
    )
    h3_holds = all(b["frozen_surface_gate"]["n_issued"] == 0 for b in not_enriched)

    n_with_scored = sum(1 for b in enriched
                        if b["n_counter_evidence_verified_scored_rows"] >= 1)
    n_with_sound = sum(1 for b in enriched if b["n_sound_verified_scored_rows"] >= 1)

    vacuous_reasons = []
    if not (consistency["hypothesis_sha_matches_freeze_record"]
            and consistency["frozen_predicate_sha_matches_hypothesis"]
            and consistency["frozen_engine_sha_matches_hypothesis"]):
        vacuous_reasons.append("freeze/predicate digest inconsistency")
    if not pins_before["all_match"]:
        vacuous_reasons.append("input pin drift before execution")
    if not pins_after["all_match"]:
        vacuous_reasons.append("input pin drift after execution")
    if not ctrl["all_hold"]:
        vacuous_reasons.append("control failure")
    if not h3_holds:
        vacuous_reasons.append("NOT-ENRICHED control has n_issued != 0")
    if n_with_scored == 0:
        vacuous_reasons.append("no enriched bundle carries a verified scored counter row")

    if vacuous_reasons:
        verdict, code = "NOT_MEASURED_VACUOUS", EXIT_VACUOUS
    elif h1_holds and h2_holds:
        verdict, code = "CAPABILITY_FALSIFIED_CONTENT_DEFECTIVE", EXIT_FALSIFIED
    elif n_with_sound >= 1:
        verdict, code = "SOUND_COUNTER_ROW_PRESENT", EXIT_NOT_VACUOUS
    else:
        verdict, code = "PARTIAL_OR_UNEXPECTED", EXIT_NOT_VACUOUS

    return {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": hyp["direction_version"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry_point": "python -m evaluation.fast_mvp_current_head_ca_falsifier",
        "verdict": verdict,
        "exit_code": code,
        "falsification_proven": code == EXIT_FALSIFIED,
        "vacuous_reasons": vacuous_reasons,
        "hypothesis": {"path": HYPOTHESIS_RELPATH, "sha256": hyp_sha},
        "freeze_record": {"path": FREEZE_RELPATH, "sha256": freeze_sha},
        "consistency": consistency,
        "product_mount": str(mount),
        "product_mount_head": mount_head(mount),
        "product_accepted_cycle": hyp["population_FROZEN"]["expected_product_accepted_cycle"],
        "scored_statuses_from_frozen_rubric": scored,
        "frozen_predicates_reused": {
            "counter_evidence_quality_benchmark.py": classification_sha,
            "mapping_free_recall_falsifier.py": relation_sha,
        },
        "hypothesis_checks": {
            "H1_surface_gates_and_source_validity_on_enriched": h1_holds,
            "H2_all_verified_scored_rows_content_defective": h2_holds,
            "H3_not_enriched_control_zero_issued": h3_holds,
            "H4_controls_all_hold": ctrl["all_hold"],
            "H5_pins_identical_before_after": (
                pins_before["all_match"] and pins_after["all_match"]),
        },
        "aggregate": {
            "n_bundles": len(bundles),
            "n_enriched": len(enriched),
            "n_enriched_with_verified_scored_row": n_with_scored,
            "n_enriched_with_sound_counter_row": n_with_sound,
            "n_verified_scored_rows_total": sum(
                b["n_counter_evidence_verified_scored_rows"] for b in enriched),
            "n_defective_verified_scored_rows_total": sum(
                b["n_defective_verified_scored_rows"] for b in enriched),
            "defect_histogram": _histogram(bundles),
            "distinct_defective_decision_ids": sorted({
                r["decision_id"] for b in bundles for r in b["verified_scored_rows"]
                if r["defects"]}),
        },
        "controls": ctrl,
        "pins_before_execution": pins_before,
        "pins_after_execution": pins_after,
        "bundles": bundles,
        "numeric_environment": numeric_environment(),
        "no_new_thresholds": True,
        "no_174k_benchmark_rerun": True,
        "benchmark_of_record_untouched": True,
        "v67_item_2_status": "NOT_YET_DISCRIMINATING (unchanged)",
        "claim_ceiling": hyp["claim_ceiling"],
        "packet_admitted": False,
        "machine_gate_ready": False,
        "human_gate_ready": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
    }


def _histogram(bundles: list[dict]) -> dict:
    out: dict[str, int] = {}
    for b in bundles:
        for r in b["verified_scored_rows"]:
            for d in r["defects"]:
                out[d] = out.get(d, 0) + 1
    return dict(sorted(out.items()))


def write_report(rec: dict, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    p = report_dir / f"FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_{rec['run_id']}.md"
    lines = [
        f"# FAST-MVP current-head counter-authority falsifier — run {rec['run_id']}",
        "",
        f"- Verdict: **{rec['verdict']}** (exit {rec['exit_code']})",
        f"- Falsification proven: **{rec['falsification_proven']}**",
        f"- Direction: v{rec['direction_version']}",
        f"- Product mount head: `{rec['product_mount_head']}` (cycle {rec['product_accepted_cycle']})",
        f"- New bytes scored: {rec['aggregate']['n_bundles']} bundles "
        f"({rec['aggregate']['n_enriched']} enriched, "
        f"{rec['aggregate']['n_bundles'] - rec['aggregate']['n_enriched']} not-enriched control)",
        "- This is NOT the benchmark of record and does NOT re-run packet-of-record 39319405429.",
        "",
        "## Hypothesis checks",
        "",
    ]
    for k, v in rec["hypothesis_checks"].items():
        lines.append(f"- {k}: **{v}**")
    lines += ["", "## Controls", ""]
    for c in rec["controls"]["battery"]:
        lines.append(f"- {c['control']}: holds={c['holds']}")
    lines += ["", "## Per-bundle result", "",
              "| bundle | family | enriched | n_decisions | surface n_issued | verified scored | defective | sound | log |",
              "|---|---|---|---|---|---|---|---|---|"]
    for b in rec["bundles"]:
        g = b["frozen_surface_gate"]
        lines.append(
            f"| {b['label']} | {b['family']} | {b['enriched']} | {b['n_decisions']} | "
            f"{g['n_issued']} | {b['n_counter_evidence_verified_scored_rows']} | "
            f"{b['n_defective_verified_scored_rows']} | {b['n_sound_verified_scored_rows']} | "
            f"{b['language_robustness']['language_distribution']} |")
    lines += ["", "## Verified scored rows (frozen D1-D4 predicates)", ""]
    for b in rec["bundles"]:
        for r in b["verified_scored_rows"]:
            lines.append(
                f"- `{b['label']}` / `{r['decision_id']}` / {r['counter_status']}: "
                f"**{r['class']}** (defects={r['defects']}, grounded_in={r['grounded_in']}, "
                f"offset={r['first_offset']}); head={r['evidence_head'][:90]!r}")
    lines += [
        "",
        "## Aggregate",
        "",
        f"- Verified scored rows (enriched): {rec['aggregate']['n_verified_scored_rows_total']}",
        f"- Defective: {rec['aggregate']['n_defective_verified_scored_rows_total']}",
        f"- Defect histogram: {rec['aggregate']['defect_histogram']}",
        f"- Distinct defective decision ids: {rec['aggregate']['distinct_defective_decision_ids']}",
        f"- Enriched bundles with a sound counter row: {rec['aggregate']['n_enriched_with_sound_counter_row']}",
        "",
        "## Claim ceiling",
        "",
        rec["claim_ceiling"],
        "",
        "## Pin discipline",
        "",
        f"- Pins before: all_match={rec['pins_before_execution']['all_match']}",
        f"- Pins after: all_match={rec['pins_after_execution']['all_match']}",
        f"- Numeric environment: {json.dumps(rec['numeric_environment'], sort_keys=True)}",
        "",
        f"- v67 item (2): **{rec['v67_item_2_status']}**",
        "- Posture: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false, "
        "ready_for_owner_session=false, owner_decision_required=false.",
        "",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--report-dir", default=None)
    args = ap.parse_args(argv)
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR

    rec = evaluate(run_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{run_id}.json"
    out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_report(rec, report_dir)

    print(json.dumps({
        "verdict": rec["verdict"],
        "exit_code": rec["exit_code"],
        "falsification_proven": rec["falsification_proven"],
        "n_bundles": rec["aggregate"]["n_bundles"],
        "n_enriched_with_verified_scored_row": rec["aggregate"]["n_enriched_with_verified_scored_row"],
        "n_enriched_with_sound_counter_row": rec["aggregate"]["n_enriched_with_sound_counter_row"],
        "defect_histogram": rec["aggregate"]["defect_histogram"],
        "distinct_defective_decision_ids": rec["aggregate"]["distinct_defective_decision_ids"],
        "controls_all_hold": rec["controls"]["all_hold"],
        "pins_all_match": (rec["pins_before_execution"]["all_match"]
                           and rec["pins_after_execution"]["all_match"]),
        "record": str(out),
        "report": str(report),
    }, indent=1))
    return rec["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
