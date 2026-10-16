"""Aggregate per-row verdicts into the pre-registered population report.

Deterministic by construction: every collection is built from sorted rows and
emitted with sorted keys; nothing reads the clock, the network or the
environment.  The report embeds ``rules_sha256`` and the sha256 of every input
so a reader can re-hash and byte-compare.
"""

from __future__ import annotations

from typing import Any, Iterable

from .extract import bundle_facts, counter_rows, load_bundle, sha256_file
from .rubric import ALL_VARIANTS, VARIANT_PRIMARY, make_context, score_row
from .rules import FrozenRules

DEFECT_CLASSES = ("INVERTED", "OFF-DOMAIN", "BOILERPLATE-ONLY", "FRAGMENT", "UNBACKED", "SUPPORTED")

TOP_N_CONVENTIONAL = 20


def score_bundle(rules: FrozenRules, path: str, *, verify_hash: bool = True) -> dict[str, Any]:
    """Score every counter label in one bundle under all three variants."""
    relpath = _relpath_from_path(path)
    entry = rules.input_by_relpath(relpath)
    if entry is None:
        # A copy of a frozen input at an unregistered path is refused too: the
        # bytes may be a stale checkout of the same artifact.
        digest = sha256_file(path)
        same_bytes = [e["relpath_under_results_product"] for e in rules.data["inputs"]
                      if e["sha256"] == digest]
        if same_bytes:
            raise ValueError(
                f"input sha256 drift: {path} has the frozen bytes of {same_bytes[0]} but is not "
                "the frozen input path; refusing to score an unregistered copy"
            )
        raise ValueError(f"bundle is not a frozen input of RULES.json: {path}")
    digest = sha256_file(path)
    if verify_hash and digest != entry["sha256"]:
        raise ValueError(
            f"input sha256 drift for {path}: frozen {entry['sha256']} observed {digest}"
        )

    bundle = load_bundle(path)
    scored_statuses = list(rules.rubric["scored_statuses"])
    reported_statuses = list(rules.rubric["reported_separately_never_scored"])
    scored_rows, reported_rows = counter_rows(bundle, scored_statuses, reported_statuses)

    profile_key = entry["anchor_profile"]
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for variant in ALL_VARIANTS:
        ctx = make_context(rules, profile_key, variant)
        by_variant[variant] = [score_row(r, ctx) for r in scored_rows]

    primary = by_variant[VARIANT_PRIMARY]
    return {
        "relpath_under_results_product": entry["relpath_under_results_product"],
        "population": entry["population"],
        "qid": entry["qid"],
        "anchor_profile": profile_key,
        "sha256": digest,
        "sha256_matches_frozen": digest == entry["sha256"],
        "content_sha256": entry.get("content_sha256"),
        "admissible": entry.get("admissible"),
        "admissibility_findings": entry.get("admissibility_findings"),
        "fixture_mode": entry.get("fixture_mode"),
        "facts": bundle_facts(bundle),
        "n_scored": len(primary),
        "n_reported_only": len(reported_rows),
        "reported_only_rows": [
            {
                "decision_id": r["decision_id"],
                "rank": r["rank"],
                "language": r["language"],
                "counter_status": r["counter_status"],
                "counter_evidence": r["counter_evidence"],
                "counter_uncertainty": r["counter_uncertainty"],
            }
            for r in reported_rows
        ],
        "rows": primary,
        "rows_by_variant": by_variant,
    }


def _relpath_from_path(path: str) -> str:
    norm = path.replace("\\", "/")
    marker = "results/product/"
    idx = norm.rfind(marker)
    if idx >= 0:
        return norm[idx + len(marker) :]
    return norm


