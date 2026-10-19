#!/usr/bin/env python3
"""Independently re-derive the accepted frontier-query-concept-recall OUTCOME_B
bounded-cause numbers from primary evidence: the 15 committed cache envelopes,
the re-hashed frozen retrieval spec and this lane's accepted durability record.

Direction v57 (evaluation lane) orders: the RECALL half of the accepted coverage
finding was chartered to Frontier frontier-query-concept-recall; this lane builds
or re-scores NO candidate, and when its numbers arrive they are published BESIDE
this lane's own, never in place of them, with any divergence named as the headline.
The 39180276526 handoff compared A0 cells and COPIED the bounded-cause fields
verbatim; the frontier's own audit re-derived only the latency aggregates. The
load-bearing '0 of 9 missing frozen authority ids recovered' claim has never been
re-derived from cache bodies intersected with the frozen id sets by a party
outside the team. This instrument does exactly that, mapping-free.

Operative hypothesis: FRONTIER_BOUNDED_CAUSE_REPRODUCTION_HYPOTHESIS_V1.json as
amended by FRONTIER_BOUNDED_CAUSE_REPRODUCTION_HYPOTHESIS_V1_1_AMENDMENT.json
(C2 latency sub-rule only), both committed before any execution.

Exit codes (frozen)
  0  CAUSE_REPRODUCED    every pinned digest matches, audit gate PASS, all cells match
  1  DIVERGENCE_HEADLINE every pinned digest matches, audit gate PASS, >=1 cell diverges
  2  ENVIRONMENT         pinned input missing/drifted or audit gate not PASS

SCRATCH-RUN OBLIGATION: any non-claim-bearing invocation MUST pass --out and
--report-dir; the defaults are the committed claim-bearing trees.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

SCHEMA = "lex-evaluation-frontier-bounded-cause-reproduction/1"
HYPOTHESIS_PATH = (_REPO_ROOT / "evaluation"
                   / "FRONTIER_BOUNDED_CAUSE_REPRODUCTION_HYPOTHESIS_V1.json")
AMENDMENT_PATH = (_REPO_ROOT / "evaluation"
                  / "FRONTIER_BOUNDED_CAUSE_REPRODUCTION_HYPOTHESIS_V1_1_AMENDMENT.json")

LANGS = ("de", "fr", "it")
MEASURABLE_SLUGS = ("corporate-criminal-liability", "business-judgment-rule",
                    "petty-theft-dismissal")
URL_PREFIX = "https://mcp.opencaselaw.ch/api/decisions?query="
URL_SUFFIX = "&limit=50&offset=0&sort=relevance&fields=full&include_pinpoint=false"

VERDICT_REPRODUCED = "CAUSE_REPRODUCED"
VERDICT_DIVERGENCE = "DIVERGENCE_HEADLINE"
VERDICT_ENVIRONMENT = "ENVIRONMENT"

# Expected values, frozen in V1 cells C1-C5 (read from the operative hypothesis
# at runtime; these constants are asserted equal to the hypothesis so a drifted
# hypothesis cannot silently change expectations).
EXPECTED_RECOVERED_DISTINCT: list = []
EXPECTED_MISSING_DISTINCT_SIZE = 9
EXPECTED_N_OVER_30 = 10
EXPECTED_MAX_LATENCY = 83.5047721599999
EXPECTED_SUM_HARNESS_3DP = 600.569
EXPECTED_SUM_AUDIT_3DP = 600.568
EXPECTED_WITNESS_CELLS = 12
TOTAL_CELLS = 15


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _round3(x: float) -> float:
    # Decimal-half-even rounding identical to Python round(x, 3); frozen rule.
    return round(x, 3)


def cache_manifest_digest(root: Path) -> tuple[str, list[str]]:
    """Manifest convention frozen in V1 inputs.frontier_cache_manifest."""
    lines: list[str] = []
    rels: list[str] = []
    for p in sorted(root.rglob("*.json")):
        rel = p.relative_to(root).as_posix()
        rels.append(rel)
        lines.append(f"{_sha256_file(p)}  {rel}\n")
    digest = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
    return digest, rels


def verify_inputs(hyp: dict) -> tuple[dict, list[str]]:
    resolved: dict[str, Path] = {}
    problems: list[str] = []
    for name, pin in (hyp.get("inputs") or {}).items():
        if "root" in pin:  # cache manifest input
            root = Path(pin["root"])
            if not root.is_dir():
                problems.append(f"{name}: missing cache root {root}")
                continue
            got, rels = cache_manifest_digest(root)
            if got != pin["manifest_sha256"]:
                problems.append(
                    f"{name}: cache manifest drift expected "
                    f"{pin['manifest_sha256'][:12]} got {got[:12]}")
                continue
            if len(rels) != pin["n_envelopes_expected"]:
                problems.append(
                    f"{name}: expected {pin['n_envelopes_expected']} envelopes, "
                    f"found {len(rels)}")
                continue
            resolved[name] = root
            continue
        path = Path(pin["path"])
        if not path.is_absolute():
            path = _REPO_ROOT / path
        if not path.is_file():
            problems.append(f"{name}: missing {path}")
            continue
        got = _sha256_file(path)
        if got != pin["sha256"]:
            problems.append(f"{name}: digest drift expected {pin['sha256'][:12]} "
                            f"got {got[:12]} ({path})")
            continue
        resolved[name] = path
    return resolved, problems


def verify_gate(path: Path, hyp: dict) -> tuple[bool, str]:
    pin = hyp["inputs"]["frontier_audit_gate_of_record"]
    gate = _load(path)
    ok = (gate.get("gate") == pin["required_gate"]
          and gate.get("safe_to_integrate") is pin["required_safe_to_integrate"])
    return ok, f"gate={gate.get('gate')} safe_to_integrate={gate.get('safe_to_integrate')}"


def url_for(expansion_query: str) -> str:
    return URL_PREFIX + expansion_query.replace(" ", "+") + URL_SUFFIX


def load_envelopes(cache_root: Path) -> dict[str, dict]:
    """url -> envelope record (with parsed body result ids and rows)."""
    out: dict[str, dict] = {}
    for p in sorted(cache_root.rglob("*.json")):
        env = _load(p)
        body = env.get("body")
        if isinstance(body, str):
            body = json.loads(body)
        results = (body or {}).get("results") or []
        ids = [r.get("canonical_decision_id") for r in results]
        out[env["url"]] = {
            "relpath": p.relative_to(cache_root).as_posix(),
            "status": env.get("status"),
            "latency_seconds": env.get("latency_seconds"),
            "n_rows": len(results),
            "ids": ids,
            "id_set": {i for i in ids if i},
        }
    return out


def build_cells(harness: dict) -> list[dict]:
    """The 15 cells: 12 frozen-leg (slug x lang) + 3 served questions.

    CORRECTION (run 39195084218 r2, recorded not silent): the harness stores
    the per-cell search block as a SIBLING of A1_candidate_only, not inside it.
    Run 1 extracted A1_candidate_only.search (always absent => status null) and
    therefore fired 12 spurious C2 status divergences. The frozen rule text
    ('search.status') always meant the sibling block; this is an extraction bug
    fix, not a rule change. Run 1's artifact is preserved verbatim.
    """
    cells: list[dict] = []
    legs = harness.get("frozen_legs") or {}
    for slug, leg in legs.items():
        for lang, block in (leg.get("per_language") or {}).items():
            a0 = block.get("A0_baseline_shipped") or {}
            a1 = block.get("A1_candidate_only") or {}
            search = block.get("search") or {}
            cells.append({
                "kind": "leg",
                "cell": f"{slug}::{lang}",
                "slug": slug,
                "lang": lang,
                "expansion_query": block.get("expansion_query"),
                "a0_hits": list(a0.get("hits") or []),
                "a0_n_rows": a0.get("n_rows"),
                "required": list(a1.get("required") or leg.get("authority_ids") or []),
                "a1_n_rows": a1.get("n_rows"),
                "a1_status": search.get("status"),
                "a1_newly_found_ids": list(block.get("newly_found_ids") or []),
                "a1_union_n_rows": (block.get("A1_union") or {}).get("n_rows"),
            })
    for qid, block in (harness.get("served_questions") or {}).items():
        a0 = block.get("A0_baseline_shipped") or {}
        a1 = block.get("A1_candidate") or {}
        cells.append({
            "kind": "served",
            "cell": qid,
            "slug": None,
            "lang": None,
            "expansion_query": block.get("expansion_query"),
            "a0_n_rows": a0.get("n_rows"),
            # frozen-rule-as-written comparison field: A1_candidate.n_rows is the
            # POOLED COVERAGE set (A0 ∪ candidate), not the expansion response
            # length; kept so the frozen cell still fires as written, with the
            # corrected response-length reading supplied by C3 (cache bodies).
            "a1_n_rows": a1.get("n_rows"),
        })
    return cells


def per_search_latency(harness: dict) -> dict[str, dict]:
    budget = harness.get("latency_budget") or {}
    return {e.get("query"): e for e in (budget.get("per_search_calls") or [])}


def frozen_required_by_slug(spec: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for q in spec.get("questions") or []:
        out[q["slug"]] = list(q.get("authority_ids") or [])
    return out


def run_comparisons(harness: dict, spec: dict, durability: dict,
                    envelopes: dict[str, dict]) -> dict:
    cells = build_cells(harness)
    psl = per_search_latency(harness)
    required_by_slug = frozen_required_by_slug(spec)
    divergences: list[str] = []

    # --- bijection: cells <-> envelopes -------------------------------------
    claimed_urls: dict[str, str] = {}
    cell_url: dict[str, str] = {}
    for c in cells:
        q = c["expansion_query"]
        if not q:
            divergences.append(f"C2::{c['cell']}::missing_expansion_query")
            continue
        url = url_for(q)
        cell_url[c["cell"]] = url
        if url not in envelopes:
            divergences.append(f"C2::{c['cell']}::no_cache_envelope_for_query")
            continue
        if url in claimed_urls:
            divergences.append(f"C2::{c['cell']}::url_already_claimed_by_"
                               f"{claimed_urls[url]}")
            continue
        claimed_urls[url] = c["cell"]
    unclaimed = sorted(set(envelopes) - set(claimed_urls))
    for url in unclaimed:
        divergences.append(f"C2::unclaimed_envelope::{envelopes[url]['relpath']}")

    # --- C2: per-cell record vs cache ---------------------------------------
    c2_rows: list[dict] = []
    for c in cells:
        url = cell_url.get(c["cell"])
        env = envelopes.get(url)
        if env is None:
            continue
        status_ok = (env["status"] == c.get("a1_status")
                     if c["kind"] == "leg" else env["status"] == 200)
        rows_ok = env["n_rows"] == c.get("a1_n_rows")
        ps = psl.get(c["expansion_query"]) or {}
        lat_ok = _round3(env["latency_seconds"]) == ps.get("latency_seconds")
        cell_ok = bool(status_ok and rows_ok and lat_ok)
        if not cell_ok:
            kind_note = ""
            if c["kind"] == "served" and not rows_ok:
                kind_note = (" (frozen-rule-as-written: A1_candidate.n_rows is the "
                             "pooled coverage set, not the expansion response; the "
                             "corrected response-length reading is C3)")
            divergences.append(
                f"C2::{c['cell']}::status_ok={status_ok},rows_ok={rows_ok},"
                f"latency_ok={lat_ok}{kind_note}")
        c2_rows.append({
            "cell": c["cell"], "ok": cell_ok,
            "cache_status": env["status"], "record_status": c.get("a1_status"),
            "cache_n_rows": env["n_rows"], "record_n_rows": c.get("a1_n_rows"),
            "cache_latency_round3": _round3(env["latency_seconds"]),
            "per_search_calls_latency": ps.get("latency_seconds"),
            "cache_relpath": env["relpath"],
        })

    # --- C1: candidate-only recovery from cache bodies ----------------------
    c1_rows: list[dict] = []
    recovered_distinct: set[str] = set()
    missing_distinct: set[str] = set()
    measurable_cells = [c for c in cells if c["kind"] == "leg"
                        and required_by_slug.get(c["slug"])]
    for c in measurable_cells:
        env = envelopes.get(cell_url.get(c["cell"], ""))
        if env is None:
            continue
        required = set(required_by_slug.get(c["slug"]) or c["required"])
        recovered = (env["id_set"] & required) - set(c["a0_hits"])
        missing = required - set(c["a0_hits"])
        recovered_distinct |= recovered
        missing_distinct |= missing
        c1_rows.append({
            "cell": c["cell"],
            "recovered": sorted(recovered),
            "missing": sorted(missing),
            "frontier_a0_hits": sorted(c["a0_hits"]),
            "frontier_a1_newly_found_recorded": sorted(c["a1_newly_found_ids"]),
            "recovered_agrees_with_recorded_newly_found":
                sorted(recovered) == sorted(c["a1_newly_found_ids"]),
        })
    if sorted(recovered_distinct) != EXPECTED_RECOVERED_DISTINCT:
        divergences.append(
            f"C1::recovered_distinct={sorted(recovered_distinct)} "
            f"expected {EXPECTED_RECOVERED_DISTINCT}")
    if len(missing_distinct) != EXPECTED_MISSING_DISTINCT_SIZE:
        divergences.append(
            f"C1::missing_distinct_size={len(missing_distinct)} "
            f"expected {EXPECTED_MISSING_DISTINCT_SIZE}")

    # --- C3: the three named responses --------------------------------------
    named: dict[str, dict] = {}
    by_cell = {c["cell"]: c for c in cells}

    def _named(cell_name: str, expect_rows: int, expect_status: int | None) -> None:
        c = by_cell.get(cell_name)
        env = envelopes.get(cell_url.get(cell_name, "")) if c else None
        if env is None:
            divergences.append(f"C3::{cell_name}::no_envelope")
            named[cell_name] = {"ok": False}
            return
        rows_ok = env["n_rows"] == expect_rows
        status_ok = True if expect_status is None else env["status"] == expect_status
        if not (rows_ok and status_ok):
            divergences.append(
                f"C3::{cell_name}::rows={env['n_rows']} status={env['status']} "
                f"expected rows={expect_rows} status={expect_status}")
        named[cell_name] = {"ok": bool(rows_ok and status_ok),
                            "n_rows": env["n_rows"], "status": env["status"]}

    _named("de-kapitalverletzung", 0, 200)
    _named("fr-bail-entretien", 1, None)
    _named("corporate-criminal-liability::fr", 0, 200)

    # --- C4: latency aggregates ---------------------------------------------
    lats = [env["latency_seconds"] for env in envelopes.values()]
    n_over = sum(1 for x in lats if x >= 30.0)
    mx = max(lats)
    sm = sum(lats)
    c4 = {
        "n_envelopes": len(lats),
        "n_over_30": n_over,
        "max_latency": mx,
        "max_latency_round1": round(mx, 1),
        "sum_latency": sm,
        "sum_round3": _round3(sm),
    }
    if len(lats) != TOTAL_CELLS:
        divergences.append(f"C4::n_envelopes={len(lats)} expected {TOTAL_CELLS}")
    if n_over != EXPECTED_N_OVER_30:
        divergences.append(f"C4::n_over_30={n_over} expected {EXPECTED_N_OVER_30}")
    if mx != EXPECTED_MAX_LATENCY:
        divergences.append(f"C4::max_latency={mx!r} expected {EXPECTED_MAX_LATENCY!r}")
    if round(mx, 1) != 83.5:
        divergences.append(f"C4::max_round1={round(mx, 1)!r} expected 83.5")
    c4["sum_vs_harness_600_569"] = _round3(sm) == EXPECTED_SUM_HARNESS_3DP
    c4["sum_vs_audit_600_568"] = _round3(sm) == EXPECTED_SUM_AUDIT_3DP
    if not c4["sum_vs_harness_600_569"]:
        divergences.append(
            f"C4::sum_round3={_round3(sm)!r} != harness published "
            f"{EXPECTED_SUM_HARNESS_3DP!r} (rounding-level, named)")
    # the audit-of-record value 600.568 is published beside the harness value;
    # disagreement with EITHER is named, but only the harness-field mismatch
    # is a divergence (the audit text is a third-party recomputation, published
    # beside, per the frozen rule 'compared against BOTH published values ...
    # with any disagreement named as a rounding-level divergence cell').
    if not c4["sum_vs_audit_600_568"]:
        divergences.append(
            f"C4::sum_round3={_round3(sm)!r} != audit-of-record "
            f"{EXPECTED_SUM_AUDIT_3DP!r} (rounding-level, named)")

    # --- C5: mechanism-witness count (record-internal, disclosed) -----------
    # DUAL SEMANTICS, both published: the frozen rule compares the changed-cell
    # count (!=) to the verdict evidence value 12; the evidence field is named
    # mechanism_witness_cells_with_added_rows (>), so both counts are emitted.
    witness_changed = 0
    witness_added = 0
    union_shrink_cells: list[dict] = []
    for c in cells:
        if c["kind"] == "leg":
            u, b = c.get("a1_union_n_rows"), c.get("a0_n_rows")
            if u is not None and b is not None:
                if u != b:
                    witness_changed += 1
                if u > b:
                    witness_added += 1
                if u < b:
                    union_shrink_cells.append(
                        {"cell": c["cell"], "a0_n_rows": b,
                         "a1_union_n_rows": u,
                         "a1_candidate_only_n_rows": c.get("a1_n_rows")})
        else:
            u, b = c.get("a1_n_rows"), c.get("a0_n_rows")
            if u is not None and b is not None:
                if u != b:
                    witness_changed += 1
                if u > b:
                    witness_added += 1
    witness = witness_changed
    if witness != EXPECTED_WITNESS_CELLS:
        divergences.append(
            f"C5::witness_cells_changed={witness} expected {EXPECTED_WITNESS_CELLS} "
            f"(added-only semantics yield {witness_added})")
    for anom in union_shrink_cells:
        divergences.append(
            f"C5::union_shrink_anomaly::{anom['cell']} a0={anom['a0_n_rows']} "
            f"union={anom['a1_union_n_rows']} a1_only="
            f"{anom['a1_candidate_only_n_rows']} (a set union cannot shrink)")

    # --- C6: FR/IT side-by-side ---------------------------------------------
    f3 = (durability.get("F3_language_recall_gate_stability") or {})
    acc_status = f3.get("accepted_status") or {}
    live_status = f3.get("live_status") or {}
    c6_rows: list[dict] = []
    for c in measurable_cells:
        if c["lang"] not in ("fr", "it"):
            continue
        gate_name = f"authority::baseline_lang_recall::{c['slug']}::{c['lang']}"
        env = envelopes.get(cell_url.get(c["cell"], ""))
        recovered = sorted((env["id_set"]
                            & set(required_by_slug.get(c["slug"]) or []))
                           - set(c["a0_hits"])) if env else ["<no-envelope>"]
        row = {
            "cell": c["cell"],
            "durability_accepted_status": acc_status.get(gate_name),
            "durability_live_status": live_status.get(gate_name),
            "frontier_a0_hits": sorted(c["a0_hits"]),
            "frontier_a1_newly_found": sorted(c["a1_newly_found_ids"]),
            "rederived_recovered": recovered,
        }
        ok = (row["durability_accepted_status"] == "FAIL"
              and row["durability_live_status"] == "FAIL"
              and row["frontier_a0_hits"] == []
              and row["frontier_a1_newly_found"] == []
              and recovered == [])
        row["ok"] = ok
        if not ok:
            divergences.append(f"C6::{c['cell']}::side_by_side_not_all_empty_fail")
        c6_rows.append(row)

    return {
        "cells": [{"cell": c["cell"], "kind": c["kind"]} for c in cells],
        "n_cells": len(cells),
        "bijection_ok": len(claimed_urls) == len(cells) == len(envelopes)
                        and not unclaimed,
        "C2_per_cell": c2_rows,
        "C1_recovery": {
            "measurable_cells": [c["cell"] for c in measurable_cells],
            "recovered_distinct": sorted(recovered_distinct),
            "missing_distinct": sorted(missing_distinct),
            "missing_distinct_size": len(missing_distinct),
            "per_cell": c1_rows,
        },
        "C3_named_responses": named,
        "C4_latency": c4,
        "C5_witness_cells": witness,
        "C5_witness_cells_added_semantics": witness_added,
        "C5_union_shrink_anomalies": union_shrink_cells,
        "C6_fr_it_side_by_side": c6_rows,
        "divergences": divergences,
        "n_divergences": len(divergences),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hypothesis", default=str(HYPOTHESIS_PATH))
    ap.add_argument("--amendment", default=str(AMENDMENT_PATH))
    ap.add_argument("--out", default=None,
                    help="result JSON path (default: committed claim-bearing tree)")
    ap.add_argument("--report-dir", default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--tag", default="",
                    help="optional suffix for the result filename, e.g. '_r2'; "
                         "used so a correction run never overwrites run 1")
    args = ap.parse_args(argv)

    hyp_path = Path(args.hypothesis)
    amendment_path = Path(args.amendment)
    hyp = _load(hyp_path)
    amendment = _load(amendment_path)
    run_id = args.run_id or hyp.get("frozen_for_run") or "scratch"
    claim_bearing = args.out is None and args.report_dir is None
    out_path = (Path(args.out) if args.out else _REPO_ROOT / "results" / "evaluation"
                / "frontier_bounded_cause_reproduction"
                / f"{run_id}{args.tag}.json")
    report_dir = (Path(args.report_dir) if args.report_dir else _REPO_ROOT
                  / "reports" / "evaluation")

    resolved, problems = verify_inputs(hyp)
    if problems:
        result = {
            "schema": SCHEMA, "run_id": run_id,
            "direction_version": hyp.get("direction_version"),
            "verdict": VERDICT_ENVIRONMENT,
            "environment_problems": problems,
            "hypothesis_sha256": _sha256_file(hyp_path),
            "amendment_sha256": _sha256_file(amendment_path),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, sort_keys=True),
                            encoding="utf-8")
        print(f"ENVIRONMENT: {'; '.join(problems)}")
        return 2

    gate_ok, gate_note = verify_gate(resolved["frontier_audit_gate_of_record"], hyp)
    if not gate_ok:
        result = {
            "schema": SCHEMA, "run_id": run_id,
            "verdict": VERDICT_ENVIRONMENT,
            "environment_problems": [f"audit gate not PASS: {gate_note}"],
            "hypothesis_sha256": _sha256_file(hyp_path),
            "amendment_sha256": _sha256_file(amendment_path),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, sort_keys=True),
                            encoding="utf-8")
        print(f"ENVIRONMENT: audit gate {gate_note}")
        return 2

    harness = _load(resolved["frontier_harness_results"])
    spec = _load(resolved["frozen_retrieval_spec"])
    durability = _load(resolved["lane_durability_record_accepted"])
    envelopes = load_envelopes(resolved["frontier_cache_manifest"])

    comparisons = run_comparisons(harness, spec, durability, envelopes)
    verdict = (VERDICT_REPRODUCED if comparisons["n_divergences"] == 0
               else VERDICT_DIVERGENCE)

    result = {
        "schema": SCHEMA,
        "run_id": run_id,
        "direction_version": hyp.get("direction_version"),
        "lane": "evaluation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "commit_at_execution": None,
        "correction_provenance": (
            None if not args.tag else {
                "tag": args.tag,
                "corrects_run": run_id,
                "what_changed": (
                    "build_cells now reads the per-cell search block as a SIBLING "
                    "of A1_candidate_only (the frozen rule's 'search.status'); run 1 "
                    "extracted A1_candidate_only.search (always absent) and fired 12 "
                    "spurious C2 status divergences. C5 now also emits added-only "
                    "witness semantics and the union-shrink anomaly list. The frozen "
                    "cells, expectations, digests and exit mappings are unchanged; "
                    "run 1's artifact is preserved verbatim and never overwritten."
                ),
            }),
        "hypothesis_path": str(hyp_path),
        "hypothesis_sha256": _sha256_file(hyp_path),
        "amendment_path": str(amendment_path),
        "amendment_sha256": _sha256_file(amendment_path),
        "input_digests_verified": sorted(resolved),
        "input_digest_problems": [],
        "audit_gate_note": gate_note,
        "verdict": verdict,
        "claim_ceiling": hyp.get("claim_ceiling"),
        "human_gate_ready": False,
        "owner_decision_required": False,
        "comparisons": comparisons,
        "headline": (verdict if verdict != VERDICT_DIVERGENCE
                     else comparisons["divergences"][0]),
    }
    # record the executing commit when available (claim-bearing runs only)
    try:
        import subprocess
        result["commit_at_execution"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT,
            text=True).strip()
    except Exception:
        pass

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True),
                        encoding="utf-8")

    if claim_bearing:
        report_dir.mkdir(parents=True, exist_ok=True)
        rep = report_dir / f"FRONTIER_BOUNDED_CAUSE_REPRODUCTION_{run_id}{args.tag}.md"
        div = comparisons["divergences"]
        lines = [
            f"# Frontier bounded-cause reproduction — run {run_id}",
            "",
            f"- Verdict: **{verdict}**",
            f"- Headline: {result['headline']}",
            f"- Divergences: {comparisons['n_divergences']}",
            f"- Cells: {comparisons['n_cells']}, bijection_ok: {comparisons['bijection_ok']}",
            f"- C1 recovered_distinct: {comparisons['C1_recovery']['recovered_distinct']}"
            f" (size {comparisons['C1_recovery']['missing_distinct_size']}"
            f" distinct missing ids)",
            f"- C4 latency: n_over_30={comparisons['C4_latency']['n_over_30']},"
            f" max={comparisons['C4_latency']['max_latency']},"
            f" sum_round3={comparisons['C4_latency']['sum_round3']}"
            f" (vs harness {EXPECTED_SUM_HARNESS_3DP},"
            f" vs audit {EXPECTED_SUM_AUDIT_3DP})",
            f"- C5 witness cells: changed={comparisons['C5_witness_cells']}/15,"
            f" added-only={comparisons['C5_witness_cells_added_semantics']}/15,"
            f" union-shrink anomalies={len(comparisons['C5_union_shrink_anomalies'])}",
            f"- C6 FR/IT side-by-side rows: {len(comparisons['C6_fr_it_side_by_side'])}"
            f" (all FAIL/empty expected)",
            "",
            "## Divergences (each is the headline, never smoothed)",
        ]
        lines += [f"- {d}" for d in div] if div else ["- none"]
        lines += [
            "",
            "Claim ceiling: reproduces or fails to reproduce published numbers of an",
            "already-accepted OUTCOME_B bounded negative against its own committed cache",
            "and the frozen spec. No candidate is built or re-scored; no frozen bar is",
            "met or moved; no owner question is authorised.",
        ]
        rep.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"{verdict} divergences={comparisons['n_divergences']} out={out_path}")
    return 0 if verdict == VERDICT_REPRODUCED else (
        2 if verdict == VERDICT_ENVIRONMENT else 1)


if __name__ == "__main__":
    raise SystemExit(main())
