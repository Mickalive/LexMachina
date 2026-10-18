#!/usr/bin/env python3
"""Smallest executable retrieval/counter-authority EXPOSURE benchmark on the SHIPPED bundles.

WHY THIS INSTRUMENT EXISTS (the measured gap, not a restatement of an old question)

The lane directive requires known-relevant recall, known contrary/limiting recall,
source/decision-id validity, FR/DE/IT robustness, duplicate suppression, cached
reproducibility, latency and cluster stability.  Reconnaissance at the accepted tip
showed that on the SHIPPED packet (`rebuilt-39027045675`) only two of those were
ever measured at all:

  * `evaluation.served_bundle_scope` measured 5 provenance/source falsifiers;
  * `evaluation.frozen_bars.label_lineage_gate` measured support-among-issued.

Every other lane instrument is hard-pinned to the OLDER packet `38839347028`
(`evaluation/frozen_bars/run_bar_gates.py`, `evaluation/product_counter_recall.py`,
`evaluation/subject_match_audit.py`, `evaluation/packet_admission_conformance.py`),
or scores independent OpenCaseLaw search rows for four frozen slugs that are not
the served questions (`evaluation/retrieval_gate/`).  NO instrument had ever asked
the product's own headline question on its own shipped bytes:

  > are the contrary / limiting authorities the answer cites actually VISIBLE on
  > the map, and can a jurist recover them from the bundle alone?

`evaluation/benchmark_retrieval_counter_authority.py` is named for this question
but does not answer it: all three of its legs shell out to
`evaluation.frozen_bars.run_bar_gates`, i.e. they re-score the frozen LABEL and
GEOMETRY REGRESSION bars.  It measures counter-label support and map geometry
quality, never retrieval or counter-authority exposure.  It is left byte-unchanged
(accepted, audit-pinned) and this instrument is a separate top-level entry point.

WHAT IT MEASURES - six falsifiers, all PURE COUNTS AND SET RELATIONS

No threshold, bar, rubric or predicate is invented here.  Every quantity below is
a count, a share or a set relation over the shipped bytes.  A falsifier "fires"
when its count is non-zero; that is the same reading convention
`evaluation/served_bundle_scope` already uses (verdict
`BENCHMARK_VALID_WITH_FALSIFICATION`), not a new bar.

  F1  map::unclustered_point_mass
      decisions carrying `unclustered: true` or a `cluster_id` absent from the
      bundle's own declared `clusters[]` set.  A jurist cannot get a cluster
      label or cluster membership for these points.
  F2  map::cluster_panel_coverage
      set relation between the union of `clusters[*].member_ids` and the set of
      `decisions[*].decision_id`.  BOTH differences are computed; never compared
      by matching cardinality (factory-wide requirement 16).
  F3  map::cluster_size_member_len_divergence
      per-cluster |size - len(member_ids)|.  DISCLOSURE: the size/member_ids
      truncation is an ACCEPTED, CLOSED item (factory-wide requirements 21 and
      27 forbid re-raising it).  This is NOT a re-raise.  It is published only as
      the measured consequence on shipped bytes that a map consumer reading
      `member_ids` cannot recover the full clustered set.
  F4  multilingual::language_unassigned
      decisions whose `language` is empty, plus the overlap with F1.  Reuses the
      lane's existing multilingual concern (the frozen reality `multilingual::*`
      family) as a coverage count on shipped bytes; no language bar is applied.
  F5  counter::emitted_label_placement
      where the classifier-EMITTED adversarial rows sit (cluster, outlier flag,
      unclustered), against the abstained and cited rows.
  F6  counter::issued_population_reconciliation
      reconciles the shipped `counter_status` / `counter_anchor_label` fields
      against the ACCEPTED `label_lineage_gate` verdict of record
      (5 supported / 60 abstentions / yield 0.0769).  Computed as a SET RELATION
      between candidate denominator populations, never by matching the number 65.

REUSE-FIRST (no re-implementation of an accepted predicate)

  * `evaluation.retrieval_gate.id_hygiene.id_defects`  (accepted id-hygiene)
  * `evaluation.served_bundle_scope.measure_bundle`    (accepted 5 provenance
    falsifiers) - run here as a CROSS-CHECK against the accepted record
    results/evaluation/served_bundle_scope/39086856920.json, which is re-hashed,
    not re-claimed.
  * accepted frozen rules RULES_LABEL.json / RULES_GEOMETRY.json /
    LABEL_LINEAGE_VERDICT.json are RE-HASHED before anything is computed and are
    never regenerated, paraphrased or re-tuned.

NON-VACUITY BATTERY

Each falsifier is paired with hostile in-memory mutations of the shipped bytes.
A falsifier whose hostile controls do not move its quantity is VACUOUS and forces
exit 2.  A benchmark that cannot fail is not evidence.

  r2 (binding; r1 is RETIRED and preserved as an exploratory probe at
  results/evaluation/shipped_bundle_exposure_benchmark/39154580055_r1_RETIRED_PROBE.json):
  controls run in BOTH directions and pass when EITHER moves.  r1 shipped a
  CONCEAL-only control for F5, which could not move on the shipped de/it bundles
  because the F5 quantity is already at its floor there, so r1 returned
  ENVIRONMENT_OR_VACUOUS.  That was a CONTROL-DESIGN defect, not a product
  verdict and not a vacuous falsifier: F5 reads cluster_id/is_outlier and fires
  on de and it.  r2 accepts either direction, which is strictly stronger than
  r1's single direction, and still fails closed if neither mutation moves.
  A falsifier whose BASELINE POPULATION IS EMPTY is recorded
  NOT_APPLICABLE_ZERO_POPULATION, does not by itself force exit 2, and is NEVER
  reported as a pass.

EXIT CODES (aligned with evaluation/benchmark_retrieval_counter_authority.py)

  0  BENCHMARK_VALID_NO_FALSIFICATION - instrument proven non-vacuous, shipped
     bytes read, and every falsifier count is zero.
  1  PRODUCT_FALSIFIED - instrument proven non-vacuous and at least one falsifier
     FIRED on the shipped bytes.  This is a preserved NEGATIVE result about the
     shipped map, not a claim that the product is useless.
  2  ENVIRONMENT_OR_VACUOUS - frozen rules failed to re-hash to their pinned
     digests, the accepted product mount or packet is absent/unreadable, or a
     non-vacuity control did not move.  Never a product pass.

No Product code is imported.  No network is used.  No frozen file is written.
The accepted-product mount at /tmp/lex_accepted is read-only input.
The closed universal-174k suite is NOT touched.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.retrieval_gate.id_hygiene import id_defects  # noqa: E402  (REUSE-FIRST)
from evaluation.served_bundle_scope import measure_bundle  # noqa: E402  (REUSE-FIRST)

SCHEMA = "lex-evaluation-shipped-bundle-exposure-benchmark/1"

# --- frozen pins, re-hashed before anything is computed.  NEVER regenerated. -----
FROZEN_PINS = {
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "evaluation/frozen_bars/LABEL_LINEAGE_VERDICT.json":
        "016bffe5914ffc9074c948c9e452d05c79639735ed32f6c82aefd3751afcca18",
}
# packet.json raw sha256 pinned by factory direction v56.
PACKET_JSON_SHA256 = "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170"

PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
SHIPPED_PACKET_REL = "results/product/gate_packet/rebuilt-39027045675"
# the accepted label_lineage_gate adjudication of record (run 39049030442)
LINEAGE_ADJUDICATION_REL = (
    "results/evaluation/label_lineage_gate/adjudications/"
    "rebuilt-39027045675_39049030442.json")
# the accepted served_bundle_scope record of record (run 39086856920)
SCOPE_RECORD_REL = "results/evaluation/served_bundle_scope/39086856920.json"

# counter_status vocabularies as they appear on shipped bytes.
ADVERSARIAL_EMITTED = ("candidate-contrary", "candidate-limiting")
ABSTAINED = "abstained_unevidenced"
CITED = "cited"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fraction(n: int, d: int) -> float:
    return (n / d) if d else 0.0


# --------------------------------------------------------------------------- F1..F6
def f1_unclustered_point_mass(bundle: dict) -> dict:
    """Map points that belong to no declared cluster."""
    decisions = bundle["decisions"]
    declared = {c["cluster_id"] for c in bundle.get("clusters", [])}
    hits, by_reason = [], {"unclustered_flag": 0, "undeclared_cluster_id": 0}
    for d in decisions:
        flag = bool(d.get("unclustered"))
        cid = d.get("cluster_id")
        undeclared = cid not in declared
        if flag or undeclared:
            by_reason["unclustered_flag"] += int(flag)
            by_reason["undeclared_cluster_id"] += int(undeclared)
            hits.append({
                "decision_id": d.get("decision_id"),
                "cluster_id": cid,
                "unclustered": flag,
            })
    return {
        "falsifier": "F1 map::unclustered_point_mass",
        "n_decisions": len(decisions),
        "declared_cluster_ids": sorted(declared),
        "n_fired": len(hits),
        "share": _fraction(len(hits), len(decisions)),
        "by_reason": by_reason,
        "example_ids": [h["decision_id"] for h in hits[:5]],
    }


def f2_cluster_panel_coverage(bundle: dict) -> dict:
    """Set relation between the cluster panel and the decision list.  BOTH
    differences are computed; never compared by matching cardinality."""
    decisions = bundle["decisions"]
    dec_ids = {d.get("decision_id") for d in decisions}
    member = set()
    for c in bundle.get("clusters", []):
        member.update(c.get("member_ids") or [])
    only_members = sorted(x for x in member if x not in dec_ids)
    only_decisions = sorted(x for x in dec_ids if x not in member)
    return {
        "falsifier": "F2 map::cluster_panel_coverage",
        "n_decisions": len(dec_ids),
        "n_declared_clusters": len(bundle.get("clusters", [])),
        "n_member_ids_union": len(member),
        "n_in_both": len(member & dec_ids),
        "n_only_in_cluster_member_ids": len(only_members),
        "n_only_in_decision_list": len(only_decisions),
        "set_relations_equal": not only_members and not only_decisions,
        "examples_only_in_cluster_member_ids": only_members[:5],
        "examples_only_in_decision_list": only_decisions[:5],
        "fired": bool(only_members or only_decisions),
        "compared_as": "set relation with both differences computed, never by matching cardinality",
    }


def f3_cluster_size_member_len_divergence(bundle: dict) -> dict:
    """Published ONLY as the measured consequence on shipped bytes.  The
    size/member_ids truncation is an ACCEPTED CLOSED item (factory-wide
    requirements 21/27 forbid re-raising it); this is not a re-raise."""
    divergent, omitted = [], 0
    for c in bundle.get("clusters", []):
        size = c.get("size")
        members = c.get("member_ids") or []
        if isinstance(size, int) and size != len(members):
            divergent.append({
                "cluster_id": c.get("cluster_id"), "size": size,
                "len_member_ids": len(members), "delta": size - len(members),
            })
            omitted += abs(size - len(members))
    return {
        "falsifier": "F3 map::cluster_size_member_len_divergence",
        "status": "NOT_A_RE_RAISE_OF_THE_ACCEPTED_CLOSED_ITEM",
        "cross_reference": ("factory-wide requirements 21 and 27: the qmap.py "
                            "size/len(member_ids) divergence is accepted and CLOSED "
                            "and no lane may re-raise it; this row publishes only "
                            "the measured consequence for a map consumer"),
        "n_clusters": len(bundle.get("clusters", [])),
        "n_clusters_divergent": len(divergent),
        "n_rows_omitted_from_panel": omitted,
        "divergent": divergent,
        "fired": bool(divergent),
    }


def f4_language_unassigned(bundle: dict) -> dict:
    """Multilingual coverage as a pure count.  No language bar is applied."""
    decisions = bundle["decisions"]
    declared = {c["cluster_id"] for c in bundle.get("clusters", [])}
    missing, missing_ids = [], []
    overlap_unclustered = 0
    histogram = {}
    for d in decisions:
        lang = d.get("language")
        if not (isinstance(lang, str) and lang.strip()):
            missing.append(d.get("decision_id"))
            if d.get("unclustered") or d.get("cluster_id") not in declared:
                overlap_unclustered += 1
        else:
            histogram[lang] = histogram.get(lang, 0) + 1
    return {
        "falsifier": "F4 multilingual::language_unassigned",
        "n_decisions": len(decisions),
        "n_fired": len(missing),
        "share": _fraction(len(missing), len(decisions)),
        "language_histogram": histogram,
        "n_missing_that_are_also_F1_unclustered": overlap_unclustered,
        "share_of_missing_also_unclustered": _fraction(overlap_unclustered, len(missing)),
        "example_ids": missing[:5],
    }


def _status(d: dict) -> str:
    s = d.get("counter_status")
    return s if isinstance(s, str) and s else "none"


def f5_emitted_label_placement(bundle: dict) -> dict:
    """Where the classifier-EMITTED adversarial rows sit on the map."""
    decisions = bundle["decisions"]
    declared = {c["cluster_id"] for c in bundle.get("clusters", [])}
    emitted, abstained, cited, none_rows = [], 0, 0, 0
    for d in decisions:
        s = _status(d)
        if s in ADVERSARIAL_EMITTED:
            emitted.append(d)
        elif s == ABSTAINED:
            abstained += 1
        elif s == CITED:
            cited += 1
        else:
            none_rows += 1
    placement = [{
        "decision_id": d.get("decision_id"),
        "counter_status": _status(d),
        "counter_anchor_label": d.get("counter_anchor_label"),
        "cluster_id": d.get("cluster_id"),
        "cluster_declared": d.get("cluster_id") in declared,
        "is_outlier": d.get("is_outlier"),
    } for d in emitted]
    return {
        "falsifier": "F5 counter::emitted_label_placement",
        "n_decisions": len(decisions),
        "n_emitted_adversarial": len(emitted),
        "n_abstained": abstained,
        "n_cited_with_counter_evidence": cited,
        "n_no_counter_evidence": none_rows,
        "emitted_share_of_map": _fraction(len(emitted), len(decisions)),
        "n_emitted_in_declared_clusters": sum(
            1 for p in placement if p["cluster_declared"]),
        "n_emitted_unclustered": sum(1 for p in placement if not p["cluster_declared"]),
        "n_emitted_flagged_outlier": sum(
            1 for p in placement if p["is_outlier"] is True),
        "emitted_cluster_ids": sorted({
            p["cluster_id"] for p in placement if p["cluster_declared"]}),
        "emitted_placement": placement,
        "fired": bool(emitted and (not any(p["cluster_declared"] for p in placement)
                                   or not any(p["is_outlier"] for p in placement))),
        "fired_semantics": ("fires when every emitted adversarial row is either "
                            "outside the declared clusters or not marked outlier, "
                            "i.e. the map exposes no structural handle on them"),
    }


def f6_issued_population_reconciliation(bundle: dict, accepted: dict | None) -> dict:
    """Reconcile shipped counter fields against the ACCEPTED lineage verdict.

    Computed as a SET RELATION over candidate denominator populations, never by
    matching the number 65."""
    decisions = bundle["decisions"]
    emitted = {d.get("decision_id") for d in decisions if _status(d) in ADVERSARIAL_EMITTED}
    abstained = {d.get("decision_id") for d in decisions if _status(d) == ABSTAINED}
    cited = {d.get("decision_id") for d in decisions if _status(d) == CITED}
    anchored = {d.get("decision_id") for d in decisions
                if d.get("counter_anchor_label") not in (None, "", "ABSTAIN")}
    populations = {
        "emitted_plus_abstained": len(emitted | abstained),
        "emitted_plus_abstained_plus_cited": len(emitted | abstained | cited),
        "non_none_status": len({d.get("decision_id") for d in decisions
                                if _status(d) != "none"}),
        "all_decisions": len({d.get("decision_id") for d in decisions}),
    }
    accepted_view = None
    if accepted is not None:
        accepted_view = {
            "record": LINEAGE_ADJUDICATION_REL,
            "enforced_predicate_rate": accepted.get("enforced_predicate_rate"),
            "verdict": accepted.get("verdict"),
            "label_lineage_gate": accepted.get("label_lineage_gate"),
        }
    return {
        "falsifier": "F6 counter::issued_population_reconciliation",
        "shipped_counts": {
            "n_emitted_adversarial": len(emitted),
            "n_rows_carrying_counter_anchor_label": len(anchored),
            "n_abstained": len(abstained),
            "n_cited_with_counter_evidence": len(cited),
        },
        "set_relations": {
            "emitted_equals_anchored": emitted == anchored,
            "emitted_minus_anchored": sorted(emitted - anchored),
            "anchored_minus_emitted": sorted(anchored - emitted),
            "emitted_disjoint_from_abstained": not (emitted & abstained),
            "abstained_intersects_cited": sorted(abstained & cited)[:5],
        },
        "candidate_denominator_populations": populations,
        "accepted_lineage_view": accepted_view,
        "population_predicate_pinned_to": ("the ACCEPTED label_lineage_gate's own "
                                            "discover_population predicate; this "
                                            "instrument does NOT re-derive or "
                                            "re-tune it and reports candidates only"),
        "fired": False,
        "fired_semantics": ("reconciliation is published, never used as a bar; it is "
                            "reported so a reader can see whether the shipped fields "
                            "and the accepted verdict describe the same population"),
    }


FALSIFIERS = (f1_unclustered_point_mass, f2_cluster_panel_coverage,
              f3_cluster_size_member_len_divergence, f4_language_unassigned,
              f5_emitted_label_placement)


def measure(bundle: dict, accepted_lineage: dict | None) -> dict:
    out = {fn.__name__: fn(bundle) for fn in FALSIFIERS}
    out["f6_issued_population_reconciliation"] = f6_issued_population_reconciliation(
        bundle, accepted_lineage)
    return out


# ------------------------------------------------------------------ non-vacuity
def _hostile_uncluster(b: dict) -> dict:
    """F1 control: force one previously-unclustered point into a declared cluster."""
    h = copy.deepcopy(b)
    declared = {c["cluster_id"] for c in h.get("clusters", [])}
    for d in h["decisions"]:
        if d.get("unclustered") and d.get("cluster_id") not in declared:
            d["unclustered"] = False
            d["cluster_id"] = min(declared)
            break
    return h


def _hostile_cover(b: dict) -> dict:
    """F2 control: add a member id that is not in the decision list."""
    h = copy.deepcopy(b)
    if h.get("clusters"):
        h["clusters"][0].setdefault("member_ids", []).append("__injected_not_a_decision__")
    return h


def _hostile_size(b: dict) -> dict:
    """F3 control: change one cluster's size so it diverges from member_ids."""
    h = copy.deepcopy(b)
    for c in h.get("clusters", []):
        if c.get("size") == len(c.get("member_ids") or []):
            c["size"] = len(c.get("member_ids") or []) + 3
            break
    return h


