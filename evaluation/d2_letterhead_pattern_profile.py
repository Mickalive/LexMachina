#!/usr/bin/env python3
"""D2 letterhead pattern heterogeneity profile (v67 evaluation ordered work item 1).

FAST MVP / OPERATIONAL RESUME (GitHub run 40089391202, resumed producer snapshot
40085602229): POPULATION EXTENSION of the frozen item-(2) probe under the
ALREADY-FROZEN D2/D3/D4 predicates (instrument sha256 aac86527..., byte-identical,
re-hashed REPORTED-ONLY, NEVER edited). This run does NOT replace, re-baseline
or move accepted baseline 40062917685; it is disclosed as a separate named run.

Population: every committed flagship offline/server slice bundle family on the
accepted-product mount PLUS the packet-of-record 39319405429 question bundles,
both labelled. For each D2_letterhead_zone row the profile publishes a distinct
letterhead pattern (whitespace-normalized evidence digest), per-pattern counts,
languages, full_text offsets, line structure, and a mechanical detectability
class:

  P1_OFFSET0_MULTILINE_COURT_HEADER  offset == 0, >= 2 lines, every line <= 120 chars
  P2_MID_DOCUMENT_HEADER_ZONE        0 < offset < 400
  P3_OTHER_LETTERHEAD_ZONE_FORM      any other letterhead-zone form (requires inspection)

Reachability per row is ANNOTATED from accepted PATH_SCOPE_RESIDUAL ARM2
(cycle 40070818687, accept d0d3c4a7a) and is never re-run: slice-family rows are
fixture_bypass_only; the accepted ARM2 finding additionally established the
unmodified filter abstains pivot_absent on the known offset-0 trilingual header
when routed diagnostically.

Controls: C3 frozen rubric re-hash REPORTED-ONLY; C4 frozen instrument digest;
C5 planted letterhead/mid-document non-vacuity; C6 accepted-baseline 15-bundle
population cross-check NORMALIZED-IDENTICAL to artifact 40062917685.

No Product code is imported. No network is used. No frozen bar is scored; no
rubric/threshold/bar is edited; no serve verdict or posture flag changes.

Exit codes:
  0  LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED (all observed forms P1/P2)
  1  HETEROGENEOUS_BEYOND_MECHANICAL_DETECTION (>= 1 P3 form observed)
  2  CONTROLS_FAILED / ENVIRONMENT_ERROR (never a product verdict)
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

# Import FROZEN probe definitions BY VALUE from the accepted benchmark
from evaluation.counter_evidence_quality_benchmark import (  # noqa: E402
    LANGUAGE_MARKER_SETS,
    LETTERHEAD_ZONE_OFFSET_MAX,
    MARKUP_TOKENS,
    MIN_MARKER_HITS,
    classify_verified_row,
)

SCHEMA = "lex-evaluation-d2-letterhead-pattern-profile/1"

MOUNT = Path("/tmp/lex_accepted/product")
PACKET_OF_RECORD = "39319405429"
FROZEN_INSTRUMENT = _REPO_ROOT / "evaluation" / "counter_evidence_quality_benchmark.py"
FROZEN_INSTRUMENT_SHA_EXPECTED = (
    "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"
)
FROZEN_RUBRICS = {
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
}
ACCEPTED_BASELINE_ARTIFACT = (
    _REPO_ROOT / "results" / "evaluation" / "counter_evidence_quality_benchmark"
    / "40062917685.json"
)
ACCEPTED_BASELINE_HISTOGRAM = {"D2_letterhead_zone": 10, "D3_markup_residue": 4,
                               "D4_language_marker_mismatch": 4}
ACCEPTED_BASELINE_DECISIONS = {"bge_BGE_121_III_260", "gr_gerichte_ERZ 2010 25"}

# Cited, never re-run (accepted PATH_SCOPE_RESIDUAL ARM2, cycle 40070818687)
ARM2_CITATION = {
    "source": "accepted evaluation cycle 40070818687 (accept d0d3c4a7a), "
              "results/evaluation/d2_path_scope_probe/40070818687.json ARM2",
    "finding": "unmodified filter ABSTAINS reason_code=pivot_absent, "
               "span_selected=false, abstention_preserves_incumbent_evidence=true, "
               "outcome FILTER_LEAVES_ROW on the known offset-0 trilingual "
               "Graubunden letterhead row when routed diagnostically",
    "usage": "reachability annotation only; NOT re-run this cycle",
}

MAX_LINE_LEN_P1 = 120


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def numeric_environment() -> dict:
    env = {"platform": sys.platform, "python": sys.version.split()[0]}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = "absent"
    env["thread_env"] = {k: os.environ.get(k) for k in
                         ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                          "MKL_NUM_THREADS")}
    return env


def _current_direction_version() -> int:
    try:
        d = json.loads((_REPO_ROOT / "state" / "evaluation.json").read_text(
            encoding="utf-8"))
        return int(d.get("direction_version") or 0)
    except Exception:
        return 0


def _probe_verified_rows(mount: Path, relpath: str) -> tuple[dict | None, list[dict]]:
    """Apply the frozen row predicate + classify_verified_row to one bundle."""
    p = mount / relpath
    if not p.is_file():
        return None, []
    doc = json.loads(p.read_text(encoding="utf-8"))
    rows = doc.get("decisions") or []
    bearing = [r for r in rows if r.get("counter_status") not in (None, "none")]
    verified = [r for r in bearing if r.get("counter_evidence_verified") is True]
    per_row = []
    for r in verified:
        cl = classify_verified_row(r)
        per_row.append({
            "bundle": relpath,
            "decision_id": r.get("decision_id"),
            "counter_status": r.get("counter_status"),
            "counter_uncertainty": r.get("counter_uncertainty"),
            "language": r.get("language"),
            **cl,
        })
    return {
        "n_decisions": len(rows),
        "n_status_bearing": len(bearing),
        "n_counter_evidence_verified": len(verified),
    }, per_row


def _discover_population(mount: Path) -> list[dict]:
    """Named, sha256-pinned bundle set: all committed flagship offline/server
    slice bundles + packet-of-record question bundles, with family labels."""
    # accepted-baseline family map (paths named in artifact 40062917685)
    family_map: dict[str, str] = {}
    if ACCEPTED_BASELINE_ARTIFACT.is_file():
        base = json.loads(ACCEPTED_BASELINE_ARTIFACT.read_text(encoding="utf-8"))
        for b in base.get("bundles") or []:
            if b.get("bundle"):
                family_map[b["bundle"]] = b.get("family") or "accepted_baseline"
        pc = base.get("prior_cycle_control")
        if pc and pc.get("bundle"):
            family_map[pc["bundle"]] = pc.get("family") or "prior_cycle_control"

    # latest dirs (same discovery rule as accepted measure_current_head_slices)
    latest_offline = max((mount / "results/product/offline_slice").glob("*"),
                         default=None, key=lambda d: d.name)
    latest_server = max((mount / "results/product/server_slice").glob("*"),
                        default=None, key=lambda d: d.name)

    population: list[dict] = []
    for root, latest, prefix in (
        (mount / "results/product/offline_slice", latest_offline, "offline"),
        (mount / "results/product/server_slice", latest_server, "server"),
    ):
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            for bf in sorted(d.glob("*.bundle.json")):
                rel = str(bf.relative_to(mount))
                if rel in family_map:
                    family = family_map[rel]
                elif latest is not None and d.resolve() == latest.resolve():
                    family = f"{prefix}_latest_{d.name}"
                else:
                    family = f"{prefix}_slice_other_{d.name}"
                population.append({
                    "bundle": rel,
                    "family": family,
                    "scope": "shipped_slice",
                    "sha256": _sha256_file(bf),
                })

    packet_root = (mount / "results/product/gate_packet" / PACKET_OF_RECORD
                   / "questions")
    if packet_root.is_dir():
        for bf in sorted(packet_root.glob("*.bundle.json")):
            rel = str(bf.relative_to(mount))
            population.append({
                "bundle": rel,
                "family": f"packet_of_record_{PACKET_OF_RECORD}",
                "scope": "packet_of_record",
                "sha256": _sha256_file(bf),
            })
    return population


def _classify_pattern(ev_s: str, detail: dict) -> tuple[str, dict]:
    """Assign the frozen detectability taxonomy to one D2 row's evidence."""
    offset = detail.get("first_offset")
    lines = ev_s.splitlines() or [ev_s]
    line_lengths = [len(l) for l in lines]
    structure = {
        "n_lines": len(lines),
        "line_lengths": line_lengths,
        "line_previews": [l[:120] for l in lines[:6]],
        "first_offset": offset,
    }
    if isinstance(offset, int) and offset > 0 and offset < LETTERHEAD_ZONE_OFFSET_MAX:
        return "P2_MID_DOCUMENT_HEADER_ZONE", structure
    if (isinstance(offset, int) and offset == 0
            and len(lines) >= 2
            and all(n <= MAX_LINE_LEN_P1 for n in line_lengths)):
        return "P1_OFFSET0_MULTILINE_COURT_HEADER", structure
    return "P3_OTHER_LETTERHEAD_ZONE_FORM", structure


