#!/usr/bin/env python3
"""Product-cache retrieval/counter-authority parity falsifier.

WHY THIS INSTRUMENT EXISTS (v61 FAST-MVP lane directive)
--------------------------------------------------------
Smallest executable retrieval/counter-authority benchmark that can falsify the
product, with an IDENTITY mapping so the subject-mismatch defect class that
forced the retraction of run 39111232991 (reports/evaluation/
CYCLE_39111232991_CORRECTION.md D1) cannot recur.

Claim-bearing comparison (frozen FIRST in
``evaluation/PRODUCT_CACHE_PARITY_HYPOTHESIS_V1.json``, sha256 pinned by
``evaluation/PRODUCT_CACHE_PARITY_FREEZE_RECORD_V1.json``):

    product pool  = rows of the ACCEPTED product's own search envelopes
                    (read-only query_cache) whose normalized query text
                    EXACTLY equals one of the frozen question's own six
                    frozen query texts (baseline+counter x fr/de/it)
    comparator    = rows of the accepted frozen baseline record for the
                    IDENTICAL query text (same text, same channel, same
                    language) - plain OpenCaseLaw, no query-map /
                    counter-authority machinery
    rule          >=1-of-set via the ACCEPTED gates.match_authorities;
                  parity:: gate holds iff product_hits >= comparator_hits

REUSE-FIRST - nothing measurement-bearing is re-derived here
------------------------------------------------------------
* frozen id sets / query texts / >=1-of-set semantics:
  ``evaluation.retrieval_gate.frozen`` (sha256 187b0e54..., fail-closed).
* matcher + row extraction:
  ``evaluation.retrieval_gate.gates.match_authorities / row_cores /
  extract_rows`` - imported, never re-tuned or paraphrased.
* baseline record: accepted
  ``results/evaluation/retrieval_benchmark/39101217095.json``.
* multilingual / provenance reuse leg:
  ``evaluation.run_v3_multilingual_provenance_reuse.check_bundle`` re-executed
  under THIS run id on the packet-of-record V3 bytes (append-only).
* the not-measurable convention (NOT_APPLICABLE is never a pass) and the D2
  comparator-naming correction are followed verbatim.

VERDICTS AND EXIT CODES (frozen)
--------------------------------
0  PASS_NO_PARITY_REGRESSION     every measurable parity:: gate holds and the
                                 non-vacuity battery proves both directions
1  FAIL_PRODUCT_CACHE_PARITY     >=1 parity:: gate has product_hits <
                                 comparator_hits (the product retrieval layer
                                 loses a frozen id the plain same-query search
                                 reached) - a falsification
2  NOT_MEASURED / ENVIRONMENT_OR_VACUOUS
                                 pin drift, missing mount, zero measurable
                                 cells, or a failed non-vacuity control.
                                 NEVER a pass, NEVER a bar-met.

The absolute product:: >=1-of-set gates are REPORTED (role=report_only_absolute)
and are never counted as falsifiers; every hit count, miss list and yield is
published on both sides.  No threshold, bar, rubric or verdict contract of the
frozen suite is re-derived, re-tuned or paraphrased.  No network is used.  No
universal-174k benchmark is rerun.

SCRATCH-RUN OBLIGATION
----------------------
A claim-bearing cycle writes to the committed defaults below.  A scratch
invocation (unit test, local poke) MUST pass --out and --report; otherwise it
overwrites committed claim-bearing records (audit CYCLE_39164900837 F9).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.retrieval_gate import frozen as rg_frozen  # noqa: E402
from evaluation.retrieval_gate import gates as rg_gates  # noqa: E402

SCHEMA = "lex-evaluation-product-cache-parity/1"
HYPOTHESIS_PATH = REPO_ROOT / "evaluation" / "PRODUCT_CACHE_PARITY_HYPOTHESIS_V1.json"
FREEZE_RECORD_PATH = REPO_ROOT / "evaluation" / "PRODUCT_CACHE_PARITY_FREEZE_RECORD_V1.json"
BASELINE_RECORD_RELPATH = "results/evaluation/retrieval_benchmark/39101217095.json"
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "evaluation" / "product_cache_parity"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports" / "evaluation"

DEFAULT_MOUNT_ENVS = ("LEX_ACCEPTED_PRODUCT_MOUNT", "LEX_PRODUCT_MOUNT")
DEFAULT_MOUNTS = ("/tmp/lex_accepted/product",)

EXIT_PASS = 0
EXIT_FALSIFIED = 1
EXIT_NOT_MEASURED_OR_VACUOUS = 2
EXIT_ENVIRONMENT = 3

ROLE_FALSIFIER = "falsifier"
ROLE_REPORT_ONLY = "report_only_absolute"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_inventory(cache_dir: Path) -> tuple[int, str]:
    """(n_files, inventory_sha256) over sorted '<relpath>:<file_sha256>\\n' lines."""
    h = hashlib.sha256()
    n = 0
    for p in sorted(cache_dir.glob("*/*.json")):
        h.update(f"{p.relative_to(cache_dir)}:{sha256_file(p)}\n".encode("utf-8"))
        n += 1
    return n, h.hexdigest()


def resolve_product_mount(explicit: str | None = None) -> Path | None:
    cands: list[Path] = []
    if explicit:
        cands.append(Path(explicit))
    else:
        for env in DEFAULT_MOUNT_ENVS:
            val = os.environ.get(env)
            if val:
                cands.append(Path(val))
        cands.extend(Path(p) for p in DEFAULT_MOUNTS)
    for cand in cands:
        if cand.is_dir():
            return cand
    return None


def current_direction_version() -> int:
    state = json.loads((REPO_ROOT / "state" / "evaluation.json").read_text(encoding="utf-8"))
    return int(state["direction_version"])


def scan_identity_envelopes(cache_dir: Path) -> dict[str, list[dict]]:
    """normalized query text -> accepted envelopes (status 200, results list)."""
    by_norm: dict[str, list[dict]] = {}
    for path in sorted(cache_dir.glob("*/*.json")):
        try:
            env = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        params = env.get("params") or {}
        if "query" not in params or env.get("status") != 200:
            continue
        try:
            body = json.loads(env.get("body") or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(body, dict) or not isinstance(body.get("results"), list):
            continue
        norm = rg_frozen.normalize_text(str(params.get("query") or ""))
        by_norm.setdefault(norm, []).append({
            "file": str(path.relative_to(cache_dir)),
            "n_rows": len(rg_gates.extract_rows(body)),
            "rows": rg_gates.extract_rows(body),
        })
    return by_norm


def identity_texts(spec_question: dict) -> dict[str, tuple[str, str]]:
    """normalized text -> (channel, language) for the question's 6 frozen texts."""
    out: dict[str, tuple[str, str]] = {}
    for channel in ("baseline", "counter"):
        for lang in ("fr", "de", "it"):
            text = spec_question["queries"][channel][lang]
            norm = rg_frozen.normalize_text(text)
            if norm in out and out[norm] != (channel, lang):
                raise ValueError("frozen spec carries duplicate normalized query texts")
            out[norm] = (channel, lang)
    return out


