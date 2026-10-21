#!/usr/bin/env python3
"""Smallest executable retrieval/counter-authority benchmark that can falsify
the product's single-language adversarial pass.

WHY THIS INSTRUMENT EXISTS (factory direction v61, lanes.evaluation)
--------------------------------------------------------------------
The lane's frozen retrieval benchmark measures the counter-authority channel
POOLED over all three official languages (``counter::known_counter_recall`` =
the union of the FR, DE and IT counter queries, 90 counter rows per question),
and it measures the BASELINE channel per language
(``authority::baseline_lang_recall::<slug>::<lang>``).  What nobody in this
lane has measured is the cut the Master Prompt's adversarial research
requirement actually depends on:

    can the independent counter-authority pass, issued in ONE of FR/DE/IT,
    still reach the known contrary/limiting authorities of that question?

If the answer is no for a language, a product that runs the adversarial pass
only in the question's own language silently loses known counter authority in
the other two, which is exactly what the retrieval-first doctrine forbids
("a visualization cannot reveal an authority that retrieval failed to find").

REUSE-FIRST — nothing measurement-bearing is re-derived here
------------------------------------------------------------
* frozen id sets, query texts and languages:
  ``evaluation/retrieval_gate/frozen_retrieval_benchmark.json`
  (sha256 187b0e54..., re-hashed fail-closed before AND after execution);
* id matching, alnum-core reconciliation, row extraction, pooling:
  the ACCEPTED ``evaluation.retrieval_gate.gates`` module (match_authorities /
  row_cores / _pool / extract_rows) — no matcher, tokeniser or stoplist is
  written, re-tuned or paraphrased;
* the measurement input is the ACCEPTED offline-replay record
  ``results/evaluation/retrieval_benchmark/39117425713.json`` (audit gate
  PASS for run 39117425713, the same record the accepted stand-ready
  multilingual probe and concept-seed instrument pin as their frozen record);
* the per-language BASELINE authority cells are REPUBLISHED read-only beside
  this run's own numbers, never re-decided;
* the accepted pooled ``counter::known_counter_recall`` gate is reused as the
  faithfulness oracle for this cut (subset identity, see control C2).

WHAT IS NEW is only the decomposition itself: per (question x language)
known-counter hit sets of the frozen counter channel, plus the strictness
disclosure ``pooled_only`` (hit by the pooled gate but by no single-language
counter query).

FROZEN RULE (evaluation/COUNTER_CHANNEL_LANGUAGE_REACH_HYPOTHESIS_V1.json,
written BEFORE this scorer executed; the pre-freeze reconnaissance is disclosed
there verbatim)
------------------------------------------------------------------------------
per slug, with a non-empty frozen known-counter set and all three counter
queries answered (status 200, rows > 0):

  REACH_LOST   some language's counter channel reaches ZERO known counter ids
  REACH_HELD   every language's counter channel reaches >= 1 known counter id

  NOT_MEASURED_NO_RESPONSE        a counter query is unanswered / has no rows
  NOT_MEASURED_EMPTY_FROZEN_SET   the frozen known-counter set is empty

NOT_MEASURED is never a pass and never a fail (the accepted not-measurable
convention).  Exit codes:

  0  COUNTER_SINGLE_LANGUAGE_REACH_HELD   >=1 slug measured, none REACH_LOST
  1  COUNTER_SINGLE_LANGUAGE_REACH_LOST   >=1 slug REACH_LOST (falsifies H)
  2  ENVIRONMENT_OR_VACUOUS               pin drift, control failure, or no
                                          measurable slug

Zero new thresholds: "reaches zero" is set emptiness on frozen ids, not a
tuned number; no bar, rubric, stoplist, tokeniser or verdict contract of the
frozen suite is read for enforcement, edited, re-derived or paraphrased.  The
frozen absolute LABEL_SOUND / GEOMETRY_SOUND bars stay REPORTED-ONLY and are
not touched by this instrument at all.

SCRATCH-RUN OBLIGATION
----------------------
``--out`` / ``--report`` MUST be given for any non-claim-bearing invocation
(a unit test, a local poke); the defaults are the committed claim-bearing
paths for run 39587184968 and a scratch run would overwrite them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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

SCHEMA = "lex-evaluation-counter-channel-language-reach/1"
SPEC_RELPATH = "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"
RECORD_RELPATH = "results/evaluation/retrieval_benchmark/39117425713.json"
HYPOTHESIS_RELPATH = "evaluation/COUNTER_CHANNEL_LANGUAGE_REACH_HYPOTHESIS_V1.json"
FREEZE_RECORD_RELPATH = "evaluation/COUNTER_CHANNEL_LANGUAGE_REACH_FREEZE_RECORD_V1.json"
GATES_RELPATH = "evaluation/retrieval_gate/gates.py"
FROZEN_MOD_RELPATH = "evaluation/retrieval_gate/frozen.py"
ENGINE_RELPATH = "evaluation/counter_channel_language_reach.py"

RUN_ID = "39587184968"
DEFAULT_OUT = REPO_ROOT / "results" / "evaluation" / "counter_channel_language_reach" / f"{RUN_ID}.json"
DEFAULT_REPORT = REPO_ROOT / "reports" / "evaluation" / f"COUNTER_CHANNEL_LANGUAGE_REACH_{RUN_ID}.md"

EXIT_HELD = 0
EXIT_LOST = 1
EXIT_ENVIRONMENT = 2

CLASS_REACH_LOST = "REACH_LOST"
CLASS_REACH_HELD = "REACH_HELD"
CLASS_NM_NO_RESPONSE = "NOT_MEASURED_NO_RESPONSE"
CLASS_NM_EMPTY_SET = "NOT_MEASURED_EMPTY_FROZEN_SET"

MEASURED_CLASSES = (CLASS_REACH_LOST, CLASS_REACH_HELD)

CLAIM_CEILING = (
    "This instrument establishes exactly one thing: on the ACCEPTED offline-replay "
    "retrieval record of the frozen 4-question benchmark, whether each of the FR/DE/IT "
    "counter-authority queries independently reaches at least one of the frozen known "
    "counter ids of its question. It is a retrieval-layer measurement of the frozen "
    "baseline channel, NOT of Product's shipped counter-emission stage, and NOT a claim "
    "about LABEL_SOUND / GEOMETRY_SOUND (both stay REPORTED-ONLY), about jurist "
    "usefulness, or about the map. It lifts no DO-NOT-SERVE order; admission stays "
    "fail-closed; human_gate_ready and owner_decision_required stay false. No universal-174k "
    "benchmark is run."
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _display_path(path: Path) -> str:
    """Repo-relative path when inside the repo, absolute otherwise (scratch runs)."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def numeric_environment() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "numeric_scope": "pure-Python set operations on committed record bytes; no BLAS/numpy "
                         "reduction order is involved, so no float comparison is made",
    }


