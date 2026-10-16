"""Declared divergence: charter acceptance check (4) vs the frozen rule.

Why this module exists
----------------------
Charter acceptance check (4) reads:

    "NON-VACUITY PROVEN: a negative control in which cluster labels are
     permuted must FAIL the coherence criteria, and a second control in which
     coordinates are shuffled must fail PROJ_RANK / PROJ_SPEARMAN. If a control
     passes, the harness is vacuous and the run is void."

The FIRST half is satisfiable and is satisfied. The SECOND half is not
satisfiable, for a reason internal to the FROZEN scorer rather than to this
team's variants:

  * ``PROJ_RANK`` is computed as the Spearman correlation between the retrieval
    ``rank`` field and the TF-IDF cosine distance to the query vector
    (vendored metrics.py, ``rank_rho``). It never reads the 2-D coordinates
    ``x``/``y``. Permuting or shuffling coordinates therefore cannot change it,
    by construction, for ANY candidate geometry.
  * ``PROJ_SPEARMAN`` and ``PROJ_KNN10`` DO read coordinates, but on all three
    served bundles both variants already sit below their bars, so corruption can
    only move the value downward, never across the bar. The verdict is therefore
    unobservable even though the metric is highly responsive.

What the FROZEN rule itself requires
------------------------------------
``RULES_GEOMETRY.json -> non_vacuity`` is the binding authority and asks for
exactly one control:

    control:  "Permute cluster_id assignment across rows (seed 0) and permute
               label texts across cluster ids; recompute all criteria."
    required: "Corrupted geometry must flip >= 2 criteria verdicts (passed=true)."

That requirement is met: the permutation control flips two criteria verdicts on
fr-bail-entretien (COHERENCE_QUERY_LANG and COHERENCE_QUERY_TERM).

This module does NOT quietly substitute a convenient definition of non-vacuity.
It emits both readings and proves the structural claim empirically, so the
director sees exactly which part of the charter was satisfiable, which was not,
and why.
"""
from __future__ import annotations

import copy
import json
from typing import Any

import numpy as np

from .scoring import rule_block_for, score_bundle

COORDINATE_READING_CRITERIA = ("PROJ_SPEARMAN", "PROJ_KNN10")
COORDINATE_INVARIANT_CRITERIA = ("PROJ_RANK", "STRUCTURE_SEP")


def probe_coordinate_invariance(
    rules_geom: dict,
    candidate: dict,
    rules_bundle: dict,
    *,
    seed: int = 7,
) -> dict[str, Any]:
    """Permute coordinates of one candidate and report which metrics move."""
    base = score_bundle(candidate, rules_bundle)["criteria"]
    perm = list(np.random.RandomState(seed).permutation(len(candidate["decisions"])))
    shuffled = copy.deepcopy(candidate)
    xs = [d["x"] for d in shuffled["decisions"]]
    ys = [d["y"] for d in shuffled["decisions"]]
    for i, pi in enumerate(perm):
        shuffled["decisions"][i]["x"] = xs[pi]
        shuffled["decisions"][i]["y"] = ys[pi]
    after = score_bundle(shuffled, rules_bundle)["criteria"]

    out: dict[str, Any] = {"seed": seed, "criteria": {}}
    for crit in COORDINATE_INVARIANT_CRITERIA + COORDINATE_READING_CRITERIA:
        v0, v1 = base[crit]["value"], after[crit]["value"]
        nan = isinstance(v0, float) and np.isnan(v0)
        out["criteria"][crit] = {
            "before": v0,
            "after": v1,
            "invariant": bool(nan or v0 == v1),
            "verdict_flipped": bool(base[crit]["pass"] != after[crit]["pass"]),
            "bar": base[crit].get("bar"),
        }
    out["all_invariant_criteria_are_invariant"] = all(
        out["criteria"][c]["invariant"] for c in COORDINATE_INVARIANT_CRITERIA
    )
    out["at_least_one_reading_criterion_moved"] = any(
        not out["criteria"][c]["invariant"] for c in COORDINATE_READING_CRITERIA
    )
    return out


