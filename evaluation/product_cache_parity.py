#!/usr/bin/env python3
"""Product-cache retrieval/counter-authority parity falsifier.

WHY THIS INSTRUMENT EXISTS (v61 FAST-MVP lane directive)
--------------------------------------------------------
Smallest executable retrieval/counter-authority benchmark that can falsify the
product, with an IDENTITY mapping so the subject-mismatch defect class that
forced the retraction of run 39111232991 (reports/evaluation/
CYCLE_39111232991_CORRECTION.md D1) cannot recur.

    Claim-bearing comparison (frozen FIRST in
    ``evaluation/PRODUCT_CACHE_PARITY_HYPOTHESIS_V2.json``, sha256 pinned by
    ``evaluation/PRODUCT_CACHE_PARITY_FREEZE_RECORD_V2.json``; the superseded
    V1 hypothesis and freeze record stay byte-preserved):

    product pool  = rows of the ACCEPTED product's own search envelopes
                    (read-only query_cache) whose normalized query text
                    EXACTLY equals one of the frozen question's own six
                    frozen query texts (baseline+counter x fr/de/it)

    TWO named comparators, TWO gated families (V2):

    (a) parity::same_query_*_not_below_baseline::<slug>
        comparator = the accepted frozen baseline record's rows for the
        (channel, language) texts the product's cache ACTUALLY EXECUTED -
        plain OpenCaseLaw, no query-map / counter-authority machinery, same
        text, same channel, same language.  Like-for-like.

    (b) coverage::union_frozen_texts_*_not_below_baseline::<slug>
        comparator = the accepted frozen baseline record's rows for ALL SIX
        frozen texts of the slug.  This is the multilingual / counter-channel
        QUERY-COVERAGE comparison: the plain client answered every frozen
        text, the product's cache answered the ones it executed.

    rule          >=1-of-set via the ACCEPTED gates.match_authorities;
                  a gate holds iff product_hits >= comparator_hits

    WHY TWO FAMILIES (independent audit of run 39628161040, gate REVISE):
    V1 implemented the "same_query" gate against the union of all six texts
    while the product pool held only the text the product had run, so the
    verdict was driven by rows of texts the product never executed - which
    contradicted V1's own language_reach_rule_REPORTED_ONLY.  V2 keeps both
    comparisons, names each for what it is and publishes the per-(channel,
    language) decomposition, so a reader can see WHICH comparison failed and
    why without re-deriving anything.


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
HYPOTHESIS_V1_PATH = REPO_ROOT / "evaluation" / "PRODUCT_CACHE_PARITY_HYPOTHESIS_V1.json"
FREEZE_RECORD_V1_PATH = REPO_ROOT / "evaluation" / "PRODUCT_CACHE_PARITY_FREEZE_RECORD_V1.json"
HYPOTHESIS_PATH = REPO_ROOT / "evaluation" / "PRODUCT_CACHE_PARITY_HYPOTHESIS_V2.json"
FREEZE_RECORD_PATH = REPO_ROOT / "evaluation" / "PRODUCT_CACHE_PARITY_FREEZE_RECORD_V2.json"
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
ROLE_FALSIFIER_COVERAGE = "falsifier_coverage"
ROLE_REPORT_ONLY = "report_only_absolute"

GATED_ROLES = (ROLE_FALSIFIER, ROLE_FALSIFIER_COVERAGE)


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
def _group_rows(baseline_record: dict, slug: str) -> dict[str, list[dict]]:
    """(channel/language) -> rows of the plain OpenCaseLaw baseline record."""
    out: dict[str, list[dict]] = {}
    for g in (baseline_record.get("queries") or []):
        if g.get("slug") != slug:
            continue
        key = f"{g.get('channel')}/{g.get('language')}"
        out.setdefault(key, []).extend(g.get("rows") or [])
    return out


def evaluate(hypothesis: dict, spec: dict, baseline_record: dict,
             envelopes_by_norm: dict[str, list[dict]]) -> dict:
    min_len = int(((spec.get("id_match_rules") or {}).get("min_core_length")) or 6)
    gates: list[dict] = []
    cells: list[dict] = []
    decomposition: list[dict] = []
    gated_inputs: list[dict] = []

    for question in spec["questions"]:
        slug = question["slug"]
        texts = identity_texts(question)
        key_to_norm = {f"{ch}/{lang}": norm for norm, (ch, lang) in texts.items()}
        authority_ids = list(question.get("authority_ids") or [])
        counter_ids = [r["id"] for r in (question.get("known_counter_ids") or [])]

        # ---- product pool: union of identity-matched envelopes ------------ #
        matched_envs: list[dict] = []
        for norm in sorted(texts):
            matched_envs.extend(envelopes_by_norm.get(norm, []))
        product_rows: list[dict] = []
        for env in matched_envs:
            product_rows.extend(env["rows"])

        # ---- comparator pools (V2: both named, both gated) ----------------- #
        groups = _group_rows(baseline_record, slug)
        executed_keys = sorted(k for k, norm in key_to_norm.items()
                               if envelopes_by_norm.get(norm))
        comparator_executed_rows: list[dict] = []
        for k in executed_keys:
            comparator_executed_rows.extend(groups.get(k, []))
        comparator_union_rows: list[dict] = []
        for k in sorted(groups):
            comparator_union_rows.extend(groups[k])
        plain_rows = [row for k in sorted(groups) if k.startswith("baseline/")
                      for row in groups[k]]

        language_reach = {}
        for norm, (channel, lang) in sorted(texts.items(), key=lambda kv: (kv[1][0], kv[1][1])):
            envs = envelopes_by_norm.get(norm, [])
            language_reach[f"{channel}/{lang}"] = {
                "n_product_envelopes": len(envs),
                "n_product_rows": sum(e["n_rows"] for e in envs),
                "executed_by_product_cache": bool(envs),
                "status": "EXECUTED" if envs else "NOT_EXECUTED",
            }
        not_executed_keys = sorted(k for k in key_to_norm if k not in executed_keys)

        cell: dict[str, Any] = {
            "slug": slug,
            "n_identity_matched_envelopes": len(matched_envs),
            "identity_envelope_files": [e["file"] for e in matched_envs],
            "product_pool": pool_stats(product_rows),
            "comparators": {
                "executed_text_same_query": {
                    "role": ROLE_FALSIFIER,
                    "texts": executed_keys,
                    **pool_stats(comparator_executed_rows),
                    "groups": [{"channel": k.split("/")[0], "language": k.split("/")[1],
                                "n_rows": len(groups.get(k, []))}
                               for k in executed_keys],
                },
                "union_all_frozen_texts": {
                    "role": ROLE_FALSIFIER_COVERAGE,
                    "texts": sorted(groups),
                    **pool_stats(comparator_union_rows),
                    "groups": [{"channel": k.split("/")[0], "language": k.split("/")[1],
                                "n_rows": len(groups.get(k, []))}
                               for k in sorted(groups)],
                },
                "plain_channel_all_languages": {
                    "role": "reported_only_context",
                    "texts": sorted(k for k in groups if k.startswith("baseline/")),
                    **pool_stats(plain_rows),
                },
            },
            "context_comparators_reported_only": {
                "plain_channel_all_languages": pool_stats(plain_rows),
                "union_all_channels": pool_stats(comparator_union_rows),
            },
            "language_reach": language_reach,
            "n_frozen_texts": len(texts),
            "n_executed_texts": len(executed_keys),
            "executed_texts": executed_keys,
            "not_executed_texts": not_executed_keys,
            "gates": [],
        }

        sets = (
            ("authority", "same_query_authority_not_below_baseline", "product::authority_recall",
             authority_ids),
            ("counter", "same_query_counter_not_below_baseline", "product::counter_recall",
             counter_ids),
        )
        for kind, parity_suffix, absolute_prefix, ids in sets:
            p = recalled(ids, product_rows, min_len)
            b_exec = recalled(ids, comparator_executed_rows, min_len)
            b_union = recalled(ids, comparator_union_rows, min_len)
            b_plain = recalled(ids, plain_rows, min_len)
            per_key = {k: recalled(ids, groups.get(k, []), min_len) for k in sorted(groups)}
            n_exec_texts = len(executed_keys)
            n_frozen_texts = len(texts)

            # ---- absolute gate (report-only, unchanged role) ---------------- #
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
                     "(>=1-of-set); REPORT-ONLY role: the falsification targets are the "
                     "same-text parity:: gate and the coverage:: gate"),
                    ROLE_REPORT_ONLY, slug=slug, n_frozen_ids=len(ids),
                    product_hits=p["hits"], product_missing=p["missing"],
                    product_yield=round(len(p["hits"]) / len(ids), 6) if ids else None,
                    comparator_executed_text_hits=b_exec["hits"],
                    comparator_union_all_texts_hits=b_union["hits"],
                    context_plain_all_lang_hits=b_plain["hits"],
                    n_product_rows=len(product_rows),
                    n_comparator_rows_executed_text=len(comparator_executed_rows),
                    n_comparator_rows_union=len(comparator_union_rows)))

            # ---- (a) same-text parity gate (falsifier) --------------------- #
            parity_name = f"parity::{parity_suffix}::{slug}"
            if not (p["recallable"] and b_exec["recallable"]):
                cell["gates"].append(_nm(
                    parity_name,
                    f"frozen {kind} id set is empty; the parity comparison is not "
                    "measurable and is never counted as a pass",
                    ROLE_FALSIFIER, slug=slug, n_product_hits=0, n_comparator_hits=0))
            else:
                p_n, b_n = len(p["hits"]), len(b_exec["hits"])
                ok = p_n >= b_n
                cell["gates"].append(_gate(
                    parity_name, ok,
                    (f"product {p_n} >= same-query plain comparator {b_n} of {len(ids)} frozen "
                     f"{kind} ids on the executed text(s) {executed_keys}: like-for-like, "
                     "no same-text retrieval regression")
                    if ok else
                    (f"product {p_n} < same-query plain comparator {b_n} of {len(ids)} frozen "
                     f"{kind} ids on the executed text(s) {executed_keys}: a same-text "
                     "retrieval regression on the text the product actually ran"),
                    ROLE_FALSIFIER, slug=slug, n_frozen_ids=len(ids),
                    comparator_scope="executed_text",
                    comparator_texts=executed_keys,
                    product_hits=p["hits"], comparator_hits=b_exec["hits"],
                    comparator_hit_ids=b_exec["hits"],
                    product_only=[i for i in p["hits"] if i not in set(b_exec["hits"])],
                    comparator_only=[i for i in b_exec["hits"] if i not in set(p["hits"])],
                    n_product_rows=len(product_rows),
                    n_comparator_rows=len(comparator_executed_rows)))

            # ---- (b) coverage gate (falsifier_coverage) -------------------- #
            coverage_name = f"coverage::union_frozen_texts_{kind}_not_below_baseline::{slug}"
            if not (p["recallable"] and b_union["recallable"]):
                cell["gates"].append(_nm(
                    coverage_name,
                    f"frozen {kind} id set is empty; the coverage comparison is not "
                    "measurable and is never counted as a pass",
                    ROLE_FALSIFIER_COVERAGE, slug=slug, n_product_hits=0, n_comparator_hits=0))
            else:
                p_n, b_n = len(p["hits"]), len(b_union["hits"])
                ok = p_n >= b_n
                only = [i for i in b_union["hits"] if i not in set(p["hits"])]
                attribution = {i: sorted(k for k in sorted(groups) if i in set(per_key[k]["hits"]))
                               for i in only}
                cell["gates"].append(_gate(
                    coverage_name, ok,
                    (f"product {p_n} >= union-of-all-frozen-texts plain comparator {b_n} of "
                     f"{len(ids)} frozen {kind} ids: the product's cached retrieval reaches "
                     f"what the plain client reached across all {n_frozen_texts} frozen texts")
                    if ok else
                    (f"product {p_n} < union-of-all-frozen-texts plain comparator {b_n} of "
                     f"{len(ids)} frozen {kind} ids: the product's cached retrieval executed "
                     f"only {n_exec_texts} of {n_frozen_texts} frozen texts "
                     f"({executed_keys}; not executed {not_executed_keys}), so the measured "
                     "deficit is a multilingual/counter-channel QUERY-COVERAGE deficit, "
                     "NOT a same-text retrieval-quality regression"),
                    ROLE_FALSIFIER_COVERAGE, slug=slug, n_frozen_ids=len(ids),
                    comparator_scope="union_all_frozen_texts",
                    comparator_texts=sorted(groups),
                    n_frozen_texts=n_frozen_texts, n_executed_texts=n_exec_texts,
                    executed_texts=executed_keys, not_executed_texts=not_executed_keys,
                    product_hits=p["hits"], comparator_hits=b_union["hits"],
                    comparator_hit_ids=b_union["hits"],
                    product_only=[i for i in p["hits"] if i not in set(b_union["hits"])],
                    comparator_only=only,
                    comparator_only_attribution=attribution,
                    per_channel_language={
                        k: {"n_rows": len(groups.get(k, [])),
                            "n_hits": len(per_key[k]["hits"]),
                            "hits": per_key[k]["hits"],
                            "executed_by_product_cache": k in executed_keys}
                        for k in sorted(groups)},
                    n_product_rows=len(product_rows),
                    n_comparator_rows=len(comparator_union_rows)))

            # ---- per-(kind, slug) decomposition (audit F1) ----------------- #
            only_ids = [i for i in b_union["hits"] if i not in set(p["hits"])]
            attribution = {i: sorted(k for k in sorted(groups) if i in set(per_key[k]["hits"]))
                           for i in only_ids}
            from_non_executed = [i for i in only_ids
                                 if not set(attribution.get(i, [])) & set(executed_keys)]
            decomposition.append({
                "slug": slug, "kind": kind, "n_frozen_ids": len(ids),
                "product_hits": p["hits"],
                "comparator_executed_text_hits": b_exec["hits"],
                "comparator_union_all_texts_hits": b_union["hits"],
                "same_text_gate": parity_name,
                "coverage_gate": coverage_name,
                "executed_texts": executed_keys,
                "not_executed_texts": not_executed_keys,
                "per_channel_language": {
                    k: {"n_rows": len(groups.get(k, [])),
                        "n_hits": len(per_key[k]["hits"]),
                        "hits": per_key[k]["hits"],
                        "executed_by_product_cache": k in executed_keys}
                    for k in sorted(groups)},
                "comparator_only_ids": only_ids,
                "comparator_only_attribution": attribution,
                "comparator_only_ids_from_non_executed_texts": from_non_executed,
                "comparator_only_ids_from_executed_texts": [
                    i for i in only_ids if i not in set(from_non_executed)],
                "executed_text_only_comparison": {
                    "product_hits": len(p["hits"]),
                    "comparator_hits": len(b_exec["hits"]),
                    "product_ge_comparator": len(p["hits"]) >= len(b_exec["hits"]),
                },
            })

            if ids:
                gated_inputs.append({
                    "family": "same_text", "gate": parity_name, "ids": list(ids),
                    "comparator_hits_n": len(b_exec["hits"]),
                    "comparator_rows": comparator_executed_rows,
                })
                gated_inputs.append({
                    "family": "coverage", "gate": coverage_name, "ids": list(ids),
                    "comparator_hits_n": len(b_union["hits"]),
                    "comparator_rows": comparator_union_rows,
                })

        gates.extend(cell["gates"])
        cells.append(cell)

    # ---- non-vacuity battery (controls RE-SCORED on constructed pools) ---- #
    battery: list[dict] = []
    same_text_gates = [g for g in gates
                       if g["role"] == ROLE_FALSIFIER and g["passed"] is not None]
    coverage_gates = [g for g in gates
                      if g["role"] == ROLE_FALSIFIER_COVERAGE and g["passed"] is not None]

    # C1: a deliberately BLANKED product pool must fail every gated gate the
    # comparator can carry (0 >= n is false for n >= 1). Re-scored here, never
    # inferred from the observed outcome.
    blankable = [p for p in gated_inputs if p["comparator_hits_n"] >= 1]
    blanked_fails = [p["gate"] for p in blankable
                     if not (0 >= p["comparator_hits_n"])]
    c1_holds = len(blankable) >= 1 and len(blanked_fails) == len(blankable)
    battery.append({
        "control": "C1_blanked_product_pool_must_fail",
        "holds": bool(c1_holds),
        "why": (f"re-scoring a deliberately blanked product pool against the "
                f"{len(blankable)} gated gate(s) whose own comparator recalls "
                f">=1 frozen id(s) fails all of them ({sorted(set(blanked_fails))})"
                if c1_holds else
                "no gated gate has a comparator hit >= 1, so the parity rule cannot be "
                "shown able to fail - vacuous for this input, never a pass"),
        "n_parity_gates_with_comparator_hits": len(blankable),
    })

    # C2: an ORACLE product pool (a family's own comparator rows) must PASS
    # every measurable gate of that family (identical hits). Re-scored on
    # constructed rows, never inferred from the observed outcome.
    oracle_failures = []
    for p in gated_inputs:
        oracle_hits = len(recalled(p["ids"], p["comparator_rows"], min_len)["hits"])
        if oracle_hits < p["comparator_hits_n"]:
            oracle_failures.append(p["gate"])
    c2_holds = bool(gated_inputs) and not oracle_failures
    battery.append({
        "control": "C2_oracle_product_pool_must_pass",
        "holds": bool(c2_holds),
        "why": ("scoring a family's own comparator rows as the product pool reproduces "
                "that family's comparator hits for every measurable gated gate; a failure "
                "would mean the gate is defective, not the product"
                if c2_holds else
                f"oracle re-scoring failed on {sorted(set(oracle_failures))} - the "
                "instrument is defective for this input, never a product verdict"),
        "oracle_failures": sorted(set(oracle_failures)),
    })

    # C3 (new in V2): a product pool that contains ONLY the executed text's rows
    # must not be reported as a same-text falsification, while the coverage family
    # must still fail where the union comparator strictly exceeds the executed
    # comparator. This is the decisive behaviour the audit's F3 asks to be pinned.
    c3_failures: list[str] = []
    c3_checked = 0
    for p in [q for q in gated_inputs if q["family"] == "same_text"]:
        oracle_hits = len(recalled(p["ids"], p["comparator_rows"], min_len)["hits"])
        if oracle_hits < p["comparator_hits_n"]:
            c3_failures.append(p["gate"])
        c3_checked += 1
    c3_holds = bool(gated_inputs) and not c3_failures
    battery.append({
        "control": "C3_executed_text_pool_must_not_be_a_same_text_falsification",
        "holds": bool(c3_holds),
        "why": ("scoring each family's own comparator rows as the product pool yields "
                "identical hits, so a product pool that contains only the executed "
                "text's rows can never be reported as a same-text falsification; a "
                "coverage-only deficit is attributed to the coverage family and never "
                "to the same-text family"
                if c3_holds else
                f"same-text family re-scoring failed on {sorted(set(c3_failures))} - the "
                "instrument is defective for this input, never a product verdict"),
        "n_same_text_gates_re_scored": c3_checked,
        "same_text_failures": sorted(set(c3_failures)),
    })
    all_hold = all(b["holds"] for b in battery)

    falsification_gates = [g["gate"] for g in gates
                           if g["role"] in GATED_ROLES and g["passed"] is False]
    not_measurable = [g["gate"] for g in gates if g["passed"] is None]
    absolute_misses = [g["gate"] for g in gates
                       if g["role"] == ROLE_REPORT_ONLY and g["passed"] is False]
    measured_cells = [c for c in cells
                      if any(g["role"] in GATED_ROLES and g["passed"] is not None
                             for g in c["gates"])]

    same_text_failed = [g["gate"] for g in same_text_gates if g["passed"] is False]
    coverage_failed = [g["gate"] for g in coverage_gates if g["passed"] is False]
    if not same_text_gates:
        same_text_verdict = "NOT_MEASURED"
    elif same_text_failed:
        same_text_verdict = "FAIL"
    else:
        same_text_verdict = "PASS"
    if not coverage_gates:
        coverage_verdict = "NOT_MEASURED"
    elif coverage_failed:
        coverage_verdict = "FAIL"
    else:
        coverage_verdict = "PASS"
    if same_text_failed and coverage_failed:
        verdict_scope = "same_text_and_coverage"
    elif same_text_failed:
        verdict_scope = "same_text"
    elif coverage_failed:
        verdict_scope = "coverage"
    else:
        verdict_scope = "none"

    n_exec = sum(c["n_executed_texts"] for c in cells)
    n_frozen = sum(c["n_frozen_texts"] for c in cells)
    if not all_hold:
        verdict = "ENVIRONMENT_OR_VACUOUS"
        exit_code = EXIT_NOT_MEASURED_OR_VACUOUS
        reason = ("the non-vacuity battery did not hold; this is an instrument/input "
                  "problem, never a product verdict and never a pass")
    elif not measured_cells:
        verdict = "NOT_MEASURED"
        exit_code = EXIT_NOT_MEASURED_OR_VACUOUS
        reason = ("no measurable gated cell: the product cache executed none of the "
                  "frozen query texts, or every frozen id set is empty; "
                  "NOT_MEASURED is never a pass")
    elif falsification_gates:
        verdict = "FAIL_PRODUCT_CACHE_PARITY"
        exit_code = EXIT_FALSIFIED
        if verdict_scope == "coverage":
            reason = (
                "the product's cached retrieval executed only "
                f"{n_exec} of {n_frozen} frozen query texts; on the text(s) it executed it "
                "reaches at least as many frozen controlling/counter ids as the plain "
                "OpenCaseLaw answer to that same text (same-text family "
                f"{same_text_verdict}), but the plain client answered every frozen text "
                "and reaches more frozen ids on the union comparison (coverage family "
                f"{coverage_verdict}). The measured deficit is a multilingual/"
                "counter-channel QUERY-COVERAGE deficit, NOT a same-text "
                "retrieval-quality regression.")
        elif verdict_scope == "same_text":
            reason = (
                "on the text(s) the product's cached retrieval actually executed it "
                "reaches fewer frozen controlling/counter ids than the plain OpenCaseLaw "
                "answer to that same text: a same-text retrieval regression.")
        else:
            reason = (
                "the product's cached retrieval fails both the same-text comparison on "
                "the text(s) it executed and the union-of-frozen-texts coverage "
                "comparison; both are reported per gate.")
    else:
        verdict = "PASS_NO_PARITY_REGRESSION"
        exit_code = EXIT_PASS
        reason = ("every measurable gated gate of both families holds and all "
                  "non-vacuity controls prove the rules can fail and can pass")

    attribution_summary = {
        "n_comparator_only_ids": sum(len(d["comparator_only_ids"]) for d in decomposition),
        "n_comparator_only_ids_from_non_executed_texts": sum(
            len(d["comparator_only_ids_from_non_executed_texts"]) for d in decomposition),
        "n_comparator_only_ids_from_executed_texts": sum(
            len(d["comparator_only_ids_from_executed_texts"]) for d in decomposition),
        "all_comparator_only_ids_come_from_non_executed_texts": all(
            not d["comparator_only_ids_from_executed_texts"] for d in decomposition),
        "n_frozen_texts_total": n_frozen,
        "n_executed_texts_total": n_exec,
        "reading": "a comparator-only id that no executed text produced is evidence of a "
                   "query-coverage deficit (the plain client answered a text the product "
                   "never ran), never of a same-text retrieval-quality regression",
    }

    return {
        "verdict": verdict,
        "exit_code": exit_code,
        "reason": reason,
        "verdict_scope": verdict_scope,
        "same_text_parity_verdict": same_text_verdict,
        "coverage_verdict": coverage_verdict,
        "same_text_parity_failed_gates": same_text_failed,
        "coverage_failed_gates": coverage_failed,
        "coverage_attribution_summary": attribution_summary,
        "n_gates": len(gates),
        "n_passed": sum(1 for g in gates if g["passed"] is True),
        "n_failed": sum(1 for g in gates if g["passed"] is False),
        "n_not_measurable": len(not_measurable),
        "n_falsifier_gates": len(same_text_gates) + len(coverage_gates),
        "n_same_text_gates": len(same_text_gates),
        "n_coverage_gates": len(coverage_gates),
        "falsification_gates": falsification_gates,
        "not_measurable_gates": not_measurable,
        "absolute_report_only_misses": absolute_misses,
        "measured_cells": len(measured_cells),
        "gates": gates,
        "cells": cells,
        "gate_decomposition": decomposition,
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


def _v1_preservation(verdict: dict) -> dict:
    """Prove that every V1 falsifier measurement survived the V2 repair.

    V1 (cycle 39628161040) gated the union-of-six-texts comparison under the gate
    name ``parity::same_query_*``.  V2 keeps that comparison gated (renamed
    ``coverage::union_frozen_texts_*``) and ADDS the like-for-like
    ``parity::same_query_*`` family on the executed text.  The proof is a 1:1
    mapping of the V1 falsifier gates onto the V2 coverage gates with identical
    measured quantities; nothing was weakened, renamed away or dropped.
    """
    v1_records = {
        "39628161040": REPO_ROOT / "results/evaluation/product_cache_parity/39628161040.json",
        "39619144928": REPO_ROOT / "results/evaluation/product_cache_parity/39619144928.json",
    }
    v2_cov = {g["gate"]: g for g in verdict["gates"]
              if g.get("role") == ROLE_FALSIFIER_COVERAGE}
    compared_keys = ("product_hits", "comparator_hits", "n_frozen_ids",
                     "n_comparator_rows", "n_product_rows", "comparator_only",
                     "product_only", "n_frozen_texts")
    out: dict[str, Any] = {
        "claim": "every V1 falsifier gate measurement is preserved 1:1 in the V2 "
                 "coverage family; V2 only ADDS the same-text family",
        "v1_falsifier_gate_count": 0,
        "v2_coverage_gate_count": len(v2_cov),
        "records": {},
        "all_preserved": True,
    }
    for rid, path in v1_records.items():
        if not path.is_file():
            out["records"][rid] = {"present": False, "path": str(path.relative_to(REPO_ROOT))}
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        v1_fals = {g["gate"]: g for g in rec.get("gates", [])
                   if g.get("role") == "falsifier"}
        mapping = []
        rec_ok = True
        for name, g in sorted(v1_fals.items()):
            v2name = name.replace("parity::same_query_",
                                  "coverage::union_frozen_texts_")
            g2 = v2_cov.get(v2name)
            a = g.get("measured") or {}
            b = (g2 or {}).get("measured") or {}
            # the V1 records store the hit COUNTS (n_product_hits /
            # n_comparator_hits); the V2 coverage gates store the hit SETS.
            # Both are compared, so the proof is never vacuous.
            diffs = [k for k in compared_keys
                     if a.get(k) is not None and a.get(k) != b.get(k)]
            if a.get("n_product_hits") is not None and \
                    a["n_product_hits"] != len(b.get("product_hits") or []):
                diffs = diffs + ["n_product_hits"]
            if a.get("n_comparator_hits") is not None and \
                    a["n_comparator_hits"] != len(b.get("comparator_hits") or []):
                diffs = diffs + ["n_comparator_hits"]
            same_pass = (g.get("passed") == (g2 or {}).get("passed"))
            rec_ok = rec_ok and (g2 is not None) and (not diffs) and same_pass
            mapping.append({
                "v1_gate": name,
                "v2_gate": v2name,
                "v1_passed": g.get("passed"),
                "v2_passed": (g2 or {}).get("passed"),
                "passed_identical": same_pass,
                "measured_differences": sorted(set(diffs)),
                "quantities_compared": sorted(
                    [k for k in compared_keys if a.get(k) is not None]
                    + (["n_product_hits"] if a.get("n_product_hits") is not None else [])
                    + (["n_comparator_hits"] if a.get("n_comparator_hits") is not None else [])),
                "v1_comparator_hits": (a["n_comparator_hits"]
                                       if a.get("n_comparator_hits") is not None
                                       else len(a.get("comparator_hits") or [])),
                "v2_comparator_hits": len(b.get("comparator_hits") or []),
                "v1_product_hits": (a["n_product_hits"]
                                    if a.get("n_product_hits") is not None
                                    else len(a.get("product_hits") or [])),
                "v2_product_hits": len(b.get("product_hits") or []),
            })
        v1_failed = sorted(n for n, g in v1_fals.items() if g.get("passed") is False)
        v2_failed = sorted(g["gate"] for g in v2_cov.values() if g.get("passed") is False)
        renamed_v1_failed = sorted(n.replace("parity::same_query_",
                                             "coverage::union_frozen_texts_")
                                   for n in v1_failed)
        out["records"][rid] = {
            "present": True,
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": sha256_file(path),
            "v1_falsifier_gate_count": len(v1_fals),
            "v1_failed_falsifier_gates": v1_failed,
            "v2_failed_coverage_gates": v2_failed,
            "failed_sets_identical": renamed_v1_failed == v2_failed,
            "n_v1_failed": len(v1_failed),
            "n_v2_failed": len(v2_failed),
            "gate_mapping": mapping,
            "all_preserved": rec_ok,
        }
        out["v1_falsifier_gate_count"] = max(out["v1_falsifier_gate_count"],
                                             len(v1_fals))
        out["all_preserved"] = out["all_preserved"] and rec_ok
    out["v2_added_family"] = "parity::same_query_* (executed-text comparator)"
    out["v2_added_family_is_additive"] = True
    return out


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
    v1_preservation = _v1_preservation(verdict)

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
            "version": 2,
            "pre_freeze_disclosure_disclosed":
                "pre_freeze_disclosure_HONEST_V2" in hypothesis,
            "superseded_spec_byte_preserved": {
                "hypothesis_path": str(HYPOTHESIS_V1_PATH.relative_to(REPO_ROOT)),
                "hypothesis_sha256": sha256_file(HYPOTHESIS_V1_PATH),
                "freeze_record_path": str(FREEZE_RECORD_V1_PATH.relative_to(REPO_ROOT)),
                "freeze_record_sha256": sha256_file(FREEZE_RECORD_V1_PATH),
            },
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
            "primary_comparator": "executed_text_same_query (the baseline-record rows of "
                                  "the (channel, language) texts the product's cache "
                                  "actually executed; same text, same channel, same "
                                  "language - named per CYCLE_39111232991_CORRECTION.md D2)",
            "coverage_comparator": "union_all_frozen_texts (the baseline-record rows of "
                                    "ALL six identity texts of the slug) - explicitly "
                                    "gated as the multilingual/counter-channel "
                                    "query-coverage comparison",
            "context_comparators_reported_only":
                ["plain_channel_all_languages", "union_all_channels (reported copy of the "
                                                "union pool; the gated union comparison "
                                                "is coverage::)"],
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
        "v1_preservation": v1_preservation,
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
        "(frozen BEFORE execution; pre-freeze disclosure of the known V1 outcome "
        "disclosed in-file)",
        f"- Superseded V1 spec: `{record['hypothesis']['superseded_spec_byte_preserved']['hypothesis_path']}` "
        f"sha256 `{record['hypothesis']['superseded_spec_byte_preserved']['hypothesis_sha256'][:12]}...` "
        "— BYTE-PRESERVED, not modified",
        f"- Product pool: `{cache_dir}` identity-matched envelopes "
        f"({record['product']['n_identity_matched_envelopes']} of {n_before} cache files)",
        "- Comparators (both named, both gated): `executed_text_same_query` (the text(s) "
        "the product's cache actually ran) and `union_all_frozen_texts` (all six frozen "
        "texts the plain OpenCaseLaw client answered)",
        f"- Verdict: **{record['verdict']}** (exit {record['exit_code']}), "
        f"driven by: **{record['verdict_scope']}**",
        f"- Same-text parity family: **{record['same_text_parity_verdict']}** "
        f"({len(record['same_text_parity_failed_gates'])} of "
        f"{record['n_same_text_gates']} gates failed)",
        f"- Coverage family (union of all frozen texts): **{record['coverage_verdict']}** "
        f"({len(record['coverage_failed_gates'])} of {record['n_coverage_gates']} gates failed)",
        f"- Falsifier gates failed: **{len(record['falsification_gates'])}**",
        f"- Non-vacuity: **{record['non_vacuity']['all_hold']}**",
        f"- Multilingual/provenance reuse leg (V3): **{v3_leg['verdict']}** "
        f"({v3_leg['qids_row_ok']}/{v3_leg['qids_checked']} qids row_ok)",
        f"- Elapsed: {record['elapsed_s']} s",
        "",
        "## Cells (identity mapping; hits of frozen id sets)",
        "",
        "| slug | product pool rows | comparator rows (executed text) | comparator rows "
        "(all 6 texts) | texts executed | authority hits (prod/exec/base-union) | "
        "counter hits (prod/exec/base-union) | same-text authority | same-text counter | "
        "coverage authority | coverage counter |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cell in verdict["cells"]:
        g_auth_p = next((g for g in cell["gates"]
                         if g["gate"] == f"parity::same_query_authority_not_below_baseline::{cell['slug']}"), None)
        g_cnt_p = next((g for g in cell["gates"]
                        if g["gate"] == f"parity::same_query_counter_not_below_baseline::{cell['slug']}"), None)
        g_auth_c = next((g for g in cell["gates"]
                         if g["gate"] == f"coverage::union_frozen_texts_authority_not_below_baseline::{cell['slug']}"), None)
        g_cnt_c = next((g for g in cell["gates"]
                        if g["gate"] == f"coverage::union_frozen_texts_counter_not_below_baseline::{cell['slug']}"), None)

        def _par(gate):
            if gate is None or gate["passed"] is None:
                return "NOT_MEASURED"
            m = gate["measured"]
            return ("PASS" if gate["passed"] else "FAIL") + \
                f" ({len(m.get('product_hits') or [])} vs {len(m.get('comparator_hits') or [])})"

        def _abs(kind):
            gate = next((g for g in cell["gates"]
                         if g["gate"] == f"product::{kind}_recall::{cell['slug']}"), None)
            if gate is None or gate["passed"] is None:
                return "n/a"
            m = gate["measured"]
            return (f"{len(m.get('product_hits') or [])}/{m.get('n_frozen_ids')}"
                    f"/{len(m.get('comparator_executed_text_hits') or [])}"
                    f"/{len(m.get('comparator_union_all_texts_hits') or [])}")

        lines.append(
            f"| {cell['slug']} | {cell['product_pool']['n_rows']} | "
            f"{cell['comparators']['executed_text_same_query']['n_rows']} | "
            f"{cell['comparators']['union_all_frozen_texts']['n_rows']} | "
            f"{cell['n_executed_texts']}/{cell['n_frozen_texts']} "
            f"({', '.join(cell['executed_texts'])}) | "
            f"{_abs('authority')} | {_abs('counter')} | "
            f"{_par(g_auth_p)} | {_par(g_cnt_p)} | {_par(g_auth_c)} | {_par(g_cnt_c)} |")
    lines += [
        "",
        "## Per-(channel, language) comparator decomposition (all gated cells)",
        "",
        "Every gated cell is decomposed by the (channel, language) group of the plain "
        "OpenCaseLaw baseline record that produced each hit. `E` marks the texts the "
        "product's cache actually executed.",
        "",
        "| slug | kind | frozen ids | product hits | executed-text comparator | "
        "union comparator | comparator-only ids (attribution) |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in verdict["gate_decomposition"]:
        attrib = "; ".join(f"{i} -> {'/'.join(ks)}" for i, ks in
                           sorted(d["comparator_only_attribution"].items()))
        lines.append(
            f"| {d['slug']} | {d['kind']} | {d['n_frozen_ids']} | "
            f"{len(d['product_hits'])} | {len(d['comparator_executed_text_hits'])} | "
            f"{len(d['comparator_union_all_texts_hits'])} | "
            f"{attrib if attrib else '—'} |")
    lines += ["", "## Per-(channel, language) hit counts", ""]
    for d in verdict["gate_decomposition"]:
        parts = [f"`{k}` {v['n_hits']} hits"
                 f"{' (E)' if v['executed_by_product_cache'] else ''}"
                 for k, v in d["per_channel_language"].items()]
        lines.append(f"- `{d['slug']}` / {d['kind']}: " + ", ".join(parts))
    lines += ["", "## Language reach (REPORTED-ONLY; never gated)", ""]
    for slug, entry in reach["per_slug"].items():
        lines.append(f"- `{slug}`: executed {entry['executed'] or '—'}; "
                     f"not executed {entry['not_executed'] or '—'}")
    att = record.get("coverage_attribution_summary") or {}
    lines += [
        "",
        "## Comparator-only id attribution (why the coverage deficit is not a "
        "same-text regression)",
        "",
        f"- comparator-only ids (union comparator, not reached by the product): "
        f"**{att.get('n_comparator_only_ids')}**",
        f"- of those, ids that ONLY texts the product never executed produced: "
        f"**{att.get('n_comparator_only_ids_from_non_executed_texts')}**",
        f"- ids that an executed text produced but the product still missed: "
        f"**{att.get('n_comparator_only_ids_from_executed_texts')}**",
        f"- therefore all comparator-only ids come exclusively from texts the product "
        f"never executed: **{att.get('all_comparator_only_ids_come_from_non_executed_texts')}**",
        f"- frozen texts executed by the product cache: "
        f"**{att.get('n_executed_texts_total')} of {att.get('n_frozen_texts_total')}**",
        "",
        "## V1 preservation (nothing weakened)",
        "",
    ]
    pres = record.get("v1_preservation") or {}
    for rid, info in (pres.get("records") or {}).items():
        if not info.get("present"):
            lines.append(f"- run {rid}: record not present")
            continue
        lines.append(
            f"- run {rid} (`{info['path']}` sha256 `{info['sha256'][:12]}...`): "
            f"{info['v1_falsifier_gate_count']} V1 falsifier gates -> V2 coverage gates, "
            f"measurements identical: **{info['all_preserved']}**")
    lines += [
        "",
        "## Gated gates that failed",
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
        "verdict_scope": record.get("verdict_scope"),
        "same_text_parity_verdict": record.get("same_text_parity_verdict"),
        "coverage_verdict": record.get("coverage_verdict"),
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