def _require_pins(freeze: dict, overrides: dict[str, Path] | None = None) -> dict[str, Any]:
    """Fail-closed re-hash of every pinned input.  Drift -> exit 2, never a verdict.

    ``overrides`` substitutes the path actually read for a pinned relative path,
    so passing a tampered ``--record`` cannot satisfy the pin of the committed
    record: the bytes actually measured must equal the frozen bytes.
    """
    pins = freeze.get("pins") or {}
    overrides = overrides or {}
    checked: dict[str, str] = {}
    drift: dict[str, dict[str, str | None]] = {}
    for rel, expected in pins.items():
        path = overrides.get(rel, REPO_ROOT / rel)
        actual = sha256_file(path) if path.is_file() else None
        checked[rel] = actual or "MISSING"
        if actual != expected:
            drift[rel] = {"expected": expected, "actual": actual}
    return {"checked": checked, "drift": drift, "ok": not drift}


# --------------------------------------------------------------------------- #
# measurement
# --------------------------------------------------------------------------- #
def _accepted_pooled_counter_hits(record: dict, slug: str) -> dict[str, Any]:
    """The accepted pooled counter gate's own hit set (read-only reuse)."""
    for g in (record.get("verdict") or {}).get("gates") or []:
        if g.get("gate") == f"counter::known_counter_recall::{slug}":
            measured = g.get("measured") or {}
            return {
                "present": True,
                "passed": g.get("passed"),
                "hits": sorted(measured.get("hits") or []),
                "n_required": len(measured.get("required") or []),
            }
    return {"present": False, "passed": None, "hits": [], "n_required": None}


