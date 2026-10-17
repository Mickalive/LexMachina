#!/usr/bin/env python3
"""Can the frozen geometry gate's regression semantics be re-grounded on a
lineage-stable property, or must it be re-scoped to served_lineage only?

Why this exists
---------------
Direction v50 gave this lane the two frozen-bar gates. Cycle 38993062549 then
FALSIFIED the incumbent-count regression semantics as packet admission: the
verdict is anchor-determined (F5) -- re-pointing the frozen predicate
'regressed iff count < anchor count' at each of the three in-scope packets
produces three different verdict sets over one immutable population. The
accepted state names exactly one successor question (state/evaluation.json
next_recommendation item (3)):

    decide whether the regression semantics can be re-grounded on a
    lineage-stable property (criterion-level pass vectors, or
    degradation-monotone criteria such as fr STRUCTURE_LARGEST) or whether
    the gate must be re-scoped to served_lineage only.

This module answers that, executably, over the same accepted population.

Candidate semantics (frozen in
results/evaluation/reground_semantics/FROZEN_HYPOTHESIS_38996043415.json at
commit 9392ff8b, BEFORE this module was executed):

  S1  clean-prefix cell regression -- a cell fires when the packet fails it
      and EVERY earlier packet in the objective lineage order passed it.
      The reference is the WHOLE prefix, never one build. No anchor exists.
  S2  monotone-degradation endpoint -- a static-scalar-bar cell fires when
      its numeric values move strictly in the frozen degrading direction
      across the lineage AND the endpoint crosses the frozen bar. Direction
      is PARSED from the frozen RULES_GEOMETRY bar string, never invented.
  S3  served-lineage membership -- the re-scope fallback: an identity test
      against the shas the accepted GEOMETRY_HALF.json measured. Makes no
      degradation claim.

REUSE-FIRST (no scoring re-implemented)
---------------------------------------
* Both RULES files are re-hashed to the accepted sha256 before anything runs.
* Per-cell masks and values come from the ACCEPTED engine
  `geometry_gate.score_packet` (the same function the gate calls), via the
  accepted `packet_lineage_sweep.criterion_mask` helper. No criterion, bar,
  threshold or pass predicate is re-derived.
* The negative control is the ACCEPTED `run_bar_gates._hostile_geometry`,
  imported by value so it stays byte-identical to the gate's own control.
* S2's inequality direction is read from the frozen RULES_GEOMETRY bar
  strings; no numeric constant is introduced.

Exit codes (frozen)
-------------------
0  REGROUNDABLE     -- R1-R4 all hold; a lineage-stable regression property
                       exists and the verdict names which semantics provides it.
1  MUST_RESCOPE     -- at least one of R1-R4 failed; first-class negative
                       result about the gate's expressiveness. The gate may
                       only state served-lineage membership (S3).
2  ENVIRONMENT_OR_UNPROVEN -- rules sha drift, empty population, engine
                       environment failure, or the no-new-threshold check (R5)
                       found an implementation bug. NOT a product verdict;
                       suppresses every finding.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.frozen_bars import geometry_gate  # noqa: E402
from evaluation.packet_lineage_sweep import (  # noqa: E402
    INCUMBENT_PACKET_ID,
    PRODUCT_MOUNT,
    PACKET_ROOT_REL,
    QIDS,
    criterion_mask,
    discover_packets,
    verify_rules_identity,
)

EXIT_REGROUNDABLE = 0
EXIT_MUST_RESCOPE = 1
EXIT_ENVIRONMENT = 2

# S2 applies ONLY to criteria with a STATIC scalar frozen bar (a constant
# yardstick shared by every packet). Dynamic-baseline and compound-bar
# criteria are excluded by the frozen hypothesis; the exclusion is a design
# choice, not an oversight, and is asserted in the tests.
S2_STATIC_BAR_CRITERIA = (
    "PROJ_RANK",
    "PROJ_SPEARMAN",
    "PROJ_KNN10",
    "STRUCTURE_LARGEST",
    "STRUCTURE_SEP",
    "LABEL_CONTENT_FRACTION",
    "LABEL_JACCARD",
)
S2_EXCLUDED_BY_DESIGN = {
    "COHERENCE_QUERY_LANG": "dynamic bar max(0.25, 0.5*baseline): baseline moves per packet",
    "COHERENCE_QUERY_TERM": "dynamic bar = bundle baseline: baseline moves per packet",
    "OUTLIER_VALIDITY": "compound predicate, no single scalar value/bar",
    "RELATIONS": "compound predicate, no single scalar value/bar",
}

# R5 static scan: no numeric literal may be compared against a criterion
# value as a bar inside this module. The only numeric literals allowed are
# structural (0, 1, 2 for indexing / k>=1). The scan looks for the classic
# threshold-writing shapes.
_THRESHOLD_SHAPE = re.compile(
    r"(value|vals?|v_\w+|score|metric)\s*(<=|>=|<|>)\s*"
    r"(\d+\.\d+|\d+)(?!\s*# structural)",
)


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------- lineage ordering --
def read_generated_at(mount: Path, packet_id: str) -> dict:
    """Objective temporal ground truth from the packet's own packet.json."""
    p = mount / PACKET_ROOT_REL / packet_id / "packet.json"
    if not p.exists():
        return {"present": False, "generated_at": None, "path": str(p)}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"present": True, "generated_at": None,
                "error": f"{type(e).__name__}: {e}", "path": str(p)}
    return {"present": True, "generated_at": d.get("generated_at"), "path": str(p)}


