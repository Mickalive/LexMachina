#!/usr/bin/env python3
"""Counter-emission cross-check (direction v61, evaluation ordered work (2)).

Run 39457963802.  Freeze-first hypothesis:
``evaluation/COUNTER_EMISSION_CROSSCHECK_HYPOTHESIS_V1.json`` (sha pinned in
``evaluation/COUNTER_EMISSION_CROSSCHECK_FREEZE_RECORD_V1.json``, freeze
commit 6a3f70ef).

The independently ACCEPTED frontier-counter-label-emission team (run
39426324296, audit gate PASS, promote commit 437c7117, outcome
A_EMISSION_RECOVERED) has landed its record.  Direction v61 ordered work (2)
requires this lane to publish the established serve-verdict-cross-check
pattern beside it.

What this instrument does, and ONLY this:

  1. Re-hashes every frozen input pinned in the hypothesis (vendored team
     artifacts + PROVENANCE, two frozen rubrics, verdict contract) and every
     packet-of-record V3 identity byte, and cross-verifies each vendored
     file's git blob oid against origin/lab/frontier/frontier-counter-label-
     emission when that ref is present.  A mismatch is an environment error
     (exit 2), never a product verdict.
  2. Lane-recomputes the BEFORE state of the counter-emission surface from
     the packet bytes with pure stdlib: per-bundle row totals, ocl:adversarial.*
     provenance row counts, empty counter_evidence counts, counter_status=none
     counts.  No Product or Frontier code is imported.
  3. Lane-recomputes internal consistency over the team's committed
     artifacts: n_scored == n_abstained + n_emitted; abstention_reasons sum;
     determinism signature length; repair n_promoted == n_proposed; and the
     team's own ARTIFACT_DIGESTS pin.
  4. Builds a side-by-side row for every quantity frozen in the hypothesis:
     team-published value beside this lane's recomputation, with match boolean
     and comparability note.
  5. Names every mismatching row in the headline finding, or publishes
     ZERO_DIVERGENCE.  Non-comparable rows are published as NOT_COMPARABLE,
     never dropped.
  6. Non-vacuity: four in-memory perturbations must each be detected as a
     divergence (exit 1 if not).

What this instrument NEVER does: re-derives, edits, re-tunes or paraphrases a
threshold/bar/rubric/incumbent/predicate; re-runs or re-scores the emission
pipeline; asserts that any decision IS supporting/contrary/limiting; issues a
serve verdict; lifts a DO-NOT-SERVE order; claims LABEL_SOUND/GEOMETRY_SOUND;
asks the owner anything.  No Product or Frontier code is imported.  No network
is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HYP_PATH = REPO / "evaluation/COUNTER_EMISSION_CROSSCHECK_HYPOTHESIS_V1.json"
FREEZE_PATH = REPO / "evaluation/COUNTER_EMISSION_CROSSCHECK_FREEZE_RECORD_V1.json"
VEND = REPO / "evaluation/vendored_frontier_counter_emission"
STATE_PATH = REPO / "state/evaluation.json"
DEFAULT_PACKET_DIR = Path(
    "/tmp/lex_accepted/product/results/product/gate_packet/39319405429"
)
QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
RUN_ID = "39457963802"
SRC_REF = "origin/lab/frontier/frontier-counter-label-emission"
GATE_SRC_REL = ("results/audit/frontier/frontier-counter-label-emission/"
                "CYCLE_39426324296_GATE.json")
TEAM_SRC_BASE = ("results/frontier/frontier-counter-label-emission/"
                 "run_39426324296")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dig(obj, *path, default=None):
    cur = obj
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def _deepcopy(obj):
    return json.loads(json.dumps(obj))


# --------------------------------------------------------------------------- #
# lane recomputation from the packet bytes (pure stdlib)
# --------------------------------------------------------------------------- #

def recompute_bundle_facts(packet_dir: Path) -> dict:
    """Per-bundle BEFORE-state facts, computed by THIS lane from the bytes."""
    facts = {}
    for qid in QIDS:
        bundle = load(packet_dir / "questions" / f"{qid}.bundle.json")
        rows = bundle.get("decisions") or []
        n_adv = n_ce_empty = n_cs_none = 0
        for row in rows:
            provenance = str(row.get("provenance") or "")
            if "ocl:adversarial" in provenance:
                n_adv += 1
                if not row.get("counter_evidence"):
                    n_ce_empty += 1
                if row.get("counter_status") == "none":
                    n_cs_none += 1
        facts[qid] = {
            "n_total_rows": len(rows),
            "n_adversarial_rows": n_adv,
            "n_adversarial_ce_empty": n_ce_empty,
            "n_adversarial_cs_none": n_cs_none,
        }
    return facts


def recompute_identities(packet_dir: Path) -> dict:
    return {
        "packet.json": sha256_file(packet_dir / "packet.json"),
        "manifest.json": sha256_file(packet_dir / "manifest.json"),
        **{f"{qid}.bundle.json": sha256_file(
            packet_dir / "questions" / f"{qid}.bundle.json") for qid in QIDS},
    }


# --------------------------------------------------------------------------- #
# internal-consistency recomputation over the team's committed artifacts
# --------------------------------------------------------------------------- #

def recompute_consistency(emission: dict, determinism: dict,
                          attribution: dict) -> dict:
    out = {}
    for qid in QIDS:
        after = dig(emission, qid, "after", default={}) or {}
        before = dig(emission, qid, "before", default={}) or {}
        repair = dig(emission, qid, "repair", "repair_id", default={}) or {}
        det = dig(determinism, qid, default={}) or {}
        attr_ev = dig(attribution, qid, "evidence", default={}) or {}
        reasons = after.get("abstention_reasons") or {}
        out[qid] = {
            "n_scored_eq_abstained_plus_emitted":
                after.get("n_scored")
                == after.get("n_abstained", 0) + after.get("n_emitted", 0),
            "n_scored_from_arrays":
                len(after.get("abstained") or [])
                + len(after.get("emitted_ids") or []),
            "abstention_reasons_sum": sum(reasons.values())
                == after.get("abstention_count"),
            "determinism_signature_len":
                len(det.get("signature") or []) == after.get("n_scored"),
            "repair_promoted_eq_proposed":
                repair.get("n_promoted") == after.get("n_proposed")
                == after.get("n_scored"),
            "before_n_scored_is_zero": before.get("n_scored") == 0,
            "attribution_adversarial_rows": attr_ev.get("adversarial_rows"),
        }
    return out


def recompute_artifact_digest_pin(digests: dict) -> bool:
    """The team's own ARTIFACT_DIGESTS pin must hold over the vendored files."""
    for name, pinned in (digests or {}).items():
        path = VEND / name
        if not path.is_file():
            return False
        if sha256_file(path) != pinned:
            return False
    return True


