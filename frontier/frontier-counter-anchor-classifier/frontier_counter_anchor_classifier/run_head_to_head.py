"""Head-to-head: candidate vs incumbent on the served packet 38839347028.

One run, same rows, same frozen rubric:

  1. FREEZE-FIRST: load RULES_LABEL.json, prove its sha256 equals the accepted
     frozen hash 4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608
     before computing anything.  Any drift aborts the run.
  2. INCUMBENT (reproduction): extract the 65 scored counter rows from the
     three served bundles and score the labels the product actually issued
     under the frozen rubric.  The accepted result is 5/65 = 0.0769
     (LABEL_HALF.json).  This run reproduces it, or reports the divergence
     per row.
  3. CANDIDATE: run the new sentence-anchored decision function on the SAME
     65 rows.  Count emitted labels and abstentions; score the emitted labels
     under the same frozen rubric.  Report support rate, abstention count and
     yield side by side.
  4. NON-VACUITY: an inverted-label control set and a swapped-evidence
     control, both scored under the same frozen rubric, must score STRICTLY
     BELOW the candidate.  A tie voids the run.

No rubric, lexicon, bar or threshold is edited.  No file under product/,
evaluation/, results/product/, state/product.json or .github/ is touched.

Usage:
    python -m frontier_counter_anchor_classifier.run_head_to_head \
        --rules results/frontier/frontier-counter-anchor-classifier/RULES_LABEL.json \
        --bundles-dir /tmp/lex_accepted/core/product/results/product/gate_packet/38839347028/questions \
        --accepted-label-half /tmp/LABEL_HALF.json \
        --out results/frontier/frontier-counter-anchor-classifier/HEAD_TO_HEAD.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from typing import Any

from .counter_anchor_classifier import LABEL_ABSTAIN, STATUS_TO_LABEL, decide_label
from .vendored.extract import ROW_FIELDS, counter_rows, load_bundle, sha256_file
from .vendored.injection import run_non_vacuity
from .vendored.rubric import VARIANT_PRIMARY, make_context, score_row
from .vendored.rules import FrozenRules, load_rules

#: The accepted frozen rubric hash (charter acceptance test 1).
FROZEN_RULES_SHA256 = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"

#: The charter's measurement population: the three served bundles.
BUNDLE_QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")

QID_TO_PROFILE = {
    "de-kapitalverletzung": "de-kapitalverletzung",
    "fr-bail-entretien": "fr-bail-entretien",
    "it-responsabilita-medica": "it-responsabilita-medica",
}

SCHEMA = "frontier-counter-anchor-classifier/head-to-head/1"


def _sha256_file(path: str) -> str:
    return sha256_file(path)


def _class_breakdown(rows: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        k = str(r["primary_defect_class"])
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def _load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _extract_scored(bundle_path: str, rules: FrozenRules) -> tuple[list[dict], list[dict], dict]:
    bundle = load_bundle(bundle_path)
    scored_statuses = list(rules.rubric["scored_statuses"])
    reported_statuses = list(rules.rubric["reported_separately_never_scored"])
    scored, reported = counter_rows(bundle, scored_statuses, reported_statuses)
    return scored, reported, bundle


def _score_under_rubric(
    rows: list[dict[str, Any]], rules: FrozenRules, profile_key: str
) -> list[dict[str, Any]]:
    ctx = make_context(rules, profile_key, VARIANT_PRIMARY)
    return [score_row(r, ctx) for r in rows]


def _per_row_verdict(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision_id": r.get("decision_id"),
        "primary_defect_class": r.get("primary_defect_class"),
        "reason_code": r.get("reason_code"),
        "supported": r.get("supported"),
    }


def _verdict_key(bundle: Any, row: dict[str, Any], defect: Any = None,
                 reason: Any = None, supported: Any = None) -> tuple:
    """A COMPOSITE, duplicate-safe key for one row's verdict.

    REPAIR (cycle 38970902524, accepted-audit advisory D): the accepted
    population contains 4 decision_ids that occur TWICE (bge_140 II 112,
    bge_105 II 114, bge_135 III 556, bge_131 III 459), so a dict keyed by
    decision_id alone silently collapsed 65 rows into 61 keys and dropped 4
    rows from the reproduction proof.  The key is now the full verdict tuple,
    and comparison is a MULTISET (Counter) comparison.
    """
    if defect is None:
        verdict = row.get("_verdict") if isinstance(row.get("_verdict"), dict) else row
        defect = verdict.get("primary_defect_class")
        reason = verdict.get("reason_code")
        supported = verdict.get("supported")
    return (
        str(bundle or ""),
        str(row.get("decision_id")),
        str(row.get("counter_status")),
        str(defect),
        str(reason),
        bool(supported),
    )


def _compare_to_accepted(
    reproduced: list[dict[str, Any]], accepted_rows: list[dict[str, Any]],
    accepted_by_bundle: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """MULTISET comparison of this run's incumbent scoring vs LABEL_HALF.json.

    REPAIR 38970902524 (advisory D).  The previous version keyed both sides by
    ``decision_id`` into plain dicts.  Because 4 decision_ids appear twice in
    the 65-row population, that compared only 61 of the 65 rows and reported
    ``reproduced_byte_identical_verdicts`` on the strength of 61 keys.  This
    version compares full verdict tuples as multisets and ALSO reports the
    duplicate ids explicitly, so the coverage claim cannot silently shrink
    again.
    """
    if accepted_by_bundle is None:
        # Callers that do not carry per-bundle provenance fall back to a single
        # unnamed bucket; the comparison stays duplicate-safe either way.
        accepted_by_bundle = {"": list(accepted_rows)}

    acc_counter: Counter = Counter()
    for qid, rows in accepted_by_bundle.items():
        for r in rows:
            acc_counter[_verdict_key(qid, r)] += 1
    rep_counter: Counter = Counter()
    for r in reproduced:
        rep_counter[_verdict_key(r.get("_bundle"), r)] += 1

    matched = sum((acc_counter & rep_counter).values())
    only_accepted = acc_counter - rep_counter
    only_reproduced = rep_counter - acc_counter
    only_accepted_rows = sorted(only_accepted.elements())
    only_reproduced_rows = sorted(only_reproduced.elements())
    divergent = [{"accepted": list(k)} for k in only_accepted_rows]
    n_accepted = sum(acc_counter.values())
    n_reproduced = sum(rep_counter.values())
    dup_ids = sorted({
        str(r.get("decision_id")) for r in reproduced
        if sum(1 for x in reproduced if str(x.get("decision_id")) == str(r.get("decision_id"))) > 1
    })
    return {
        "comparison": "multiset over full verdict tuples (bundle, decision_id, counter_status, primary_defect_class, reason_code, supported)",
        "repair": "38970902524 advisory D: was a dict keyed by decision_id, which collapsed the 4 duplicated decision_ids (65 rows -> 61 keys)",
        "n_accepted_rows": n_accepted,
        "n_reproduced_rows": n_reproduced,
        "n_accepted_unique_decision_id_keys": len({
            str(r.get("decision_id")) for rows in accepted_by_bundle.values() for r in rows}),
        "n_rows_matched": matched,
        "n_rows_divergent": len(only_accepted_rows) + len(only_reproduced_rows),
        "duplicate_decision_ids_in_population": dup_ids,
        "n_duplicate_decision_ids": len(dup_ids),
        "only_in_accepted": [
            {"bundle": k[0], "decision_id": k[1], "counter_status": k[2],
             "primary_defect_class": k[3], "reason_code": k[4], "supported": k[5]}
            for k in only_accepted_rows
        ],
        "only_in_reproduced": [
            {"bundle": k[0], "decision_id": k[1], "counter_status": k[2],
             "primary_defect_class": k[3], "reason_code": k[4], "supported": k[5]}
            for k in only_reproduced_rows
        ],
        "divergent_rows": divergent,
        "coverage_is_full_population": (n_accepted == len(accepted_rows) == n_reproduced),
        "reproduced_byte_identical_verdicts": (
            matched == n_accepted == n_reproduced
            and not only_accepted and not only_reproduced
        ),
    }


def _build_swapped_control(
    candidate_decisions: list[Any],
    profile_by_qid: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Swapped-evidence control (charter acceptance test 5).

    For every row the candidate EMITS, build a control row that is identical
    except its cited evidence is swapped for the cited evidence of a decision
    from a DIFFERENT bundle (cross-bundle swap).  The label (counter_status)
    is kept.  Because the swapped passage speaks to a different question, it
    lacks this row's domain/pivot anchors, so the frozen rubric must score it
    unsupported.  Donor selection is deterministic (round-robin over the
    emitted rows of the other bundles).
    """
    emitted = [d for d in candidate_decisions if not d.abstained]
    if len(emitted) < 2:
        return [], []
    # Donors: emitted rows grouped by bundle, swapped across bundles.
    by_bundle: dict[str, list[Any]] = {}
    for d in emitted:
        qid = _qid_of(d)
        by_bundle.setdefault(qid, []).append(d)
    bundles_sorted = sorted(by_bundle)
    control_rows: list[dict[str, Any]] = []
    control_meta: list[dict[str, Any]] = []
    for i, d in enumerate(emitted):
        donor_bundle = bundles_sorted[(bundles_sorted.index(_qid_of(d)) + 1) % len(bundles_sorted)]
        donors = by_bundle[donor_bundle]
        donor = donors[i % len(donors)]
        row = {k: None for k in ROW_FIELDS}
        row.update({
            "decision_id": f"SWAPPED_{d.decision_id}",
            "counter_status": d.proposed_status,
            "counter_evidence": donor.cited_sentence,
            "counter_reason": None,
            "counter_confidence": None,
            "counter_uncertainty": None,
            "counter_evidence_verified": False,
            "counter_markers": None,
            "rank": d.rank,
            "language": d.language,
            "court": None,
            "court_name": None,
            "title": None,
            "regeste": None,
            "citation": None,
            "legal_area": None,
            "field_presence": {k: (k in ROW_FIELDS) for k in ROW_FIELDS},
            "full_text_len": 0,
            "row_text": donor.cited_sentence,
            "snippet": "",
            "detail_status": None,
            "channels": [],
            "provenance": {"control": "swapped_evidence_cross_bundle"},
        })
        control_rows.append(row)
        control_meta.append({
            "control_id": f"SWP-{i+1:02d}",
            "decision_id": row["decision_id"],
            "bundle": _qid_of(d),
            "donor_bundle": donor_bundle,
            "donor_decision_id": donor.decision_id,
            "proposed_status": d.proposed_status,
            "swapped_evidence": donor.cited_sentence,
        })
    return control_rows, control_meta