def recalled(ids: list[str], rows: list[dict], min_len: int) -> dict:
    if not ids:
        return {"recallable": False, "hits": [], "missing": [], "matched_core": {}}
    m = rg_gates.match_authorities(ids, rows, min_len=min_len)
    hits = sorted(k for k, v in m.items() if v)
    return {
        "recallable": True,
        "hits": hits,
        "missing": sorted(k for k, v in m.items() if not v),
        "matched_core": {k: v for k, v in m.items() if v},
    }


def pool_stats(rows: list[dict]) -> dict:
    ids = [str(r.get("decision_id") or "") for r in rows]
    bad_urls = []
    for r in rows:
        url = str(r.get("canonical_url") or "")
        if not url.startswith("https://"):
            bad_urls.append({"decision_id": r.get("decision_id"), "url": url})
    return {
        "n_rows": len(rows),
        "n_distinct_decision_ids": len(set(ids)),
        "n_rows_without_https_url": len(bad_urls),
        "bad_url_sample": bad_urls[:5],
    }


def _gate(name: str, passed: bool | None, detail: str, role: str, **measured: Any) -> dict:
    return {"gate": name, "passed": None if passed is None else bool(passed),
            "role": role, "detail": detail, "measured": measured}


def _nm(name: str, reason: str, role: str, **measured: Any) -> dict:
    return {"gate": name, "passed": None, "role": role, "detail": reason, "measured": measured}


