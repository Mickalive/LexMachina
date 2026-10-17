"""Half (a): LABEL SUPPORT, independently recomputed with the frozen rubric.

Applies the ACCEPTED vendored frozen label rubric (RULES_LABEL.json via
label_gate / the vendored frontier_counter_label_integrity harness) to the
rebuilt packet's ISSUED counter rows. Publishes BOTH accepted label
instruments' verdicts side by side:
  * label_gate.py absolute status + population-pinned regression verdict
    (AS WRITTEN),
  * label_lineage_gate.py population-free regression verdict (AS WRITTEN).
NOT_APPLICABLE and NOT_MEASURED are never a pass. No threshold is re-derived.
"""
from __future__ import annotations

from pathlib import Path

from .paths import QIDS, bootstrap_vendored_instruments

bootstrap_vendored_instruments()

from evaluation.frozen_bars import label_gate  # noqa: E402
from evaluation.frozen_bars import label_lineage_gate  # noqa: E402
from evaluation.frozen_bars.vendored.frontier_counter_label_integrity.extract import (  # noqa: E402
    counter_rows,
    load_bundle,
)
from evaluation.frozen_bars.vendored.frontier_counter_label_integrity.rubric import (  # noqa: E402
    VARIANT_PRIMARY,
    make_context,
    score_row,
)
from evaluation.frozen_bars.vendored.frontier_counter_label_integrity.rules import (  # noqa: E402
    load_rules,
)

ABSTAIN_MARKER = "abstained_unevidenced"
RULES_LABEL_PATH = Path(label_gate.__file__).resolve().parent / "RULES_LABEL.json"


def _issued_and_abstained(bundle: dict, scored_statuses: set[str]) -> tuple[list, list, list]:
    decisions = bundle.get("decisions") or []
    issued = [d for d in decisions if (d.get("counter_status") or "none") in scored_statuses]
    abstained = [d for d in decisions if (d.get("counter_status") or "none") == ABSTAIN_MARKER]
    cited = [d for d in decisions if (d.get("counter_status") or "none") == "cited"]
    return issued, abstained, cited


def recompute_bundle(packet_questions: Path, qid: str) -> dict:
    """Independently recompute label support for one rebuilt anchor bundle."""
    rules = label_gate.load_frozen_rules(str(RULES_LABEL_PATH))
    bundle_path = packet_questions / f"{qid}.bundle.json"
    bundle = load_bundle(str(bundle_path))
    scored_statuses = list(rules.rubric["scored_statuses"])
    reported_statuses = list(rules.rubric["reported_separately_never_scored"])
    scored_rows, reported_rows = counter_rows(bundle, scored_statuses, reported_statuses)
    # counter_rows already partitions: scored_rows are exactly the ISSUED
    # counter rows (abstained_unevidenced and cited are excluded by status).
    _, abstained, _ = _issued_and_abstained(bundle, set(scored_statuses))
    ctx = make_context(rules, qid, VARIANT_PRIMARY)
    scored = [score_row(r, ctx) for r in scored_rows]
    n_supported = sum(1 for r in scored if r["supported"])
    n_scored = len(scored)
    classes: dict[str, int] = {}
    for r in scored:
        classes[r["primary_defect_class"]] = classes.get(r["primary_defect_class"], 0) + 1
    n_decisions = len(bundle.get("decisions") or [])
    denom = n_scored + len(abstained)
    return {
        "qid": qid,
        "bundle_path": str(bundle_path),
        "n_decisions": n_decisions,
        "n_scored_issued": n_scored,
        "n_supported_issued": n_supported,
        "support_rate_among_issued": (n_supported / n_scored) if n_scored else None,
        "n_abstained": len(abstained),
        "n_cited_placeholders": len(reported_rows),
        "yield_over_classifier_population": (n_scored / denom) if denom else None,
        "classifier_population_size": denom,
        "defect_class_counts": classes,
        "issued_rows": [
            {
                "decision_id": r["decision_id"],
                "rank": r["rank"],
                "language": r["language"],
                "counter_status": r["counter_status"],
                "supported": r["supported"],
                "primary_defect_class": r["primary_defect_class"],
                "reason_code": r["reason_code"],
            }
            for r in scored
        ],
    }


