"""Non-vacuity: inject known defects and require the harness to flag them.

Charter acceptance test (8).  This tests the HARNESS, not the population: the
injected rows never enter a support rate, never enter the verdict, and never
satisfy the minimum-population requirement.  The injection manifest (rows,
expected classes, exact evidence strings, pass condition) lives in the frozen
RULES.json, so the test cannot be re-tuned after the population is scored.
"""

from __future__ import annotations

from typing import Any

from .extract import ROW_FIELDS
from .rubric import ALL_VARIANTS, VARIANT_LENIENT, VARIANT_PRIMARY, make_context, score_row
from .rules import FrozenRules

DEFECT_CRITERIA = ("INVERTED", "OFF-DOMAIN", "BOILERPLATE-ONLY", "FRAGMENT", "UNBACKED")


def _as_row(spec: dict[str, Any]) -> dict[str, Any]:
    row = {k: spec.get(k) for k in ROW_FIELDS}
    row["field_presence"] = {k: (k in spec) for k in ROW_FIELDS}
    row["full_text_len"] = 0
    row["row_text"] = "\n".join(
        str(x) for x in (spec.get("counter_evidence"), spec.get("title"), spec.get("regeste")) if x
    )
    row["snippet"] = ""
    return row


def run_non_vacuity(rules: FrozenRules) -> dict[str, Any]:
    spec = rules.non_vacuity
    min_criteria = int(spec["min_criteria_flagged"])
    cases: list[dict[str, Any]] = []
    exercised: set[str] = set()
    matched = 0

    for inj in spec["injection_rows"]:
        ctx = make_context(rules, inj["anchor_profile"], VARIANT_PRIMARY)
        result = score_row(_as_row(inj), ctx)
        got_class = result["primary_defect_class"]
        got_reason = result["reason_code"]
        ok = (got_class == inj["expected_class"]) and (got_reason == inj["expected_reason_code"])
        if inj["expected_class"] in DEFECT_CRITERIA and got_class == inj["expected_class"]:
            exercised.add(got_class)
        matched += int(ok)
        cases.append({
            "inject_id": inj["inject_id"],
            "decision_id": inj["decision_id"],
            "anchor_profile": inj["anchor_profile"],
            "counter_status": inj["counter_status"],
            "cited_evidence": inj["counter_evidence"],
            "expected_class": inj["expected_class"],
            "expected_reason_code": inj["expected_reason_code"],
            "observed_class": got_class,
            "observed_reason_code": got_reason,
            "pass": ok,
            "precedence_step_fired": result["precedence_step_fired"],
            "criterion_marks": {
                k: {"pass": v["pass"], "matches": v["matches"]} for k, v in result["criterion_marks"].items()
            },
            "defect_signals": result["defect_signals"],
        })

    # Sensitivity passes must also agree with the frozen expectations for the
    # primary pass, so a variant cannot quietly become the real rubric.
    variant_agreement: dict[str, int] = {}
    for variant in ALL_VARIANTS:
        if variant == VARIANT_PRIMARY:
            continue
        agree = 0
        for inj in spec["injection_rows"]:
            if variant == VARIANT_LENIENT and inj["expected_class"] == "OFF-DOMAIN":
                continue  # the variant removes exactly that criterion
            ctx = make_context(rules, inj["anchor_profile"], variant)
            res = score_row(_as_row(inj), ctx)
            agree += int(res["primary_defect_class"] == inj["expected_class"])
        variant_agreement[variant] = agree

    n_rows = len(spec["injection_rows"])
    passed = (
        matched == n_rows
        and len(exercised) >= min_criteria
        and all(
            variant_agreement[v] == sum(
                1 for inj in spec["injection_rows"]
                if not (v == VARIANT_LENIENT and inj["expected_class"] == "OFF-DOMAIN")
            )
            for v in variant_agreement
        )
    )

    return {
        "purpose": spec["purpose"],
        "min_criteria_flagged": min_criteria,
        "n_injected": n_rows,
        "n_expected_class_matched": matched,
        "n_defect_criteria_exercised": len(exercised),
        "defect_criteria_exercised": sorted(exercised),
        "variant_expected_class_agreement": dict(sorted(variant_agreement.items())),
        "passed": bool(passed),
        "population_impact": (
            "none: injected rows are scored in isolation and are excluded from every support rate, "
            "from the minimum-population count and from the verdict"
        ),
        "cases": sorted(cases, key=lambda c: c["inject_id"]),
    }