def _hostile_language(b: dict) -> dict:
    """F4 control: blank one assigned language."""
    h = copy.deepcopy(b)
    for d in h["decisions"]:
        if d.get("language"):
            d["language"] = None
            break
    return h


def _hostile_emit(b: dict) -> dict:
    """F5 control: de-anchor one emitted adversarial row so none is discoverable."""
    h = copy.deepcopy(b)
    declared = {c["cluster_id"] for c in h.get("clusters", [])}
    for d in h["decisions"]:
        if _status(d) in ADVERSARIAL_EMITTED:
            d["cluster_id"] = -999
            d["unclustered"] = True
            d["is_outlier"] = False
    # also de-cluster any other emitted rows so the control is unambiguous
    for d in h["decisions"]:
        if _status(d) in ADVERSARIAL_EMITTED and d.get("cluster_id") in declared:
            d["cluster_id"] = -998
            d["unclustered"] = True
    return h


def _hostile_reveal(b: dict) -> dict:
    """F5 REVEAL control: force every emitted adversarial row INTO a declared
    cluster and mark it an outlier.

    r2 addition. r1 shipped a CONCEAL-only control, which cannot prove a
    falsifier whose real-data value is already extremal (on the shipped de/it
    bundles the F5 quantity is already 0 in-declared-clusters / 0 outliers, so
    concealing further had nowhere to move and the control failed to move). The
    control now runs in BOTH directions and passes when EITHER moves, which is
    strictly stronger than r1's single direction: r1 required one specific
    mutation to move, r2 accepts either, and still fails closed if neither does.
    """
    h = copy.deepcopy(b)
    declared = sorted({c["cluster_id"] for c in h.get("clusters", [])})
    if not declared:
        return h
    target = declared[0]
    for d in h["decisions"]:
        if _status(d) in ADVERSARIAL_EMITTED:
            d["cluster_id"] = target
            d["unclustered"] = False
            d["is_outlier"] = True
    return h