def _reachability_label(family: str, scope: str) -> str:
    if scope == "packet_of_record":
        return ("packet_of_record_served_bytes (frozen verified-row predicate "
                "population; production emission path, label only)")
    return ("fixture_bypass_only (emitted on the fixture path: "
            "product/offline_slice.py fixture_generation=True gates the span "
            "seam at product/query/pipeline.py:1339; the filter never runs). "
            "Per accepted PATH_SCOPE_RESIDUAL ARM2 (40070818687) the unmodified "
            "filter would ABSTAIN pivot_absent on the known offset-0 trilingual "
            "header if routed - cited, not re-run.")


def run(run_id: str, out_dir: Path, report_dir: Path) -> tuple[int, dict]:
    t0 = time.time()
    controls: dict[str, dict] = {}

    # ---- C3: frozen rubric re-hash REPORTED-ONLY --------------------------
    rubric_status = {}
    for rel, expected in FROZEN_RUBRICS.items():
        p = _REPO_ROOT / rel
        actual = _sha256_file(p) if p.is_file() else None
        rubric_status[rel] = {"expected": expected, "actual": actual,
                              "matches": actual == expected}
    controls["C3"] = {
        "control": "C3_frozen_rubric_rehash_reported_only",
        "passed": all(v["matches"] for v in rubric_status.values()),
        "rubrics": rubric_status,
        "note": "re-hashed REPORTED-ONLY; never applied, edited or re-derived",
    }

    # ---- C4: frozen instrument digest -------------------------------------
    inst_sha = _sha256_file(FROZEN_INSTRUMENT)
    controls["C4"] = {
        "control": "C4_frozen_instrument_digest_unchanged",
        "expected": FROZEN_INSTRUMENT_SHA_EXPECTED,
        "instrument_sha256": inst_sha,
        "passed": inst_sha == FROZEN_INSTRUMENT_SHA_EXPECTED,
        "note": "proves the imported D2/D3/D4 predicate file is byte-identical "
                "to the frozen accepted instrument (accepted cycle 40062917685); "
                "the predicates themselves are never re-derived here",
    }

    # ---- C5: planted letterhead / planted mid-document non-vacuity --------
    planted_lh = {
        "counter_evidence": ("Kantonsgericht X\nGericht Y\n"
                             "________________________"),
        "full_text": "Kantonsgericht X\nGericht Y\n________________________"
                     + (" substantive body" * 40),
        "language": "de", "counter_status": "candidate-limiting",
        "counter_evidence_verified": True,
    }
    planted_mid_ev = ("Erwägung: im vorliegenden Fall wurde die Kündigung "
                      "geprüft und als rechtmäßig erachtet, weshalb auf die "
                      "Berufung nicht einzutreten ist.")
    planted_mid = {
        "counter_evidence": planted_mid_ev,
        "full_text": ("x" * 500) + "\n" + planted_mid_ev,
        "language": "de", "counter_status": "cited",
        "counter_evidence_verified": True,
    }
    cl_lh = classify_verified_row(planted_lh)
    cl_mid = classify_verified_row(planted_mid)
    controls["C5"] = {
        "control": "C5_non_vacuity_planted_letterhead_vs_mid_document",
        "letterhead_defects": cl_lh["defects"],
        "letterhead_offset": cl_lh["detail"].get("first_offset"),
        "mid_defects": cl_mid["defects"],
        "mid_offset": cl_mid["detail"].get("first_offset"),
        "passed": ("D2_letterhead_zone" in cl_lh["defects"]
                   and "D2_letterhead_zone" not in cl_mid["defects"]),
        "note": "planted letterhead-span row must be caught; planted "
                "mid-document substantive span (offset >= 400) must NOT be "
                "flagged D2",
    }

    if not MOUNT.is_dir():
        controls["ENV"] = {"control": "mount_present", "passed": False,
                           "detail": f"missing {MOUNT}"}
        rec = {"schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_ERROR",
               "controls": controls, "exit_code": 2,
               "generated_at_utc": datetime.now(timezone.utc).strftime(
                   "%Y-%m-%dT%H:%M:%SZ")}
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{run_id}.json").write_text(
            json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return 2, rec

    # ---- population discovery (sha256-pinned) ------------------------------
    population = _discover_population(MOUNT)
    n_slice = sum(1 for b in population if b["scope"] == "shipped_slice")
    n_packet = sum(1 for b in population if b["scope"] == "packet_of_record")

    # ---- C6: accepted-baseline population cross-check ----------------------
    c6_rows: list[dict] = []
    c6_missing: list[str] = []
    baseline_paths: list[tuple[str, str]] = []
    if ACCEPTED_BASELINE_ARTIFACT.is_file():
        base = json.loads(ACCEPTED_BASELINE_ARTIFACT.read_text(encoding="utf-8"))
        for b in base.get("bundles") or []:
            baseline_paths.append((b["bundle"], b.get("family") or "accepted_baseline"))
        pc = base.get("prior_cycle_control")
        if pc and pc.get("bundle"):
            baseline_paths.append((pc["bundle"],
                                   pc.get("family") or "prior_cycle_control"))
    for rel, fam in baseline_paths:
        stats, rows = _probe_verified_rows(MOUNT, rel)
        if stats is None:
            c6_missing.append(rel)
            continue
        c6_rows.extend(rows)
    from collections import Counter
    c6_hist = Counter()
    for r in c6_rows:
        for dcode in r["defects"]:
            c6_hist[dcode] += 1
    c6_decisions = {r["decision_id"] for r in c6_rows if r["defects"]}
    c6_norm = dict(sorted(c6_hist.items()))
    base_norm = dict(sorted(ACCEPTED_BASELINE_HISTOGRAM.items()))
    controls["C6"] = {
        "control": "C6_accepted_baseline_population_crosscheck",
        "baseline_artifact": "results/evaluation/counter_evidence_quality_benchmark/40062917685.json",
        "n_baseline_bundles_reprobed": len(baseline_paths),
        "n_baseline_bundles_missing": len(c6_missing),
        "missing": c6_missing,
        "n_verified_rows": len(c6_rows),
        "defect_histogram_actual": c6_norm,
        "defect_histogram_accepted": base_norm,
        "defective_decisions_actual": sorted(c6_decisions),
        "passed": (not c6_missing and c6_norm == base_norm
                   and c6_decisions == ACCEPTED_BASELINE_DECISIONS),
        "note": "re-probing the accepted-baseline bundles must reproduce the "
                "accepted defect histogram NORMALIZED-IDENTICAL to artifact "
                "40062917685; pins identical predicates, moves nothing",
    }

    controls_all_pass = all(c.get("passed") for c in controls.values())

    # ---- probe the named population ----------------------------------------
    bundle_records = []
    all_rows: list[dict] = []
    for b in population:
        stats, rows = _probe_verified_rows(MOUNT, b["bundle"])
        rec = dict(b)
        rec.update(stats or {})
        rec["n_verified_with_defects"] = sum(1 for r in rows if r["defects"])
        bundle_records.append(rec)
        all_rows.extend(rows)

    # ---- pattern inventory over D2 rows -------------------------------------
    patterns: dict[str, dict] = {}
    d2_rows = [r for r in all_rows if "D2_letterhead_zone" in r["defects"]]
    for r in d2_rows:
        ev = r.get("evidence_head") or ""
        # evidence_head is truncated at 160 chars by the frozen classifier;
        # re-read the full evidence for structure fidelity
        full_ev = _full_evidence_for_row(MOUNT, r["bundle"], r["decision_id"])
        ev_s = full_ev if full_ev is not None else ev
        key = _sha256_text(_normalize_ws(ev_s))
        det_class, structure = _classify_pattern(ev_s, r["detail"])
        scope = next((b["scope"] for b in population
                      if b["bundle"] == r["bundle"]), "shipped_slice")
        fam = next((b["family"] for b in population
                    if b["bundle"] == r["bundle"]), "unknown")
        p = patterns.setdefault(key, {
            "pattern_key": key,
            "normalized_evidence_sha256": key,
            "detectability_class": det_class,
            "n_rows": 0,
            "languages": set(), "bundle_families": set(), "bundles": set(),
            "decisions": set(), "full_text_offsets": set(),
            "line_structure": structure,
            "reachability_labels": set(),
            "evidence_preview": _normalize_ws(ev_s)[:240],
        })
        p["n_rows"] += 1
        p["languages"].add(r.get("language"))
        p["bundle_families"].add(fam)
        p["bundles"].add(r["bundle"])
        p["decisions"].add(r.get("decision_id"))
        p["full_text_offsets"].add(r["detail"].get("first_offset"))
        p["reachability_labels"].add(_reachability_label(fam, scope))

    # serialize sets
    pattern_list = []
    for p in patterns.values():
        p["languages"] = sorted(x for x in p["languages"] if x)
        p["bundle_families"] = sorted(p["bundle_families"])
        p["bundles"] = sorted(p["bundles"])
        p["decisions"] = sorted(x for x in p["decisions"] if x)
        p["full_text_offsets"] = sorted(x for x in p["full_text_offsets"]
                                        if isinstance(x, int))
        p["reachability_labels"] = sorted(p["reachability_labels"])
        pattern_list.append(p)
    pattern_list.sort(key=lambda p: (-p["n_rows"], p["pattern_key"]))

    # per-pattern defect-class counts (D2 rows only by construction; counts
    # every defect code observed on those same rows for completeness)
    defect_class_by_pattern = {}
    for p in pattern_list:
        cnt: Counter = Counter()
        for r in d2_rows:
            if r["bundle"] in p["bundles"] and r.get("decision_id") in p["decisions"]:
                for dc in r["defects"]:
                    cnt[dc] += 1
        defect_class_by_pattern[p["pattern_key"]] = dict(sorted(cnt.items()))
        p["defect_class_counts"] = defect_class_by_pattern[p["pattern_key"]]

    # whole-population defect histogram (descriptive, all classes)
    pop_hist: Counter = Counter()
    for r in all_rows:
        for dc in r["defects"]:
            pop_hist[dc] += 1

    packet_bundles = [b for b in bundle_records if b["scope"] == "packet_of_record"]
    packet_verified_total = sum(b.get("n_counter_evidence_verified") or 0
                                for b in packet_bundles)
    slice_bundles = [b for b in bundle_records if b["scope"] == "shipped_slice"]
    slice_verified_total = sum(b.get("n_counter_evidence_verified") or 0
                               for b in slice_bundles)
    slice_defective_total = sum(b.get("n_verified_with_defects") or 0
                                for b in slice_bundles)

    p3 = [p for p in pattern_list
          if p["detectability_class"] == "P3_OTHER_LETTERHEAD_ZONE_FORM"]
    if not controls_all_pass:
        verdict, exit_code = "CONTROLS_FAILED", 2
    elif p3:
        verdict, exit_code = ("HETEROGENEOUS_BEYOND_MECHANICAL_DETECTION", 1)
    else:
        verdict, exit_code = "LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED", 0

    finding = (
        f"Population-extension profile over {len(population)} named sha256-pinned "
        f"bundles ({n_slice} shipped-slice + {n_packet} packet-of-record "
        f"{PACKET_OF_RECORD}): {len(d2_rows)} D2_letterhead_zone rows collapse "
        f"into {len(pattern_list)} distinct letterhead pattern(s) "
        f"({', '.join(sorted({p['detectability_class'] for p in pattern_list})) or 'none observed'}). "
        f"Slice verified rows {slice_verified_total} "
        f"({slice_defective_total} defective); packet-of-record verified rows "
        f"{packet_verified_total} under the frozen predicate (accepted "
        f"requirement 36/42 expectation: 0 on served bytes - labelled, not an "
        f"error)."
    )

    rec = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction_version": _current_direction_version(),
        "direction_version_pin_note": "state-level direction_version read at runtime; v67 is the controlling direction for this run",
        "product_mount": str(MOUNT),
        "product_mount_head": _mount_head(),
        "packet_of_record": PACKET_OF_RECORD,
        "population_extension_disclosure": (
            "v67 item (1) POPULATION EXTENSION: separate named run; does NOT "
            "replace, re-baseline or move accepted baseline 40062917685; scores "
            "no frozen bar; edits nothing frozen."),
        "probe_is_not_a_frozen_bar": (
            "the population is the product's shipped slice bundles plus the "
            "packet-of-record question bundles, NOT the RULES_LABEL population; "
            "the frozen rubrics are re-hashed REPORTED-ONLY and never applied, "
            "edited or re-derived"),
        "frozen_predicate_instrument_sha256": FROZEN_INSTRUMENT_SHA_EXPECTED,
        "n_bundles": len(population),
        "n_bundles_shipped_slice": n_slice,
        "n_bundles_packet_of_record": n_packet,
        "n_verified_rows_shipped_slice": slice_verified_total,
        "n_verified_rows_packet_of_record": packet_verified_total,
        "population_defect_histogram": dict(sorted(pop_hist.items())),
        "d2_rows_profiled": len(d2_rows),
        "n_distinct_letterhead_patterns": len(pattern_list),
        "letterhead_patterns": pattern_list,
        "detectability_summary": {
            "P1_OFFSET0_MULTILINE_COURT_HEADER": sum(
                1 for p in pattern_list
                if p["detectability_class"] == "P1_OFFSET0_MULTILINE_COURT_HEADER"),
            "P2_MID_DOCUMENT_HEADER_ZONE": sum(
                1 for p in pattern_list
                if p["detectability_class"] == "P2_MID_DOCUMENT_HEADER_ZONE"),
            "P3_OTHER_LETTERHEAD_ZONE_FORM": len(p3),
            "p3_patterns": [
                {"pattern_key": p["pattern_key"],
                 "evidence_preview": p["evidence_preview"],
                 "line_structure": p["line_structure"],
                 "n_rows": p["n_rows"]}
                for p in p3],
        },
        "reachability_rule": (
            "slice-family D2 rows are fixture_bypass_only (filter never runs on "
            "the fixture path); ARM2 abstention finding is CITED from accepted "
            "cycle 40070818687 and NOT re-run"),
        "arm2_citation": ARM2_CITATION,
        "population": bundle_records,
        "controls": controls,
        "controls_all_pass": controls_all_pass,
        "verdict": verdict,
        "finding": finding,
        "claim_ceiling": (
            "Descriptive letterhead-pattern inventory ONLY: tells Core Product's "
            "P0-residual decision whether deterministic letterhead filtering is "
            "mechanically feasible on the observed variant distribution. Scores "
            "no frozen bar, edits nothing frozen, classifies no decision as "
            "supporting/contrary under the frozen rubric, changes no serve "
            "verdict and makes no legal-usefulness claim. Both DO-NOT-SERVE "
            "orders stand; admission stays fail-closed; comparative "
            "map-versus-ranked-list stays VACUOUS; owner_decision_required stays "
            "false."),
        "no_bar_movement": True,
        "no_obsolete_174k_benchmark_rerun": True,
        "numeric_environment": numeric_environment(),
        "elapsed_s": round(time.time() - t0, 3),
        "exit_code": exit_code,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}.json").write_text(
        json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    report_dir.mkdir(parents=True, exist_ok=True)
    _write_report(report_dir / f"D2_LETTERHEAD_PATTERN_PROFILE_{run_id}.md", rec)
    return exit_code, rec


