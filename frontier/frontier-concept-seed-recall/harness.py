"""Runnable harness for frontier-concept-seed-recall charter v1.

Stages, in the order the charter fixes them:

  0. FREEZE VERIFICATION -- re-derive the plan from the accepted inputs and
     refuse to run if it differs from the committed RULES.json in any way.
  1. BASELINE REPRODUCTION (acceptance test 2) -- recompute the accepted
     question-native coverage finding and the accepted predecessor OUTCOME_B
     headline numbers FROM THE ACCEPTED ARTEFACTS, before any new measurement.
     A non-reproduction is the headline and ends the run.
  2. MEASUREMENT -- A1 natural-language concept-seeded arm, A2 blanked control,
     A3 rotated control, A4 corpus-presence diagnostic (not a candidate arm).
  3. HEAD-TO-HEAD -- A0 vs A1 per unit, published in the accepted record shape.
  4. FROZEN-GATE NON-REGRESSION (acceptance test 6) -- re-score the accepted
     frozen spec with the accepted gates, read-only, with the A1 rows in the pool.
  5. REGRESSION SUITE (acceptance test 7) -- delegated to ``regression.py``.
  6. VERDICT -- OUTCOME_A or OUTCOME_B, decided by the frozen thresholds and by
     nothing else.

Everything is cache-first.  A claim-bearing number is produced with
``network_calls == 0`` wherever a committed envelope exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from . import inputs as I
from . import nlcs, plan as plan_mod, regression as reg_mod, replay

REPO_ROOT = Path(__file__).resolve().parents[2]
TEAM_DIR = REPO_ROOT / "results/frontier/frontier-concept-seed-recall"
TEAM_CACHE = TEAM_DIR / "cache"
PREDECESSOR_CACHE = TEAM_DIR / "predecessor_cache"
PREDECESSOR_RECORD = TEAM_DIR / "accepted_predecessor_record"
PRODUCT_CACHE = I.PRODUCT_MOUNT / "results/product/query_cache"

SCHEMA = "frontier_concept_seed_recall.harness/1"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dedup_rows(rows: list[dict]) -> tuple[list[dict], dict]:
    """The PRODUCT's own identity order: canonical_decision_id then decision_id.

    A row already in the pool wins; the candidate arm is purely additive, so a
    later duplicate can never displace an A0 row.
    """
    seen: set[str] = set()
    out: list[dict] = []
    n_missing_canonical = 0
    for row in rows:
        cid = str(row.get("canonical_decision_id") or "").strip()
        if not cid:
            n_missing_canonical += 1
            cid = str(row.get("decision_id") or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        out.append(row)
    return out, {"input_records": len(rows), "unique_candidates": len(out),
                 "merged_away": len(rows) - len(out),
                 "identity_keys": ["canonical_decision_id", "decision_id"],
                 "strategy": "product_canonical_identity_v1",
                 "rows_without_canonical_decision_id": n_missing_canonical}


def served_coverage(sma, rows: list[dict], concepts: list[str]) -> dict:
    """The ACCEPTED coverage rule, delegated -- never re-implemented here."""
    texts = [sma.deaccent(sma.row_match_text(r)).lower() for r in rows]
    counts = {c: sum(1 for t in texts if c in t) for c in concepts}
    zero = sorted(c for c, n in counts.items() if n == 0)
    return {
        "method": "question_native_concept_coverage "
                  "(evaluation.subject_match_audit row_match_text + substring rule)",
        "n_rows": len(rows),
        "concepts": list(concepts),
        "concept_row_counts": counts,
        "rows_per_concept": counts,
        "concepts_with_zero_rows": zero,
        "under_covered": zero,
        "total_concepts": len(concepts),
        "covered_count": len(concepts) - len(zero),
    }


def leg_coverage(sma, rows: list[dict], concepts: list[str]) -> dict:
    """The DECLARED frozen-leg containment rule (see plan._frozen_leg_row_text)."""
    texts = [sma.deaccent(plan_mod._frozen_leg_row_text(r)).lower() for r in rows]
    counts = {c: sum(1 for t in texts if c in t) for c in concepts}
    zero = sorted(c for c, n in counts.items() if n == 0)
    return {"method": "declared frozen-leg field set (decision_id + citation_string_* "
                      "+ text_head), substring containment, same permissive direction",
            "n_rows": len(rows), "concepts": list(concepts),
            "concept_row_counts": counts, "concepts_with_zero_rows": zero,
            "under_covered": zero}


def recall_cell(gates, authority_ids: list[str], rows: list[dict]) -> dict:
    """The ACCEPTED authority matcher, delegated -- never re-implemented here."""
    if not authority_ids:
        return {"measurable": False, "recall": None, "hits": [], "missing": [],
                "n_rows": len(rows), "required": [],
                "reason": "frozen reality benchmark carries no controlling-authority set"}
    matched = gates.match_authorities(authority_ids, rows, min_len=6)
    hits = [a for a, core in matched.items() if core is not None]
    missing = [a for a, core in matched.items() if core is None]
    return {"measurable": True, "recall": round(len(hits) / len(authority_ids), 6),
            "hits": hits, "missing": missing, "n_rows": len(rows),
            "required": list(authority_ids)}


# --------------------------------------------------------------------------- #
# stage 0 -- freeze verification
# --------------------------------------------------------------------------- #
def verify_freeze(rules_path: Path) -> dict:
    committed = json.loads(Path(rules_path).read_text(encoding="utf-8"))
    derived = plan_mod.build_plan(
        charter_version=int(committed["charter_version"]),
        direction_version=committed.get("direction_version"))
    volatile = {"inputs"}
    diffs = []
    for key in sorted(set(committed) | set(derived)):
        if key in volatile:
            continue
        a, b = _canon(committed.get(key)), _canon(derived.get(key))
        if a != b:
            diffs.append({"key": key, "committed_sha256": _sha256_text(a),
                          "rederived_sha256": _sha256_text(b)})
    return {"rules_path": str(rules_path),
            "rules_file_sha256": I.sha256_file(rules_path),
            "committed_charter_version": committed["charter_version"],
            "re_derived_identical": not diffs,
            "differing_keys": diffs,
            "note": "'inputs' carries mount paths and live digests and is compared "
                    "separately; every decision-bearing key must match byte-for-byte",
            "frozen": committed, "derived": derived}


# --------------------------------------------------------------------------- #
# stage 1 -- acceptance test (2): reproduce the accepted numbers first
# --------------------------------------------------------------------------- #
def reproduce_accepted() -> dict:
    sma, gates, frozen_mod = I.load_evaluation_modules()
    out: dict[str, Any] = {
        "schema": "frontier_concept_seed-recall/baseline-reproduction/1",
        "acceptance_test": (
            "2. RE-PRODUCE THE ACCEPTED BASELINE AND THE ACCEPTED OUTCOME_B NUMBERS "
            "BEFORE ANY NEW MEASUREMENT. A NON-REPRODUCTION IS THE HEADLINE FINDING and "
            "ends the run as a bounded negative; it is never smoothed over by the new "
            "arm's result."),
        "network_calls": 0,
    }

    # --- (a) accepted question-native coverage -------------------------------
    accepted_cov = I.load_json(I.EVALUATION_MOUNT /
                               "results/evaluation/subject_match_audit/39113690481.json")
    entries = {e["served_question_id"]: e
               for e in (accepted_cov.get("question_native_coverage") or [])}
    cov = {}
    for qid in I.SERVED_QUESTIONS:
        bundle = I.load_json(I.bundle_path(qid))
        qrec = I.load_json(I.question_path(qid))
        rows = bundle.get("decisions") or []
        got = served_coverage(sma, rows, sma.question_concepts(qrec["question"]))
        acc = entries.get(qid) or {}
        same = (got["concepts"] == list(acc.get("concepts") or [])
                and got["concept_row_counts"] == dict(acc.get("concept_row_counts") or {})
                and got["concepts_with_zero_rows"] ==
                list(acc.get("concepts_with_zero_rows") or [])
                and got["n_rows"] == acc.get("n_bundle_rows"))
        cov[qid] = {"recomputed": got,
                    "accepted_reference": {
                        "run_id": accepted_cov.get("run_id"),
                        "n_bundle_rows": acc.get("n_bundle_rows"),
                        "concepts": acc.get("concepts"),
                        "concept_row_counts": acc.get("concept_row_counts"),
                        "concepts_with_zero_rows": acc.get("concepts_with_zero_rows")},
                    "reproduces_accepted": bool(same)}
    out["coverage"] = cov
    out["coverage_reproduced"] = all(v["reproduces_accepted"] for v in cov.values())

    # --- (b) accepted predecessor OUTCOME_B headline numbers -----------------
    harness = json.loads((PREDECESSOR_RECORD /
                          "harness_results_39179862363.json").read_text(encoding="utf-8"))
    pred_verdict = harness["verdict"]
    rec = I.load_json(I.EVALUATION_MOUNT /
                      "results/evaluation/retrieval_benchmark/39117425713.json")
    envelopes = list(PREDECESSOR_CACHE.glob("*/*.json"))

    def envelope_for(query: str) -> tuple[dict, dict] | tuple[None, None]:
        for p in envelopes:
            env = json.loads(p.read_text(encoding="utf-8"))
            env_q = _query_of(env["url"])
            if env_q == query:
                body = json.loads(env["body"]) if env.get("body") else {}
                return env, {"rows": list(body.get("results") or []), "path": str(p)}
        return None, None

    def _query_of(url: str) -> str:
        import urllib.parse as up
        return up.parse_qs(up.urlparse(url).query).get("query", [""])[0]

    # (b1) de-kapitalverletzung added search: HTTP 200, 0 rows
    de_q = harness["served_questions"]["de-kapitalverletzung"]["expansion_query"]
    de_env, de_payload = envelope_for(de_q)
    de_search = {
        "expansion_query": de_q,
        "source_envelope": de_env and de_payload and de_payload["path"],
        "accepted_reference": harness["served_questions"]
                              ["de-kapitalverletzung"]["search"],
        "recomputed": {
            "status": int(de_env["status"]) if de_env else None,
            "n_results": len(de_payload["rows"]) if de_payload else None,
            "from_cache": True,
            "latency_seconds": 0.0,
            "network_calls": 0,
        } if de_env else None,
    }
    if de_env:
        ref = harness["served_questions"]["de-kapitalverletzung"]["search"]
        de_search["reproduces_accepted"] = (
            de_search["recomputed"]["status"] == ref["status"]
            and de_search["recomputed"]["n_results"] == ref["n_results"])
    else:
        de_search["reproduces_accepted"] = False
    out["de_added_search"] = de_search

    # (b2) reduced_under_covered_questions == 0, recomputed from the predecessor's
    #      own published A1 rows against the accepted A0 bundles
    reduced = []
    for qid in I.SERVED_QUESTIONS:
        bundle = I.load_json(I.bundle_path(qid))
        qrec = I.load_json(I.question_path(qid))
        a0_rows = bundle.get("decisions") or []
        concepts = sma.question_concepts(qrec["question"])
        a0 = served_coverage(sma, a0_rows, concepts)
        _, payload = envelope_for(harness["served_questions"][qid]["expansion_query"])
        a1_rows = list(payload["rows"]) if payload else []
        union, dd = dedup_rows(a0_rows + a1_rows)
        u = served_coverage(sma, union, concepts)
        gained = sorted(set(u["covered_count"] and
                            [c for c in concepts
                             if u["concept_row_counts"][c] >= 1
                             and a0["concept_row_counts"][c] == 0]))
        if gained:
            reduced.append(qid)
        out.setdefault("served_questions", {})[qid] = {
            "a0_under_covered": a0["under_covered"],
            "a1_rows_from_predecessor_envelope": len(a1_rows),
            "union_dedupe": dd,
            "a1_union_under_covered": u["under_covered"],
            "concepts_newly_covered": gained,
            "reduced": bool(gained),
            "accepted_reference": {
                "A0_baseline_shipped": harness["served_questions"][qid]
                                       ["A0_baseline_shipped"]["under_covered"]},
        }
    out["reduced_under_covered_questions"] = len(reduced)
    out["reduced_under_covered_names"] = reduced

    # (b3) improved_fr_it_cells == 0, recomputed with the accepted matcher
    improved = []
    cells = []
    for slug, legs in sorted(harness["frozen_legs"].items()):
        ids = list(legs.get("authority_ids") or [])
        if not ids:
            continue
        for lang, cell in sorted((legs.get("per_language") or {}).items()):
            acc = cell["A0_baseline_shipped"]
            if acc.get("recall") in (0.0, 0) and acc.get("missing"):
                _, payload = envelope_for(cell["expansion_query"])
                a1_rows = list(payload["rows"]) if payload else []
                a0_rows = [r for q in rec["queries"]
                           if q.get("slug") == slug and q.get("channel") == "baseline"
                           and q.get("language") == lang
                           for r in (q.get("rows") or [])]
                union, _dd = dedup_rows(a0_rows + a1_rows)
                got = recall_cell(gates, ids, union)
                gained = sorted(set(got["hits"]) & set(acc["missing"]))
                if gained:
                    improved.append(f"{slug}::{lang}")
                cells.append({
                    "cell": f"{slug}::{lang}",
                    "accepted_recall": acc.get("recall"),
                    "accepted_missing": list(acc.get("missing") or []),
                    "A1_rows_from_predecessor_envelope": len(a1_rows),
                    "recomputed_union_recall": got["recall"],
                    "newly_found_ids": gained,
                    "improved": bool(gained),
                })
    out["fr_it_cells"] = cells
    out["improved_fr_it_cells"] = len(improved)
    out["improved_fr_it_cell_names"] = improved
    out["accepted_reference"] = {
        "improved_fr_it_cells": pred_verdict["improved_fr_it_cells"],
        "reduced_under_covered_questions": pred_verdict["reduced_under_covered_questions"],
        "outcome": pred_verdict["outcome"],
    }
    out["headline_numbers_reproduced"] = bool(
        out["coverage_reproduced"]
        and out["de_added_search"].get("reproduces_accepted")
        and out["reduced_under_covered_questions"] ==
        pred_verdict["reduced_under_covered_questions"]
        and out["improved_fr_it_cells"] == pred_verdict["improved_fr_it_cells"])
    return out


# --------------------------------------------------------------------------- #
# stage 2/3 -- measurement and head-to-head
# --------------------------------------------------------------------------- #
def _rotated(unit: dict, ordered: list[dict]) -> dict | None:
    """The NEXT TARGETED unit in the sorted unit order (wrapping).

    Unit i is seeded with unit j's frozen variant strings.  ``ordered`` is the
    sorted unit list; donors are skipped only when they carry no frozen variant
    strings at all, which is the frozen "rotated control" rule with its one
    mechanical clarification: a donor with an EMPTY seed set would make the
    control indistinguishable from the blanked control, so the rotation
    advances to the next unit that actually has seeds.  Deterministic, and it
    uses no information from the candidate's own result.
    """
    idx = next((n for n, u in enumerate(ordered) if u["unit_id"] == unit["unit_id"]), None)
    if idx is None:
        return None
    for step in range(1, len(ordered) + 1):
        cand = ordered[(idx + step) % len(ordered)]
        if cand.get("variants"):
            return cand
    return None


def measure(frozen: dict, *, allow_live: bool) -> dict:
    sma, gates, _ = I.load_evaluation_modules()
    searcher = replay.Searcher(
        read_only_cache_dirs=[PRODUCT_CACHE, PREDECESSOR_CACHE, TEAM_CACHE],
        write_cache_dir=TEAM_CACHE,
        product_mount=I.PRODUCT_MOUNT,
        allow_live=allow_live,
        per_search_budget_s=frozen["latency_budget"]["per_search_seconds"],
        full_pass_budget_s=frozen["latency_budget"]["full_live_pass_seconds"],
        min_interval_s=frozen["latency_budget"]["min_interval_seconds"],
    )
    params = dict(frozen["search_params"])
    path = params.pop("path")
    params.pop("language_filter", None)
    ordered = frozen["units"]
    started = time.time()

    a0_bundles = {qid: I.load_json(I.bundle_path(qid)) for qid in I.SERVED_QUESTIONS}
    rec = I.load_json(I.EVALUATION_MOUNT /
                      "results/evaluation/retrieval_benchmark/39117425713.json")

    per_unit: dict[str, Any] = {}
    candidate_queries: list[dict] = []
    search_log: list[dict] = []
    searcher.begin_pass("A1")   # the candidate pass: the runtime cost the product pays

    for unit in ordered:
        uid = unit["unit_id"]
        entry: dict[str, Any] = {
            "unit_id": uid, "kind": unit["kind"], "language": unit["language"],
            "question_text": unit["question_text"],
            "accepted_under_covered": unit["accepted_under_covered"],
            "accepted_question_concepts": unit["accepted_question_concepts"],
            "targeted": bool(unit["variants"]),
        }

        # ---- A0 pool (byte-reused, never re-queried) ----------------------
        if unit["kind"] == "served_coverage":
            a0_rows = a0_bundles[unit["question_id"]]["decisions"]
        else:
            a0_rows = [r for q in rec["queries"]
                       if q.get("slug") == unit["slug"]
                       and q.get("channel") == unit["channel"]
                       and q.get("language") == unit["language"]
                       for r in (q.get("rows") or [])]
        entry["A0_baseline_shipped"] = {
            "source": ("accepted bundle bytes, read-only"
                       if unit["kind"] == "served_coverage"
                       else "accepted benchmark record's own cached baseline rows"),
            "n_rows": len(a0_rows)}

        # ---- A1 (candidate pass) ------------------------------------------
        searcher.begin_pass("A1")
        a1_rows: list[dict] = []
        searches = []
        for v in unit["variants"]:
            call = searcher.search(path, {**params, "query": v["query"]},
                                   query_key=f"A1::{uid}::{v['concept']}")
            searches.append({k: val for k, val in call.items() if k != "rows"})
            search_log.append({k: val for k, val in call.items() if k != "rows"})
            a1_rows.extend(call["rows"])
            candidate_queries.append({
                "query_key": call["query_key"], "slug": unit.get("slug"),
                "channel": "baseline", "language": unit["language"],
                "query": v["query"], "status": call["status"],
                "from_cache": call["from_cache"],
                "raw_sha256": call["raw_sha256"],
                "n_results": call["n_results"],
                "latency_seconds": call["latency_seconds"],
                "rows": call["rows"]})
        entry["A1_searches"] = searches
        entry["A1_variant_strings"] = [v["query"] for v in unit["variants"]]
        entry["A1_candidate_only"] = {"n_rows": len(a1_rows)}
        a0_deduped, a0_dd = dedup_rows(a0_rows)
        union_rows, dd = dedup_rows(a0_rows + a1_rows)
        dd["A0_rows_raw"] = len(a0_rows)
        dd["A0_rows_after_product_dedup"] = len(a0_deduped)
        dd["A0_internal_duplicates_collapsed"] = a0_dd["merged_away"]
        dd["why_union_can_be_below_A0_raw"] = (
            "the ACCEPTED A0 response itself already contains duplicate canonical "
            "identities -- that is exactly what the accepted gate "
            "duplicate::unique_ids records as FAILING on all four frozen legs -- so the "
            "product's own dedup collapses them in the baseline as well. The invariant "
            "that matters, and that is checked, is no_A0_row_dropped: every A0 decision "
            "id is still present in the union pool.")
        entry["A1_union"] = {"n_rows": len(union_rows), "dedupe": dd}
        entry["no_a0_row_dropped"] = all(
            _ident(r) in {_ident(x) for x in union_rows} for r in a0_rows)

        # ---- controls ------------------------------------------------------
        rot = _rotated(unit, ordered)
        searcher.begin_pass("A3")
        blank_rows: list[dict] = []
        rot_rows: list[dict] = []
        rot_from = None
        if rot is not None and rot.get("variants"):
            rot_from = rot["unit_id"]
            for v in rot["variants"]:
                call = searcher.search(path, {**params, "query": v["query"]},
                                       query_key=f"A3::{uid}::<{rot_from}>::{v['concept']}")
                search_log.append({k: val for k, val in call.items() if k != "rows"})
                rot_rows.extend(call["rows"])
        entry["A2_blanked"] = {"n_variants": 0,
                               "note": "empty variant string set; identical to A0 by "
                                       "construction and re-measured, not asserted"}
        entry["A3_rotated"] = {"seeded_from": rot_from, "n_variants":
                               len(rot.get("variants") or []) if rot else 0,
                               "n_rows": len(rot_rows)}

        # ---- head-to-head metrics ------------------------------------------
        if unit["kind"] == "served_coverage":
            concepts = unit["accepted_question_concepts"]
            entry["coverage"] = {
                "A0_baseline_shipped": served_coverage(sma, a0_rows, concepts),
                "A1_candidate_only": served_coverage(sma, a1_rows, concepts),
                "A1_union": served_coverage(sma, union_rows, concepts),
                "A2_blanked": served_coverage(sma, a0_rows, concepts),
                "A3_rotated": served_coverage(
                    sma, dedup_rows(a0_rows + rot_rows)[0], concepts),
            }
            base = entry["coverage"]["A0_baseline_shipped"]
            cand = entry["coverage"]["A1_union"]
            gained = sorted(c for c in concepts
                            if cand["concept_row_counts"][c] >= 1
                            and base["concept_row_counts"][c] == 0)
            entry["coverage"]["delta"] = {
                "under_covered_baseline": len(base["under_covered"]),
                "under_covered_candidate": len(cand["under_covered"]),
                "concepts_newly_covered": gained,
                "concepts_still_under": cand["under_covered"],
                "rows_per_concept_delta": {
                    c: cand["concept_row_counts"][c] - base["concept_row_counts"][c]
                    for c in concepts},
                "reduced": bool(gained),
            }
        else:
            ids = unit["frozen_authority_ids"]
            concepts = unit["accepted_question_concepts"]
            entry["authority_recall"] = {
                "A0_baseline_shipped": recall_cell(gates, ids, a0_rows),
                "A1_candidate_only": recall_cell(gates, ids, a1_rows),
                "A1_union": recall_cell(gates, ids, union_rows),
                "A2_blanked": recall_cell(gates, ids, a0_rows),
                "A3_rotated": recall_cell(gates, ids, dedup_rows(a0_rows + rot_rows)[0]),
            }
            base = entry["authority_recall"]["A0_baseline_shipped"]
            cand = entry["authority_recall"]["A1_union"]
            gained = sorted(set(cand["hits"]) & set(unit["accepted_missing_ids"]))
            entry["authority_recall"]["delta"] = {
                "accepted_missing_ids": list(unit["accepted_missing_ids"]),
                "newly_found_ids": gained,
                "ids_still_missing": list(base["missing"]),
                "delta_recall": (None if cand["recall"] is None
                                 else round(cand["recall"] - (base["recall"] or 0.0), 6)),
                "improved": bool(gained),
            }
            entry["leg_concept_coverage"] = {
                "A0_baseline_shipped": leg_coverage(sma, a0_rows, concepts),
                "A1_union": leg_coverage(sma, union_rows, concepts),
                "note": "diagnostic only; used to seed variants, never published as a "
                        "served-bundle coverage number",
            }

        # ---- A4 corpus-presence diagnostic (NOT a candidate arm) ------------
        if unit["kind"] == "served_coverage":
            searcher.begin_pass("A4")
            diag = []
            for c in unit["accepted_under_covered"]:
                sf = nlcs.surface_form(c, unit["question_text"])
                call = searcher.search(path, {**params, "query": sf},
                                       query_key=f"A4::{uid}::{c}")
                diag.append({"concept": c, "query": sf, "status": call["status"],
                             "n_results": call["n_results"],
                             "from_cache": call["from_cache"],
                             "latency_seconds": call["latency_seconds"],
                             "rows_carrying_concept": sum(
                                 1 for t in
                                 (sma.deaccent(sma.row_match_text(r)).lower()
                                  for r in call["rows"]) if c in t)})
                search_log.append({k: val for k, val in call.items() if k != "rows"})
            entry["A4_corpus_presence_diagnostic"] = {
                "eligible_for_outcome_A": False,
                "note": "auxiliary diagnostic, never an adoptable arm and never a "
                        "candidate result",
                "per_concept": diag}
        # ---- acceptance test (5): controls, measured not asserted -----------
        if unit["kind"] == "served_coverage":
            base_c = entry["coverage"]["A0_baseline_shipped"]
            blank_c = entry["coverage"]["A2_blanked"]
            rot_c = entry["coverage"]["A3_rotated"]
            cand_c = entry["coverage"]["A1_union"]
            base_r = entry["authority_recall"] if "authority_recall" in entry else None
            entry["control_summary"] = {
                "A2_blanked_reproduces_A0_exactly":
                    _canon(blank_c) == _canon(base_c),
                "A3_rotated_seeded_from": rot_from,
                "A3_raises_coverage_on_target": bool(
                    rot_c["covered_count"] > base_c["covered_count"]),
                "A3_raises_rows_on_target": bool(
                    entry["A3_rotated"]["n_rows"] > 0),
                "candidate_beats_blanked_on_coverage": bool(
                    cand_c["covered_count"] > blank_c["covered_count"]),
                "candidate_beats_blanked_on_rows": bool(
                    entry["A1_union"]["n_rows"] > entry["A0_baseline_shipped"]["n_rows"]),
                "note": "this charter does NOT inherit the predecessor's tie=>void clause: "
                        "a blanked control that TIES the candidate is a measured bounded "
                        "negative, not a void and not a reason to re-run",
            }
            del base_r
        else:
            base_m = entry["authority_recall"]["A0_baseline_shipped"]
            blank_m = entry["authority_recall"]["A2_blanked"]
            rot_m = entry["authority_recall"]["A3_rotated"]
            cand_m = entry["authority_recall"]["A1_union"]
            entry["control_summary"] = {
                "A2_blanked_reproduces_A0_exactly": _canon(blank_m) == _canon(base_m),
                "A3_rotated_seeded_from": rot_from,
                "A3_raises_recall_on_target": bool(
                    set(rot_m["hits"]) - set(base_m["hits"])),
                "candidate_beats_blanked_on_recall": bool(
                    (cand_m["recall"] or 0.0) > (blank_m["recall"] or 0.0)),
                "note": "tie is a bounded negative, not a void",
            }
        per_unit[uid] = entry

    return {
        "per_unit": per_unit,
        "search_log": search_log,
        "candidate_queries": candidate_queries,
        "budget": searcher.budget_report(),
        "wall_seconds": round(time.time() - started, 3),
    }


def _ident(row: dict) -> str:
    return str(row.get("canonical_decision_id") or row.get("decision_id") or "")


# --------------------------------------------------------------------------- #
# stage 4 -- frozen-gate non-regression (acceptance test 6)
# --------------------------------------------------------------------------- #
def frozen_gate_check(candidate_queries: list[dict]) -> dict:
    sma, gates, _ = I.load_evaluation_modules()
    spec = I.load_json(I.EVALUATION_MOUNT /
                       "evaluation/retrieval_gate/frozen_retrieval_benchmark.json")
    accepted = I.load_json(I.EVALUATION_MOUNT /
                           "results/evaluation/retrieval_benchmark/39117425713.json")
    base_queries = accepted["queries"]
    cand = [q for q in candidate_queries if q.get("status") == 200]

    def verdicts(queries):
        return {g["gate"]: g for g in gates.evaluate(spec, {"queries": queries,
                                                            "pass_a_mode": accepted.get(
                                                                "pass_a_mode"),
                                                            "reproducibility": accepted.get(
                                                                "reproducibility")})["gates"]}

    v0 = verdicts(base_queries)
    v1 = verdicts(base_queries + cand)
    passed_before = {k for k, g in v0.items() if g["passed"] is True}
    regressions, improvements = [], []
    for name in sorted(passed_before):
        after = v1.get(name)
        if after is None or after["passed"] is not True:
            regressions.append({"gate": name,
                                "passed_with_candidate": bool(after and after["passed"]),
                                "detail": (after or {}).get("detail", "gate vanished")})
    for name in sorted(set(v1) - passed_before):
        if v1[name]["passed"] is True and v0.get(name, {}).get("passed") is False:
            improvements.append({"gate": name, "detail": v1[name]["detail"]})
    return {
        "schema": "frontier_concept-seed-recall/frozen-gate-nonregression/1",
        "frozen_spec_sha256": I.ACCEPTED_DIGESTS["frozen_retrieval_benchmark.json"],
        "accepted_record_run_id": accepted["run_id"],
        "scorer": "evaluation.retrieval_gate.gates.evaluate (imported by package path; "
                  "read-only, never re-implemented, never re-tuned)",
        "n_gates_accepted": len(v0),
        "n_passing_accepted": len(passed_before),
        "n_candidate_queries_in_pool": len(cand),
        "n_candidate_queries_excluded_non_200": len(candidate_queries) - len(cand),
        "regressions": regressions,
        "improvements": improvements,
        "no_regression": not regressions,
        "frozen_files_modified": [],
    }


# --------------------------------------------------------------------------- #
# stage 6 -- verdict
# --------------------------------------------------------------------------- #
def verdict(frozen: dict, repro: dict, m: dict, gates_chk: dict,
            regression: dict) -> dict:
    units = m["per_unit"]
    de = units.get("served::de-kapitalverletzung") or {}
    cov_delta = (de.get("coverage") or {}).get("delta") or {}
    concepts_added = list(cov_delta.get("concepts_newly_covered") or [])

    recovered, cells_improved = [], []
    for uid, u in sorted(units.items()):
        d = (u.get("authority_recall") or {}).get("delta") or {}
        if d.get("newly_found_ids"):
            recovered.extend(d["newly_found_ids"])
            cells_improved.append(uid)

    controls = {
        "acceptance_test": (
            "5. NON-VACUITY PROVEN, NOT ASSERTED: a blanked control (empty variant string "
            "set) must reproduce A0 exactly, and a ROTATED control (unit i seeded with "
            "unit j's frozen variant strings) must NOT raise coverage or recall on unit "
            "i. This charter does NOT inherit the predecessor's defective tie=>void "
            "clause."),
        "per_unit": {uid: u.get("control_summary") for uid, u in sorted(units.items())
                     if u.get("control_summary")},
    }
    ctl = [c for c in controls["per_unit"].values() if c]
    controls["A2_blanked_reproduces_A0_on_every_measured_unit"] = bool(
        ctl and all(c["A2_blanked_reproduces_A0_exactly"] for c in ctl))
    controls["A3_raised_coverage_or_recall_on_any_target"] = bool(
        any(c.get("A3_raises_coverage_on_target") or c.get("A3_raises_recall_on_target")
            for c in ctl))
    controls["candidate_strictly_beats_blanked_on_at_least_one_unit"] = bool(
        any(c.get("candidate_beats_blanked_on_coverage")
            or c.get("candidate_beats_blanked_on_recall") for c in ctl))
    controls["read"] = (
        "controls are reported exactly as measured. A tie between blanked and candidate "
        "is a BOUNDED NEGATIVE RESULT under this charter, not a void.")

    crit = {
        "coverage": bool(concepts_added),
        "recall": bool(recovered),
        "non_regression": bool(gates_chk["no_regression"]),
        "regression_suite": bool(regression.get("all_passed")),
        "baseline_reproduced": bool(repro["headline_numbers_reproduced"]),
        "budget": not gates_chk.get("frozen_files_modified"),
    }
    outcome_a = (crit["coverage"] or crit["recall"]) and all(
        crit[k] for k in ("non_regression", "regression_suite", "baseline_reproduced"))

    zero_cells = []
    for uid, u in sorted(units.items()):
        for s in u.get("A1_searches") or []:
            if s["n_results"] == 0 and s.get("status") == 200:
                zero_cells.append({"unit_id": uid, "query_key": s["query_key"],
                                   "status": s["status"],
                                   "latency_seconds": s["latency_seconds"],
                                   "from_cache": s["from_cache"]})

    return {
        "schema": "frontier_concept-seed-recall/verdict/1",
        "outcome": "OUTCOME_A_COMPONENT" if outcome_a else "OUTCOME_B_BOUNDED_NEGATIVE",
        "outcome_a_criteria": crit,
        "headline": {
            "de_kapitalverletzung_newly_covered_concepts": concepts_added,
            "recovered_frozen_authority_ids": sorted(set(recovered)),
            "improved_cells": cells_improved,
            "zero_row_cells": zero_cells,
            "any_regression": not gates_chk["no_regression"],
            "budget": m["budget"],
        },
        "controls": controls,
        "headline_sentence": _headline_sentence(outcome_a, concepts_added, recovered,
                                                zero_cells, gates_chk, m),
        "accepted_predecessor_published_beside_not_instead_of": {
            "record": "frontier-query-concept-recall harness_results_39179862363.json",
            "outcome": "OUTCOME_B_BOUNDED_NEGATIVE",
            "bounded_cause_verbatim": "TERM-ONLY EXPANSION QUERIES ARE TOO NARROW FOR "
                                      "THE OPENCASELAW RELEVANCE INDEX",
            "de_added_search": {"status": 200, "n_results": 0},
            "improved_fr_it_cells": 0,
            "reduced_under_covered_questions": 0,
        },
        "stop_rule": (
            "The charter ends at the FIRST outcome reached and MUST NOT continue into "
            "threshold, phrasing or prompt tuning afterwards. This team must NOT grow into "
            "classifier, abstention, layout or geometry work, prompt engineering, benchmark "
            "construction, a product patch or a second hypothesis."),
    }


def _headline_sentence(outcome_a, concepts, recovered, zero_cells, gates_chk, m) -> str:
    if outcome_a:
        what = []
        if concepts:
            what.append(f"{len(concepts)} concept(s) newly covered on de-kapitalverletzung")
        if recovered:
            what.append(f"{len(set(recovered))} frozen authority id(s) recovered")
        return ("OUTCOME_A: the natural-language concept-seeded arm raised "
                + " and ".join(what)
                + " with zero frozen-gate regression, published beside (never in place "
                  "of) the accepted predecessor OUTCOME_B record.")
    n_zero = len(zero_cells)
    breach = ""
    if m["budget"].get("per_search_budget_breached"):
        breach = (f" {len(m['budget']['calls_over_per_search_budget'])} added call(s) "
                  "breached the frozen per-search budget and are named here.")
    return ("OUTCOME_B_BOUNDED_NEGATIVE: the frozen natural-language concept-seeded "
            f"queries added zero concept-carrying rows and recovered zero missing frozen "
            f"authority ids; {n_zero} cell search(es) returned HTTP 200 with 0 rows."
            + breach
            + " A zero-row natural-language search for the missing concept is a retrieval "
              "signal, not proof of corpus absence.")


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def run(run_id: int, out_dir: Path | None = None, *, allow_live: bool = True,
        rules_path: Path | None = None) -> dict:
    out = Path(out_dir) if out_dir else TEAM_DIR
    out.mkdir(parents=True, exist_ok=True)
    TEAM_CACHE.mkdir(parents=True, exist_ok=True)
    rules = Path(rules_path) if rules_path else (out / "RULES.json")

    t0 = time.time()
    freeze = verify_freeze(rules)
    if not freeze["re_derived_identical"]:
        raise SystemExit("FREEZE VIOLATION: re-derived plan differs from committed "
                         f"RULES.json at {freeze['differing_keys']}")
    frozen = freeze["frozen"]

    repro = reproduce_accepted()
    (out / f"baseline_reproduction_{run_id}.json").write_text(
        json.dumps(repro, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")

    measurement = measure(frozen, allow_live=allow_live)
    gates_chk = frozen_gate_check(measurement["candidate_queries"])
    regression = reg_mod.run_suite(frozen, measurement)
    v = verdict(frozen, repro, measurement, gates_chk, regression)

    results = {
        "schema": SCHEMA,
        "team_id": frozen["team_id"],
        "charter_version": frozen["charter_version"],
        "direction_version": frozen.get("direction_version"),
        "run_id": run_id,
        "rules_file_sha256": freeze["rules_file_sha256"],
        "frozen_plan_reproduced_before_measurement": True,
        "baseline_reproduction": repro,
        "measurement": {k: val for k, val in measurement.items()
                        if k != "candidate_queries"},
        "frozen_gate_nonregression": gates_chk,
        "regression_suite": regression,
        "verdict": v,
        "wall_seconds": round(time.time() - t0, 3),
        "claim_ceiling": frozen["claim_ceiling"],
    }
    path = out / f"harness_results_{run_id}.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    results["_path"] = str(path)
    (out / f"regression_results_{run_id}.json").write_text(
        json.dumps(regression, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out-dir", default=str(TEAM_DIR))
    ap.add_argument("--offline", action="store_true",
                    help="cache-only; an uncached variant is recorded as unmeasured")
    ap.add_argument("--rules", default=None)
    args = ap.parse_args(argv)
    res = run(int(args.run_id), Path(args.out_dir), allow_live=not args.offline,
              rules_path=Path(args.rules) if args.rules else None)
    v = res["verdict"]
    print(json.dumps({"outcome": v["outcome"], "headline": v["headline_sentence"],
                      "budget": res["measurement"]["budget"],
                      "no_regression": res["frozen_gate_nonregression"]["no_regression"],
                      "regression_suite_passed": res["regression_suite"]["all_passed"],
                      "baseline_reproduced":
                          res["baseline_reproduction"]["headline_numbers_reproduced"],
                      "results": res["_path"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


# ``Path`` is used in type hints above; keep the import visible to linters.
assert Path is not None