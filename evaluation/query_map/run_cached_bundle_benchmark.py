#!/usr/bin/env python3
"""Smallest executable retrieval / counter-authority benchmark for the query map.

Audit CYCLE_39199651952 F5 named the unbuilt user-visible capability: *does real
or cached OpenCaseLaw input produce a source-linked result bundle and clickable
map?*  ``evaluation/query_map/bundle_producer.py`` answers the build half; this
module answers the **falsify** half by scoring whatever bundle it is given with
the already-accepted ``evaluation.query_map.harness`` and two deliberately
regressed inputs that the same checks must reject.

THREE LEGS, ONE COMBINED RECORD, EXIT CODES THAT CAN FALSIFY

  leg 1  producer_baseline
           Build each frozen question's bundle from the lane's raw OpenCaseLaw
           response cache and run the accepted harness.  Every harness check
           must be true.  Exit 1 means the DATA PLANE or the producer cannot
           honour the bundle contract -- a real finding about whether OpenCaseLaw
           rows can carry the map at all.
  leg 2  falsification_blanked_counter_evidence
           Strip ``counter_evidence`` from every counter-labelled decision.
           ``counter_classifications_supported`` must go FALSE.  Proves the
           counter-evidence contract is live on real rows, not vacuous.
  leg 3  falsification_broken_source_url
           Repoint one decision's ``canonical_url`` off ``mcp.opencaselaw.ch``.
           ``source_urls_valid`` must go FALSE.  Proves source validity is
           live on real rows, not vacuous.

  exit 0  BENCHMARK_VALID_NO_FALSIFICATION
  exit 1  BUNDLE_CONTRACT_VIOLATED   (leg 1 failed on real cached input)
  exit 2  ENVIRONMENT_OR_VACUOUS     (missing cache / frozen spec, or a
                                      falsification leg did NOT fire)

MEASURED, NOT THRESHOLDED
-------------------------
Known-relevant-authority recall, known-counter reach and per-language coverage
are REPORTED with their numerators and denominators.  This module introduces no
new threshold and does not re-derive, re-tune or paraphrase the frozen spec; it
opens it read-only and re-hashes it before and after execution.

SCRATCH-RUN OBLIGATION (same class as benchmark_retrieval_counter_authority.py)
-------------------------------------------------------------------------------
A claim-bearing cycle writes to the committed defaults below.  A scratch
invocation MUST pass ``--out-dir`` / ``--report-dir``, otherwise it silently
rewrites committed claim-bearing records.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.query_map.bundle_producer import (  # noqa: E402
    alnum_core, build_bundle, index_cache, match_frozen_id, read_cache,
)
from evaluation.query_map.harness import evaluate_query_map_bundle  # noqa: E402

SCHEMA = "lex-evaluation-query-map-cached-bundle-benchmark/1"
DEFAULT_SPEC = _REPO_ROOT / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"
DEFAULT_CACHE = _REPO_ROOT / "results/evaluation/retrieval_benchmark/cache"
DEFAULT_OUT_DIR = _REPO_ROOT / "results/evaluation/query_map_cached_bundle_benchmark"
DEFAULT_REPORT_DIR = _REPO_ROOT / "reports/evaluation"

#: Frozen input digests re-hashed by this runner. NEVER edited here; a mismatch is
#: exit 2, never a silent re-freeze.
FROZEN_SPEC_SHA256 = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _hit(row: dict, frozen_id: str, min_core: int) -> dict | None:
    return match_frozen_id(row, frozen_id, min_core_length=min_core)


def score_recall(bundle: dict, question: dict, spec: dict) -> dict:
    """Frozen-id reach measured against the built bundle. Reported, never gated."""
    min_core = int(spec["id_match_rules"]["min_core_length"])
    rows = list(bundle.get("decisions", []))

    def reach(ids: list[str]) -> dict:
        hits = []
        for fid in ids:
            m = next((m for m in (_hit(r, fid, min_core) for r in rows) if m), None)
            hits.append({"id": fid, "found": m is not None,
                         "matched_row": m["row_decision_id"] if m else None})
        n = len(ids)
        found = sum(h["found"] for h in hits)
        return {"expected": n, "found": found,
                "recall": (round(found / n, 4) if n else None),
                "missing": [h["id"] for h in hits if not h["found"]],
                "hits": hits}

    counter_rows = {str(d.get("decision_id")) for d in rows
                    if d.get("counter_status") == "candidate-limiting"}
    counter_reach = reach([c["id"] for c in question.get("known_counter_ids", [])])
    labelled = sum(1 for h in counter_reach["hits"]
                   if h["found"] and h["matched_row"] in counter_rows)
    return {
        "known_relevant": reach(list(question.get("authority_ids", []))),
        "known_counter_reach": counter_reach,
        "n_counter_candidates_emitted": len(counter_rows),
        "n_known_counter_ids_labelled": labelled,
        "languages": sorted({str(d.get("language")) for d in rows}),
    }


def _ensure_one_counter_label(final: dict) -> tuple[dict, bool]:
    """Guarantee the falsification leg has something to falsify.

    If the frozen marker_rule emitted no candidate counter label for this
    question -- which IS the case for 2 of the 4 frozen questions on the cached
    input, and is published as a finding, not hidden -- attach one to the
    top-ranked REAL row using that row's own snippet as evidence.  This is a
    negative-control scaffold only: it makes leg 2 a control that can actually
    fire, it changes nothing leg 1 measures, and the injection is recorded.
    """
    out = copy.deepcopy(final)
    for d in out.get("decisions", []):
        if d.get("counter_status") == "candidate-limiting":
            return out, False
    if out.get("decisions"):
        d = out["decisions"][0]
        d["counter_status"] = "candidate-limiting"
        d["counter_evidence"] = (
            "non-vacuity control: derived from this real row's own snippet - "
            + str(d.get("snippet") or "")[:300])
        d["counter_uncertainty"] = 0.5
    return out, True


def _blank_counter_evidence(final: dict) -> dict:
    out = copy.deepcopy(final)
    for d in out.get("decisions", []):
        if d.get("counter_status") in {"limiting", "contrary_or_exception",
                                       "candidate-limiting", "candidate-contrary"}:
            d["counter_evidence"] = ""
    return out


def _break_one_source_url(final: dict) -> dict:
    out = copy.deepcopy(final)
    for d in out.get("decisions", []):
        if d.get("canonical_url"):
            d["canonical_url"] = "https://example.invalid/entscheid/" + str(d["decision_id"])
            return out
    return out


def run_benchmark(run_id: str, out_dir: Path, report_dir: Path,
                  spec_path: Path, cache_dir: Path) -> tuple[int, dict]:
    t0 = time.time()
    spec_sha_before = sha256_file(spec_path)
    if spec_sha_before != FROZEN_SPEC_SHA256:
        return 2, {"schema": SCHEMA, "run_id": run_id,
                   "verdict": "ENVIRONMENT_OR_VACUOUS",
                   "detail": f"frozen spec digest drift: {spec_sha_before} != {FROZEN_SPEC_SHA256}",
                   "exit_code": 2}
    if not cache_dir.exists():
        return 2, {"schema": SCHEMA, "run_id": run_id,
                   "verdict": "ENVIRONMENT_OR_VACUOUS",
                   "detail": f"raw response cache missing: {cache_dir}", "exit_code": 2}

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    envelopes = read_cache(cache_dir)
    index = index_cache(envelopes, spec)

    per_question: list[dict] = []
    baseline_ok = True
    counter_fires = True
    source_fires = True

    for question in spec["questions"]:
        slug = question["slug"]
        built = build_bundle(slug, index, spec)
        initial, final = built["initial"], built["final"]
        rep = evaluate_query_map_bundle(initial, final)
        leg1_rc = 0 if rep["pass"] else 1
        baseline_ok = baseline_ok and leg1_rc == 0

        rep2_base, injected = _ensure_one_counter_label(final)
        rep2 = evaluate_query_map_bundle(initial, _blank_counter_evidence(rep2_base))
        counter_fires = counter_fires and (rep2["checks"]["counter_classifications_supported"] is False)

        rep3 = evaluate_query_map_bundle(initial, _break_one_source_url(final))
        source_fires = source_fires and (rep3["checks"]["source_urls_valid"] is False)

        built["initial"]["provenance"]["frozen_spec_sha256"] = spec_sha_before
        built["final"]["provenance"]["frozen_spec_sha256"] = spec_sha_before

        per_question.append({
            "slug": slug,
            "producer_meta": built["meta"],
            "leg1_producer_baseline": {
                "exit_code": leg1_rc, "pass": rep["pass"], "checks": rep["checks"],
                "counts": rep["counts"], "languages": rep["languages"],
                "geometry_preserved": rep["geometry"]["preserved"],
                "bad_source_ids": rep["bad_source_ids"],
                "invalid_cited_ids": rep["invalid_cited_ids"],
                "unsupported_counter_ids": rep["unsupported_counter_ids"],
            },
            "leg2_falsification_blanked_counter_evidence": {
                "expected": "counter_classifications_supported == False",
                "observed": rep2["checks"]["counter_classifications_supported"],
                "fired": rep2["checks"]["counter_classifications_supported"] is False,
                "unsupported_counter_ids_n": len(rep2["unsupported_counter_ids"]),
                "n_counter_candidates_from_frozen_marker_rule": built["meta"]["n_counter_candidates"],
                "non_vacuity_label_injected": injected,
                "non_vacuity_note": (
                    "the frozen marker_rule emitted NO candidate counter label for this "
                    "question on cached input; a candidate label derived from the top "
                    "ranked REAL row's own snippet was attached so leg 2 can fire. The "
                    "zero-yield measurement is reported unchanged above and in "
                    "counter_authority_yield - the scaffold changes only leg 2."),
            },
            "leg3_falsification_broken_source_url": {
                "expected": "source_urls_valid == False",
                "observed": rep3["checks"]["source_urls_valid"],
                "fired": rep3["checks"]["source_urls_valid"] is False,
                "bad_source_ids_n": len(rep3["bad_source_ids"]),
            },
            "recall_measured_not_thresholded": score_recall(final, question, spec),
            "bundle_initial": built["initial"],
            "bundle_final": built["final"],
        })

    falsification_proven = counter_fires and source_fires

    zero_yield = [q["slug"] for q in per_question
                  if q["producer_meta"]["n_counter_candidates"] == 0]
    n_cand_total = sum(q["producer_meta"]["n_counter_candidates"] for q in per_question)
    counter_yield = {
        "questions_with_zero_counter_candidates": zero_yield,
        "n_questions": len(per_question),
        "n_counter_candidates_total": n_cand_total,
        "per_question": {q["slug"]: q["producer_meta"]["n_counter_candidates"]
                         for q in per_question},
        "finding": (
            "COUNTER-AUTHORITY DISCOVERY IS EMPTY FOR "
            f"{len(zero_yield)}/{len(per_question)} FROZEN QUESTIONS on the cached input: "
            f"{zero_yield}. The counter channel returns rows, but the frozen marker_rule "
            "(a norm_token AND a limitation_token in title+regeste+snippet) selects none of "
            "them. This is a NEGATIVE RESULT about the product's counter-authority capability "
            "measured on real OpenCaseLaw rows, and it is the opposite of a pass: the map's "
            "counter layer would be empty for half the query set."
            if zero_yield else
            "every frozen question yielded at least one candidate counter label"),
        "not_claimed": ("this measures lexical marker yield under the frozen rule on cached "
                        "rows; it is NOT a measurement of a learned or adjudicated counter "
                        "classifier, and the Frontier recall component is a separate build"),
    }
    if baseline_ok and falsification_proven:
        verdict, exit_code = "BENCHMARK_VALID_NO_FALSIFICATION", 0
        reason = ("real cached OpenCaseLaw input builds a source-linked, duplicate-free, "
                  "geometry-stable bundle for every frozen question and both regressed "
                  "inputs are rejected")
    elif not baseline_ok:
        verdict, exit_code = "BUNDLE_CONTRACT_VIOLATED", 1
        reason = "at least one harness check is false on the bundle built from real cached input"
    else:
        verdict, exit_code = "ENVIRONMENT_OR_VACUOUS", 2
        reason = "a falsification leg did NOT fire - the checks are vacuous on this input"

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": verdict,
        "exit_code": exit_code,
        "reason": reason,
        "falsification_proven": falsification_proven,
        "producer": "evaluation/query_map/bundle_producer.py",
        "evaluator": "evaluation/query_map/harness.py (ACCEPTED, unmodified)",
        "frozen_spec": {
            "path": str(spec_path.relative_to(_REPO_ROOT)),
            "sha256_before": spec_sha_before,
            "sha256_after": sha256_file(spec_path),
        },
        "cache": {"path": str(cache_dir.relative_to(_REPO_ROOT)),
                  "n_envelopes": len(envelopes),
                  "n_indexed_for_frozen_queries": len(index)},
        "n_questions": len(per_question),
        "counter_authority_yield": counter_yield,
        "questions": per_question,
        "claim_ceiling": (
            "This benchmark proves only that REAL cached OpenCaseLaw rows carry the fields "
            "the query_result_bundle contract needs (decision_id, canonical_url on "
            "mcp.opencaselaw.ch, language, citation strings, statutes, a frozen-marker-rule "
            "text surface) and that the ACCEPTED harness rejects a regressed bundle. It does "
            "NOT prove that Product builds such a bundle, that the map is useful to a jurist, "
            "that counter labels are calibrated (counter_uncertainty is a fixed fixture "
            "constant), that the coordinates are a good layout (they are a deterministic "
            "fixture layout, not a geometry claim), or anything about the absolute "
            "LABEL_SOUND / GEOMETRY_SOUND bars. Recall figures are measured, not thresholded."),
        "elapsed_s": round(time.time() - t0, 3),
    }
    spec_sha_after = record["frozen_spec"]["sha256_after"]
    if spec_sha_after != spec_sha_before:
        record["verdict"] = "ENVIRONMENT_OR_VACUOUS"
        record["exit_code"] = 2
        record["reason"] = "the frozen spec changed during execution"

    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for slug_dir in ("bundles",):
        d = out_dir / slug_dir
        d.mkdir(exist_ok=True)
        for q in per_question:
            (d / f"{run_id}_{q['slug']}.initial.json").write_text(
                json.dumps(q["bundle_initial"], indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            (d / f"{run_id}_{q['slug']}.final.json").write_text(
                json.dumps(q["bundle_final"], indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")

    lines = [
        f"# Query-map cached-bundle falsification benchmark — run {run_id}", "",
        f"- Schema: `{SCHEMA}`",
        f"- Verdict: **{verdict}** (exit {exit_code})",
        f"- Falsification proven: **{falsification_proven}**",
        f"- Frozen spec: `{record['frozen_spec']['path']}` sha256 "
        f"`{spec_sha_before[:16]}…` (re-hashed before and after execution, unchanged)",
        f"- Cache: {record['cache']['n_envelopes']} raw OpenCaseLaw envelopes, "
        f"{record['cache']['n_indexed_for_frozen_queries']} matched to frozen query text", "",
        "## Per-question results", "",
        "| question | decisions | clusters | counter candidates | dup suppressed | leg1 | leg2 fires | leg3 fires |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for q in per_question:
        m = q["producer_meta"]
        lines.append(
            f"| {q['slug']} | {m['n_decisions']} | {m['n_clusters']} | "
            f"{m['n_counter_candidates']} | {m['n_duplicates_suppressed']} | "
            f"{'PASS' if q['leg1_producer_baseline']['pass'] else 'FAIL'} | "
            f"{q['leg2_falsification_blanked_counter_evidence']['fired']} | "
            f"{q['leg3_falsification_broken_source_url']['fired']} |")
    lines += ["", "## Counter-authority yield (NEGATIVE RESULT)", "",
              counter_yield["finding"], "",
              f"- per-question candidate counts: `{json.dumps(counter_yield['per_question'])}`",
              f"- not claimed: {counter_yield['not_claimed']}", ""]
    lines += ["", "## Recall (measured, NOT thresholded)", "",
              "| question | known relevant | known counter reach | counter ids also labelled |",
              "|---|---|---|---|"]
    for q in per_question:
        r = q["recall_measured_not_thresholded"]
        kr, kc = r["known_relevant"], r["known_counter_reach"]
        kr_rec = "n/a" if kr["recall"] is None else f"{kr['recall']:.3f}"
        kc_rec = "n/a" if kc["recall"] is None else f"{kc['recall']:.3f}"
        lines.append(
            f"| {q['slug']} | {kr['found']}/{kr['expected']} ({kr_rec}) "
            f"| {kc['found']}/{kc['expected']} ({kc_rec}) "
            f"| {r['n_known_counter_ids_labelled']}/{kc['expected']} |")
    lines += ["", "## Reason", "", reason, "", "## Claim ceiling", "",
              record["claim_ceiling"], "",
              f"Machine record: `{(out_dir / f'{run_id}.json')}`", ""]
    (report_dir / f"QUERY_MAP_CACHED_BUNDLE_{run_id}.md").write_text(
        "\n".join(lines), encoding="utf-8")

    return exit_code, record


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-dir", default=None,
                    help="scratch runs MUST override this")
    ap.add_argument("--report-dir", default=None,
                    help="scratch runs MUST override this")
    ap.add_argument("--spec", default=str(DEFAULT_SPEC))
    ap.add_argument("--cache", default=str(DEFAULT_CACHE))
    args = ap.parse_args(argv)
    run_id = args.run_id or __import__("os").environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR
    code, record = run_benchmark(run_id, out_dir, report_dir,
                                 Path(args.spec), Path(args.cache))
    print(json.dumps({
        "verdict": record.get("verdict"), "exit_code": code,
        "falsification_proven": record.get("falsification_proven"),
        "n_questions": record.get("n_questions"),
        "questions": [
            {"slug": q["slug"],
             "leg1_pass": q["leg1_producer_baseline"]["pass"],
             "leg2_fired": q["leg2_falsification_blanked_counter_evidence"]["fired"],
             "leg3_fired": q["leg3_falsification_broken_source_url"]["fired"],
             "known_relevant": f"{q['recall_measured_not_thresholded']['known_relevant']['found']}"
                               f"/{q['recall_measured_not_thresholded']['known_relevant']['expected']}",
             "known_counter_reach": f"{q['recall_measured_not_thresholded']['known_counter_reach']['found']}"
                                    f"/{q['recall_measured_not_thresholded']['known_counter_reach']['expected']}"}
            for q in record.get("questions", [])],
        "reason": record.get("reason"),
    }, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())