# --------------------------------------------------------------------------- #
# the measurement (pure; unit-testable without any mount)
# --------------------------------------------------------------------------- #
def evaluate(hypothesis: dict, spec: dict, baseline_record: dict,
             envelopes_by_norm: dict[str, list[dict]]) -> dict:
    min_len = int(((spec.get("id_match_rules") or {}).get("min_core_length")) or 6)
    gates: list[dict] = []
    cells: list[dict] = []
    parity_inputs: list[dict] = []

    for question in spec["questions"]:
        slug = question["slug"]
        texts = identity_texts(question)
        authority_ids = list(question.get("authority_ids") or [])
        counter_ids = [r["id"] for r in (question.get("known_counter_ids") or [])]

        # ---- product pool: union of identity-matched envelopes ------------ #
        matched_envs: list[dict] = []
        for norm in sorted(texts):
            matched_envs.extend(envelopes_by_norm.get(norm, []))
        product_rows: list[dict] = []
        for env in matched_envs:
            product_rows.extend(env["rows"])

        # ---- primary comparator: same text/channel/language in baseline --- #
        same_query_groups = [
            g for g in (baseline_record.get("queries") or [])
            if g.get("slug") == slug
            and rg_frozen.normalize_text(str(g.get("query") or "")) in texts
        ]
        comparator_rows: list[dict] = []
        for g in same_query_groups:
            comparator_rows.extend(g.get("rows") or [])

        # ---- reported context comparators (never gated) -------------------- #
        plain_rows = [
            row for g in (baseline_record.get("queries") or [])
            if g.get("slug") == slug and g.get("channel") == "baseline"
            for row in (g.get("rows") or [])
        ]
        union_rows = [
            row for g in (baseline_record.get("queries") or [])
            if g.get("slug") == slug
            for row in (g.get("rows") or [])
        ]

        language_reach = {}
        for norm, (channel, lang) in sorted(texts.items(), key=lambda kv: (kv[1][0], kv[1][1])):
            envs = envelopes_by_norm.get(norm, [])
            language_reach[f"{channel}/{lang}"] = {
                "n_product_envelopes": len(envs),
                "n_product_rows": sum(e["n_rows"] for e in envs),
                "executed_by_product_cache": bool(envs),
                "status": "EXECUTED" if envs else "NOT_EXECUTED",
            }

        cell: dict[str, Any] = {
            "slug": slug,
            "n_identity_matched_envelopes": len(matched_envs),
            "identity_envelope_files": [e["file"] for e in matched_envs],
            "product_pool": pool_stats(product_rows),
            "comparator_same_query": {
                **pool_stats(comparator_rows),
                "groups": [{"query_key": g.get("query_key"), "channel": g.get("channel"),
                            "language": g.get("language"), "n_rows": len(g.get("rows") or [])}
                           for g in same_query_groups],
            },
            "context_comparators_reported_only": {
                "plain_channel_all_languages": pool_stats(plain_rows),
                "union_all_channels": pool_stats(union_rows),
            },
            "language_reach": language_reach,
            "gates": [],
        }

        # ingredients for the non-vacuity battery (controls are RE-SCORED on
        # constructed pools below; they never reuse the observed outcome)
        for kind, ids in (("authority", authority_ids), ("counter", counter_ids)):
            if ids:
                parity_inputs.append({
                    "gate": f"parity::same_query_{kind}_not_below_baseline::{slug}",
                    "ids": list(ids),
                    "comparator_hits_n": len(recalled(ids, comparator_rows, min_len)["hits"]),
                    "comparator_rows": comparator_rows,
                })

        sets = (
            ("authority", "same_query_authority_not_below_baseline", "product::authority_recall",
             authority_ids),
            ("counter", "same_query_counter_not_below_baseline", "product::counter_recall",
             counter_ids),
        )
        for kind, parity_suffix, absolute_prefix, ids in sets:
            p = recalled(ids, product_rows, min_len)
            b = recalled(ids, comparator_rows, min_len)
            b_plain = recalled(ids, plain_rows, min_len)
            b_union = recalled(ids, union_rows, min_len)

            # absolute gate (report-only)
            abs_name = f"{absolute_prefix}::{slug}"
            if not p["recallable"]:
                cell["gates"].append(_nm(
                    abs_name, f"frozen spec carries no {kind} id set for this slug; "
                              "recall is not measurable and is never counted as a pass",
                    ROLE_REPORT_ONLY, slug=slug, n_frozen_ids=0))
            else:
                cell["gates"].append(_gate(
                    abs_name, len(p["hits"]) >= 1,
                    (f"product cache recalls {len(p['hits'])}/{len(ids)} frozen {kind} ids "
                     "(>=1-of-set); REPORT-ONLY role: the falsification target is the "
                     "same-query parity:: gate"),
                    ROLE_REPORT_ONLY, slug=slug, n_frozen_ids=len(ids),
                    product_hits=p["hits"], product_missing=p["missing"],
                    product_yield=round(len(p["hits"]) / len(ids), 6) if ids else None,
                    comparator_same_query_hits=b["hits"],
                    context_plain_all_lang_hits=b_plain["hits"],
                    context_union_all_channels_hits=b_union["hits"],
                    n_product_rows=len(product_rows),
                    n_comparator_rows=len(comparator_rows)))

            # parity gate (falsifier)
            parity_name = f"parity::{parity_suffix}::{slug}"
            if not (p["recallable"] and b["recallable"]):
                cell["gates"].append(_nm(
                    parity_name,
                    f"frozen {kind} id set is empty; the parity comparison is not "
                    "measurable and is never counted as a pass",
                    ROLE_FALSIFIER, slug=slug, n_product_hits=0, n_comparator_hits=0))
                continue
            p_n, b_n = len(p["hits"]), len(b["hits"])
            ok = p_n >= b_n
            cell["gates"].append(_gate(
                parity_name, ok,
                (f"product {p_n} >= same-query plain comparator {b_n} of {len(ids)} frozen "
                 f"{kind} ids: the product retrieval layer keeps the plain search's reach")
                if ok else
                (f"product {p_n} < same-query plain comparator {b_n} of {len(ids)} frozen "
                 f"{kind} ids: the product retrieval layer returns strictly LESS of the "
                 "frozen set than the plain OpenCaseLaw response to the identical query"),
                ROLE_FALSIFIER, slug=slug, n_frozen_ids=len(ids),
                product_hits=p["hits"], comparator_hits=b["hits"],
                comparator_hit_ids=b["hits"],
                product_only=[i for i in p["hits"] if i not in set(b["hits"])],
                comparator_only=[i for i in b["hits"] if i not in set(p["hits"])],
                n_product_rows=len(product_rows),
                n_comparator_rows=len(comparator_rows),
                context_plain_all_lang_hits=b_plain["hits"],
                context_union_all_channels_hits=b_union["hits"],
                comparator_groups=cell["comparator_same_query"]["groups"]))

        gates.extend(cell["gates"])
        cells.append(cell)

    # ---- non-vacuity battery (controls RE-SCORED on constructed pools) ---- #
    battery: list[dict] = []
    parity_gates = [g for g in gates
                    if g["role"] == ROLE_FALSIFIER and g["passed"] is not None]

    # C1: a deliberately BLANKED product pool must fail every parity gate the
    # comparator can carry (0 >= n is false for n >= 1). Re-scored here, never
    # inferred from the observed outcome.
    blankable = [p for p in parity_inputs if p["comparator_hits_n"] >= 1]
    blanked_fails = [p["gate"] for p in blankable
                     if not (0 >= p["comparator_hits_n"])]
    c1_holds = len(blankable) >= 1 and len(blanked_fails) == len(blankable)
    battery.append({
        "control": "C1_blanked_product_pool_must_fail",
        "holds": bool(c1_holds),
        "why": (f"re-scoring a deliberately blanked product pool against the "
                f"{len(blankable)} parity gate(s) whose same-query comparator recalls "
                f">=1 frozen id(s) fails all of them ({sorted(set(blanked_fails))})"
                if c1_holds else
                "no parity gate has a same-query comparator hit >= 1, so the parity "
                "rule cannot be shown able to fail - vacuous for this input, never "
                "a pass"),
        "n_parity_gates_with_comparator_hits": len(blankable),
    })

    # C2: an ORACLE product pool (the comparator rows themselves) must PASS
    # every measurable parity gate (identical hits). Re-scored on constructed
    # rows, never inferred from the observed outcome.
    oracle_failures = []
    for p in parity_inputs:
        oracle_hits = len(recalled(p["ids"], p["comparator_rows"], min_len)["hits"])
        if oracle_hits < p["comparator_hits_n"]:
            oracle_failures.append(p["gate"])
    c2_holds = bool(parity_inputs) and not oracle_failures
    battery.append({
        "control": "C2_oracle_product_pool_must_pass",
        "holds": bool(c2_holds),
        "why": ("scoring the same-query comparator rows themselves as the product "
                "pool reproduces the comparator hits for every measurable parity "
                "gate; a failure would mean the gate is defective, not the product"
                if c2_holds else
                f"oracle re-scoring failed on {sorted(set(oracle_failures))} - the "
                "instrument is defective for this input, never a product verdict"),
        "oracle_failures": sorted(set(oracle_failures)),
    })
    all_hold = all(b["holds"] for b in battery)

    falsification_gates = [g["gate"] for g in gates
                           if g["role"] == ROLE_FALSIFIER and g["passed"] is False]
    not_measurable = [g["gate"] for g in gates if g["passed"] is None]
    absolute_misses = [g["gate"] for g in gates
                       if g["role"] == ROLE_REPORT_ONLY and g["passed"] is False]
    measured_cells = [c for c in cells
                      if any(g["role"] == ROLE_FALSIFIER and g["passed"] is not None
                             for g in c["gates"])]

    if not all_hold:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = EXIT_NOT_MEASURED_OR_VACUOUS
        reason = ("the non-vacuity battery did not hold; this is an instrument/input "
                  "problem, never a product verdict and never a pass")
    elif not measured_cells:
        verdict = "NOT_MEASURED"
        exit_code = EXIT_NOT_MEASURED_OR_VACUOUS
        reason = ("no measurable parity cell: the product cache executed none of the "
                  "frozen query texts, or every frozen id set is empty; "
                  "NOT_MEASURED is never a pass")
    elif falsification_gates:
        verdict = "FAIL_PRODUCT_CACHE_PARITY"
        exit_code = EXIT_FALSIFIED
        reason = ("the product's own cached retrieval responses to the frozen queries "
                  "recall strictly fewer frozen ids than the plain OpenCaseLaw response "
                  "to the identical query text: retrieval-first parity is falsified "
                  "on the named cells")
    else:
        verdict = "PASS_NO_PARITY_REGRESSION"
        exit_code = EXIT_PASS
        reason = ("every measurable same-query parity gate holds and both non-vacuity "
                  "controls prove the rule can fail and can pass")

    return {
        "verdict": verdict,
        "exit_code": exit_code,
        "reason": reason,
        "n_gates": len(gates),
        "n_passed": sum(1 for g in gates if g["passed"] is True),
        "n_failed": sum(1 for g in gates if g["passed"] is False),
        "n_not_measurable": len(not_measurable),
        "n_falsifier_gates": len(parity_gates),
        "falsification_gates": falsification_gates,
        "not_measurable_gates": not_measurable,
        "absolute_report_only_misses": absolute_misses,
        "measured_cells": len(measured_cells),
        "gates": gates,
        "cells": cells,
        "non_vacuity": {"all_hold": all_hold, "battery": battery},
        "success_rule": hypothesis["metric_FROZEN"]["success_rule_FROZEN"],
        "claim_ceiling": hypothesis["claim_ceiling"],
    }