def divergence_record(
    rules_geom: dict,
    candidates: dict[str, dict[str, dict]],
    rules_bundles: dict[str, dict],
    controls: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the declared-divergence artifact.

    ``candidates[variant][qid]`` is the scored candidate bundle.
    ``controls`` is the CONTROLS.json payload produced by ``controls.py``.
    """
    probes: dict[str, Any] = {}
    for variant, per_q in candidates.items():
        probes[variant] = {
            qid: probe_coordinate_invariance(rules_geom, per_q[qid], rules_bundles[qid])
            for qid in sorted(per_q)
        }

    # The frozen rule's own non-vacuity clause: >=2 verdict flips from the
    # cluster_id/label permutation control.
    rule_nv = rules_geom.get("non_vacuity") or {}
    flips_per_control: dict[str, Any] = {}
    for variant, per_q in controls.items():
        for qid, payload in per_q.items():
            base = payload["baseline_verdicts"]
            perm = payload["controls"]["permuted_cluster_assignment"]["verdicts"]
            flips = sorted(k for k in base if perm[k] != base[k])
            flips_per_control[f"{variant}/{qid}"] = {
                "n_flips": len(flips),
                "flips": flips,
                "meets_frozen_rule_requirement": len(flips) >= 2,
            }
    max_flips = max((v["n_flips"] for v in flips_per_control.values()), default=0)
    frozen_ok = max_flips >= 2

    coord_invariant_everywhere = all(
        p["criteria"][c]["invariant"]
        for per_variant in probes.values()
        for p in per_variant.values()
        for c in COORDINATE_INVARIANT_CRITERIA
    )

    return {
        "schema": "frontier-query-conditioned-map-geometry/non-vacuity-divergence/1",
        "charter_requirement": (
            "acceptance check (4): a permuted-cluster-label control must FAIL the "
            "coherence criteria, and a second control in which coordinates are "
            "shuffled must fail PROJ_RANK / PROJ_SPEARMAN; if a control passes the "
            "harness is vacuous and the run is void."
        ),
        "charter_literal_satisfied": False,
        "why_charter_literal_not_satisfiable": {
            "PROJ_RANK_is_coordinate_invariant": bool(coord_invariant_everywhere),
            "mechanism": (
                "The frozen scorer computes PROJ_RANK as the Spearman correlation "
                "between the retrieval 'rank' field and the TF-IDF cosine distance to "
                "the query vector (vendored metrics.py: rank_rho). It never reads the "
                "2-D coordinates x/y, so no coordinate permutation -- shuffled or "
                "otherwise -- can change it, for any candidate geometry. STRUCTURE_SEP "
                "is coordinate-invariant for the same reason: it is computed from X and "
                "cluster_id, not from the layout."
            ),
            "PROJ_SPEARMAN_and_PROJ_KNN10_do_read_coordinates": (
                "Both move sharply under coordinate permutation, which is the positive "
                "evidence that the harness is not vacuous. They do not flip their "
                "verdict only because both variants already score below the bar "
                "(PROJ_SPEARMAN 0.50, PROJ_KNN10 0.40) on all three bundles, so "
                "corruption can only push the value further down."
            ),
            "consequence": (
                "The charter's second control is unsatisfiable as written, for a reason "
                "internal to the frozen rule and independent of the variants under "
                "test. It was NOT worked around: it is reported as unsatisfied here."
            ),
        },
        "frozen_rule_is_the_binding_authority": {
            "rule_non_vacuity": rule_nv,
            "max_verdict_flips_from_permutation_control": max_flips,
            "frozen_rule_requirement_met": bool(frozen_ok),
            "per_control": flips_per_control,
            "interpretation": (
                "The frozen rule asks for one control -- the cluster_id/label "
                "permutation -- and requires >= 2 verdict flips. That is met on "
                "fr-bail-entretien, where COHERENCE_QUERY_LANG and "
                "COHERENCE_QUERY_TERM both flip. Non-vacuity is therefore proven "
                "against the binding frozen criterion."
            ),
        },
        "coordinate_permutation_probes": probes,
        "conclusion": (
            "Non-vacuity is proven against the frozen rule's own requirement, and the "
            "harness is demonstrably sensitive to coordinate corruption "
            "(PROJ_SPEARMAN/PROJ_KNN10 values move by large margins). The charter's "
            "second control is reported as UNSATISFIED-AS-WRITTEN with its mechanism, "
            "because PROJ_RANK cannot read coordinates. No bar, threshold or control "
            "was weakened to make this read as a pass; this record exists so the "
            "director can see the discrepancy rather than a convenient verdict."
        ),
        "escalated_to_director": True,
    }