def lineage_order(mount: Path, in_scope_ids: list[str]) -> dict:
    """Order by generated_at (primary) and by packet-id sort (cross-check).

    R1 requires the two to be IDENTICAL. A disagreement is a finding, not a
    silent tiebreak: lineage order is the objective grounding that replaces
    the discarded anchor choice.
    """
    meta = {pid: read_generated_at(mount, pid) for pid in in_scope_ids}
    missing = [p for p, m in meta.items() if not m.get("generated_at")]
    if missing:
        return {"ok": False, "missing_generated_at": missing, "meta": meta}
    by_time = [p for p, _ in sorted(
        ((p, meta[p]["generated_at"]) for p in in_scope_ids),
        key=lambda kv: (kv[1], kv[0]))]
    by_id = sorted(in_scope_ids)
    return {
        "ok": True,
        "meta": meta,
        "order_by_generated_at": by_time,
        "order_by_packet_id": by_id,
        "orders_identical": by_time == by_id,
        "generated_at_values": {p: meta[p]["generated_at"] for p in in_scope_ids},
    }


# ------------------------------------------------- S2 direction parsing --
def parse_bar_direction(rules: dict, criterion: str) -> dict:
    """Read the inequality direction from the frozen RULES_GEOMETRY bar string.

    '>= X'  -> higher is better, so DECREASING is degrading (down_degrading).
    '<= X' or '< X' -> lower is better, so INCREASING is degrading
    (up_degrading).
    Returns None when no single inequality can be parsed (compound bar).
    No threshold value is extracted or used: only the direction.
    """
    entry = (rules.get("criteria") or {}).get(criterion) or {}
    bar = str(entry.get("bar") or "")
    # A compound bar joins two clauses with AND; a dynamic bar references a
    # per-packet baseline. Either disqualifies the criterion for S2.
    if " AND " in bar or "baseline" in bar.lower():
        return {"applicable": False, "bar": bar,
                "reason": "compound or dynamic bar; no single static inequality"}
    if ">=" in bar:
        return {"applicable": True, "bar": bar, "direction": "down_degrading"}
    if "<=" in bar or "<" in bar:
        return {"applicable": True, "bar": bar, "direction": "up_degrading"}
    return {"applicable": False, "bar": bar, "reason": "no parseable inequality"}


def s2_applicable_criteria(rules: dict) -> dict:
    """Which criteria S2 covers, computed FROM the frozen rubric, not assumed."""
    out = {}
    for c in geometry_gate.CRITERIA_ORDER:
        parsed = parse_bar_direction(rules, c)
        out[c] = parsed
    applicable = [c for c, p in out.items() if p.get("applicable")]
    return {"per_criterion": out, "applicable": applicable,
            "excluded": {c: p for c, p in out.items() if not p.get("applicable")}}


