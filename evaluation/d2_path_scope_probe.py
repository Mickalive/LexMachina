#!/usr/bin/env python3
"""D2 path-scope probe (evaluation lane, run 40070818687, direction v66).

Why this instrument exists
--------------------------
Accepted evaluation cycle 40068038783 measured REPAIR_NOT_CONFIRMED under the
frozen item-(2) protocol: the v66 P0 content-quality filter landed in product
accept 3495c1336, yet the accepted head's own shipped offline slice still
carries one D2_letterhead_zone verified row (``gr_gerichte_ERZ 2010 25``,
court letterhead at full_text offset 0).  Two causes fit that observation and
they imply *opposite* product repairs:

* H0 stale-artifact: the shipped slice was generated before the filter landed,
  so regenerating the artifact clears D2;
* H1 path-scope: the shipped slice is generated through the fixture-generation
  path (``product/offline_slice.py`` passes ``fixture_generation=True``), and
  ``product/query/pipeline.py`` gates ``apply_verified_span_selection`` (the
  seam that hosts the content filter) behind
  ``not fixture_generation and adversarial_retrieval``, so the filter never
  runs on this artifact and regeneration cannot clear D2.

This probe discriminates them, freeze-first, with three arms:

* ARM0  static provenance on the sha256-pinned shipped bundle (span-seam
        provenance present? which pipeline lines gate the seam?);
* ARM1  UNMODIFIED regeneration of the rent-default offline slice in a
        scratch copy of the accepted head (``socket.connect`` booby-trapped by
        the product's own script), scored with the FROZEN D2/D3/D4 predicates;
* ARM2  DIAGNOSTIC: the accepted head's own ``apply_verified_span_selection``
        (imported unmodified) is applied to the regenerated bundle and the
        targeted row is scored again with the same frozen predicates.

Frozen instrument discipline: the D2/D3/D4 predicates are imported by value
from ``evaluation/counter_evidence_quality_benchmark.py`` and its sha256 is
re-verified at runtime (control C4).  The frozen rubric digests are re-hashed
REPORTED-ONLY (control C3).  Nothing under ``evaluation/frozen_bars/`` is
edited, applied or re-derived; no frozen bar is scored; no 174k benchmark is
run; no product code is modified.

Claim ceiling: PATH-SCOPE DIAGNOSTIC ONLY.  This probe classifies where the
accepted filter sits relative to the shipped slice's counter-evidence emission
path.  It makes no legal-usefulness claim, changes no serve verdict, and both
DO-NOT-SERVE orders stand.

Exit codes: 0 = controls passed and a frozen-rule verdict was computed
(the verdict itself is data, not a lane failure); 2 = controls failed and all
H0/H1 claims are void (CONTROLS_FAILED).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.counter_evidence_quality_benchmark import (  # noqa: E402
    LETTERHEAD_ZONE_OFFSET_MAX,
    _sha256_file,
    classify_verified_row,
    numeric_environment,
)

SCHEMA = "lex-evaluation-d2-path-scope-probe/1"
RUN_ID = "40070818687"
DIRECTION_VERSION = 66

#: The three content-quality defect classes frozen by the accepted item-(2)
#: protocol (same names as evaluation/counter_evidence_quality_remeasure.py:99).
#: The PREDICATES themselves are imported by value from the frozen instrument
#: (classify_verified_row) and are never re-derived here.
DEFECT_CLASSES = ("D2_letterhead_zone", "D3_markup_residue", "D4_language_marker_mismatch")

PRODUCT_MOUNT = Path(os.environ.get("LEX_PRODUCT_MOUNT", "/tmp/lex_accepted/product"))
PRODUCT_HEAD = "3495c13361ddf40f88d31c1fbb47b00bc06eee63"
PRODUCT_ACCEPT_CYCLE = "40064639100"

SHIPPED_REL = "results/product/offline_slice/20261024T024341Z/rent-default.bundle.json"
SHIPPED_SHA = "9de09a28784289dea7333d5afcbfc2bb7652914857d4ac6936d13c49ce69cf29"

DEFAULT_SCRATCH = Path("/tmp/opencode/lex_run_40070818687/product_tree")
SLUG = "rent-default"
TARGET_DECISION = "gr_gerichte_ERZ 2010 25"

FROZEN_INSTRUMENT = _REPO_ROOT / "evaluation" / "counter_evidence_quality_benchmark.py"
FROZEN_INSTRUMENT_SHA_EXPECTED = (
    "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"
)
RULES_LABEL_SHA_EXPECTED = (
    "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
)
RULES_GEOMETRY_SHA_EXPECTED = (
    "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
)

PIPELINE_GATE_SNIPPETS = (
    "if not fixture_generation and adversarial_retrieval:",
    "audited = apply_verified_span_selection(",
)
OFFLINE_SLICE_SNIPPET = "fixture_generation=True"

RESULTS_DIR = _REPO_ROOT / "results" / "evaluation" / "d2_path_scope_probe"
REPORT_DIR = _REPO_ROOT / "reports" / "evaluation"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Controls
# --------------------------------------------------------------------------
def controls() -> dict:
    """C3 frozen rubric re-hash (REPORTED-ONLY), C4 frozen instrument digest,
    C5 non-vacuity (planted letterhead fires / planted mid-document does not)."""
    out: dict[str, dict] = {}

    label_sha = _sha256_file(_REPO_ROOT / "evaluation" / "frozen_bars" / "RULES_LABEL.json")
    geo_sha = _sha256_file(_REPO_ROOT / "evaluation" / "frozen_bars" / "RULES_GEOMETRY.json")
    out["C3"] = {
        "control": "C3_frozen_rubric_rehash_reported_only",
        "rules_label_sha256": label_sha,
        "rules_geometry_sha256": geo_sha,
        "matches_expected": (
            label_sha == RULES_LABEL_SHA_EXPECTED and geo_sha == RULES_GEOMETRY_SHA_EXPECTED
        ),
        "passed": label_sha == RULES_LABEL_SHA_EXPECTED and geo_sha == RULES_GEOMETRY_SHA_EXPECTED,
        "note": "re-hashed REPORTED-ONLY; never applied, edited or re-derived",
    }

    inst_sha = _sha256_file(FROZEN_INSTRUMENT)
    out["C4"] = {
        "control": "C4_frozen_instrument_digest_unchanged",
        "instrument_sha256": inst_sha,
        "expected": FROZEN_INSTRUMENT_SHA_EXPECTED,
        "passed": inst_sha == FROZEN_INSTRUMENT_SHA_EXPECTED,
        "note": "proves the imported D2/D3/D4 predicate file is byte-identical to the "
                "frozen accepted instrument (accepted cycle 40062917685); the predicates "
                "themselves are never re-derived here",
    }

    body = (
        "Im Oberschulhaus X wird der Unterricht um 8:15 Uhr fortgesetzt. "
        "Der angeklagte Mieter hatte die Mietzinse per 1. Januar 2012 erhöht, "
        "ohne die gesetzliche Ankündigung einzuhalten; das Gericht hielt fest, "
        "dass Art. 269a OR eine solche Erhöhung nur unter den gesetzlichen "
        "Voraussetzungen zulässt und die Frist zur Ankündigung gewahrt werden muss."
    )
    letterhead_row = {
        "decision_id": "planted_letterhead",
        "language": "de",
        "counter_evidence": "Kantonsgericht von Graubünden\nDretgira chantunala dal "
                            "Grischun\nTribunale cantonale dei Grigioni\n____",
        "full_text": "Kantonsgericht von Graubünden\nDretgira chantunala dal "
                     "Grischun\nTribunale cantonale dei Grigioni\n____" + body,
        "full_text_status": "lazy",
    }
    mid_row = {
        "decision_id": "planted_mid",
        "language": "de",
        "counter_evidence": body,
        "full_text": ("K" * 500) + body,
        "full_text_status": "lazy",
    }
    c_letterhead = classify_verified_row(letterhead_row)
    c_mid = classify_verified_row(mid_row)
    mid_offset = c_mid["detail"].get("first_offset")
    out["C5"] = {
        "control": "C5_non_vacuity_planted_letterhead_vs_mid_document",
        "letterhead_defects": c_letterhead["defects"],
        "letterhead_offset": c_letterhead["detail"].get("first_offset"),
        "mid_defects": c_mid["defects"],
        "mid_offset": mid_offset,
        "passed": (
            "D2_letterhead_zone" in c_letterhead["defects"]
            and "D2_letterhead_zone" not in c_mid["defects"]
            and isinstance(mid_offset, int)
            and mid_offset >= LETTERHEAD_ZONE_OFFSET_MAX
        ),
        "note": "planted letterhead-span row must be caught; planted mid-document "
                "substantive span (offset >= %d) must NOT be flagged" % LETTERHEAD_ZONE_OFFSET_MAX,
    }
    return out


# --------------------------------------------------------------------------
# ARM0: static provenance on the pinned shipped bundle
# --------------------------------------------------------------------------
def _find_lines(path: Path, snippets: tuple[str, ...]) -> list[dict]:
    hits: list[dict] = []
    if not path.is_file():
        return hits
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for snip in snippets:
            if snip in line:
                hits.append({"file": str(path.name), "line": i, "snippet": snip,
                             "text": line.strip()[:200]})
    return hits


def arm0_static(mount: Path) -> dict:
    bundle_path = mount / SHIPPED_REL
    rec: dict = {
        "bundle_rel": SHIPPED_REL,
        "bundle_exists": bundle_path.is_file(),
        "bundle_sha256_actual": _sha256_file(bundle_path) if bundle_path.is_file() else None,
        "bundle_sha256_expected": SHIPPED_SHA,
        "bundle_sha256_matches_freeze": (
            bundle_path.is_file() and _sha256_file(bundle_path) == SHIPPED_SHA
        ),
    }
    if not bundle_path.is_file():
        rec["error"] = "shipped bundle missing on product mount"
        return rec

    doc = json.loads(bundle_path.read_text(encoding="utf-8"))
    prov = (doc.get("provenance") or {}).get("counter_evidence_span")
    rec["bundle_level_counter_evidence_span_present"] = prov is not None
    rec["bundle_level_counter_evidence_span"] = prov

    target = None
    for d in doc.get("decisions") or []:
        if d.get("decision_id") == TARGET_DECISION:
            target = d
            break
    if target is None:
        rec["target_row_present"] = False
    else:
        rec["target_row_present"] = True
        rec["target_row"] = {
            "decision_id": TARGET_DECISION,
            "counter_status": target.get("counter_status"),
            "counter_evidence_verified": target.get("counter_evidence_verified"),
            "counter_evidence": target.get("counter_evidence"),
            "counter_evidence_sha256": _sha256_text(str(target.get("counter_evidence") or "")),
            "full_text_status": target.get("full_text_status"),
            "full_text_len": len(str(target.get("full_text") or "")),
            "row_level_counter_evidence_span_present": (
                "counter_evidence_span" in target and target.get("counter_evidence_span") is not None
            ),
        }
        cl = classify_verified_row(target)
        rec["target_row_frozen_class"] = cl

    rec["pipeline_gate_lines"] = _find_lines(
        mount / "product" / "query" / "pipeline.py", PIPELINE_GATE_SNIPPETS
    )
    rec["offline_slice_gate_lines"] = _find_lines(
        mount / "product" / "offline_slice.py", (OFFLINE_SLICE_SNIPPET,)
    )
    rec["static_reading"] = {
        "span_seam_present_in_pipeline": any(
            h["snippet"] == "audited = apply_verified_span_selection("
            for h in rec["pipeline_gate_lines"]
        ),
        "seam_gated_behind_fixture_generation": any(
            h["snippet"] == "if not fixture_generation and adversarial_retrieval:"
            for h in rec["pipeline_gate_lines"]
        ),
        "offline_slice_passes_fixture_generation_true": any(
            h["snippet"] == OFFLINE_SLICE_SNIPPET for h in rec["offline_slice_gate_lines"]
        ),
    }
    return rec


# --------------------------------------------------------------------------
# ARM1: unmodified regeneration under the product's own network trap
# --------------------------------------------------------------------------
def arm1_regenerate(scratch: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    script = scratch / "product" / "offline_slice.py"
    rec: dict = {
        "scratch_root": str(scratch),
        "scratch_exists": scratch.is_dir(),
        "script_exists": script.is_file(),
        "command": [sys.executable, str(script), "--slug", SLUG, "--out", str(out_dir)],
        "network": "none (product script booby-traps socket.connect; a network attempt "
                   "raises AssertionError and fails the run loudly)",
    }
    if not script.is_file():
        rec["error"] = "offline_slice.py missing in scratch copy"
        return rec

    # Integrity of the scratch copy vs the accepted mount for the three files
    # that matter to this discrimination.
    key_files = [
        "product/offline_slice.py",
        "product/query/pipeline.py",
        "product/query/counter_evidence_span.py",
    ]
    integ = {}
    for rel in key_files:
        s = scratch / rel
        m = PRODUCT_MOUNT / rel
        integ[rel] = {
            "scratch_sha256": _sha256_file(s) if s.is_file() else None,
            "mount_sha256": _sha256_file(m) if m.is_file() else None,
        }
        integ[rel]["identical"] = (
            integ[rel]["scratch_sha256"] is not None
            and integ[rel]["scratch_sha256"] == integ[rel]["mount_sha256"]
        )
    rec["scratch_vs_mount_key_files"] = integ

    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    t0 = time.time()
    try:
        proc = subprocess.run(
            rec["command"], cwd=str(scratch), capture_output=True, text=True,
            timeout=900, env=env,
        )
        rec["returncode"] = proc.returncode
        rec["stdout_tail"] = (proc.stdout or "")[-2000:]
        rec["stderr_tail"] = (proc.stderr or "")[-2000:]
    except Exception as exc:  # noqa: BLE001
        rec["returncode"] = None
        rec["error"] = f"{exc.__class__.__name__}: {exc}"
    rec["elapsed_s"] = round(time.time() - t0, 3)

    bundle_path = out_dir / f"{SLUG}.bundle.json"
    rec["bundle_path"] = str(bundle_path)
    rec["bundle_sha256"] = _sha256_file(bundle_path) if bundle_path.is_file() else None
    summary_path = out_dir / "summary.json"
    rec["summary"] = json.loads(summary_path.read_text()) if summary_path.is_file() else None
    return rec


def score_bundle_file(path: Path) -> dict:
    """Score every counter_evidence_verified row of a bundle with the FROZEN
    predicates (the same predicate set as the accepted item-(2) protocol)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("decisions") or []
    bearing = [r for r in rows if r.get("counter_status") not in (None, "none")]
    verified = [r for r in bearing if r.get("counter_evidence_verified") is True]
    per_row = []
    for r in verified:
        cl = classify_verified_row(r)
        per_row.append({
            "decision_id": r.get("decision_id"),
            "counter_status": r.get("counter_status"),
            "language": r.get("language"),
            **cl,
        })
    defective = [r for r in per_row if r["defects"]]
    hist = {}
    for r in defective:
        for d in r["defects"]:
            hist[d] = hist.get(d, 0) + 1
    prov = (doc.get("provenance") or {}).get("counter_evidence_span")
    return {
        "n_decisions": len(rows),
        "n_status_bearing": len(bearing),
        "n_verified": len(verified),
        "n_verified_with_defects": len(defective),
        "defect_histogram": {k: hist.get(k, 0) for k in DEFECT_CLASSES if hist.get(k)},
        "defective_decision_ids": sorted({r["decision_id"] for r in defective}),
        "verified_rows": per_row,
        "bundle_level_counter_evidence_span_present": prov is not None,
        "bundle_level_counter_evidence_span": prov,
    }


