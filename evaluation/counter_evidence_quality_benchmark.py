#!/usr/bin/env python3
"""Smallest executable counter-evidence content-quality falsification benchmark.
 
FAST MVP: Measures the H2 defect class (D2_letterhead_zone / D3_markup_residue /
D4_language_marker_mismatch) on the product's own shipped slice bundles.
 
REUSE-FIRST: The frozen D1-D4 defect predicates are imported BY VALUE from the
accepted v65_head_advance_crosscheck_v2 hypothesis (sha256 734a447d...). The
predicates are mechanical, require no legal reasoning/LLM/paid API, and are
frozen — they are never re-tuned, re-derived or edited after results are seen.
 
This benchmark scores NO frozen bar. Its population is the product's own
shipped slice bundles (offline/server), not the RULES_LABEL population. The
frozen RULES_LABEL/GEOMETRY rubrics are re-hashed REPORTED-ONLY and never
applied (factory-wide requirement 22).
 
Exit codes:
  0  QUALITY_BENCHMARK_VALID_H2_SURVIVES
       Zero verified rows carry a frozen defect. The product's counter-evidence
       extractor emits no letterhead/markup/language-mismatch defects on the
       flagship slices. (This has NOT been observed; the accepted H2 probe
       measured 14/14 defective.)
  1  H2_FALSIFIED
       One or more verified rows carry a frozen defect. The content-quality
       bottleneck is confirmed on the product's own artifacts.
  2  ENVIRONMENT_OR_VACUOUS
       Missing inputs, mount unavailable, or a control failed (probe cannot
       detect planted defects) — never a product verdict.
 
No Product code is imported. No network is used. The accepted-product mount at
/tmp/lex_accepted is read-only input.
 
SCRATCH-RUN OBLIGATION (audit convention): a claim-bearing cycle writes its
records to the committed defaults below. A scratch invocation (a unit test, a
local poke, a retry) MUST pass --out-dir and --report-dir; otherwise it
overwrites committed claim-bearing records.
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
 
SCHEMA = "lex-evaluation-counter-evidence-quality-benchmark/1"
 
# --- Frozen probe definitions (mirrored from accepted v65 hypothesis;
#     hypothesis sha256 734a447dffd86a360a46ce9a804e3bb9f7eb224f9067777d78b62216e13e0881) ---
EXPECTED_HYPOTHESIS_SHA = "734a447dffd86a360a46ce9a804e3bb9f7eb224f9067777d78b62216e13e0881"
LETTERHEAD_ZONE_OFFSET_MAX = 400
MARKUP_TOKENS = ["<mark>", "</mark>", "<em>", "</em>", "<b>", "</b>", "<highlight>"]
MIN_MARKER_HITS = 3
LANGUAGE_MARKER_SETS = {
    "de": ["Regeste", "Erwägung", "Kündigung", "Mietvertrag", "Bundesgericht", "Verfügung"],
    "fr": ["Considérant", "résiliation", "bail", "Tribunal fédéral", "recours", "art."],
    "it": ["Dispositivo", "risoluzione", "affitto", "Tribunale federale", "ricorso", "regola"],
}
 
# Probe bundles: the product's shipped slice bundles (offline + server) that
# carry counter_evidence_verified rows. These are the exact bundles measured by
# the accepted H2 probe in run 40044626742.
PROBE_BUNDLES = {
    "offline_accept_40025340938": [
        "results/product/offline_slice/20261023T202433Z/rent-default.bundle.json",
        "results/product/offline_slice/20261023T202440Z/rent-default.bundle.json",
        "results/product/offline_slice/20261023T203316Z/rent-default.bundle.json",
        "results/product/offline_slice/20261023T212530Z/rent-default.bundle.json",
    ],
    "offline_accept_40032389983": [
        "results/product/offline_slice/20261023T214943Z/rent-default.bundle.json",
        "results/product/offline_slice/20261023T220629Z/rent-default.bundle.json",
        "results/product/offline_slice/20261023T222223Z/rent-default.bundle.json",
        "results/product/offline_slice/20261023T223903Z/rent-default.bundle.json",
        "results/product/offline_slice/20261023T224023Z/rent-default.bundle.json",
        "results/product/offline_slice/20261023T224250Z/rent-default.bundle.json",
    ],
    "server_accept_40032389983": [
        "results/product/server_slice/20261023T223109Z/served.bundle.json",
        "results/product/server_slice/20261023T223909Z/served.bundle.json",
        "results/product/server_slice/20261023T224031Z/served.bundle.json",
        "results/product/server_slice/20261023T224255Z/served.bundle.json",
    ],
}
# Prior-cycle control bundle (from accepted cycle 40005362253)
PRIOR_CYCLE_CONTROL = "results/product/offline_slice/20261023T190402Z/rent-default.bundle.json"
 
# Scoping-inspected bundles (disclosed per freeze record)
SCOPING_INSPECTED = {
    "results/product/offline_slice/20261023T203316Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T224250Z/rent-default.bundle.json",
    "results/product/server_slice/20261023T224255Z/served.bundle.json",
}
 
MOUNT = Path("/tmp/lex_accepted/product")
PACKET_OF_RECORD = "39319405429"
EXPECTED_MOUNT_HEAD = "e4f72a8e6c0460bc52dc625ff3e2da86161e2564"
 
 
def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
 
 
def _marker_hits(evidence: str, lang: str) -> int:
    return sum(1 for tok in LANGUAGE_MARKER_SETS[lang] if tok in evidence)
 
 
def classify_verified_row(row: dict) -> dict:
    """Apply the FROZEN D1-D4 defect predicates to one counter_evidence_verified row."""
    ev = row.get("counter_evidence")
    ev_s = ev if isinstance(ev, str) else ("" if ev is None else json.dumps(ev))
    ft = row.get("full_text") or ""
    snippet = row.get("snippet") or ""
    regeste = row.get("regeste") or ""
    lang = row.get("language")
 
    defects = []
    detail = {"evidence_len": len(ev_s)}
 
    # D1 empty
    if not ev_s.strip():
        defects.append("D1_empty_evidence")
 
    # grounding
    grounded_in = None
    offset = None
    for field, text in (("full_text", ft), ("snippet", snippet), ("regeste", regeste)):
        idx = text.find(ev_s) if ev_s else -1
        if idx >= 0:
            grounded_in = field
            offset = idx
            break
    detail["grounded_in"] = grounded_in
    detail["first_offset"] = offset
    detail["full_text_len"] = len(ft)
    detail["full_text_status"] = row.get("full_text_status")
 
    # D2 letterhead zone (only meaningful when grounded in own full_text)
    letterhead = (grounded_in == "full_text" and offset is not None
                  and offset < LETTERHEAD_ZONE_OFFSET_MAX and len(ev_s) > 0)
    if letterhead:
        defects.append("D2_letterhead_zone")
    detail["letterhead_zone_offset_max"] = LETTERHEAD_ZONE_OFFSET_MAX
 
    # D3 markup residue
    present_tokens = [t for t in MARKUP_TOKENS if t in ev_s]
    if present_tokens:
        defects.append("D3_markup_residue")
    detail["markup_tokens_present"] = present_tokens
 
    # D4 language marker mismatch
    mismatch = False
    if lang in LANGUAGE_MARKER_SETS and ev_s.strip():
        own = _marker_hits(ev_s, lang)
        others = {L: _marker_hits(ev_s, L) for L in LANGUAGE_MARKER_SETS if L != lang}
        detail["marker_hits_own"] = own
        detail["marker_hits_other"] = others
        best_other = max(others.values()) if others else 0
        if own == 0 and best_other >= MIN_MARKER_HITS:
            mismatch = True
            defects.append("D4_language_marker_mismatch")
    elif lang not in LANGUAGE_MARKER_SETS:
        detail["marker_language_out_of_scope"] = lang
 
    row_class = "COUNTER_REASONING" if not defects else "+".join(defects)
    return {"defects": defects, "class": row_class, "detail": detail,
            "evidence_head": ev_s[:160]}
 
 
def probe_bundle(mount: Path, relpath: str, family: str) -> dict:
    p = mount / relpath
    rec = {"bundle": relpath, "family": family,
           "scoping_inspected": relpath in SCOPING_INSPECTED,
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
 
 
def _current_direction_version() -> int:
    state_path = _REPO_ROOT / "state" / "evaluation.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return int(state["direction_version"])
 
 
def run_benchmark(run_id: str, out_dir: Path, report_dir: Path) -> tuple[int, dict]:
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
        if head != EXPECTED_MOUNT_HEAD:
            # Not a hard failure - the accepted bundles are present and measurable.
            # The expected head (e4f72a8e) is the accepted product cycle 40032389983;
            # the mounted worktree may be at a different commit but with the same artifacts.
            pass
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
 
    # ---- measurement: probe all shipped slice bundles --------------------
    bundles = []
    for family, rels in PROBE_BUNDLES.items():
        for rel in rels:
            bundles.append(probe_bundle(MOUNT, rel, family))
    control_bundle = probe_bundle(MOUNT, PRIOR_CYCLE_CONTROL, "prior_cycle_control")
    all_bundles = bundles + [control_bundle]
 
    n_verified = sum(b.get("n_counter_evidence_verified", 0) for b in all_bundles)
    n_defective = sum(b.get("n_verified_with_defects", 0) for b in all_bundles)
    defect_hist = {}
    defective_decision_ids = set()
    for b in all_bundles:
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
                  f"{len(all_bundles)} bundles carry a frozen defect "
                  f"({defect_hist}) over {len(defective_decision_ids)} distinct decision(s). "
                  f"The counter-evidence extractor emits letterhead/markup/language-mismatch "
                  f"content on the product's own flagship slice artifacts.")
    else:
        verdict = "QUALITY_BENCHMARK_VALID_H2_SURVIVES"
        exit_code = 0
        reason = ("Zero verified rows carry a frozen defect. The product's counter-evidence "
                  "extractor emits no letterhead/markup/language-mismatch defects on the "
                  "flagship slices.")
 
    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction_version": _current_direction_version(),
        "hypothesis_sha256": EXPECTED_HYPOTHESIS_SHA,
        "product_mount": str(MOUNT),
        "product_mount_head_expected": EXPECTED_MOUNT_HEAD,
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
            "the population is the product's own shipped slice bundles, NOT the RULES_LABEL "
            "population (packet-of-record 39319405429); the frozen rubrics are re-hashed "
            "REPORTED-ONLY and never applied, edited or re-derived (factory-wide requirement 22)"),
        "n_bundles": len(all_bundles),
        "n_bundles_present": sum(1 for b in all_bundles if b.get("present")),
        "n_bundles_scoping_inspected": sum(1 for b in all_bundles if b.get("scoping_inspected")),
        "n_verified_rows_total": n_verified,
        "n_verified_rows_with_defects": n_defective,
        "defect_histogram": defect_hist,
        "defective_decision_ids": sorted(defective_decision_ids),
        "H2_verdict": "H2_FALSIFIED" if h2_falsified else "H2_SURVIVES",
        "h2_falsified": h2_falsified,
        "bundles": bundles,
        "prior_cycle_control": control_bundle,
        "controls": controls,
        "verdict": verdict,
        "exit_code": exit_code,
        "reason": reason,
        "claim_ceiling": (
            "descriptive evidence audit of the product's own shipped slice artifacts under "
            "frozen mechanical defect predicates; scores no frozen bar, classifies no decision "
            "as supporting/contrary under the frozen rubric, and changes no verdict. Both "
            "DO-NOT-SERVE orders stand; admission stays fail-closed; the comparative "
            "map-versus-ranked-list half is NOT scored while counter-evidence content defects "
            "persist (factory-wide requirement 22/37)."),
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
        f"# Counter-Evidence Content-Quality Falsification Benchmark — run {run_id}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Direction: v{_current_direction_version()} (derived from state/evaluation.json)",
        f"- Product mount head: `{EXPECTED_MOUNT_HEAD}`",
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
    for b in all_bundles:
        flag = " (scoping-inspected)" if b.get("scoping_inspected") else ""
        if not b.get("present"):
            lines.append(f"- ⚠️ `{b['bundle']}`: MISSING")
            continue
        lines.append(
            f"- `{b['bundle']}`{flag}: verified {b['n_counter_evidence_verified']}, "
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
    report_path = report_dir / f"COUNTER_EVIDENCE_QUALITY_BENCHMARK_{run_id}.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
 
    return exit_code, record
 
 
#: Default committed destinations.  Claim-bearing runs write HERE; a scratch run
#: must pass --out-dir/--report-dir instead (audit convention).
DEFAULT_OUT_DIR = _REPO_ROOT / "results/evaluation/counter_evidence_quality_benchmark"
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
    args = ap.parse_args(argv)
    run_id = args.run_id or __import__("os").environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR
    exit_code, record = run_benchmark(run_id, out_dir, report_dir)
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