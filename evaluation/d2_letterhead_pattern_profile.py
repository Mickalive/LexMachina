#!/usr/bin/env python3
"""D2 letterhead pattern heterogeneity profile (v68 evaluation lane scope).

OPERATIONAL POPULATION EXTENSION under direction v68 ordered item (5): a further
cycle that repeats the D2 profile is ZERO DELTA and is recorded as OPERATIONAL,
not as evidence. This run discharges NO ordered item. (The instrument was first
authored under v67 item (1); that item is closed and is not re-opened here.)

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

Reachability per row is MEASURED from the bundle's own committed
``provenance.counter_evidence_span`` payload at the pinned product mount head
(applied / n_candidates / n_selected / abstained_ids / abstention_reasons /
content_filter / n_downgraded / downgraded_ids), published per bundle under
``population[].counter_evidence_span_provenance`` and aggregated in
``span_provenance_summary``; and ANNOTATED from accepted PATH_SCOPE_RESIDUAL
ARM2 (cycle 40070818687, accept d0d3c4a7a) which is cited, never re-run: the
accepted ARM2 finding established that the unmodified filter abstains
pivot_absent on the known offset-0 trilingual header when routed diagnostically.

SUPERSESSION (cycle 40246705199, direction v68): the pre-51d306c
``fixture_bypass_only`` reachability clause this instrument used to publish is
SUPERSEDED AS EXPLANATION. It is wrong at product head 3de8431d and later: the
span seam call is product/query/pipeline.py:1400-1407, gated only on
``if adversarial_retrieval:`` (in-code comment "Run even in fixture mode so the
shipped offline/slice path exercises the filter."), and the
``if not fixture_generation:`` at product/query/pipeline.py:1408 guards only
apply_counter_emission_repair. See
reports/evaluation/D2_REACHABILITY_CLAUSE_SUPERSESSION_OF_RECORD_40246705199.md
and reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md.

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

# The accepted-product mount may be re-pointed at a pinned product head with
# LEXMACHINA_PRODUCT_MOUNT (used to reproduce a pinned-head measurement without
# disturbing the shared /tmp/lex_accepted mount). The resolved path AND the
# resolved HEAD are both published in the artifact, so the measurement never
# becomes path- or head-ambiguous.
MOUNT = Path(os.environ.get("LEXMACHINA_PRODUCT_MOUNT")
             or "/tmp/lex_accepted/product")
PACKET_OF_RECORD = "39319405429"

# Optional reproducibility guard: when set (flag --expect-head or env
# LEXMACHINA_EXPECT_HEAD) the run refuses (exit 2, ENVIRONMENT_ERROR) instead of
# silently profiling a different population than the one the artifact names.
EXPECT_HEAD = os.environ.get("LEXMACHINA_EXPECT_HEAD") or None

# Controlling mounted control-plane direction for this run.
CONTROLLING_DIRECTION_VERSION = 68
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

# Corrected product code citations at the pinned head (independently verified
# by independent audit CYCLE_40246705199, R1). These REPLACE the pre-51d306c
# fixture-bypass clause; they are read from the product tree, never asserted.
PRODUCT_PATH_CITATIONS = {
    "span_seam_call": (
        "product/query/pipeline.py:1400-1407 - `if adversarial_retrieval:` -> "
        "apply_verified_span_selection, in-code comment \"Run even in fixture "
        "mode so the shipped offline/slice path exercises the filter.\""),
    "fixture_gate": (
        "product/query/pipeline.py:1408 - `if not fixture_generation:` guards "
        "apply_counter_emission_repair ONLY, never the span seam"),
    "rejection_incumbent_leg": (
        "product/query/counter_evidence_span.py:385-394 - direction v68 P0 "
        "rejection/incumbent leg (\"REPLACE it (direction v68 P0 "
        "rejection/incumbent leg)\")"),
    "correction_of_record": (
        "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"),
}

# House-supersession block, published in every artifact this instrument emits.
REACHABILITY_SUPERSESSION = {
    "status": "SUPERSEDED_AS_EXPLANATION",
    "superseded_clause_reference": (
        "the pre-51d306c fixture-bypass reachability clause that earlier runs of "
        "this instrument published as current state for slice-family D2 rows "
        "(the wording that blamed a fixture-only gate on the span seam)"),
    "superseded_clause_published_by": [
        "results/evaluation/d2_letterhead_pattern_profile/40089391202.json",
        "results/evaluation/d2_letterhead_pattern_profile/40094203248.json",
        "results/evaluation/d2_letterhead_pattern_profile/40096174340.json",
        "results/evaluation/d2_letterhead_pattern_profile/40099481633.json",
        "results/evaluation/d2_letterhead_pattern_profile/test_live_profile.json",
    ],
    "disposition": (
        "those five artifacts are NAMED RUN artifacts and are left byte-untouched "
        "per the binding F-3B disposition item 4 (a file named for run X holds "
        "run X's measurement; nothing is deleted from history). The clause they "
        "carry is superseded here and in the dedicated correction note rather "
        "than by editing them."),
    "superseding_note": (
        "reports/evaluation/D2_REACHABILITY_CLAUSE_SUPERSESSION_OF_RECORD_"
        "40246705199.md"),
    "correction_of_record": (
        "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"),
    "corrected_product_citations": PRODUCT_PATH_CITATIONS,
    "measurement_unchanged": (
        "supersession is provenance/mechanism only; every measurement number in "
        "this artifact is unchanged from the pinned-head measurement of record"),
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


def _span_provenance(mount: Path, relpath: str) -> dict | None:
    """Read ``provenance.counter_evidence_span`` from one committed bundle.

    This is the MEASURED seam reachability for that bundle's own bytes at the
    pinned product head. Returns ``None`` when the bundle carries no payload
    (a pre-seam artifact) - absence is reported as absence, never inferred.
    """
    p = mount / relpath
    if not p.is_file():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    prov = (doc.get("provenance") or {}).get("counter_evidence_span")
    if not isinstance(prov, dict):
        return None
    keep = ("applied", "mode", "n_candidates", "n_selected", "n_abstained",
            "abstained_ids", "abstention_reasons", "selected_ids",
            "downgraded_ids", "n_downgraded", "n_incumbent_downgraded",
            "retained_content_sound", "guard_available", "guard_phrase_count",
            "content_filter_applied", "content_filter_leg", "reason",
            "frozen_rules_sha256")
    out = {k: prov.get(k) for k in keep if k in prov}
    out["content_filter_present"] = "content_filter" in prov
    return out


def _span_state(prov: dict | None) -> str:
    if prov is None:
        return "span_provenance_absent"
    if prov.get("applied") is True:
        return "span_seam_applied"
    return "span_seam_ran_applied_false"


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


def _reachability_label(family: str, scope: str, prov: dict | None = None,
                        head: str | None = None) -> str:
    """Reachability label for one D2 row, MEASURED from that row's bundle.

    ``prov`` is the bundle's own committed provenance.counter_evidence_span
    payload at the pinned head (None = the bundle carries no payload, i.e. it
    predates the seam; that is reported as absence, never as a bypass claim).
    """
    if scope == "packet_of_record":
        return ("packet_of_record_served_bytes (frozen verified-row predicate "
                "population; production emission path, label only)")
    state = _span_state(prov)
    head_s = head or "unknown-head"
    arm2 = (" Per accepted PATH_SCOPE_RESIDUAL ARM2 (40070818687) the unmodified "
            "filter would ABSTAIN pivot_absent on the known offset-0 trilingual "
            "header if routed - cited, not re-run.")
    seam = (f" Seam call product/query/pipeline.py:1400-1407 is gated only on "
            f"`if adversarial_retrieval:` (\"Run even in fixture mode so the "
            f"shipped offline/slice path exercises the filter.\"); the "
            f"`if not fixture_generation:` at product/query/pipeline.py:1408 "
            f"guards apply_counter_emission_repair ONLY.")
    supers = (" The pre-51d306c fixture-bypass reachability clause is SUPERSEDED "
              "AS EXPLANATION (supersession block in this artifact; correction "
              "of record reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_"
              "RECORD_40105794124_v68.md).")
    if state == "span_seam_applied":
        bits = [f"applied=true", f"n_candidates={prov.get('n_candidates')}",
                f"n_selected={prov.get('n_selected')}"]
        if prov.get("abstained_ids"):
            bits.append(f"abstained_ids={prov.get('abstained_ids')}")
        if prov.get("abstention_reasons"):
            bits.append(f"abstention_reasons={prov.get('abstention_reasons')}")
        if prov.get("content_filter_present"):
            bits.append("content_filter=present")
            bits.append(f"n_downgraded={prov.get('n_downgraded')}")
            bits.append(f"downgraded_ids={prov.get('downgraded_ids')}")
        return (f"span_seam_applied MEASURED on this bundle at product head "
                f"{head_s}: provenance.counter_evidence_span {', '.join(bits)}."
                f"{seam}{supers}{arm2}")
    if state == "span_seam_ran_applied_false":
        return (f"span_seam_ran_applied_false MEASURED on this bundle at product "
                f"head {head_s}: provenance.counter_evidence_span applied=false, "
                f"n_candidates={prov.get('n_candidates')}, "
                f"n_selected={prov.get('n_selected')}"
                + (f", reason={prov.get('reason')}" if prov.get("reason") else "")
                + f", content_filter_present={prov.get('content_filter_present')}."
                f"{seam}{supers}{arm2}")
    return (f"span_provenance_absent MEASURED on this bundle at product head "
            f"{head_s}: no provenance.counter_evidence_span payload is committed "
            f"on these bytes, so seam reachability is NOT MEASURED here "
            f"(bundle predates the seam; absence is reported as absence, never "
            f"inferred as a bypass).{seam}{supers}{arm2}")


def run(run_id: str, out_dir: Path, report_dir: Path,
        expect_head: str | None = None,
        also_report: Path | None = None) -> tuple[int, dict]:
    t0 = time.time()
    controls: dict[str, dict] = {}
    mount_head = _mount_head()
    producing_commit = _producing_commit()
    expect_head = expect_head or EXPECT_HEAD

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

    # ---- head pin guard: never silently profile a different population -----
    if expect_head and not (mount_head or "").startswith(str(expect_head)):
        controls["ENV"] = {
            "control": "mount_head_matches_expected_pin", "passed": False,
            "expected": expect_head, "actual": mount_head,
            "detail": (f"mount {MOUNT} is at {mount_head}, not {expect_head}; "
                       f"refusing to publish a measurement for a population the "
                       f"artifact does not name")}
        rec = {"schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_ERROR",
               "product_mount": str(MOUNT), "product_mount_head": mount_head,
               "expected_head": expect_head, "controls": controls,
               "exit_code": 2,
               "generated_at_utc": datetime.now(timezone.utc).strftime(
                   "%Y-%m-%dT%H:%M:%SZ")}
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{run_id}.json").write_text(
            json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return 2, rec
    if expect_head:
        controls["C7"] = {
            "control": "C7_mount_head_pin",
            "expected": expect_head, "actual": mount_head,
            "passed": True,
            "note": "mount HEAD verified against the pinned product head before "
                    "population discovery, so a re-execution either reproduces "
                    "the named population or refuses loudly",
        }

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
    prov_by_bundle: dict[str, dict | None] = {}
    for b in population:
        stats, rows = _probe_verified_rows(MOUNT, b["bundle"])
        prov = _span_provenance(MOUNT, b["bundle"])
        prov_by_bundle[b["bundle"]] = prov
        rec_ = dict(b)
        rec_.update(stats or {})
        rec_["n_verified_with_defects"] = sum(1 for r in rows if r["defects"])
        rec_["span_state"] = _span_state(prov)
        rec_["counter_evidence_span_provenance"] = prov
        bundle_records.append(rec_)
        all_rows.extend(rows)

    # ---- MEASURED span-seam provenance over the whole named population -----
    from collections import Counter as _Counter
    span_state_counts = _Counter(_span_state(prov_by_bundle.get(b["bundle"]))
                                 for b in population)
    applied_bundles = [b["bundle"] for b in population
                       if _span_state(prov_by_bundle.get(b["bundle"]))
                       == "span_seam_applied"]
    rejection_leg_bundles = [b["bundle"] for b in population
                             if (prov_by_bundle.get(b["bundle"]) or {}).get(
                                 "content_filter_present")]
    abstained_ids: _Counter = _Counter()
    abstention_reasons: _Counter = _Counter()
    n_candidates_total = n_selected_total = n_downgraded_total = 0
    for b in population:
        prov = prov_by_bundle.get(b["bundle"])
        if not prov:
            continue
        n_candidates_total += int(prov.get("n_candidates") or 0)
        n_selected_total += int(prov.get("n_selected") or 0)
        n_downgraded_total += int(prov.get("n_downgraded") or 0)
        for i in prov.get("abstained_ids") or []:
            abstained_ids[str(i)] += 1
        for k, v in (prov.get("abstention_reasons") or {}).items():
            abstention_reasons[str(k)] += int(v or 0)
    span_provenance_summary = {
        "measurement": "provenance.counter_evidence_span read from each "
                       "committed bundle of the named population at the pinned "
                       "product head (MEASURED, not inferred)",
        "product_mount": str(MOUNT),
        "product_mount_head": mount_head,
        "n_bundles": len(population),
        "span_state_counts": dict(sorted(span_state_counts.items())),
        "n_bundles_with_span_provenance": sum(
            1 for b in population if prov_by_bundle.get(b["bundle"]) is not None),
        "n_bundles_span_seam_applied": len(applied_bundles),
        "n_bundles_span_seam_applied_false":
            span_state_counts.get("span_seam_ran_applied_false", 0),
        "n_bundles_span_provenance_absent":
            span_state_counts.get("span_provenance_absent", 0),
        "n_bundles_with_rejection_incumbent_leg_payload": len(
            rejection_leg_bundles),
        "rejection_incumbent_leg_bundles": rejection_leg_bundles,
        "n_candidates_total": n_candidates_total,
        "n_selected_total": n_selected_total,
        "n_downgraded_total": n_downgraded_total,
        "abstained_ids": dict(sorted(abstained_ids.items())),
        "abstention_reasons": dict(sorted(abstention_reasons.items())),
        "note": "counts are bundle-level provenance fields summed across the "
                "named population; they are descriptive seam telemetry, NOT a "
                "frozen-bar result and NOT a class-level repair verdict",
    }

    # ---- pattern inventory over D2 rows -------------------------------------
    patterns: dict[str, dict] = {}
    d2_rows = [r for r in all_rows if "D2_letterhead_zone" in r["defects"]]
    d2_span_states = _Counter()
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
        d2_span_states[_span_state(prov_by_bundle.get(r["bundle"]))] += 1
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
        p["reachability_labels"].add(
            _reachability_label(fam, scope, prov_by_bundle.get(r["bundle"]),
                                mount_head))

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
        "producing_commit": producing_commit,
        "producing_tree_clean": _producing_tree_clean(),
        "producing_commit_note": (
            "git rev-parse HEAD of this evaluation tree when the instrument "
            "executed, on a clean worktree; the artifact and this report are "
            "committed in the follow-up commit whose message names this run"),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction_version": _current_direction_version(),
        "controlling_direction_version": CONTROLLING_DIRECTION_VERSION,
        "direction_version_pin_note": (
            "state-level direction_version read at runtime; v68 is the "
            "CONTROLLING mounted control-plane direction for this run "
            "(factory_direction.json version 68)"),
        "scope_label": "OPERATIONAL_POPULATION_EXTENSION_NO_ORDERED_ITEM_DISCHARGED",
        "scope_statement": (
            "Direction v68 ordered item (5): a further cycle that repeats the D2 "
            "profile is ZERO DELTA and is recorded as OPERATIONAL, not as "
            "evidence. This run is an operational population extension: it "
            "discharges NO ordered item, scores no frozen bar, and publishes no "
            "product-facing repair requirement."),
        "ordered_item_status": {
            "item_1_report_only_correction_of_record": (
                "DISCHARGED_ELSEWHERE - accepted in the base tree as "
                "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_"
                "40105794124_v68.md; not re-derived here"),
            "item_2_conditional_remeasure": (
                "NOT_YET_DISCRIMINATING - the rejection/incumbent leg IS landed "
                "at the pinned head 3de8431d (product/query/counter_evidence_"
                "span.py:385-394 present; measured content_filter payload on "
                f"{len(rejection_leg_bundles)} bundles of this population), BUT "
                "the 15-bundle flagship family pinned in "
                "results/evaluation/counter_evidence_quality_benchmark/"
                "40062917685.json (all 20261023T2* dirs) has NOT been "
                "regenerated at a rejection-leg head - the newest slice dirs "
                "are single-query bundles - so the precondition is UNMET and no "
                "re-measure, synthetic stand-in or standing-falsification rerun "
                "is executed"),
            "item_3_standing_falsification_record": "KEPT, unchanged, not re-run",
            "item_4_report_only_nonblocking_fixes": "REPORTED only where quoted",
            "item_5_no_zero_delta_cycle": "APPLIED HERE - recorded as OPERATIONAL",
        },
        "product_mount": str(MOUNT),
        "product_mount_head": mount_head,
        "head_pin": {"expected": expect_head, "applied": bool(expect_head)},
        "packet_of_record": PACKET_OF_RECORD,
        "population_extension_disclosure": (
            "OPERATIONAL population extension under v68 ordered item (5): "
            "separate named run; discharges no ordered item; does NOT replace, "
            "re-baseline or move accepted baseline 40062917685; scores no "
            "frozen bar; edits nothing frozen."),
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
        "span_provenance_summary": span_provenance_summary,
        "d2_row_span_states": dict(sorted(d2_span_states.items())),
        "reachability_rule": (
            "slice-family reachability is MEASURED per bundle from the bundle's "
            "own committed provenance.counter_evidence_span payload at product "
            f"head {mount_head} and published under "
            "population[].counter_evidence_span_provenance plus "
            "span_provenance_summary (span_state_counts "
            f"{dict(sorted(span_state_counts.items()))}); the pre-51d306c "
            "fixture-bypass clause is SUPERSEDED AS EXPLANATION (see "
            "supersession block); ARM2 pivot_absent abstention is CITED from "
            "accepted cycle 40070818687 and NOT re-run"),
        "supersession": REACHABILITY_SUPERSESSION,
        "product_path_citations": PRODUCT_PATH_CITATIONS,
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
    if also_report is not None:
        # F-3B-safe second destination: the legacy cycle report name is written
        # with THIS run's stamped content (run id + producing commit) instead of
        # the run re-deriving it by re-using a non-run-id measurement filename.
        extra = Path(also_report)
        if not extra.is_absolute():
            extra = _REPO_ROOT / extra
        extra.parent.mkdir(parents=True, exist_ok=True)
        _write_report(extra, rec)
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


def _producing_commit() -> str | None:
    """HEAD of the evaluation tree the instrument is executing on."""
    import subprocess
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT,
            capture_output=True, text=True, timeout=15,
        ).stdout.strip() or None
    except Exception:
        return None


def _producing_tree_clean() -> bool | None:
    import subprocess
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"], cwd=_REPO_ROOT,
            capture_output=True, text=True, timeout=15,
        ).stdout
        return not out.strip()
    except Exception:
        return None


def _write_report(path: Path, rec: dict) -> None:
    ctl_summary = ", ".join(
        "{}={}".format(k, "PASS" if v.get("passed") else "FAIL")
        for k, v in rec["controls"].items())
    sps = rec.get("span_provenance_summary") or {}
    ois = rec.get("ordered_item_status") or {}
    lines = [
        f"# D2 Letterhead Pattern Heterogeneity Profile — {rec['run_id']}",
        "",
        f"- run_id: {rec['run_id']}",
        f"- producing commit: `{rec.get('producing_commit')}` "
        f"(clean worktree at execution: {rec.get('producing_tree_clean')}) — "
        f"the tree the instrument ran on; this report and "
        f"`results/evaluation/d2_letterhead_pattern_profile/{rec['run_id']}.json` "
        f"are committed in the follow-up commit whose message names run "
        f"{rec['run_id']}",
        f"- direction_version: {rec['direction_version']} — v68 is the "
        f"CONTROLLING mounted control-plane direction; scope = "
        f"**{rec.get('scope_label')}** (v68 ordered item (5): a further cycle "
        f"that repeats the D2 profile is zero delta and is recorded as "
        f"OPERATIONAL, not as evidence) — accepted baseline 40062917685 UNMOVED",
        f"- product mount: `{rec['product_mount']}` head `{rec['product_mount_head']}`",
        f"- packet-of-record: {rec['packet_of_record']} (labelled; "
        f"verified rows under frozen predicate: {rec['n_verified_rows_packet_of_record']})",
        f"- verdict: **{rec['verdict']}** (exit {rec['exit_code']})",
        f"- controls: {'ALL PASS' if rec['controls_all_pass'] else 'FAILED'} "
        f"({ctl_summary})",
        "",
        "## Ordered-item status (direction v68)",
        "",
        f"- item (1) report-only correction of record: {ois.get('item_1_report_only_correction_of_record')}",
        f"- item (2) conditional re-measure: **{ois.get('item_2_conditional_remeasure', '').split(' - ')[0]}** — "
        f"{ois.get('item_2_conditional_remeasure', '').split(' - ', 1)[-1]}",
        f"- item (3) standing falsification record: {ois.get('item_3_standing_falsification_record')}",
        f"- item (5) no zero-delta cycle: {ois.get('item_5_no_zero_delta_cycle')}",
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
            f"- reachability (MEASURED): {p['reachability_labels']}",
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
        "## Measured span-seam provenance (per bundle, at the pinned head)",
        "",
        f"- product head: `{sps.get('product_mount_head')}`",
        f"- bundles: {sps.get('n_bundles')} — span_state_counts: "
        f"`{sps.get('span_state_counts')}`",
        f"- bundles with a committed provenance.counter_evidence_span payload: "
        f"{sps.get('n_bundles_with_span_provenance')} "
        f"(applied=true {sps.get('n_bundles_span_seam_applied')}, "
        f"applied=false {sps.get('n_bundles_span_seam_applied_false')}, "
        f"absent {sps.get('n_bundles_span_provenance_absent')})",
        f"- bundles carrying the v68 rejection/incumbent-leg payload "
        f"(content_filter present): "
        f"{sps.get('n_bundles_with_rejection_incumbent_leg_payload')}",
        f"- summed provenance counters: n_candidates="
        f"{sps.get('n_candidates_total')}, n_selected={sps.get('n_selected_total')}, "
        f"n_downgraded={sps.get('n_downgraded_total')}",
        f"- abstained_ids: `{sps.get('abstained_ids')}`; abstention_reasons: "
        f"`{sps.get('abstention_reasons')}`",
        f"- D2 profiled rows by span state: `{rec.get('d2_row_span_states')}`",
        f"- scope caveat: {sps.get('note')}",
        "",
        "## Supersession of the pre-51d306c reachability clause",
        "",
        f"- status: **{rec['supersession']['status']}**",
        f"- superseded clause (by reference): "
        f"{rec['supersession']['superseded_clause_reference']}",
        f"- published by (left byte-untouched, F-3B disposition item 4): "
        + ", ".join(f"`{p}`" for p in rec["supersession"]["superseded_clause_published_by"]),
        f"- disposition: {rec['supersession']['disposition']}",
        f"- superseding note: `{rec['supersession']['superseding_note']}`",
        f"- correction of record: `{rec['supersession']['correction_of_record']}`",
    ]
    for k, v in rec["product_path_citations"].items():
        lines.append(f"- product citation ({k}): {v}")
    lines += [
        f"- measurement unchanged: {rec['supersession']['measurement_unchanged']}",
        "",
        "## Feasibility reading for Core Product (descriptive, claim ceiling)",
        "",
    ]
    if rec["verdict"] == "LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED":
        lines.append(
            "All observed D2 letterhead forms fall into the mechanically "
            "detectable classes (P1/P2). On this named population the "
            "deterministic letterhead-filter branch remains mechanically "
            "viable. Reachability is MEASURED on these very bytes, not assumed: "
            f"{sps.get('n_bundles_span_seam_applied')} of {sps.get('n_bundles')} "
            "bundles carry provenance.counter_evidence_span.applied=true and "
            f"{sps.get('n_bundles_with_rejection_incumbent_leg_payload')} carry "
            "the rejection/incumbent-leg payload, so the pre-51d306c "
            "fixture-bypass clause is SUPERSEDED as explanation (supersession "
            "section above). The ARM2 abstention finding (pivot_absent on the "
            "known offset-0 trilingual header when routed) still binds the "
            "filter's own detector. This lane asserts no repair requirement of "
            "its own: rejection/incumbent handling is Core Product's ordered "
            "work under direction v68, and ordered item (2) stays "
            "NOT_YET_DISCRIMINATING until the pinned 15-bundle flagship family "
            "is regenerated at a rejection-leg head.")
    else:
        lines.append(
            "At least one P3 (heterogeneous-beyond-mechanical) letterhead form "
            "was observed; under v68 this profile is recorded as an OPERATIONAL "
            "population extension (item (5)), published as a bounded-negative "
            "observation rather than as a defect count. See "
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
    ap.add_argument("--expect-head", default=None,
                    help="refuse (exit 2) unless the mount HEAD starts with this "
                         "sha; keeps a re-execution on the named population")
    ap.add_argument("--also-report", default=None,
                    help="additionally write the report to this path (repo "
                         "relative or absolute); used to keep the legacy cycle "
                         "report name stamped without re-using a non-run-id "
                         "measurement filename")
    args = ap.parse_args(argv)
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID") or (
        "local_eval_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out_dir = Path(args.out_dir) if args.out_dir else (
        _REPO_ROOT / "results" / "evaluation" / "d2_letterhead_pattern_profile")
    report_dir = Path(args.report_dir) if args.report_dir else (
        _REPO_ROOT / "reports" / "evaluation")
    code, rec = run(run_id, out_dir, report_dir,
                    expect_head=args.expect_head,
                    also_report=args.also_report)
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
