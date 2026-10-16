"""Counter-label-support gate: FROZEN RULES_LABEL.json, no new thresholds.

Scores any query_result_bundle (or a whole gate packet) with the frozen
counter-label support rubric via the byte-identical vendored harness. The
rules file sha256 is verified before anything is scored; a mismatch is an
environment error, never a product verdict.

GATE SEMANTICS (direction v50): FAIL only on REGRESSION BELOW THE RECOMPUTED
INCUMBENT (aggregate support below 5/65 on the served-packet lineage).
The absolute frozen bar (support_rate == 1.0) is REPORTED, not enforced.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_BAR_DIR = Path(__file__).resolve().parent
if str(_BAR_DIR.parent.parent) not in sys.path:
    sys.path.insert(0, str(_BAR_DIR.parent.parent))

from evaluation.frozen_bars.vendored.frontier_counter_label_integrity.extract import (  # noqa: E402
    counter_rows,
    load_bundle,
)
from evaluation.frozen_bars.vendored.frontier_counter_label_integrity.injection import (  # noqa: E402
    run_non_vacuity,
)
from evaluation.frozen_bars.vendored.frontier_counter_label_integrity.rubric import (  # noqa: E402
    VARIANT_PRIMARY,
    make_context,
    score_row,
)
from evaluation.frozen_bars.vendored.frontier_counter_label_integrity.rules import (  # noqa: E402
    load_rules,
)

RULES_LABEL_PATH = _BAR_DIR / "RULES_LABEL.json"
EXPECTED_RULES_SHA256 = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"

# Recomputed incumbent of record (direction v50): the accepted served-packet
# measurement LABEL_HALF.json, 65 scored rows = 25 de + 15 fr + 25 it.
INCUMBENT = {
    "n_scored": 65,
    "n_supported": 5,
    "classes": {"OFF-DOMAIN": 38, "UNBACKED": 22, "SUPPORTED": 5, "INVERTED": 0},
}
INCUMBENT_QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frozen_rules(rules_path: str | Path = RULES_LABEL_PATH):
    rules = load_rules(str(rules_path))
    if rules.sha256 != EXPECTED_RULES_SHA256:
        raise RuntimeError(
            f"RULES_LABEL sha256 mismatch: expected {EXPECTED_RULES_SHA256}, "
            f"observed {rules.sha256} from {rules_path}. "
            "Frozen bars are reused by re-hash, never re-derived; refusing to score."
        )
    return rules


def score_bundle(bundle_path: str | Path, rules, profile_key: str) -> dict:
    """Score one bundle under the frozen rubric (primary variant, decisive)."""
    bundle = load_bundle(str(bundle_path))
    scored_statuses = list(rules.rubric["scored_statuses"])
    reported_statuses = list(rules.rubric["reported_separately_never_scored"])
    scored_rows, reported_rows = counter_rows(bundle, scored_statuses, reported_statuses)
    ctx = make_context(rules, profile_key, VARIANT_PRIMARY)
    scored = [score_row(r, ctx) for r in scored_rows]
    classes: dict[str, int] = {}
    for r in scored:
        classes[r["primary_defect_class"]] = classes.get(r["primary_defect_class"], 0) + 1
    n_supported = sum(1 for r in scored if r["supported"])
    return {
        "bundle_path": str(bundle_path),
        "sha256": sha256_file(bundle_path),
        "anchor_profile": profile_key,
        "n_decisions": len(bundle.get("decisions") or []),
        "n_scored": len(scored),
        "n_reported_only": len(reported_rows),
        "n_supported": n_supported,
        "support_rate": (n_supported / len(scored)) if scored else None,
        "classes": classes,
        "rows": [
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


def score_packet(bundles: dict[str, str], rules) -> dict:
    """Score a {qid: bundle_path} packet; profile key == qid (frozen anchors).

    Qids without a frozen anchor profile are refused with an actionable
    ValueError (mirroring geometry_gate's lexicon refusal) instead of
    leaking a raw KeyError: the gates never invent anchor profiles for
    qids the frozen RULES_LABEL.json does not define. Admitting a genuinely
    new packet requires a disclosed rules re-freeze.
    """
    known_anchors = set(rules.anchors)
    unknown = [qid for qid in bundles if qid not in known_anchors]
    if unknown:
        raise ValueError(
            f"no frozen anchor profile for bundle(s) {unknown!r}; refusing to invent one "
            "(admitting a new packet requires a disclosed RULES_LABEL re-freeze)"
        )
    per_bundle = {qid: score_bundle(path, rules, qid) for qid, path in bundles.items()}
    n_scored = sum(b["n_scored"] for b in per_bundle.values())
    n_supported = sum(b["n_supported"] for b in per_bundle.values())
    classes: dict[str, int] = {}
    for b in per_bundle.values():
        for k, v in b["classes"].items():
            classes[k] = classes.get(k, 0) + v
    support_rate = (n_supported / n_scored) if n_scored else None
    # Absolute frozen bar (verdict_rule LABEL_SOUND): reported, NOT enforced.
    absolute_bar = 1.0
    absolute_status = (
        "LABEL_SOUND" if (n_scored and n_supported == n_scored) else "LABEL_UNSOUND"
    )
    # Regression comparison: applies to the served-packet lineage only
    # (the three served qids at the incumbent population size). Anything else
    # is reported without a regression verdict.
    lineage = set(per_bundle) == set(INCUMBENT_QIDS) and n_scored == INCUMBENT["n_scored"]
    if lineage:
        regressed = n_supported < INCUMBENT["n_supported"]
        regression_verdict = "FAIL_REGRESSION" if regressed else "PASS_NO_REGRESSION"
    else:
        regressed = False
        regression_verdict = "NOT_APPLICABLE"
    out: dict = {
        "gate": "counter-label-support",
        "rules_sha256": rules.sha256,
        "absolute_bar": absolute_bar,
        "absolute_status": absolute_status,
        "absolute_enforced_as_build_blocker": False,
        "n_scored": n_scored,
        "n_supported": n_supported,
        "support_rate": support_rate,
        "classes": classes,
        "incumbent": dict(INCUMBENT),
        "lineage_matches_incumbent_population": lineage,
        "regression_verdict": regression_verdict,
        "gate_blocks_build": bool(lineage and regressed),
        "per_bundle": per_bundle,
    }
    return out


def non_vacuity_control(rules) -> dict:
    """Proven non-vacuity: the frozen injection battery (lives in RULES_LABEL).

    Returns the vendored run_non_vacuity verdict verbatim plus an explicit
    gate-level reading: the harness must flag the injected defects, otherwise
    the support rate above would be vacuous.
    """
    result = run_non_vacuity(rules)
    cases = result.get("cases", [])
    n_pass = sum(1 for c in cases if c.get("pass"))
    return {
        "control": "frozen injection battery from RULES_LABEL.non_vacuity",
        "n_cases": len(cases),
        "n_cases_pass": n_pass,
        "exercised_classes": result.get("defect_criteria_exercised", []),
        "min_criteria_flagged_required": result.get("min_criteria_flagged"),
        "proven_non_vacuous": bool(result.get("passed", False)),
        "vendored_result": result,
    }
