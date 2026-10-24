#!/usr/bin/env python3
"""v68 post-repair family: precondition gate + FAST-MVP counter-authority falsifier.

WHAT THIS IS
------------
Two executable halves of factory-direction v68 evaluation ordered work, in one
freeze-first instrument:

1. PRECONDITION GATE (ordered item (2), adjudicated from committed bytes):
   does the product at mount head carry the P0 rejection/incumbent leg, and is
   the FULL flagship offline/server slice family (the frozen 15-member probe
   family) regenerated? Both are decided as SET RELATIONS with intersections and
   both differences published (factory-wide requirement 16), never by matching
   cardinalities. If the family condition fails, the ordered item-(2) protocol
   (frozen protocol on the named family + packet-of-record 39319405429 +
   d2_path_scope_probe) is NOT run and is reported NOT_YET_DISCRIMINATING.

2. FAST-MVP FALSIFICATION on the NEW post-repair bytes (ordered item (3)
   contract: a NEW pre-registered falsification on NEW bytes with its own
   freeze-first record). This is the smallest executable retrieval/
   counter-authority benchmark that can falsify the product's P0 repair claim.

REUSE-FIRST (no re-implementation, everything by hash-verified import)
----------------------------------------------------------------------
* ``evaluation.fast_mvp_current_head_ca_falsifier.controls``   (C1-C4 battery)
* ``evaluation.fast_mvp_current_head_ca_falsifier.score_bundle`` (per-bundle scoring)
* ``evaluation.counter_evidence_quality_benchmark.classify_verified_row`` (frozen D1-D4)
* ``evaluation.mapping_free_recall_falsifier`` surface/source/duplicate/language helpers
* frozen ``scored_statuses`` vocabulary from RULES_LABEL.json
* the accepted multilingual/provenance test suites are re-executed alongside

No threshold, predicate, rubric, tokeniser, stoplist or verdict contract is
defined here. The instrument adds only population selection, the precondition
set-relation adjudicator, a false-reject sweep, an aggregation table and a
verdict rule frozen in the hypothesis file BEFORE execution.

Exit codes (identical vocabulary to the accepted FAST-MVP falsifier):
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
from evaluation import fast_mvp_current_head_ca_falsifier as FAS  # noqa: E402

SCHEMA = "lex-evaluation-post-repair-family-ca-falsifier/1"
HYPOTHESIS_RELPATH = (
    "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40134202991_HYPOTHESIS_V1.json")
FREEZE_RELPATH = (
    "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40134202991_FREEZE_V1.json")
RULES_LABEL_RELPATH = "evaluation/frozen_bars/RULES_LABEL.json"
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/post_repair_family_ca_falsifier"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports/evaluation"

EXIT_NOT_VACUOUS = 0
EXIT_FALSIFIED = 1
EXIT_VACUOUS = 2

SOUND_ROW_ID = "bstger_SK.2023.49"


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
    """Re-hash every frozen input, population bundle and baseline family member."""
    rows: list[dict] = []
    ok = True

    def check(label: str, path: Path, expected: str) -> None:
        nonlocal ok
        actual = sha256_file(path) if path.is_file() else None
        match = actual == expected
        ok = ok and match
        rows.append({"input": label, "path": str(path), "expected": expected,
                     "actual": actual, "match": match})

    for rel, expected in (hyp.get("frozen_inputs_REPORTED_ONLY") or {}).items():
        if rel.startswith("mount:"):
            check(f"mount:{rel[6:]}", Path(hyp["population_FROZEN"]["product_mount"]) / rel[6:],
                  expected)
        else:
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

    # baseline flagship family must be byte-unchanged (append-only respected)
    for rel, expected in (hyp["frozen_probe_family_FROZEN"]["members_sha256"] or {}).items():
        check(f"baseline_family:{rel}", mount / rel, expected)

    return {"all_match": ok, "checks": rows}


# --------------------------------------------------------------------------- #
# half 1: ordered item (2) precondition adjudicator
# --------------------------------------------------------------------------- #
def _role_key(path: str) -> tuple[str, str]:
    """(slice_kind, query) role of a bundle path, e.g. ('offline','rent-default')."""
    parts = path.split("/")
    kind = "server" if "server_slice" in parts else "offline"
    name = parts[-1]
    query = name.split(".bundle.json")[0]
    return kind, query


def leg_markers(mount: Path, hyp: dict) -> dict:
    spec = hyp["product_code_markers_FROZEN"]
    src = mount / spec["file"]
    found: dict[str, dict] = {}
    present = src.is_file()
    text = src.read_text(encoding="utf-8") if present else ""
    lines = text.splitlines()
    for needle in spec["required_substrings"]:
        hits = [i + 1 for i, ln in enumerate(lines) if needle in ln]
        found[needle] = {"found": bool(hits), "line_numbers": hits[:5],
                         "n_hits": len(hits)}
    return {
        "file": spec["file"],
        "file_sha256": sha256_file(src) if present else None,
        "file_present": present,
        "markers": found,
        "all_markers_present": present and all(v["found"] for v in found.values()),
        "line_evidence_declared_at_freeze": spec["line_evidence_at_freeze"],
    }


def post_repair_inventory(mount: Path) -> list[dict]:
    """All shipped slice bundles whose provenance carries the content filter."""
    out: list[dict] = []
    for slice_dir in ("offline_slice", "server_slice"):
        base = mount / "results" / "product" / slice_dir
        if not base.is_dir():
            continue
        for bundle in sorted(base.glob("*/*.bundle.json")):
            try:
                doc = json.loads(bundle.read_text(encoding="utf-8"))
            except Exception:
                continue
            ces = ((doc.get("provenance") or {}).get("counter_evidence_span") or {})
            if "content_filter" not in ces:
                continue
            rel = str(bundle.relative_to(mount))
            out.append({
                "path": rel,
                "role_key": list(_role_key(rel)),
                "n_downgraded": ces.get("n_downgraded"),
                "n_incumbent_downgraded": ces.get("n_incumbent_downgraded"),
                "abstained_ids": ces.get("abstained_ids"),
                "abstention_reasons": ces.get("abstention_reasons"),
                "post_repair_marker": "provenance.counter_evidence_span.content_filter",
            })
    return out


def precondition_gate(hyp: dict, mount: Path) -> dict:
    markers = leg_markers(mount, hyp)
    inventory = post_repair_inventory(mount)

    frozen_members = sorted(hyp["frozen_probe_family_FROZEN"]["members_sha256"])
    frozen_set = set(frozen_members)
    post_set = {b["path"] for b in inventory}

    by_path_intersection = sorted(frozen_set & post_set)
    frozen_only = sorted(frozen_set - post_set)
    post_only = sorted(post_set - frozen_set)

    def roles(paths: set[str]) -> dict:
        acc: dict[str, int] = {}
        for p in paths:
            k = "/".join(_role_key(p))
            acc[k] = acc.get(k, 0) + 1
        return dict(sorted(acc.items()))

    frozen_roles = roles(frozen_set)
    post_roles = roles(post_set)
    role_union = sorted(set(frozen_roles) | set(post_roles))
    role_relation = {
        k: {"frozen_family": frozen_roles.get(k, 0),
            "post_repair": post_roles.get(k, 0),
            "covered": post_roles.get(k, 0) >= frozen_roles.get(k, 0)}
        for k in role_union
    }

    product_claim = hyp["product_claim_FROZEN"]
    claim = product_claim["claim_string"]
    claim_roles_ok = all(
        post_roles.get(r, 0) >= 1 for r in
        ("offline/rent-default", "offline/petty-theft-dismissal",
         "offline/corporate-criminal-liability", "offline/business-judgment-rule",
         "server/served"))

    # member-for-member regeneration under the append-only rule: each frozen family
    # member is matched to at most one DISTINCT post-repair bundle with the same
    # (slice_kind, query) role. Path identity is structurally impossible once the
    # baseline is preserved, so the relation is computed on roles WITH multiplicity.
    matched_per_role = {k: min(frozen_roles.get(k, 0), post_roles.get(k, 0))
                        for k in sorted(set(frozen_roles) | set(post_roles))}
    matched_members = sum(matched_per_role.values())
    role_covered = all(post_roles.get(k, 0) >= 1 for k in frozen_roles)
    parity_ok = all(post_roles.get(k, 0) >= frozen_roles.get(k, 0) for k in frozen_roles)

    h1 = markers["all_markers_present"] and len(inventory) >= 1
    h2 = matched_members == len(frozen_set)

    return {
        "H1_precondition_leg_landed": h1,
        "H2_precondition_full_family_regenerated": h2,
        "leg_markers": markers,
        "post_repair_inventory": {
            "n_bundles": len(inventory),
            "paths": sorted(post_set),
            "roles": post_roles,
            "bundles": inventory,
        },
        "set_relations_REQUIREMENT_16": {
            "frozen_probe_family_n": len(frozen_set),
            "post_repair_n": len(post_set),
            "path_identity": {
                "intersection_by_path_n": len(by_path_intersection),
                "intersection_by_path": by_path_intersection,
                "frozen_family_only_n": len(frozen_only),
                "frozen_family_only": frozen_only,
                "post_repair_only_n": len(post_only),
                "post_repair_only": post_only,
                "interpretation": "path identity is EXPECTED to be 0 while the baseline "
                                  "family is preserved byte-for-byte (append-only); it is "
                                  "reported for completeness and is never the sole basis "
                                  "of the verdict",
            },
            "roles_frozen_family": frozen_roles,
            "roles_post_repair": post_roles,
            "role_relation": role_relation,
            "member_for_member_matching": {
                "rule": "each frozen family member matches at most one distinct "
                        "post-repair bundle of the same (slice_kind, query) role",
                "matched_per_role": matched_per_role,
                "matched_members": matched_members,
                "of": len(frozen_set),
            },
            "role_covered_every_frozen_role_has_a_post_repair_bundle": role_covered,
            "per_role_multiplicity_parity": parity_ok,
            "never_cardinality_only": "path-identity sets, role tables and the "
                                      "member-for-member matching are all published; no "
                                      "'exactly/all-of' claim is made from a count alone",
        },
        "product_claim_adjudication": {
            "claim_string": claim,
            "claim_source": product_claim["source"],
            "claim_definition_member_count": 5,
            "frozen_direction_member_count": len(frozen_set),
            "claim_roles_satisfied_by_post_repair_bytes": claim_roles_ok,
            "finding": (
                "Product's claimed family (4 offline query bundles + 1 server bundle) "
                "and the direction's named family (the frozen 15-member probe family: "
                "11 offline rent-default + 4 server served) are DIFFERENT SETS. "
                f"Member-for-member regeneration of the named family is "
                f"{matched_members}/{len(frozen_set)}; every frozen role has a "
                f"post-repair bundle={role_covered}; per-role multiplicity parity="
                f"{parity_ok}; Product's own 4+1 claim is satisfied by the present "
                f"bytes={claim_roles_ok}. Both readings are published; neither is "
                "silently preferred, and no 'all of the family' claim is made from a "
                "cardinality."),
        },
        "item_2_full_protocol_status": (
            "READY" if h2 else
            "NOT_YET_DISCRIMINATING (ordered item (2) protocol not executed: "
            f"member-for-member regeneration of the named frozen family is "
            f"{matched_members}/{len(frozen_set)}; no synthetic stand-in is "
            "substituted, d2_path_scope_probe is not re-run as the ordered "
            "re-measure, packet-of-record 39319405429 is not scored and the standing "
            "falsification is not re-run)"),
        "item_2_leg_status": "LANDED" if h1 else "NOT_LANDED",
    }


# --------------------------------------------------------------------------- #
# half 2: post-repair byte scoring + false-reject / path-scope sweeps
# --------------------------------------------------------------------------- #
def classify_row_like(row: dict) -> dict:
    """Frozen D1-D4 classification of one row, via the byte-pinned instrument."""
    return CQ.classify_verified_row(row)


def downgraded_row_sweep(mount: Path, bundles: list[dict], scored: list[str]) -> dict:
    """False-reject + PATH_SCOPE_RESIDUAL measurement over the post-repair bytes.

    FALSE REJECT (regression): a row the filter downgraded whose RETAINED counter
    evidence passes the frozen D1-D4 predicates, i.e. evidence the frozen predicates
    do not condemn was marked unevidenced.
    REPAIR MISS: a downgraded row that is still counter_evidence_verified=true while
    its retained evidence carries a frozen defect.
    PATH_SCOPE_RESIDUAL: a pivot_absent abstention that still leaves a DEFECTIVE
    incumbent counter_evidence_verified=true.
    """
    scored_set = {str(s).strip().lower() for s in scored}
    false_rejects: list[dict] = []
    repair_misses: list[dict] = []
    downgrades: list[dict] = []
    residuals: list[dict] = []
    pivot_rows: list[dict] = []
    sound_rows: list[dict] = []

    for entry in bundles:
        path = mount / entry["path"]
        doc = json.loads(path.read_text(encoding="utf-8"))
        decisions = doc.get("decisions") or []
        by_id = {str(d.get("decision_id")): d for d in decisions}
        ces = ((doc.get("provenance") or {}).get("counter_evidence_span") or {})
        reasons = list((ces.get("abstention_reasons") or {}).keys())

        for rec in (ces.get("downgrades") or []):
            did = str(rec.get("decision_id"))
            row = by_id.get(did) or {}
            cls = classify_row_like({**row, "decision_id": did})
            entry_rec = {
                "bundle": entry["label"], "path": entry["path"], "decision_id": did,
                "leg": rec.get("leg"), "reason_code": rec.get("reason_code"),
                "product_recorded_defects": rec.get("defects"),
                "verified_after": row.get("counter_evidence_verified"),
                "frozen_predicate_defects_on_retained_evidence": cls["defects"],
                "frozen_predicate_class": cls["class"],
                "grounded_in": cls["detail"].get("grounded_in"),
                "first_offset": cls["detail"].get("first_offset"),
            }
            downgrades.append(entry_rec)
            if not cls["defects"]:
                false_rejects.append({**entry_rec, "note": (
                    "filter condemned evidence the frozen predicates do not condemn")})
            if row.get("counter_evidence_verified") is True and cls["defects"]:
                repair_misses.append({**entry_rec, "note": (
                    "still counter_evidence_verified=true with a frozen defect")})

        if "pivot_absent" in reasons:
            for did in (ces.get("abstained_ids") or []):
                row = by_id.get(str(did)) or {}
                cls = classify_row_like({**row, "decision_id": str(did)})
                pivot_rows.append({
                    "bundle": entry["label"], "decision_id": did,
                    "verified": row.get("counter_evidence_verified"),
                    "frozen_predicate_defects": cls["defects"],
                    "reason_codes": reasons,
                })
                if row.get("counter_evidence_verified") is True and cls["defects"]:
                    residuals.append(pivot_rows[-1])

        for row in decisions:
            status = str(row.get("counter_status") or "").strip().lower()
            if status not in scored_set or row.get("counter_evidence_verified") is not True:
                continue
            cls = classify_row_like(row)
            if not cls["defects"]:
                sound_rows.append({
                    "bundle": entry["label"], "decision_id": row.get("decision_id"),
                    "counter_status": row.get("counter_status"),
                    "language": row.get("language"),
                    "class": cls["class"],
                    "verified": row.get("counter_evidence_verified"),
                })

    return {
        "n_downgrade_records": len(downgrades),
        "downgrades": downgrades,
        "false_rejects_n": len(false_rejects),
        "false_rejects": false_rejects,
        "zero_false_rejects": len(false_rejects) == 0,
        "repair_misses_n": len(repair_misses),
        "repair_misses": repair_misses,
        "pivot_absent_rows": pivot_rows,
        "path_scope_residual_rows": residuals,
        "path_scope_residual_cleared": len(residuals) == 0,
        "defect_free_verified_scored_rows": sound_rows,
        "sound_row_preserved": any(
            r["decision_id"] == SOUND_ROW_ID and r["verified"] for r in sound_rows),
    }


def evaluate(run_id: str) -> dict:
    hyp, freeze, scored = load_frozen()
    hpath = REPO_ROOT / HYPOTHESIS_RELPATH
    fpath = REPO_ROOT / FREEZE_RELPATH
    hyp_sha = sha256_file(hpath)
    freeze_sha = sha256_file(fpath)
    mount = Path(hyp["population_FROZEN"]["product_mount"])
    classification_sha = sha256_file(Path(CQ.__file__))
    engine_sha = sha256_file(Path(MF.__file__))
    adapter_sha = sha256_file(Path(FAS.__file__))

    consistency = {
        "hypothesis_sha_matches_freeze_record":
            hyp_sha == freeze.get("hypothesis_sha256_at_freeze"),
        "frozen_predicate_sha_matches_hypothesis":
            classification_sha == hyp["frozen_inputs_REPORTED_ONLY"][
                "evaluation/counter_evidence_quality_benchmark.py"],
        "frozen_engine_sha_matches_hypothesis":
            engine_sha == hyp["frozen_inputs_REPORTED_ONLY"][
                "evaluation/mapping_free_recall_falsifier.py"],
        "accepted_adapter_sha_matches_hypothesis":
            adapter_sha == hyp["frozen_inputs_REPORTED_ONLY"][
                "evaluation/fast_mvp_current_head_ca_falsifier.py"],
    }

    pins_before = verify_pins(hyp, freeze)
    ctrl = FAS.controls(scored, classification_sha)

    # ---- half 1: precondition adjudicator (reads provenance, no scoring) ----
    precondition = precondition_gate(hyp, mount)

    # ---- half 2: frozen-predicate scoring of the post-repair population ----
    bundles = [FAS.score_bundle(mount, b, scored)
               for b in hyp["population_FROZEN"]["bundles"]]
    sweeps = downgraded_row_sweep(
        mount, hyp["population_FROZEN"]["bundles"], scored)
    pins_after = verify_pins(hyp, freeze)

    enriched = [b for b in bundles if b["enriched"]]
    not_enriched = [b for b in bundles if not b["enriched"]]

    h1_surface = all(
        b["frozen_surface_gate"]["n_issued"] == 1
        and b["frozen_surface_gate"]["n_with_empty_evidence"] == 0
        and b["source_validity"]["n_rows_missing_id_or_url"] == 0
        and b["duplicate_suppression"]["duplicates"] == 0
        for b in enriched)
    h3_falsification = all(
        b["n_counter_evidence_verified_scored_rows"] >= 1
        and b["n_defective_verified_scored_rows"]
        == b["n_counter_evidence_verified_scored_rows"]
        for b in enriched)
    h_control = all(b["frozen_surface_gate"]["n_issued"] == 0 for b in not_enriched)

    n_with_scored = sum(1 for b in enriched
                        if b["n_counter_evidence_verified_scored_rows"] >= 1)
    n_with_sound = sum(1 for b in enriched if b["n_sound_verified_scored_rows"] >= 1)

    vacuous_reasons: list[str] = []
    if not all(consistency.values()):
        vacuous_reasons.append("freeze/predicate digest inconsistency")
    if not pins_before["all_match"]:
        vacuous_reasons.append("input pin drift before execution")
    if not pins_after["all_match"]:
        vacuous_reasons.append("input pin drift after execution")
    if not ctrl["all_hold"]:
        vacuous_reasons.append("control failure")
    if not h_control:
        vacuous_reasons.append("NOT-ENRICHED control has n_issued != 0")
    if n_with_scored == 0:
        vacuous_reasons.append("no enriched bundle carries a verified scored counter row")

    if vacuous_reasons:
        verdict, code = "NOT_MEASURED_VACUOUS", EXIT_VACUOUS
    elif h1_surface and h3_falsification:
        verdict, code = "CAPABILITY_FALSIFIED_CONTENT_DEFECTIVE", EXIT_FALSIFIED
    elif n_with_sound >= 1:
        verdict, code = "SOUND_COUNTER_ROW_PRESENT", EXIT_NOT_VACUOUS
    else:
        verdict, code = "PARTIAL_OR_UNEXPECTED", EXIT_NOT_VACUOUS

    histogram = FAS._histogram(bundles)
    distinct_defective = sorted({
        r["decision_id"] for b in bundles for r in b["verified_scored_rows"]
        if r["defects"]})

    success = hyp["success_rule_FROZEN"]
    success_measured = {
        "defect_histogram_zero": all(histogram.get(k, 0) == 0 for k in
                                     ("D2_letterhead_zone", "D3_markup_residue",
                                      "D4_language_marker_mismatch")),
        "defect_histogram": histogram,
        "sound_row_preserved": sweeps["sound_row_preserved"],
        "zero_false_rejects": sweeps["zero_false_rejects"],
        "path_scope_residual_cleared": sweeps["path_scope_residual_cleared"],
        "note": success["note"],
    }

    return {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": hyp["direction_version"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry_point": hyp["entry_point"],
        "verdict": verdict,
        "exit_code": code,
        "falsification_proven": code == EXIT_FALSIFIED,
        "vacuous_reasons": vacuous_reasons,
        "hypothesis": {"path": HYPOTHESIS_RELPATH, "sha256": hyp_sha},
        "freeze_record": {"path": FREEZE_RELPATH, "sha256": freeze_sha},
        "consistency": consistency,
        "product_mount": str(mount),
        "product_mount_head": mount_head(mount),
        "product_accepted_cycle": hyp["population_FROZEN"][
            "expected_product_accepted_cycle"],
        "scored_statuses_from_frozen_rubric": scored,
        "frozen_predicates_reused": {
            "counter_evidence_quality_benchmark.py": classification_sha,
            "mapping_free_recall_falsifier.py": engine_sha,
            "fast_mvp_current_head_ca_falsifier.py": adapter_sha,
        },
        "precondition": precondition,
        "hypothesis_checks": {
            "H1_precondition_leg_landed": precondition["H1_precondition_leg_landed"],
            "H2_precondition_full_family_regenerated":
                precondition["H2_precondition_full_family_regenerated"],
            "H3_all_verified_scored_rows_content_defective": h3_falsification,
            "H4_controls_all_hold": ctrl["all_hold"],
            "H5_pins_identical_before_after":
                pins_before["all_match"] and pins_after["all_match"],
            "H1_surface_gates_and_source_validity_on_enriched": h1_surface,
            "H_control_not_enriched_zero_issued": h_control,
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
            "defect_histogram": histogram,
            "distinct_defective_decision_ids": distinct_defective,
        },
        "success_criteria_REPORT_ONLY": success_measured,
        "sweeps": sweeps,
        "baselines_REFERENCE": hyp["baselines_REFERENCE"],
        "controls": ctrl,
        "pins_before_execution": pins_before,
        "pins_after_execution": pins_after,
        "bundles": bundles,
        "numeric_environment": numeric_environment(),
        "no_new_thresholds": True,
        "no_174k_benchmark_rerun": True,
        "benchmark_of_record_untouched": True,
        "packet_of_record_not_scored": "39319405429",
        "ordered_work_status": {
            "item_1_correction_of_record": "DISCHARGED (accepted cycle 40133253347, "
                "gate PASS with NON-BLOCKING CC6/CC7 mount-history note)",
            "item_2_conditional_remeasure": precondition["item_2_full_protocol_status"],
            "item_2_leg_half": precondition["item_2_leg_status"],
            "item_3_standing_falsification_record": "UNCHANGED; benchmark of record "
                "PRODUCT_FALSIFIED on packet-of-record 39319405429 still stands and is "
                "superseded only by a NEW pre-registered falsification on NEW bytes",
            "item_4_non_blocking_required_fixes_of_CYCLE_39965089504":
                "reported wherever this lane quotes those counts: D1 wording 6-vs-7 "
                "tests, D2 wording new-vs-appended test file, D3 environment skip "
                "variance 172/1309/20 vs 172/1308/21 - all non-blocking, gate PASS",
        },
        "claim_ceiling": hyp["claim_ceiling"],
        "packet_admitted": False,
        "machine_gate_ready": False,
        "human_gate_ready": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
    }


def write_report(rec: dict, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    p = report_dir / f"POST_REPAIR_FAMILY_CA_FALSIFIER_{rec['run_id']}.md"
    pre = rec["precondition"]
    rel = pre["set_relations_REQUIREMENT_16"]
    lines = [
        f"# Post-repair family precondition gate + CA falsifier — run {rec['run_id']}",
        "",
        f"- Falsifier verdict: **{rec['verdict']}** (exit {rec['exit_code']}), "
        f"falsification_proven={rec['falsification_proven']}",
        f"- Ordered item (2) precondition (a) rejection/incumbent leg: "
        f"**{pre['item_2_leg_status']}**",
        f"- Ordered item (2) precondition (b) full flagship family regenerated: "
        f"**{pre['H2_precondition_full_family_regenerated']}**",
        f"- Ordered item (2) full protocol status: **{pre['item_2_full_protocol_status']}**",
        f"- Direction: v{rec['direction_version']}",
        f"- Product mount head: `{rec['product_mount_head']}` "
        f"(accepted cycle {rec['product_accepted_cycle']})",
        "",
        "## 1. Precondition set relation (requirement 16: sets, never cardinalities)",
        "",
        f"- Frozen probe family members: {rel['frozen_probe_family_n']}",
        f"- Post-repair bundles found: {rel['post_repair_n']}",
        f"- Intersection by path: {rel['intersection_by_path_n']} "
        f"(path identity is expected to be 0 while the baseline is preserved)",
        f"- Frozen-family-only (missing post-repair counterpart): {rel['frozen_family_only_n']}",
        f"- Post-repair-only (roles absent from the frozen family): {rel['post_repair_only_n']}",
        f"- Member-for-member regeneration: "
        f"{rel['member_for_member_matching']['matched_members']}/"
        f"{rel['member_for_member_matching']['of']} "
        f"({json.dumps(rel['member_for_member_matching']['matched_per_role'], sort_keys=True)})",
        f"- Every frozen role has a post-repair bundle: "
        f"{rel['role_covered_every_frozen_role_has_a_post_repair_bundle']}; "
        f"per-role multiplicity parity: {rel['per_role_multiplicity_parity']}",
        f"- Roles frozen family: `{json.dumps(rel['roles_frozen_family'], sort_keys=True)}`",
        f"- Roles post-repair: `{json.dumps(rel['roles_post_repair'], sort_keys=True)}`",
        "",
        "### Product's own family claim",
        "",
        f"- Claim: \"{pre['product_claim_adjudication']['claim_string']}\"",
        f"- Source: {pre['product_claim_adjudication']['claim_source']}",
        f"- {pre['product_claim_adjudication']['finding']}",
        "",
        "### Leg markers (file:line at mount head)",
        "",
        f"- file: `{pre['leg_markers']['file']}` sha256 `{pre['leg_markers']['file_sha256']}`",
    ]
    for k, v in pre["leg_markers"]["markers"].items():
        lines.append(f"- `{k}`: found={v['found']} lines={v['line_numbers']}")
    lines += [
        "",
        "## 2. Falsifier on the post-repair bytes",
        "",
        "| bundle | family | enriched | n_dec | surface n_issued | verified scored | defective | sound |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for b in rec["bundles"]:
        g = b["frozen_surface_gate"]
        lines.append(
            f"| {b['label']} | {b['family']} | {b['enriched']} | {b['n_decisions']} | "
            f"{g['n_issued']} | {b['n_counter_evidence_verified_scored_rows']} | "
            f"{b['n_defective_verified_scored_rows']} | {b['n_sound_verified_scored_rows']} |")
    agg = rec["aggregate"]
    base = rec["baselines_REFERENCE"]
    lines += [
        "",
        f"- Defect histogram (post-repair): `{json.dumps(agg['defect_histogram'], sort_keys=True)}`",
        f"- Distinct defective decision ids: {agg['distinct_defective_decision_ids']}",
        f"- BEFORE 40105794124: `{json.dumps(base['40105794124_FAST_MVP_falsifier']['defect_histogram'], sort_keys=True)}`",
        f"- BEFORE 40062917685: `{json.dumps(base['40062917685_frozen_probe_baseline']['defect_histogram'], sort_keys=True)}`",
        "",
        "## 3. Product-facing success criteria (REPORT-ONLY, never a frozen bar)",
        "",
    ]
    for k, v in rec["success_criteria_REPORT_ONLY"].items():
        lines.append(f"- {k}: **{v}**")
    lines += [
        "",
        "## 4. False-reject and PATH_SCOPE sweeps",
        "",
        f"- Downgrade records inspected: {rec['sweeps']['n_downgrade_records']}",
        f"- False rejects: {rec['sweeps']['false_rejects_n']} "
        f"(zero_false_rejects={rec['sweeps']['zero_false_rejects']})",
        f"- PATH_SCOPE_RESIDUAL rows: {len(rec['sweeps']['path_scope_residual_rows'])} "
        f"(cleared={rec['sweeps']['path_scope_residual_cleared']})",
        f"- Sound row {SOUND_ROW_ID} preserved: "
        f"**{rec['sweeps']['sound_row_preserved']}**",
        "",
        "## 5. Controls and pins",
        "",
    ]
    for c in rec["controls"]["battery"]:
        lines.append(f"- {c['control']}: holds={c['holds']}")
    lines += [
        f"- pins before: {rec['pins_before_execution']['all_match']}; "
        f"pins after: {rec['pins_after_execution']['all_match']}",
        f"- numeric environment: `{json.dumps(rec['numeric_environment'], sort_keys=True)}`",
        "",
        "## 6. Ordered-work status and claim ceiling",
        "",
    ]
    for k, v in rec["ordered_work_status"].items():
        lines.append(f"- {k}: {v}")
    lines += [
        "",
        rec["claim_ceiling"],
        "",
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
        "item_2_leg": rec["precondition"]["item_2_leg_status"],
        "item_2_full_family_regenerated":
            rec["precondition"]["H2_precondition_full_family_regenerated"],
        "item_2_status": rec["precondition"]["item_2_full_protocol_status"],
        "defect_histogram": rec["aggregate"]["defect_histogram"],
        "false_rejects": rec["sweeps"]["false_rejects_n"],
        "path_scope_residual_cleared": rec["sweeps"]["path_scope_residual_cleared"],
        "sound_row_preserved": rec["sweeps"]["sound_row_preserved"],
        "controls_all_hold": rec["controls"]["all_hold"],
        "pins_all_match": (rec["pins_before_execution"]["all_match"]
                           and rec["pins_after_execution"]["all_match"]),
        "record": str(out),
        "report": str(report),
    }, indent=1))
    return rec["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