# ------------------------------------------------------ candidate scoring --
def score_lineage(masks: dict, values: dict, order: list[str],
                  qids: tuple[str, ...] | None = None) -> dict:
    """Apply S1, S1-immediate-prior and S2 to a lineage.

    masks:   {packet_id: {qid: {criterion: bool_pass}}}
    values:  {packet_id: {qid: {criterion: numeric_value_or_none}}}
    order:   lineage order, earliest first.
    qids:    which query ids to iterate; defaults to the three frozen qids.
             Tests pass a single synthetic qid to pin the predicate in
             isolation; production always uses the frozen set.
    """
    crit_all = geometry_gate.CRITERIA_ORDER
    qid_set = tuple(qids) if qids else tuple(QIDS)
    s1_fired: list[dict] = []
    s1ip_fired: list[dict] = []
    s2_fired: list[dict] = []
    s2_na_cells: list[dict] = []

    # Direction map is computed once from the frozen rules by the caller and
    # passed via the closure of s2_applicable; here we only need the map.
    # The caller sets score_lineage.direction_map before invoking.
    direction_map: dict = getattr(score_lineage, "direction_map", {})

    for i, pid in enumerate(order):
        for q in qid_set:
            for c in crit_all:
                p_now = bool(masks[pid][q][c])
                # ---- S1: clean-prefix reference (whole prefix, no anchor)
                if i == 0:
                    prefix_all_pass = False  # empty prefix: never fires
                else:
                    prefix_all_pass = all(bool(masks[order[j]][q][c])
                                          for j in range(i))
                if (not p_now) and i >= 1 and prefix_all_pass:
                    s1_fired.append({"packet_id": pid, "qid": q, "criterion": c,
                                     "position": i, "value": values[pid][q][c]})
                # ---- S1-IP control: single-build (immediate-prior) reference
                if i >= 1 and (not p_now) and bool(masks[order[i - 1]][q][c]):
                    s1ip_fired.append({"packet_id": pid, "qid": q, "criterion": c,
                                       "position": i, "value": values[pid][q][c]})
                # ---- S2: monotone-degradation endpoint
                direction = direction_map.get(c)
                if direction is None:
                    s2_na_cells.append({"packet_id": pid, "qid": q, "criterion": c,
                                        "reason": "criterion not S2-applicable"})
                    continue
                seq = [values[order[j]][q][c] for j in range(i + 1)]
                if any(not isinstance(v, (int, float)) for v in seq):
                    s2_na_cells.append({"packet_id": pid, "qid": q, "criterion": c,
                                        "reason": "non-numeric value in sequence"})
                    continue
                if i < 1:
                    continue  # need >= 2 observations
                strict = all(
                    (seq[k + 1] > seq[k] if direction == "up_degrading"
                     else seq[k + 1] < seq[k])
                    for k in range(len(seq) - 1)
                )
                if strict and (not p_now):
                    # Descriptive subclassification (NOT a new predicate or
                    # threshold): did any EARLIER packet in the prefix ever
                    # pass this cell? If yes, the monotone trend crossed the
                    # bar from a passing state = a true crossing regression.
                    # If no, the cell never passed and the trend is a worsening
                    # of an already-failing property = a trend warning. Both
                    # are reported; the semantics' fired-set is unchanged.
                    ever_passed_before = any(bool(masks[order[j]][q][c])
                                             for j in range(i))
                    s2_fired.append({"packet_id": pid, "qid": q, "criterion": c,
                                     "position": i, "sequence": seq,
                                     "direction": direction,
                                     "value": values[pid][q][c],
                                     "subclass": ("crossing_regression"
                                                  if ever_passed_before
                                                  else "worsening_while_always_failing"),
                                     "ever_passed_in_prefix": ever_passed_before})

    def _key(e):
        return (e["packet_id"], e["qid"], e["criterion"])

    return {
        "S1_clean_prefix": {
            "fired": sorted(s1_fired, key=_key),
            "fired_keys": sorted({_key(e) for e in s1_fired}),
            "n_fired": len({_key(e) for e in s1_fired}),
            "firing_packets": sorted({e["packet_id"] for e in s1_fired}),
        },
        "S1_immediate_prior_CONTROL": {
            "fired": sorted(s1ip_fired, key=_key),
            "fired_keys": sorted({_key(e) for e in s1ip_fired}),
            "n_fired": len({_key(e) for e in s1ip_fired}),
            "differs_from_S1": sorted({_key(e) for e in s1ip_fired})
                               != sorted({_key(e) for e in s1_fired}),
        },
        "S2_monotone": {
            "fired": sorted(s2_fired, key=_key),
            "fired_keys": sorted({_key(e) for e in s2_fired}),
            "n_fired": len({_key(e) for e in s2_fired}),
            "firing_packets": sorted({e["packet_id"] for e in s2_fired}),
            "n_not_applicable_cells": len(s2_na_cells),
            "subclass_split": {
                "crossing_regression": sorted(
                    {_key(e) for e in s2_fired
                     if e.get("subclass") == "crossing_regression"}),
                "worsening_while_always_failing": sorted(
                    {_key(e) for e in s2_fired
                     if e.get("subclass") == "worsening_while_always_failing"}),
            },
            "subclass_note": (
                "descriptive only: crossing_regression = the monotone trend "
                "crossed the frozen bar from a previously-passing state (a "
                "true regression); worsening_while_always_failing = the cell "
                "never passed anywhere in the observed prefix and its value "
                "degraded monotonically while remaining failing (a trend "
                "warning, not a pass-to-fail transition). No predicate, "
                "threshold or verdict changes under this label."),
        },
        "union_fired_keys": sorted(
            {_key(e) for e in s1_fired} | {_key(e) for e in s2_fired}),
    }