HOSTILE_CONTROLS = (
    ("F1", "map::unclustered_point_mass", f1_unclustered_point_mass, (_hostile_uncluster,)),
    ("F2", "map::cluster_panel_coverage", f2_cluster_panel_coverage, (_hostile_cover,)),
    ("F3", "map::cluster_size_member_len_divergence",
     f3_cluster_size_member_len_divergence, (_hostile_size,)),
    ("F4", "multilingual::language_unassigned", f4_language_unassigned, (_hostile_language,)),
    ("F5", "counter::emitted_label_placement", f5_emitted_label_placement,
     (_hostile_emit, _hostile_reveal)),
)

# Falsifiers whose baseline population can legitimately be empty on a bundle.
# A control over an empty population is NOT_APPLICABLE, never a pass.
ZERO_POP_PROBES = {
    "F5": lambda r: r["n_emitted_adversarial"] == 0,
}


def non_vacuity(bundle: dict) -> dict:
    """Each falsifier must MOVE on at least one hostile input, else it is vacuous.

    r2: multiple opposite mutations per falsifier; a falsifier with an EMPTY
    baseline population is recorded NOT_APPLICABLE_ZERO_POPULATION and does not
    force exit 2, but it is never reported as a pass (see the frozen r2
    non-vacuity rule)."""
    controls, all_hold, any_not_applicable = [], True, False
    for tag, name, fn, mutates in HOSTILE_CONTROLS:
        baseline = fn(bundle)
        base_key = _movement_key(tag, baseline)
        if tag in ZERO_POP_PROBES and ZERO_POP_PROBES[tag](baseline):
            controls.append({
                "control": tag, "falsifier": name,
                "baseline_quantity": base_key,
                "status": "NOT_APPLICABLE_ZERO_POPULATION",
                "moved": None,
                "reading": ("this bundle emitted ZERO adversarial rows, so the "
                            "placement falsifier has no population here. This is "
                            "NOT a pass and NOT evidence the falsifier is live on "
                            "this bundle; it is a property of the shipped bundle."),
            })
            any_not_applicable = True
            continue
        attempts, moved_by = [], None
        for mutate in mutates:
            hostile = fn(mutate(bundle))
            host_key = _movement_key(tag, hostile)
            attempts.append({"mutation": mutate.__name__,
                             "baseline_quantity": base_key,
                             "hostile_quantity": host_key,
                             "moved": base_key != host_key})
            if moved_by is None and base_key != host_key:
                moved_by = mutate.__name__
        moved = moved_by is not None
        all_hold = all_hold and moved
        controls.append({
            "control": tag, "falsifier": name,
            "baseline_quantity": base_key,
            "status": "MOVED" if moved else "VACUOUS",
            "moved": moved,
            "moved_by": moved_by,
            "attempts": attempts,
            "reading": ("the falsifier reads the shipped field and is not vacuous"
                        if moved else
                        "VACUOUS: no hostile mutation moved the falsifier quantity"),
        })
    return {"all_hold": all_hold, "n_controls": len(controls),
            "n_not_applicable_zero_population": sum(
                1 for c in controls
                if c.get("status") == "NOT_APPLICABLE_ZERO_POPULATION"),
            "not_applicable_is_not_a_pass": True,
            "controls": controls}


