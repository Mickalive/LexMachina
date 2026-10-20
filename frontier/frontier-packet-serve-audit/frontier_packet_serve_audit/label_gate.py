"""Label-support gate: FROZEN RULES_LABEL.json applied BYTE-IDENTICALLY.

The scoring itself is the vendored accepted rubric (vendor_label/). This
module adds the packet-level aggregation the charter requires: support among
ISSUED, the abstention count, the yield over the row population, the frozen
scorer's absolute/regression status AS WRITTEN, and the accepted
population-free label_lineage_gate verdict published BESIDE it.

No threshold is re-derived here. The absolute bar (support_rate == 1.0) and
the regression predicate are the frozen scorer's own, applied as written.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_TEAM_ROOT = Path(__file__).resolve().parents[1]
if str(_TEAM_ROOT) not in sys.path:
    sys.path.insert(0, str(_TEAM_ROOT))

from frontier_packet_serve_audit.vendor_label.extract import counter_rows, load_bundle  # noqa: E402
from frontier_packet_serve_audit.vendor_label.rules import FrozenRules, load_rules  # noqa: E402
from frontier_packet_serve_audit.vendor_label.rubric import VARIANT_PRIMARY, make_context, score_row  # noqa: E402

RULES_LABEL_SHA256 = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"

# Recomputed incumbent of record (direction v50), from the accepted verdict
# contract: the accepted served-packet measurement on packet 38839347028.
# NOT this packet's population. Used only for the regression comparison.
INCUMBENT = {"n_scored": 65, "n_supported": 5,
             "classes": {"OFF-DOMAIN": 38, "UNBACKED": 22, "SUPPORTED": 5, "INVERTED": 0}}
INCUMBENT_QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frozen_rules(rules_path: str | Path) -> FrozenRules:
    rules = load_rules(str(rules_path))
    if rules.sha256 != RULES_LABEL_SHA256:
        raise RuntimeError(
            f"RULES_LABEL sha256 mismatch: expected {RULES_LABEL_SHA256}, "
            f"observed {rules.sha256}. Frozen rules are reused by re-hash, "
            "never re-derived; refusing to score."
        )
    return rules


def score_bundle(bundle_path: str | Path, rules: FrozenRules, profile_key: str) -> dict:
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
    n_decisions = len(bundle.get("decisions") or [])
    # Abstention accounting: 'none' rows carry no counter label and are
    # descriptive row-status context, NOT abstentions. 'abstained_unevidenced'
    # is the disclosed abstention marker if present. 'cited' is a NON_QUOTE_REF
    # placeholder, reported separately, never scored and never an abstention.
    # The abstention_count is taken from the packet's committed disclosures
    # (see score_packet); the status_counts below are descriptive only.
    from collections import Counter
    status_counts = Counter(d.get("counter_status") for d in (bundle.get("decisions") or []))
    n_none_rows = int(status_counts.get("none", 0))
    n_abstained_marker = int(status_counts.get("abstained_unevidenced", 0))
    return {
        "bundle_path": str(bundle_path),
        "sha256": sha256_file(bundle_path),
        "anchor_profile": profile_key,
        "n_decisions": n_decisions,
        "n_scored": len(scored),
        "n_reported_only": len(reported_rows),
        "n_abstain": n_abstained_marker + n_none_rows,  # fallback only; see score_packet
        "n_none_rows_descriptive": n_none_rows,
        "yield_over_population": (n_supported / n_decisions) if n_decisions else 0.0,
        "n_supported": n_supported,
        "support_rate": (n_supported / len(scored)) if scored else None,
        "status_counts": dict(sorted(status_counts.items())),
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


def score_packet(bundles: dict[str, str], rules: FrozenRules,
                 abstain_by_qid: dict[str, int] | None = None) -> dict:
    """Score a {qid: bundle_path} packet; profile key == qid (frozen anchors).

    abstain_by_qid: the packet's OWN committed disclosures
    (disclosures.json per_bundle.<qid>.counter_anchor.n_abstained) -- the
    frozen metric definition's abstention count. When supplied it overrides
    the bundle-status fallback in score_bundle and the source is recorded;
    when omitted the fallback counts 'none' + 'abstained_unevidenced' rows
    and says so explicitly (never silently).
    """
    known_anchors = set(rules.anchors)
    unknown = [qid for qid in bundles if qid not in known_anchors]
    if unknown:
        raise ValueError(
            f"no frozen anchor profile for bundle(s) {unknown!r}; refusing to invent one"
        )
    per_bundle = {qid: score_bundle(path, rules, qid) for qid, path in bundles.items()}
    n_scored = sum(b["n_scored"] for b in per_bundle.values())
    n_supported = sum(b["n_supported"] for b in per_bundle.values())
    n_decisions = sum(b["n_decisions"] for b in per_bundle.values())
    if abstain_by_qid is not None:
        missing = [qid for qid in per_bundle if qid not in abstain_by_qid]
        if missing:
            raise ValueError(f"no disclosed abstention count for bundle(s) {missing!r}")
        n_abstain = sum(int(abstain_by_qid[qid]) for qid in per_bundle)
        abstention_source = ("packet disclosures.json per_bundle.counter_anchor.n_abstained "
                             "(frozen RULES.json metric definition: abstention_count)")
    else:
        n_abstain = sum(b["n_abstain"] for b in per_bundle.values())
        abstention_source = ("fallback: bundle status_counts of counter_status 'none' + "
                             "'abstained_unevidenced' rows (descriptions only; the packet's "
                             "disclosures were not supplied)")
    classes: dict[str, int] = {}
    for b in per_bundle.values():
        for k, v in b["classes"].items():
            classes[k] = classes.get(k, 0) + v
    support_rate = (n_supported / n_scored) if n_scored else None
    # Absolute frozen bar AS WRITTEN (LABEL_SOUND): reported, NOT enforced.
    absolute_status = (
        "LABEL_SOUND" if (n_scored and n_supported == n_scored) else "LABEL_UNSOUND"
    )
    # Regression predicate AS WRITTEN (population-pinned to the 65-row incumbent).
    lineage = set(per_bundle) == set(INCUMBENT_QIDS) and n_scored == INCUMBENT["n_scored"]
    if lineage:
        regressed = n_supported < INCUMBENT["n_supported"]
        regression_verdict = "FAIL_REGRESSION" if regressed else "PASS_NO_REGRESSION"
    else:
        regressed = False
        regression_verdict = "NOT_APPLICABLE"
    return {
        "gate": "counter-label-support",
        "rules_sha256": rules.sha256,
        "absolute_bar": 1.0,
        "absolute_status": absolute_status,
        "absolute_enforced_as_build_blocker": False,
        "n_scored": n_scored,
        "n_supported": n_supported,
        "support_rate": support_rate,
        "n_decisions": n_decisions,
        "n_abstain": n_abstain,
        "abstention_source": abstention_source,
        "yield_over_population": (n_supported / n_decisions) if n_decisions else 0.0,
        "yield_definition": "n_supported / n_decisions (frozen RULES.json metric definition)",
        "classes": classes,
        "incumbent": dict(INCUMBENT),
        "lineage_matches_incumbent_population": lineage,
        "regression_verdict": regression_verdict,
        "gate_blocks_build": bool(lineage and regressed),
        "per_bundle": {
            qid: {
                **b,
                "n_abstain": (int(abstain_by_qid[qid]) if abstain_by_qid is not None
                              else b["n_abstain"]),
                "n_none_rows_descriptive": b["n_none_rows_descriptive"],
            }
            for qid, b in per_bundle.items()
        },
    }


# The single predicate value, derived from the accepted pinned incumbent
# (never re-typed): 5/65 = 0.07692307692307693.
PREDICATE_RATE = INCUMBENT["n_supported"] / INCUMBENT["n_scored"]


def label_lineage_gate_verdict(label_result: dict) -> dict:
    """The accepted population-free label_lineage_gate verdict, published BESIDE
    the population-pinned label_gate regression verdict.

    Faithful reuse of the accepted predicate (label_lineage_gate.py):
      lineage := set(per_bundle) == the three frozen qids
      FAIL_REGRESSION := lineage AND n_scored > 0 AND support_rate < 5/65 (strict)  BLOCKS
      PASS_NO_REGRESSION := lineage AND n_scored > 0 AND support_rate >= 5/65
      NOT_MEASURED := lineage AND n_scored == 0  (not a pass, not a block)
      NOT_APPLICABLE := not lineage  (not a pass)
    NOT_APPLICABLE and NOT_MEASURED are never counted as a pass.
    """
    n_scored = label_result.get("n_scored", 0)
    n_supported = label_result.get("n_supported", 0)
    support_rate = label_result.get("support_rate")
    lineage = set(label_result.get("per_bundle", {})) == set(INCUMBENT_QIDS)
    if not lineage:
        verdict, blocks = "NOT_APPLICABLE", False
    elif not n_scored:
        verdict, blocks = "NOT_MEASURED", False
    else:
        regressed = bool(support_rate is not None and support_rate < PREDICATE_RATE)
        verdict = "FAIL_REGRESSION" if regressed else "PASS_NO_REGRESSION"
        blocks = regressed
    return {
        "gate": "counter-label-support-lineage",
        "rules_sha256": label_result.get("rules_sha256"),
        "predicate": ("lineage := set(per_bundle) == the three frozen qids; "
                      "FAIL_REGRESSION := lineage AND n_scored > 0 AND support_rate < 5/65 (strict)"),
        "predicate_rate": PREDICATE_RATE,
        "lineage_matches_frozen_qid_set": bool(lineage),
        "n_scored": n_scored,
        "n_supported": n_supported,
        "support_rate": support_rate,
        "regression_verdict": verdict,
        "gate_blocks_build": bool(blocks),
        "is_pass": verdict == "PASS_NO_REGRESSION",
        "not_applicable_is_not_a_pass": verdict in ("NOT_APPLICABLE", "NOT_MEASURED"),
        "note": ("NOT_MEASURED (n_scored=0) and NOT_APPLICABLE are inapplicability / "
                 "non-measurement markers, never passes; only PASS_NO_REGRESSION is a pass."),
        "population_pinned_label_gate_side_by_side": {
            "regression_verdict": label_result.get("regression_verdict"),
            "gate_blocks_build": label_result.get("gate_blocks_build"),
            "lineage_matches_incumbent_population": label_result.get("lineage_matches_incumbent_population"),
        },
    }
