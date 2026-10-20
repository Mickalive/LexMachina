"""Compute the frozen scorer's absolute-bar status AS WRITTEN.

Never re-derives the bar or the required-minimum.  Reads the frozen rubric's
own ``verdict_rule`` / ``populations`` blocks and applies them literally.
``NOT_APPLICABLE`` and ``NOT_MEASURED`` are NEVER a pass.
"""

from __future__ import annotations

from typing import Any

#: Status vocabulary (frozen-rubric semantics, never invented here).
STATUS_LABEL_SOUND = "LABEL_SOUND"
STATUS_LABEL_UNSOUND = "LABEL_UNSOUND"
STATUS_INSUFFICIENT = "INSUFFICIENT_POPULATION"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
STATUS_NOT_MEASURED = "NOT_MEASURED"


def _required_min_population(rules_data: dict[str, Any]) -> int | None:
    """Read the required primary minimum from the frozen rubric, as written."""
    populations = rules_data.get("populations") or {}
    # The frozen rubric nests the primary minimum under populations.primary;
    # older spellings put it at the top level.  Read both deterministically.
    primary = populations.get("primary") if isinstance(populations.get("primary"), dict) else {}
    scopes = (primary, populations)
    for scope in scopes:
        for key in (
            "required_min_population_primary",
            "required_min_primary",
            "min_population_primary",
        ):
            if key in scope:
                try:
                    return int(scope[key])
                except (TypeError, ValueError):
                    pass
    vr = rules_data.get("verdict_rule") or {}
    # Parse the frozen INSUFFICIENT_POPULATION sentence as written.
    text = str(vr.get("INSUFFICIENT_POPULATION") or "")
    marker = "required_min_population_primary"
    if marker in text:
        import re
        m = re.search(marker + r"[^0-9]{0,20}([0-9]+)", text)
        if m:
            return int(m.group(1))
    return None


def compute_absolute_bar_status(
    emission_record: dict[str, Any],
    rules_data: dict[str, Any],
) -> dict[str, Any]:
    """Apply the frozen verdict_rule AS WRITTEN to one emission record.

    ``emission_record`` must carry ``n_scored``, ``n_emitted`` and
    ``support_rate_among_issued`` (from the accepted classifier).
    """
    n_scored = int(emission_record.get("n_scored") or 0)
    n_emitted = int(emission_record.get("n_emitted") or 0)
    support = float(emission_record.get("support_rate_among_issued") or 0.0)
    required = _required_min_population(rules_data)

    if n_scored == 0:
        status = STATUS_NOT_MEASURED
        reason = (
            "n_scored == 0: the accepted classifier received no scored "
            "proposal, so the frozen absolute-bar predicate has no population "
            "to evaluate.  NOT_MEASURED is never a pass."
        )
        satisfied = False
    elif required is None:
        status = STATUS_NOT_APPLICABLE
        reason = (
            "required_min_population_primary could not be read from the "
            "frozen rubric; NOT_APPLICABLE is never a pass."
        )
        satisfied = False
    elif n_scored < required:
        status = STATUS_INSUFFICIENT
        reason = (
            f"n_scored ({n_scored}) < required_min_population_primary "
            f"({required}); INSUFFICIENT_POPULATION is a NON-RESULT and is "
            "never a pass."
        )
        satisfied = False
    elif support >= 1.0 and n_emitted == n_scored:
        status = STATUS_LABEL_SOUND
        reason = (
            f"n_scored == required ({required}) and support_rate == 1.0 "
            f"({support}); every issued label is supported by its own cited "
            "evidence under criteria i-v."
        )
        satisfied = True
    else:
        status = STATUS_LABEL_UNSOUND
        reason = (
            f"n_scored == required ({required}) but support_rate "
            f"({support}) < 1.0; LABEL_UNSOUND."
        )
        satisfied = False

    return {
        "absolute_bar": 1.0,
        "required_min_population_primary": required,
        "n_scored": n_scored,
        "n_emitted": n_emitted,
        "support_rate_among_issued": support,
        "status": status,
        "satisfied": satisfied,
        "reason": reason,
        "as_written": True,
        "not_measured_never_a_pass": True,
        "not_applicable_never_a_pass": True,
    }


__all__ = [
    "STATUS_INSUFFICIENT",
    "STATUS_LABEL_SOUND",
    "STATUS_LABEL_UNSOUND",
    "STATUS_NOT_APPLICABLE",
    "STATUS_NOT_MEASURED",
    "compute_absolute_bar_status",
]