# ------------------------------------------------ old semantics (contrast) --
def old_anchor_contrast(per_counts: dict, order: list[str]) -> dict:
    """F5 reproduction: the frozen count predicate re-pointed at each anchor.

    'regressed iff per-bundle count < anchor count', exactly as the accepted
    sweep computed it. REPORTED only; the incumbent itself is never re-pointed.
    """
    anchors = {}
    for anchor in order:
        ac = per_counts[anchor]
        regressed = []
        for pid in order:
            c = per_counts[pid]
            below = [q for q in QIDS if c[q] < ac[q]]
            if below:
                regressed.append({"packet_id": pid, "qids_below_anchor": below})
        anchors[anchor] = {
            "anchor_counts": ac,
            "marked_regressed": [r["packet_id"] for r in regressed],
            "includes_itself": anchor in {r["packet_id"] for r in regressed},
        }
    distinct = len({tuple(v["marked_regressed"]) for v in anchors.values()})
    return {
        "anchors": anchors,
        "n_distinct_verdict_sets": distinct,
        "verdict_set_is_anchor_determined": distinct > 1,
        "F5_reproduced": distinct >= 2,
    }


# --------------------------------------------------------------- R5 check --
def r5_no_new_threshold(module_path: Path) -> dict:
    """Static scan: no numeric literal may be written as a bar against a value.

    This catches an implementation bug that would silently invent a threshold.
    A failure is classified ENVIRONMENT (voids the run), never MUST_RESCOPE.
    """
    src = module_path.read_text(encoding="utf-8")
    offenders = []
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""'):
            continue
        m = _THRESHOLD_SHAPE.search(line)
        if m:
            offenders.append({"line": i, "text": stripped[:160]})
    return {
        "scanned": str(module_path),
        "n_offending_lines": len(offenders),
        "offenders": offenders,
        "holds": len(offenders) == 0,
        "note": ("the scan is a guard against an implementation bug, not a "
                 "claim about the design; the frozen bars themselves contain "
                 "thresholds and are read, never written, by this module"),
    }