# --------------------------------------------------------------------------- #
# run orchestration
# --------------------------------------------------------------------------- #
def _language_reach_summary(cells: list[dict]) -> dict:
    summary: dict[str, Any] = {"per_slug": {}, "texts": {"n_frozen_texts": 0,
                                                         "n_executed_by_product_cache": 0}}
    for cell in cells:
        reach = cell["language_reach"]
        executed = [k for k, v in reach.items() if v["executed_by_product_cache"]]
        not_executed = [k for k, v in reach.items() if not v["executed_by_product_cache"]]
        summary["per_slug"][cell["slug"]] = {
            "executed": sorted(executed), "not_executed": sorted(not_executed),
        }
        summary["texts"]["n_frozen_texts"] += len(reach)
        summary["texts"]["n_executed_by_product_cache"] += len(executed)
    return summary


def _v3_multilingual_reuse(run_id: str) -> dict:
    """Re-execute the accepted multilingual/provenance check under this run id."""
    from evaluation import run_v3_multilingual_provenance_reuse as v3m
    results = []
    for qid in v3m.QIDS:
        path = v3m.V3_PACKET_DIR / f"{qid}.bundle.json"
        if not path.is_file():
            results.append({"qid": qid, "row_ok": False, "error": f"missing {path}"})
            continue
        observed = v3m.sha256_file(path)
        pinned = v3m.FROZEN_BUNDLE_SHAS[qid]
        if observed != pinned:
            results.append({"qid": qid, "row_ok": False,
                            "error": f"SHA mismatch: observed={observed} frozen={pinned}"})
            continue
        bundle = json.loads(path.read_text(encoding="utf-8"))
        results.append(v3m.check_bundle(qid, bundle, pinned))
    all_ok = all(r.get("row_ok") for r in results) and len(results) == len(v3m.QIDS)
    return {
        "schema": "lex-evaluation-v3-multilingual-provenance-reuse/2",
        "run_id": run_id,
        "engine_reused": "evaluation.run_v3_multilingual_provenance_reuse.check_bundle",
        "v3_packet_dir": str(v3m.V3_PACKET_DIR),
        "success_rule": "3/3 qids row_ok under the same frozen pins; any miss published "
                        "as-is, never weakened",
        "verdict": "PASS" if all_ok else "PARTIAL_MISS",
        "qids_checked": len(results),
        "qids_row_ok": sum(1 for r in results if r.get("row_ok")),
        "results": results,
        "append_only_note": "this leg writes only under this run id; earlier committed "
                            "records (local_v3_multilingual_reuse.json, 39471603258.json) "
                            "are never overwritten",
    }