def _republished_baseline_lang_cells(record: dict, slug: str) -> dict[str, Any]:
    """Accepted per-language BASELINE authority cells, republished read-only."""
    out: dict[str, Any] = {}
    for g in (record.get("verdict") or {}).get("gates") or []:
        name = str(g.get("gate") or "")
        prefix = f"authority::baseline_lang_recall::{slug}::"
        if not name.startswith(prefix):
            continue
        measured = g.get("measured") or {}
        out[name[len(prefix):]] = {
            "passed": g.get("passed"),
            "detail": g.get("detail"),
            "hits": sorted(measured.get("hits") or []),
            "missing": sorted(measured.get("missing") or []),
            "n_required": len(measured.get("required") or []),
            "republished_not_redecided": True,
        }
    return out


def classify(per_lang_hits: dict[str, list[str]], known: list[str],
             per_lang_response: dict[str, dict[str, Any]]) -> str:
    """The frozen rule.  Pure function: same inputs -> same classification."""
    if not known:
        return CLASS_NM_EMPTY_SET
    for lang in rg_frozen.LANGUAGES:
        resp = per_lang_response.get(lang) or {}
        if resp.get("status") != 200 or not resp.get("n_rows"):
            return CLASS_NM_NO_RESPONSE
    for lang in rg_frozen.LANGUAGES:
        if not per_lang_hits.get(lang):
            return CLASS_REACH_LOST
    return CLASS_REACH_HELD


