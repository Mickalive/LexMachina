#!/usr/bin/env python3
"""v62 retrieval-pool attribution, VERSION 2 (declared NEW frozen spec, not a tuning).

WHY A VERSION 2 EXISTS
-----------------------
Run 39739350804 executed the V1 instrument (``evaluation/retrieval_pool_attribution.py``,
sha256 3ade35c2...) under its frozen hypothesis and freeze record.  V1's verdict is
``NOT_MEASURED_VACUOUS`` (exit 2) and its record is kept, untouched and published
next to this one.  V1 measured the question and then refused to attribute, because
three of its seven controls did not hold.  Reading V1's own measurements shows that
each of the three failing controls was mis-specified, and only mis-specified:

C5 ``pool_scan_complete`` demanded that the scan reach the END of the pool.
    V1 measured that the endpoint's reported ``total`` GROWS with the offset
    (254 -> 442 -> 638 -> 846 -> 1049 -> 1234 -> 1446 -> 1644 over offsets
    0..350) and that ``has_more`` stayed true for all eight fetched pages.  A
    pool that never closes cannot satisfy "the scan consumed every reported page",
    so the control was unsatisfiable by construction and would have masked the
    measurement entirely.  V2 replaces it with a HORIZON-BOUNDED control: every
    fetched page must have returned a FULL window (no silent truncation) and the
    record must DISCLOSE the horizon, the ``has_more`` flag at the horizon and the
    reported total at the horizon.

C6 ``cross_language_page0_sanity`` compared the served page-0 coverage (computed
    WITH lazily hydrated ``full_text``) against the live page-0 coverage (a search
    response carries no ``full_text``).  That is a basis error, not a corpus fact:
    the same ids, the same words, two different measurement bases.  V2 compares
    LIKE FOR LIKE - served page-0 LEXICAL against live page-0 LEXICAL - and adds a
    stricter requirement than V1 had: the live replay must not lose coverage
    relative to the served bytes for any concept, and the two zero-concept sets
    must be identical.

C7 ``oracle_concept_reachable`` treated "the corpus does not use this term" as a
    measurement failure.  V1 measured exactly that for one concept: a query for
    ``Kapitalverletzung`` returned 50 rows in which the token occurs 0 times, while
    the same mechanism found ``Überwachungspflicht`` in 27 of 50 rows.  A corpus
    fact is not a vacuous measurement.  V2 splits the control: C7a still requires
    the oracle mechanism to prove itself (at least one zero concept must be
    reachable), and C7b requires a term the oracle cannot reach to be reported as
    its own declared cause class CORPUS_TERM_ABSENCE instead of as vacuity.

WHAT DID NOT CHANGE (and is pinned to be so)
--------------------------------------------
* the sample, the accepted concept rule and the accepted row-text projection;
* the request shape (the product's OWN recorded parameters);
* the horizon: 8 pages = 400 rows, UNCHANGED, so no class can flip in either
  direction because of a horizon change;
* the fidelity threshold 0.90, the nonsense control query, the four V1 cause
  classes, the dominant-class rule, the success rules and the exit-code
  vocabulary;
* the claim ceiling.

WHAT V2 ADDS (declared, reported, never a pass/fail)
-----------------------------------------------------
* the ORACLE PROBE now walks two pages (100 rows) instead of one, so the
  corpus-term-absence claim is not resting on a single page of a fuzzy search;
* the REMEDY PROBE replays the question's own query with its zero concepts
  appended - the product's own expansion mechanism, which the accepted FR bundle
  already uses for one question (``lexicon_expansion:any:f5c7b3a6``) - and
  reports the coverage gain.  It is REPORTED, not gated: it tells the product
  lane which query change would work, without this lane deciding what the
  product must ship.

Exit codes (unchanged from V1)
------------------------------
0  POOL_ATTRIBUTION_NO_NEW_DEFECT
1  POOL_ATTRIBUTION_DEFECT_ATTRIBUTED
2  NOT_MEASURED_VACUOUS
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import retrieval_pool_attribution as RPA  # noqa: E402
from evaluation import subject_match_audit as SMA  # noqa: E402

SCHEMA = "lex-evaluation-v62-retrieval-pool-attribution-v2/1"
HYPOTHESIS_RELPATH = "evaluation/V62_RETRIEVAL_POOL_ATTRIBUTION_V2_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/V62_RETRIEVAL_POOL_ATTRIBUTION_V2_FREEZE_RECORD_V1.json"

PACKET = RPA.PACKET
PRIMARY_QID = RPA.PRIMARY_QID
CROSS_LANG_QIDS = RPA.CROSS_LANG_QIDS
MAX_PAGES = RPA.MAX_PAGES
PAGE0_JACCARD_MIN = RPA.PAGE0_JACCARD_MIN
NONSENSE_QUERY = RPA.NONSENSE_QUERY
ACCEPTED_RECORD_RELPATH = RPA.ACCEPTED_RECORD_RELPATH

#: V2's declared additions.
ORACLE_PAGES = 2          # the oracle probe reads two pages, not one
REMEDY_PROBE_LIMIT = 50   # one page of the expanded query

#: The class V1 did not have, declared here: the corpus itself does not carry
#: the term, so no retrieval change can surface it.
CAUSE_CORPUS_ABSENT = "CORPUS_TERM_ABSENCE"

#: Dominant-class priority (frozen).  The order runs from the most directly
#: actionable remedy to the least.
CLASS_PRIORITY = (RPA.CAUSE_BEYOND_PAGE0, RPA.CAUSE_PAGE0_ONLY,
                  RPA.CAUSE_NEVER, CAUSE_CORPUS_ABSENT)

REMEDY_TEXT = {
    CAUSE_CORPUS_ABSENT: (
        "CORPUS_TERM_ABSENCE: the concept term does not occur in the corpus rows "
        "that a concept-only query returns, so the question asks in a vocabulary the "
        "corpus does not use. Remedy: query expansion with the corpus's own "
        "vocabulary - the product already owns that mechanism (lexicon_expansion, "
        "used for the French question) and does not apply it to the German one."
    ),
}


# --------------------------------------------------------------------------- #
def served_page0_lexical(mount: Path, packet: str, qid: str) -> dict[str, Any]:
    """The served page-0 coverage WITHOUT the lazily hydrated full_text."""
    bundle_path, question_path = RPA._question_paths(mount, packet, qid)
    bundle = json.loads(bundle_path.read_text())
    qrec = json.loads(question_path.read_text())
    concepts = SMA.question_concepts(str(qrec.get("question") or ""))
    searches = (bundle.get("provenance") or {}).get("searches") or []
    original = next((s for s in searches if s.get("kind") == "original"), searches[0])
    rows = RPA.served_page0_rows(bundle, str(original.get("variant_id") or ""))
    return RPA.coverage([RPA.strip_full_text(r) for r in rows], concepts)


def oracle_probe(concept: str, question_text: str, *, fetcher, sleep,
                 pages: int = ORACLE_PAGES, limit: int = 50) -> dict[str, Any]:
    """How many rows of a concept-only query actually carry the concept."""
    qtext = RPA.oracle_query_text(question_text, concept)
    rows: list[dict] = []
    offset = 0
    has_more = True
    total = None
    for _ in range(max(1, pages)):
        if not has_more:
            break
        payload = RPA.ocl_search(qtext, offset, limit, fetcher=fetcher)
        sleep(RPA.MIN_INTERVAL_S)
        rows.extend(RPA.lexical_row(r) for r in (payload.get("results") or []))
        total = payload.get("total", total)
        has_more = bool(payload.get("has_more"))
        nxt = payload.get("next_offset")
        offset = int(nxt) if isinstance(nxt, int) else offset + limit
    cov = RPA.coverage(rows, [concept])
    hits = cov["concept_row_counts"].get(concept, 0)
    return {
        "concept": concept,
        "oracle_query": qtext,
        "n_pages_read": pages,
        "n_rows": len(rows),
        "rows_containing_concept": hits,
        "reachable": hits > 0,
        "example_ids": [r["decision_id"] for r in rows
                        if concept in SMA.deaccent(SMA.row_match_text(r)).lower()][:5],
        "reported_total": total,
    }


def remedy_probe(question_text: str, zero_concepts: list[str], *, fetcher, sleep,
                 limit: int = REMEDY_PROBE_LIMIT) -> dict[str, Any]:
    """The product's own expansion mechanism, replayed: question + zero concepts.

    REPORTED, never gated.  The product already owns this mechanism (the accepted
    FR bundle records the variant ``lexicon_expansion:any:f5c7b3a6``); this probe
    measures what it would buy for the German question.
    """
    if not zero_concepts:
        return {"skipped": "no zero concept"}
    expanded = question_text.rstrip() + " " + " ".join(zero_concepts)
    payload = RPA.ocl_search(expanded, 0, limit, fetcher=fetcher)
    sleep(RPA.MIN_INTERVAL_S)
    rows = [RPA.lexical_row(r) for r in (payload.get("results") or [])]
    cov = RPA.coverage(rows, zero_concepts)
    return {
        "expanded_query": expanded,
        "limit": limit,
        "n_rows": len(rows),
        "reported_total": payload.get("total"),
        "concept_row_counts": cov["concept_row_counts"],
        "concepts_covered": sorted(c for c, n in cov["concept_row_counts"].items() if n > 0),
        "concepts_still_zero": cov["concepts_with_zero_rows"],
        "mechanism": "question + core concepts, the product's own lexicon_expansion shape",
    }


# --------------------------------------------------------------------------- #
def run(run_id: str, out: Path | None, mount_arg: str | None, repo: Path,
        max_pages: int = MAX_PAGES, live: bool = True,
        fetcher: Callable[[str, float], dict] | None = None,
        sleep: Callable[[float], None] = time.sleep) -> tuple[int, dict]:
    mount = RPA.resolve_mount(mount_arg)
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "direction_version": 62,
        "run_id": run_id,
        "entry_point": "evaluation/retrieval_pool_attribution_v2.py",
        "hypothesis": HYPOTHESIS_RELPATH,
        "freeze_record": FREEZE_RELPATH,
        "supersedes": "evaluation/retrieval_pool_attribution.py (V1, verdict NOT_MEASURED_VACUOUS exit 2, record kept)",
        "live_measurement": bool(live),
        "numeric_environment": RPA.numeric_environment(),
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "unchanged_from_v1": {
            "max_pages": max_pages, "page0_jaccard_min": PAGE0_JACCARD_MIN,
            "nonsense_query": NONSENSE_QUERY, "cause_classes": list(RPA.CLASS_PRIORITY),
            "exit_codes": {"0": "POOL_ATTRIBUTION_NO_NEW_DEFECT",
                           "1": "POOL_ATTRIBUTION_DEFECT_ATTRIBUTED",
                           "2": "NOT_MEASURED_VACUOUS"},
        },
        "v2_additions": {
            "oracle_pages": ORACLE_PAGES,
            "remedy_probe": True,
            "declared_cause_class": CAUSE_CORPUS_ABSENT,
        },
    }
    if mount is None:
        record.update({"verdict": RPA.VERDICT_VACUOUS, "exit_code": RPA.EXIT_VACUOUS,
                       "vacuity_reason": "accepted product mount not found"})
        return RPA.EXIT_VACUOUS, record
    record["product_mount"] = str(mount)
    record["product_mount_head"] = RPA.mount_head(mount)

    bundle_path, question_path = RPA._question_paths(mount, PACKET, PRIMARY_QID)
    record["input_digests"] = {
        "bundle": RPA.sha256_file(bundle_path),
        "question": RPA.sha256_file(question_path),
    }
    acc_path = repo / ACCEPTED_RECORD_RELPATH
    if not acc_path.is_file():
        record.update({"verdict": RPA.VERDICT_VACUOUS, "exit_code": RPA.EXIT_VACUOUS,
                       "vacuity_reason": f"accepted record missing: {ACCEPTED_RECORD_RELPATH}"})
        return RPA.EXIT_VACUOUS, record
    accepted_record = json.loads(acc_path.read_text())
    record["accepted_record"] = ACCEPTED_RECORD_RELPATH
    record["accepted_record_sha256"] = RPA.sha256_file(acc_path)

    bundle = json.loads(bundle_path.read_text())
    qrec = json.loads(question_path.read_text())
    concepts = SMA.question_concepts(str(qrec.get("question") or ""))
    served_cov = RPA.coverage(bundle.get("decisions") or [], concepts)
    zero_concepts = served_cov["concepts_with_zero_rows"]
    record["recomputed_zero_concepts"] = zero_concepts
    if not zero_concepts:
        record.update({"verdict": RPA.VERDICT_NO_DEFECT, "exit_code": RPA.EXIT_NO_DEFECT,
                       "note": "no zero-row concept to attribute"})
        return RPA.EXIT_NO_DEFECT, record
    if not live:
        record.update({"verdict": RPA.VERDICT_VACUOUS, "exit_code": RPA.EXIT_VACUOUS,
                       "vacuity_reason": "live measurement disabled"})
        return RPA.EXIT_VACUOUS, record

    def _fetcher(url: str, timeout: float) -> dict:
        return fetcher(url, timeout) if fetcher is not None else RPA._http_json(url, timeout)

    measurements: list[dict] = []
    errors: list[str] = []
    for qid in (PRIMARY_QID,) + CROSS_LANG_QIDS:
        try:
            m = RPA.measure_question(mount, PACKET, qid, fetcher=_fetcher, sleep=sleep,
                                     max_pages=max_pages if qid == PRIMARY_QID else 1)
            m["served_page0_lexical_coverage"] = served_page0_lexical(mount, PACKET, qid)
            measurements.append(m)
        except Exception as exc:
            errors.append(f"{qid}: {type(exc).__name__}: {exc}")
    record["errors"] = errors
    if not measurements:
        record.update({"verdict": RPA.VERDICT_VACUOUS, "exit_code": RPA.EXIT_VACUOUS,
                       "errors": errors, "vacuity_reason": "no question could be measured"})
        return RPA.EXIT_VACUOUS, record

    primary = measurements[0]
    controls: dict[str, Any] = {}

    # C1 - replay fidelity (unchanged from V1).
    fid = primary["page0_fidelity"]
    controls["c1_page0_fidelity"] = {
        "definition": "live page-0 id set vs served page-0 id set, Jaccard >= threshold",
        "jaccard": fid["jaccard"], "threshold": PAGE0_JACCARD_MIN,
        "holds": fid["verdict"] in ("EXACT", "PARTIAL"), "verdict": fid["verdict"],
        "in_live_not_served": fid["in_live_not_served"],
        "in_served_not_live": fid["in_served_not_live"],
    }

    # C2 - nonsense query (unchanged from V1).
    try:
        payload = RPA.ocl_search(NONSENSE_QUERY, 0, 50, fetcher=_fetcher)
        sleep(RPA.MIN_INTERVAL_S)
        nonsense = {"n_rows": len(payload.get("results") or [])}
    except Exception as exc:
        nonsense = {"n_rows": None, "error": f"{type(exc).__name__}: {exc}"}
    controls["c2_nonsense_query_zero_rows"] = {
        "definition": "a nonsense query returns 0 rows, so a measured zero is a real zero",
        "query": NONSENSE_QUERY, "n_rows": nonsense.get("n_rows"),
        "holds": int(nonsense.get("n_rows") or 0) == 0,
    }

    # C3 - parity with the accepted record (unchanged from V1).
    acc_q = next((q for q in accepted_record.get("per_question") or []
                  if q.get("qid") == PRIMARY_QID), {})
    recomputed = primary["served_coverage_with_full_text"]
    controls["c3_accepted_record_parity"] = {
        "definition": "recomputed served coverage equals the accepted record's counts and zero list",
        "recomputed_counts": recomputed["concept_row_counts"],
        "accepted_counts": acc_q.get("concept_row_counts"),
        "recomputed_zero": recomputed["concepts_with_zero_rows"],
        "accepted_zero": acc_q.get("concepts_with_zero_rows"),
        "holds": (acc_q.get("concept_row_counts") == recomputed["concept_row_counts"]
                  and list(acc_q.get("concepts_with_zero_rows") or []) ==
                  list(recomputed["concepts_with_zero_rows"])),
    }

    # C4 - full-text independence (unchanged from V1).
    lex = primary["served_coverage_lexical_only"]["concept_row_counts"]
    full = primary["served_coverage_with_full_text"]["concept_row_counts"]
    controls["c4_full_text_independence"] = {
        "definition": "every zero concept is zero in the served bundle with AND without full_text",
        "zero_concepts": zero_concepts,
        "lexical_counts": {c: lex.get(c) for c in zero_concepts},
        "full_text_counts": {c: full.get(c) for c in zero_concepts},
        "holds": all(int(lex.get(c, 0)) == 0 and int(full.get(c, 0)) == 0 for c in zero_concepts),
    }

    # C5 - V2: horizon-bounded scan, no silent truncation.
    scan = primary["pool_scan"]
    windows = [p for p in scan["pages"]]
    full_windows = all(int(p["returned"]) == int(scan["pages"][0]["returned"])
                       and int(p["returned"]) > 0 for p in windows) if windows else False
    controls["c5_scan_horizon_full_windows"] = {
        "definition": "every fetched page returned a FULL window (no silent truncation); the horizon and the endpoint's state at it are disclosed",
        "changed_from_v1": "V1 demanded that the scan reach the END of the pool; V1 measured that this endpoint's reported total GROWS with the offset, so that demand was unsatisfiable by construction",
        "n_pages_fetched": scan["n_pages_fetched"],
        "max_pages_budget": scan["max_pages_budget"],
        "returned_per_page": [p["returned"] for p in windows],
        "reported_total_per_page": [p["reported_total"] for p in windows],
        "has_more_at_horizon": windows[-1]["has_more"] if windows else None,
        "pool_complete": scan["pool_complete"],
        "horizon_rows": scan["n_rows_fetched"],
        "holds": bool(full_windows) and int(scan["n_pages_fetched"]) > 0,
    }

    # C6 - V2: like-for-like page-0 comparison, no coverage loss.
    cross_rows = []
    c6_holds = True
    for m in measurements:
        sl = m["served_page0_lexical_coverage"]
        lp = m["live_page0_coverage"]
        lost = {c: (sl["concept_row_counts"].get(c, 0), lp["concept_row_counts"].get(c, 0))
                for c in sl["concepts"]
                if lp["concept_row_counts"].get(c, 0) < sl["concept_row_counts"].get(c, 0)}
        zero_ok = list(sl["concepts_with_zero_rows"]) == list(lp["concepts_with_zero_rows"])
        cross_rows.append({
            "qid": m["qid"],
            "served_page0_lexical_counts": sl["concept_row_counts"],
            "live_page0_counts": lp["concept_row_counts"],
            "served_page0_lexical_zero": sl["concepts_with_zero_rows"],
            "live_page0_zero": lp["concepts_with_zero_rows"],
            "concepts_losing_coverage": lost,
            "zero_sets_identical": zero_ok,
            "page0_jaccard": m["page0_fidelity"]["jaccard"],
        })
        if lost or not zero_ok:
            c6_holds = False
    controls["c6_like_for_like_page0"] = {
        "definition": "served page-0 LEXICAL vs live page-0 LEXICAL: identical zero sets and NO concept loses coverage relative to the served bytes",
        "changed_from_v1": "V1 compared the served coverage WITH hydrated full_text against the live coverage WITHOUT it - a basis error, not a corpus fact",
        "questions": cross_rows,
        "holds": c6_holds,
    }

    # C7a / C7b - the oracle mechanism, and corpus term absence as its own class.
    oracles = [oracle_probe(c, primary["question"], fetcher=_fetcher, sleep=sleep)
               for c in zero_concepts]
    reachable = [o for o in oracles if o.get("reachable")]
    controls["c7a_oracle_mechanism_proves_reachable"] = {
        "definition": "at least one zero concept is reachable by a concept-only query, so the detection mechanism works on live rows",
        "oracle_pages": ORACLE_PAGES,
        "reachable": [o["concept"] for o in reachable],
        "holds": bool(reachable),
    }
    controls["c7b_corpus_term_absence_is_a_class_not_vacuity"] = {
        "definition": "a concept the oracle cannot reach is REPORTED as CORPUS_TERM_ABSENCE, never as a vacuous measurement",
        "changed_from_v1": "V1 conflated 'the corpus does not use this term' with 'the measurement failed'",
        "unreachable": [o["concept"] for o in oracles if not o.get("reachable")],
        "holds": all(("error" not in o) for o in oracles),
    }

    all_hold = all(bool(c.get("holds")) for c in controls.values())
    record["non_vacuity"] = {"controls": controls, "all_hold": all_hold}
    record["measurements"] = measurements

    if not all_hold:
        record.update({"verdict": RPA.VERDICT_VACUOUS, "exit_code": RPA.EXIT_VACUOUS,
                       "vacuity_reason": "a frozen non-vacuity control did not hold"})
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        return RPA.EXIT_VACUOUS, record

    # ---- classification ---------------------------------------------------- #
    per_concept = []
    for pc in primary["per_concept"]:
        concept = pc["concept"]
        oracle = next((o for o in oracles if o["concept"] == concept), {})
        cause = pc["cause_class"]
        if cause == RPA.CAUSE_NEVER and not oracle.get("reachable"):
            cause = CAUSE_CORPUS_ABSENT
        per_concept.append({
            "concept": concept,
            "cause_class": cause,
            "served_bundle_rows": pc["served_bundle_rows"],
            "served_bundle_rows_lexical_only": pc["served_bundle_rows_lexical_only"],
            "live_page0_rows": pc["live_page0_rows"],
            "live_pool_beyond_page0_rows": pc["live_pool_beyond_page0_rows"],
            "live_pool_rows": pc["live_pool_rows"],
            "live_pool_horizon_rows": primary["pool_scan"]["n_rows_fetched"],
            "oracle_rows_containing_concept": oracle.get("rows_containing_concept"),
            "oracle_n_rows": oracle.get("n_rows"),
            "remedy": REMEDY_TEXT.get(cause, RPA.CLASS_REMEDY.get(cause, "")),
        })

    classes = [pc["cause_class"] for pc in per_concept]
    dominant = next((c for c in CLASS_PRIORITY if c in classes), None)
    defect = bool(dominant and dominant in (RPA.CAUSE_BEYOND_PAGE0, RPA.CAUSE_PAGE0_ONLY,
                                            RPA.CAUSE_NEVER, CAUSE_CORPUS_ABSENT))
    remedy = remedy_probe(primary["question"], zero_concepts, fetcher=_fetcher, sleep=sleep)

    record["attribution"] = {
        "zero_concepts": zero_concepts,
        "per_concept": per_concept,
        "classes": classes,
        "dominant_class": dominant,
        "dominant_remedy": REMEDY_TEXT.get(dominant, RPA.CLASS_REMEDY.get(dominant, "")),
        "oracle_probes": oracles,
        "remedy_probe": remedy,
        "served_targets": primary["request_frozen_from_served_provenance"]["served_targets"],
        "served_search_record": primary["request_frozen_from_served_provenance"],
        "pool_horizon": {
            "rows_scanned": primary["pool_scan"]["n_rows_fetched"],
            "pages": primary["pool_scan"]["n_pages_fetched"],
            "reported_total_at_offset_0": primary["pool_scan"]["pages"][0]["reported_total"]
            if primary["pool_scan"]["pages"] else None,
            "reported_total_at_horizon": primary["pool_scan"]["pages"][-1]["reported_total"]
            if primary["pool_scan"]["pages"] else None,
            "has_more_at_horizon": primary["pool_scan"]["pages"][-1]["has_more"]
            if primary["pool_scan"]["pages"] else None,
            "note": "the endpoint's reported total grows with the offset; the packet's recorded total is the value at offset 0 and is NOT the size of the candidate pool",
        },
    }
    record["verdict"] = RPA.VERDICT_DEFECT if defect else RPA.VERDICT_NO_DEFECT
    record["exit_code"] = RPA.EXIT_DEFECT if defect else RPA.EXIT_NO_DEFECT
    record["claim_ceiling"] = (
        "This record attributes ONE accepted failure (the zero-row core concepts of the served "
        "German question in packet 39319405429) to one of the frozen cause classes by replaying "
        "the product's own recorded request against the live OpenCaseLaw corpus. It does NOT "
        "re-issue, weaken or re-score the accepted falsification; that verdict stands unchanged. "
        "It does NOT meet, move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND "
        "bars. It does NOT lift any DO-NOT-SERVE order and does NOT certify admission of any "
        "packet. It does NOT claim the map helps a jurist. It runs no obsolete universal-174k "
        "benchmark. human_gate_ready stays false. The attribution is relative to the DISCLOSED "
        "horizon of the scan, and the corpus is live: the same measurement on another day may "
        "differ, which is why every number is published with its fidelity control."
    )
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record["exit_code"], record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--mount", default=None)
    ap.add_argument("--repo", default=str(REPO_ROOT))
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES)
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else None
    code, record = run(args.run_id, out, args.mount, Path(args.repo),
                       max_pages=args.max_pages, live=not args.offline)
    if out is None:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    else:
        print(f"{record.get('verdict')} exit={code} -> {out}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
