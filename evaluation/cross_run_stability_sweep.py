#!/usr/bin/env python3
"""Cross-run stability sweep — is the accepted P1 run-instability general?

WHY THIS INSTRUMENT EXISTS (direction v58 lanes.evaluation)
-----------------------------------------------------------
Cycle 39315343123 established finding P1 on the accepted product mount: the
SAME live FR question produced 1 evidenced ``candidate-limiting`` in
CYCLE_39128456801 and ZERO scored counter labels in
CYCLE_39139648336_F1F2_VERIFY, so contrary/limiting-authority discovery is
run-unstable at the live surface.  That comparison was (a) pair-specific and
(b) counter-stage-only.  Product must now choose between a determinism fix and
a run-to-run disclosure, and the choice depends on whether P1 is an ISOLATED
counter-stage defect or a SYSTEMIC property of the live query pipeline
(retrieval set, ranking, clusters, language composition, answer).

The accepted product mount already contains a second same-query multi-run
group that the per-run probe never compared to itself: two DE runs of
``Kündigung Mietvertrag Mietrecht`` 13 hours apart.  This instrument answers
the generalization question offline, from committed bytes, in well under a
second, and without pre-empting the unserved packet 39275520116.

REUSE-FIRST — every predicate is IMPORTED, never re-derived
----------------------------------------------------------
* evaluation.mapping_free_recall_falsifier.concept_coverage
* evaluation.mapping_free_recall_falsifier.source_validity
* evaluation.mapping_free_recall_falsifier.duplicate_suppression
* evaluation.mapping_free_recall_falsifier.counter_authority_surface
* evaluation.mapping_free_recall_falsifier.language_robustness
* evaluation.mapping_free_recall_falsifier.sha256_file / numeric_environment
* evaluation.stand_ready_multilingual_probe.counter_stage_applicability
* evaluation.frozen_bars/RULES_LABEL.json rubric.scored_statuses (read-only)

ZERO thresholds, bars, stoplists, tokenisers or score floors are introduced.
The claim-bearing metric is VERDICT DIVERGENCE under the already-accepted
gate contract.  Every overlap / rank / cluster / language number is
REPORTED-ONLY and can never flip the exit code.

Exit codes (frozen in evaluation/CROSS_RUN_STABILITY_SWEEP_HYPOTHESIS_V1.json)
-----------------------------------------------------------------------------
0  STABILITY_NOT_GENERALIZED   every applicable accepted gate returns the same
                               verdict for every run inside every same-query
                               group; P1 is RETAINED as an isolated pair finding
1  RUN_INSTABILITY_GENERALIZED  >=1 same-query group is DIVERGENT on >=1
                               applicable accepted gate (group + gate named)
2  ENVIRONMENT_OR_VACUOUS      pin drift, population drift, <2 comparable
                               groups, no group with >=2 counter-applicable
                               runs, or a non-vacuity control failing — never a
                               pass, never a bar-met

SCRATCH-RUN OBLIGATION
----------------------
A claim-bearing run writes to the committed default
``results/evaluation/cross_run_stability_sweep/<run_id>.json``.  Any scratch
invocation MUST pass ``--out`` to a non-committed path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.mapping_free_recall_falsifier import (  # noqa: E402
    concept_coverage,
    counter_authority_surface,
    duplicate_suppression,
    language_robustness,
    numeric_environment,
    sha256_file,
    source_validity,
)
from evaluation.stand_ready_multilingual_probe import (  # noqa: E402
    counter_stage_applicability,
)

SCHEMA = "lex-evaluation-cross-run-stability-sweep/1"
HYPOTHESIS_RELPATH = "evaluation/CROSS_RUN_STABILITY_SWEEP_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/CROSS_RUN_STABILITY_SWEEP_FREEZE_RECORD.json"
RULES_LABEL_RELPATH = "evaluation/frozen_bars/RULES_LABEL.json"

EXIT_STABLE = 0
EXIT_GENERALIZED = 1
EXIT_ENVIRONMENT = 2

DEFAULT_MOUNTS = [
    "/tmp/lex_accepted/product",
    "/tmp/lex_accepted/product-mount",
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def resolve_mount() -> Path | None:
    for var in ("LEX_ACCEPTED_PRODUCT", "LEX_PRODUCT_MOUNT"):
        val = os.environ.get(var)
        if val and Path(val).is_dir():
            return Path(val)
    for p in DEFAULT_MOUNTS:
        if Path(p).is_dir():
            return Path(p)
    return None


def normalise_query(text: Any) -> str:
    if isinstance(text, dict):
        text = text.get("text") or text.get("query") or ""
    return unicodedata.normalize("NFKC", str(text or "")).strip()


def query_text_of(record: dict, bundle: dict) -> str:
    return normalise_query(bundle.get("query") or record.get("query") or "")


def mount_head(mount: Path) -> str | None:
    import subprocess
    try:
        out = subprocess.run(
            ["git", "-C", str(mount), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=20,
        )
        return out.stdout.strip() or None
    except Exception:  # pragma: no cover
        return None


# --------------------------------------------------------------------------- #
# frozen pins + population (fail-closed)
# --------------------------------------------------------------------------- #
def verify_frozen_pins(repo: Path, freeze: dict) -> dict:
    checks = []
    for rel, pinned in (freeze.get("frozen_inputs_rehashed_before_execution") or {}).items():
        path = repo / rel
        actual = sha256_file(path) if path.is_file() else None
        checks.append({"file": rel, "pinned": pinned, "actual": actual,
                       "match": actual == pinned})
    hyp = repo / HYPOTHESIS_RELPATH
    frz = repo / FREEZE_RELPATH
    checks.append({
        "file": HYPOTHESIS_RELPATH,
        "pinned": freeze.get("hypothesis_sha256"),
        "actual": sha256_file(hyp) if hyp.is_file() else None,
        "match": bool(hyp.is_file()) and sha256_file(hyp) == freeze.get("hypothesis_sha256"),
    })
    checks.append({
        "file": FREEZE_RELPATH,
        "pinned": "FILE_PRESENT",
        "actual": "FILE_PRESENT" if frz.is_file() else None,
        "match": frz.is_file(),
    })
    return {"all_match": all(c["match"] for c in checks), "checks": checks}


def verify_population(mount: Path, hypothesis: dict) -> dict:
    pop = hypothesis.get("population_pinned_before_execution") or {}
    checks = []
    for entry in pop.get("live_runs") or []:
        for kind in ("record", "bundle"):
            path = mount / entry[kind]
            actual = sha256_file(path) if path.is_file() else None
            checks.append({
                "file": entry[kind],
                "pinned": entry[f"{kind}_sha256"],
                "actual": actual,
                "match": actual == entry[f"{kind}_sha256"],
            })
    head = mount_head(mount)
    pinned_head = pop.get("product_mount_head")
    return {
        "mount_head_pinned": pinned_head,
        "mount_head_actual": head,
        "mount_head_match": head == pinned_head,
        "files": checks,
        "all_match": (head == pinned_head) and all(c["match"] for c in checks),
    }


# --------------------------------------------------------------------------- #
# per-run gate evaluation (all predicates imported)
# --------------------------------------------------------------------------- #
def evaluate_run(record: dict, bundle: dict, scored_statuses: list[str],
                 record_rel: str) -> dict:
    qrec = {"question": query_text_of(record, bundle), "qid": record_rel}
    cov = concept_coverage(qrec, bundle)
    src = source_validity(bundle)
    dup = duplicate_suppression(bundle)
    cas = counter_authority_surface(bundle, scored_statuses)
    lang = language_robustness(bundle)
    applic = counter_stage_applicability(record)

    gates: list[dict] = []
    gates.append({
        "gate": "sr::concept_coverage",
        "passed": cov["n_zero"] == 0,
        "measured": cov,
    })
    gates.append({
        "gate": "sr::source_validity",
        "passed": src["n_rows_missing_id_or_url"] == 0,
        "measured": src,
    })
    gates.append({
        "gate": "sr::duplicate_suppression",
        "passed": dup["duplicates"] == 0,
        "measured": dup,
    })
    if applic["applicable"]:
        gates.append({
            "gate": "sr::counter_authority_surface",
            "passed": (cas["n_issued"] >= 1 and cas["n_with_empty_evidence"] == 0),
            "measured": {**cas, "stage_applicability": applic},
        })
    else:
        gates.append({
            "gate": "sr::counter_authority_surface",
            "passed": None,
            "measured": {**cas, "stage_applicability": applic},
            "qualification": "NOT_APPLICABLE_STAGE_NOT_RUN — never a pass, never a fail "
                             "(requirement-25 instrument-qualified envelope)",
        })
    gates.append({
        "gate": "sr::language_robustness",
        "passed": None,
        "measured": lang,
        "qualification": "REPORTED-ONLY — published BESIDE the frozen benchmark fr/it "
                         "authority-recall cells, never a pass/fail",
    })

    failed = [g["gate"] for g in gates if g["passed"] is False]
    return {
        "record": record_rel,
        "query": query_text_of(record, bundle),
        "product_record_verdict": record.get("verdict"),
        "product_n_failed_checks": record.get("n_failed_checks"),
        "stages_executed": record.get("stages_executed"),
        "counters_block": record.get("counters"),
        "counter_stage_applicable": bool(applic["applicable"]),
        "counter_stage_applicability_basis": applic.get("basis"),
        "gates": gates,
        "failed_gates": failed,
        "n_gates_failed": len(failed),
        "run_verdict_on_applicable_gates": "FALSIFIED" if failed else "PASS_ON_APPLICABLE_GATES",
    }


# --------------------------------------------------------------------------- #
# reported-only diagnostics (never gate)
# --------------------------------------------------------------------------- #
def _id_rank_map(bundle: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for d in bundle.get("decisions") or []:
        did = str(d.get("decision_id") or "")
        if did:
            out[did] = int(d.get("rank") if d.get("rank") is not None else len(out))
    return out


def _id_cluster_map(bundle: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for d in bundle.get("decisions") or []:
        did = str(d.get("decision_id") or "")
        if did:
            out[did] = d.get("cluster_id")
    return out


def _id_counter_map(bundle: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for d in bundle.get("decisions") or []:
        did = str(d.get("decision_id") or "")
        if did:
            out[did] = {
                "counter_status": str(d.get("counter_status") or ""),
                "counter_evidence_present": bool(str(d.get("counter_evidence") or "").strip()),
            }
    return out


def pair_diagnostics(bundle_a: dict, bundle_b: dict) -> dict:
    ids_a = set(_id_rank_map(bundle_a))
    ids_b = set(_id_rank_map(bundle_b))
    common = ids_a & ids_b
    only_a = sorted(ids_a - ids_b)
    only_b = sorted(ids_b - ids_a)
    union = ids_a | ids_b
    jaccard = (len(common) / len(union)) if union else 1.0

    ranks_a, ranks_b = _id_rank_map(bundle_a), _id_rank_map(bundle_b)
    displacements = [abs(ranks_a[i] - ranks_b[i]) for i in common]
    rank_changed = sum(1 for i in common if ranks_a[i] != ranks_b[i])

    cl_a, cl_b = _id_cluster_map(bundle_a), _id_cluster_map(bundle_b)
    common_cl = [i for i in common if cl_a.get(i) is not None and cl_b.get(i) is not None]
    reassigned = [i for i in common_cl if cl_a[i] != cl_b[i]]

    cm_a, cm_b = _id_counter_map(bundle_a), _id_counter_map(bundle_b)
    status_changed = [i for i in common
                      if cm_a[i]["counter_status"] != cm_b[i]["counter_status"]]
    evid_lost = [i for i in common
                 if cm_a[i]["counter_evidence_present"] and not cm_b[i]["counter_evidence_present"]]
    evid_gained = [i for i in common
                   if cm_b[i]["counter_evidence_present"] and not cm_a[i]["counter_evidence_present"]]

    def lang_dist(b: dict) -> dict:
        return dict(Counter(str(d.get("language") or "").strip() or "UNLABELLED"
                            for d in b.get("decisions") or []))

    la, lb = lang_dist(bundle_a), lang_dist(bundle_b)
    langs = sorted(set(la) | set(lb))

    def answer_digest(b: dict) -> dict:
        ans = b.get("answer") or {}
        prose = ans.get("prose") if isinstance(ans, dict) else None
        return {
            "present": bool(prose),
            "status": ans.get("status") if isinstance(ans, dict) else None,
            "prose_sha256": hashlib.sha256(str(prose).encode("utf-8")).hexdigest()
                            if prose else None,
            "n_cited_decision_ids": len(ans.get("cited_decision_ids") or [])
                                    if isinstance(ans, dict) else 0,
        }

    return {
        "qualification": "REPORTED-ONLY — no threshold is applied to any number in "
                         "this block and none of them can change the exit code",
        "n_a": len(ids_a),
        "n_b": len(ids_b),
        "n_common": len(common),
        "n_only_a": len(only_a),
        "n_only_b": len(only_b),
        "only_a_examples": only_a[:10],
        "only_b_examples": only_b[:10],
        "jaccard": round(jaccard, 6),
        "rank": {
            "n_common": len(common),
            "n_rank_changed": rank_changed,
            "max_abs_displacement": max(displacements) if displacements else 0,
            "mean_abs_displacement": round(
                (sum(displacements) / len(displacements)), 6) if displacements else 0.0,
        },
        "cluster": {
            "n_common_with_cluster": len(common_cl),
            "n_reassigned": len(reassigned),
            "reassigned_share": round(len(reassigned) / len(common_cl), 6) if common_cl else 0.0,
            "reassigned_examples": sorted(reassigned)[:10],
        },
        "counter_status_changes": {
            "n_changed": len(status_changed),
            "examples": sorted(status_changed)[:10],
            "n_evidence_lost": len(evid_lost),
            "n_evidence_gained": len(evid_gained),
            "evidence_lost_examples": sorted(evid_lost)[:10],
            "evidence_gained_examples": sorted(evid_gained)[:10],
        },
        "language_distribution_a": la,
        "language_distribution_b": lb,
        "language_delta": {k: lb.get(k, 0) - la.get(k, 0) for k in langs},
        "answer_a": answer_digest(bundle_a),
        "answer_b": answer_digest(bundle_b),
    }


# --------------------------------------------------------------------------- #
# non-vacuity battery (designs frozen in the hypothesis)
# --------------------------------------------------------------------------- #
def _synthetic_bundle(rows: list[dict], query: str = "SYNTH Q") -> dict:
    return {"query": query, "decisions": rows, "clusters": []}


def _synthetic_record(**kw) -> dict:
    base = {"query": "SYNTH Q", "counters": {"counter_authorities": 1,
                                             "by_status": {"cited": 1}}}
    base.update(kw)
    return base


def non_vacuity(scored_statuses: list[str]) -> dict:
    controls: list[dict] = []

    scored_row = {
        "decision_id": "synth_limiting_0001",
        "canonical_url": "https://example.invalid/synth_limiting_0001",
        "title": "synth limiting decision",
        "counter_status": "candidate-limiting",
        "counter_evidence": "limiting the earlier line",
        "language": "de", "rank": 0, "cluster_id": 0,
    }
    plain_row = {
        "decision_id": "synth_plain_0001",
        "canonical_url": "https://example.invalid/synth_plain_0001",
        "title": "synth plain decision",
        "counter_status": "none",
        "counter_evidence": "",
        "language": "de", "rank": 1, "cluster_id": 0,
    }

    # V1 — a run that drops the single scored row must flip the counter gate.
    a = evaluate_run(_synthetic_record(), _synthetic_bundle([scored_row, plain_row]),
                     scored_statuses, "synth_A")
    b = evaluate_run(_synthetic_record(), _synthetic_bundle([plain_row]),
                     scored_statuses, "synth_B")
    va = next(g for g in a["gates"] if g["gate"] == "sr::counter_authority_surface")
    vb = next(g for g in b["gates"] if g["gate"] == "sr::counter_authority_surface")
    v1 = (va["passed"] is True and vb["passed"] is False)
    controls.append({
        "control": "V1_divergence_detector_must_fire",
        "holds": v1,
        "why": "run A issues one evidenced scored label and passes the accepted counter "
               "gate; run B, which drops that row, must FAIL it — otherwise the "
               "divergence detector is vacuous",
        "measured": {"run_a_passed": va["passed"], "run_b_passed": vb["passed"]},
    })

    # V2 — byte-equal runs must be identical on every gate and every delta.
    a2 = evaluate_run(_synthetic_record(), _synthetic_bundle([scored_row, plain_row]),
                      scored_statuses, "synth_A2")
    d2 = pair_diagnostics(_synthetic_bundle([scored_row, plain_row]),
                          _synthetic_bundle([scored_row, plain_row]))
    g_a = {g["gate"]: g["passed"] for g in a["gates"]}
    g_a2 = {g["gate"]: g["passed"] for g in a2["gates"]}
    zeroish = (d2["jaccard"] == 1.0 and d2["n_only_a"] == 0 and d2["n_only_b"] == 0
               and d2["rank"]["n_rank_changed"] == 0
               and d2["cluster"]["n_reassigned"] == 0
               and d2["counter_status_changes"]["n_changed"] == 0
               and all(v == 0 for v in d2["language_delta"].values()))
    v2 = (g_a == g_a2 and zeroish)
    controls.append({
        "control": "V2_identical_runs_must_not_fire",
        "holds": v2,
        "why": "identical runs must produce identical gate verdicts and exactly-zero "
               "diagnostics, or the sweep would report instability everywhere",
        "measured": {"gate_maps_equal": g_a == g_a2, "diagnostics_zero": zeroish},
    })

    # V3 — stage-not-run is NOT_APPLICABLE, never a verdict.
    nr = _synthetic_record(stages_executed={"counter_authority": False})
    nr_bundle = _synthetic_bundle([plain_row])
    nr_run = evaluate_run(nr, nr_bundle, scored_statuses, "synth_NR")
    nrg = next(g for g in nr_run["gates"] if g["gate"] == "sr::counter_authority_surface")
    v3 = (nrg["passed"] is None and nr_run["counter_stage_applicable"] is False)
    controls.append({
        "control": "V3_not_applicable_is_never_a_verdict",
        "holds": v3,
        "why": "a gate whose stage never ran must be NOT_APPLICABLE (passed=None); it "
               "can count toward neither the stable nor the generalized verdict",
        "measured": {"passed": nrg["passed"],
                     "applicable": nr_run["counter_stage_applicable"]},
    })

    return {"controls": controls, "all_hold": all(c["holds"] for c in controls)}


# --------------------------------------------------------------------------- #
# grouping
# --------------------------------------------------------------------------- #
def group_runs(entries: list[dict], loaded: dict[str, dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for e in entries:
        key = loaded[e["run"]]["query_key"]
        groups.setdefault(key, []).append(e["run"])
    return groups


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def run(mount: Path, repo: Path, run_id: str) -> tuple[dict, int]:
    hypothesis = json.loads((repo / HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    freeze = json.loads((repo / FREEZE_RELPATH).read_text(encoding="utf-8"))
    rules = json.loads((repo / RULES_LABEL_RELPATH).read_text(encoding="utf-8"))
    scored_statuses = list(((rules.get("rubric") or {}).get("scored_statuses")) or [])

    frozen = verify_frozen_pins(repo, freeze)
    population = verify_population(mount, hypothesis)

    pop = hypothesis["population_pinned_before_execution"]
    entries = pop.get("live_runs") or []
    if len(entries) < 2:
        return ({
            "schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_OR_VACUOUS",
            "exit_code": EXIT_ENVIRONMENT,
            "reason": "pinned population holds fewer than two live runs",
        }, EXIT_ENVIRONMENT)

    loaded: dict[str, dict] = {}
    for e in entries:
        record = json.loads((mount / e["record"]).read_text(encoding="utf-8"))
        bundle = json.loads((mount / e["bundle"]).read_text(encoding="utf-8"))
        loaded[e["run"]] = {
            "record": record, "bundle": bundle,
            "query_key": query_text_of(record, bundle),
        }

    groups = group_runs(entries, loaded)
    vac = non_vacuity(scored_statuses)

    # ---- group structure checks (exit-2 conditions) -----------------------
    group_structure = {
        "n_groups": len(groups),
        "group_sizes": {k: len(v) for k, v in groups.items()},
        "expected_n_groups": (hypothesis["population_pinned_before_execution"]
                              .get("expected_groups", {}).get("expected_n_groups")),
        "expected_group_sizes": (hypothesis["population_pinned_before_execution"]
                                 .get("expected_groups", {}).get("expected_group_sizes")),
    }
    comparable_groups = {k: v for k, v in groups.items() if len(v) >= 2}
    group_structure["n_comparable_groups"] = len(comparable_groups)

    # V5 — at least one comparable group with >=2 counter-applicable runs.
    v5_detail = []
    v5_ok = False
    for gkey, runs in comparable_groups.items():
        applicable_runs = [r for r in runs
                           if evaluate_run(loaded[r]["record"], loaded[r]["bundle"],
                                           scored_statuses, r)["counter_stage_applicable"]]
        v5_detail.append({"group": gkey, "n_runs": len(runs),
                          "n_counter_applicable": len(applicable_runs),
                          "counter_applicable_runs": applicable_runs})
        if len(applicable_runs) >= 2:
            v5_ok = True

    # ---- per-run evaluation ---------------------------------------------
    per_run = []
    for e in entries:
        r = loaded[e["run"]]
        per_run.append(evaluate_run(r["record"], r["bundle"], scored_statuses, e["record"]))
    per_run_by_name = {p["record"]: p for p in per_run}

    # ---- per-group comparison -------------------------------------------
    group_results = []
    n_divergent = 0
    for gkey, runs in sorted(comparable_groups.items()):
        runs_sorted = sorted(runs)
        a_name, b_name = runs_sorted[0], runs_sorted[1]
        ra, rb = per_run_by_name[a_name], per_run_by_name[b_name]
        ga = {g["gate"]: g for g in ra["gates"]}
        gb = {g["gate"]: g for g in rb["gates"]}
        legs = []
        group_divergent = False
        for gate_name in sorted(set(ga) | set(gb)):
            pa = ga.get(gate_name, {}).get("passed")
            pb = gb.get(gate_name, {}).get("passed")
            if pa is None or pb is None:
                status = "NOT_APPLICABLE"
                divergent = False
                detail = ("one or both runs do not carry an applicable verdict for "
                          "this gate; never a pass, never a fail")
            else:
                divergent = pa != pb
                status = "DIVERGENT" if divergent else "STABLE"
                detail = (f"run A passed={pa}, run B passed={pb}")
                if divergent:
                    group_divergent = True
            legs.append({
                "gate": gate_name,
                "run_a": a_name, "run_b": b_name,
                "run_a_passed": pa, "run_b_passed": pb,
                "status": status, "divergent": divergent,
                "detail": detail,
                "run_a_measured": ga.get(gate_name, {}).get("measured"),
                "run_b_measured": gb.get(gate_name, {}).get("measured"),
            })
        if group_divergent:
            n_divergent += 1
        group_results.append({
            "group": gkey,
            "n_runs": len(runs),
            "runs": runs_sorted,
            "query_text": gkey,
            "pair_compared": [a_name, b_name],
            "legs": legs,
            "n_legs_divergent": sum(1 for l in legs if l["divergent"]),
            "n_legs_not_applicable": sum(1 for l in legs if l["status"] == "NOT_APPLICABLE"),
            "group_verdict": "RUN_INSTABILITY_GENERALIZED" if group_divergent else "STABLE",
            "reported_only_diagnostics": pair_diagnostics(
                loaded[a_name]["bundle"], loaded[b_name]["bundle"]),
        })

    singletons = sorted(k for k, v in groups.items() if len(v) < 2)

    # ---- verdict ---------------------------------------------------------
    reasons = []
    if not frozen["all_match"]:
        reasons.append("frozen pin drift")
    if not population["all_match"]:
        reasons.append("population / mount-head pin drift")
    if not vac["all_hold"]:
        reasons.append("non-vacuity control failure")
    if len(comparable_groups) < 2:
        reasons.append("fewer than two same-query groups with >=2 runs")
    if not v5_ok:
        reasons.append("no comparable group carries >=2 counter-applicable runs "
                       "(V5)")

    if reasons:
        verdict, exit_code = "ENVIRONMENT_OR_VACUOUS", EXIT_ENVIRONMENT
        verdict_detail = "; ".join(reasons)
    elif n_divergent > 0:
        verdict, exit_code = "RUN_INSTABILITY_GENERALIZED", EXIT_GENERALIZED
        verdict_detail = "; ".join(
            f"group '{g['group']}': {[l['gate'] for l in g['legs'] if l['divergent']]}"
            for g in group_results if g["group_verdict"] == "RUN_INSTABILITY_GENERALIZED")
    else:
        verdict, exit_code = "STABILITY_NOT_GENERALIZED", EXIT_STABLE
        verdict_detail = (
            "every applicable accepted gate returns the same verdict for every run "
            "inside every same-query group; the accepted P1 finding is RETAINED as an "
            "isolated pair result and does not generalize on this population"
        )

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": hypothesis.get("direction_version"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hypothesis_sha256": sha256_file(repo / HYPOTHESIS_RELPATH),
        "freeze_record_sha256": sha256_file(repo / FREEZE_RELPATH),
        "product_mount": str(mount),
        "product_mount_head": mount_head(mount),
        "environment": numeric_environment(),
        "frozen_pin_verification": frozen,
        "population_pin_verification": population,
        "scored_statuses_from_frozen_rubric": scored_statuses,
        "non_vacuity": vac,
        "v5_counter_stage_capability": {"holds": v5_ok, "per_group": v5_detail},
        "group_structure": group_structure,
        "single_query_runs_not_comparable": singletons,
        "per_run": per_run,
        "groups": group_results,
        "n_groups_comparable": len(comparable_groups),
        "n_groups_divergent": n_divergent,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "exit_code": exit_code,
        "claim_ceiling": hypothesis.get("claim_ceiling"),
        "human_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
        "unserved_packet_39275520116": {
            "status": "NOT_TOUCHED_BY_THIS_SWEEP",
            "falsification_verdict": "WITHHELD_PENDING_SERVE",
            "note": "this instrument reads only results/product/live_slice/*; it "
                    "computes no gate, no verdict and no admission record on any "
                    "gate-packet directory",
        },
    }
    return record, exit_code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mount", default=None, help="accepted product mount")
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "scratch"))
    ap.add_argument("--out", default=None,
                    help="output path (scratch runs MUST pass this)")
    args = ap.parse_args(argv)

    mount = Path(args.mount) if args.mount else resolve_mount()
    if mount is None or not mount.is_dir():
        print("ENVIRONMENT_OR_VACUOUS: accepted product mount not found", file=sys.stderr)
        return EXIT_ENVIRONMENT

    record, code = run(mount, REPO_ROOT, str(args.run_id))
    out = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "evaluation" / "cross_run_stability_sweep"
        / f"{args.run_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=False)
                   + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": record.get("verdict"),
        "exit_code": code,
        "n_groups_comparable": record.get("n_groups_comparable"),
        "n_groups_divergent": record.get("n_groups_divergent"),
        "out": str(out),
    }, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