def measure_slug(question: dict, record: dict) -> dict[str, Any]:
    slug = question["slug"]
    known = [str(k["id"]) for k in question.get("known_counter_ids") or []]
    queries = record.get("queries") or []

    per_lang_hits: dict[str, list[str]] = {}
    per_lang_missing: dict[str, list[str]] = {}
    per_lang_response: dict[str, dict[str, Any]] = {}
    per_lang_evidence: dict[str, list[dict[str, str]]] = {}
    union: set[str] = set()

    for lang in rg_frozen.LANGUAGES:
        rows = rg_gates._pool(queries, slug=slug, channel="counter", language=lang)
        meta = next((q for q in queries if q.get("slug") == slug
                     and q.get("channel") == "counter" and q.get("language") == lang), {})
        per_lang_response[lang] = {
            "query_key": meta.get("query_key"),
            "status": meta.get("status"),
            "n_rows": len(rows),
            "raw_sha256": meta.get("raw_sha256"),
        }
        matches = rg_gates.match_authorities(known, rows) if known else {}
        hits = sorted(k for k, v in matches.items() if v)
        missing = sorted(k for k, v in matches.items() if not v)
        per_lang_hits[lang] = hits
        per_lang_missing[lang] = missing
        union |= set(hits)
        per_lang_evidence[lang] = [
            {"decision_id": rows[i].get("decision_id"),
             "canonical_url": rows[i].get("canonical_url")}
            for i in range(len(rows))
            if rows[i].get("decision_id") in set(hits)
        ][:5]

    classification = classify(per_lang_hits, known, per_lang_response)
    pooled = _accepted_pooled_counter_hits(record, slug)
    pooled_hits = set(pooled["hits"])
    counter_union = set(union)
    lang_sets = {lang: set(per_lang_hits.get(lang) or []) for lang in rg_frozen.LANGUAGES}
    distinct_sets = {frozenset(v) for v in lang_sets.values()}

    pairwise = {}
    for i, a in enumerate(rg_frozen.LANGUAGES):
        for b in rg_frozen.LANGUAGES[i + 1:]:
            pairwise[f"{a}_vs_{b}"] = {
                "equal": lang_sets[a] == lang_sets[b],
                "only_in_" + a: sorted(lang_sets[a] - lang_sets[b]),
                "only_in_" + b: sorted(lang_sets[b] - lang_sets[a]),
            }

    return {
        "slug": slug,
        "known_counter_ids": known,
        "n_known": len(known),
        "classification": classification,
        "falsifies_single_language_reach": classification == CLASS_REACH_LOST,
        "per_language": {
            lang: {
                "n_rows": per_lang_response[lang]["n_rows"],
                "status": per_lang_response[lang]["status"],
                "n_hits": len(per_lang_hits[lang]),
                "hits": per_lang_hits[lang],
                "missing": per_lang_missing[lang],
                "evidence": per_lang_evidence[lang],
            } for lang in rg_frozen.LANGUAGES
        },
        "cross_language": {
            "n_distinct_hit_sets": len(distinct_sets),
            "sets_identical_across_languages": len(distinct_sets) == 1,
            "pairwise": pairwise,
        },
        "decomposition": {
            "counter_channel_union_hits": sorted(counter_union),
            "n_counter_channel_union_hits": len(counter_union),
            "accepted_pooled_gate_present": pooled["present"],
            "accepted_pooled_gate_passed": pooled["passed"],
            "accepted_pooled_gate_hits": sorted(pooled_hits),
            "n_accepted_pooled_gate_hits": len(pooled_hits),
            "counter_union_not_in_pooled": sorted(counter_union - pooled_hits),
            "pooled_only_reached_by_baseline_channel": sorted(pooled_hits - counter_union),
        },
        "republished_baseline_language_cells": _republished_baseline_lang_cells(record, slug),
        "response_pins": per_lang_response,
    }


def measure(spec: dict, record: dict) -> dict[str, Any]:
    slugs = [measure_slug(q, record) for q in spec.get("questions") or []]
    measured = [s for s in slugs if s["classification"] in MEASURED_CLASSES]
    lost = [s for s in slugs if s["classification"] == CLASS_REACH_LOST]
    return {
        "slugs": slugs,
        "n_slugs": len(slugs),
        "n_measured": len(measured),
        "n_reach_lost": len(lost),
        "reach_lost_slugs": [s["slug"] for s in lost],
        "measured_slugs": [s["slug"] for s in measured],
        "not_measured": {s["slug"]: s["classification"] for s in slugs
                         if s["classification"] not in MEASURED_CLASSES},
    }


# --------------------------------------------------------------------------- #
# non-vacuity controls (frozen in the hypothesis, evaluated every run)
# --------------------------------------------------------------------------- #
def _blanked_counter_record(spec: dict, record: dict) -> dict:
    out = dict(record)
    out["queries"] = [
        dict(q, rows=[]) if q.get("channel") == "counter" else q
        for q in record.get("queries") or []
    ]
    return out