# -------------------------------------------------------------------- main --
def run(run_id: str, mount: Path = PRODUCT_MOUNT,
        out_path: Path | None = None) -> tuple[int, dict]:
    t0 = time.time()

    rules_id = verify_rules_identity(mount)
    if not rules_id["all_match"]:
        rec = {"schema": "lex-evaluation-reground-semantics/1", "run_id": run_id,
               "verdict": "ENVIRONMENT_OR_UNPROVEN",
               "detail": "frozen RULES sha mismatch; refusing every statement",
               "rules_identity": rules_id}
        return EXIT_ENVIRONMENT, _finish(rec, out_path, t0)

    discovery = discover_packets(mount)
    in_scope = [p for p in discovery["packets"] if p["in_scope"]]
    if not in_scope:
        rec = {"schema": "lex-evaluation-reground-semantics/1", "run_id": run_id,
               "verdict": "ENVIRONMENT_OR_UNPROVEN",
               "detail": "no in-scope packet on the mount; empty population is not evidence",
               "discovery": discovery}
        return EXIT_ENVIRONMENT, _finish(rec, out_path, t0)

    in_scope_ids = sorted(p["packet_id"] for p in in_scope)
    order_info = lineage_order(mount, in_scope_ids)
    if not order_info["ok"]:
        rec = {"schema": "lex-evaluation-reground-semantics/1", "run_id": run_id,
               "verdict": "ENVIRONMENT_OR_UNPROVEN",
               "detail": "objective lineage order unavailable; no order, no semantics",
               "lineage_order": order_info}
        return EXIT_ENVIRONMENT, _finish(rec, out_path, t0)
    order = order_info["order_by_generated_at"]

    rules = geometry_gate.load_frozen_geometry_rules()
    s2_cov = s2_applicable_criteria(rules)
    direction_map = {c: s2_cov["per_criterion"][c]["direction"]
                     for c in s2_cov["applicable"]}
    # attach for score_lineage (kept as an attribute to keep the signature
    # stable for the tests, which call score_lineage directly)
    score_lineage.direction_map = direction_map

    masks: dict = {}
    values: dict = {}
    per_counts: dict = {}
    for pid in in_scope_ids:
        m = criterion_mask(mount, pid)
        masks[pid] = m["mask"]
        values[pid] = m["values"]
        per_counts[pid] = m["per_bundle_counts"]

    base = score_lineage(masks, values, order)

    # ---- hostile-geometry extension (R4 / N3): served packet corrupted and
    # appended as a FOURTH newest member. The corruption is the ACCEPTED
    # control imported by value; the re-measurement uses the ACCEPTED engine.
    ext_order = order + ["__hostile__"]
    ext_masks = dict(masks)
    ext_values = dict(values)
    hostile_detail: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        from evaluation.frozen_bars.run_bar_gates import _hostile_geometry

        qdir = mount / PACKET_ROOT_REL / INCUMBENT_PACKET_ID / "questions"
        hostile_bundles = {}
        for q in QIDS:
            b = json.loads((qdir / f"{q}.bundle.json").read_text(encoding="utf-8"))
            hostile_bundles[q] = _hostile_geometry(b)
        # score the hostile packet through the accepted engine (same path the
        # gate itself uses) so no scoring is re-implemented here
        lang_by_qid = {e.get("bundle"): e.get("query_language")
                       for e in rules.get("inputs", [])}
        lexicons = rules.get("query_term_lexicons", {})
        h_masks: dict = {q: {} for q in QIDS}
        h_values: dict = {q: {} for q in QIDS}
        for q in QIDS:
            V, _detail = geometry_gate.score_bundle(
                hostile_bundles[q], lang_by_qid[q], lexicons[q])
            h_masks[q] = {c: bool(V[c]["pass"]) for c in geometry_gate.CRITERIA_ORDER}
            h_values[q] = {c: V[c].get("value") for c in geometry_gate.CRITERIA_ORDER}
        ext_masks["__hostile__"] = h_masks
        ext_values["__hostile__"] = h_values
        hostile_detail = {
            "control": "evaluation.frozen_bars.run_bar_gates._hostile_geometry (accepted, imported by value)",
            "re_measured_through": "evaluation.frozen_bars.geometry_gate.score_bundle (accepted engine)",
            "hostile_pass_counts": {q: sum(1 for c in geometry_gate.CRITERIA_ORDER
                                           if h_masks[q][c]) for q in QIDS},
        }

    extended = score_lineage(ext_masks, ext_values, ext_order)

    # ---- old-semantics contrast (R2 / N4)
    old = old_anchor_contrast(per_counts, order)

    # ---- R1 order grounding
    r1 = {
        "orders_identical": order_info["orders_identical"],
        "order_by_generated_at": order_info["order_by_generated_at"],
        "order_by_packet_id": order_info["order_by_packet_id"],
        "generated_at_values": order_info["generated_at_values"],
        "verdict_sets_single_valued": True,  # S1/S2 have no anchor parameter
        "holds": bool(order_info["orders_identical"]),
    }

    # ---- R2 anchor freedom
    s1_keys = base["S1_clean_prefix"]["fired_keys"]
    s2_keys = base["S2_monotone"]["fired_keys"]
    s1ip_keys = base["S1_immediate_prior_CONTROL"]["fired_keys"]
    ext_s1_keys = extended["S1_clean_prefix"]["fired_keys"]
    ext_s1ip_keys = extended["S1_immediate_prior_CONTROL"]["fired_keys"]
    r2 = {
        "old_semantics_F5_reproduced": old["F5_reproduced"],
        "old_n_distinct_verdict_sets": old["n_distinct_verdict_sets"],
        "S1_n_verdict_sets": 1,  # structural: no anchor parameter exists
        "S2_n_verdict_sets": 1,
        "S1_vs_S1_immediate_prior_on_real_population": {
            "S1": s1_keys, "S1_immediate_prior": s1ip_keys,
            "differ": s1_keys != s1ip_keys},
        "S1_vs_S1_immediate_prior_on_hostile_extension": {
            "S1_extended": ext_s1_keys,
            "S1_immediate_prior_extended": ext_s1ip_keys,
            "differ": ext_s1_keys != ext_s1ip_keys},
        "whole_prefix_reference_load_bearing": (s1_keys != s1ip_keys)
                                               or (ext_s1_keys != ext_s1ip_keys),
        "holds": bool(old["F5_reproduced"]),
        "disclosure": (
            "the S1-immediate-prior control is computed on both the real "
            "population and the hostile extension; if the two S1 variants "
            "coincide everywhere, R2 still holds on the structural + F5-"
            "contrast argument and the coincidence is disclosed as a "
            "limitation of this population's power"),
    }

    # ---- R3 real degradation detection (against the ACCEPTED F3 cells)
    expected_f3 = [
        (order[-1], "de-kapitalverletzung", "PROJ_RANK"),
        (order[1], "fr-bail-entretien", "STRUCTURE_LARGEST")
        if len(order) > 1 else None,
    ]
    expected_f3 = [e for e in expected_f3 if e]
    union_keys = set(base["union_fired_keys"])
    found = {e: (e in union_keys) for e in expected_f3}
    r3 = {
        "expected_accepted_F3_degradations": [list(e) for e in expected_f3],
        "found": {str(e): v for e, v in found.items()},
        "holds": all(found.values()) if found else False,
    }

    # ---- R4 non-vacuity: hostile extension fires strictly more than the
    # uncorrupted served packet alone
    served_keys = {k for k in (set(ext_s1_keys) | set(
        extended["S2_monotone"]["fired_keys"])) if k[0] == INCUMBENT_PACKET_ID}
    hostile_keys = {k for k in (set(ext_s1_keys) | set(
        extended["S2_monotone"]["fired_keys"])) if k[0] == "__hostile__"}
    r4 = {
        "served_packet_fired_keys": sorted(served_keys),
        "hostile_extension_fired_keys": sorted(hostile_keys),
        "hostile_fires_new_cells": bool(hostile_keys - served_keys),
        "new_cells": sorted(hostile_keys - served_keys),
        "holds": bool(hostile_keys - served_keys),
        **hostile_detail,
    }

    # ---- R5 no new threshold
    r5 = r5_no_new_threshold(Path(__file__))

    # ---- battery N1-N5
    battery = {
        "N1_at_least_one_real_fire": {
            "holds": bool(base["union_fired_keys"]),
            "union_fired_keys": base["union_fired_keys"]},
        "N2_not_indiscriminate": {
            "holds": len({k[0] for k in base["union_fired_keys"]}) < len(order),
            "firing_packets": sorted({k[0] for k in base["union_fired_keys"]}),
            "n_in_scope": len(order)},
        "N3_hostile_detects_new": {"holds": r4["holds"],
                                   "new_cells": r4["new_cells"]},
        "N4_old_F5_reproduced": {"holds": old["F5_reproduced"],
                                 "n_distinct": old["n_distinct_verdict_sets"]},
        "N5_rules_identity": {"holds": rules_id["all_match"]},
    }
    battery["all_hold"] = all(v["holds"] for v in battery.values()
                              if isinstance(v, dict))

    # ---- verdict
    if not r5["holds"]:
        verdict = "ENVIRONMENT_OR_UNPROVEN"
        detail = ("R5 no-new-threshold static scan found an offending line; "
                  "this is an implementation bug, not evidence, and voids "
                  "every finding")
        code = EXIT_ENVIRONMENT
    elif not battery["all_hold"]:
        verdict = "ENVIRONMENT_OR_UNPROVEN"
        detail = "non-vacuity battery incomplete; every predicate statement is void"
        code = EXIT_ENVIRONMENT
    elif r1["holds"] and r2["holds"] and r3["holds"] and r4["holds"]:
        verdict = "REGROUNDABLE"
        detail = ("a lineage-stable regression property exists over the frozen "
                  "bars; see which semantics regrounded below")
        code = EXIT_REGROUNDABLE
    else:
        verdict = "MUST_RESCOPE"
        failed = [name for name, r in (("R1", r1), ("R2", r2),
                                       ("R3", r3), ("R4", r4)) if not r["holds"]]
        detail = (f"failed requirements: {failed}; the gate must be re-scoped "
                  "to served_lineage membership only (S3)")
        code = EXIT_MUST_RESCOPE

    # which semantics regrounded (only meaningful on REGROUNDABLE)
    regrounded = []
    if verdict == "REGROUNDABLE":
        if base["S1_clean_prefix"]["n_fired"] > 0:
            regrounded.append("S1_clean_prefix_cell_regression")
        if base["S2_monotone"]["n_fired"] > 0:
            regrounded.append("S2_monotone_degradation_endpoint")
        if not regrounded:
            regrounded.append("STRUCTURAL_ONLY (R1-R4 hold but neither "
                              "semantics fired on the real population)")

    rec = {
        "schema": "lex-evaluation-reground-semantics/1",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verdict": verdict,
        "detail": detail,
        "exit_code": code,
        "regrounded_semantics": regrounded,
        "claim_ceiling": (
            "Tests the GATE's regression SEMANTICS, not the CANDIDATE. Decides "
            "only whether a lineage-stable regression property exists over the "
            "frozen bars. Does NOT re-measure either Frontier candidate, does "
            "NOT touch either frozen bar, does NOT meet the absolute bars, "
            "does NOT change any exit-code contract or packet-admission "
            "wiring, and says nothing about jurist usefulness."),
        "rules_identity": rules_id,
        "population": {
            "root": discovery["root"],
            "n_in_scope": len(in_scope),
            "in_scope_packet_ids": in_scope_ids,
            "out_of_scope": [
                {"packet_id": p["packet_id"], "reason": p["out_of_scope_reason"]}
                for p in discovery["packets"] if not p["in_scope"]],
            "lineage_order": order,
        },
        "lineage_order_grounding": order_info,
        "S2_coverage_from_frozen_rubric": s2_cov,
        "real_population_scoring": base,
        "hostile_extension_scoring": extended,
        "old_semantics_contrast": old,
        "R1_order_grounding": r1,
        "R2_anchor_freedom": r2,
        "R3_real_degradation_detection": r3,
        "R4_non_vacuity_hostile": r4,
        "R5_no_new_threshold": r5,
        "non_vacuity_battery": battery,
    }
    return code, _finish(rec, out_path, t0)


def _finish(rec: dict, out_path: Path | None, t0: float) -> dict:
    rec["elapsed_s"] = round(time.time() - t0, 3)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", default="adhoc")
    ap.add_argument("--mount", default=str(PRODUCT_MOUNT))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    code, rec = run(args.run_id, Path(args.mount),
                    Path(args.out) if args.out else None)
    brief = {k: v for k, v in rec.items()
             if k not in ("real_population_scoring", "hostile_extension_scoring",
                          "non_vacuity_battery", "lineage_order_grounding",
                          "S2_coverage_from_frozen_rubric")}
    print(json.dumps(brief, indent=1, default=str))
    print(f"VERDICT {rec['verdict']} exit={code} regrounded={rec.get('regrounded_semantics')}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