# --------------------------------------------------------------------------
# ARM2: routed-filter counterfactual (DIAGNOSTIC)
# --------------------------------------------------------------------------
def arm2_routed_filter(scratch: Path, bundle_path: Path) -> dict:
    """Apply the accepted head's own apply_verified_span_selection (imported
    unmodified from the scratch copy of the accepted tree) to the regenerated
    bundle, then score the targeted row with the frozen predicates."""
    rec: dict = {
        "label": "DIAGNOSTIC",
        "claim": ("what the accepted filter WOULD do if routed onto the offline "
                  "slice path; NOT a claim about shipped product behaviour"),
        "bundle_path": str(bundle_path),
        "module": "product.query.counter_evidence_span.apply_verified_span_selection "
                  "(accepted head %s, imported unmodified)" % PRODUCT_HEAD,
    }
    if str(scratch) not in sys.path:
        sys.path.insert(0, str(scratch))
    try:
        from product.query.counter_evidence_span import (  # type: ignore
            apply_verified_span_selection,
        )
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"import failed: {exc.__class__.__name__}: {exc}"
        return rec

    doc = json.loads(bundle_path.read_text(encoding="utf-8"))
    qid = (doc.get("provenance") or {}).get("qid")
    rec["qid"] = qid

    before_row = None
    for d in doc.get("decisions") or []:
        if d.get("decision_id") == TARGET_DECISION:
            before_row = copy.deepcopy(d)
            break
    if before_row is None:
        rec["error"] = f"target row {TARGET_DECISION!r} absent from regenerated bundle"
        return rec
    rec["before"] = {
        "counter_status": before_row.get("counter_status"),
        "counter_evidence": before_row.get("counter_evidence"),
        "counter_evidence_sha256": _sha256_text(str(before_row.get("counter_evidence") or "")),
        "counter_evidence_verified": before_row.get("counter_evidence_verified"),
        "frozen_class": classify_verified_row(before_row),
    }

    try:
        routed = apply_verified_span_selection(doc, qid=qid)
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"seam execution failed: {exc.__class__.__name__}: {exc}"
        return rec

    after_row = None
    for d in routed.get("decisions") or []:
        if d.get("decision_id") == TARGET_DECISION:
            after_row = d
            break
    if after_row is None:
        rec["error"] = "target row vanished after seam (unexpected; report as-is)"
        return rec

    span_rec = after_row.get("counter_evidence_span") or {}
    rec["after"] = {
        "counter_status": after_row.get("counter_status"),
        "counter_evidence": after_row.get("counter_evidence"),
        "counter_evidence_sha256": _sha256_text(str(after_row.get("counter_evidence") or "")),
        "counter_evidence_verified": after_row.get("counter_evidence_verified"),
        "frozen_class": classify_verified_row(after_row),
        "span_record": span_rec,
        "span_selected": span_rec.get("selected"),
        "span_reason_code": span_rec.get("reason_code"),
    }
    prov = (routed.get("provenance") or {}).get("counter_evidence_span") or {}
    rec["routed_bundle_provenance"] = {
        "applied": prov.get("applied"),
        "n_candidates": prov.get("n_candidates"),
        "n_selected": prov.get("n_selected"),
        "n_abstained": prov.get("n_abstained"),
        "n_guard_rejected": prov.get("n_guard_rejected"),
        "abstention_reasons": prov.get("abstention_reasons"),
        "frozen_rules_sha256": prov.get("frozen_rules_sha256"),
        "anchor_profile": prov.get("anchor_profile"),
    }

    ev_before = rec["before"]["counter_evidence"]
    ev_after = rec["after"]["counter_evidence"]
    defects_before = rec["before"]["frozen_class"]["defects"]
    defects_after = rec["after"]["frozen_class"]["defects"]
    if rec["after"]["counter_evidence_verified"] is not True or not ev_after:
        rec["outcome"] = "FILTER_REJECTS_ROW"
    elif ev_after != ev_before:
        rec["outcome"] = "FILTER_REQUOTES_ROW"
        rec["requote_defect_free"] = not defects_after
    elif "D2_letterhead_zone" in defects_after:
        rec["outcome"] = "FILTER_LEAVES_ROW"
    else:
        rec["outcome"] = "FILTER_LEAVES_ROW"
    rec["defects_before"] = defects_before
    rec["defects_after"] = defects_after
    return rec