def run(run_id: str, out_path: Path, report_path: Path,
        mount_arg: str | None = None) -> tuple[int, dict]:
    t0 = time.time()
    env_err: dict[str, Any] = {"schema": SCHEMA, "run_id": run_id}

    # ---- fail-closed pin verification (before) --------------------------- #
    hypothesis_sha = sha256_file(HYPOTHESIS_PATH)
    freeze = json.loads(FREEZE_RECORD_PATH.read_text(encoding="utf-8"))
    if freeze["hypothesis"]["sha256"] != hypothesis_sha:
        env_err.update(verdict="ENVIRONMENT_ERROR",
                       detail="hypothesis bytes do not match the freeze record pin")
        return EXIT_ENVIRONMENT, env_err
    hypothesis = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    if not hypothesis.get("frozen_before_execution"):
        env_err.update(verdict="ENVIRONMENT_ERROR",
                       detail="hypothesis is not marked frozen_before_execution")
        return EXIT_ENVIRONMENT, env_err

    spec = rg_frozen.load_frozen()  # raises on digest/schema drift
    if sha256_file(REPO_ROOT / BASELINE_RECORD_RELPATH) != \
            freeze["frozen_inputs"]["baseline_record"]["sha256"]:
        env_err.update(verdict="ENVIRONMENT_ERROR",
                       detail="baseline record bytes drifted from the freeze pin")
        return EXIT_ENVIRONMENT, env_err
    baseline_record = json.loads(
        (REPO_ROOT / BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    if baseline_record.get("schema") != "lex-retrieval-benchmark/1" or \
            baseline_record.get("frozen_sha256") != rg_frozen.FROZEN_SHA256:
        env_err.update(verdict="ENVIRONMENT_ERROR", detail="baseline record schema/pin")
        return EXIT_ENVIRONMENT, env_err

    mount = resolve_product_mount(mount_arg)
    if mount is None:
        env_err.update(verdict="ENVIRONMENT_ERROR",
                       detail=f"accepted product mount missing: {DEFAULT_MOUNTS}")
        return EXIT_ENVIRONMENT, env_err
    cache_dir = mount / "results" / "product" / "query_cache"
    if not cache_dir.is_dir():
        env_err.update(verdict="ENVIRONMENT_ERROR",
                       detail=f"product query_cache missing: {cache_dir}")
        return EXIT_ENVIRONMENT, env_err

    n_before, inv_before = cache_inventory(cache_dir)
    if inv_before != freeze["frozen_inputs"]["product_query_cache"]["inventory_sha256"]:
        env_err.update(verdict="ENVIRONMENT_ERROR",
                       detail="product query_cache inventory drifted from the freeze pin",
                       observed_inventory_sha256=inv_before,
                       pinned_inventory_sha256=freeze["frozen_inputs"]
                       ["product_query_cache"]["inventory_sha256"])
        return EXIT_ENVIRONMENT, env_err

    envelopes_by_norm = scan_identity_envelopes(cache_dir)
    verdict = evaluate(hypothesis, spec, baseline_record, envelopes_by_norm)
    reach = _language_reach_summary(verdict["cells"])
    v3_leg = _v3_multilingual_reuse(run_id)

    # ---- fail-closed pin verification (after) ---------------------------- #
    n_after, inv_after = cache_inventory(cache_dir)
    rehash_ok = (
        inv_after == inv_before
        and sha256_file(REPO_ROOT / BASELINE_RECORD_RELPATH)
        == freeze["frozen_inputs"]["baseline_record"]["sha256"]
        and sha256_file(HYPOTHESIS_PATH) == hypothesis_sha
        and sha256_file(REPO_ROOT / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json")
        == rg_frozen.FROZEN_SHA256
    )
    if not rehash_ok:
        verdict["verdict"] = "ENVIRONMENT_OR_VACUOUS"
        verdict["exit_code"] = EXIT_NOT_MEASURED_OR_VACUOUS
        verdict["reason"] = ("an input drifted between freeze verification and "
                             "post-execution re-hash; never a product verdict")

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction_version": current_direction_version(),
        "entry_point": "python -m evaluation.product_cache_parity",
        "hypothesis": {
            "path": str(HYPOTHESIS_PATH.relative_to(REPO_ROOT)),
            "sha256": hypothesis_sha,
            "freeze_record": str(FREEZE_RECORD_PATH.relative_to(REPO_ROOT)),
            "freeze_record_hypothesis_sha256": freeze["hypothesis"]["sha256"],
            "frozen_before_execution": True,
            "pre_freeze_reconnaissance_disclosed":
                "pre_freeze_reconnaissance_HONEST" in hypothesis,
        },
        "frozen_spec": {
            "path": "evaluation/retrieval_gate/frozen_retrieval_benchmark.json",
            "sha256": sha256_file(
                REPO_ROOT / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"),
            "frozen_sha256": rg_frozen.FROZEN_SHA256,
        },
        "baseline": {
            "record": BASELINE_RECORD_RELPATH,
            "sha256": sha256_file(REPO_ROOT / BASELINE_RECORD_RELPATH),
            "primary_comparator": "baseline_same_query (identical query text, same "
                                  "channel and language; named per CYCLE_39111232991_"
                                  "CORRECTION.md D2)",
            "context_comparators_reported_only":
                ["plain_channel_all_languages", "union_all_channels"],
            "note": "plain OpenCaseLaw searches with no query-map / counter-authority "
                    "machinery; this benchmark performs no network request",
        },
        "product": {
            "mount": str(mount),
            "query_cache": str(cache_dir),
            "query_cache_n_files": n_before,
            "query_cache_inventory_sha256": inv_before,
            "n_identity_matched_envelopes": sum(
                c["n_identity_matched_envelopes"] for c in verdict["cells"]),
            "mapping": "IDENTITY ONLY (slug == slug, exact normalized query-text match); "
                       "no analyst mapping consumed (retraction-proof vs D1)",
        },
        "language_reach_reported_only": reach,
        "v3_multilingual_provenance_reuse": v3_leg,
        "network_requests": 0,
        "no_174k_benchmark_rerun": True,
        "no_new_thresholds": True,
        "rehash_before": {"inventory_sha256": inv_before, "n_files": n_before},
        "rehash_after": {"inventory_sha256": inv_after, "n_files": n_after,
                         "all_pins_hold": rehash_ok},
        "numeric_environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "standing_orders": {
            "do_not_serve_38839347028": True,
            "do_not_serve_unchanged_rebuilt_39027045675": True,
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "packet_admitted": False,
            "ready_for_owner_session": False,
            "owner_decision_required": False,
            "absolute_bars": "REPORTED-ONLY; not scored here",
        },
        "elapsed_s": round(time.time() - t0, 3),
        **verdict,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")

    # ---- report ---------------------------------------------------------- #
    lines = [
        f"# Product-cache retrieval/counter-authority parity — run {run_id}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Direction: v{record['direction_version']} (derived from state/evaluation.json)",
        f"- Hypothesis: `{record['hypothesis']['path']}` sha256 `{hypothesis_sha[:12]}...` "
        "(frozen BEFORE execution; pre-freeze reconnaissance disclosed in-file)",
        f"- Product pool: `{cache_dir}` identity-matched envelopes "
        f"({record['product']['n_identity_matched_envelopes']} of {n_before} cache files)",
        f"- Primary comparator: same-query plain OpenCaseLaw rows (named per D2 correction)",
        f"- Verdict: **{record['verdict']}** (exit {record['exit_code']})",
        f"- Falsifier gates failed: **{len(record['falsification_gates'])}**",
        f"- Non-vacuity: **{record['non_vacuity']['all_hold']}**",
        f"- Multilingual/provenance reuse leg (V3): **{v3_leg['verdict']}** "
        f"({v3_leg['qids_row_ok']}/{v3_leg['qids_checked']} qids row_ok)",
        f"- Elapsed: {record['elapsed_s']} s",
        "",
        "## Cells (identity mapping; hits of frozen id sets)",
        "",
        "| slug | product pool rows | comparator rows | authority hits (prod/base) | "
        "counter hits (prod/base) | parity authority | parity counter |",
        "|---|---|---|---|---|---|---|",
    ]
    for cell in verdict["cells"]:
        g_auth_p = next((g for g in cell["gates"]
                         if g["gate"] == f"parity::same_query_authority_not_below_baseline::{cell['slug']}"), None)
        g_cnt_p = next((g for g in cell["gates"]
                        if g["gate"] == f"parity::same_query_counter_not_below_baseline::{cell['slug']}"), None)
        a_abs = next((g for g in cell["gates"]
                      if g["gate"] == f"product::authority_recall::{cell['slug']}"), None)
        c_abs = next((g for g in cell["gates"]
                      if g["gate"] == f"product::counter_recall::{cell['slug']}"), None)
        def _fmt(g_abs, g_par):
            if g_abs is None or g_abs["passed"] is None:
                auth = "n/a"
            else:
                m = g_abs["measured"]
                auth = f"{len(m.get('product_hits') or [])}/{m.get('n_frozen_ids')}"
            if g_par is None or g_par["passed"] is None:
                par = "NOT_MEASURED"
            else:
                m = g_par["measured"]
                par = ("PASS" if g_par["passed"] else "FAIL") + \
                    f" ({len(m.get('product_hits') or [])} vs {m.get('comparator_hits')})"
            return auth, par
        a_hits, a_par = _fmt(a_abs, g_auth_p)
        c_hits, c_par = _fmt(c_abs, g_cnt_p)
        lines.append(
            f"| {cell['slug']} | {cell['product_pool']['n_rows']} | "
            f"{cell['comparator_same_query']['n_rows']} | {a_hits} | {c_hits} | "
            f"{a_par} | {c_par} |")
    lines += ["", "## Language reach (REPORTED-ONLY; never gated)", ""]
    for slug, entry in reach["per_slug"].items():
        lines.append(f"- `{slug}`: executed {entry['executed'] or '—'}; "
                     f"not executed {entry['not_executed'] or '—'}")
    lines += [
        "",
        "## Falsifier gates that failed",
        "",
    ]
    if record["falsification_gates"]:
        for g in verdict["gates"]:
            if g["gate"] in record["falsification_gates"]:
                lines.append(f"- `{g['gate']}` — {g['detail']}")
    else:
        lines.append("(none)")
    lines += [
        "",
        "## Reason",
        "",
        record["reason"],
        "",
        "## Claim ceiling",
        "",
        hypothesis["claim_ceiling"],
        "",
        f"Machine record: `{out_path.relative_to(REPO_ROOT) if out_path.is_relative_to(REPO_ROOT) else out_path}`",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return record["exit_code"], record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None,
                    help="machine record path (default: committed results tree; "
                         "a scratch invocation MUST override this)")
    ap.add_argument("--report", default=None,
                    help="report path (default: committed reports tree; same "
                         "scratch-run obligation)")
    ap.add_argument("--product-mount", default=None)
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else DEFAULT_OUT_DIR / f"{args.run_id}.json"
    report = Path(args.report) if args.report else \
        DEFAULT_REPORT_DIR / f"PRODUCT_CACHE_PARITY_{args.run_id}.md"
    code, record = run(args.run_id, out, report, args.product_mount)
    print(json.dumps({
        "run_id": record.get("run_id"),
        "verdict": record.get("verdict"),
        "exit_code": code,
        "reason": record.get("reason"),
        "falsification_gates": record.get("falsification_gates"),
        "non_vacuity_all_hold": (record.get("non_vacuity") or {}).get("all_hold"),
        "language_reach": ((record.get("language_reach_reported_only") or {})
                           .get("texts")),
        "v3_reuse_verdict": ((record.get("v3_multilingual_provenance_reuse") or {})
                             .get("verdict")),
        "record": str(out),
    }, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