def _full_evidence_for_row(mount: Path, bundle_rel: str,
                           decision_id: str) -> str | None:
    """Re-read the full counter_evidence string for one verified row."""
    p = mount / bundle_rel
    if not p.is_file():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    for r in doc.get("decisions") or []:
        if (r.get("decision_id") == decision_id
                and r.get("counter_evidence_verified") is True):
            ev = r.get("counter_evidence")
            return ev if isinstance(ev, str) else (
                "" if ev is None else json.dumps(ev))
    return None


def _mount_head() -> str | None:
    import subprocess
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=MOUNT,
            capture_output=True, text=True, timeout=15,
        ).stdout.strip() or None
    except Exception:
        return None


def _write_report(path: Path, rec: dict) -> None:
    ctl_summary = ", ".join(
        "{}={}".format(k, "PASS" if v.get("passed") else "FAIL")
        for k, v in rec["controls"].items())
    lines = [
        f"# D2 Letterhead Pattern Heterogeneity Profile — {rec['run_id']}",
        "",
        f"- direction_version: {rec['direction_version']} (v67 ordered work item (1), "
        f"population extension, separate named run — accepted baseline 40062917685 UNMOVED)",
        f"- product mount: `{rec['product_mount']}` head `{rec['product_mount_head']}`",
        f"- packet-of-record: {rec['packet_of_record']} (labelled; "
        f"verified rows under frozen predicate: {rec['n_verified_rows_packet_of_record']})",
        f"- verdict: **{rec['verdict']}** (exit {rec['exit_code']})",
        f"- controls: {'ALL PASS' if rec['controls_all_pass'] else 'FAILED'} "
        f"({ctl_summary})",
        "",
        "## Finding",
        "",
        rec["finding"],
        "",
        "## Letterhead pattern inventory",
        "",
        f"D2 rows profiled: {rec['d2_rows_profiled']} — distinct patterns: "
        f"{rec['n_distinct_letterhead_patterns']}",
        "",
    ]
    for p in rec["letterhead_patterns"]:
        lines += [
            f"### pattern `{p['pattern_key'][:16]}…` — {p['detectability_class']}",
            "",
            f"- n_rows: {p['n_rows']}; languages: {p['languages']}",
            f"- decisions: {p['decisions']}",
            f"- bundles ({len(p['bundles'])}): " + ", ".join(
                f"`{b}`" for b in p["bundles"][:8]) + (
                " …" if len(p["bundles"]) > 8 else ""),
            f"- families: {p['bundle_families']}",
            f"- full_text offsets: {p['full_text_offsets']}",
            f"- line structure: {p['line_structure']['n_lines']} lines, "
            f"lengths {p['line_structure']['line_lengths']}",
            f"- evidence preview: {p['evidence_preview'][:160]!r}",
            f"- reachability: {p['reachability_labels']}",
            f"- defect classes on these rows: {p['defect_class_counts']}",
            "",
        ]
    lines += [
        "## Detectability summary",
        "",
        f"- P1 offset-0 multi-line court headers: {rec['detectability_summary']['P1_OFFSET0_MULTILINE_COURT_HEADER']}",
        f"- P2 mid-document headers: {rec['detectability_summary']['P2_MID_DOCUMENT_HEADER_ZONE']}",
        f"- P3 other letterhead-zone forms: {rec['detectability_summary']['P3_OTHER_LETTERHEAD_ZONE_FORM']}",
        "",
        "## Feasibility reading for Core Product (descriptive, claim ceiling)",
        "",
    ]
    if rec["verdict"] == "LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED":
        lines.append(
            "All observed D2 letterhead forms fall into the mechanically "
            "detectable classes (P1/P2). On this named population the "
            "deterministic letterhead-filter branch remains mechanically "
            "viable; reachability remains fixture_bypass_only for slice rows "
            "and the ARM2 abstention finding (pivot_absent on the known "
            "offset-0 trilingual header when routed) still binds the filter's "
            "own detector — product's P0 repair must fix BOTH legs per v67.")
    else:
        lines.append(
            "At least one P3 (heterogeneous-beyond-mechanical) letterhead form "
            "was observed; per v67 this profile IS the load-bearing "
            "bounded-negative evidence for the deterministic filter branch, "
            "published as such rather than as a defect count. See "
            "detectability_summary.p3_patterns for the verbatim forms.")
    lines += [
        "",
        "## Posture",
        "",
        "Both DO-NOT-SERVE orders stand; admission stays fail-closed "
        "(PACKET_ADMITTED=FALSE, MACHINE_GATE_READY=FALSE, "
        "HUMAN_GATE_READY=FALSE, READY_FOR_OWNER_SESSION=FALSE); comparative "
        "map-versus-ranked-list stays VACUOUS; owner_decision_required=false; "
        "no frozen bar, rubric, threshold or verdict contract was edited; no "
        "174k benchmark was rerun.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--report-dir", default=None)
    args = ap.parse_args(argv)
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID") or (
        "local_eval_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out_dir = Path(args.out_dir) if args.out_dir else (
        _REPO_ROOT / "results" / "evaluation" / "d2_letterhead_pattern_profile")
    report_dir = Path(args.report_dir) if args.report_dir else (
        _REPO_ROOT / "reports" / "evaluation")
    code, rec = run(run_id, out_dir, report_dir)
    print(json.dumps({
        "verdict": rec.get("verdict"),
        "exit_code": code,
        "controls_all_pass": rec.get("controls_all_pass"),
        "n_bundles": rec.get("n_bundles"),
        "d2_rows_profiled": rec.get("d2_rows_profiled"),
        "n_distinct_letterhead_patterns": rec.get("n_distinct_letterhead_patterns"),
        "detectability_summary": rec.get("detectability_summary"),
        "finding": rec.get("finding"),
    }, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