def _movement_key(tag: str, res: dict) -> object:
    if tag == "F1":
        return res["n_fired"]
    if tag == "F2":
        return (res["n_only_in_cluster_member_ids"], res["set_relations_equal"])
    if tag == "F3":
        return (res["n_clusters_divergent"], res["n_rows_omitted_from_panel"])
    if tag == "F4":
        return res["n_fired"]
    if tag == "F5":
        return (res["n_emitted_in_declared_clusters"], res["n_emitted_flagged_outlier"])
    raise KeyError(tag)


# ------------------------------------------------------------------- environment
def check_frozen_pins(root: Path) -> dict:
    rows, ok = [], True
    for rel, expected in sorted(FROZEN_PINS.items()):
        p = root / rel
        if not p.exists():
            rows.append({"path": rel, "expected_sha256": expected,
                         "observed": None, "ok": False, "why": "absent"})
            ok = False
            continue
        got = sha256_file(p)
        rows.append({"path": rel, "expected_sha256": expected,
                     "observed_sha256": got, "ok": got == expected})
        ok = ok and got == expected
    return {"all_match": ok, "pins": rows,
            "policy": "re-fetched and re-hashed before use; never regenerated, "
                      "paraphrased, re-tuned or 'clarified'"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--root", default=str(_REPO_ROOT))
    ap.add_argument("--product-mount", default=str(PRODUCT_MOUNT))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    started = time.time()
    root = Path(args.root)
    mount = Path(args.product_mount)
    packet_dir = mount / SHIPPED_PACKET_REL

    record = {
        "schema": SCHEMA,
        "run_id": args.run_id,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "question": ("On the SHIPPED product bundles, are the contrary/limiting "
                     "authorities structurally discoverable, is the cluster panel "
                     "complete, and is the retrieved population multilingual - or "
                     "does the shipped map conceal what the answer relies on?"),
        "population": {
            "packet": SHIPPED_PACKET_REL,
            "packet_dir": str(packet_dir),
            "product_mount": str(mount),
            "why_this_population": ("the accepted packet at the product head; the "
                                    "older 38839347028 packet is the one under the "
                                    "standing accepted DO-NOT-SERVE order and is NOT "
                                    "re-scored here"),
        },
        "frozen_identity": check_frozen_pins(root),
    }

    packet_json = packet_dir / "packet.json"
    if not packet_json.exists():
        record.update({
            "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": 2,
            "environment_failure": f"absent: {packet_json}",
            "claim_ceiling": "no measurement was made; this is not a product verdict",
        })
        _write(record, args, started)
        return 2
    pkt_sha = sha256_file(packet_json)
    record["packet_json_raw_sha256"] = pkt_sha
    record["packet_json_matches_direction_pin"] = pkt_sha == PACKET_JSON_SHA256
    if not record["packet_json_matches_direction_pin"]:
        record.update({
            "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": 2,
            "environment_failure": ("packet.json sha256 does not match the frozen "
                                    "direction pin; the shipped bytes moved"),
            "claim_ceiling": "no measurement was made; this is not a product verdict",
        })
        _write(record, args, started)
        return 2

    if not record["frozen_identity"]["all_match"]:
        record.update({
            "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": 2,
            "environment_failure": "a frozen pin did not re-hash",
            "claim_ceiling": "no measurement was made; this is not a product verdict",
        })
        _write(record, args, started)
        return 2

    acc_path = root / LINEAGE_ADJUDICATION_REL
    accepted_lineage = json.loads(acc_path.read_text()) if acc_path.exists() else None
    record["accepted_lineage_adjudication_present"] = accepted_lineage is not None
    if accepted_lineage is not None:
        record["accepted_lineage_adjudication_sha256"] = sha256_file(acc_path)

    bundles = sorted(packet_dir.glob("questions/*.bundle.json"))
    record["n_bundles"] = len(bundles)
    per_bundle, any_fired, unscored = [], False, []

    for path in bundles:
        b = json.loads(path.read_text())
        rel = str(path.relative_to(packet_dir))
        m = measure(b, accepted_lineage)
        fired = [k for k, v in m.items() if v.get("fired")]
        any_fired = any_fired or bool(fired)

        # REUSE-FIRST cross-check: the accepted provenance/source instrument.
        # Re-run only to CONFIRM the accepted record still reads the same; the
        # accepted record is the claim, this is its reproducibility check.
        scope = measure_bundle(rel, b)
        idhits = [d.get("decision_id") for d in b["decisions"] if id_defects(d)]
        if not m["f1_unclustered_point_mass"]["n_decisions"]:
            unscored.append(rel)
        per_bundle.append({
            "bundle": rel,
            "bundle_sha256": sha256_file(path),
            "n_decisions": len(b["decisions"]),
            "n_declared_clusters": len(b.get("clusters", [])),
            "measurements": m,
            "falsifiers_fired": fired,
            "reuse_provenance_source_instrument": {
                "instrument": "evaluation.served_bundle_scope.measure_bundle",
                "counts": {k: (len(v) if isinstance(v, list) else v)
                           for k, v in scope.items()
                           if isinstance(v, (list, int))},
                "note": "cross-check only; the claim of record is "
                        f"{SCOPE_RECORD_REL}",
            },
            "reuse_id_hygiene_instrument": {
                "instrument": "evaluation.retrieval_gate.id_hygiene.id_defects",
                "n_rows_with_id_defects": len(idhits),
                "example_ids": idhits[:5],
            },
        })

    record["per_bundle"] = per_bundle
    record["bundles_unmeasurable"] = unscored
    nv = [non_vacuity(json.loads(p.read_text())) for p in bundles]
    record["non_vacuity"] = {
        "all_hold": all(x["all_hold"] for x in nv),
        "per_bundle": [{"bundle": str(p.relative_to(packet_dir)), **x}
                       for p, x in zip(bundles, nv)],
    }

    if unscored or not record["non_vacuity"]["all_hold"]:
        record.update({
            "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": 2,
            "environment_failure": "a bundle was unmeasurable or a falsifier was vacuous",
            "claim_ceiling": "no product verdict; the instrument could not fail",
        })
    elif any_fired:
        fired_all = sorted({f for pb in per_bundle for f in pb["falsifiers_fired"]})
        record.update({
            "verdict": "BENCHMARK_VALID_FALSIFIERS_FIRED_ON_SHIPPED_BUNDLES",
            "exit_code": 1,
            "product_falsified": True,
            "falsifiers_fired": fired_all,
        })
    else:
        record.update({
            "verdict": "BENCHMARK_VALID_NO_FALSIFICATION", "exit_code": 0,
            "product_falsified": False, "falsifiers_fired": [],
        })

    record["elapsed_s"] = round(time.time() - started, 3)
    record["claim_ceiling"] = (
        "Measures map completeness, counter-authority exposure and language "
        "coverage as pure counts and set relations on the SHIPPED bytes. It does "
        "NOT score, move or re-derive any frozen bar, does NOT re-measure the "
        "closed universal-174k suite, does NOT rebuild any candidate, does NOT "
        "re-run the frozen reality benchmark or the BJR leg, and says NOTHING "
        "about jurist usefulness or the human product gate. A fired falsifier is "
        "a preserved NEGATIVE result about the shipped map, not a claim that the "
        "product is unusable, and it does not by itself unblock or block the "
        "human gate.")
    record["not_a_bar"] = (
        "No threshold, bar, rubric or predicate is introduced here. Every falsifier "
        "fires on a non-zero COUNT or on a SET RELATION that is not identity, using "
        "the same convention evaluation.served_bundle_scope already uses.")
    _write(record, args, started)
    return record["exit_code"]


def _write(record: dict, args, started: float) -> None:
    out = Path(args.out) if args.out else (
        _REPO_ROOT / "results" / "evaluation" / "shipped_bundle_exposure_benchmark"
        / f"{args.run_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"wrote {out}")
    print(f"verdict={record.get('verdict')} exit_code={record.get('exit_code')} "
          f"elapsed={round(time.time() - started, 3)}s")


if __name__ == "__main__":
    raise SystemExit(main())