def score_with_accepted_label_gate(packet_questions: Path) -> dict:
    """The ACCEPTED label_gate.score_packet AS WRITTEN on the rebuilt bundles."""
    rules = label_gate.load_frozen_rules(str(RULES_LABEL_PATH))
    bundles = {qid: str(packet_questions / f"{qid}.bundle.json") for qid in QIDS}
    return label_gate.score_packet(bundles, rules)


def score_with_accepted_lineage_gate(packet_questions: Path) -> dict:
    """The ACCEPTED population-free label_lineage_gate AS WRITTEN."""
    rules = label_gate.load_frozen_rules(str(RULES_LABEL_PATH))
    bundles = {qid: str(packet_questions / f"{qid}.bundle.json") for qid in QIDS}
    result = label_lineage_gate.score_packet(bundles, rules)
    # Keep only the fields the charter requires side by side, plus the
    # explicit NOT_APPLICABLE / NOT_MEASURED is-not-a-pass guards.
    return {
        "gate": result.get("gate", "counter-label-support-lineage"),
        "lineage": result.get("lineage", result.get("regression_verdict") not in ("NOT_APPLICABLE",)),
        "n_scored": result.get("n_scored"),
        "n_supported": result.get("n_supported"),
        "support_rate": result.get("support_rate"),
        "enforced_predicate_rate": result.get("enforced_predicate_rate", label_lineage_gate.PREDICATE_RATE),
        "regression_verdict": result.get("regression_verdict"),
        "gate_blocks_build": result.get("gate_blocks_build"),
        "absolute_status": result.get("absolute_status"),
        "accepted_gate_side_by_side": result.get("accepted_gate_side_by_side"),
        "not_applicable_is_not_a_pass": True,
        "not_measured_is_not_a_pass": True,
        "threshold_re_derived": False,
    }


def measure(packet_questions: Path) -> dict:
    per_bundle = {qid: recompute_bundle(packet_questions, qid) for qid in QIDS}
    n_issued = sum(b["n_scored_issued"] for b in per_bundle.values())
    n_supported = sum(b["n_supported_issued"] for b in per_bundle.values())
    n_abstained = sum(b["n_abstained"] for b in per_bundle.values())
    n_cited = sum(b["n_cited_placeholders"] for b in per_bundle.values())
    classifier_pop = n_issued + n_abstained
    pooled_rate = (n_supported / n_issued) if n_issued else None
    absolute = score_with_accepted_label_gate(packet_questions)
    lineage = score_with_accepted_lineage_gate(packet_questions)
    return {
        "half": "a_label_support",
        "rules_label_sha256": absolute.get("rules_sha256"),
        "per_bundle": per_bundle,
        "pooled": {
            "n_issued": n_issued,
            "n_supported": n_supported,
            "support_rate_among_issued": pooled_rate,
            "n_abstained": n_abstained,
            "n_cited_placeholders": n_cited,
            "classifier_population_size": classifier_pop,
            "yield_over_classifier_population": (n_issued / classifier_pop) if classifier_pop else None,
        },
        "accepted_label_gate_as_written": {
            "absolute_bar": absolute.get("absolute_bar"),
            "absolute_status": absolute.get("absolute_status"),
            "absolute_enforced_as_build_blocker": absolute.get("absolute_enforced_as_build_blocker"),
            "n_scored": absolute.get("n_scored"),
            "n_supported": absolute.get("n_supported"),
            "support_rate": absolute.get("support_rate"),
            "classes": absolute.get("classes"),
            "lineage_matches_incumbent_population": absolute.get("lineage_matches_incumbent_population"),
            "regression_verdict": absolute.get("regression_verdict"),
            "gate_blocks_build": absolute.get("gate_blocks_build"),
            "not_applicable_is_not_a_pass": True,
        },
        "accepted_label_lineage_gate_as_written": lineage,
        "not_applicable_is_not_a_pass": True,
        "threshold_re_derived": False,
    }