def _oracle_counter_record(spec: dict, record: dict, inject_langs: tuple[str, ...]) -> dict:
    """Counter channel replaced by an ORACLE pool: every query keeps exactly one
    unrelated row (so the query is answered and has rows — a NOT_MEASURED guard
    stays out of the way) plus, for each language in ``inject_langs``, one row
    carrying EVERY known counter id of that question."""
    queries = [dict(q) for q in record.get("queries") or []]
    for q in queries:
        if q.get("channel") != "counter":
            continue
        spec_q = next((s for s in spec.get("questions") or []
                       if s["slug"] == q.get("slug")), None)
        if not spec_q:
            continue
        rows: list[dict] = [{
            "decision_id": "oracle_unrelated_row_0001",
            "canonical_decision_id": "oracle_unrelated_row_0001",
            "docket_number": "", "court": "",
            "citation_string_de": "", "citation_string_fr": "",
            "citation_string_it": "", "language": q.get("language"),
            "decision_date": "", "canonical_url": "https://example.invalid/oracle",
            "relevance_score": None, "text_head": "control C3 unrelated row",
        }]
        if q.get("language") in inject_langs:
            for kid in spec_q.get("known_counter_ids") or []:
                rows.append({
                    "decision_id": str(kid.get("id")),
                    "canonical_decision_id": str(kid.get("id")),
                    "docket_number": "", "court": "",
                    "citation_string_de": "", "citation_string_fr": "",
                    "citation_string_it": "", "language": q.get("language"),
                    "decision_date": "", "canonical_url": "https://example.invalid/oracle",
                    "relevance_score": None,
                    "text_head": "oracle injection for control C3",
                })
        q["rows"] = rows
    return {"queries": queries, "verdict": record.get("verdict")}


def controls(spec: dict, record: dict) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    # C1 — a counter query with no response must be NOT_MEASURED, never a verdict.
    c1_record = dict(record)
    c1_record["queries"] = [
        dict(q, rows=[], status=503, error="control C1 simulated transport failure")
        if (q.get("channel") == "counter" and q.get("slug") == (spec["questions"][0]["slug"]))
        else q
        for q in record.get("queries") or []
    ]
    c1_res = measure(spec, c1_record)
    c1_target = spec["questions"][0]["slug"]
    c1_class = next((s["classification"] for s in c1_res["slugs"]
                     if s["slug"] == c1_target), None)
    c1_ok = c1_class == CLASS_NM_NO_RESPONSE
    out.append({
        "control": "C1_unanswered_counter_query_is_NOT_MEASURED_not_a_verdict",
        "holds": c1_ok,
        "why": f"with the {c1_target} counter queries simulated as unanswered, the slug "
               f"classifies {c1_class!r}; a gate that reported a product verdict from "
               f"missing data would be vacuous",
        "measured": {"slug": c1_target, "classification": c1_class},
    })

    # C2 — faithfulness: this cut's union must be a SUBSET of the accepted pooled
    # counter gate's hits, otherwise the decomposition is unfaithful.
    c2_failures = []
    c2_pooled_only = {}
    for s in measure(spec, record)["slugs"]:
        d = s["decomposition"]
        if d["counter_union_not_in_pooled"]:
            c2_failures.append({"slug": s["slug"],
                                "counter_union_not_in_pooled": d["counter_union_not_in_pooled"]})
        c2_pooled_only[s["slug"]] = d["pooled_only_reached_by_baseline_channel"]
        if not d["accepted_pooled_gate_present"]:
            c2_failures.append({"slug": s["slug"], "reason": "accepted pooled counter gate absent"})
    out.append({
        "control": "C2_counter_channel_union_is_subset_of_accepted_pooled_counter_gate",
        "holds": not c2_failures,
        "why": "the per-language cut pools a subset of the rows the accepted "
               "counter::known_counter_recall gate pools (90 counter rows of 240 total), so "
               "its hit set can never exceed the accepted gate's; a violation would mean "
               "this cut is not a faithful decomposition and must not be published",
        "measured": {"failures": c2_failures, "pooled_only_per_slug": c2_pooled_only},
    })

    # C3 — A/B flip: the rule must recognise a fully-reached ORACLE record as
    # HELD and must flip to LOST when exactly one language's reach is removed
    # (the query stays answered, so the flip can never be a NOT_MEASURED artefact).
    full = _oracle_counter_record(spec, record, tuple(rg_frozen.LANGUAGES))
    full_res = measure(spec, full)
    nonempty = [s for s in full_res["slugs"] if s["n_known"] > 0]
    all_held = bool(nonempty) and all(s["classification"] == CLASS_REACH_HELD
                                      for s in nonempty)
    minus_it = _oracle_counter_record(spec, record,
                                      tuple(l for l in rg_frozen.LANGUAGES if l != "it"))
    minus_it_res = measure(spec, minus_it)
    nonempty2 = [s for s in minus_it_res["slugs"] if s["n_known"] > 0]
    flipped = bool(nonempty2) and all(s["classification"] == CLASS_REACH_LOST
                                      for s in nonempty2)
    out.append({
        "control": "C3_rule_flips_HELD_when_one_language_loses_reach",
        "holds": bool(all_held and flipped),
        "why": "an ORACLE counter pool that reaches every known counter id from every "
               "language must classify REACH_HELD, and removing only the IT injection "
               "(keeping the IT query answered with an unrelated row) must flip every "
               "non-empty-set slug to REACH_LOST — otherwise the rule could not "
               "discriminate and an observed HELD would be vacuous",
        "measured": {"oracle_all_langs_classifications": {s["slug"]: s["classification"]
                                                          for s in full_res["slugs"]},
                     "oracle_without_it_classifications": {s["slug"]: s["classification"]
                                                           for s in minus_it_res["slugs"]}},
    })
    return out