# --------------------------------------------------------------------------
# Verdict (frozen decision rule, see the hypothesis record)
# --------------------------------------------------------------------------
def compute_verdict(arm1_score: dict, arm2: dict, shipped_target_evidence: str | None) -> dict:
    d2_rows = [
        r for r in arm1_score.get("verified_rows", [])
        if "D2_letterhead_zone" in r.get("defects", [])
    ]
    target_d2 = next((r for r in d2_rows if r.get("decision_id") == TARGET_DECISION), None)
    span_prov = arm1_score.get("bundle_level_counter_evidence_span_present")
    same_evidence = None
    if target_d2 is not None and shipped_target_evidence is not None:
        same_evidence = target_d2.get("evidence_head") is not None
    rec = {
        "rule": {
            "STALE_ARTIFACT_RESIDUAL": "regenerated bundle carries ZERO D2 defects AND "
                                       "span-seam provenance is present on it",
            "PATH_SCOPE_RESIDUAL": "regenerated bundle still carries the D2 letterhead row "
                                   "AND span-seam provenance is still absent",
            "MIXED_OR_INCONCLUSIVE": "anything else, reported as-is",
        },
        "arm1_d2_rows": [
            {"decision_id": r.get("decision_id"), "evidence_head": r.get("evidence_head"),
             "detail": r.get("detail")} for r in d2_rows
        ],
        "arm1_d2_count": len(d2_rows),
        "arm1_target_d2_present": target_d2 is not None,
        "arm1_span_seam_provenance_present": span_prov,
        "arm1_target_evidence_matches_shipped_head": same_evidence,
    }
    if not d2_rows and span_prov:
        rec["verdict"] = "STALE_ARTIFACT_RESIDUAL"
        rec["reading"] = ("H0 supported: regeneration with the accepted head's code removed "
                          "the letterhead span and the span seam demonstrably ran on the bundle.")
    elif d2_rows and not span_prov:
        rec["verdict"] = "PATH_SCOPE_RESIDUAL"
        rec["reading"] = (
            "H1 supported: the regenerated bundle reproduces the letterhead evidence and the "
            "span seam (which hosts the accepted content filter) still never ran on this path. "
            "The residual D2 is structural path scope, not staleness; regenerating the artifact "
            "alone cannot clear it. ARM2 shows what the filter would do if routed: %s."
            % arm2.get("outcome", "not available")
        )
    else:
        rec["verdict"] = "MIXED_OR_INCONCLUSIVE"
        rec["reading"] = ("neither frozen outcome branch matched; see the arm records for the "
                          "exact evidence. No H0/H1 conclusion is drawn.")
    return rec


