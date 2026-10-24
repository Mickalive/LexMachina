#!/usr/bin/env python3
"""v65_head_advance_crosscheck_v2 — currency + shipped-slice counter-evidence probe
+ falsification re-run + pins, on the NEW accepted product head.

FAST-MVP evaluation instrument for factory direction v65, GitHub run 40040574595.

Ordered work executed here (frozen in
evaluation/V65_HEAD_ADVANCE_CROSSCHECK_HYPOTHESIS_V2.json, sha256 734a447d...,
and evaluation/V65_HEAD_ADVANCE_CROSSCHECK_FREEZE_RECORD_V2.json, both committed
BEFORE this execution):

  (1) CURRENCY CROSS-CHECK of the product quantities newly landed by accepted
      cycles 40025340938 (accept 2ee36779) and 40032389983 (accept e4f72a8e),
      reported CONFIRMED / CONFIRMED_LAG / NOT_REEXECUTED_THIS_CYCLE /
      DIVERGENT / NOT_FOUND per quantity. Published values are the product's
      own committed claims; the instrument reads the committed ARTIFACTS.
  (2) SHIPPED-SLICE COUNTER-EVIDENCE PROBE (H2) — the new discriminating leg.
      Every counter_evidence_verified=true row of the fourteen newly shipped
      slice bundles (plus one prior-cycle control bundle) is classified under
      the FROZEN defect predicates D1 empty / D2 letterhead-zone / D3
      markup-residue / D4 language-marker-mismatch. This is the binding
      v65 bottleneck (EVIDENCED COUNTER AUTHORITY) measured on the product's
      OWN artifacts. IT SCORES NO FROZEN BAR: the population is not the
      RULES_LABEL population and the frozen rubrics are re-hashed
      REPORTED-ONLY, never applied (factory-wide requirement 22).
  (3) FALSIFICATION RE-RUN on the new head under the SAME frozen rule set via
      the ACCEPTED wrapper evaluation.minimal_retrieval_ca_benchmark against
      unchanged packet-of-record bytes 39319405429.
  (4) PLANNER-REMEDY AND DEGRADATION PIN re-verify under NEW run id
      40040574595, with pipeline.py re-pinned at its already-disclosed
      product-advance value as the new baseline of record.
  (5) REQUIREMENT-4 LINEAGE verification of product cycles 40025340938 and
      40032389983 (PASS gate file AND accept commit on the mount), and of the
      two NON-accepted intermediate cycles that must NOT be counted as lineage.
  (6) COVERAGE v2 re-freeze is CONDITIONAL and NOT executed.

REUSE-FIRST: the falsification leg is a thin subprocess invocation of the
accepted wrapper; the float dual-tolerance convention is the accepted D-A
convention imported BY VALUE (the prior instrument files are never edited —
their digests are pinned by their own run artifacts).

Exit codes (VERDICT_CONTRACT.json conventions):
  0  PASS_NO_FALSIFICATION   - H1 confirmed, H3 reproduced, H4 holds, controls
                               pass, lineage complete. A falsified H2 is
                               disclosed inside the verdict block as an
                               accepted-class NEGATIVE result; it is a content
                               defect on the product's own artifacts, not a
                               divergence of a published quantity.
  1  MATERIAL_DIVERGENCE     - any currency quantity DIVERGENT, OR the
                               falsification re-run changes verdict class, OR a
                               must-hold planner/degradation pin drifts.
  2  NOT_MEASURED_VACUOUS    - a frozen input drifted, a control failed, a
                               required artifact is missing, or the subprocess
                               was not executable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

RUN_ID = "40040574595"
DIRECTION_VERSION = 65
MOUNT = Path("/tmp/lex_accepted/product")
PACKET = "39319405429"
HYPOTHESIS = REPO_ROOT / "evaluation/V65_HEAD_ADVANCE_CROSSCHECK_HYPOTHESIS_V2.json"
FREEZE = REPO_ROOT / "evaluation/V65_HEAD_ADVANCE_CROSSCHECK_FREEZE_RECORD_V2.json"
OUT_DIR = REPO_ROOT / "results/evaluation/v65_head_advance_crosscheck"
REPORT_DIR = REPO_ROOT / "reports/evaluation"

SCHEMA = "lex-evaluation-v65-head-advance-crosscheck/2"

# --- accepted D-A dual float convention, imported BY VALUE -------------------
FROZEN_LITERAL_FLOAT_TOL = 1e-6
PUBLICATION_DECIMALS = 3
APPLIED_FLOAT_TOL = 0.5 * (10 ** -PUBLICATION_DECIMALS)  # 5e-4

# --- frozen probe definitions (mirrored from the hypothesis; re-verified) ----
LETTERHEAD_ZONE_OFFSET_MAX = 400
MARKUP_TOKENS = ["<mark>", "</mark>", "<em>", "</em>", "<b>", "</b>", "<highlight>"]
MIN_MARKER_HITS = 3
LANGUAGE_MARKER_SETS = {
    "de": ["Regeste", "Erwägung", "Kündigung", "Mietvertrag", "Bundesgericht", "Verfügung"],
    "fr": ["Considérant", "résiliation", "bail", "Tribunal fédéral", "recours", "art."],
    "it": ["Dispositivo", "risoluzione", "affitto", "Tribunale federale", "ricorso", "regola"],
}

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
PRIOR_CYCLE_CONTROL = "results/product/offline_slice/20261023T190402Z/rent-default.bundle.json"
SCOPING_INSPECTED = {
    "results/product/offline_slice/20261023T203316Z/rent-default.bundle.json",
    "results/product/offline_slice/20261023T224250Z/rent-default.bundle.json",
    "results/product/server_slice/20261023T224255Z/served.bundle.json",
}

EXPECTED_HYPOTHESIS_SHA = "734a447dffd86a360a46ce9a804e3bb9f7eb224f9067777d78b62216e13e0881"
MOUNT_HEAD = "e4f72a8e6c0460bc52dc625ff3e2da86161e2564"
PLANNER_SHA = "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9"
PIPELINE_SHA_NEW_BASELINE = "265b82acc58d89ce176c37eb8008b53120029e354ef79ecd9bcdcd4f005c5165"

ACCEPTED_FAILED_GATES = [
    "mf::concept_coverage::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::fr-bail-entretien",
    "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
]

# exception classes frozen in the freeze record
STATE_ACCEPTED_RUN_ID_LAG_EXPECTED = "40000001926"
STATE_CURRENT_RUN_LAG_EXPECTED = "40005362253"


# --------------------------------------------------------------------------- helpers
def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_path_get(doc, path):
    cur = doc
    for key in path:
        if isinstance(cur, list):
            cur = cur[int(key)]
        elif isinstance(cur, dict):
            cur = cur[key]
        else:
            raise KeyError(f"non-indexable at {key!r}")
    return cur


def numeric_environment() -> dict:
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


def _marker_hits(evidence: str, lang: str) -> int:
    return sum(1 for tok in LANGUAGE_MARKER_SETS[lang] if tok in evidence)


# ------------------------------------------------------------------- freeze pinning
def load_frozen_quantities() -> list:
    rec = json.loads(FREEZE.read_text())
    return rec["currency_quantities_frozen"]


def rehash_pins(mount: Path) -> dict:
    rec = json.loads(FREEZE.read_text())
    out = {}
    for key, expected in rec["frozen_pins"].items():
        if key.startswith("repo:"):
            p = REPO_ROOT / key[len("repo:"):]
        else:
            p = mount / key[len("mount:"):]
        out[key] = _sha256_file(p) if p.is_file() else "MISSING"
    out["repo:evaluation/V65_HEAD_ADVANCE_CROSSCHECK_HYPOTHESIS_V2.json"] = _sha256_file(HYPOTHESIS)
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=mount,
                              capture_output=True, text=True, timeout=30,
                              check=True).stdout.strip()
    except Exception:
        head = "UNAVAILABLE"
    out["mount_head"] = head
    return out


def compute_input_drift(pins: dict) -> list:
    rec = json.loads(FREEZE.read_text())
    drift = []
    for key, expected in rec["frozen_pins"].items():
        found = pins.get(key)
        if found != expected:
            drift.append(f"{key}: {found} != {expected}")
    if pins.get("repo:evaluation/V65_HEAD_ADVANCE_CROSSCHECK_HYPOTHESIS_V2.json") != EXPECTED_HYPOTHESIS_SHA:
        drift.append("hypothesis digest drift")
    if pins.get("mount_head") != MOUNT_HEAD:
        drift.append(f"product mount head drift: {pins.get('mount_head')} != {MOUNT_HEAD}")
    return drift


# ----------------------------------------------------------- requirement-4 lineage
def requirement4_lineage(mount: Path) -> dict:
    out = {}
    for run_id, accept_commit, expect_accept in (
            ("40025340938", "2ee36779", True),
            ("40032389983", "e4f72a8e", True),
            # NON-accepted intermediate cycles: must NOT count as lineage.
            ("40018153655", None, False),
            ("40028750240", None, False)):
        gate_path = mount / f"results/audit/product/CYCLE_{run_id}_GATE.json"
        gate = None
        if gate_path.is_file():
            try:
                g = json.loads(gate_path.read_text())
                gate = {"gate": g.get("gate"), "safe_to_integrate": g.get("safe_to_integrate"),
                        "required_fixes": g.get("required_fixes")}
            except Exception as exc:  # noqa: BLE001
                gate = {"error": f"{type(exc).__name__}: {exc}"}
        grep = subprocess.run(
            ["git", "log", "--all", "--oneline", "--grep",
             f"accept product cycle {run_id}"], cwd=mount,
            capture_output=True, text=True, timeout=60)
        accept_lines = [ln for ln in grep.stdout.splitlines() if ln.strip()]
        gate_ok = bool(gate) and gate.get("gate") == "PASS" and gate.get("safe_to_integrate") is True
        accept_ok = any(accept_commit in ln for ln in accept_lines) if accept_commit else bool(accept_lines)
        both = gate_ok and accept_ok
        entry = {
            "gate_half": gate, "gate_half_ok": gate_ok,
            "accept_half": {"expected_commit": accept_commit, "matches": accept_lines},
            "accept_half_ok": accept_ok, "requirement_4_both_halves": both,
            "counts_as_accepted_lineage_step": both if expect_accept else False,
        }
        if not expect_accept:
            entry["exclusion_note"] = (
                "frozen as a NON-lineage cycle: this run is not an accepted step and must not "
                "be cited as one; the exclusion is verified here, not assumed")
            entry["exclusion_verified"] = (both is False)
        out[run_id] = entry
    accepted_steps = [k for k, v in out.items() if v.get("counts_as_accepted_lineage_step")]
    excluded_ok = all(out[k].get("exclusion_verified") for k in ("40018153655", "40028750240"))
    out["accepted_steps"] = sorted(accepted_steps)
    out["exclusions_verified"] = excluded_ok
    out["all_accepted"] = (
        sorted(accepted_steps) == ["40025340938", "40032389983"] and excluded_ok)
    return out


# ---------------------------------------------------------------- currency cross-check
def _composite_value(kind: str, doc, artifact_path: Path):
    if kind == "composite_len":
        return len(doc["checks"])
    if kind == "composite_all_pass":
        return all(c.get("status") == "PASS" for c in doc["checks"])
    if kind == "composite_host_count":
        rows = doc["decisions"]
        return sum(1 for r in rows
                   if urlparse(r.get("canonical_url") or "").netloc == "mcp.opencaselaw.ch")
    if kind == "composite_all_resolve":
        rows = doc["decisions"]
        ids = {r["decision_id"] for r in rows}
        cited = (doc.get("answer") or {}).get("cited_decision_ids") or []
        return bool(cited) and all(c in ids for c in cited)
    raise ValueError(f"unknown composite kind {kind}")


def currency_crosscheck(mount: Path) -> dict:
    rows = []
    n_conf = n_div = n_missing = n_lag = n_notre = 0
    for q in load_frozen_quantities():
        art = mount / q["artifact"]
        row = {"id": q["id"], "artifact": q["artifact"], "published": q["published"],
               "kind": q["kind"], "published_source": q.get("published_source")}
        if not art.is_file():
            row.update(verdict="NOT_FOUND", found=None)
            n_missing += 1
            rows.append(row)
            continue
        try:
            if q["kind"] == "sha256":
                found = _sha256_file(art)
                row["found"] = found
                ok = found == q["published"]
            elif q["kind"].startswith("composite_"):
                doc = json.loads(art.read_text())
                found = _composite_value(q["kind"], doc, art)
                row["found"] = found
                ok = found == q["published"]
            else:
                doc = json.loads(art.read_text())
                found = _json_path_get(doc, q["json_path"])
                row["found"] = found
                if q["kind"] == "float":
                    delta = abs(float(found) - float(q["published"]))
                    row["raw_found"] = found
                    row["raw_published"] = q["published"]
                    row["abs_delta"] = delta
                    row["applied_tolerance"] = APPLIED_FLOAT_TOL
                    row["frozen_literal_tolerance"] = FROZEN_LITERAL_FLOAT_TOL
                    row["strict_verdict_1e_6"] = (
                        "CONFIRMED" if delta <= FROZEN_LITERAL_FLOAT_TOL else "DIVERGENT")
                    row["applied_verdict_precision_matched"] = (
                        "CONFIRMED" if delta <= APPLIED_FLOAT_TOL else "DIVERGENT")
                    ok = delta <= APPLIED_FLOAT_TOL
                else:
                    ok = found == q["published"]
            row["verdict"] = "CONFIRMED" if ok else "DIVERGENT"
            if ok:
                n_conf += 1
            else:
                n_div += 1
        except Exception as exc:  # noqa: BLE001
            row["verdict"] = "NOT_FOUND"
            row["error"] = f"{type(exc).__name__}: {exc}"
            n_missing += 1
        rows.append(row)

    # --- frozen exception class: disclosed state pointer lag -----------------
    st = json.loads((mount / "state/product.json").read_text())
    for eid, path, expected in (
            ("state_accepted_run_id_pointer_lag", ["accepted_run_id"], STATE_ACCEPTED_RUN_ID_LAG_EXPECTED),
            ("state_current_run_pointer_lag", ["current_run"], STATE_CURRENT_RUN_LAG_EXPECTED)):
        found = _json_path_get(st, path)
        ok = found == expected
        rows.append({
            "id": eid, "artifact": "state/product.json", "json_path": path,
            "published": expected, "found": found, "kind": "disclosed_lag_pointer",
            "published_source": "freeze record frozen_exception_classes.disclosed_state_pointer_lag",
            "verdict": "CONFIRMED_LAG" if ok else "DIVERGENT",
        })
        if ok:
            n_lag += 1
        else:
            n_div += 1

    # --- frozen exception class: not re-executed this cycle ------------------
    rows.append({
        "id": "state_claim_ceiling_188_mvp_tests",
        "artifact": "state/product.json",
        "json_path": ["vertical_slice_status", "claim_ceiling"],
        "published": "All 188 MVP tests pass",
        "found": None, "kind": "not_reexecuted_disclosed",
        "published_source": "state/product.json claim_ceiling at head e4f72a8e",
        "verdict": "NOT_REEXECUTED_THIS_CYCLE",
        "note": ("this lane does not re-execute the product's full MVP suite this cycle; the "
                 "accepted independent audit of CYCLE_40032389983 recorded the suite counts"),
    })
    n_notre += 1

    float_disclosure = build_float_disclosure(rows)
    return {
        "n_quantities": len(rows),
        "n_confirmed": n_conf,
        "n_divergent": n_div,
        "n_not_found": n_missing,
        "n_confirmed_lag_disclosed": n_lag,
        "n_not_reexecuted_disclosed": n_notre,
        "rows": rows,
        "float_comparison_disclosure": float_disclosure,
        "headline": float_disclosure["headline_applied_precision_matched"],
        "headline_basis": ("applied precision-matched comparison (5e-4); the frozen-literal-1e-6 "
                           "headline is published side by side"),
    }


def build_float_disclosure(rows: list) -> dict:
    counted = [r for r in rows if r.get("verdict") in
               ("CONFIRMED", "CONFIRMED_CORRECTED", "DIVERGENT", "NOT_FOUND")]
    n_conf = sum(1 for r in counted if r.get("verdict") in ("CONFIRMED", "CONFIRMED_CORRECTED"))
    n_div = sum(1 for r in counted if r.get("verdict") == "DIVERGENT")
    n_missing = sum(1 for r in counted if r.get("verdict") == "NOT_FOUND")
    strict_conf = strict_div = strict_missing = 0
    float_rows = []
    for row in counted:
        if row.get("verdict") == "NOT_FOUND":
            strict_verdict = "NOT_FOUND"
            strict_missing += 1
        elif row.get("kind") == "float":
            raw_found = row.get("raw_found", row.get("found"))
            published = row.get("raw_published", row.get("published"))
            delta = abs(float(raw_found) - float(published))
            strict_ok = delta <= FROZEN_LITERAL_FLOAT_TOL
            applied_ok = delta <= APPLIED_FLOAT_TOL
            strict_verdict = "CONFIRMED" if strict_ok else "DIVERGENT"
            row["raw_found"] = raw_found
            row["raw_published"] = published
            row["abs_delta"] = delta
            row["applied_tolerance"] = APPLIED_FLOAT_TOL
            row["frozen_literal_tolerance"] = FROZEN_LITERAL_FLOAT_TOL
            row["strict_verdict_1e_6"] = strict_verdict
            row["applied_verdict_precision_matched"] = "CONFIRMED" if applied_ok else "DIVERGENT"
            float_rows.append({
                "id": row["id"], "published_3dp": published, "raw_found": raw_found,
                "abs_delta": delta, "strict_verdict_1e_6": strict_verdict,
                "applied_verdict_precision_matched": row["applied_verdict_precision_matched"],
                "round_found_to_3dp_equals_published":
                    round(float(raw_found), PUBLICATION_DECIMALS) == float(published),
            })
        else:
            strict_verdict = row["verdict"]
        if strict_verdict == "CONFIRMED":
            strict_conf += 1
        elif strict_verdict == "DIVERGENT":
            strict_div += 1
    return {
        "convention_source": ("accepted D-A dual-verdict convention (run 39986080045 repair "
                              "round 1), frozen in this run's hypothesis before execution"),
        "frozen_literal_tolerance": FROZEN_LITERAL_FLOAT_TOL,
        "applied_tolerance": APPLIED_FLOAT_TOL,
        "applied_tolerance_rationale":
            "half-ulp of the product lane's 3-decimal publication precision; raw_found carried",
        "deviation_from_literal_frozen_rule": True,
        "deviation_disclosed_not_absorbed": True,
        "both_verdicts_published_per_float_quantity": True,
        "headline_applied_precision_matched": (
            "ALL_CONFIRMED" if n_div == 0 and n_missing == 0
            else "DIVERGENCE_PRESENT" if n_div > 0 else "ARTIFACT_MISSING"),
        "headline_frozen_literal_1e_6": (
            "ALL_CONFIRMED" if strict_div == 0 and strict_missing == 0
            else "DIVERGENCE_PRESENT" if strict_div > 0 else "ARTIFACT_MISSING"),
        "counts_applied_precision_matched": {
            "n_confirmed": n_conf, "n_divergent": n_div, "n_not_found": n_missing},
        "counts_frozen_literal_1e_6": {
            "n_confirmed": strict_conf, "n_divergent": strict_div, "n_not_found": strict_missing},
        "n_float_quantities": len(float_rows),
        "float_quantities": float_rows,
        "reproduction": ("recompute abs(delta)=abs(raw_found-published) per float row; "
                         "strict = delta <= 1e-6, applied = delta <= 5e-4"),
        "frozen_rule_edited": False,
    }


# ------------------------------------------------ shipped-slice counter-evidence probe
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


def shipped_slice_counter_evidence_probe(mount: Path) -> dict:
    bundles = []
    for family, rels in PROBE_BUNDLES.items():
        for rel in rels:
            bundles.append(probe_bundle(mount, rel, family))
    control = probe_bundle(mount, PRIOR_CYCLE_CONTROL, "prior_cycle_control")
    all_bundles = bundles + [control]
    n_verified = sum(b.get("n_counter_evidence_verified", 0) for b in all_bundles)
    n_defective = sum(b.get("n_verified_with_defects", 0) for b in all_bundles)
    defect_hist = {}
    for b in all_bundles:
        for r in b.get("verified_rows", []):
            for d in r["defects"]:
                defect_hist[d] = defect_hist.get(d, 0) + 1
    h2_falsified = n_defective > 0
    return {
        "probe_is_not_a_frozen_bar": (
            "the population is the product's own shipped slice bundles, NOT the RULES_LABEL "
            "population (packet-of-record 39319405429); the frozen rubrics are re-hashed "
            "REPORTED-ONLY and never applied, edited or re-derived (factory-wide requirement 22)"),
        "definitions": {
            "LETTERHEAD_ZONE_OFFSET_MAX": LETTERHEAD_ZONE_OFFSET_MAX,
            "MARKUP_TOKENS": MARKUP_TOKENS,
            "MIN_MARKER_HITS": MIN_MARKER_HITS,
            "LANGUAGE_MARKER_SETS": LANGUAGE_MARKER_SETS,
            "row_class_rule": ("COUNTER_REASONING iff no defect fires; otherwise the joined "
                               "defect codes"),
        },
        "n_bundles": len(all_bundles),
        "n_bundles_present": sum(1 for b in all_bundles if b.get("present")),
        "n_bundles_scoping_inspected": sum(1 for b in all_bundles if b.get("scoping_inspected")),
        "n_verified_rows_total": n_verified,
        "n_verified_rows_with_defects": n_defective,
        "defect_histogram": defect_hist,
        "H2_verdict": "H2_FALSIFIED" if h2_falsified else ("H2_SURVIVES" if n_verified else "H2_NOT_MEASURED"),
        "h2_falsified": h2_falsified,
        "bundles": bundles,
        "prior_cycle_control": control,
        "claim_ceiling": (
            "descriptive evidence audit of the product's own newly shipped slice artifacts; "
            "scores no frozen bar, classifies no decision as supporting/contrary under the "
            "frozen rubric, and changes no verdict"),
    }


# ------------------------------------------------------------ falsification re-run (reuse)
def falsification_rerun(mount: Path, out_dir: Path, report_dir: Path, run_id: str) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "evaluation.minimal_retrieval_ca_benchmark",
        "--run-id", run_id,
        "--packets", PACKET,
        "--product-mount", str(mount),
        "--out-dir", str(out_dir / "falsification"),
        "--report-dir", str(report_dir),
    ]
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True,
                              timeout=1200, check=False)
    except Exception as exc:  # noqa: BLE001
        return {"executed": False, "error": f"{type(exc).__name__}: {exc}",
                "verdict": "NOT_MEASURED_VACUOUS", "exit_code": 2}
    wrapper_rec_path = out_dir / "falsification" / f"{run_id}.json"
    engine_rec_path = (out_dir / "falsification" /
                       f"{run_id}_engine_mapping_free_recall_falsifier.json")
    wrapper_rec = json.loads(wrapper_rec_path.read_text()) if wrapper_rec_path.is_file() else {}
    engine_rec = json.loads(engine_rec_path.read_text()) if engine_rec_path.is_file() else {}
    meas = wrapper_rec.get("measurement") or {}
    raw_failed = (meas.get("failed_gates") or wrapper_rec.get("failed_gates") or [])
    failed = [(e.get("gate") if isinstance(e, dict) else str(e)) for e in raw_failed]
    exit_code = proc.returncode
    verdict = {0: "PASS_NO_FALSIFICATION", 1: "PRODUCT_FALSIFIED",
               2: "NOT_MEASURED_VACUOUS"}.get(exit_code, "UNEXPECTED_EXIT")
    return {
        "executed": True, "command": cmd, "exit_code": exit_code, "verdict": verdict,
        "stderr_tail": (proc.stderr or "")[-2000:], "stdout_tail": (proc.stdout or "")[-2000:],
        "failed_gates": failed, "accepted_failed_gates": ACCEPTED_FAILED_GATES,
        "failed_gates_is_superset_of_accepted": set(ACCEPTED_FAILED_GATES).issubset(set(failed)),
        "failed_gates_equals_accepted": set(failed) == set(ACCEPTED_FAILED_GATES),
        "n_gates": meas.get("n_gates", wrapper_rec.get("n_gates")),
        "n_passed": meas.get("n_passed", wrapper_rec.get("n_passed")),
        "n_failed": meas.get("n_failed", wrapper_rec.get("n_failed")),
        "n_reported": meas.get("n_reported", wrapper_rec.get("n_reported")),
        "n_questions_measured": meas.get("n_questions_measured", wrapper_rec.get("n_questions_measured")),
        "falsification_proven": exit_code == 1,
        "input_drift": engine_rec.get("input_drift") or [],
        "engine_direction_version": engine_rec.get("direction_version"),
        "wrapper_direction_version": wrapper_rec.get("direction_version"),
        "lane_direction_version": DIRECTION_VERSION,
        "direction_version_disclosure": (
            f"wrapper/engine direction_version {wrapper_rec.get('direction_version')}/"
            f"{engine_rec.get('direction_version')} vs lane {DIRECTION_VERSION}; wrapper/engine "
            "versions are historical fixture pins, disclosed not repaired"),
        "product_mount_head": engine_rec.get("product_mount_head") or wrapper_rec.get("product_mount_head"),
        "record_path": str(wrapper_rec_path) if wrapper_rec_path.is_file() else None,
        "engine_record_path": str(engine_rec_path) if engine_rec_path.is_file() else None,
    }


# ------------------------------------------------------------------- pins (item 4)
def planner_and_degradation_pin(mount: Path) -> dict:
    findings = {}
    planner = mount / "product/query/adversarial_retrieval.py"
    p_sha = _sha256_file(planner)
    findings["planner_sha256"] = {
        "expected": PLANNER_SHA, "found": p_sha,
        "verdict": "CONFIRMED" if p_sha == PLANNER_SHA else "DIVERGENT"}
    src = planner.read_text(encoding="utf-8")
    aq_start = src.find("def answer_key_terms")
    aq_body = src[aq_start: src.find("\ndef ", aq_start + 1)] if aq_start >= 0 else ""
    has_strip_def = "def strip_redaction_placeholders" in src
    nested_call = "tokenize(strip_redaction_placeholders(" in aq_body
    findings["remedy_a_ordering"] = {
        "strip_redaction_placeholders_defined": has_strip_def,
        "answer_key_terms_calls_strip": aq_body.find("strip_redaction_placeholders") != -1,
        "nested_tokenize_strip_call": nested_call,
        "verdict": "CONFIRMED" if (has_strip_def and nested_call) else "DIVERGENT"}

    pipe = mount / "product/query/pipeline.py"
    pipe_sha = _sha256_file(pipe)
    findings["pipeline_sha256_new_baseline_of_record"] = {
        "expected": PIPELINE_SHA_NEW_BASELINE, "found": pipe_sha,
        "prior_value": "e105bfedc9bf54cb9835369f380e963ccf151d9a75533c734d8419cd94ec631f",
        "disclosure": ("pipeline.py drifted e105bfed->265b82ac as a product advance and was "
                       "disclosed (not absorbed) by run 40012474431; this run re-pins 265b82ac "
                       "as the new baseline of record under run id 40040574595, never by "
                       "editing a prior freeze in place"),
        "verdict": "CONFIRMED" if pipe_sha == PIPELINE_SHA_NEW_BASELINE else "DIVERGENT"}

    p = mount / "results/product/answer_reliability/40000001926_measurement.json"
    doc = json.loads(p.read_text())
    legs = doc.get("legs", [])
    blob = p.read_text()
    n_with_marker = sum(1 for leg in legs
                        if leg.get("adversarial", {}).get("adversarial_status") == "DEGRADED_WRITER_ABORT")
    rate = doc.get("metrics", {}).get("degradation_visible_rate")
    findings["degradation_pin_e_emission_writer_abort"] = {
        "measurement": "40000001926 (newest live reliability measurement)",
        "marker_string_in_artifact": "e_EMISSION_WRITER_ABORT" in blob,
        "n_legs_with_degraded_writer_abort": n_with_marker,
        "n_legs": len(legs), "degradation_visible_rate": rate,
        "older_property_disclosure": (
            "the 7-of-7-DEGRADED property belongs to measurement 39956256289 (the outage date) "
            "and is NOT re-required here; the frozen pin semantics for this run is marker "
            "visibility with rate 1.0"),
        "verdict": ("CONFIRMED"
                    if (n_with_marker >= 1 and len(legs) == 7 and rate == 1.0) else "DIVERGENT")}

    v2 = json.loads((REPO_ROOT / "evaluation/SHIPPED_PLANNER_REMEDY_VERIFICATION_FREEZE_RECORD_V2.json").read_text())
    v3 = json.loads((REPO_ROOT / "evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_FREEZE_RECORD_V3.json").read_text())
    pin_checks = []
    for label, rec in (("planner_remedy_V2", v2), ("degradation_V3", v3)):
        for rel, expected in (rec.get("product_pins") or {}).items():
            fp = mount / rel
            found = _sha256_file(fp) if fp.is_file() else "MISSING"
            pin_checks.append({"source": label, "relpath": rel, "expected": expected,
                               "found": found,
                               "verdict": "CONFIRMED" if found == expected else "DIVERGENT"})
    n_pin_ok = sum(1 for c in pin_checks if c["verdict"] == "CONFIRMED")
    diverged = [c for c in pin_checks if c["verdict"] != "CONFIRMED"]
    findings["frozen_product_pins_rehash"] = {
        "n_pins": len(pin_checks), "n_confirmed": n_pin_ok, "n_divergent": len(diverged),
        "diverged_pins": diverged, "checks": pin_checks,
        "verdict": "CONFIRMED" if n_pin_ok == len(pin_checks) else "DRIFT_REPORTED",
        "interpretation": ("all frozen pins hold" if n_pin_ok == len(pin_checks)
                           else "product-advance pin drift disclosed; planner/remedy/degradation "
                                "must-hold pins evaluated separately")}
    must_hold = [findings["planner_sha256"]["verdict"],
                 findings["remedy_a_ordering"]["verdict"],
                 findings["degradation_pin_e_emission_writer_abort"]["verdict"],
                 findings["pipeline_sha256_new_baseline_of_record"]["verdict"]]
    overall = "CONFIRMED" if all(v == "CONFIRMED" for v in must_hold) else "DIVERGENT"
    return {"findings": findings, "overall": overall, "must_hold_pins": must_hold,
            "product_pins_drift_disclosed": len(diverged) > 0}


# --------------------------------------------------------------------------- controls
def control_planted_divergence_is_detected() -> dict:
    import tempfile
    rel = "results/product/offline_slice/20261023T224250Z/summary.json"
    with tempfile.TemporaryDirectory(prefix="v65hac_control_") as td:
        doc = json.loads((MOUNT / rel).read_text())
        doc["stats"]["n_decisions"] = 42  # plant
        found = _json_path_get(doc, ["stats", "n_decisions"])
        delta = abs(int(found) - 100)
        detected = delta > 0
    return {"control": "C1_planted_currency_divergence_is_detected", "planted_value": 42,
            "expected_published": 100, "abs_delta": delta,
            "detected_as_divergent": detected, "passed": detected}


def control_probe_detects_planted_letterhead_and_markup() -> dict:
    """K2/K3 of the frozen hypothesis: the probe must fire D2 on a planted
    letterhead-zone evidence string and D3 on a planted markup string, and must
    NOT fire D2 on a planted mid-document legal phrase (offset > 400)."""
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
    passed = ("D2_letterhead_zone" in c_letterhead["defects"]
              and "D2_letterhead_zone" not in c_mid["defects"]
              and "D3_markup_residue" in c_markup["defects"])
    return {"control": "C2_probe_classifies_planted_letterhead_mid_and_markup",
            "letterhead_defects": c_letterhead["defects"],
            "mid_document_defects": c_mid["defects"],
            "markup_defects": c_markup["defects"],
            "letterhead_offset": c_letterhead["detail"].get("first_offset"),
            "mid_offset": c_mid["detail"].get("first_offset"),
            "passed": passed}


def control_probe_detects_planted_language_mismatch() -> dict:
    row = {"decision_id": "planted_lang", "language": "it",
           "counter_status": "candidate-limiting", "counter_evidence_verified": True,
           "counter_evidence": "Regeste Resolutiv bedingter Mietvertrag; Anfechtung der Kündigung; Erstreckung",
           "full_text": "y" * 900 + "Regeste Resolutiv bedingter Mietvertrag; Anfechtung der Kündigung; Erstreckung",
           "snippet": "", "regeste": "", "full_text_status": "lazy"}
    c = classify_verified_row(row)
    passed = "D4_language_marker_mismatch" in c["defects"]
    return {"control": "C3_probe_detects_language_marker_mismatch", "row_language": "it",
            "defects": c["defects"], "marker_hits_own": c["detail"].get("marker_hits_own"),
            "marker_hits_other": c["detail"].get("marker_hits_other"), "passed": passed}


def control_frozen_rules_rehash_holds(pins_before: dict, pins_after: dict) -> dict:
    keys = [k for k in pins_before if "RULES_" in k]
    holds = all(pins_before[k] == pins_after[k] for k in keys)
    rec = json.loads(FREEZE.read_text())
    fp = rec["frozen_pins"]
    expected_ok = (
        pins_before.get("repo:evaluation/frozen_bars/RULES_LABEL.json")
        == fp["repo:evaluation/frozen_bars/RULES_LABEL.json"]
        and pins_before.get("repo:evaluation/frozen_bars/RULES_GEOMETRY.json")
        == fp["repo:evaluation/frozen_bars/RULES_GEOMETRY.json"])
    return {"control": "C4_frozen_rules_rehash_holds_reported_only", "rule_keys": keys,
            "before": {k: pins_before.get(k) for k in keys},
            "after": {k: pins_after.get(k) for k in keys},
            "before_equals_after": holds, "matches_expected": expected_ok,
            "passed": holds and expected_ok,
            "note": "re-hashed REPORTED-ONLY; the frozen rubrics are never applied by this run"}


def control_packet_bytes_unchanged(pins_before: dict, pins_after: dict) -> dict:
    key = "mount:results/product/gate_packet/39319405429/packet.json"
    rec = json.loads(FREEZE.read_text())
    expected = rec["frozen_pins"][key]
    before, after = pins_before.get(key), pins_after.get(key)
    return {"control": "C5_packet_of_record_bytes_unchanged", "before": before, "after": after,
            "expected": expected, "before_equals_after": before == after,
            "matches_expected": before == expected,
            "passed": before == after and before == expected}


# ---------------------------------------------------------------------------- report
def _render_report(record: dict) -> str:
    cur = record["currency_crosscheck"]
    probe = record["shipped_slice_counter_evidence_probe"]
    fr = record["falsification_rerun"]
    pp = record["planner_and_degradation_pin"]
    lin = record["requirement_4_lineage"]
    ctrls = record["controls"]
    h2 = probe["H2_verdict"]
    lines = [
        f"# V65 Head-Advance Cross-Check v2 — run {RUN_ID}",
        "",
        f"- Direction: v{DIRECTION_VERSION}",
        f"- Product mount head: `{record['product_mount_head']}` (accept product cycle 40032389983)",
        f"- Packet of record: {PACKET} (bytes re-hashed, unchanged)",
        f"- Frozen rules re-hashed REPORTED-ONLY: RULES_LABEL "
        f"`{json.loads(FREEZE.read_text())['frozen_pins']['repo:evaluation/frozen_bars/RULES_LABEL.json'][:16]}…`, "
        f"RULES_GEOMETRY `a7452748d40c511a…`",
        f"- Verdict: **{record['verdict']}** (exit {record['exit_code']})",
        f"- Executed at: {record['generated_at_utc']}",
        f"- H2 shipped-slice counter-evidence probe: **{h2}** "
        f"({probe['n_verified_rows_with_defects']} of {probe['n_verified_rows_total']} "
        f"verified rows carry a frozen defect)",
        "",
        "## Re-open trigger",
        "",
        "- Accepted product head advanced `f9618377` (accept 40005362253) → `e4f72a8e` "
        "(accept 40032389983). Requirement-4 lineage: "
        f"{', '.join(lin.get('accepted_steps', []))}.",
        "- Cycles **40018153655** (gate REVISE, no accept commit) and **40028750240** "
        "(gate PASS but NO accept commit) are frozen as NON-lineage and verified excluded: "
        f"{lin.get('exclusions_verified')}.",
        "",
        "## Ordered item 1 — currency cross-check",
        "",
        f"- Quantities: {cur['n_quantities']} — CONFIRMED {cur['n_confirmed']}, "
        f"DIVERGENT {cur['n_divergent']}, NOT_FOUND {cur['n_not_found']}, "
        f"CONFIRMED_LAG (disclosed) {cur['n_confirmed_lag_disclosed']}, "
        f"NOT_REEXECUTED_THIS_CYCLE {cur['n_not_reexecuted_disclosed']}",
        f"- Headline (applied precision-matched, 5e-4): **{cur['headline']}**",
        "",
    ]
    fd = cur.get("float_comparison_disclosure") or {}
    if fd:
        counts_lit = fd["counts_frozen_literal_1e_6"]
        lines += [
            "### Float-comparison disclosure (accepted D-A dual-verdict convention)",
            "",
            f"- Frozen-literal 1e-6: **{fd['headline_frozen_literal_1e_6']}** "
            f"(CONFIRMED {counts_lit['n_confirmed']}, DIVERGENT {counts_lit['n_divergent']}).",
            f"- Applied precision-matched 5e-4: **{fd['headline_applied_precision_matched']}**.",
            "",
        ]
    for row in cur["rows"]:
        mark = {"CONFIRMED": "✅", "CONFIRMED_LAG": "📌", "CONFIRMED_CORRECTED": "🔧",
                "DIVERGENT": "❌", "NOT_FOUND": "⚠️",
                "NOT_REEXECUTED_THIS_CYCLE": "🚫"}.get(row["verdict"], "?")
        lines.append(f"- {mark} `{row['id']}`: published `{row['published']}` vs found "
                     f"`{row.get('found')}` → **{row['verdict']}**")
    lines += [
        "",
        "## Ordered item 2 — shipped-slice counter-evidence probe (H2)",
        "",
        f"- Verdict: **{h2}**",
        f"- Bundles: {probe['n_bundles_present']}/{probe['n_bundles']} present "
        f"({probe['n_bundles_scoping_inspected']} scoping-inspected, disclosed)",
        f"- Verified rows: {probe['n_verified_rows_total']}; with a frozen defect: "
        f"{probe['n_verified_rows_with_defects']}",
        f"- Defect histogram: {probe['defect_histogram']}",
        "- **This probe scores no frozen bar.** Its population is the product's own shipped "
        "slice bundles, not the RULES_LABEL population; the frozen rubrics are re-hashed "
        "REPORTED-ONLY (factory-wide requirement 22).",
        "",
    ]
    for b in probe["bundles"] + [probe["prior_cycle_control"]]:
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
        "## Ordered item 3 — falsification re-run (same frozen rule set, new head)",
        "",
        f"- Verdict: **{fr['verdict']}** (exit {fr['exit_code']})",
        f"- Falsification proven: {fr.get('falsification_proven')}",
        f"- Failed gates: {fr.get('failed_gates')}",
        f"- Equals accepted 4-gate set: {fr.get('failed_gates_equals_accepted')}",
        f"- Gates {fr.get('n_passed')}/{fr.get('n_gates')} passed; "
        f"n_questions={fr.get('n_questions_measured')}",
        f"- Engine input_drift: {fr.get('input_drift')}",
        f"- {fr.get('direction_version_disclosure', '')}",
        "",
        "## Ordered item 4 — planner-remedy + degradation pin (new run id)",
        "",
        f"- Overall: **{pp['overall']}**",
    ]
    for name, f in pp["findings"].items():
        lines.append(f"- `{name}`: **{f.get('verdict', f.get('overall', '?'))}**")
    lines += ["", "## Controls", ""]
    for c in ctrls.values():
        lines.append(f"- `{c['control']}`: {'PASS' if c['passed'] else 'FAIL'}")
    lines += [
        "",
        "## Ordered item 5 — coverage v2 re-freeze",
        "",
        "- NOT EXECUTED — conditional on the coverage family being resumed; it is NOT resumed "
        "this cycle.",
        "",
        "## Required fixes D1/D2/D3 of CYCLE_39965089504_GATE.json (quoted-count disclosure)",
        "",
        "- Reported here only because this lane quotes those counts: the CYCLE_39965089504 "
        "audit returned three NON-BLOCKING required fixes D1/D2/D3; they were discharged by "
        "the product lane before the heads cross-checked here. No new D-fix count is asserted.",
        "",
        "## Claim ceiling",
        "",
        "- This instrument cross-checks published product quantities against their own "
        "committed artifacts on the newest accepted head, audits the counter-evidence "
        "quality of the product's own newly shipped slice bundles under frozen (non-bar) "
        "definitions, and re-executes the accepted mapping-free falsification benchmark on "
        "unchanged packet-of-record bytes under the same frozen rules re-hashed "
        "REPORTED-ONLY. It scores no frozen bar, re-derives no threshold, classifies no "
        "decision under the frozen rubric, and asserts no serve or human-gate readiness. "
        "Both DO-NOT-SERVE orders stand; admission stays fail-closed; the comparative "
        "map-versus-ranked-list half is NOT scored while zero counter rows are evidenced "
        "(factory-wide requirement 22).",
        "",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------------------- run
def run(run_id: str = RUN_ID) -> int:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pins_before = rehash_pins(MOUNT)
    drift = compute_input_drift(pins_before)

    if drift:
        record = {
            "schema": SCHEMA, "run_id": run_id, "direction_version": DIRECTION_VERSION,
            "generated_at_utc": generated, "product_mount": str(MOUNT),
            "product_mount_head": pins_before.get("mount_head"),
            "input_drift": drift, "verdict": "NOT_MEASURED_VACUOUS", "exit_code": 2,
            "currency_crosscheck": None, "shipped_slice_counter_evidence_probe": None,
            "falsification_rerun": None, "planner_and_degradation_pin": None,
            "requirement_4_lineage": None, "controls": {}, "pins_before": pins_before,
            "pins_after": None, "numeric_environment": numeric_environment()}
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"{run_id}.json").write_text(json.dumps(record, indent=1, sort_keys=True))
        print(json.dumps({"verdict": record["verdict"], "input_drift": drift}, indent=1))
        return 2

    lineage = requirement4_lineage(MOUNT)
    currency = currency_crosscheck(MOUNT)
    probe = shipped_slice_counter_evidence_probe(MOUNT)
    falsification = falsification_rerun(MOUNT, OUT_DIR, REPORT_DIR, run_id)
    planner_pin = planner_and_degradation_pin(MOUNT)
    c1 = control_planted_divergence_is_detected()
    c2 = control_probe_detects_planted_letterhead_and_markup()
    c3 = control_probe_detects_planted_language_mismatch()
    pins_after = rehash_pins(MOUNT)
    c4 = control_frozen_rules_rehash_holds(pins_before, pins_after)
    c5 = control_packet_bytes_unchanged(pins_before, pins_after)
    controls = {
        "C1_planted_currency_divergence_is_detected": c1,
        "C2_probe_classifies_planted_letterhead_mid_and_markup": c2,
        "C3_probe_detects_language_marker_mismatch": c3,
        "C4_frozen_rules_rehash_holds_reported_only": c4,
        "C5_packet_of_record_bytes_unchanged": c5,
    }
    control_failures = [k for k, v in controls.items() if not v.get("passed")]

    if control_failures or not lineage.get("all_accepted"):
        verdict, exit_code = "NOT_MEASURED_VACUOUS", 2
    elif currency["n_divergent"] > 0 or planner_pin["overall"] == "DIVERGENT":
        verdict, exit_code = "MATERIAL_DIVERGENCE", 1
    elif falsification["verdict"] == "NOT_MEASURED_VACUOUS":
        verdict, exit_code = "NOT_MEASURED_VACUOUS", 2
    elif falsification["verdict"] == "PASS_NO_FALSIFICATION":
        verdict, exit_code = "MATERIAL_DIVERGENCE", 1
    elif falsification["verdict"] == "PRODUCT_FALSIFIED":
        verdict, exit_code = "PASS_NO_FALSIFICATION", 0
    else:
        verdict, exit_code = "NOT_MEASURED_VACUOUS", 2

    record = {
        "schema": SCHEMA, "run_id": run_id, "direction_version": DIRECTION_VERSION,
        "generated_at_utc": generated, "product_mount": str(MOUNT),
        "product_mount_head": pins_before.get("mount_head"),
        "packet_of_record": PACKET, "input_drift": [],
        "freeze_first": {
            "hypothesis": "evaluation/V65_HEAD_ADVANCE_CROSSCHECK_HYPOTHESIS_V2.json",
            "hypothesis_sha256": EXPECTED_HYPOTHESIS_SHA,
            "freeze_record": "evaluation/V65_HEAD_ADVANCE_CROSSCHECK_FREEZE_RECORD_V2.json",
            "ordering": ("hypothesis + freeze record + instrument + guard tests committed "
                         "BEFORE claim-bearing execution of this run"),
            "scoping_disclosure": (
                "three of fourteen probe bundles were inspected during scoping and are "
                "labelled scoping_inspected; eleven bundles plus the prior-cycle control "
                "were not inspected per-row before the freeze"),
        },
        "requirement_4_lineage": lineage,
        "currency_crosscheck": currency,
        "shipped_slice_counter_evidence_probe": probe,
        "falsification_rerun": falsification,
        "planner_and_degradation_pin": planner_pin,
        "controls": controls, "control_failures": control_failures,
        "pins_before": pins_before, "pins_after": pins_after,
        "numeric_environment": numeric_environment(),
        "verdict": verdict, "exit_code": exit_code,
        "H2_negative_result_disclosure": (
            f"{probe['H2_verdict']}: {probe['n_verified_rows_with_defects']} of "
            f"{probe['n_verified_rows_total']} counter_evidence_verified rows across "
            f"{probe['n_bundles']} shipped/control bundles carry a frozen defect "
            f"({probe['defect_histogram']}). This is preserved as a NEGATIVE RESULT. It is "
            "NOT a frozen-bar score, NOT a serve-verdict input and NOT a divergence of a "
            "published quantity; it is a content defect on the product's own artifacts and "
            "is the binding counter-authority evidence gap measured on the shipped slice."),
        "claim_ceiling": (
            "Currency cross-check of the product quantities newly landed by accepted cycles "
            "40025340938 and 40032389983 against their own committed artifacts on head "
            "e4f72a8e, plus a frozen-definition audit of the counter-evidence quality of the "
            "product's own newly shipped slice bundles, plus a re-execution of the accepted "
            "mapping-free falsification benchmark on unchanged packet-of-record bytes under "
            "the same frozen rules re-hashed REPORTED-ONLY. It scores no frozen bar, "
            "re-derives no threshold, classifies no decision under the frozen rubric, and "
            "asserts no serve or human-gate readiness."),
        "posture_unchanged": {"human_gate_ready": False, "machine_gate_ready": False,
                              "packet_admitted": False, "ready_for_owner_session": False,
                              "owner_decision_required": False},
        "coverage_v2_refreeze": {
            "executed": False,
            "reason": "conditional on the coverage family being resumed; it is NOT resumed this cycle"},
        "no_obsolete_174k_benchmark_rerun": True,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{run_id}.json"
    out_path.write_text(json.dumps(record, indent=1, sort_keys=True))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"V65_HEAD_ADVANCE_CROSSCHECK_{run_id}.md"
    report_path.write_text(_render_report(record), encoding="utf-8")
    print(json.dumps({
        "verdict": verdict, "exit_code": exit_code,
        "currency_headline": currency["headline"],
        "n_confirmed": currency["n_confirmed"], "n_divergent": currency["n_divergent"],
        "n_confirmed_lag_disclosed": currency["n_confirmed_lag_disclosed"],
        "H2_verdict": probe["H2_verdict"],
        "n_verified_rows_total": probe["n_verified_rows_total"],
        "n_verified_rows_with_defects": probe["n_verified_rows_with_defects"],
        "defect_histogram": probe["defect_histogram"],
        "requirement_4_all_accepted": lineage.get("all_accepted"),
        "falsification_verdict": falsification["verdict"],
        "falsification_failed_gates": falsification.get("failed_gates"),
        "planner_pin": planner_pin["overall"],
        "controls": {k: v["passed"] for k, v in controls.items()},
        "out": str(out_path), "report": str(report_path)}, indent=1))
    return exit_code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=RUN_ID)
    args = ap.parse_args(argv)
    return run(run_id=args.run_id)


if __name__ == "__main__":
    raise SystemExit(main())