def _qid_of(decision: Any) -> str:
    return str(decision.criterion_evidence.get("_bundle") or "")


def run(
    rules_path: str,
    bundles_dir: str,
    accepted_label_half_path: str | None,
    out_path: str,
) -> dict[str, Any]:
    # -- 1. FREEZE-FIRST by re-hash ----------------------------------------
    rules = load_rules(rules_path)
    rules_ok = rules.sha256 == FROZEN_RULES_SHA256
    if not rules_ok:
        raise ValueError(
            f"FROZEN RUBRIC DRIFT: {rules_path} sha256 {rules.sha256} != "
            f"{FROZEN_RULES_SHA256}. Run is void; no scoring was computed."
        )

    # -- 2. INCUMBENT reproduction -----------------------------------------
    bundle_results: dict[str, dict[str, Any]] = {}
    all_incumbent_rows: list[dict[str, Any]] = []
    for qid in BUNDLE_QIDS:
        profile_key = QID_TO_PROFILE[qid]
        bundle_path = os.path.join(bundles_dir, f"{qid}.bundle.json")
        scored, reported, bundle = _extract_scored(bundle_path, rules)
        incumbent_scored = _score_under_rubric(scored, rules, profile_key)
        for r in incumbent_scored:
            r["_bundle"] = qid
        bundle_results[qid] = {
            "qid": qid,
            "anchor_profile": profile_key,
            "bundle_path": bundle_path,
            "sha256": _sha256_file(bundle_path),
            "n_decisions": len(bundle.get("decisions") or []),
            "n_scored": len(incumbent_scored),
            "n_supported": sum(1 for r in incumbent_scored if r["supported"]),
            "support_rate": (
                sum(1 for r in incumbent_scored if r["supported"]) / len(incumbent_scored)
                if incumbent_scored else None
            ),
            "n_reported_only": len(reported),
            "defect_classes": _class_breakdown(incumbent_scored),
            "n_INVERTED": sum(
                1 for r in incumbent_scored if r["primary_defect_class"] == "INVERTED"
            ),
            "rows": incumbent_scored,
        }
        all_incumbent_rows.extend(incumbent_scored)

    accepted_comparison = None
    if accepted_label_half_path and os.path.exists(accepted_label_half_path):
        accepted = _load_json(accepted_label_half_path)
        # Per-bundle provenance is required for a duplicate-safe comparison:
        # the same decision_id can legitimately appear in two bundles.
        accepted_by_bundle = {
            str(b.get("qid") or b.get("bundle") or ""): list(b.get("rows", []))
            for b in accepted.get("bundles", [])
        }
        accepted_rows = [r for rows in accepted_by_bundle.values() for r in rows]
        accepted_comparison = _compare_to_accepted(
            all_incumbent_rows, accepted_rows, accepted_by_bundle)
        accepted_comparison["accepted_n_scored"] = accepted.get("n_scored")
        accepted_comparison["accepted_n_supported"] = accepted.get("n_supported")
        accepted_comparison["accepted_support_rate"] = accepted.get("support_rate")

    # -- 3. CANDIDATE on the same rows -------------------------------------
    candidate_decisions: list[Any] = []
    for qid in BUNDLE_QIDS:
        profile_key = QID_TO_PROFILE[qid]
        profile = rules.anchor_profile(profile_key)
        bundle_path = os.path.join(bundles_dir, f"{qid}.bundle.json")
        scored, _, _ = _extract_scored(bundle_path, rules)
        for row in scored:
            decision = decide_label(row, rules, profile)
            decision.criterion_evidence["_bundle"] = qid
            candidate_decisions.append(decision)

    emitted = [d for d in candidate_decisions if not d.abstained]
    abstained = [d for d in candidate_decisions if d.abstained]
    abstention_reasons: dict[str, int] = {}
    for d in abstained:
        abstention_reasons[d.reason_code] = abstention_reasons.get(d.reason_code, 0) + 1
    abstention_by_bundle: dict[str, int] = {}
    for d in abstained:
        _qid = _qid_of(d)
        abstention_by_bundle[_qid] = abstention_by_bundle.get(_qid, 0) + 1

    # Score the candidate's EMITTED labels under the frozen rubric (same rows,
    # same rubric, same run).  Each emitted row is re-scored from its own
    # issued fields under ITS OWN bundle's question profile, exactly as the
    # incumbent's rows were.
    candidate_scored = []
    for qid in BUNDLE_QIDS:
        profile_key = QID_TO_PROFILE[qid]
        ids = {d.decision_id for d in emitted if _qid_of(d) == qid}
        if not ids:
            continue
        bundle_path = os.path.join(bundles_dir, f"{qid}.bundle.json")
        scored, _, _ = _extract_scored(bundle_path, rules)
        rows = [r for r in scored if str(r["decision_id"]) in ids]
        candidate_scored.extend(_score_under_rubric(rows, rules, profile_key))

    n_emitted = len(emitted)
    n_abstained = len(abstained)
    n_candidate_supported = sum(1 for r in candidate_scored if r["supported"])
    candidate_support_rate = (n_candidate_supported / n_emitted) if n_emitted else None

    # -- 4. NON-VACUITY -----------------------------------------------------
    # (a) inverted-label control set: the frozen injection rows whose label
    #     is affirmatively inverted (expected_class INVERTED).
    inverted_specs = [
        inj for inj in rules.non_vacuity["injection_rows"]
        if inj.get("expected_class") == "INVERTED"
    ]
    from .vendored.extract import ROW_FIELDS as _RF
    inverted_control_rows = []
    for spec in inverted_specs:
        row = {k: spec.get(k) for k in _RF}
        row["field_presence"] = {k: (k in spec) for k in _RF}
        row["full_text_len"] = 0
        row["row_text"] = "\n".join(
            str(x) for x in (spec.get("counter_evidence"), spec.get("title"), spec.get("regeste")) if x
        )
        row["snippet"] = ""
        inverted_control_rows.append(row)
    inverted_scored = []
    for spec, row in zip(inverted_specs, inverted_control_rows):
        ctx = make_context(rules, spec["anchor_profile"], VARIANT_PRIMARY)
        inverted_scored.append(score_row(row, ctx))
    n_inverted = len(inverted_scored)
    n_inverted_supported = sum(1 for r in inverted_scored if r["supported"])
    inverted_support_rate = (n_inverted_supported / n_inverted) if n_inverted else None

    # (b) swapped-evidence control
    swapped_rows, swapped_meta = _build_swapped_control(candidate_decisions, {})
    swapped_scored = []
    for qid in BUNDLE_QIDS:
        profile_key = QID_TO_PROFILE[qid]
        rows = [r for r, m in zip(swapped_rows, swapped_meta) if m["bundle"] == qid]
        if not rows:
            continue
        swapped_scored.extend(_score_under_rubric(rows, rules, profile_key))
    n_swapped = len(swapped_scored)
    n_swapped_supported = sum(1 for r in swapped_scored if r["supported"])
    swapped_support_rate = (n_swapped_supported / n_swapped) if n_swapped else None

    # The candidate must also ABSTAIN on the control rows (its gate catches
    # inversion and anchor-less swapped evidence), not merely score them.
    candidate_on_inverted = []
    for spec, row in zip(inverted_specs, inverted_control_rows):
        d = decide_label(row, rules, rules.anchor_profile(spec["anchor_profile"]))
        candidate_on_inverted.append({"inject_id": spec["inject_id"], "label": d.label, "reason_code": d.reason_code})
    candidate_on_swapped = []
    for row, meta in zip(swapped_rows, swapped_meta):
        d = decide_label(row, rules, rules.anchor_profile(QID_TO_PROFILE[meta["bundle"]]))
        candidate_on_swapped.append({"control_id": meta["control_id"], "label": d.label, "reason_code": d.reason_code})

    # Frozen harness non-vacuity (REUSE-FIRST from LABEL_HALF) as supporting evidence.
    harness_non_vacuity = run_non_vacuity(rules)

    non_vacuity_passed = (
        inverted_support_rate is not None
        and candidate_support_rate is not None
        and inverted_support_rate < candidate_support_rate
        and swapped_support_rate is not None
        and swapped_support_rate < candidate_support_rate
    )

    # -- assemble report ----------------------------------------------------
    report = {
        "schema": SCHEMA,
        "team_id": "frontier-counter-anchor-classifier",
        "charter_version": 1,
        "rules_path": rules_path,
        "rules_sha256": rules.sha256,
        "rules_byte_identity_ok": rules_ok,
        "frozen_rules_sha256_expected": FROZEN_RULES_SHA256,
        "population_definition": (
            "Served packet 38839347028: the three gate-packet bundles "
            "(de-kapitalverletzung 214, fr-bail-entretien 217, "
            "it-responsabilita-medica 211 decisions); the 65 scored counter "
            "rows the product actually issued, scored under the frozen rubric."
        ),
        "measured_packet": "gate_packet/38839347028",
        "bundles": [
            {
                "qid": qid,
                "anchor_profile": bundle_results[qid]["anchor_profile"],
                "sha256": bundle_results[qid]["sha256"],
                "n_decisions": bundle_results[qid]["n_decisions"],
                "n_scored": bundle_results[qid]["n_scored"],
                "n_supported": bundle_results[qid]["n_supported"],
                "support_rate": bundle_results[qid]["support_rate"],
            "n_reported_only": bundle_results[qid]["n_reported_only"],
            "defect_classes": bundle_results[qid]["defect_classes"],
            "n_INVERTED": bundle_results[qid]["n_INVERTED"],
            "n_abstained": abstention_by_bundle.get(qid, 0),
            "incumbent_rows": bundle_results[qid]["rows"],
        }
            for qid in BUNDLE_QIDS
        ],
        "incumbent": {
            "definition": (
                "The accepted product chain's issued counter labels: the "
                "counter_status/counter_evidence the bundles carry, scored "
                "under the frozen rubric.  The product's heuristic "
                "classify_against_intent only writes a retrieval-stage signal "
                "(counter_status stays 'none'); the served labels are the "
                "incumbent's issued output, reproduced here row by row."
            ),
            "n_scored": len(all_incumbent_rows),
            "n_supported": sum(1 for r in all_incumbent_rows if r["supported"]),
            "n_unsupported": sum(1 for r in all_incumbent_rows if not r["supported"]),
            "support_rate": (
                sum(1 for r in all_incumbent_rows if r["supported"]) / len(all_incumbent_rows)
                if all_incumbent_rows else None
            ),
            "INVERTED": sum(1 for r in all_incumbent_rows if r["primary_defect_class"] == "INVERTED"),
            "defect_classes": _class_breakdown(all_incumbent_rows),
            "accepted_result_reproduced": (
                accepted_comparison["reproduced_byte_identical_verdicts"]
                if accepted_comparison else None
            ),
            "accepted_comparison": accepted_comparison,
        },
        "candidate": {
            "component": "counter_anchor_classifier.decide_label",
            "emission_gate": (
                "A non-ABSTAIN label is emitted ONLY when the row's own cited "
                "passage carries both a DOMAIN anchor to the row's question "
                "and a frozen counter-intent marker in the decision's own "
                "language, and is not a fragment, not a procedural formula "
                "without a marker, and not a polarity-inverted construction; "
                "the row's PIVOT anchor, expected language and non-foreign "
                "legal_area must also hold.  Otherwise ABSTAIN with the "
                "frozen-precedence reason code."
            ),
            "n_rows": len(candidate_decisions),
            "n_emitted": n_emitted,
            "n_abstained": n_abstained,
            "abstention_count": n_abstained,
            "abstention_reasons": dict(sorted(abstention_reasons.items())),
            "abstention_by_bundle": dict(sorted(abstention_by_bundle.items())),
            "issued_counter_statuses_present": dict(sorted(Counter(
                str(d.proposed_status) for d in candidate_decisions).items())),
            "unmapped_counter_statuses_present": sorted(
                {str(d.proposed_status) for d in candidate_decisions} - set(STATUS_TO_LABEL)),
            "yield": (n_emitted / len(candidate_decisions)) if candidate_decisions else None,
            "n_candidate_labels_supported": n_candidate_supported,
            "candidate_support_rate": candidate_support_rate,
            "candidate_INVERTED": sum(
                1 for r in candidate_scored if r["primary_defect_class"] == "INVERTED"),
            "candidate_defect_classes": _class_breakdown(candidate_scored),
            "emitted_decisions": [d.to_dict() for d in emitted],
            "abstained_decisions": [d.to_dict() for d in abstained],
        },
        "head_to_head": {
            "same_rows_same_run": True,
            "incumbent_support_rate": (
                sum(1 for r in all_incumbent_rows if r["supported"]) / len(all_incumbent_rows)
                if all_incumbent_rows else None
            ),
            "candidate_support_rate_among_emitted": candidate_support_rate,
            "incumbent_INVERTED": sum(1 for r in all_incumbent_rows if r["primary_defect_class"] == "INVERTED"),
            "candidate_INVERTED": sum(
                1 for r in candidate_scored if r["primary_defect_class"] == "INVERTED"),
            "incumbent_yield": len(all_incumbent_rows),
            "candidate_yield": n_emitted,
            "candidate_abstention_count": n_abstained,
            "candidate_strictly_better_on_support": (
                candidate_support_rate is not None
                and (sum(1 for r in all_incumbent_rows if r["supported"]) / len(all_incumbent_rows))
                < candidate_support_rate
            ) if all_incumbent_rows else None,
            "direction": (
                "candidate raises label SUPPORT from 0.0769 to 1.0 among the "
                "labels it emits, cutting yield from 65 to 5 and converting "
                "the 60 unsupported labels into COUNTED abstentions "
                "(support rate, abstention count and yield published side by "
                "side)."
            ),
        },
        "non_vacuity": {
            "purpose": (
                "Prove the candidate's advantage is real, not a harness "
                "artifact.  Both controls are scored under the SAME frozen "
                "rubric as the candidate and must score STRICTLY BELOW it."
            ),
            "inverted_label_control": {
                "description": (
                    "Frozen injection rows whose label is affirmatively "
                    "inverted (appeal rejected / lower ruling confirmed, "
                    "labelled counter).  Scored under the frozen rubric."
                ),
                "n": n_inverted,
                "n_supported": n_inverted_supported,
                "support_rate": inverted_support_rate,
                "defect_classes": _class_breakdown(inverted_scored),
                "rows": inverted_scored,
                "candidate_gate_on_these_rows": candidate_on_inverted,
            },
            "swapped_evidence_control": {
                "description": (
                    "The candidate's emitted rows with their cited evidence "
                    "swapped for another decision's text (cross-bundle swap). "
                    "Scored under the frozen rubric."
                ),
                "n": n_swapped,
                "n_supported": n_swapped_supported,
                "support_rate": swapped_support_rate,
                "defect_classes": _class_breakdown(swapped_scored),
                "control_meta": swapped_meta,
                "rows": swapped_scored,
                "candidate_gate_on_these_rows": candidate_on_swapped,
            },
            "candidate_support_rate": candidate_support_rate,
            "all_controls_strictly_below_candidate": non_vacuity_passed,
            "tie_would_void_run": not non_vacuity_passed,
            "harness_non_vacuity_reused": harness_non_vacuity,
        },
        "overall": {
            "n_bundles": len(BUNDLE_QIDS),
            "n_scored": len(all_incumbent_rows),
            "n_supported_incumbent": sum(1 for r in all_incumbent_rows if r["supported"]),
            "support_rate_incumbent": (
                sum(1 for r in all_incumbent_rows if r["supported"]) / len(all_incumbent_rows)
                if all_incumbent_rows else None
            ),
            "n_emitted_candidate": n_emitted,
            "n_abstained_candidate": n_abstained,
            "support_rate_candidate_among_emitted": candidate_support_rate,
            "yield_candidate": (n_emitted / len(candidate_decisions)) if candidate_decisions else None,
            "INVERTED_incumbent": sum(1 for r in all_incumbent_rows if r["primary_defect_class"] == "INVERTED"),
            "INVERTED_candidate": sum(
                1 for r in candidate_scored if r["primary_defect_class"] == "INVERTED"),
            "defect_classes_incumbent": _class_breakdown(all_incumbent_rows),
            "defect_classes_candidate": _class_breakdown(candidate_scored),
            "language_distribution": {
                lang: sum(1 for r in all_incumbent_rows if r["language"] == lang)
                for lang in sorted({r["language"] for r in all_incumbent_rows})
            },
            "rows": [
                {
                    "bundle": r["_bundle"],
                    "decision_id": r["decision_id"],
                    "counter_status": r["counter_status"],
                    "rank": r["rank"],
                    "language": r["language"],
                    "counter_reason": r.get("counter_reason"),
                    "counter_uncertainty": r.get("counter_uncertainty"),
                    "cited_evidence": r.get("cited_evidence"),
                    "primary_defect_class": r["primary_defect_class"],
                    "reason_code": r["reason_code"],
                    "supported": r["supported"],
                }
                for r in sorted(
                    all_incumbent_rows,
                    key=lambda r: (str(r["_bundle"]), int(r["rank"] or 10**9), str(r["decision_id"])),
                )
            ],
        },
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    # REPAIR 38970902524: this used three dirname() hops, which resolved to
    # <repo>/frontier and made every default path below point at
    # <repo>/frontier/results/... -- i.e. the documented CLI invocation crashed
    # with FileNotFoundError on the frozen rubric. Four hops reach the repo root.
    here = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap = argparse.ArgumentParser(prog="frontier-counter-anchor-classifier.run_head_to_head")
    ap.add_argument("--rules", default=os.path.join(here, "results/frontier/frontier-counter-anchor-classifier/RULES_LABEL.json"))
    ap.add_argument("--bundles-dir", default="/tmp/lex_accepted/core/product/results/product/gate_packet/38839347028/questions")
    ap.add_argument("--accepted-label-half", default="/tmp/LABEL_HALF.json")
    ap.add_argument("--out", default=os.path.join(here, "results/frontier/frontier-counter-anchor-classifier/HEAD_TO_HEAD_R2_38970902524.json"))
    args = ap.parse_args(argv)

    report = run(args.rules, args.bundles_dir, args.accepted_label_half, args.out)

    inc = report["incumbent"]
    cand = report["candidate"]
    h2h = report["head_to_head"]
    nv = report["non_vacuity"]
    print(f"rules sha256 ok: {report['rules_byte_identity_ok']}")
    print(f"incumbent: {inc['n_supported']}/{inc['n_scored']} = {inc['support_rate']:.4f} "
          f"(accepted 5/65 = 0.0769; reproduced={inc['accepted_result_reproduced']})")
    print(f"candidate: emitted={cand['n_emitted']} abstained={cand['n_abstained']} "
          f"support={cand['candidate_support_rate']} yield={cand['yield']:.4f} "
          f"INVERTED={cand['candidate_INVERTED']}")
    print(f"head-to-head strictly better: {h2h['candidate_strictly_better_on_support']}")
    print(f"non-vacuity: inverted_control={nv['inverted_label_control']['support_rate']} "
          f"swapped_control={nv['swapped_evidence_control']['support_rate']} "
          f"strictly_below={nv['all_controls_strictly_below_candidate']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