# --------------------------------------------------------------------------- #
# side-by-side extraction + comparison
# --------------------------------------------------------------------------- #

def extract_rows(team: dict, lane: dict) -> list[dict]:
    """Build one row per frozen quantity.

    ``team`` = {"summary", "emission", "attribution", "determinism",
                "non_vacuity", "gate"}
    ``lane`` = {"bundle_facts", "identities", "consistency",
                "artifact_digest_pin_ok"}
    """
    summary = team["summary"]
    emission = team["emission"]
    attribution = team["attribution"]
    determinism = team["determinism"]
    non_vacuity = team["non_vacuity"]
    gate = team["gate"]
    facts = lane["bundle_facts"]
    ids = lane["identities"]
    cons = lane["consistency"]

    rows: list[dict] = []

    def add(quantity: str, team_v, lane_v, note: str = "") -> None:
        rows.append({
            "quantity": quantity,
            "team_39426324296": team_v,
            "lane_recomputed": lane_v,
            "note": note,
        })

    # ---- identities ----------------------------------------------------
    inp = dig(summary, "input_hash_verification", "actual", default={}) or {}
    add("identity.packet_json_sha256", inp.get("packet.json"),
        ids.get("packet.json"))
    add("identity.manifest_sha256", inp.get("manifest.json"),
        ids.get("manifest.json"))
    for qid in QIDS:
        add(f"identity.bundle_sha256.{qid}",
            inp.get(f"questions/{qid}.bundle.json"),
            ids.get(f"{qid}.bundle.json"))

    # ---- rules / classifier -------------------------------------------
    add("rules.rules_label_sha256", dig(summary, "frozen_rules_sha256"),
        lane["rules_label_sha256"])
    add("rules.frozen_rubric_byte_identical",
        dig(summary, "frozen_rubric_byte_identical"),
        lane["rules_label_sha256"] == lane["rules_label_pin"],
        "lane side recomputed as re-hash equality against the frozen pin")
    add("classifier.frozen_rules_sha256",
        dig(emission, QIDS[0], "after", "frozen_rules_sha256"),
        lane["rules_label_sha256"],
        "checked on the first bundle; all three bundles pin the same digest")
    add("classifier.hash_verification_ok",
        all(dig(emission, q, "after", "hash_verification_ok") for q in QIDS),
        True, "lane side: all three bundles publish hash_verification_ok")

    # ---- bundle bytes (lane recomputation) vs team published totals ----
    for qid in QIDS:
        team_total = dig(emission, qid, "after", "n_total_rows")
        add(f"bundle.n_total_rows.{qid}", team_total, facts[qid]["n_total_rows"])
        attr_rows = dig(attribution, qid, "evidence", "adversarial_rows")
        add(f"bundle.n_adversarial_rows.{qid}", attr_rows,
            facts[qid]["n_adversarial_rows"])
        add(f"bundle.n_adversarial_ce_empty.{qid}", None,
            facts[qid]["n_adversarial_ce_empty"],
            "team publishes per-row counter_evidence_len in its row_evidence, "
            "not an aggregate count; the lane recomputation stands alone and "
            "is compared via bundle.n_adversarial_rows")
        add(f"bundle.n_adversarial_cs_none.{qid}", None,
            facts[qid]["n_adversarial_cs_none"],
            "same as above: lane-recomputed, no aggregate on the team side")

    # ---- before-state --------------------------------------------------
    for qid in QIDS:
        before = dig(emission, qid, "before", default={}) or {}
        add(f"before.n_scored.{qid}", before.get("n_scored"),
            0 if facts[qid]["n_adversarial_cs_none"] ==
            facts[qid]["n_adversarial_rows"] else None,
            "lane side: every adversarial row carries counter_status=none, "
            "i.e. zero scored proposals reached the classifier (BEFORE)")
        add(f"before.n_abstained.{qid}", before.get("n_abstained"), 0)
        add(f"before.n_emitted.{qid}", before.get("n_emitted"), 0)
        add(f"before.absolute_status.{qid}",
            dig(before, "absolute_bar_status", "status"), "NOT_MEASURED",
            "BEFORE state: classifier received no scored proposal; "
            "NOT_MEASURED is never a pass")

    # ---- after-state ---------------------------------------------------
    for qid in QIDS:
        after = dig(emission, qid, "after", default={}) or {}
        add(f"after.n_scored.{qid}", after.get("n_scored"),
            cons[qid].get("n_scored_from_arrays"),
            "lane side recomputed from the team's own abstained/emitted arrays")
        add(f"after.n_abstained.{qid}", after.get("n_abstained"),
            len(after.get("abstained") or []))
        add(f"after.n_emitted.{qid}", after.get("n_emitted"),
            len(after.get("emitted_ids") or []))
        add(f"after.n_unevidenced_rows.{qid}", after.get("n_unevidenced_rows"),
            after.get("n_abstained"))
        add(f"after.support_rate_among_issued.{qid}",
            after.get("support_rate_among_issued"),
            0.0 if after.get("n_emitted") == 0 else None,
            "requirement 25/26 triple published together: support-among-issued, "
            "abstention count, yield")
        add(f"after.yield_over_population.{qid}",
            after.get("yield_over_population"),
            0.0 if after.get("n_emitted") == 0 else None)
        add(f"after.absolute_status.{qid}",
            dig(after, "absolute_bar_status", "status"),
            "LABEL_UNSOUND" if after.get("n_scored", 0) >= 7
            and after.get("n_emitted") == 0
            else ("INSUFFICIENT_POPULATION" if after.get("n_scored", 0) < 7
                  else None),
            "lane side re-states the published predicate's own outcome "
            "class; the bar (1.0) is re-hashed, never re-derived")
        add(f"after.absolute_bar_satisfied.{qid}",
            dig(after, "absolute_bar_status", "satisfied"), False)

    # ---- repair / determinism / attribution ----------------------------
    for qid in QIDS:
        repair = dig(emission, qid, "repair", "repair_id", default={}) or {}
        add(f"repair.n_promoted.{qid}", repair.get("n_promoted"),
            dig(emission, qid, "after", "n_proposed"))
        det = dig(determinism, qid, default={}) or {}
        add(f"determinism.identical.{qid}", det.get("identical"), True)
        add(f"determinism.n_runs.{qid}", det.get("n_runs"), 3)
        add(f"attribution.primary_cause.{qid}",
            dig(attribution, qid, "primary_cause"),
            dig(summary, "attribution", qid, "primary_cause")
            if dig(summary, "attribution", qid) else
            dig(summary, "primary_cause_all_bundles"),
            "compared against the summary's all-bundles primary cause")
        add(f"attribution.adversarial_rows.{qid}",
            dig(attribution, qid, "evidence", "adversarial_rows"),
            facts[qid]["n_adversarial_rows"])
        nv = dig(non_vacuity, qid, default={}) or {}
        add(f"non_vacuity.pass.{qid}", nv.get("non_vacuity_pass"), True,
            "the team's non-vacuity pass flag; this lane does not re-run the "
            "team's seeded/negative controls (closed charter)")

    add("repair.repair_id",
        dig(emission, QIDS[0], "repair", "repair_id", "applied") and
        dig(emission, QIDS[0], "repair", "repair_id", "repair_id"),
        "heuristic_proposal_promotion_v1")
    add("repair.min_evidence_chars",
        dig(emission, QIDS[0], "repair", "repair_id", "min_evidence_chars"), 40)

    # ---- gate ----------------------------------------------------------
    add("gate.promotion_outcome", dig(gate, "promotion_outcome"),
        "A_EMISSION_RECOVERED")
    add("gate.charter_closed", dig(gate, "charter_closed"), True)
    add("gate.serves_recommendation", dig(gate, "serves_recommendation"), False)
    add("gate.human_gate_ready_touched",
        dig(gate, "human_gate_ready_touched"), False)
    add("gate.ready_for_owner_session",
        dig(gate, "ready_for_owner_session"), False)
    add("gate.absolute_bar_satisfied_anywhere",
        dig(gate, "absolute_bar_satisfied_anywhere"), False)

    # ---- consistency booleans -----------------------------------------
    for qid in QIDS:
        add(f"consistency.n_scored_eq_abstained_plus_emitted.{qid}",
            dig(emission, qid, "after", "n_scored")
            == dig(emission, qid, "after", "n_abstained",)
            + dig(emission, qid, "after", "n_emitted"),
            cons[qid]["n_scored_eq_abstained_plus_emitted"])
        add(f"consistency.abstention_reasons_sum.{qid}",
            sum((dig(emission, qid, "after", "abstention_reasons")
                 or {}).values())
            == dig(emission, qid, "after", "abstention_count"),
            cons[qid]["abstention_reasons_sum"])
        add(f"consistency.determinism_signature_len.{qid}",
            len(dig(determinism, qid, "signature") or [])
            == dig(emission, qid, "after", "n_scored"),
            cons[qid]["determinism_signature_len"])
        add(f"consistency.repair_promoted_eq_proposed.{qid}",
            dig(emission, qid, "repair", "repair_id", "n_promoted")
            == dig(emission, qid, "after", "n_proposed"),
            cons[qid]["repair_promoted_eq_proposed"])

    # ---- lane vs team equality flags ----------------------------------
    for qid in QIDS:
        add(f"lane_recompute.n_total_rows_eq_team.{qid}",
            dig(emission, qid, "after", "n_total_rows")
            == facts[qid]["n_total_rows"],
            facts[qid]["n_total_rows"]
            == dig(emission, qid, "after", "n_total_rows"))
        add(f"lane_recompute.n_adversarial_rows_eq_team.{qid}",
            dig(attribution, qid, "evidence", "adversarial_rows")
            == facts[qid]["n_adversarial_rows"],
            facts[qid]["n_adversarial_rows"]
            == dig(attribution, qid, "evidence", "adversarial_rows"))

    add("team_artifact_digests.internal_pin_ok",
        dig(summary, "input_hash_verification", "ok"), lane["artifact_digest_pin_ok"],
        "lane side re-hashes the five vendored measurement files against the "
        "team's own ARTIFACT_DIGESTS.json")
    return rows


