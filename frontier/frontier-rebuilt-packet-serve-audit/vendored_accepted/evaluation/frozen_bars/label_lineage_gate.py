"""Counter-label-support regression gate over the ACCEPTED packet LINEAGE.

Why this module exists
----------------------
The accepted counter-label gate (`label_gate.score_packet`, accepted cycle
38971202786) applies its regression predicate at a POPULATION-PIN: it can emit
a regression verdict only when the scored-row count equals the incumbent 65.
Its own accepted record names the consequence three times:

* ``L2_gate_admits_total_label_collapse`` (enforced, holds) - accepted packet
  38799024807 scores 0 supported of 7 scored (rate 0.0) and is admitted with
  ``gate_blocks_build == false``, while the geometry gate blocks the very same
  packet.
* ``L3_gate_population_predicate_is_confounded`` (enforced, holds) - only 1 of
  the 3 accepted-lineage packets can receive any regression verdict at all.
* ``L4_rate_and_count_semantics_disagree`` (enforced, holds) - the count reading
  at a pinned population would FAIL accepted packet 38812599575, whose support
  rate 1/9 = 0.1111 is STRICTLY BETTER than the incumbent 5/65 = 0.0769.

Factory direction v50 fixes the mandated predicate in its own words: "each gate
FAILS CI on a REGRESSION BELOW ITS RECOMPUTED INCUMBENT (**label support below
5/65**, ...)". That is a RATE predicate. This module applies exactly that
reading, on exactly the qid-set lineage the accepted geometry gate already uses,
and changes nothing else.

WHAT IS NOT INVENTED
--------------------
The single number used is ``label_gate.INCUMBENT["n_supported"] /
label_gate.INCUMBENT["n_scored"]`` = 5/65, derived at runtime from accepted
pinned literals - never re-typed, never tuned, never rounded. No criterion,
lexicon, anchor, injection case, projection constant, absolute bar or support
test is added, removed, retuned or clarified. The absolute frozen label bar
(``support_rate == 1.0``) is still reported as LABEL_SOUND/LABEL_UNSOUND and is
still never a build blocker.

WHAT IS PRESERVED
-----------------
``label_gate.py``, ``geometry_gate.py``, ``run_bar_gates.py`` and
``VERDICT_CONTRACT.json`` are untouched. Every previously accepted statement
stays computable: this module reports the accepted population-pinned verdict
SIDE BY SIDE with the population-free one, under
``accepted_gate_side_by_side`` and ``reported_only_readings``, so the L4
divergence between the two readings is published rather than resolved by
silence.

Read-only, stdlib-only, no network, no Product import.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_BAR_DIR = Path(__file__).resolve().parent
if str(_BAR_DIR.parent.parent) not in sys.path:
    sys.path.insert(0, str(_BAR_DIR.parent.parent))

from evaluation.frozen_bars import label_gate  # noqa: E402

#: The three frozen anchor qids (accepted literal; a qid set that is not exactly
#: this set is off-lineage and receives no regression verdict).
LINEAGE_QIDS = tuple(label_gate.INCUMBENT_QIDS)

#: THE ONLY NUMBER. Direction v50's mandated predicate value, derived from the
#: accepted pinned incumbent rather than re-typed: 5/65 = 0.07692307692307693.
PREDICATE_RATE = label_gate.INCUMBENT["n_supported"] / label_gate.INCUMBENT["n_scored"]

#: Frozen input identity is re-hashed by label_gate.load_frozen_rules before
#: anything is scored; a mismatch is an environment error, never a verdict.
RULES_LABEL_SHA256 = label_gate.EXPECTED_RULES_SHA256

VERDICT_CONTRACT_PATH = _BAR_DIR / "LABEL_LINEAGE_VERDICT.json"
EXPECTED_VERDICT_CONTRACT_SHA256 = (
    "016bffe5914ffc9074c948c9e452d05c79639735ed32f6c82aefd3751afcca18"
)

SCORED_STATUSES = ("candidate-limiting", "candidate-contrary",
                   "contrary_or_exception", "limiting")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_verdict_contract(path: str | Path = VERDICT_CONTRACT_PATH) -> dict:
    """Load this gate's own verdict contract; refuse a byte-drifted copy."""
    p = Path(path)
    observed = sha256_file(p)
    if observed != EXPECTED_VERDICT_CONTRACT_SHA256:
        raise RuntimeError(
            f"LABEL_LINEAGE_VERDICT.json sha256 mismatch: expected "
            f"{EXPECTED_VERDICT_CONTRACT_SHA256}, observed {observed}. Refusing to classify."
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema") != "lex-evaluation-label-lineage-verdict/1":
        raise RuntimeError(f"unexpected verdict-contract schema in {p}")
    return data


# --------------------------------------------------------------------------
# population discovery
# --------------------------------------------------------------------------
def discover_population(root: str | Path) -> dict:
    """Every packet dir under ``root`` that carries ALL THREE frozen qids.

    A packet directory may hold its bundles directly or under a ``questions/``
    subdirectory (the accepted product layout); both are probed and the resolved
    directory is recorded, so the reported shas always name the bytes actually
    read.

    Packets with a different qid set are RECORDED as out-of-scope with a
    reason, never silently dropped (same discipline as the accepted
    packet_lineage_sweep population).
    """
    root = Path(root)
    in_scope, out_of_scope = [], []
    if not root.is_dir():
        raise FileNotFoundError(f"packet root does not exist: {root}")
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        candidates = [d / "questions", d] if (d / "questions").is_dir() else [d]
        resolved = next((c for c in candidates if any(
            (c / f"{q}.bundle.json").exists() for q in LINEAGE_QIDS)), None)
        if resolved is None:
            out_of_scope.append({
                "packet_id": d.name,
                "n_frozen_qids_present": 0,
                "reason": (
                    "packet carries no <qid>.bundle.json for any of the three frozen qids "
                    "(de-kapitalverletzung, fr-bail-entretien, it-responsabilita-medica); the "
                    "frozen rubric's anchors and query-term lexicons are pinned to those three "
                    "qids, so the gate never invents an anchor profile for it"
                ),
            })
            continue
        present = [q for q in LINEAGE_QIDS if (resolved / f"{q}.bundle.json").exists()]
        if len(present) == len(LINEAGE_QIDS):
            in_scope.append({
                "packet_id": d.name,
                "questions_dir": str(resolved),
                "bundle_sha256": {q: sha256_file(resolved / f"{q}.bundle.json") for q in LINEAGE_QIDS},
            })
        else:
            out_of_scope.append({
                "packet_id": d.name,
                "n_frozen_qids_present": len(present),
                "reason": (
                    "packet does not carry all three frozen qids (missing: "
                    f"{sorted(set(LINEAGE_QIDS) - set(present))!r}); the frozen rubric's anchors "
                    "are pinned to the three frozen qids, so no lineage verdict applies and the "
                    "gate never invents an anchor profile for it"
                ),
            })
    return {"root": str(root), "n_packet_dirs": len(in_scope) + len(out_of_scope),
            "in_scope": in_scope, "out_of_scope": out_of_scope}


# --------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------
def score_packet(bundles: dict[str, str], rules) -> dict:
    """Judge one packet on the three frozen qids under the mandated rate predicate.

    ``bundles`` maps qid -> path to <qid>.bundle.json. A qid set that is not
    exactly the three frozen qids is off-lineage and is refused/scored as
    NOT_APPLICABLE, exactly as the accepted geometry gate does. An unknown qid
    is refused with the accepted actionable ValueError from label_gate.

    States emitted (enumerated in LABEL_LINEAGE_VERDICT.json):
      FAIL_REGRESSION  - lineage holds and pooled support_rate < 5/65. BLOCKS.
      PASS_NO_REGRESSION - lineage holds and pooled support_rate >= 5/65.
      NOT_MEASURED     - lineage holds but there are no scored counter rows, so
                         no support rate exists to compare. Not a pass, not a
                         block, and it certifies nothing.
      NOT_APPLICABLE   - not the three frozen qids. Not a pass.
    """
    # The accepted gate is the single reader of the frozen rubric; we never
    # re-implement scoring, we only add the regression comparison it omits.
    accepted = label_gate.score_packet(bundles, rules)

    n_scored = accepted["n_scored"]
    n_supported = accepted["n_supported"]
    support_rate = accepted["support_rate"]
    lineage = set(bundles) == set(LINEAGE_QIDS)

    # Enforced reading: direction v50's own rate predicate.
    if not lineage:
        verdict, blocks = "NOT_APPLICABLE", False
        rate_cmp = None
    elif not n_scored:
        verdict, blocks = "NOT_MEASURED", False
        rate_cmp = None
    else:
        regressed = support_rate < PREDICATE_RATE
        verdict = "FAIL_REGRESSION" if regressed else "PASS_NO_REGRESSION"
        blocks = bool(regressed)
        rate_cmp = {"observed": support_rate, "predicate": PREDICATE_RATE,
                    "comparison": "< (strict; equality passes)"}

    # Reported-only reading: the accepted population-pinned count predicate,
    # retained verbatim so every previously accepted statement stays computable
    # and so the L4 divergence is published instead of silently resolved.
    acc_lineage = bool(accepted["lineage_matches_incumbent_population"])
    count_regressed = acc_lineage and n_supported < label_gate.INCUMBENT["n_supported"]

    # Reported-only reading: the SAME count comparison with the population pin
    # REMOVED. This is the counterfactual that makes accepted finding L4
    # MEASURED rather than asserted: it is the variant that would falsely block
    # an accepted packet whose support rate is strictly better than the
    # incumbent's. Never enforced.
    count_nopin = bool(lineage and n_scored and n_supported < label_gate.INCUMBENT["n_supported"])

    readings_disagree = bool(
        lineage and n_scored
        and (blocks is not bool(count_regressed))
    )
    # The counterfactual that actually isolates the rate/count question.
    rate_vs_count_nopin_disagree = bool(
        lineage and n_scored and (blocks is not count_nopin)
    )

    return {
        "gate": "counter-label-support-lineage",
        "rules_sha256": rules.sha256,
        "enforced_reading": {
            "name": "direction_v50_rate",
            "predicate": ("lineage := set(bundles) == the three frozen qids; "
                          "FAIL_REGRESSION := lineage AND n_scored > 0 AND "
                          "support_rate < 5/65 (strict)"),
            "value": PREDICATE_RATE,
            "value_derivation": "label_gate.INCUMBENT[n_supported] / label_gate.INCUMBENT[n_scored]",
            "enforced_as_build_blocker": True,
        },
        "reported_only_readings": {
            "accepted_count_at_pinned_population": {
                "predicate": ("lineage := set(bundles) == the three frozen qids AND "
                              "n_scored == 65; FAIL := lineage AND n_supported < 5"),
                "n_scored": n_scored,
                "n_supported": n_supported,
                "regressed": bool(count_regressed),
                "enforced_as_build_blocker": False,
                "why_not_enforced": (
                    "accepted finding L4_rate_and_count_semantics_disagree (enforced, holds): "
                    "this reading FAILS accepted packet 38812599575 (1 supported of 9 scored, "
                    "rate 0.1111) whose support rate is strictly BETTER than the incumbent "
                    "0.0769. Enforcing it would falsely block an accepted, strictly-better "
                    "artifact. Retained verbatim as evidence, never enforced."
                ),
            },
            "readings_disagree_on_this_packet": readings_disagree,
            "count_reading_without_population_pin": {
                "predicate": ("lineage := set(bundles) == the three frozen qids; "
                              "FAIL := lineage AND n_supported < 5  [population pin REMOVED]"),
                "n_supported": n_supported,
                "regressed": count_nopin,
                "enforced_as_build_blocker": False,
                "purpose": (
                    "MEASURED counterfactual for accepted finding L4_rate_and_count_semantics_"
                    "disagree: this is the variant that would falsely block an accepted packet "
                    "whose support rate is strictly BETTER than the incumbent 0.0769. It is "
                    "computed and published on every packet so the L4 divergence is a measurement, "
                    "not an assertion."
                ),
            },
            "rate_vs_count_nopin_disagree_on_this_packet": rate_vs_count_nopin_disagree,
        },
        "lineage_matches_frozen_qid_set": lineage,
        "lineage_qids": list(LINEAGE_QIDS),
        "n_scored": n_scored,
        "n_supported": n_supported,
        "support_rate": support_rate,
        "rate_comparison": rate_cmp,
        "classes": accepted["classes"],
        "absolute_status": accepted["absolute_status"],
        "absolute_enforced_as_build_blocker": False,
        "regression_verdict": verdict,
        "gate_blocks_build": blocks,
        "is_pass": verdict == "PASS_NO_REGRESSION",
        "incumbent": dict(label_gate.INCUMBENT),
        "accepted_gate_side_by_side": {
            "source": "evaluation/frozen_bars/label_gate.py::score_packet (accepted 38971202786)",
            "regression_verdict": accepted["regression_verdict"],
            "gate_blocks_build": accepted["gate_blocks_build"],
            "lineage_matches_incumbent_population": accepted["lineage_matches_incumbent_population"],
            "why_reported": (
                "the accepted gate is preserved unchanged; this gate is additive. Where the two "
                "disagree, the accepted verdict is NOT overwritten and the disagreement is the "
                "measured finding."
            ),
        },
        "per_bundle": {q: {k: b[k] for k in
                           ("n_scored", "n_supported", "support_rate", "classes", "sha256")}
                       for q, b in accepted["per_bundle"].items()},
    }


def score_packet_dicts(bundle_dicts: dict[str, dict], rules) -> dict:
    """Same judgement from already-parsed bundles (used for derived controls)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        paths = {}
        for q, b in bundle_dicts.items():
            p = Path(tmp) / f"{q}.bundle.json"
            p.write_text(json.dumps(b), encoding="utf-8")
            paths[q] = str(p)
        return score_packet(paths, rules)


# --------------------------------------------------------------------------
# non-vacuity: minimal delta on the incumbent population itself
# --------------------------------------------------------------------------
def minimal_delta_control(bundle_dicts: dict[str, str], rules) -> dict:
    """The smallest falsifier: remove the evidence of exactly ONE supported row.

    Deterministic choice of the row: the first SUPPORTED scored row in the
    frozen extract order (rank ascending, then decision_id ascending), which is
    the same order the vendored extract uses, so the control is reproducible
    without depending on dict ordering.

    n_scored is UNCHANGED (65 -> 65); only n_supported moves (5 -> 4), i.e. the
    rate moves 0.076923 -> 0.061538 and crosses the predicate. A gate that
    cannot see this cannot see anything.
    """
    base_paths = {q: p for q, p in bundle_dicts.items()}
    base = score_packet(base_paths, rules)

    # Locate one supported scored row across the packet.
    target = None
    for qid in LINEAGE_QIDS:
        res = label_gate.score_bundle(base_paths[qid], rules, qid)
        for row in res["rows"]:
            if row["supported"]:
                target = (qid, row["decision_id"])
                break
        if target:
            break
    if target is None:
        return {"control": "one_supported_row_evidence_removed",
                "proven_non_vacuous": False,
                "reason": "no supported scored row found in the packet; control inapplicable"}
    qid, did = target

    derived = {q: json.loads(Path(p).read_text(encoding="utf-8"))
               for q, p in base_paths.items()}
    edited = False
    for d in derived[qid].get("decisions", []):
        if d.get("decision_id") == did:
            d["counter_evidence"] = ""
            edited = True
            break
    if not edited:
        return {"control": "one_supported_row_evidence_removed", "proven_non_vacuous": False,
                "reason": f"target decision {did} not found in {qid}"}

    after = score_packet_dicts(derived, rules)
    delta = {
        "field_edited": "counter_evidence",
        "rows_removed": 0,
        "qid": qid,
        "decision_id": did,
        "n_scored_before": base["n_scored"],
        "n_scored_after": after["n_scored"],
        "n_supported_before": base["n_supported"],
        "n_supported_after": after["n_supported"],
        "support_rate_before": base["support_rate"],
        "support_rate_after": after["support_rate"],
    }
    return {
        "control": "one_supported_row_evidence_removed",
        "purpose": "minimal-delta non-vacuity on the incumbent population itself",
        "delta": delta,
        "verdict_before": base["regression_verdict"],
        "verdict_after": after["regression_verdict"],
        "gate_blocks_build_after": after["gate_blocks_build"],
        "flipped_to_red": bool(base["regression_verdict"] == "PASS_NO_REGRESSION"
                               and after["regression_verdict"] == "FAIL_REGRESSION"),
        "population_unchanged": base["n_scored"] == after["n_scored"],
        "proven_non_vacuous": bool(
            base["regression_verdict"] == "PASS_NO_REGRESSION"
            and after["regression_verdict"] == "FAIL_REGRESSION"
            and after["gate_blocks_build"] is True),
    }


def geometry_incumbent_floor_disclosure(geometry_rows: list[dict]) -> dict:
    """MEASURE whether the enforced geometry incumbent is a floor over the population.

    Accepted finding F2_INCUMBENT_NOT_A_FLOOR holds: over the accepted packet
    population the minimum per-bundle criterion-count is de 6 / fr 4 / it 4,
    which is BELOW the enforced incumbent de 6 / fr 5 / it 5. This recomputes
    that minimum from the measured rows instead of restating it, and reports the
    divergence. Direction v50 FIXES the geometry incumbent at de 6 / fr 5 / it
    5, so this function changes nothing; it exists so a packet-admission
    consumer is told, in machine-readable form, that the geometry bar is a
    'no worse than the served packet' reference rather than the worst case
    observed in the accepted population.
    """
    from evaluation.frozen_bars import geometry_gate as _gg

    mins: dict[str, dict | None] = {}
    for qid in _gg.INCUMBENT_COUNTS:
        vals = [r["accepted_geometry_gate"]["per_bundle_counts"].get(qid)
                for r in geometry_rows
                if r["accepted_geometry_gate"]["per_bundle_counts"].get(qid) is not None]
        mins[qid] = min(vals) if vals else None
    below = {qid: {"incumbent": _gg.INCUMBENT_COUNTS[qid], "min_over_population": m}
             for qid, m in mins.items()
             if m is not None and m < _gg.INCUMBENT_COUNTS[qid]}
    return {
        "incumbent_counts": dict(_gg.INCUMBENT_COUNTS),
        "min_counts_over_in_scope_population": mins,
        "incumbent_is_a_floor": not below and bool(mins),
        "qids_with_a_population_member_below_the_incumbent": below,
        "disclosure": (
            "the enforced geometry incumbent is NOT the worst case in the accepted population; "
            "it is the served packet's own score. The gate still blocks those packets, because "
            "the predicate is 'below the incumbent', but an admission consumer must not read "
            "'PASS_NO_REGRESSION' as 'no geometry defect exists anywhere in the population'."
            if below else
            "no in-scope population member falls below the enforced geometry incumbent"),
        "not_a_change": ("direction v50 fixes the geometry incumbent at de 6 / fr 5 / it 5; this "
                         "lane does not move it and invents no alternative floor"),
    }


def verify_frozen_predictions(freeze_path: str | Path, sweep: dict,
                              frozen_identity: dict | None = None) -> dict:
    """Execute the PREDICTIONS of the pre-execution freeze against a sweep record.

    The freeze file is READ, never written. Only the `predicted` blocks are
    evaluated, because those are the operative pre-registered values; the
    `statement` prose is scored separately as `statement_defects` so a
    self-inconsistent sentence can never be laundered into a pass.
    """
    fz = json.loads(Path(freeze_path).read_text(encoding="utf-8"))
    preds = fz.get("predicates", {})
    observed = {r["packet_id"]: r["lineage_gate"] for r in sweep.get("blocking_matrix", [])}
    rows = sweep.get("blocking_matrix", [])
    out: dict = {"freeze_file": str(freeze_path), "freeze_run_id": fz.get("run_id"),
                 "evaluated": [], "statement_defects": []}

    p1 = preds.get("P1_label_gate_parity_on_accepted_lineage", {})
    for pid, exp in (p1.get("predicted") or {}).items():
        obs = observed.get(pid)
        if obs is None:
            out["evaluated"].append({"predicate": "P1", "packet_id": pid, "status": "MISSING",
                                     "detail": "packet not in the measured in-scope population"})
            continue
        checks = {
            "n_scored": obs["n_scored"] == exp["n_scored"],
            "n_supported": obs["n_supported"] == exp["n_supported"],
            "regression_verdict": obs["regression_verdict"] == exp["verdict"],
            "gate_blocks_build": obs["gate_blocks_build"] == exp["gate_blocks_build"],
        }
        out["evaluated"].append({
            "predicate": "P1", "packet_id": pid, "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks, "predicted": exp,
            "observed": {k: obs[k] for k in ("n_scored", "n_supported", "support_rate",
                                             "regression_verdict", "gate_blocks_build")}})
    # The P1 statement prose claims a 2-of-2 block count; its own predicted table
    # blocks exactly 1 of the 2. Recorded, never repaired in place.
    p1_blocking = sorted(pid for pid, o in observed.items() if o["gate_blocks_build"])
    out["statement_defects"].append({
        "predicate": "P1", "field": "statement",
        "defect": "internal_inconsistency_in_the_freeze",
        "detail": ("the P1 `statement` prose says '2 of 2 non-incumbent packets' block, but P1's "
                   f"own `predicted` table blocks exactly {p1_blocking}. The predicted table is "
                   "the operative pre-registered value and it held; the prose sentence was "
                   "mis-written before execution. Preserved verbatim, corrected by erratum "
                   "FREEZE_ERRATA_39020603510.json, never edited in the freeze file."),
    })

    nv = sweep.get("non_vacuity_minimal_delta") or {}
    p3_ok = bool(nv.get("flipped_to_red") and nv.get("population_unchanged")
                 and nv.get("gate_blocks_build_after"))
    out["evaluated"].append({"predicate": "P3", "status": "PASS" if p3_ok else "FAIL",
                             "checks": {"flipped_to_red": bool(nv.get("flipped_to_red")),
                                        "population_unchanged": bool(nv.get("population_unchanged")),
                                        "blocks_after": bool(nv.get("gate_blocks_build_after"))},
                             "delta": nv.get("delta")})

    # P4: no false block. The incumbent and every accepted packet whose rate is at
    # or above the incumbent rate must NOT block.
    false_blocks = sorted(pid for pid, o in observed.items()
                          if o["gate_blocks_build"] and o["support_rate"] is not None
                          and o["support_rate"] >= label_gate.INCUMBENT["n_supported"]
                          / label_gate.INCUMBENT["n_scored"])
    out["evaluated"].append({
        "predicate": "P4", "status": "PASS" if not false_blocks else "FAIL",
        "checks": {"false_blocks": false_blocks},
        "detail": ("no accepted packet at or above the incumbent rate is blocked by the enforced "
                   "reading")})
    out["statement_defects"].append({
        "predicate": "P4", "field": "predicted",
        "defect": "mis_stated_about_which_predicate_diverges",
        "detail": ("the freeze predicted that 38812599575 would be 'true under the reported-only "
                   "count reading'. The count reading it referred to is the ACCEPTED "
                   "population-pinned one, which cannot fire off the 65-row population at all, so "
                   "the real divergence is between the enforced RATE reading and the count reading "
                   "WITH THE POPULATION PIN REMOVED. That counterfactual is now measured on every "
                   "packet as reported_only_readings.count_reading_without_population_pin; the "
                   "freeze text is preserved verbatim and corrected by erratum.")})

    # P5: off-lineage packets get no lineage verdict; nothing was silently dropped.
    oos = sweep.get("population", {}).get("out_of_scope", [])
    dropped = oos == [] and sweep.get("population", {}).get("n_packet_dirs", 0) > 0
    p5_ok = not dropped
    out["evaluated"].append({
        "predicate": "P5", "status": "PASS" if p5_ok else "FAIL",
        "checks": {"out_of_scope_recorded_with_reason": all(
            bool(o.get("reason")) for o in oos), "n_out_of_scope": len(oos)},
        "out_of_scope": oos})

    # P2: are the named accepted findings of record closed by this measurement?
    collapse = [r for r in rows
                if r["lineage_gate"]["n_scored"] > 0 and r["lineage_gate"]["n_supported"] == 0]
    l4_measured = [r["packet_id"] for r in rows
                   if r["closure"]["L4_rate_and_count_semantics_disagree"]["divergence_observed_here"]]
    n_in_scope = sweep.get("population", {}).get("n_in_scope", 0)
    n_admissible = len([r for r in rows if r["lineage_gate"]["n_scored"] > 0])
    trap_still_open = [r["packet_id"] for r in collapse
                       if not r["lineage_gate"]["gate_blocks_build"]]
    p2_checks = {
        "L2_closed": bool(collapse) and all(r["lineage_gate"]["gate_blocks_build"] for r in collapse),
        "L3_closed": n_admissible == n_in_scope and n_in_scope > 0,
        "L4_measured_not_merely_asserted": bool(l4_measured),
        "naive_consumer_trap_closed": bool(collapse) and not trap_still_open,
    }
    out["evaluated"].append({
        "predicate": "P2", "status": "PASS" if all(p2_checks.values()) else "FAIL",
        "checks": p2_checks,
        "evidence": {
            "total_label_collapse_packets": [r["packet_id"] for r in collapse],
            "admissible_in_scope_packets": n_admissible,
            "n_in_scope_packets": n_in_scope,
            "packets_where_rate_and_count_nopin_readings_diverge": l4_measured,
            "packets_where_the_trap_is_still_open": trap_still_open,
        }})

    # P6: every frozen digest re-verified byte-identical this execution.
    ident = frozen_identity or sweep.get("frozen_identity") or {}
    p6_ok = bool(ident) and all(v["matches"] for v in ident.values())
    out["evaluated"].append({
        "predicate": "P6", "status": "PASS" if p6_ok else ("FAIL" if ident else "NOT_RUN"),
        "checks": {k: v["matches"] for k, v in ident.items()}})

    statuses = [e["status"] for e in out["evaluated"]]
    out["verdict"] = "ALL_PREDICTIONS_HELD" if all(s == "PASS" for s in statuses) else (
        "PREDICTION_FAILED")
    out["n_statement_defects"] = len(out["statement_defects"])
    return out


def closure_report(bundle_paths: dict[str, str], rules, accepted_verdict: dict) -> dict:
    """Which accepted findings of record this gate closes on THIS packet."""
    res = score_packet(bundle_paths, rules)
    rate = res["support_rate"]
    below = bool(res["n_scored"] and rate < PREDICATE_RATE)
    ro = res["reported_only_readings"]
    return {
        "packet_id": accepted_verdict.get("packet_id"),
        "regression_verdict": res["regression_verdict"],
        "gate_blocks_build": res["gate_blocks_build"],
        "support_rate": rate,
        "L2_gate_admits_total_label_collapse": {
            "closed_here": bool(below and res["gate_blocks_build"]),
            "reading": ("a packet whose pooled support rate is strictly below the incumbent rate "
                        "and below the incumbent count now BLOCKS, instead of being admitted"),
        },
        "L3_gate_population_predicate_is_confounded": {
            "admissible_here": bool(res["lineage_matches_frozen_qid_set"]),
            "reading": "the population pin is gone; admissibility depends on the qid set only",
        },
        "L4_rate_and_count_semantics_disagree": {
            "divergence_observed_here": ro["rate_vs_count_nopin_disagree_on_this_packet"],
            "divergence_against": (
                "the enforced RATE reading vs the count reading WITH THE POPULATION PIN REMOVED "
                "(count_reading_without_population_pin) - this is the comparison L4 is about"),
            "divergence_against_the_population_pinned_count_reading_here":
                ro["readings_disagree_on_this_packet"],
            "reading": ("where the rate and count readings disagree, the enforced reading is the "
                        "mandated rate one and the count reading is published. NOTE the two "
                        "divergence flags are different quantities and must not be conflated: the "
                        "population-pinned count reading is blind off the 65-row population and so "
                        "disagrees with the enforced reading on ANY non-incumbent packet, which "
                        "says nothing about L4; only the pin-removed counterfactual isolates the "
                        "rate/count question itself."),
        },
        "naive_consumer_trap": {
            "fires_here": bool(res["n_supported"] == 0 and not res["gate_blocks_build"]
                               and res["lineage_matches_frozen_qid_set"]),
            "reading": ("exit 0 / blocks false with n_supported == 0 on lineage is no longer "
                        "reachable; the trap of VERDICT_CONTRACT.json is closed for this gate"),
        },
    }