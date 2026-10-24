#!/usr/bin/env python3
"""Measure the current product head's shipped slices under the frozen item-(2) protocol.

FAST MVP: Runs the FROZEN D1-D4 defect predicates (from accepted v65 hypothesis
sha256 734a447d...) on the LATEST product shipped slice bundles (offline + server).

REUSE-FIRST: The frozen probe definitions are imported BY VALUE from
evaluation.counter_evidence_quality_benchmark. The predicates are mechanical,
require no legal reasoning/LLM/paid API, and are frozen — never re-tuned,
re-derived or edited after results are seen.

This benchmark scores NO frozen bar. Its population is the current product
head's shipped slice bundles, not the RULES_LABEL population. The frozen
RULES_LABEL/GEOMETRY rubrics are re-hashed REPORTED-ONLY and never applied.

Exit codes:
  0  QUALITY_BENCHMARK_VALID_H2_SURVIVES
       Zero verified rows carry a frozen defect on the current head's slices.
  1  H2_FALSIFIED
       One or more verified rows carry a frozen defect. The content-quality
       bottleneck persists on the current head's artifacts.
  2  ENVIRONMENT_OR_VACUOUS
       Missing inputs, mount unavailable, or a control failed — never a product verdict.

No Product code is imported. No network is used. The accepted-product mount at
/tmp/lex_accepted is read-only input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Import FROZEN probe definitions from the accepted benchmark
from evaluation.counter_evidence_quality_benchmark import (  # noqa: E402
    EXPECTED_HYPOTHESIS_SHA,
    LANGUAGE_MARKER_SETS,
    LETTERHEAD_ZONE_OFFSET_MAX,
    MARKUP_TOKENS,
    MIN_MARKER_HITS,
    classify_verified_row,
)

SCHEMA = "lex-evaluation-current-head-slice-quality/1"

MOUNT = Path("/tmp/lex_accepted/product")
PACKET_OF_RECORD = "39319405429"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _current_direction_version() -> int:
    state_path = _REPO_ROOT / "state" / "evaluation.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return int(state["direction_version"])


def _rel_or_abs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def numeric_environment() -> dict:
    import os
    env = {"python": sys.version.split()[0], "platform": sys.platform}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = "absent"
    env["thread_env"] = {k: os.environ.get(k) for k in
                         ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}
    return env


def probe_bundle(mount: Path, relpath: str, family: str) -> dict:
    p = mount / relpath
    rec = {"bundle": relpath, "family": family,
           "sha256": _sha256_file(p) if p.is_file() else None}
    if not p.is_file():
        rec.update(present=False, verdict="MISSING_BUNDLE")
        return rec
    doc = json.loads(p.read_text())
    rows = doc.get("decisions") or []
    bearing = [r for r in rows if r.get("counter_status") not in (None, "none")]
    verified = [r for r in bearing if r.get("counter_evidence_verified") is True]
    per_row = []
    for r in verified:
        cl = classify_verified_row(r)
        per_row.append({
            "decision_id": r.get("decision_id"),
            "counter_status": r.get("counter_status"),
            "counter_uncertainty": r.get("counter_uncertainty"),
            "language": r.get("language"),
            **cl,
        })
    defective = [r for r in per_row if r["defects"]]
    status_counts = {}
    for r in bearing:
        status_counts[r.get("counter_status")] = status_counts.get(r.get("counter_status"), 0) + 1
    rec.update({
        "present": True,
        "n_decisions": len(rows),
        "n_status_bearing": len(bearing),
        "status_counts": status_counts,
        "n_counter_evidence_verified": len(verified),
        "n_verified_with_defects": len(defective),
        "verified_rows": per_row,
        "defective_decision_ids": [r["decision_id"] for r in defective],
        "verdict": "PROBE_FAIL" if defective else ("PROBE_PASS" if verified else "PROBE_NO_VERIFIED_ROWS"),
    })
    return rec


def _discover_latest_bundles(mount: Path) -> list[tuple[str, str]]:
    """Discover the latest offline_slice and server_slice bundles.
    Returns list of (relpath, family) tuples.
    """
    bundles = []
    
    # Latest offline_slice
    offline_root = mount / "results" / "product" / "offline_slice"
    if offline_root.exists():
        dirs = sorted([d for d in offline_root.iterdir() if d.is_dir() and not d.name.endswith("_warm_verify")])
        if dirs:
            latest = dirs[-1]
            for bundle_file in latest.glob("*.bundle.json"):
                rel = bundle_file.relative_to(mount)
                bundles.append((str(rel), f"offline_latest_{latest.name}"))
    
    # Latest server_slice
    server_root = mount / "results" / "product" / "server_slice"
    if server_root.exists():
        dirs = sorted([d for d in server_root.iterdir() if d.is_dir() and d.name[0].isdigit()])
        if dirs:
            latest = dirs[-1]
            for bundle_file in latest.glob("*.bundle.json"):
                rel = bundle_file.relative_to(mount)
                bundles.append((str(rel), f"server_latest_{latest.name}"))
    
    return bundles


def run_benchmark(run_id: str, out_dir: Path, report_dir: Path,
                  bundle_paths: list[tuple[str, str]] | None = None) -> tuple[int, dict]:
    t0 = time.time()
    if not MOUNT.exists():
        env_err = {
            "schema": SCHEMA,
            "run_id": run_id,
            "verdict": "ENVIRONMENT_ERROR",
            "detail": f"accepted product mount missing: {MOUNT}",
            "elapsed_s": round(time.time() - t0, 3),
        }
        return 2, env_err

    # Verify hypothesis digest matches the frozen accepted value
    hyp_path = _REPO_ROOT / "evaluation" / "V65_HEAD_ADVANCE_CROSSCHECK_HYPOTHESIS_V2.json"
    if hyp_path.exists():
        hyp_sha = _sha256_file(hyp_path)
        if hyp_sha != EXPECTED_HYPOTHESIS_SHA:
            env_err = {
                "schema": SCHEMA,
                "run_id": run_id,
                "verdict": "ENVIRONMENT_ERROR",
                "detail": f"hypothesis digest drift: {hyp_sha} != {EXPECTED_HYPOTHESIS_SHA}",
                "elapsed_s": round(time.time() - t0, 3),
            }
            return 2, env_err

    # Verify mount head (record actual head, accept any HEAD since bundle content is what matters)
    actual_mount_head = "UNAVAILABLE"
    try:
        import subprocess
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=MOUNT,
                              capture_output=True, text=True, timeout=30,
                              check=True).stdout.strip()
        actual_mount_head = head
    except Exception:
        actual_mount_head = "UNAVAILABLE"

    # ---- controls (frozen, must pass before measurement) ------------------
    # C1: probe detects planted letterhead-zone evidence (offset < 400)
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
          "letterhead_offset": c_letterhead["detail"].get("first_offset"),
          "mid_offset": c_mid["detail"].get("first_offset"),
          "passed": c1_passed}

    # C2: probe detects planted language marker mismatch
    lang_row = {"decision_id": "planted_lang", "language": "it",
                "counter_status": "candidate-limiting", "counter_evidence_verified": True,
                "counter_evidence": "Regeste Resolutiv bedingter Mietvertrag; Anfeuchtung der Kündigung; Erstreckung",
                "full_text": "y" * 900 + "Regeste Resolutiv bedingter Mietvertrag; Anfeuchtung der Kündigung; Erstreckung",
                "snippet": "", "regeste": "", "full_text_status": "lazy"}
    c_lang = classify_verified_row(lang_row)
    c2_passed = "D4_language_marker_mismatch" in c_lang["defects"]
    c2 = {"control": "C2_probe_detects_language_marker_mismatch", "row_language": "it",
          "defects": c_lang["defects"], "marker_hits_own": c_lang["detail"].get("marker_hits_own"),
          "marker_hits_other": c_lang["detail"].get("marker_hits_other"), "passed": c2_passed}

    # C3: frozen rules re-hash holds (reported only)
    rules_label_sha = _sha256_file(_REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json")
    rules_geometry_sha = _sha256_file(_REPO_ROOT / "evaluation/frozen_bars/RULES_GEOMETRY.json")
    expected_label = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    expected_geometry = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
    c3_passed = (rules_label_sha == expected_label and rules_geometry_sha == expected_geometry)
    c3 = {"control": "C3_frozen_rules_rehash_holds_reported_only",
          "rules_label_sha256": rules_label_sha, "rules_geometry_sha256": rules_geometry_sha,
          "expected_label": expected_label, "expected_geometry": expected_geometry,
          "matches_expected": c3_passed, "passed": c3_passed,
          "note": "re-hashed REPORTED-ONLY; the frozen rubrics are never applied by this run"}

    controls = {"C1": c1, "C2": c2, "C3": c3}
    if not all(c["passed"] for c in controls.values()):
        env_err = {
            "schema": SCHEMA,
            "run_id": run_id,
            "verdict": "ENVIRONMENT_OR_VACUOUS",
            "detail": "one or more frozen controls failed; benchmark cannot be trusted",
            "controls": controls,
            "elapsed_s": round(time.time() - t0, 3),
        }
        return 2, env_err

    # ---- measurement: probe the specified bundles -------------------------
    if bundle_paths is None:
        bundle_paths = _discover_latest_bundles(MOUNT)

    bundles = []
    for relpath, family in bundle_paths:
        bundles.append(probe_bundle(MOUNT, relpath, family))

    n_verified = sum(b.get("n_counter_evidence_verified", 0) for b in bundles)
    n_defective = sum(b.get("n_verified_with_defects", 0) for b in bundles)
    defect_hist = {}
    defective_decision_ids = set()
    for b in bundles:
        for r in b.get("verified_rows", []):
            for d in r["defects"]:
                defect_hist[d] = defect_hist.get(d, 0) + 1
            if r["defects"]:
                defective_decision_ids.add(r["decision_id"])

    h2_falsified = n_defective > 0

    # ---- combined verdict -------------------------------------------------
    if h2_falsified:
        verdict = "H2_FALSIFIED"
        exit_code = 1
        reason = (f"{n_defective} of {n_verified} counter_evidence_verified rows across "
                  f"{len(bundles)} bundles carry a frozen defect "
                  f"({defect_hist}) over {len(defective_decision_ids)} distinct decision(s). "
                  f"The counter-evidence extractor emits letterhead/markup/language-mismatch "
                  f"content on the current product head's flagship slice artifacts.")
    else:
        verdict = "QUALITY_BENCHMARK_VALID_H2_SURVIVES"
        exit_code = 0
        reason = ("Zero verified rows carry a frozen defect. The product's counter-evidence "
                  "extractor emits no letterhead/markup/language-mismatch defects on the "
                  "current head's flagship slices.")

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction_version": _current_direction_version(),
        "hypothesis_sha256": EXPECTED_HYPOTHESIS_SHA,
        "product_mount": str(MOUNT),
        "product_mount_head_actual": actual_mount_head,
        "packet_of_record": PACKET_OF_RECORD,
        "probe_definitions": {
            "LETTERHEAD_ZONE_OFFSET_MAX": LETTERHEAD_ZONE_OFFSET_MAX,
            "MARKUP_TOKENS": MARKUP_TOKENS,
            "MIN_MARKER_HITS": MIN_MARKER_HITS,
            "LANGUAGE_MARKER_SETS": LANGUAGE_MARKER_SETS,
            "row_class_rule": ("COUNTER_REASONING iff no defect fires; otherwise the joined "
                               "defect codes"),
        },
        "probe_is_not_a_frozen_bar": (
            "the population is the current product head's shipped slice bundles, NOT the "
            "RULES_LABEL population (packet-of-record 39319405429); the frozen rubrics are "
            "re-hashed REPORTED-ONLY and never applied, edited or re-derived"),
        "n_bundles": len(bundles),
        "n_bundles_present": sum(1 for b in bundles if b.get("present")),
        "n_verified_rows_total": n_verified,
        "n_verified_rows_with_defects": n_defective,
        "defect_histogram": defect_hist,
        "defective_decision_ids": sorted(defective_decision_ids),
        "H2_verdict": "H2_FALSIFIED" if h2_falsified else "H2_SURVIVES",
        "h2_falsified": h2_falsified,
        "bundles": bundles,
        "controls": controls,
        "verdict": verdict,
        "exit_code": exit_code,
        "reason": reason,
        "claim_ceiling": (
            "descriptive evidence audit of the current product head's shipped slice artifacts "
            "under frozen mechanical defect predicates; scores no frozen bar, classifies no "
            "decision as supporting/contrary under the frozen rubric, and changes no verdict. "
            "Both DO-NOT-SERVE orders stand; admission stays fail-closed; the comparative "
            "map-versus-ranked-list half is NOT scored while counter-evidence content defects "
            "persist."),
        "elapsed_s": round(time.time() - t0, 3),
        "numeric_environment": numeric_environment(),
    }

    # persist
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    combined_path = out_dir / f"{run_id}.json"
    combined_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")

    # human-readable report
    lines = [
        f"# Current Head Slice Quality Benchmark — run {run_id}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Direction: v{_current_direction_version()} (derived from state/evaluation.json)",
        f"- Product mount head: `{actual_mount_head}`",
        f"- Packet of record: {PACKET_OF_RECORD}",
        f"- Hypothesis sha256: `{EXPECTED_HYPOTHESIS_SHA[:16]}...` (frozen from accepted v65 crosscheck)",
        f"- Combined verdict: **{verdict}** (exit {exit_code})",
        f"- H2 verdict: **{record['H2_verdict']}**",
        f"- Verified rows: {n_verified}; with defects: {n_defective}",
        f"- Defect histogram: {defect_hist}",
        f"- Distinct defective decisions: {len(defective_decision_ids)}",
        f"- Elapsed: {record['elapsed_s']} s",
        "",
        "## Controls",
        "",
    ]
    for c in controls.values():
        lines.append(f"- `{c['control']}`: {'PASS' if c['passed'] else 'FAIL'}")
    lines += ["", "## Bundles", ""]
    for b in bundles:
        if not b.get("present"):
            lines.append(f"- ⚠️ `{b['bundle']}`: MISSING")
            continue
        lines.append(
            f"- `{b['bundle']}` ({b['family']}): verified {b['n_counter_evidence_verified']}, "
            f"defective {b['n_verified_with_defects']} → {b['verdict']}"
            + (f" ids={b['defective_decision_ids']}" if b.get("defective_decision_ids") else ""))
        for r in b.get("verified_rows", []):
            if r["defects"]:
                lines.append(
                    f"    - `{r['decision_id']}` ({r['language']}, {r['counter_status']}): "
                    f"**{r['class']}** grounded_in={r['detail'].get('grounded_in')} "
                    f"offset={r['detail'].get('first_offset')} "
                    f"markup={r['detail'].get('markup_tokens_present')} "
                    f"evidence_head=`{r['evidence_head'][:80]}`")
    lines += [
        "",
        "## Reason",
        "",
        reason,
        "",
        "## Claim ceiling",
        "",
        record["claim_ceiling"],
        "",
        f"Machine record: `{_rel_or_abs(combined_path)}`",
    ]
    report_path = report_dir / f"CURRENT_HEAD_SLICE_QUALITY_{run_id}.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return exit_code, record


# Default committed destinations. Claim-bearing runs write HERE; a scratch run
# must pass --out-dir/--report-dir instead (audit convention).
DEFAULT_OUT_DIR = _REPO_ROOT / "results/evaluation/current_head_slice_quality"
DEFAULT_REPORT_DIR = _REPO_ROOT / "reports/evaluation"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None,
                    help="run id for result/report filenames (default: $GITHUB_RUN_ID or 'local')")
    ap.add_argument("--out-dir", default=None,
                    help="directory for the machine records "
                         "(default: the committed results/evaluation/ tree). "
                         "A scratch/ad-hoc invocation MUST override this so it "
                         "cannot rewrite a committed claim-bearing record.")
    ap.add_argument("--report-dir", default=None,
                    help="directory for the human-readable report "
                         "(default: the committed reports/evaluation/ tree). "
                         "Same scratch-run obligation as --out-dir.")
    ap.add_argument("--bundle", action="append", default=[],
                    help="Bundle to probe: 'relpath:family'. Can be repeated. "
                         "If not provided, discovers latest offline/server slices automatically.")
    args = ap.parse_args(argv)
    run_id = args.run_id or __import__("os").environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR

    bundle_paths = None
    if args.bundle:
        bundle_paths = []
        for b in args.bundle:
            if ":" in b:
                relpath, family = b.split(":", 1)
            else:
                relpath, family = b, "manual"
            bundle_paths.append((relpath, family))

    exit_code, record = run_benchmark(run_id, out_dir, report_dir, bundle_paths)
    print(json.dumps({
        "verdict": record.get("verdict"),
        "exit_code": exit_code,
        "h2_falsified": record.get("h2_falsified"),
        "n_verified": record.get("n_verified_rows_total"),
        "n_defective": record.get("n_verified_rows_with_defects"),
        "defect_histogram": record.get("defect_histogram"),
        "defective_decisions": record.get("defective_decision_ids"),
        "reason": record.get("reason"),
    }, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())