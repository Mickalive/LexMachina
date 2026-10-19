#!/usr/bin/env python3
"""Does the product's stoplist-filtered concept extraction create a STRUCTURAL
BLIND SPOT in the ``query_concepts_under_covered`` disclosure?

Why this exists
---------------
The accepted frontier recall handoff (consumed by delivered cycle 39180276526,
verdict ``DIVERGENCE_HEADLINE``) established that the product-side
``content_concepts`` returns a strict subset or near-subset of this lane's
mapping-free ``question_concepts`` on all three served questions, because the
product's ``STOPWORDS`` list filters legal-sounding tokens (``begrenzen``,
``blossen``, ``resiliation``, ``jusqu``, ``quale``, ``devono``, ``essere``,
``dimostrati``, ``escludono``) that the eval-side instrument retains as core
concepts.  On today's served bundles every filtered-out concept happens to
carry >=1 supporting row, so the under-covered SETS still match and the ordered
``query_concepts_under_covered`` warning (accepted handoff
``question_native_coverage_39113690481``, consumed by accepted cycle
39177046762) fires correctly on the concepts it measures.

The open falsification question is whether that divergence is MATERIAL: does
the product's stoplist create a structural blind spot in which a core legal
concept of the question has zero supporting rows and the product's disclosure
can NEVER name it, because ``content_concepts`` never emits the token at all?

Legs (all frozen in CONCEPT_EXTRACTION_BLINDSPOT_HYPOTHESIS_V1.json)
-------------------------------------------------------------------
A  extraction divergence   product_concepts vs eval_concepts, cell-by-cell
B  active blind spot       any filtered-out concept with row_count == 0 on the
                           served bundle
C  counterfactual          remove every row carrying the lowest-row-count
                           filtered-out concept; re-run the product's OWN
                           coverage_report; the blind spot is proven LATENT iff
                           the concept is absent from the product's under_covered
                           AND present as a zero-row concept under an eval-side
                           re-count of the same counterfactual rows
D  frozen inputs           every pinned sha256 re-hashed before measurement

Exit codes
    0  the instrument ran and wrote a record (a falsification is a RESULT)
    2  environment / pin error, nothing claim-bearing recorded

SCRATCH-RUN OBLIGATION: a non-claim-bearing invocation (unit test, local poke)
MUST pass --out and --report-dir; the defaults are the committed claim-bearing
trees and a scratch run that does not redirect becomes accepted evidence via
the workflow's ``git add -A`` persist step.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA = "lex-evaluation-concept-extraction-blindspot/1"
DEFAULT_HYPOTHESIS = (_REPO_ROOT / "evaluation"
                      / "CONCEPT_EXTRACTION_BLINDSPOT_HYPOTHESIS_V1.json")
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
PACKET = "results/product/gate_packet/rebuilt-39027045675"
SERVED_QIDS = ("de-kapitalverletzung", "fr-bail-entretien",
               "it-responsabilita-medica")

VERDICT_ACTIVE = "BLIND_SPOT_ACTIVE"
VERDICT_LATENT = "BLIND_SPOT_LATENT_COUNTERFACTUAL_PROVEN"
VERDICT_NONE = "NO_BLIND_SPOT"
VERDICT_ENV = "ENVIRONMENT"


def _utc_now() -> str:
    return (datetime.now(timezone.utc).replace(microsecond=0)
            .isoformat().replace("+00:00", "Z"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(value) -> str:
    """NFKD, strip combining marks, casefold, collapse whitespace.

    Byte-identical in behaviour to product/query/concept_coverage.py::norm and
    to the eval-side row matching used for QUESTION_NATIVE_COVERAGE.json.
    """
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())


def _load_product_concept_coverage(mount: Path):
    """Load product/query/concept_coverage.py by file path, bypassing the
    package __init__ (numpy is absent in this environment)."""
    path = mount / "product" / "query" / "concept_coverage.py"
    if not path.is_file():
        raise FileNotFoundError(f"product concept_coverage.py not found: {path}")
    spec = importlib.util.spec_from_file_location(
        "_lex_product_concept_coverage", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, path


def _eval_row_text(row: dict) -> str:
    """The same row fields QUESTION_NATIVE_COVERAGE.json used for matching."""
    return " ".join(
        str(row.get(k) or "")
        for k in ("title", "regeste", "snippet", "full_text", "citation",
                  "decision_id"))


def _eval_side_recount(concept: str, decisions: list[dict]) -> int:
    """Eval-side substring containment count (the accepted coverage record's
    own matching rule, re-applied to a possibly-modified decision list)."""
    c = _norm(concept)
    if not c:
        return 0
    n = 0
    for row in decisions:
        if c in _norm(_eval_row_text(row)):
            n += 1
    return n


def verify_inputs(hypothesis: dict) -> tuple[dict, list[str]]:
    """Re-hash every pinned input. Returns (resolved path map, problems)."""
    resolved: dict[str, Path] = {}
    problems: list[str] = []
    inputs = hypothesis.get("inputs") or {}
    for key, spec in inputs.items():
        if not isinstance(spec, dict):
            continue
        rel = spec.get("path")
        want = spec.get("sha256")
        if not rel:
            continue
        # product-side paths are absolute and mount-scoped
        p = Path(rel)
        if not p.is_absolute():
            p = _REPO_ROOT / rel
        # directory pins (served question/bundle dirs) are existence-checked,
        # file pins are existence- + digest-checked
        if p.is_dir():
            resolved[key] = p
            continue
        if not p.is_file():
            problems.append(f"{key}: missing {p}")
            continue
        resolved[key] = p
        if want:
            got = _sha256_file(p)
            if got != want:
                problems.append(
                    f"{key}: digest drift want={want[:16]} got={got[:16]}")
    # the product mount itself must exist
    if not PRODUCT_MOUNT.is_dir():
        problems.append(f"product mount absent: {PRODUCT_MOUNT}")
    return resolved, problems


def _load_question_text(qid: str) -> str:
    path = PRODUCT_MOUNT / PACKET / "questions" / f"{qid}.question.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    return str(rec.get("question") or "")


def _load_bundle_rows(qid: str) -> list[dict]:
    path = PRODUCT_MOUNT / PACKET / "questions" / f"{qid}.bundle.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    rows = rec.get("decisions") or rec.get("rows") or []
    return [r for r in rows if isinstance(r, dict)]


def run_legs(hypothesis: dict, product_mod) -> tuple[str, dict, list[str]]:
    """Execute legs A-D. Returns (verdict, detail, divergences)."""
    coverage_path = (hypothesis["inputs"]["question_native_coverage"]["path"])
    coverage = json.loads(
        (_REPO_ROOT / coverage_path).read_text(encoding="utf-8"))
    eval_qs = coverage.get("questions") or {}

    cells: list[dict] = []
    divergences: list[str] = []
    active_cells: list[dict] = []
    counterfactual_cells: list[dict] = []
    any_blind_spot = False
    any_counterfactual_proven = False

    for qid in SERVED_QIDS:
        qtext = _load_question_text(qid)
        product_concepts = list(product_mod.content_concepts(qtext))
        eval_entry = eval_qs.get(qid) or {}
        eval_concepts = list(eval_entry.get("concepts") or [])
        row_counts = dict(eval_entry.get("concept_row_counts") or {})

        filtered_out = [c for c in eval_concepts if c not in product_concepts]
        added = [c for c in product_concepts if c not in eval_concepts]

        cells.append({
            "question": qid,
            "product_concepts": product_concepts,
            "eval_concepts": eval_concepts,
            "filtered_out": filtered_out,
            "added": added,
            "n_product": len(product_concepts),
            "n_eval": len(eval_concepts),
        })
        if filtered_out:
            divergences.append(
                f"{qid}::filtered_out {filtered_out} (product "
                f"{len(product_concepts)} vs eval {len(eval_concepts)})")
        if added:
            divergences.append(
                f"{qid}::added {added} (product-only concepts)")

        # Leg B: any filtered-out concept with zero rows on the served bundle?
        zero_row_filtered = [
            c for c in filtered_out if int(row_counts.get(c, -1)) == 0]
        if zero_row_filtered:
            active_cells.append({
                "question": qid,
                "concepts": zero_row_filtered,
                "row_counts": {c: row_counts.get(c) for c in zero_row_filtered},
            })
            any_blind_spot = True
            divergences.append(
                f"{qid}::ACTIVE_BLIND_SPOT {zero_row_filtered} have 0 rows "
                "and are filtered out by the product stoplist")

        # Leg C: counterfactual on the lowest-row-count filtered-out concept
        if filtered_out and not zero_row_filtered:
            # pick the concept with the smallest positive row count
            candidates = sorted(
                filtered_out,
                key=lambda c: (int(row_counts.get(c, 10 ** 6)), c))
            target = candidates[0]
            rows = _load_bundle_rows(qid)
            kept = [r for r in rows
                    if _norm(target) not in _norm(_eval_row_text(r))]
            removed = len(rows) - len(kept)

            # product re-measures its OWN coverage on the counterfactual
            report = product_mod.coverage_report(qtext, kept)
            product_under = list(report.get("under_covered") or [])
            product_concepts_cf = list(report.get("concepts") or [])

            # eval-side re-count of the same counterfactual rows
            eval_count_cf = _eval_side_recount(target, kept)

            proven = (target not in product_concepts_cf
                      and target not in product_under
                      and eval_count_cf == 0)
            counterfactual_cells.append({
                "question": qid,
                "target_concept": target,
                "served_row_count": int(row_counts.get(target, -1)),
                "rows_removed": removed,
                "rows_kept": len(kept),
                "product_concepts_on_counterfactual": product_concepts_cf,
                "product_under_covered_on_counterfactual": product_under,
                "eval_side_count_on_counterfactual": eval_count_cf,
                "blind_spot_proven_on_cell": proven,
            })
            if proven:
                any_counterfactual_proven = True
                divergences.append(
                    f"{qid}::COUNTERFACTUAL_BLIND_SPOT target={target} "
                    f"removed={removed} rows; product never emits it, "
                    "eval-side re-count is 0")

    if any_blind_spot:
        verdict = VERDICT_ACTIVE
    elif any_counterfactual_proven:
        verdict = VERDICT_LATENT
    else:
        verdict = VERDICT_NONE

    detail = {
        "cells": cells,
        "active_blindspot_cells": active_cells,
        "counterfactual_cells": counterfactual_cells,
        "any_blind_spot_active": any_blind_spot,
        "counterfactual_proven": any_counterfactual_proven,
    }
    return verdict, detail, divergences


def run(run_id: str, hypothesis_path: Path) -> tuple[int, dict]:
    hypothesis = json.loads(hypothesis_path.read_text(encoding="utf-8"))
    resolved, problems = verify_inputs(hypothesis)

    if problems:
        record = {
            "schema": SCHEMA,
            "run_id": run_id,
            "direction_version": hypothesis.get("direction_version"),
            "generated_at_utc": _utc_now(),
            "hypothesis_path": str(hypothesis_path),
            "hypothesis_sha256": _sha256_file(hypothesis_path),
            "verdict": VERDICT_ENV,
            "headline": "; ".join(problems[:5]),
            "input_digest_problems": problems,
            "input_digests_verified": sorted(resolved),
            "human_gate_ready": False,
            "owner_decision_required": False,
        }
        return 2, record

    product_mod, product_path = _load_product_concept_coverage(PRODUCT_MOUNT)
    product_digest = _sha256_file(product_path)

    verdict, detail, divergences = run_legs(hypothesis, product_mod)

    headline = {
        VERDICT_ACTIVE: "the product's stoplist filters a core concept that "
                        "has ZERO supporting rows on served bytes - the "
                        "query_concepts_under_covered disclosure can never "
                        "name it",
        VERDICT_LATENT: "the product's stoplist filters core concepts that "
                        "today have >=1 row, but a minimal counterfactual "
                        "row-removal proves the disclosure stays silent while "
                        "an eval-side re-count flags the concept as zero-row",
        VERDICT_NONE: "no filtered-out concept is zero-row on served bytes "
                      "and no counterfactual cell proves a blind spot",
    }[verdict]

    n_filtered = sum(len(c["filtered_out"]) for c in detail["cells"])
    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": hypothesis.get("direction_version"),
        "generated_at_utc": _utc_now(),
        "hypothesis_path": str(hypothesis_path),
        "hypothesis_sha256": _sha256_file(hypothesis_path),
        "product_concept_coverage_sha256": product_digest,
        "input_digests_verified": sorted(resolved),
        "input_digest_problems": [],
        "verdict": verdict,
        "headline": headline,
        "falsification_proven": verdict in (VERDICT_ACTIVE, VERDICT_LATENT),
        "n_filtered_out_total": n_filtered,
        "divergences": divergences,
        **detail,
        "publishes_beside_frontier": (
            "the accepted DIVERGENCE_HEADLINE of delivered cycle 39180276526 "
            "(results/evaluation/frontier_recall_handoff/39180276526.json) is "
            "the naming of the concept-count divergence; this record is the "
            "MATERIALITY verdict on that divergence and never replaces it"
        ),
        "claim_ceiling": hypothesis.get("claim_ceiling"),
        "human_gate_ready": False,
        "owner_decision_required": False,
    }
    return 0, record


def _persist(record: dict, out_path: Path, report_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Concept-extraction blind-spot falsification - run {record['run_id']}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Verdict: **{record.get('verdict')}**",
        f"- Falsification proven: {record.get('falsification_proven')}",
        f"- Headline: {record.get('headline')}",
        "",
        "## Extraction divergence (leg A)",
        "",
        "| question | n_product | n_eval | filtered_out | added |",
        "|---|---|---|---|---|",
    ]
    for c in record.get("cells") or []:
        lines.append(
            f"| {c['question']} | {c['n_product']} | {c['n_eval']} | "
            f"{c['filtered_out']} | {c['added']} |")
    lines += ["", "## Active blind spot (leg B)", ""]
    active = record.get("active_blindspot_cells") or []
    if active:
        for a in active:
            lines.append(f"- **{a['question']}**: {a['concepts']} "
                         f"(row_counts {a['row_counts']})")
    else:
        lines.append("- none: every filtered-out concept has >=1 row on the "
                     "served bundle")
    lines += ["", "## Counterfactual (leg C)", ""]
    cf = record.get("counterfactual_cells") or []
    if cf:
        lines.append("| question | target | served_rows | removed | "
                     "product_under_covered | eval_count_cf | proven |")
        lines.append("|---|---|---|---|---|---|---|")
        for c in cf:
            lines.append(
                f"| {c['question']} | {c['target_concept']} | "
                f"{c['served_row_count']} | {c['rows_removed']} | "
                f"{c['product_under_covered_on_counterfactual']} | "
                f"{c['eval_side_count_on_counterfactual']} | "
                f"{c['blind_spot_proven_on_cell']} |")
    else:
        lines.append("- not applicable (no eligible cell)")
    lines += [
        "",
        "## Divergences (each is a headline, never smoothed)",
        "",
    ]
    lines += [f"- {d}" for d in record.get("divergences") or []] or ["- none"]
    lines += [
        "",
        "## Publishes beside the frontier handoff",
        "",
        str(record.get("publishes_beside_frontier")),
        "",
        "## Claim ceiling",
        "",
        str(record.get("claim_ceiling")),
        "",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--hypothesis", default=str(DEFAULT_HYPOTHESIS))
    ap.add_argument("--out", default=None)
    ap.add_argument("--report-dir", default=None)
    args = ap.parse_args(argv)
    out_path = (Path(args.out) if args.out else
                _REPO_ROOT / "results/evaluation/concept_extraction_blindspot"
                / f"{args.run_id}.json")
    report_dir = (Path(args.report_dir) if args.report_dir else
                  _REPO_ROOT / "reports/evaluation")
    report_path = report_dir / f"CONCEPT_EXTRACTION_BLINDSPOT_{args.run_id}.md"
    exit_code, record = run(args.run_id, Path(args.hypothesis))
    _persist(record, out_path, report_path)
    print(json.dumps({
        "verdict": record.get("verdict"),
        "headline": record.get("headline"),
        "falsification_proven": record.get("falsification_proven"),
        "n_divergences": len(record.get("divergences") or []),
        "exit_code": exit_code,
    }, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