def _class_breakdown(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for cls in DEFECT_CLASSES:
        ids = sorted(str(r["decision_id"]) for r in rows if r["primary_defect_class"] == cls)
        out[cls] = {"count": len(ids), "row_ids": ids}
    return out


def _signal_breakdown(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    signals = sorted({s for r in rows for s in r["defect_signals"]})
    out = {}
    for sig in signals:
        ids = sorted(str(r["decision_id"]) for r in rows if sig in r["defect_signals"])
        out[sig] = {"count": len(ids), "row_ids": ids}
    return out


def _criterion_breakdown(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    out = {}
    for key in ("i", "ii", "iii", "iv", "v"):
        failed = sorted(str(r["decision_id"]) for r in rows if not r["criterion_marks"][key]["pass"])
        out[key] = {
            "criterion": rows[0]["criterion_marks"][key]["criterion"] if rows else None,
            "n_failed": len(failed),
            "row_ids": failed,
        }
    return out


def _population_summary(bundles: list[dict[str, Any]], population: str) -> dict[str, Any]:
    sel = [b for b in bundles if b["population"] == population]
    rows: list[dict[str, Any]] = []
    for b in sorted(sel, key=lambda x: x["relpath_under_results_product"]):
        for r in b["rows"]:
            rows.append({**r, "bundle": b["relpath_under_results_product"], "qid": b["qid"],
                         "population": b["population"]})
    rows.sort(key=lambda r: (str(r["bundle"]), int(r["rank"] or 10**9), str(r["decision_id"])))

    n = len(rows)
    supported = [r for r in rows if r["supported"]]
    unsupported = [r for r in rows if not r["supported"]]
    rate = (len(supported) / n) if n else None

    lang: dict[str, int] = {}
    for r in rows:
        lang[r["language"]] = lang.get(r["language"], 0) + 1
    status: dict[str, int] = {}
    for r in rows:
        status[r["counter_status"]] = status.get(r["counter_status"], 0) + 1

    supported_outside_top_n = sorted(
        str(r["decision_id"]) for r in supported if int(r["rank"] or 0) > TOP_N_CONVENTIONAL
    )
    all_ranks = sorted(int(r["rank"] or 0) for r in rows)
    uncertainties = sorted(float(r["counter_uncertainty"]) for r in rows if r["counter_uncertainty"] is not None)

    marker_precision = {
        "rows_with_counter_markers_field": sum(
            1 for r in rows if r["markers_precision"]["reported_field_present"]
        ),
        "rows_with_marker_list": sum(1 for r in rows if r["markers_precision"]["n_reported"]),
        "rows_with_any_marker_in_cited_evidence": sum(
            1 for r in rows if r["markers_precision"]["n_in_cited_evidence"]
        ),
        "rows_with_marker_document_wide_only": sum(
            1 for r in rows if r["markers_precision"]["document_wide_only_markers"]
        ),
        "rows_with_full_text_available": sum(1 for r in rows if (r["full_text_len"] or 0) > 0),
        "document_wide_only_markers_by_row": {
            str(r["decision_id"]): r["markers_precision"]["document_wide_only_markers"]
            for r in rows
            if r["markers_precision"]["document_wide_only_markers"]
        },
        "note": (
            "The accepted bundle contract emits no counter_markers field on any counter row, so "
            "'markers reported' is unreported at accepted head. The document-wide-only column is "
            "the measurable proxy for the audited scope defect: markers that exist somewhere in "
            "the row's own text but NOT in the sentence the label cites."
        ),
    }

    return {
        "population": population,
        "n_bundles": len(sel),
        "bundles": sorted(b["relpath_under_results_product"] for b in sel),
        "n_scored": n,
        "n_supported": len(supported),
        "n_unsupported": len(unsupported),
        "support_rate": rate,
        "supported_row_ids": sorted(str(r["decision_id"]) for r in supported),
        "unsupported_row_ids": sorted(str(r["decision_id"]) for r in unsupported),
        "defect_classes": _class_breakdown(rows),
        "defect_signals": _signal_breakdown(rows),
        "criterion_failures": _criterion_breakdown(rows),
        "language_distribution": dict(sorted(lang.items())),
        "counter_status_distribution": dict(sorted(status.items())),
        "rank_distribution": {
            "ranks": all_ranks,
            "min": all_ranks[0] if all_ranks else None,
            "max": all_ranks[-1] if all_ranks else None,
            "supported_ranks": sorted(int(r["rank"] or 0) for r in supported),
            "n_supported_outside_top20": len(supported_outside_top_n),
            "supported_outside_top20_row_ids": supported_outside_top_n,
            "conventional_top_n": TOP_N_CONVENTIONAL,
        },
        "uncertainty": {
            "values": uncertainties,
            "min": uncertainties[0] if uncertainties else None,
            "max": uncertainties[-1] if uncertainties else None,
            "unsupported_with_uncertainty_at_or_above_0_95": sorted(
                str(r["decision_id"]) for r in unsupported if float(r["counter_uncertainty"] or 0) >= 0.95
            ),
            "unsupported_with_lowest_uncertainty_in_its_bundle": sorted(
                str(r["decision_id"]) for b in sel
                for r in b["rows"]
                if not r["supported"]
                and b["rows"]
                and float(r["counter_uncertainty"] or 2) == min(
                    float(x["counter_uncertainty"] or 2) for x in b["rows"] if x["counter_uncertainty"] is not None
                )
            ),
        },
        "marker_precision": marker_precision,
        "evidence": {
            "n_empty_cited_evidence": sum(1 for r in rows if r["cited_evidence_empty"]),
            "n_counter_evidence_field_absent": sum(1 for r in rows if not r["cited_evidence_field_present"]),
            "n_counter_evidence_verified_flag_present": sum(
                1 for r in rows if r["counter_evidence_verified_field_present"]
            ),
            "n_counter_evidence_verified_flag_true": sum(
                1 for r in rows if r["counter_evidence_verified"] is True
            ),
            "n_evidence_verbatim_in_row_text": sum(
                1 for r in rows if r["evidence_verbatim_in_row_text"] is True
            ),
            "n_evidence_verbatim_checkable": sum(
                1 for r in rows if r["evidence_verbatim_in_row_text"] is not None
            ),
            "n_rows_without_full_text": sum(1 for r in rows if not (r["full_text_len"] or 0)),
        },
        "rows": [
            {
                "bundle": r["bundle"],
                "qid": r["qid"],
                "decision_id": r["decision_id"],
                "counter_status": r["counter_status"],
                "rank": r["rank"],
                "language": r["language"],
                "counter_reason": r["counter_reason"],
                "counter_confidence": r["counter_confidence"],
                "counter_uncertainty": r["counter_uncertainty"],
                "cited_evidence": r["cited_evidence"],
                "primary_defect_class": r["primary_defect_class"],
                "reason_code": r["reason_code"],
                "defect_signals": r["defect_signals"],
                "precedence_step_fired": r["precedence_step_fired"],
                "criterion_marks": {k: v["pass"] for k, v in r["criterion_marks"].items()},
            }
            for r in rows
        ],
    }


def _verdict(rules: FrozenRules, primary: dict[str, Any], secondary: dict[str, Any],
             non_vacuity: dict[str, Any], coverage_ok: bool) -> dict[str, Any]:
    rule = rules.verdict_rule
    required = int(rules.data["populations"]["primary"]["required_min_population_primary"])
    n = primary["n_scored"]
    expected_ids = sorted(
        did
        for qid, statuses in rules.data["populations"]["primary"]["expected_rows"].items()
        for status, ids in statuses.items()
        if status in rules.rubric["scored_statuses"]
        for did in ids
    )
    observed_ids = sorted(primary["supported_row_ids"] + primary["unsupported_row_ids"])

    gaps: list[str] = []
    if n < required:
        gaps.append(f"scored {n} of the required {required} primary labelled rows")
    if sorted(set(expected_ids) - set(observed_ids)):
        gaps.append("primary rows missing from the scored population: "
                    + ",".join(sorted(set(expected_ids) - set(observed_ids))))
    if not coverage_ok:
        gaps.append("coverage rule (>=3 bundles, >=1 pre-repair) not satisfied")
    if not non_vacuity["passed"]:
        gaps.append("non-vacuity did not pass; the harness verdict is withheld")

    if gaps:
        verdict = "INSUFFICIENT_POPULATION"
    elif primary["n_supported"] == n and n > 0:
        verdict = "LABEL_SOUND"
    else:
        verdict = "LABEL_UNSOUND"

    sec_n = secondary["n_scored"]
    secondary_verdict = None
    if sec_n:
        secondary_verdict = "LABEL_SOUND" if secondary["n_supported"] == sec_n else "LABEL_UNSOUND"

    return {
        "verdict": verdict,
        "verdict_classes_available": list(rule["verdict_classes"]),
        "deciding_population": rule["deciding_population"],
        "threshold_support_rate_sound": rule["threshold_support_rate_sound"],
        "support_rate_primary": primary["support_rate"],
        "support_rate_secondary": secondary["support_rate"] if sec_n else None,
        "secondary_verdict_replication": secondary_verdict,
        "secondary_agrees_with_primary": (
            None if secondary_verdict is None else (secondary_verdict == verdict)
        ),
        "required_min_population_primary": required,
        "n_scored_primary": n,
        "non_vacuity_passed": non_vacuity["passed"],
        "gaps": gaps,
        "aggregation": rule["aggregation"],
        "insufficient_population_is_non_result": (
            "INSUFFICIENT_POPULATION is a NON-RESULT. It must not be read as LABEL_SOUND and must "
            "not be read as a pass of any product fix."
        ),
    }


def build_report(rules: FrozenRules, bundle_paths: list[str], non_vacuity: dict[str, Any]) -> dict[str, Any]:
    bundles = [score_bundle(rules, p) for p in sorted(bundle_paths)]
    primary = _population_summary(bundles, "primary")
    secondary = _population_summary(bundles, "secondary")

    n_primary_bundles = primary["n_bundles"]
    all_pre_repair = all(
        not rules.data["post_repair_probe"]["adversarial_retrieval_results_dir_exists"] for _ in bundles
    )
    coverage_ok = n_primary_bundles >= int(rules.data["coverage_rule"]["min_bundles"]) and (
        n_primary_bundles >= int(rules.data["coverage_rule"]["min_pre_repair_bundles"])
    )
    verdict = _verdict(rules, primary, secondary, non_vacuity, coverage_ok)

    variants = {}
    for variant in ALL_VARIANTS:
        rows: list[dict[str, Any]] = []
        for b in sorted(bundles, key=lambda x: x["relpath_under_results_product"]):
            if b["population"] != "primary":
                continue
            for r in b["rows_by_variant"][variant]:
                rows.append({**r, "bundle": b["relpath_under_results_product"]})
        rows.sort(key=lambda r: (str(r["bundle"]), int(r["rank"] or 10**9), str(r["decision_id"])))
        sup = [r for r in rows if r["supported"]]
        variants[variant] = {
            "n_scored": len(rows),
            "n_supported": len(sup),
            "support_rate": (len(sup) / len(rows)) if rows else None,
            "defect_classes": _class_breakdown(rows),
            "row_class_map": {
                str(r["decision_id"]): r["primary_defect_class"] for r in rows
            },
        }

    population_drift = []
    frozen_primary = rules.data["populations"]["primary"]["expected_rows"]
    for qid, statuses in sorted(frozen_primary.items()):
        for status, ids in sorted(statuses.items()):
            if status not in rules.rubric["scored_statuses"]:
                continue
            present = [r for r in primary["rows"] if r["qid"] == qid]
            observed = sorted(str(r["decision_id"]) for r in present)
            if sorted(ids) != observed:
                population_drift.append({
                    "qid": qid, "status": status, "frozen_expected": sorted(ids), "observed": observed,
                })

    inputs_digest = {
        b["relpath_under_results_product"]: b["sha256"] for b in sorted(
            bundles, key=lambda x: x["relpath_under_results_product"]
        )
    }

    report = {
        "schema": "frontier-counter-label-integrity/report/1",
        "team_id": rules.data["team_id"],
        "charter_version": rules.data["charter_version"],
        "rules_sha256": rules.sha256,
        "input_sha256": inputs_digest,
        "all_inputs_match_frozen_sha256": all(b["sha256_matches_frozen"] for b in bundles),
        "verdict": verdict,
        "claim_ceiling": rules.data["authority"]["claim_ceiling"],
        "authority": rules.data["authority"],
        "populations": {"primary": primary, "secondary": secondary},
        "bundles": [
            {
                "relpath_under_results_product": b["relpath_under_results_product"],
                "qid": b["qid"],
                "population": b["population"],
                "anchor_profile": b["anchor_profile"],
                "sha256": b["sha256"],
                "content_sha256": b.get("content_sha256"),
                "admissible": b.get("admissible"),
                "fixture_mode": b.get("fixture_mode"),
                "n_decisions": b["facts"]["n_decisions"],
                "n_scored": b["n_scored"],
                "n_reported_only": b["n_reported_only"],
                "reported_only_rows": b["reported_only_rows"],
                "support_rate": (
                    (sum(1 for r in b["rows"] if r["supported"]) / b["n_scored"]) if b["n_scored"] else None
                ),
                "defect_classes": _class_breakdown(b["rows"]),
                "language_distribution": {
                    lang: sum(1 for r in b["rows"] if r["language"] == lang)
                    for lang in sorted({r["language"] for r in b["rows"]})
                },
                "ranks": sorted(int(r["rank"] or 0) for r in b["rows"]),
                "query": b["facts"]["query"],
                "answer_method": b["facts"]["answer_method"],
                "answer_status": b["facts"]["answer_status"],
                "answer_cited_decision_ids": b["facts"]["answer_cited_decision_ids"],
                "rows": [
                    {
                        "decision_id": r["decision_id"],
                        "counter_status": r["counter_status"],
                        "rank": r["rank"],
                        "language": r["language"],
                        "counter_reason": r["counter_reason"],
                        "counter_confidence": r["counter_confidence"],
                        "counter_uncertainty": r["counter_uncertainty"],
                        "title": r["title"],
                        "regeste": r["regeste"],
                        "cited_evidence": r["cited_evidence"],
                        "primary_defect_class": r["primary_defect_class"],
                        "reason_code": r["reason_code"],
                        "defect_signals": r["defect_signals"],
                        "criterion_marks": {k: v["pass"] for k, v in r["criterion_marks"].items()},
                        "criterion_matches": {k: v["matches"] for k, v in r["criterion_marks"].items()},
                        "evidence_verbatim_in_row_text": r["evidence_verbatim_in_row_text"],
                        "markers_precision": r["markers_precision"],
                        "counter_evidence_verified_field_present": r["counter_evidence_verified_field_present"],
                        "counter_evidence_verified": r["counter_evidence_verified"],
                    }
                    for r in b["rows"]
                ],
            }
            for b in sorted(bundles, key=lambda x: x["relpath_under_results_product"])
        ],
        "sensitivity_variants": variants,
        "non_vacuity": non_vacuity,
        "coverage": {
            "n_bundles_scored": len(bundles),
            "n_primary_bundles": n_primary_bundles,
            "min_bundles_required": rules.data["coverage_rule"]["min_bundles"],
            "min_pre_repair_required": rules.data["coverage_rule"]["min_pre_repair_bundles"],
            "every_scored_bundle_is_pre_repair": all_pre_repair,
            "post_repair_artifact": rules.data["post_repair_probe"],
            "before_after_pair": None,
            "before_after_note": (
                "No post-repair artifact exists on the accepted mount (no "
                "results/product/adversarial_retrieval/, no product/query/adversarial_retrieval.py). "
                "Only a pre-repair baseline is reported. No baseline is presented as a "
                "post-repair result, and the audited 38828034436 figures are mechanism evidence "
                "only, never an accepted-chain support rate."
            ),
        },
        "population_drift": population_drift,
        "pre_scoring_drift_at_freeze": rules.data["pre_scoring_drift"],
        "charter_claims_checked_at_freeze": rules.data["charter_claims_checked_at_freeze"],
        "write_scope": rules.data["write_scope"],
        "limitations": [
            "The verdict is about the SUPPORT of the labels as issued, not about whether any "
            "specific decision is in fact supporting, contrary or limiting.",
            "The PIVOT-anchor operationalisation of criterion (v) is an authored interpretation; "
            "the lenient-domain-only sensitivity variant bounds it and is reported alongside.",
            "Where the accepted row carries no full_text, the verbatim citation check falls back to "
            "the row's regeste/title/snippet and is reported as such.",
            "counter_markers is absent from every accepted counter row, so the product's reported "
            "marker precision cannot be measured on the accepted chain; the document-wide-only "
            "marker column is the measurable proxy.",
            "Scored labels are the product's. This team proposes no lexicon, no threshold, no prompt "
            "and no patch, and did not test any fix.",
        ],
    }
    return report