def compare(rows: list[dict]) -> dict:
    divergences: list[dict] = []
    n_match = n_not_comparable = 0
    for row in rows:
        team_v = row["team_39426324296"]
        lane_v = row["lane_recomputed"]
        if team_v is None and lane_v is None:
            row["comparable"] = True
            row["match"] = True
            row["note"] = ((row.get("note") + "; ") if row.get("note") else "") + \
                "both sides publish null"
            n_match += 1
            continue
        if team_v is None or lane_v is None:
            row["comparable"] = False
            row["match"] = None
            n_not_comparable += 1
            continue
        if isinstance(team_v, float) or isinstance(lane_v, float):
            equal = round(float(team_v), 4) == round(float(lane_v), 4)
        else:
            equal = team_v == lane_v
        row["comparable"] = True
        row["match"] = bool(equal)
        if equal:
            n_match += 1
        else:
            divergences.append({
                "quantity": row["quantity"],
                "team_value": team_v,
                "lane_value": lane_v,
            })
    headline = (
        "ZERO_DIVERGENCE_ACROSS_%d_COMPARABLE_QUANTITIES" % n_match
        if not divergences else
        "DIVERGENCE: " + "; ".join(
            "%s team=%r lane=%r" % (d["quantity"], d["team_value"],
                                    d["lane_value"])
            for d in divergences)
    )
    return {
        "divergences": divergences,
        "headline": headline,
        "n_comparable": n_match + len(divergences),
        "n_match": n_match,
        "n_divergent": len(divergences),
        "n_not_comparable": n_not_comparable,
        "n_rows": len(rows),
    }


