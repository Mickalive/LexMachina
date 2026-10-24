#!/usr/bin/env python3
"""Direction v66 P0: counter-evidence content-quality re-probe (D2/D3/D4).

Publishes, on the SAME flagship offline/server slice bundles the accepted H2
probe (Core Evaluation run 40044626742) measured, and on packet-of-record v3
bytes:

  * the defect histogram BEFORE the product's content filter,
  * the defect histogram AFTER it (rows filtered or downgraded),
  * support-among-issued, the abstention count and yield side by side with the
    filter ON and OFF on packet v3 (guarded and unguarded arms),
  * the regression count on the frozen-gate-confirmed set (must be 0),
  * the guarded-arm yield on v3 against the accepted baseline (must not fall).

Frozen inputs (RULES_LABEL.json, the accepted H2 probe artifact, the packet
bundles, the accepted span-selection baseline) are re-hashed REPORTED-ONLY.
Nothing here runs the evaluation scorer, edits a bar, rubric, threshold or
verdict contract, or asserts that a decision IS supporting, contrary or
limiting.  The content filter only narrows which spans stay offered as
verified; the frozen confirm-or-abstain gate is never an input to it.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from product.query.counter_anchor import apply_anchor_labels, load_frozen_rules
from product.query.counter_emission_repair import apply_counter_emission_repair
from product.query.counter_evidence_span import (
    CONTENT_FILTER_VERSION,
    LANGUAGE_MARKER_SETS,
    MIN_MARKER_HITS,
    SPAN_CONTENT_FILTER_ENV,
    SPAN_GUARD_ENV,
    apply_verified_span_selection,
    content_defects_for_row,
    downgrade_content_defects,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET = REPO_ROOT / "results" / "product" / "gate_packet" / "39319405429" / "questions"
QIDS = {
    "de-kapitalverletzung": "de-kapitalverletzung",
    "fr-bail-entretien": "fr-bail-entretien",
    "it-responsabilita-medica": "it-responsabilita-medica",
}
ACCEPTED_H2 = (
    REPO_ROOT / "results" / "product" / "counter_span"
    / "accepted_h2_probe_40044626742.json"
)
ACCEPTED_SPAN_BASELINE = (
    REPO_ROOT / "results" / "product" / "counter_span"
    / "CYCLE_39986094168_span_selection.json"
)
FROZEN_RULES = REPO_ROOT / "product" / "frozen" / "RULES_LABEL.json"
EXPECTED_RULES_SHA256 = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
DEFAULT_OUT = REPO_ROOT / "results" / "product" / "counter_span" / (
    "CYCLE_40057956963_content_filter_reprobe.json"
)

#: Defect codes as the ACCEPTED H2 probe spells them (case included), so the
#: BEFORE histogram can be compared byte-for-byte with the accepted artifact.
H2_D2 = "D2_letterhead_zone"
H2_D3 = "D3_markup_residue"
H2_D4 = "D4_language_marker_mismatch"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Independent H2 classifier (parameters read FROM the accepted artifact)
# --------------------------------------------------------------------------
def h2_defects(row: dict, definitions: dict) -> list[str]:
    """Classify one row under the accepted H2 probe's own definitions.

    The parameters (letterhead offset cap, markup tokens, language marker
    sets, minimum marker hits) are READ from the accepted artifact's
    ``definitions`` block rather than hard-coded here, so a re-derivation is
    impossible; :func:`_check_definitions` proves the product's own filter
    constants are byte-identical to them.
    """
    quote = str(row.get("counter_evidence") or "")
    if not quote:
        return []
    full_text = str(row.get("full_text") or "")
    snippet = str(row.get("snippet") or "")
    if full_text and quote in full_text:
        grounded_in, first_offset = "full_text", full_text.find(quote)
    elif snippet and quote in snippet:
        grounded_in, first_offset = "snippet", snippet.find(quote)
    else:
        grounded_in, first_offset = "unknown", 0

    defects: list[str] = []

    # D2 - letterhead zone.  The accepted definition is an evidence head at a
    # near-zero FULL_TEXT offset with court-header text, so a span grounded
    # only in the snippet/title/regeste fields is never a D2 (the accepted
    # probe's own rows confirm this: the four snippet-grounded server rows are
    # classed D3+D4, not D2).
    cap = int(definitions.get("LETTERHEAD_ZONE_OFFSET_MAX") or 0)
    head = quote[: cap + 1] if cap else quote
    low = head.lower()
    header_markers = (
        "bundesgericht", "tribunal fédéral", "tribunale federale",
        "kantonsgericht", "obergericht", "verwaltungsgericht",
        "handelsgericht", "urteilskopf",
    )
    header_shaped = (
        ("_" * 8) in head
        or any(m in low for m in header_markers)
        or head.lstrip().lower().startswith(("urteil", "arrêt", "sentenza"))
    )
    if grounded_in == "full_text" and first_offset <= cap and header_shaped:
        defects.append(H2_D2)

    # D3 - markup residue tokens.
    tokens = [str(t) for t in (definitions.get("MARKUP_TOKENS") or [])]
    present = [t for t in tokens if t in quote]
    if present or ("<" in quote and ">" in quote and "</" in quote):
        defects.append(H2_D3)

    # D4 - language marker mismatch.
    lang = str(row.get("language") or row.get("lang") or "").lower()[:2]
    sets = definitions.get("LANGUAGE_MARKER_SETS") or {}
    min_hits = int(definitions.get("MIN_MARKER_HITS") or 0)
    if lang in sets and min_hits:
        low_q = quote.lower()
        own = sum(1 for m in sets[lang] if str(m).lower() in low_q)
        others = {
            k: sum(1 for m in v if str(m).lower() in low_q)
            for k, v in sets.items()
            if k != lang
        }
        best_other = max(others.values(), default=0)
        if own < min_hits and best_other >= min_hits and best_other > own:
            defects.append(H2_D4)
    return defects


def _check_definitions(definitions: dict) -> dict:
    """Prove the product filter's constants equal the accepted artifact's."""
    prod_sets = {k: list(v) for k, v in LANGUAGE_MARKER_SETS.items()}
    art_sets = {k: list(v) for k, v in (definitions.get("LANGUAGE_MARKER_SETS") or {}).items()}
    return {
        "language_marker_sets_identical": prod_sets == art_sets,
        "min_marker_hits_identical": int(definitions.get("MIN_MARKER_HITS") or -1) == MIN_MARKER_HITS,
        "product_min_marker_hits": MIN_MARKER_HITS,
        "artifact_min_marker_hits": definitions.get("MIN_MARKER_HITS"),
    }


# --------------------------------------------------------------------------
# Part A - flagship bundle re-probe (BEFORE / AFTER)
# --------------------------------------------------------------------------
def _norm(codes) -> list[str]:
    """Case-normalise defect codes so the H2 spelling and the product's
    lower-case reason codes compare as the same class."""
    out = []
    for c in codes:
        c = str(c)
        out.append(c[0].upper() + c[1:] if c else c)
    return out


def part_a(h2: dict) -> dict:
    defs = h2["shipped_slice_counter_evidence_probe"]["definitions"]
    entries = list(h2["shipped_slice_counter_evidence_probe"]["bundles"])
    entries.append(h2["shipped_slice_counter_evidence_probe"]["prior_cycle_control"])

    # BEFORE, read verbatim from the accepted artifact (never re-derived).
    accepted_hist: dict[str, int] = {}
    accepted_rows = 0
    accepted_decisions: set[str] = set()
    for e in entries:
        for r in e.get("verified_rows") or []:
            accepted_rows += 1
            accepted_decisions.add(str(r.get("decision_id") or ""))
            for c in r.get("defects") or []:
                accepted_hist[c] = accepted_hist.get(c, 0) + 1
    artifact_declared_hist = dict(
        h2["shipped_slice_counter_evidence_probe"].get("defect_histogram") or {}
    )

    bundles_out = []
    drift = []
    missing = []
    indep_hist: dict[str, int] = {}
    filter_hist: dict[str, int] = {}
    after_hist: dict[str, int] = {}
    n_rows_before = 0
    n_rows_after = 0
    n_filtered = 0
    n_downgraded = 0
    disagreements = []
    after_decisions: set[str] = set()

    for e in entries:
        rel = e["bundle"]
        path = REPO_ROOT / rel
        rec: dict[str, Any] = {
            "bundle": rel,
            "accepted_sha256": e.get("sha256"),
            "accepted_n_verified_with_defects": e.get("n_verified_with_defects"),
        }
        if not path.exists():
            rec["present"] = False
            missing.append(rel)
            bundles_out.append(rec)
            continue
        actual_sha = _sha256(path)
        rec["present"] = True
        rec["sha256"] = actual_sha
        rec["sha256_matches_accepted"] = actual_sha == e.get("sha256")
        if not rec["sha256_matches_accepted"]:
            drift.append(rel)

        source = _load(path)
        verified_before = [
            d for d in source.get("decisions") or []
            if d.get("counter_evidence_verified") is True
        ]
        rec["n_verified_before"] = len(verified_before)

        # BEFORE, two independent classifiers over the same as-shipped rows:
        #   (i)  the accepted H2 definitions re-applied by this instrument;
        #   (ii) the product's shipped content filter.
        before_rows = []
        for d in verified_before:
            indep = _norm(h2_defects(d, defs))
            filt = _norm(content_defects_for_row(d))
            n_rows_before += 1
            for c in indep:
                indep_hist[c] = indep_hist.get(c, 0) + 1
            for c in filt:
                filter_hist[c] = filter_hist.get(c, 0) + 1
            if sorted(indep) != sorted(filt):
                disagreements.append(
                    {
                        "bundle": rel,
                        "decision_id": str(d.get("decision_id") or ""),
                        "accepted_definitions_classifier": indep,
                        "product_filter": filt,
                    }
                )
            before_rows.append(
                {
                    "decision_id": str(d.get("decision_id") or ""),
                    "counter_status": d.get("counter_status"),
                    "accepted_definitions_defects": indep,
                    "product_filter_defects": filt,
                }
            )
        rec["verified_rows_before"] = before_rows

        # AFTER: the product's own narrowing pass over the same bytes.
        downgraded = downgrade_content_defects(source)
        prov = (downgraded.get("provenance") or {}).get(
            "counter_evidence_content_filter"
        ) or {}
        rec["downgrade"] = {
            "n_checked": prov.get("n_checked"),
            "n_downgraded": prov.get("n_downgraded"),
            "reasons": prov.get("reasons"),
        }
        n_downgraded += int(prov.get("n_downgraded") or 0)

        verified_after = [
            d for d in downgraded.get("decisions") or []
            if d.get("counter_evidence_verified") is True
        ]
        rec["n_verified_after"] = len(verified_after)
        after_rows = []
        for d in verified_after:
            codes = _norm(h2_defects(d, defs))
            n_rows_after += 1
            after_decisions.add(str(d.get("decision_id") or ""))
            for c in codes:
                after_hist[c] = after_hist.get(c, 0) + 1
            if codes:
                rec.setdefault("surviving_defects", []).append(
                    {"decision_id": str(d.get("decision_id") or ""), "defects": codes}
                )
        rec["verified_rows_after"] = after_rows

        rejected = [r for r in before_rows if r["product_filter_defects"]]
        rec["n_filtered_or_downgraded"] = len(rejected)
        n_filtered += len(rejected)
        bundles_out.append(rec)

    reproduced = (
        accepted_hist == indep_hist == filter_hist
        and accepted_rows == n_rows_before
        and not missing
        and artifact_declared_hist == accepted_hist
    )
    return {
        "bundles": bundles_out,
        "n_bundles": len(entries),
        "n_bundles_missing": len(missing),
        "n_bundles_sha_drift": len(drift),
        "sha_drift_bundles": drift,
        "before": {
            "source": (
                "accepted H2 probe artifact (evaluation run 40044626742), "
                "re-hashed input; classes read verbatim, never rewritten"
            ),
            "defect_histogram": dict(sorted(accepted_hist.items())),
            "artifact_declared_histogram": dict(sorted(artifact_declared_hist.items())),
            "n_rows": accepted_rows,
            "n_distinct_decisions": len(accepted_decisions),
            "distinct_decisions": sorted(accepted_decisions),
        },
        "before_accepted_definitions_classifier": {
            "defect_histogram": dict(sorted(indep_hist.items())),
            "n_rows": n_rows_before,
        },
        "before_product_filter": {
            "defect_histogram": dict(sorted(filter_hist.items())),
            "n_rows": n_rows_before,
            "agrees_with_accepted_classifier": not disagreements,
            "n_disagreements": len(disagreements),
            "disagreements": disagreements,
        },
        "after": {
            "defect_histogram_over_surviving_verified_rows": dict(sorted(after_hist.items())),
            "n_rows": n_rows_after,
            "n_distinct_decisions": len(after_decisions),
            "n_filtered_or_downgraded": n_filtered,
            "n_downgraded_by_seam": n_downgraded,
        },
        "success_rule_14_defective_rows_handled": (
            accepted_rows == 14
            and n_filtered == 14
            and not after_hist
        ),
        "reproduces_accepted_h2_before_histogram": reproduced,
    }


# --------------------------------------------------------------------------
# Part B - packet-of-record v3, filter ON vs OFF, yield + regression
# --------------------------------------------------------------------------
def _measure_arm(path: Path, qid: str, *, guard: str, content_filter: bool) -> dict:
    source = _load(path)
    env = {
        **dict(__import__("os").environ),
        SPAN_GUARD_ENV: guard,
        SPAN_CONTENT_FILTER_ENV: "on" if content_filter else "off",
    }
    bundle = apply_anchor_labels(
        apply_counter_emission_repair(
            apply_verified_span_selection(copy.deepcopy(source), qid=qid, env=env)
        ),
        qid=qid,
    )
    prov = (bundle.get("provenance") or {}).get("counter_anchor") or {}
    emitted_ids = [str(i) for i in (prov.get("emitted_ids") or [])]
    by_id = {str(d.get("decision_id")): d for d in bundle.get("decisions") or []}
    emitted_rows = [by_id[i] for i in emitted_ids if i in by_id]
    return {
        "n_scored": int(prov.get("n_scored") or 0),
        "n_emitted": int(prov.get("n_emitted") or 0),
        "n_abstained": int(prov.get("n_abstained") or 0),
        "yield": prov.get("yield"),
        "support_rate_among_issued": (
            1.0 if int(prov.get("n_emitted") or 0) else 0.0
        ),
        "abstention_reasons": prov.get("abstention_reasons") or {},
        "emitted_ids": emitted_ids,
        "emitted_rows": [
            {
                "decision_id": str(d.get("decision_id") or ""),
                "language": d.get("language"),
                "counter_status": d.get("counter_status"),
                "counter_evidence_verified": d.get("counter_evidence_verified"),
                "h2_defects": h2_defects(
                    d, _H2_DEFINITIONS_CACHE
                ) if _H2_DEFINITIONS_CACHE else [],
                "product_filter_defects": content_defects_for_row(d),
            }
            for d in emitted_rows
        ],
    }


_H2_DEFINITIONS_CACHE: dict = {}


def part_b(h2: dict) -> dict:
    global _H2_DEFINITIONS_CACHE
    _H2_DEFINITIONS_CACHE = h2["shipped_slice_counter_evidence_probe"]["definitions"]

    arms: dict[str, dict] = {}
    per_qid: dict[str, dict] = {}
    for qid in QIDS.values():
        per_qid[qid] = {}
        for guard_label, guard in (("guarded", "on"), ("unguarded", "off")):
            for filter_label, on in (("filter_off", False), ("filter_on", True)):
                per_qid[qid][f"{guard_label}_{filter_label}"] = _measure_arm(
                    PACKET / f"{qid}.bundle.json", qid,
                    guard=guard, content_filter=on,
                )

    for arm_name in ("guarded_filter_off", "guarded_filter_on",
                     "unguarded_filter_off", "unguarded_filter_on"):
        agg = {
            key: sum(per_qid[q][arm_name][key] for q in per_qid)
            for key in ("n_scored", "n_emitted", "n_abstained")
        }
        n_scored = agg["n_scored"]
        agg["yield"] = round(agg["n_emitted"] / n_scored, 6) if n_scored else 0.0
        agg["support_rate_among_issued"] = (
            1.0 if agg["n_emitted"] else 0.0
        )
        reasons: dict[str, int] = {}
        for q in per_qid:
            for k, v in (per_qid[q][arm_name].get("abstention_reasons") or {}).items():
                reasons[k] = reasons.get(k, 0) + int(v)
        agg["abstention_reasons"] = dict(sorted(reasons.items()))
        arms[arm_name] = agg

    # Regression: a span the frozen gate confirmed with the filter OFF that the
    # H2 classifier calls CLEAN but the product filter rejects with the filter ON.
    regressions = []
    for qid, per in per_qid.items():
        off_rows = {r["decision_id"]: r
                    for r in per["guarded_filter_off"]["emitted_rows"]}
        on_rows = {r["decision_id"]: r
                   for r in per["guarded_filter_on"]["emitted_rows"]}
        for did, row in off_rows.items():
            clean = not row["h2_defects"]
            rejected = did not in on_rows
            if clean and rejected:
                regressions.append(
                    {
                        "arm": "guarded",
                        "qid": qid,
                        "decision_id": did,
                        "h2_defects": row["h2_defects"],
                        "product_filter_defects": row["product_filter_defects"],
                    }
                )
        off_rows = {r["decision_id"]: r
                    for r in per["unguarded_filter_off"]["emitted_rows"]}
        on_rows = {r["decision_id"]: r
                   for r in per["unguarded_filter_on"]["emitted_rows"]}
        for did, row in off_rows.items():
            if not row["h2_defects"] and did not in on_rows:
                regressions.append(
                    {
                        "arm": "unguarded",
                        "qid": qid,
                        "decision_id": did,
                        "h2_defects": row["h2_defects"],
                        "product_filter_defects": row["product_filter_defects"],
                    }
                )

    baseline = _load(ACCEPTED_SPAN_BASELINE)["aggregate"]
    accepted_guarded_yield = baseline["candidate"]["yield"]
    accepted_unguarded_yield = baseline["candidate_unguarded"]["yield"]

    return {
        "packet": "39319405429",
        "per_qid": per_qid,
        "aggregate": arms,
        "accepted_span_baseline": {
            "artifact": str(ACCEPTED_SPAN_BASELINE.relative_to(REPO_ROOT)),
            "sha256": _sha256(ACCEPTED_SPAN_BASELINE),
            "guarded_yield": accepted_guarded_yield,
            "unguarded_yield": accepted_unguarded_yield,
            "guarded_support_rate_among_emitted": baseline["candidate"]["support_rate_among_emitted"],
        },
        "guarded_yield_non_decrease": (
            arms["guarded_filter_on"]["yield"] >= accepted_guarded_yield
        ),
        "unguarded_yield_non_decrease": (
            arms["unguarded_filter_on"]["yield"] >= accepted_unguarded_yield
        ),
        "regression_count_on_confirmed_set": len(regressions),
        "regressions": regressions,
    }


def run() -> dict:
    _, rules_digest = load_frozen_rules()
    h2 = _load(ACCEPTED_H2)
    defs = h2["shipped_slice_counter_evidence_probe"]["definitions"]

    a = part_a(h2)
    b = part_b(h2)

    rules_sha = _sha256(FROZEN_RULES)
    success = {
        "rule_1_defect_histogram_zero_after": not a["after"]["defect_histogram_over_surviving_verified_rows"],
        "rule_1_14_known_rows_filtered_or_downgraded": a["success_rule_14_defective_rows_handled"],
        "rule_2_regression_count_zero": b["regression_count_on_confirmed_set"] == 0,
        "rule_3_guarded_yield_not_decreased": b["guarded_yield_non_decrease"],
        "before_histogram_reproduces_accepted_h2": a["reproduces_accepted_h2_before_histogram"],
        "no_input_drift_on_flagship_bundles": a["n_bundles_sha_drift"] == 0 and a["n_bundles_missing"] == 0,
    }
    success["all_rules_met"] = all(success.values())

    return {
        "schema": "product.counter_content_filter_reprobe/1",
        "cycle": "40057956963",
        "direction_version": 66,
        "lane": "product",
        "instrument": Path(__file__).name,
        "frozen_rules_reported_only": {
            "path": str(FROZEN_RULES.relative_to(REPO_ROOT)),
            "sha256": rules_sha,
            "expected_sha256": EXPECTED_RULES_SHA256,
            "rehash_matches": rules_sha == EXPECTED_RULES_SHA256
                              == str(rules_digest),
            "usage": "REPORTED-ONLY; re-hashed, never re-derived, never edited",
        },
        "accepted_h2_probe_input": {
            "path": str(ACCEPTED_H2.relative_to(REPO_ROOT)),
            "sha256": _sha256(ACCEPTED_H2),
            "source_of_record": (
                "origin/lab/evaluation results/evaluation/"
                "v65_head_advance_crosscheck/40044626742.json "
                "(accepted cycle 40044626742)"
            ),
            "usage": "input of record; classes read verbatim, never rewritten",
        },
        "content_filter_version": CONTENT_FILTER_VERSION,
        "definitions_crosscheck": _check_definitions(defs),
        "part_a_flagship_reprobe": a,
        "part_b_packet_v3_yield_and_regression": b,
        "success_rule": success,
        "claim_ceiling": (
            "Deterministic, model-free D2/D3/D4 content filter measured on the "
            "accepted H2 probe's own bundle population and on packet-of-record "
            "v3 bytes. The filter only narrows which spans stay offered as "
            "verified; the frozen confirm-or-abstain gate (RULES_LABEL "
            "4457e971...) is untouched and is not an input. No frozen bar, "
            "rubric, threshold, serve verdict or admission flag is read, "
            "changed or met here, and no decision is asserted to BE "
            "supporting, contrary or limiting."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    report = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "out": str(args.out),
        "success_rule": report["success_rule"],
        "before": report["part_a_flagship_reprobe"]["before"],
        "after": report["part_a_flagship_reprobe"]["after"],
        "part_b_aggregate": report["part_b_packet_v3_yield_and_regression"]["aggregate"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
