#!/usr/bin/env python3
"""Smallest executable counter-authority benchmark that can falsify LexMachina
on the axis the standing accepted DO-NOT-SERVE order is predicated on.

Why this exists
---------------
Direction v50 gave this lane the two executable frozen-bar gates and said: own
the BAR, not the CANDIDATE. Accepted cycle 38993062549 delivered the GEOMETRY
half of that falsification and found the geometry regression verdict
anchor-determined on the product's own lineage. The LABEL half was undelivered,
and the label half is what the DO-NOT-SERVE order actually rests on: the accepted
verdict of record reads "LABEL_UNSOUND, support 5/65 = 0.0769 against a frozen
absolute bar of 1.0".

Two questions, both falsifiable, both on REAL accepted product artifacts:

Q1 (product axis). Under the IDENTICAL frozen RULES_LABEL.json, did the product's
    counter-authority label support actually improve across the accepted
    pre-repair -> post-repair lineage? The frozen rubric itself prescribes this
    measurement: populations.secondary.definition states that a post-repair
    artifact appearing at a later mount must be scored under the identical frozen
    rubric and reported as a before/after pair, and that the file is not re-frozen
    for that. The post-repair artifact now exists on the accepted product mount.

Q2 (bar axis). Is the ACCEPTED counter-label gate safe as the machine
    packet-admission input that Product direction obligation (1) requires? Its
    regression predicate fires only at exactly the incumbent's scored-row
    population, so the question is whether a collapse of label support on any
    other accepted artifact is observable to it at all.

REUSE-FIRST and claim discipline
--------------------------------
* Every support test, defect class, criterion and bar comes from the frozen
  rubric through the ACCEPTED `evaluation.frozen_bars.label_gate` facade. No
  scoring is re-implemented, re-tuned or re-derived (factory-wide requirement 18:
  reuse a frozen rubric by re-hash, never re-derive it).
* Both RULES files are re-hashed to the accepted sha256 BEFORE any scoring.
* The accepted 3-leg entry point `python -m evaluation.benchmark_retrieval_counter_authority`
  is executed UNCHANGED as the non-vacuity positive control.
* The absolute LABEL_SOUND bar (support_rate == 1.0) is REPORTED, never enforced.
  No bar is moved, invented or weakened.
* This module never asserts that any specific decision IS supporting, contrary or
  limiting. Those remain the product's labels; they are measured, not endorsed.

Exit codes (frozen in FROZEN_HYPOTHESIS_39004097533.json)
----------------------------------------------------------
0  BENCHMARK_VALID_PRODUCT_SURVIVES  battery proven, H1 held, >=1 of L2..L6 held
1  PRODUCT_FALSIFIED                 battery proven, H1 did not hold
2  ENVIRONMENT_OR_UNPROVEN           sha drift, empty population, unreadable
                                     artifact, or ANY battery element unproven.
                                     Never a pass, never a product verdict.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.frozen_bars import label_gate  # noqa: E402
from evaluation.packet_lineage_sweep import (  # noqa: E402
    INCUMBENT_PACKET_ID,
    read_audit,
    verify_rules_identity,
)

PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
RESULTS_REL = "results/product"
FROZEN_HYPOTHESIS_PATH = (
    "results/evaluation/counter_authority_label_benchmark/FROZEN_HYPOTHESIS_39004097533.json"
)

QIDS = label_gate.INCUMBENT_QIDS
MATCHED_ANCHOR = "kuendigung-mietrecht"

# Leg 1 population: the accepted pre-repair and post-repair adversarial-retrieval
# artifacts. Every path is relative to <mount>/results/product. The rubric's own
# population_drift_policy is honoured: the file is not re-frozen for them.
BEFORE_ARM = {
    "de": "adversarial_retrieval/38828034436/bundle_de.json",
    "fr": "adversarial_retrieval/38828034436/bundle_fr.json",
    "it": "adversarial_retrieval/38828034436/bundle_it.json",
}
AFTER_ARM = {
    "de": "adversarial_retrieval/38831241913/bundle_de_repaired.json",
    "fr": "adversarial_retrieval/38831241913/bundle_fr_repaired.json",
    "it": "adversarial_retrieval/38831241913/bundle_it_repaired.json",
}
# Recorded out of scope with a reason, never silently dropped (frozen hypothesis).
OUT_OF_SCOPE = {
    "adversarial_retrieval/38838116453": "carries row_tracking_*.json only; no bundle to score",
    "adversarial_retrieval/38828034436/bundle_mietvertrag_kuendigung.json":
        "same query as bundle_de.json in the same run; excluded from the per-language table "
        "so no decision is double counted, scored anyway for completeness",
    "adversarial_retrieval/38831241913/relabel_de_old_rows.json":
        "relabelling ledger, not a bundle",
    "adversarial_retrieval/38831241913/relabel_fr_old_rows.json":
        "relabelling ledger, not a bundle",
    "adversarial_retrieval/38831241913/relabel_it_old_rows.json":
        "relabelling ledger, not a bundle",
    "gate_packet/38838116453": "no it-responsabilita-medica bundle; the three-frozen-qid population predicate cannot be satisfied",
    "gate_packet/offline_machinery_rehearsal": "no frozen qid; fixture_mode per RULES_LABEL excluded_inputs",
}

GATE_PACKET_DIRS = ("38799024807", "38812599575", "38839347028")

EXIT_SURVIVES = 0
EXIT_PRODUCT_FALSIFIED = 1
EXIT_ENVIRONMENT = 2


# ---------------------------------------------------------------- helpers --
def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_frozen_hypothesis() -> dict:
    p = _REPO_ROOT / FROZEN_HYPOTHESIS_PATH
    if not p.exists():
        raise RuntimeError(f"frozen hypothesis missing at {p}; refusing to execute unfrozen")
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------- provenance --
def provenance(path: Path, mount: Path) -> dict:
    """N5: re-hash every in-scope artifact and record WHY it is in scope.

    A finding may never rest on an unverified shas, and an artifact with no
    independent audit record on the mount is labelled as such rather than being
    quietly called accepted.
    """
    rel = str(path.relative_to(mount))
    out: dict = {
        "relpath_under_mount": rel,
        "abs_path": str(path),
        "sha256": _sha256_file(path) if path.exists() else None,
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
    }
    # independent audit gate for this artifact's own cycle, if one is on the mount
    parts = Path(rel).parts
    run_ids = [p for p in parts if p.isdigit() and len(p) == 11]
    if run_ids:
        audit = read_audit(mount, run_ids[0])
        out["independent_audit_gate_on_mount"] = {
            "cycle": run_ids[0],
            "gate": audit.get("gate"),
            "safe_to_integrate": audit.get("safe_to_integrate"),
            "accepted": audit.get("accepted"),
            "audit_file": audit.get("audit_file"),
        }
    return out


def classify_provenance(prov: dict, rules: dict) -> str:
    """One of the four provenance classes named in the frozen hypothesis."""
    rel = prov["relpath_under_mount"]
    if prov.get("independent_audit_gate_on_mount", {}).get("accepted") is True:
        return "independent_audit_gate_PASS_on_mount"
    if rel.startswith("gate_packet/"):
        declared = {i.get("sha256") for i in rules.data.get("inputs", [])}
        if prov["sha256"] in declared:
            return "accepted_frontier_rubric_declared_primary_population"
        return ("named_by_accepted_product_frontier_verdict"
                if rel.split("/")[1] == INCUMBENT_PACKET_ID
                else "product_artifact_without_on_mount_audit_record")
    if rel.startswith("adversarial_retrieval/"):
        return "product_artifact_without_on_mount_audit_record"
    return "product_artifact_without_on_mount_audit_record"


# ------------------------------------------------------------- LEG 1: Q1 --
def score_arm(paths: dict, rules, anchor: str) -> dict:
    """Score one arm under the matched anchor, pooled and per language."""
    per_lang: dict = {}
    for lang, rel in paths.items():
        res = label_gate.score_bundle(str(paths[lang]), rules, anchor)
        per_lang[lang] = {
            "relpath_under_results_product": rel,
            "sha256": res["sha256"],
            "n_decisions": res["n_decisions"],
            "n_scored": res["n_scored"],
            "n_reported_only": res["n_reported_only"],
            "n_supported": res["n_supported"],
            "support_rate": res["support_rate"],
            "classes": res["classes"],
        }
    n_scored = sum(v["n_scored"] for v in per_lang.values())
    n_supported = sum(v["n_supported"] for v in per_lang.values())
    classes: dict = {}
    for v in per_lang.values():
        for k, n in v["classes"].items():
            classes[k] = classes.get(k, 0) + n
    return {
        "anchor_profile": anchor,
        "pooled": {
            "n_scored": n_scored,
            "n_supported": n_supported,
            "support_rate": (n_supported / n_scored) if n_scored else None,
            "classes": classes,
        },
        "per_language": per_lang,
    }


def anchor_fit_spread(paths: dict, rules) -> dict:
    """M4: support_rate under EVERY frozen anchor for the same artifact.

    Descriptive, enforced = false. It exists because kuendigung-mietrecht is a
    German-language domain lexicon applied to FR and IT artifacts: if the
    anchor choice moved the number, the reader must be able to see by how much
    instead of taking the matched-anchor figure on trust.
    """
    anchors = sorted(rules.anchors)
    out: dict = {}
    for lang, rel in paths.items():
        by_anchor: dict = {}
        for a in anchors:
            res = label_gate.score_bundle(str(paths[lang]), rules, a)
            by_anchor[a] = {"n_scored": res["n_scored"],
                            "n_supported": res["n_supported"],
                            "support_rate": res["support_rate"]}
        matched = by_anchor.get(MATCHED_ANCHOR, {})
        others = [v["support_rate"] for k, v in by_anchor.items()
                  if k != MATCHED_ANCHOR and v["support_rate"] is not None]
        out[lang] = {
            "relpath_under_results_product": rel,
            "by_anchor": by_anchor,
            "matched_anchor_support_rate": matched.get("support_rate"),
            "min_other_anchor_support_rate": (min(others) if others else None),
            "anchor_fit_margin": (
                matched["support_rate"] - min(others)
                if matched.get("support_rate") is not None and others else None),
            "enforced": False,
        }
    return out


def predicate_l1(before: dict, after: dict) -> dict:
    """L1 product falsifier, verbatim from the frozen hypothesis."""
    b = before["pooled"]
    a = after["pooled"]
    improved = (b["support_rate"] is not None and a["support_rate"] is not None
                and a["support_rate"] > b["support_rate"])
    inverted = int((a["classes"] or {}).get("INVERTED", 0))
    per_language = {}
    for lang in sorted(set(before["per_language"]) | set(after["per_language"])):
        bl = before["per_language"].get(lang, {})
        al = after["per_language"].get(lang, {})
        per_language[lang] = {
            "before_support_rate": bl.get("support_rate"),
            "after_support_rate": al.get("support_rate"),
            "before_n_scored": bl.get("n_scored"),
            "after_n_scored": al.get("n_scored"),
            "before_n_supported": bl.get("n_supported"),
            "after_n_supported": al.get("n_supported"),
            "delta_support_rate": (
                (al["support_rate"] - bl["support_rate"])
                if al.get("support_rate") is not None and bl.get("support_rate") is not None
                else None),
            "improved": (
                al["support_rate"] > bl["support_rate"]
                if al.get("support_rate") is not None and bl.get("support_rate") is not None
                else None),
        }
    holds = bool(improved and inverted == 0)
    return {
        "id": "L1_product_falsifier",
        "statement": "AFTER.support_rate > BEFORE.support_rate pooled over the three "
                     "languages under the matched anchor AND no INVERTED-class row in AFTER",
        "before_support_rate": b["support_rate"],
        "after_support_rate": a["support_rate"],
        "delta_support_rate": (a["support_rate"] - b["support_rate"]
                               if a["support_rate"] is not None and b["support_rate"] is not None
                               else None),
        "improved": improved,
        "inverted_rows_after": inverted,
        "per_language": per_language,
        "holds": holds,
        "falsified_means": "PRODUCT_FALSIFIED on the counter-authority label axis",
        "enforced": True,
    }


# ------------------------------------------------------------- LEG 2: Q2 --
def score_gate_lineage(mount: Path, rules) -> dict:
    """Run the ACCEPTED gate predicate over every in-scope accepted packet."""
    per_packet: dict = {}
    for pid in GATE_PACKET_DIRS:
        qdir = mount / RESULTS_REL / "gate_packet" / pid / "questions"
        present = {q: (qdir / f"{q}.bundle.json").exists() for q in QIDS}
        if not all(present.values()):
            per_packet[pid] = {"in_scope": False,
                               "reason": f"missing {[q for q, v in present.items() if not v]}"}
            continue
        bundles = {q: str(qdir / f"{q}.bundle.json") for q in QIDS}
        res = label_gate.score_packet(bundles, rules)
        per_packet[pid] = {
            "in_scope": True,
            "questions_dir": str(qdir),
            "n_scored": res["n_scored"],
            "n_supported": res["n_supported"],
            "support_rate": res["support_rate"],
            "classes": res["classes"],
            "lineage_matches_incumbent_population": res["lineage_matches_incumbent_population"],
            "regression_verdict": res["regression_verdict"],
            "gate_blocks_build": res["gate_blocks_build"],
            "absolute_status": res["absolute_status"],
            "absolute_enforced_as_build_blocker": res["absolute_enforced_as_build_blocker"],
            "per_bundle": {
                q: {"n_scored": b["n_scored"], "n_supported": b["n_supported"],
                    "support_rate": b["support_rate"], "classes": b["classes"],
                    "n_decisions": b["n_decisions"]}
                for q, b in res["per_bundle"].items()
            },
            "bundle_sha256": {q: b["sha256"] for q, b in res["per_bundle"].items()},
        }
    return per_packet


def shared_id_sensitivity(before_paths: dict, after_paths: dict, rules) -> dict:
    """DISCLOSED CONFOUND CONTROL, not part of the frozen predicate L1.

    The before and after arms carry the SAME query text but NOT the same retrieved
    decision population: the de arm swaps 14 rows out and 12 in, fr swaps 22 and
    24. A pooled support-rate delta across different candidate sets therefore
    mixes (a) the repair's relabelling, (b) retrieval non-determinism between the
    two runs, and (c) anchor-fit effects.

    This control re-scores BOTH arms restricted to the decision ids they share, so
    the remaining delta is attributable to labelling alone. It is descriptive,
    enforced = false, and it does NOT change L1 or the exit code: the frozen
    success rule was committed before this confound was known and is not relaxed
    now that relaxing it would favour the product.
    """
    per_lang: dict = {}
    tmpdir = Path(tempfile.mkdtemp(prefix="shared_id_"))
    try:
        for lang in sorted(set(before_paths) & set(after_paths)):
            b = json.loads(before_paths[lang].read_text(encoding="utf-8"))
            a = json.loads(after_paths[lang].read_text(encoding="utf-8"))
            b_ids = {d.get("decision_id") for d in (b.get("decisions") or [])}
            a_ids = {d.get("decision_id") for d in (a.get("decisions") or [])}
            shared = b_ids & a_ids
            paths = {}
            for tag, bundle in (("before", b), ("after", a)):
                bundle["decisions"] = [d for d in (bundle.get("decisions") or [])
                                       if d.get("decision_id") in shared]
                p = tmpdir / f"{tag}_{lang}.json"
                p.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
                paths[tag] = p
            res = {tag: label_gate.score_bundle(str(p), rules, MATCHED_ANCHOR)
                   for tag, p in paths.items()}
            changed = [
                {"decision_id": d.get("decision_id"),
                 "before": d.get("counter_status"),
                 "after": (next((x for x in (a.get("decisions") or [])
                                 if x.get("decision_id") == d.get("decision_id")),
                                {}) or {}).get("counter_status")}
                for d in (b.get("decisions") or [])
                if d.get("decision_id") in shared
                and (d.get("counter_status") or "none")
                != ((next((x for x in (a.get("decisions") or [])
                           if x.get("decision_id") == d.get("decision_id")), {}) or {})
                   .get("counter_status") or "none")
            ]
            per_lang[lang] = {
                "n_before": len(b_ids),
                "n_after": len(a_ids),
                "n_shared": len(shared),
                "n_only_before": len(b_ids - a_ids),
                "n_only_after": len(a_ids - b_ids),
                "n_changed_counter_status_among_shared": len(changed),
                "changed_rows": changed[:20],
                "before_on_shared": {"n_scored": res["before"]["n_scored"],
                                     "n_supported": res["before"]["n_supported"],
                                     "support_rate": res["before"]["support_rate"],
                                     "classes": res["before"]["classes"]},
                "after_on_shared": {"n_scored": res["after"]["n_scored"],
                                    "n_supported": res["after"]["n_supported"],
                                    "support_rate": res["after"]["support_rate"],
                                    "classes": res["after"]["classes"]},
                "delta_support_rate_on_shared": (
                    res["after"]["support_rate"] - res["before"]["support_rate"]
                    if res["before"]["support_rate"] is not None
                    and res["after"]["support_rate"] is not None else None),
            }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    pooled_b_n = sum(v["before_on_shared"]["n_scored"] for v in per_lang.values())
    pooled_b_s = sum(v["before_on_shared"]["n_supported"] for v in per_lang.values())
    pooled_a_n = sum(v["after_on_shared"]["n_scored"] for v in per_lang.values())
    pooled_a_s = sum(v["after_on_shared"]["n_supported"] for v in per_lang.values())
    return {
        "why": "the before/after arms are two different retrievals of the same query, not one "
               "repaired candidate set; restricting to shared decision ids isolates the "
               "labelling effect from retrieval non-determinism",
        "enforced": False,
        "part_of_frozen_predicate_L1": False,
        "does_not_change_the_verdict": "L1 and the exit code are untouched; this control was "
                                       "added after the confound was discovered, i.e. in the "
                                       "direction that WEAKENS the product falsification, and "
                                       "was deliberately not allowed to relax the frozen rule",
        "per_language": per_lang,
        "pooled_on_shared": {
            "before_n_scored": pooled_b_n,
            "before_n_supported": pooled_b_s,
            "before_support_rate": (pooled_b_s / pooled_b_n) if pooled_b_n else None,
            "after_n_scored": pooled_a_n,
            "after_n_supported": pooled_a_s,
            "after_support_rate": (pooled_a_s / pooled_a_n) if pooled_a_n else None,
            "delta_support_rate": ((pooled_a_s / pooled_a_n) - (pooled_b_s / pooled_b_n)
                                   if pooled_b_n and pooled_a_n else None),
        },
    }


def predicate_l2_l3_l4_l6(per_packet: dict) -> dict:
    inc = per_packet.get(INCUMBENT_PACKET_ID, {})
    inc_rate = inc.get("support_rate")
    inc_sup = inc.get("n_supported")
    others = {pid: r for pid, r in per_packet.items()
              if r.get("in_scope") and pid != INCUMBENT_PACKET_ID}
    admissible = [pid for pid, r in per_packet.items() if r.get("lineage_matches_incumbent_population")]

    l2_firing = [pid for pid, r in others.items()
                 if inc_rate is not None and r.get("support_rate") is not None
                 and r["support_rate"] < inc_rate
                 and r.get("n_supported") is not None and inc_sup is not None
                 and r["n_supported"] < inc_sup
                 and r.get("regression_verdict") != "FAIL_REGRESSION"
                 and r.get("gate_blocks_build") is False]

    l4_firing = [pid for pid, r in others.items()
                 if inc_rate is not None and r.get("support_rate") is not None
                 and r["support_rate"] > inc_rate
                 and r.get("n_supported") is not None and inc_sup is not None
                 and r["n_supported"] < inc_sup]

    by_count = sorted(
        ((r["n_supported"], pid) for pid, r in per_packet.items() if r.get("in_scope")),
        key=lambda t: (t[0], t[1]))
    by_rate = sorted(
        ((r["support_rate"], pid) for pid, r in per_packet.items() if r.get("in_scope")),
        key=lambda t: (t[0], t[1]))
    count_order = [pid for _, pid in by_count]
    rate_order = [pid for _, pid in by_rate]

    return {
        "L2_gate_admits_total_label_collapse": {
            "id": "L2_gate_admits_total_label_collapse",
            "statement": "exists an accepted-lineage artifact A != incumbent with "
                         "support_rate(A) < support_rate(incumbent) AND n_supported(A) < "
                         "INCUMBENT.n_supported, whose ACCEPTED-gate regression_verdict is "
                         "not FAIL_REGRESSION and whose gate_blocks_build is false",
            "incumbent": {"packet_id": INCUMBENT_PACKET_ID,
                          "support_rate": inc_rate, "n_supported": inc_sup,
                          "n_scored": inc.get("n_scored")},
            "firing_packets": sorted(l2_firing),
            "holds": len(l2_firing) >= 1,
            "enforced": True,
            "reading": "the gate cannot observe a collapse of counter-label support on "
                       "this lineage, so gate_blocks_build alone is unsafe as the sole "
                       "machine packet-admission input Product obligation (1) requires",
        },
        "L3_gate_population_predicate_is_confounded": {
            "id": "L3_gate_population_predicate_is_confounded",
            "statement": "the set of accepted-lineage artifacts for which the accepted gate "
                         "can return any regression verdict has cardinality 1 while the "
                         "lineage carries more than one artifact with the three frozen qids",
            "n_in_scope_packets": sum(1 for r in per_packet.values() if r.get("in_scope")),
            "n_admissible_packets": len(admissible),
            "admissible_packets": sorted(admissible),
            "scored_row_populations": {pid: r.get("n_scored")
                                       for pid, r in per_packet.items() if r.get("in_scope")},
            "holds": (len(admissible) == 1
                      and sum(1 for r in per_packet.values() if r.get("in_scope")) > 1),
            "enforced": True,
        },
        "L4_rate_and_count_semantics_disagree": {
            "id": "L4_rate_and_count_semantics_disagree",
            "statement": "exists an accepted-lineage artifact A with support_rate(A) > "
                         "support_rate(incumbent) AND n_supported(A) < INCUMBENT.n_supported",
            "firing_packets": sorted(l4_firing),
            "holds": len(l4_firing) >= 1,
            "enforced": True,
            "reading": "the gate's regression predicate (absolute count at a fixed population) "
                       "and its absolute bar (rate == 1.0) encode different notions of "
                       "improvement; at a matched population the gate would FAIL an artifact "
                       "with a strictly BETTER support rate",
        },
        "L6_anchor_ordering_is_not_quality_ordering": {
            "id": "L6_anchor_ordering_is_not_quality_ordering",
            "statement": "ordering the accepted-lineage artifacts by n_supported does not "
                         "reproduce the ordering by support_rate",
            "order_by_n_supported": count_order,
            "order_by_support_rate": rate_order,
            "orderings_agree": count_order == rate_order,
            "holds": count_order != rate_order,
            "enforced": True,
            "reading": "the verdict is a monotone function of the DECLARED anchor's row count "
                       "and not of measured label quality; this is the label-side counterpart "
                       "of accepted finding F5 for the geometry gate",
        },
    }


def predicate_l5(rules: dict, per_packet: dict) -> dict:
    """Compare declared vs incumbent inputs as SET RELATIONS with both differences.

    Factory discipline: never infer equality from matching cardinality.
    """
    inc = per_packet.get(INCUMBENT_PACKET_ID, {})
    inc_shas = set((inc.get("bundle_sha256") or {}).values())
    declared_shas = {i.get("sha256") for i in rules.data.get("inputs", []) if i.get("sha256")}
    declared_qids = {i.get("qid") for i in rules.data.get("inputs", []) if i.get("qid")}
    req_min = rules.data["populations"]["primary"].get("required_min_population_primary")
    gate_min = label_gate.INCUMBENT.get("n_scored")
    primary_def = rules.data["populations"]["primary"].get("definition", "")
    return {
        "id": "L5_frozen_rubric_population_and_gate_incumbent_disagree",
        "compared_as": "set relation with both differences computed, never matching cardinality",
        "rubric_declared_input_sha256_set": sorted(s for s in declared_shas if s),
        "incumbent_packet_bundle_sha256_set": sorted(s for s in inc_shas if s),
        "sets_equal": declared_shas == inc_shas,
        "declared_not_incumbent": sorted(s for s in declared_shas - inc_shas if s),
        "incumbent_not_declared": sorted(s for s in inc_shas - declared_shas if s),
        "cardinality_matched_but_sets_differ": (len(declared_shas) == len(inc_shas)
                                                and declared_shas != inc_shas),
        "rubric_required_min_population_primary": req_min,
        "gate_pinned_n_scored": gate_min,
        "population_constants_equal": req_min == gate_min,
        "rubric_primary_population_definition": primary_def,
        "rubric_declared_input_qids": sorted(q for q in declared_qids if q),
        "holds": bool(declared_shas != inc_shas) and (req_min != gate_min),
        "enforced": True,
        "not_a_repair": "re-deriving, re-pointing or re-freezing RULES_LABEL.json is out of this "
                        "lane's scope; the divergence is recorded, never resolved here",
    }


# ------------------------------------------------------ non-vacuity battery --
def _write_packet(packet_dir: Path, bundles: dict) -> None:
    packet_dir.mkdir(parents=True, exist_ok=True)
    for qid, bundle in bundles.items():
        (packet_dir / f"{qid}.bundle.json").write_text(
            json.dumps(bundle, ensure_ascii=False), encoding="utf-8")


def _load_served(mount: Path) -> dict:
    qdir = mount / RESULTS_REL / "gate_packet" / INCUMBENT_PACKET_ID / "questions"
    return {qid: json.loads((qdir / f"{qid}.bundle.json").read_text(encoding="utf-8"))
            for qid in QIDS}


def _set_one_scored_row(bundles: dict, delta: int, scored_statuses) -> dict:
    """Shift the incumbent's scored-row population by exactly +delta or -delta.

    delta == -1 removes one scored row (a scored status becomes 'none');
    delta == +1 mints one scored row from an unlabelled decision. Nothing else
    is touched, so n_scored moves by exactly |delta| and every other field the
    rubric reads is byte-identical.
    """
    out = copy.deepcopy(bundles)
    moved = None
    scored = set(scored_statuses)
    for qid in QIDS:
        decisions = out[qid].get("decisions") or []
        if delta < 0:
            for d in decisions:
                if (d.get("counter_status") or "none") in scored:
                    d["counter_status"] = "none"
                    moved = {"qid": qid, "decision_id": d.get("decision_id"), "delta": delta}
                    break
        else:
            for d in decisions:
                if (d.get("counter_status") or "none") == "none":
                    d["counter_status"] = "candidate-limiting"
                    moved = {"qid": qid, "decision_id": d.get("decision_id"), "delta": delta}
                    break
        if moved:
            break
    return {"bundles": out, "moved": moved}


def battery(mount: Path, rules, per_packet: dict, run_id: str, out_dir: Path) -> dict:
    """N1..N5. Every element must hold or the benchmark is exit 2."""
    bat: dict = {}

    # N1 POSITIVE: the accepted 3-leg entry point must prove both gates still fire.
    cmd = [sys.executable, "-m", "evaluation.benchmark_retrieval_counter_authority",
           "--run-id", f"{run_id}_n1"]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(_REPO_ROOT), capture_output=True,
                          text=True, timeout=1800, env=env)
    n1_record = None
    for cand in (out_dir / f"{run_id}_n1.json",
                 _REPO_ROOT / "results/evaluation/retrieval_counter_authority_benchmark"
                             / f"{run_id}_n1.json"):
        if cand.exists():
            try:
                n1_record = json.loads(cand.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                n1_record = None
            break
    legs_raw = (n1_record or {}).get("legs")
    if isinstance(legs_raw, list):
        legs = {lg.get("leg"): lg.get("exit_code") for lg in legs_raw
                if isinstance(lg, dict)}
        leg_expectations = {lg.get("leg"): lg.get("exit_code_matches_expectation")
                            for lg in legs_raw if isinstance(lg, dict)}
    else:
        legs = (n1_record or {}).get("leg_exits") or {}
        leg_expectations = {}
    bat["N1_positive_must_fire"] = {
        "definition": "the accepted 3-leg entry point reports falsification_proven == true "
                      "with legs served_baseline 0 / geometry_falsification_hostile 1 / "
                      "label_falsification_blanked_evidence 1",
        "entry_point": "python -m evaluation.benchmark_retrieval_counter_authority (accepted, unmodified)",
        "exit_code": proc.returncode,
        "elapsed_s": round(time.time() - t0, 3),
        "record_found": n1_record is not None,
        "verdict": (n1_record or {}).get("verdict"),
        "falsification_proven": (n1_record or {}).get("falsification_proven"),
        "leg_exits": legs,
        "leg_exit_codes_match_expectation": leg_expectations,
        "holds": bool((n1_record or {}).get("falsification_proven") is True
                      and legs.get("served_baseline") == 0
                      and legs.get("geometry_falsification_hostile") == 1
                      and legs.get("label_falsification_blanked_evidence") == 1),
        "meaning_if_broken": "the falsification paths are unreachable, so every 'the gate could "
                             "have caught it' statement here would be vacuous",
    }

    # N2 NEGATIVE: the incumbent must not fire.
    inc = per_packet.get(INCUMBENT_PACKET_ID, {})
    bat["N2_negative_incumbent_must_not_fire"] = {
        "definition": "packet 38839347028 returns PASS_NO_REGRESSION and gate_blocks_build false",
        "observed_verdict": inc.get("regression_verdict"),
        "observed_gate_blocks_build": inc.get("gate_blocks_build"),
        "holds": (inc.get("regression_verdict") == "PASS_NO_REGRESSION"
                  and inc.get("gate_blocks_build") is False),
    }

    # N3 rules identity.
    ident = verify_rules_identity()
    bat["N3_rules_identity"] = {
        "definition": "RULES_LABEL.json re-hashes to 4457e971... and RULES_GEOMETRY.json to "
                      "a7452748... BEFORE any scoring",
        "observed": ident,
        "holds": bool(ident.get("all_match")),
        "meaning_if_broken": "environment error, not a verdict: a re-derived or edited rubric "
                             "would invalidate the bar",
    }

    # N4 population sensitivity: the gate predicate must go blind at 64 and 66 rows.
    served = _load_served(mount)
    scored_statuses = list(rules.rubric["scored_statuses"])
    n4: dict = {"definition": "synthetic copies of the incumbent packet at n_scored 64 and 66 "
                              "both return NOT_APPLICABLE with gate_blocks_build false, proving "
                              "L3 is structural and not a data accident",
                "scored_statuses_from_frozen_rubric": scored_statuses,
                "cases": {}}
    for delta in (-1, +1):
        shifted = _set_one_scored_row(served, delta, scored_statuses)
        tmp = Path(tempfile.mkdtemp(prefix=f"n4_{delta:+d}_"))
        try:
            _write_packet(tmp, shifted["bundles"])
            res = label_gate.score_packet(
                {q: str(tmp / f"{q}.bundle.json") for q in QIDS}, rules)
            n4["cases"][f"n_scored_{res['n_scored']}"] = {
                "delta": delta,
                "moved_row": shifted["moved"],
                "n_scored": res["n_scored"],
                "n_supported": res["n_supported"],
                "support_rate": res["support_rate"],
                "regression_verdict": res["regression_verdict"],
                "gate_blocks_build": res["gate_blocks_build"],
                "absolute_status": res["absolute_status"],
                "observed_not_applicable": (res["regression_verdict"] == "NOT_APPLICABLE"
                                            and res["gate_blocks_build"] is False),
            }
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    n4["n_scored_seen"] = sorted(n4["cases"])
    n4["holds"] = (
        set(n4["cases"]) == {"n_scored_64", "n_scored_66"}
        and all(c["observed_not_applicable"] for c in n4["cases"].values())
    )
    bat["N4_population_sensitivity"] = n4

    return bat


# ------------------------------------------------------------------- main --
def _claim_bearing_strings(node, path="$") -> list:
    """Every string in the record, addressed by path, for the claim scan."""
    out: list = []
    if isinstance(node, str):
        out.append((path, node))
    elif isinstance(node, dict):
        for k in sorted(node):
            out.extend(_claim_bearing_strings(node[k], f"{path}.{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(_claim_bearing_strings(v, f"{path}[{i}]"))
    return out


def forbidden_construction_scan(rec: dict, mount: Path) -> dict:
    """Self-policing: never assert that a decision IS contrary/limiting/supporting.

    The forbidden patterns are REUSED from the accepted product verdict adoption
    file, never re-invented here. If the file is absent the scan is reported as
    NOT_RUN with its reason; a skipped scan is never a silent pass.
    """
    src = (mount / RESULTS_REL / "frontier_verdicts"
           / "ACCEPTED_frontier-served-packet-falsification_38880639079.json")
    if not src.exists():
        return {"status": "NOT_RUN",
                "reason": f"accepted verdict-adoption file absent at {src}",
                "n_violations": None}
    patterns = json.loads(src.read_text(encoding="utf-8")).get(
        "forbidden_construction_patterns") or []
    hits = []
    for path, text in _claim_bearing_strings(rec):
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                hits.append({"json_path": path, "pattern": pat, "text": text[:200]})
    return {
        "status": "RUN",
        "patterns_source": str(src),
        "patterns_source_sha256": _sha256_file(src),
        "n_patterns": len(patterns),
        "n_violations": len(hits),
        "violations": hits[:20],
        "clean": len(hits) == 0,
        "meaning": "this lane measures the SUPPORT of labels the product issued; it never "
                   "asserts that a named decision IS supporting, contrary or limiting",
    }


def check_record_coherence(rec: dict) -> tuple[bool, list]:
    """Arithmetic and contract self-check. Used by this module and by its tests.

    A benchmark that cannot check its own record is a benchmark whose verdicts
    cannot be audited, so the rules live in code and are enforced, not described.
    """
    problems: list = []

    def want(cond, msg):
        if not cond:
            problems.append(msg)

    verdict = rec.get("verdict")
    want(verdict in {"BENCHMARK_VALID_PRODUCT_SURVIVES", "PRODUCT_FALSIFIED",
                     "BENCHMARK_VALID_NO_FINDING", "ENVIRONMENT_OR_UNPROVEN"},
         f"unknown verdict {verdict!r}")
    want(rec.get("schema") == "lex-counter-authority-label-benchmark/1",
         "record schema is not the declared one")

    l1 = ((rec.get("leg1_product_axis") or {}).get("L1")) or {}
    if l1:
        recomputed = bool((l1.get("improved") is True)
                          and (l1.get("inverted_rows_after") == 0))
        want(l1.get("holds") == recomputed,
             f"L1.holds {l1.get('holds')!r} != recomputed {recomputed} "
             f"(improved={l1.get('improved')!r}, inverted_after="
             f"{l1.get('inverted_rows_after')!r})")

    preds = ((rec.get("leg2_bar_axis") or {}).get("predicates")) or {}
    l2 = preds.get("L2_gate_admits_total_label_collapse") or {}
    want(l2.get("holds") == bool(l2.get("firing_packets")),
         "L2.holds does not match len(firing_packets)")
    l3 = preds.get("L3_gate_population_predicate_is_confounded") or {}
    want(l3.get("holds") == ((l3.get("n_admissible_packets") == 1)
                             and ((l3.get("n_in_scope_packets") or 0) > 1)),
         "L3.holds does not match (n_admissible == 1 and n_in_scope > 1)")
    l4 = preds.get("L4_rate_and_count_semantics_disagree") or {}
    want(l4.get("holds") == bool(l4.get("firing_packets")),
         "L4.holds does not match len(firing_packets)")
    l6 = preds.get("L6_anchor_ordering_is_not_quality_ordering") or {}
    want(l6.get("holds") == (l6.get("orderings_agree") is False),
         "L6.holds does not match orderings_agree is False")

    # Verdict / exit-code coherence, exactly as the frozen success rule states.
    nv = rec.get("non_vacuity_all_hold")
    expected = {
        False: ("ENVIRONMENT_OR_UNPROVEN", EXIT_ENVIRONMENT),
        True: (None, None),
    }
    if nv is False:
        want(verdict == "ENVIRONMENT_OR_UNPROVEN",
             "non-vacuity did not hold but the verdict is not ENVIRONMENT_OR_UNPROVEN")
    elif l1 and not l1.get("holds"):
        want(verdict == "PRODUCT_FALSIFIED",
             f"L1 did not hold so the frozen rule requires PRODUCT_FALSIFIED, got {verdict!r}")
    elif rec.get("gate_findings_fired"):
        want(verdict == "BENCHMARK_VALID_PRODUCT_SURVIVES",
             f"gate findings fired but the verdict is {verdict!r}")

    # The absolute bar is reported, never enforced. This must hold unconditionally.
    want(rec.get("absolute_bar", {}).get("enforced_as_build_blocker") is False,
         "the absolute bar is marked as a build blocker, which direction v50 forbids")

    scan = rec.get("forbidden_construction_scan") or {}
    if scan.get("status") == "RUN":
        want(scan.get("clean") is True,
             f"forbidden-construction scan found {scan.get('n_violations')} violation(s)")

    # Every artifact that carries a finding must have a re-hashed sha256.
    for pr in rec.get("population_provenance") or []:
        want(pr.get("present") is True and pr.get("sha256"),
             f"artifact without a verified sha256: {pr.get('relpath_under_mount')!r}")
        want(bool(pr.get("provenance_class")),
             f"artifact without a provenance class: {pr.get('relpath_under_mount')!r}")

    return (not problems), problems


def run(run_id: str, mount: Path, out_dir: Path, report_dir: Path) -> tuple[int, dict]:
    started = time.time()
    frozen = load_frozen_hypothesis()
    rec: dict = {
        "schema": "lex-counter-authority-label-benchmark/1",
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": 50,
        "generated_at": _now(),
        "started_at": datetime.fromtimestamp(started, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "product_mount": str(mount),
        "frozen_hypothesis": {
            "path": FROZEN_HYPOTHESIS_PATH,
            "sha256": _sha256_file(_REPO_ROOT / FROZEN_HYPOTHESIS_PATH),
            "frozen_at_commit": "10135a0f (the commit that introduced the frozen hypothesis file)",
            "frozen_before_execution": True,
            "pre_freeze_disclosure_present": bool(frozen.get("pre_freeze_disclosure")),
        },
        "reuse_first": {
            "label_engine": "evaluation.frozen_bars.label_gate (accepted; called, never re-implemented)",
            "n1_entry_point": "python -m evaluation.benchmark_retrieval_counter_authority (accepted, unmodified)",
            "rules_label_sha256": label_gate.EXPECTED_RULES_SHA256,
            "rules_geometry_sha256": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
            "no_product_code_imported": True,
            "no_frontier_candidate_remeasured": True,
            "no_174k_rerun": True,
            "no_network": True,
        },
        "absolute_bar": {
            "LABEL_SOUND_support_rate": 1.0,
            "enforced_as_build_blocker": False,
            "rule": "direction v50: the absolute bar is REPORTED, never enforced",
        },
        "out_of_scope_recorded_with_reason": OUT_OF_SCOPE,
    }

    # N3 first: a rubric drift is an environment failure, never a verdict.
    rules_identity = verify_rules_identity()
    rec["rules_identity"] = rules_identity
    if not rules_identity.get("all_match"):
        rec["verdict"] = "ENVIRONMENT_OR_UNPROVEN"
        rec["environment_failure"] = "frozen RULES file sha256 drift; refusing to score"
        rec["elapsed_s"] = round(time.time() - started, 3)
        _write(rec, out_dir, run_id)
        return EXIT_ENVIRONMENT, rec

    try:
        rules = label_gate.load_frozen_rules()
    except Exception as e:  # noqa: BLE001
        rec["verdict"] = "ENVIRONMENT_OR_UNPROVEN"
        rec["environment_failure"] = f"frozen rules unloadable: {type(e).__name__}: {e}"
        rec["elapsed_s"] = round(time.time() - started, 3)
        _write(rec, out_dir, run_id)
        return EXIT_ENVIRONMENT, rec

    # ------------------------------------------------------ LEG 1: Q1 ------
    before_paths, after_paths = {}, {}
    prov: list = []
    for lang, rel in BEFORE_ARM.items():
        p = mount / RESULTS_REL / rel
        before_paths[lang] = p
        pr = provenance(p, mount)
        pr["arm"] = "before"
        pr["provenance_class"] = classify_provenance(pr, rules)
        prov.append(pr)
    for lang, rel in AFTER_ARM.items():
        p = mount / RESULTS_REL / rel
        after_paths[lang] = p
        pr = provenance(p, mount)
        pr["arm"] = "after"
        pr["provenance_class"] = classify_provenance(pr, rules)
        prov.append(pr)
    rec["population_provenance"] = prov

    missing = [pr["relpath_under_mount"] for pr in prov if not pr["present"]]
    if missing:
        rec["verdict"] = "ENVIRONMENT_OR_UNPROVEN"
        rec["environment_failure"] = f"in-scope artifacts absent from the accepted mount: {missing}"
        rec["elapsed_s"] = round(time.time() - started, 3)
        _write(rec, out_dir, run_id)
        return EXIT_ENVIRONMENT, rec

    before = score_arm(before_paths, rules, MATCHED_ANCHOR)
    after = score_arm(after_paths, rules, MATCHED_ANCHOR)
    rec["leg1_product_axis"] = {
        "question": "did the accepted pre-repair -> post-repair repair improve counter-label support?",
        "anchor_profile": MATCHED_ANCHOR,
        "anchor_selection": "the only frozen anchor whose domain/pivot lexicon covers "
                            "Mietvertrag-Kuendigung; every in-scope artifact carries the "
                            "rent-default question in DE/FR/IT",
        "rubric_instruction_followed": "RULES_LABEL.json populations.secondary.definition: a "
                                       "post-repair artifact appearing at a later mount must be "
                                       "scored under the identical frozen rubric and reported as "
                                       "a before/after pair; this file is not re-frozen for that",
        "before": before,
        "after": after,
        "anchor_fit_spread": {
            "enforced": False,
            "before": anchor_fit_spread(before_paths, rules),
            "after": anchor_fit_spread(after_paths, rules),
        },
        "shared_id_sensitivity": shared_id_sensitivity(before_paths, after_paths, rules),
        "L1": predicate_l1(before, after),
    }

    # ------------------------------------------------------ LEG 2: Q2 ------
    per_packet = score_gate_lineage(mount, rules)
    preds = predicate_l2_l3_l4_l6(per_packet)
    rec["leg2_bar_axis"] = {
        "question": "is the ACCEPTED counter-label gate observable on, and safe as packet "
                    "admission over, the product's own accepted lineage?",
        "gate_predicate_source": "evaluation/frozen_bars/label_gate.py::score_packet (accepted)",
        "incumbent_of_record": dict(label_gate.INCUMBENT),
        "incumbent_packet_id": INCUMBENT_PACKET_ID,
        "per_packet": per_packet,
        "predicates": preds,
        "L5": predicate_l5(rules, per_packet),
    }

    # ------------------------------------------------------ LEG 3: N1..N4 --
    rec["non_vacuity_battery"] = battery(mount, rules, per_packet, run_id, out_dir)
    rec["non_vacuity_all_hold"] = all(
        v.get("holds") for v in rec["non_vacuity_battery"].values()
        if isinstance(v, dict) and "holds" in v)

    # ------------------------------------------------------- verdict ------
    l1 = rec["leg1_product_axis"]["L1"]
    gate_findings = [pid for pid in ("L2_gate_admits_total_label_collapse",
                                     "L3_gate_population_predicate_is_confounded",
                                     "L4_rate_and_count_semantics_disagree",
                                     "L6_anchor_ordering_is_not_quality_ordering")
                     if preds[pid]["holds"]]
    gate_findings.append("L5_frozen_rubric_population_and_gate_incumbent_disagree"
                         if rec["leg2_bar_axis"]["L5"]["holds"] else None)
    gate_findings = [f for f in gate_findings if f]

    if not rec["non_vacuity_all_hold"]:
        verdict, rc = "ENVIRONMENT_OR_UNPROVEN", EXIT_ENVIRONMENT
        reason = ("a non-vacuity element did not hold, so every finding is suppressed; this is "
                  "NOT a pass and NOT a product verdict")
    elif not l1["holds"]:
        verdict, rc = "PRODUCT_FALSIFIED", EXIT_PRODUCT_FALSIFIED
        reason = ("counter-label support did not improve across the accepted repair under the "
                  "identical frozen rubric (or an INVERTED-class row appeared post-repair)")
    elif gate_findings:
        verdict, rc = "BENCHMARK_VALID_PRODUCT_SURVIVES", EXIT_SURVIVES
        reason = ("the product's counter-label support improved, and the accepted gate is "
                  "falsified as a sole machine packet-admission input")
    else:
        verdict, rc = "BENCHMARK_VALID_NO_FINDING", EXIT_SURVIVES
        reason = "battery proven, H1 held, and no gate predicate fired"

    rec["gate_findings_fired"] = gate_findings
    rec["verdict"] = verdict
    rec["verdict_rationale"] = reason
    rec["product_falsified"] = (rc == EXIT_PRODUCT_FALSIFIED)
    rec["absolute_status_reported_not_enforced"] = {
        "before_support_rate": before["pooled"]["support_rate"],
        "after_support_rate": after["pooled"]["support_rate"],
        "absolute_bar": 1.0,
        "enforced_as_build_blocker": False,
    }
    rec["claim_ceiling"] = frozen["claim_ceiling"]
    rec["product_decision_unlocked"] = frozen["product_decision_unlocked"]
    # Scan the COMPLETE record, so the verdict and rationale strings are covered too.
    rec["forbidden_construction_scan"] = forbidden_construction_scan(rec, mount)
    rec["elapsed_s"] = round(time.time() - started, 3)
    coherent, problems = check_record_coherence(rec)
    rec["record_coherence"] = {"coherent": coherent, "problems": problems,
                               "checked_before_write": True}
    _write(rec, out_dir, run_id)
    return rc, rec


def _write(rec: dict, out_dir: Path, run_id: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{run_id}.json"
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=2, sort_keys=True,
                            default=str) + "\n", encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--mount", default=str(PRODUCT_MOUNT))
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--report-dir", default=None)
    args = ap.parse_args(argv)
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID") or "local"
    mount = Path(args.mount)
    out_dir = Path(args.out_dir) if args.out_dir else (
        _REPO_ROOT / "results/evaluation/counter_authority_label_benchmark")
    report_dir = Path(args.report_dir) if args.report_dir else (
        _REPO_ROOT / "reports/evaluation")
    if not mount.is_dir():
        print(f"environment error: accepted product mount absent at {mount}", file=sys.stderr)
        return EXIT_ENVIRONMENT
    rc, rec = run(run_id, mount, out_dir, report_dir)
    print(json.dumps({"run_id": run_id, "verdict": rec["verdict"], "exit_code": rc,
                      "gate_findings_fired": rec.get("gate_findings_fired"),
                      "product_falsified": rec.get("product_falsified"),
                      "non_vacuity_all_hold": rec.get("non_vacuity_all_hold"),
                      "record": str(out_dir / f"{run_id}.json")}, indent=2))
    return rc


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())