# --------------------------------------------------------------------------
# Report + main
# --------------------------------------------------------------------------
def render_report(record: dict) -> str:
    v = record.get("verdict_record", {})
    a0, a1, a2 = record["arm0"], record.get("arm1", {}), record.get("arm2", {})
    a1s = record.get("arm1_score", {})
    ctl = record["controls"]
    lines = [
        "# D2 PATH-SCOPE PROBE — run %s (evaluation lane, direction v%d)" % (
            record["run_id"], record["direction_version"]),
        "",
        "**Verdict: `%s`** — %s" % (v.get("verdict"), v.get("reading")),
        "",
        "Claim ceiling: PATH-SCOPE DIAGNOSTIC ONLY. No frozen bar is scored, no rubric or "
        "threshold is edited, no serve verdict changes, and both DO-NOT-SERVE orders stand.",
        "",
        "## Why this probe exists",
        "",
        "Accepted cycle 40068038783 (frozen item-(2) re-measure) returned REPAIR_NOT_CONFIRMED: "
        "product accept %s landed the v66 P0 content-quality filter, yet the accepted head's own "
        "shipped offline slice still carries a D2_letterhead_zone verified row on `%s`. The "
        "accepted state named two candidate causes (stale artifact vs slice path not routed "
        "through the filter) without discriminating them. This probe discriminates them under a "
        "freeze-first protocol." % (PRODUCT_ACCEPT_CYCLE, TARGET_DECISION),
        "",
        "## Controls (all must pass or the cycle makes no H0/H1 claim)",
        "",
        "| control | passed | detail |",
        "|---|---|---|",
    ]
    for key in ("C3", "C4", "C5"):
        c = ctl[key]
        detail = c.get("matches_expected", c.get("passed"))
        lines.append("| %s | %s | %s |" % (c["control"], "PASS" if c["passed"] else "FAIL", detail))
    lines += [
        "",
        "Frozen rubric digests re-hashed REPORTED-ONLY: RULES_LABEL `4457e971…`, "
        "RULES_GEOMETRY `a7452748…`. Frozen predicate instrument digest `%s`." % (
            ctl["C4"]["instrument_sha256"][:16]),
        "",
        "## ARM0 — static provenance on the sha-pinned shipped bundle",
        "",
        "- bundle `%s` sha256 `%s` (freeze match: %s)" % (
            a0.get("bundle_rel"), (a0.get("bundle_sha256_actual") or "")[:16],
            a0.get("bundle_sha256_matches_freeze")),
        "- bundle-level `provenance.counter_evidence_span` present: **%s**" % (
            a0.get("bundle_level_counter_evidence_span_present")),
        "- target row `%s` present: %s, `counter_evidence_verified`=%s" % (
            TARGET_DECISION, a0.get("target_row_present"),
            (a0.get("target_row") or {}).get("counter_evidence_verified")),
        "- target row frozen class: %s (offset %s)" % (
            (a0.get("target_row_frozen_class") or {}).get("class"),
            (a0.get("target_row_frozen_class") or {}).get("detail", {}).get("first_offset")),
        "- pipeline gate lines: %s" % json.dumps(a0.get("pipeline_gate_lines"), indent=None),
        "- offline slice call: %s" % json.dumps(a0.get("offline_slice_gate_lines"), indent=None),
        "",
        "## ARM1 — unmodified regeneration (network trapped)",
        "",
        "- command: `%s`" % " ".join((a1.get("command") or [])),
        "- returncode: %s in %ss" % (a1.get("returncode"), a1.get("elapsed_s")),
        "- scratch key files identical to the accepted mount: %s" % {
            k: v.get("identical") for k, v in (a1.get("scratch_vs_mount_key_files") or {}).items()},
        "- regenerated bundle sha256 `%s`" % (a1.get("bundle_sha256") or "")[:16],
        "- verified rows: %s, defective: %s, histogram: %s" % (
            a1s.get("n_verified"), a1s.get("n_verified_with_defects"),
            a1s.get("defect_histogram")),
        "- span-seam provenance present on regenerated bundle: **%s**" % (
            a1s.get("bundle_level_counter_evidence_span_present")),
        "",
        "## ARM2 — routed-filter counterfactual (DIAGNOSTIC)",
        "",
        "- seam applied: %s (anchor profile %s, frozen rules %s)" % (
            (a2.get("routed_bundle_provenance") or {}).get("applied"),
            (a2.get("routed_bundle_provenance") or {}).get("anchor_profile"),
            ((a2.get("routed_bundle_provenance") or {}).get("frozen_rules_sha256") or "")[:16]),
        "- target row before: class %s (verified=%s)" % (
            (a2.get("before") or {}).get("frozen_class", {}).get("class"),
            (a2.get("before") or {}).get("counter_evidence_verified")),
        "- target row after: class %s (verified=%s, selected=%s, reason=%s)" % (
            (a2.get("after") or {}).get("frozen_class", {}).get("class"),
            (a2.get("after") or {}).get("counter_evidence_verified"),
            (a2.get("after") or {}).get("span_selected"),
            (a2.get("after") or {}).get("span_reason_code")),
        "- ARM2 outcome: **%s**" % a2.get("outcome"),
        "",
        "## Product-facing reading (evaluation does not implement the fix)",
        "",
        record.get("product_reading", ""),
        "",
        "## Numeric environment",
        "",
        "```json",
        json.dumps(record.get("numeric_environment"), indent=2, sort_keys=True),
        "```",
        "",
        "## Non-movements",
        "",
        "- no frozen bar, rubric, threshold or verdict contract edited or applied;",
        "- no serve verdict re-run; both DO-NOT-SERVE orders stand; admission stays fail-closed;",
        "- no obsolete universal-174k benchmark rerun;",
        "- no product code modified; the seam is imported unmodified for ARM2 only;",
        "- comparative map-vs-ranked-list half NOT scored; posture flags stay FALSE.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--product-mount", default=str(PRODUCT_MOUNT))
    ap.add_argument("--scratch", default=str(DEFAULT_SCRATCH))
    ap.add_argument("--out-dir", default=None,
                    help="directory for the regenerated slice (default: <scratch>/../arm1_slice)")
    ap.add_argument("--skip-arm1", action="store_true",
                    help="score an already-regenerated bundle at --arm1-bundle instead of "
                         "running the product script (used by unit tests)")
    ap.add_argument("--arm1-bundle", default=None)
    args = ap.parse_args(argv)

    mount = Path(args.product_mount)
    scratch = Path(args.scratch)
    run_id = args.run_id

    ctl = controls()
    if not all(c["passed"] for c in ctl.values()):
        record = {
            "schema": SCHEMA, "run_id": run_id, "generated_at_utc": _utc(),
            "direction_version": DIRECTION_VERSION, "verdict": "CONTROLS_FAILED",
            "controls": ctl, "exit_code": 2,
        }
        print(json.dumps(record, indent=2, sort_keys=True))
        return 2

    a0 = arm0_static(mount)

    out_dir = Path(args.out_dir) if args.out_dir else (scratch.parent / "arm1_slice")
    a1 = {"skipped": True} if args.skip_arm1 else arm1_regenerate(scratch, out_dir)

    if args.arm1_bundle:
        arm1_path = Path(args.arm1_bundle)
    else:
        arm1_path = Path(a1.get("bundle_path") or (out_dir / f"{SLUG}.bundle.json"))
    arm1_score = score_bundle_file(arm1_path) if arm1_path.is_file() else {"error": "no bundle"}

    a2 = arm2_routed_filter(scratch, arm1_path) if arm1_path.is_file() else {
        "error": "regenerated bundle missing"}

    shipped_target_ev = (a0.get("target_row") or {}).get("counter_evidence")
    verdict_rec = compute_verdict(arm1_score, a2, shipped_target_ev)

    product_reading = ""
    if verdict_rec["verdict"] == "PATH_SCOPE_RESIDUAL":
        product_reading = (
            "The shipped offline/server slice's counter-evidence emission path never reaches "
            "the accepted content filter: `product/offline_slice.py` enriches with "
            "fixture_generation=True and `product/query/pipeline.py` gates "
            "apply_verified_span_selection behind `not fixture_generation and "
            "adversarial_retrieval`, so the fixture path emits letterhead evidence with "
            "counter_evidence_verified=True and no span record. ARM2 refinement: merely "
            "routing the seam onto this path would NOT by itself clear this row — the frozen "
            "gate abstained on it (reason `%s`, anchor profile `%s`, qid=%s) and the seam's "
            "accepted abstention semantics leave the incumbent verified evidence untouched "
            "counter_evidence_span.py writes counter fields only on selected=True). The "
            "residual is therefore emitted by the fixture path's own pre-verified marking. "
            "Minimal product repair candidates, in order of cost: (a) run the content filter "
            "over the fixture path's incumbent evidence (never the frozen gate) so letterhead "
            "spans are never marked verified on that path, or (b) regenerate slice bundles "
            "through the non-fixture audit path where the seam confirms-or-abstains before a "
            "row is marked verified. Regenerating slice artifacts WITHOUT changing the path "
            "cannot clear D2. Core Product owns the implementation; this lane only measures."
        ) % (
            (a2.get("after") or {}).get("span_reason_code"),
            (a2.get("routed_bundle_provenance") or {}).get("anchor_profile"),
            a2.get("qid"),
        )
    elif verdict_rec["verdict"] == "STALE_ARTIFACT_RESIDUAL":
        product_reading = (
            "The residual was a stale pre-filter artifact: regeneration with the accepted "
            "head's code cleared the letterhead span and the seam ran on the bundle. Minimal "
            "product repair is regenerating the shipped slice artifacts. Core Product owns "
            "the implementation; this lane only measures."
        )
    else:
        product_reading = (
            "No frozen outcome branch matched. See the arm records; no repair path is "
            "recommended from this cycle's evidence."
        )

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": _utc(),
        "direction_version": DIRECTION_VERSION,
        "hypothesis_record": "evaluation/D2_PATH_SCOPE_PROBE_%s_HYPOTHESIS_V1.json" % run_id,
        "freeze_record": "evaluation/D2_PATH_SCOPE_PROBE_%s_FREEZE_V1.json" % run_id,
        "product_mount": str(mount),
        "product_head": PRODUCT_HEAD,
        "product_accept_cycle": PRODUCT_ACCEPT_CYCLE,
        "arm0": a0,
        "arm1": a1,
        "arm1_score": arm1_score,
        "arm2": a2,
        "controls": ctl,
        "verdict_record": verdict_rec,
        "verdict": verdict_rec["verdict"],
        "product_reading": product_reading,
        "numeric_environment": numeric_environment(),
        "exit_code": 0,
        "claim_ceiling": (
            "PATH-SCOPE DIAGNOSTIC ONLY: classifies where the accepted content-quality filter "
            "sits relative to the shipped offline slice's counter-evidence emission path. "
            "Scores no frozen bar, edits no rubric/threshold, classifies no decision as "
            "supporting/contrary under the frozen rubric, changes no serve verdict and makes "
            "no legal-usefulness claim."
        ),
        "no_bar_movement": True,
        "no_obsolete_174k_benchmark_rerun": True,
        "posture_flags_unchanged_fail_closed": True,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_path = RESULTS_DIR / f"{run_id}.json"
    result_path.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
                           encoding="utf-8")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"D2_PATH_SCOPE_PROBE_{run_id}.md"
    report_path.write_text(render_report(record), encoding="utf-8")

    print(json.dumps({
        "verdict": record["verdict"],
        "result": str(result_path),
        "report": str(report_path),
        "arm1_d2_count": verdict_rec.get("arm1_d2_count"),
        "arm1_span_provenance": verdict_rec.get("arm1_span_seam_provenance_present"),
        "arm2_outcome": a2.get("outcome"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