# --------------------------------------------------------------------------- #
# verdict
# --------------------------------------------------------------------------- #
def verdict_of(measure_res: dict, control_res: list[dict], pin_ok: bool) -> dict[str, Any]:
    if not pin_ok:
        return {"exit_code": EXIT_ENVIRONMENT,
                "verdict": "ENVIRONMENT_OR_VACUOUS",
                "reason": "frozen input pin drift (fail-closed before measurement)"}
    failed_controls = [c["control"] for c in control_res if not c["holds"]]
    if failed_controls:
        return {"exit_code": EXIT_ENVIRONMENT,
                "verdict": "ENVIRONMENT_OR_VACUOUS",
                "reason": f"non-vacuity control(s) did not hold: {failed_controls}"}
    if measure_res["n_measured"] == 0:
        return {"exit_code": EXIT_ENVIRONMENT,
                "verdict": "ENVIRONMENT_OR_VACUOUS",
                "reason": "no slug measurable (missing responses or empty frozen sets) — "
                          "never counted as a pass"}
    if measure_res["n_reach_lost"] >= 1:
        return {"exit_code": EXIT_LOST,
                "verdict": "COUNTER_SINGLE_LANGUAGE_REACH_LOST",
                "reason": "at least one frozen question loses ALL known counter reach in at "
                          "least one of FR/DE/IT on the counter channel alone: "
                          f"{measure_res['reach_lost_slugs']}"}
    return {"exit_code": EXIT_HELD,
            "verdict": "COUNTER_SINGLE_LANGUAGE_REACH_HELD",
            "reason": "every measurable frozen question reaches >=1 known counter id from "
                      "each of FR/DE/IT on the counter channel alone; the rule is proven "
                      "discriminating by control C3"}


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def render_report(record: dict) -> str:
    m = record["measurement"]
    v = record["verdict"]
    lines = [
        f"# Counter-Channel Single-Language Reach — run {record['run_id']}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Direction: v{record['direction_version']} (`state/evaluation.json` at run time)",
        f"- Engine: `evaluation/counter_channel_language_reach.py`",
        f"- Frozen input: `{RECORD_RELPATH}` (accepted offline replay, audit gate PASS for "
        f"run 39117425713), pinned sha256 `{record['pins']['checked'].get(RECORD_RELPATH)}`",
        f"- Frozen spec: `{SPEC_RELPATH}` sha256 "
        f"`{record['pins']['checked'].get(SPEC_RELPATH)}` (re-hashed after execution: "
        f"{'MATCH' if record['post_execution_pins']['ok'] else 'DRIFT'})",
        f"- Combined verdict: **{v['verdict']}** (exit {v['exit_code']})",
        f"- Elapsed: {record['elapsed_seconds']} s",
        "",
        "## Reason",
        "",
        v["reason"],
        "",
        "## Per-question result (frozen rule)",
        "",
        "| question | classification | fr | de | it | distinct hit sets | pooled (accepted) | pooled-only |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in m["slugs"]:
        pl = s["per_language"]
        d = s["decomposition"]
        lines.append(
            f"| {s['slug']} | `{s['classification']}` | "
            f"{pl['fr']['n_hits']} | {pl['de']['n_hits']} | {pl['it']['n_hits']} | "
            f"{s['cross_language']['n_distinct_hit_sets']} | "
            f"{d['n_accepted_pooled_gate_hits']} | "
            f"{len(d['pooled_only_reached_by_baseline_channel'])} |"
        )
    if not m["slugs"]:
        lines.append("| (no slug measured — see verdict reason) | — | — | — | — | — | — | — |")
    lines += ["",
              "Cells are known-counter hits per language (denominator = the question's frozen "
              "known-counter set); full hit id sets and per-language evidence are in the "
              "machine record."]
    lines += [
        "",
        "## Hit sets (frozen ids, per language)",
        "",
    ]
    for s in m["slugs"]:
        lines.append(f"### {s['slug']} — `{s['classification']}`")
        lines.append("")
        for lang in rg_frozen.LANGUAGES:
            pl = s["per_language"][lang]
            lines.append(f"- **{lang}** ({pl['n_rows']} counter rows, status {pl['status']}): "
                         f"{pl['n_hits']}/{s['n_known']} — {pl['hits']}")
        d = s["decomposition"]
        lines.append(f"- counter-channel union: {d['n_counter_channel_union_hits']}/{s['n_known']}")
        lines.append(f"- accepted pooled gate (all channels, all languages): "
                     f"{d['n_accepted_pooled_gate_hits']}/{s['n_known']} "
                     f"(passed={d['accepted_pooled_gate_passed']})")
        lines.append(f"- pooled-only, reached by a BASELINE query but by no single-language "
                     f"counter query: {d['pooled_only_reached_by_baseline_channel']}")
        lines.append(f"- distinct hit sets across languages: "
                     f"{s['cross_language']['n_distinct_hit_sets']}")
        base = s["republished_baseline_language_cells"]
        if base:
            lines.append("- republished accepted BASELINE per-language cells "
                         "(read-only, not re-decided): " + "; ".join(
                             f"{lang} passed={cell['passed']} "
                             f"{len(cell['hits'])}/{cell['n_required']}"
                             for lang, cell in sorted(base.items())))
        lines.append("")
    lines += ["## Non-vacuity controls", ""]
    for c in record["controls"]:
        lines.append(f"- **{c['control']}** — {'HOLDS' if c['holds'] else 'FAILED'}: {c['why']}")
    lines += ["", "## Claim ceiling", "", record["claim_ceiling"], "",
              "## Numeric environment", ""]
    for k, val in record["environment"].items():
        lines.append(f"- {k}: {val}")
    lines += ["", "## Reproducibility", ""]
    for rel, sha in record["pins"]["checked"].items():
        lines.append(f"- `{rel}` sha256 `{sha}` (pre-execution)")
    for rel, sha in record["post_execution_pins"]["checked"].items():
        lines.append(f"- `{rel}` sha256 `{sha}` (post-execution, "
                     f"{'MATCH' if record['post_execution_pins']['ok'] else 'DRIFT'})")
    lines.append("")
    lines.append(f"Machine record: `{record['out_path']}`")
    lines.append("")
    lines.append("No universal-174k benchmark was run; no frozen bar, rubric, threshold or "
                 "verdict contract was read for enforcement, edited, re-derived or "
                 "paraphrased.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def run(spec_path: Path, record_path: Path, hypothesis_path: Path, freeze_path: Path,
        out_path: Path, report_path: Path, run_id: str) -> tuple[dict, int]:
    started = time.time()
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    hypothesis = json.loads(hypothesis_path.read_text(encoding="utf-8"))

    # Fail-closed pin verification BEFORE measurement (self sha included).
    # The bytes actually read must be the frozen bytes: a tampered --record,
    # --spec or --hypothesis substitutes its own path here and fails the pin.
    pins = _require_pins(freeze, {
        SPEC_RELPATH: spec_path,
        RECORD_RELPATH: record_path,
        HYPOTHESIS_RELPATH: hypothesis_path,
    })
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    rec = json.loads(record_path.read_text(encoding="utf-8"))

    if pins["ok"]:
        rg_frozen._validate(spec)
        if rec.get("frozen_sha256") != pins["checked"][SPEC_RELPATH]:
            pins["ok"] = False
            pins["drift"]["record.frozen_sha256"] = {
                "expected": pins["checked"][SPEC_RELPATH],
                "actual": rec.get("frozen_sha256"),
            }

    measurement = measure(spec, rec) if pins["ok"] else {
        "slugs": [], "n_slugs": 0, "n_measured": 0, "n_reach_lost": 0,
        "reach_lost_slugs": [], "measured_slugs": [], "not_measured": {}}
    control_res = controls(spec, rec) if pins["ok"] else []
    v = verdict_of(measurement, control_res, pins["ok"])
    post = _require_pins(freeze, {
        SPEC_RELPATH: spec_path,
        RECORD_RELPATH: record_path,
        HYPOTHESIS_RELPATH: hypothesis_path,
    })

    result = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": hypothesis["direction_version"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "instrument": ENGINE_RELPATH,
        "hypothesis": HYPOTHESIS_RELPATH,
        "freeze_record": FREEZE_RECORD_RELPATH,
        "hypothesis_sha256": sha256_file(hypothesis_path),
        "freeze_record_sha256": sha256_file(freeze_path),
        "record_input": RECORD_RELPATH,
        "spec_input": SPEC_RELPATH,
        "pins": pins,
        "post_execution_pins": post,
        "measurement": measurement,
        "controls": control_res,
        "verdict": v,
        "hypothesis_statement": hypothesis.get("hypothesis"),
        "rule": hypothesis.get("frozen_rule"),
        "exit_code_contract": hypothesis.get("exit_code_contract"),
        "claim_ceiling": hypothesis.get("claim_ceiling", CLAIM_CEILING),
        "environment": numeric_environment(),
        "elapsed_seconds": round(time.time() - started, 3),
        "out_path": _display_path(out_path),
        "not_measured_convention": "NOT_MEASURED_* is never a pass and never a fail "
                                   "(accepted gates convention)",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(result), encoding="utf-8")
    return result, v["exit_code"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--spec", default=str(REPO_ROOT / SPEC_RELPATH))
    ap.add_argument("--record", default=str(REPO_ROOT / RECORD_RELPATH))
    ap.add_argument("--hypothesis", default=str(REPO_ROOT / HYPOTHESIS_RELPATH))
    ap.add_argument("--freeze-record", default=str(REPO_ROOT / FREEZE_RECORD_RELPATH))
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="SCRATCH RUNS MUST PASS THIS (committed claim-bearing default)")
    ap.add_argument("--report", default=str(DEFAULT_REPORT),
                    help="SCRATCH RUNS MUST PASS THIS (committed claim-bearing default)")
    args = ap.parse_args(argv)
    result, code = run(Path(args.spec), Path(args.record), Path(args.hypothesis),
                       Path(args.freeze_record), Path(args.out), Path(args.report),
                       args.run_id)
    print(json.dumps({"verdict": result["verdict"], "out": args.out,
                      "report": args.report}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