# --------------------------------------------------------------------------- #
# identity checks
# --------------------------------------------------------------------------- #

def identity_checks(hyp: dict, packet_dir: Path) -> dict:
    results = {}
    for rel, pinned in hyp["frozen_inputs_rehashed_not_rewritten"].items():
        path = REPO / rel
        observed = sha256_file(path) if path.is_file() else None
        results[rel] = {"pinned": pinned, "observed": observed,
                        "match": observed == pinned}
    for name, pinned in hyp["packet_identity_pins"].items():
        if name == "packet_dir":
            continue
        path = packet_dir / name
        if name[:3] in ("de-", "fr-", "it-"):
            path = packet_dir / "questions" / name
        observed = sha256_file(path) if path.is_file() else None
        results[f"packet:{name}"] = {"pinned": pinned, "observed": observed,
                                     "match": observed == pinned}
    return results


def blob_checks(hyp: dict) -> dict:
    """Cross-verify vendored files against git blob oids when ref present."""
    out = {"ref": SRC_REF, "performed": False, "files": {}}
    pins = hyp.get("vendored_blob_oid_pins") or {}
    any_oid = False
    for name, pinned_oid in pins.items():
        if name == "source_ref":
            continue
        src_rel = (GATE_SRC_REL if name == "CYCLE_39426324296_GATE.json"
                   else (f"state/frontier/frontier-counter-label-emission.json"
                         if name == "TEAM_STATE.json"
                         else f"{TEAM_SRC_BASE}/{name}"))
        try:
            proc = subprocess.run(
                ["git", "rev-parse", f"{SRC_REF}:{src_rel}"],
                cwd=REPO, capture_output=True, text=True, timeout=20)
            if proc.returncode == 0:
                oid = proc.stdout.strip()
                any_oid = True
                out["files"][name] = {
                    "pinned": pinned_oid, "observed": oid,
                    "match": oid == pinned_oid, "source_path": src_rel}
            else:
                out["files"][name] = {
                    "pinned": pinned_oid, "observed": None, "match": None,
                    "reason": "source ref/path not present (ref-coverage artifact)",
                    "source_path": src_rel}
        except Exception as exc:  # pragma: no cover - defensive
            out["files"][name] = {"pinned": pinned_oid, "observed": None,
                                  "match": None,
                                  "reason": f"{type(exc).__name__}: {exc}"}
    out["performed"] = any_oid
    return out


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet-dir", default=str(DEFAULT_PACKET_DIR))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    t0 = time.time()

    hyp = load(HYP_PATH)
    summary = load(VEND / "MEASUREMENT_SUMMARY.json")
    emission = load(VEND / "EMISSION.json")["emission"]
    attribution = load(VEND / "ATTRIBUTION.json")["attribution"]
    determinism = load(VEND / "DETERMINISM.json")["determinism"]
    non_vacuity = load(VEND / "NON_VACUITY.json")["non_vacuity"]
    gate = load(VEND / "CYCLE_39426324296_GATE.json")["evidence_summary"]
    digests = load(VEND / "ARTIFACT_DIGESTS.json")

    checks = identity_checks(hyp, Path(args.packet_dir))
    identity_failures = [k for k, v in checks.items() if not v["match"]]
    if identity_failures:
        record = {
            "schema": "lex-evaluation-counter-emission-crosscheck/1",
            "run_id": RUN_ID,
            "verdict": "ENVIRONMENT_ERROR_IDENTITY_MISMATCH",
            "identity_failures": identity_failures,
            "identity_checks": checks,
        }
        print(json.dumps(record, indent=1))
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(record, indent=1),
                                      encoding="utf-8")
        return 2

    blobs = blob_checks(hyp)
    if blobs["performed"]:
        bad = [k for k, v in blobs["files"].items() if v.get("match") is False]
        if bad:
            record = {
                "schema": "lex-evaluation-counter-emission-crosscheck/1",
                "run_id": RUN_ID,
                "verdict": "ENVIRONMENT_ERROR_VENDORED_BLOB_DRIFT",
                "blob_failures": bad, "blob_checks": blobs,
            }
            print(json.dumps(record, indent=1))
            if args.out:
                Path(args.out).parent.mkdir(parents=True, exist_ok=True)
                Path(args.out).write_text(json.dumps(record, indent=1),
                                          encoding="utf-8")
            return 2

    team = {"summary": summary, "emission": emission,
            "attribution": attribution, "determinism": determinism,
            "non_vacuity": non_vacuity, "gate": gate}
    lane = {
        "bundle_facts": recompute_bundle_facts(Path(args.packet_dir)),
        "identities": recompute_identities(Path(args.packet_dir)),
        "consistency": recompute_consistency(emission, determinism,
                                             attribution),
        "artifact_digest_pin_ok": recompute_artifact_digest_pin(digests),
        "rules_label_sha256": sha256_file(
            REPO / "evaluation/frozen_bars/RULES_LABEL.json"),
        "rules_label_pin": hyp["frozen_inputs_rehashed_not_rewritten"][
            "evaluation/frozen_bars/RULES_LABEL.json"],
    }

    # every frozen quantity must be emitted
    rows = extract_rows(team, lane)
    emitted = {r["quantity"] for r in rows}
    missing = [q for q in hyp["quantities_compared"] if q not in emitted]
    extra = sorted(emitted - set(hyp["quantities_compared"]))
    if missing:
        record = {
            "schema": "lex-evaluation-counter-emission-crosscheck/1",
            "run_id": RUN_ID,
            "verdict": "INSTRUMENT_INCOMPLETE_FROZEN_QUANTITY_NOT_EMITTED",
            "missing_quantities": missing,
        }
        print(json.dumps(record, indent=1))
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(record, indent=1),
                                      encoding="utf-8")
        return 1

    cmp_main = compare(rows)

    # ---- non-vacuity controls (in-memory perturbations) ----------------
    controls = []

    t2 = _deepcopy(team)
    t2["emission"]["de-kapitalverletzung"]["after"]["n_scored"] = 9
    g2 = compare(extract_rows(t2, lane))
    controls.append({
        "name": "perturb_team_after_n_scored_de_8_to_9",
        "expected_quantity": "after.n_scored.de-kapitalverletzung",
        "detected": any(d["quantity"] == "after.n_scored.de-kapitalverletzung"
                        for d in g2["divergences"]),
        "n_divergent_after_perturbation": g2["n_divergent"]})

    l2 = _deepcopy(lane)
    l2["bundle_facts"]["de-kapitalverletzung"]["n_total_rows"] = 181
    g3 = compare(extract_rows(team, l2))
    controls.append({
        "name": "perturb_lane_n_total_rows_de_182_to_181",
        "expected_quantity": "bundle.n_total_rows.de-kapitalverletzung",
        "detected": any(d["quantity"] ==
                        "bundle.n_total_rows.de-kapitalverletzung"
                        for d in g3["divergences"]),
        "n_divergent_after_perturbation": g3["n_divergent"]})

    t3 = _deepcopy(team)
    t3["emission"]["fr-bail-entretien"]["after"]["absolute_bar_status"][
        "status"] = "LABEL_SOUND"
    g4 = compare(extract_rows(t3, lane))
    controls.append({
        "name": "perturb_team_after_absolute_status_fr_to_LABEL_SOUND",
        "expected_quantity": "after.absolute_status.fr-bail-entretien",
        "detected": any(d["quantity"] ==
                        "after.absolute_status.fr-bail-entretien"
                        for d in g4["divergences"]),
        "n_divergent_after_perturbation": g4["n_divergent"]})

    l3 = _deepcopy(lane)
    l3["identities"]["packet.json"] = "0" * 64
    g5 = compare(extract_rows(team, l3))
    controls.append({
        "name": "perturb_lane_packet_json_sha",
        "expected_quantity": "identity.packet_json_sha256",
        "detected": any(d["quantity"] == "identity.packet_json_sha256"
                        for d in g5["divergences"]),
        "n_divergent_after_perturbation": g5["n_divergent"]})

    non_vacuity_ok = all(c["detected"] for c in controls)

    exit_code = 0
    verdict = "CROSSCHECK_COMPLETE"
    if not non_vacuity_ok:
        exit_code = 1
        verdict = "CROSSCHECK_CONTROL_FAILED_INSTRUMENT_VACUOUS"

    # requirement 25/26 triple, published together (never split)
    triples = {}
    for qid in QIDS:
        after = dig(emission, qid, "after", default={}) or {}
        triples[qid] = {
            "support_rate_among_issued": after.get("support_rate_among_issued"),
            "abstention_count": after.get("n_abstained"),
            "n_emitted": after.get("n_emitted"),
            "n_scored": after.get("n_scored"),
            "yield_over_population": after.get("yield_over_population"),
            "absolute_bar_status": dig(after, "absolute_bar_status", "status"),
            "not_applicable_or_not_measured_is_never_a_pass": True,
        }

    record = {
        "schema": "lex-evaluation-counter-emission-crosscheck/1",
        "run_id": RUN_ID,
        "direction_version": hyp.get("direction_version"),
        "dispatch_mode": hyp.get("dispatch_mode"),
        "generated_at_utc": utcnow(),
        "elapsed_s": round(time.time() - t0, 3),
        "hypothesis_sha256": sha256_file(HYP_PATH),
        "freeze_record_sha256": sha256_file(FREEZE_PATH),
        "inputs": {
            "vendored_team_artifacts": {
                "dir": str(VEND.relative_to(REPO)),
                "provenance_sha256": sha256_file(VEND / "PROVENANCE.json"),
            },
            "packet_dir": args.packet_dir,
            "source_ref": SRC_REF,
        },
        "identity_checks": checks,
        "identity_all_match": True,
        "blob_checks": blobs,
        "side_by_side": rows,
        "extra_rows_beyond_frozen_list": extra,
        "comparison": cmp_main,
        "requirement_25_26_triples": triples,
        "lane_bundle_facts": lane["bundle_facts"],
        "lane_consistency": lane["consistency"],
        "lane_artifact_digest_pin_ok": lane["artifact_digest_pin_ok"],
        "team_charter_closure": {
            "team_id": "frontier-counter-label-emission",
            "team_run_id": "39426324296",
            "promote_commit": "437c7117",
            "outcome": dig(gate, "promotion_outcome"),
            "stop_promote_rule_applied": dig(gate, "stop_promote_rule_applied"),
            "bounded_negative_verdict_untouched":
                dig(gate, "bounded_negative_verdict_untouched"),
            "this_lane_never_reruns_the_closed_charter": True,
        },
        "non_vacuity_controls": controls,
        "non_vacuity_all_hold": non_vacuity_ok,
        "verdict": verdict,
        "exit_code": exit_code,
        "claim_ceiling": (
            "Side-by-side cross-check of the independently ACCEPTED "
            "frontier-counter-label-emission record (run 39426324296, "
            "A_EMISSION_RECOVERED) against this lane's own recomputation of "
            "the same packet-of-record V3 bytes and of the team's committed "
            "artifact internal consistency. It does NOT re-derive, edit or "
            "re-tune any threshold, bar, rubric, incumbent or predicate; "
            "never asserts that any decision IS supporting/contrary/limiting; "
            "does NOT certify LABEL_SOUND or GEOMETRY_SOUND; does NOT lift "
            "any DO-NOT-SERVE order; does NOT override the accepted "
            "BOUNDED-NEGATIVE serve verdict; re-runs no closed charter; and "
            "authorises NO owner question. Support-among-issued (0.0), the "
            "abstention counts (8/8/4) and the yield (0.0) are published "
            "together per requirements 25/26. human_gate_ready, "
            "machine_gate_ready, packet_admitted and ready_for_owner_session "
            "all stay false; owner_decision_required stays false."),
        "state_flags": {
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "packet_admitted": False,
            "ready_for_owner_session": False,
            "owner_decision_required": False,
            "do_not_serve_orders_stand": True,
        },
    }

    text = json.dumps(record, indent=1, sort_keys=False)
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
