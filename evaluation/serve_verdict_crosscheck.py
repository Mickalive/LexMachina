#!/usr/bin/env python3
"""Serve-verdict cross-check (direction v60, evaluation ordered work (b)).

Run 39381093325 (OPERATIONAL RESUME of the persisted snapshot of run
39380758180).  Freeze-first hypothesis:
``evaluation/SERVE_VERDICT_CROSSCHECK_HYPOTHESIS_V1.json`` (sha pinned in
``evaluation/SERVE_VERDICT_CROSSCHECK_FREEZE_RECORD_V1.json``).

What this instrument does, and ONLY this:

  1. Re-hashes every frozen input pinned in the hypothesis (two frozen rubrics,
     verdict contract, this lane's two committed packet records, the vendored
     ACCEPTED serve verdict) and every packet-of-record V3 identity byte.
     A mismatch is an environment error (exit 2), never a product verdict.
  2. Builds a side-by-side row for every quantity named in the hypothesis:
     this lane's discharge record (39379766198), this lane's stand-ready
     adjudication (39338699604) and the independently ACCEPTED serve-audit
     team's recomputation on the same bytes (vendored VERDICT_39371834165).
  3. Names every mismatching row in the headline finding (direction v60 (b)),
     or publishes ZERO_DIVERGENCE.  Non-comparable rows are published as
     NOT_COMPARABLE, never dropped.
  4. Records the serve-verdict landing (outcome BOUNDED-NEGATIVE, promote
     95162685, portfolio promotion_status PROMOTED) beside the superseded
     state sentence, preserved verbatim.
  5. Records the discharge-time population-pin refresh as a RE-HASH, never as
     an edit of any frozen file.
  6. Non-vacuity: three in-memory perturbations of the lane payload must each
     be detected as a divergence (exit 1 if not).

What this instrument NEVER does: re-derives, edits, re-tunes or paraphrases a
threshold/bar/rubric/incumbent/predicate; issues or overrides a serve verdict;
lifts a DO-NOT-SERVE order; claims LABEL_SOUND/GEOMETRY_SOUND; asks the owner
anything.  No Product code is imported.  No network is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HYP_PATH = REPO / "evaluation/SERVE_VERDICT_CROSSCHECK_HYPOTHESIS_V1.json"
DISCHARGE_PATH = REPO / "results/evaluation/packet_of_record_stand_ready/39379766198.json"
STANDREADY_PATH = REPO / "results/evaluation/packet_of_record_stand_ready/39338699604.json"
VENDORED = REPO / "evaluation/vendored_frontier_serve_audit/VERDICT_39371834165.json"
VENDORED_PROV = REPO / "evaluation/vendored_frontier_serve_audit/PROVENANCE.json"
STATE_PATH = REPO / "state/evaluation.json"
DEFAULT_PACKET_DIR = Path(
    "/tmp/lex_accepted/product/results/product/gate_packet/39319405429"
)
QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
RUN_ID = "39381093325"


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


# --------------------------------------------------------------------------- #
# quantity extraction: (discharge, stand_ready, team) + comparability note
# --------------------------------------------------------------------------- #

def extract_rows(discharge: dict, standready: dict, team: dict) -> list[dict]:
    rows: list[dict] = []

    def add(quantity: str, d, s, t, note: str = "") -> None:
        rows.append({
            "quantity": quantity,
            "lane_discharge_39379766198": d,
            "lane_stand_ready_39338699604": s,
            "team_serve_audit_39371834165": t,
            "note": note,
        })

    # ---- label ---------------------------------------------------------
    add("label.n_scored",
        dig(discharge, "adjudication", "label_gate", "n_scored"),
        None,
        dig(team, "label_half", "n_scored"),
        "stand-ready record computed ZERO frozen verdicts on the packet bytes by design (pre-serve pre-emption guard)")
    add("label.n_supported",
        dig(discharge, "adjudication", "label_gate", "n_supported"),
        None,
        dig(team, "label_half", "n_supported"))
    add("label.support_rate",
        dig(discharge, "adjudication", "label_gate", "support_rate"),
        None,
        dig(team, "label_half", "support_rate"),
        "null on both sides: 0 scored rows, never 1.0")
    add("label.absolute_status",
        dig(discharge, "adjudication", "label_gate", "absolute_status"),
        None,
        dig(team, "label_half", "absolute_status"))
    add("label.regression_verdict",
        dig(discharge, "adjudication", "label_gate", "regression_verdict"),
        None,
        dig(team, "label_half", "regression_verdict"),
        "NOT_APPLICABLE is an inapplicability marker, never a pass")
    add("label.gate_blocks_build",
        dig(discharge, "adjudication", "label_gate", "gate_blocks_build"),
        None,
        dig(team, "label_half", "gate_blocks_build"))
    add("label.incumbent_population",
        dig(discharge, "adjudication", "label_gate", "incumbent_population"),
        None,
        None,
        "team records the incumbent population inside its label_lineage_gate predicate, not as a top-level row")

    # ---- geometry ------------------------------------------------------
    for qid in QIDS:
        add(f"geometry.per_bundle_counts.{qid}",
            dig(discharge, "adjudication", "geometry_gate", "per_bundle_counts", qid),
            None,
            dig(team, "geometry_half", "per_bundle_counts", qid))
        add(f"geometry.incumbent_counts.{qid}",
            dig(discharge, "adjudication", "geometry_gate", "incumbent_counts", qid),
            None,
            None,
            "incumbent is the frozen accepted count (de 6 / fr 5 / it 5), re-hashed not re-derived")
    add("geometry.absolute_status",
        dig(discharge, "adjudication", "geometry_gate", "absolute_status"),
        None,
        dig(team, "geometry_half", "absolute_status"))
    add("geometry.regression_verdict",
        dig(discharge, "adjudication", "geometry_gate", "regression_verdict"),
        None,
        dig(team, "geometry_half", "regression_verdict"))
    add("geometry.gate_blocks_build",
        dig(discharge, "adjudication", "geometry_gate", "gate_blocks_build"),
        None,
        dig(team, "geometry_half", "gate_blocks_build"))
    add("geometry.n_bundles_pass_all_11",
        dig(discharge, "adjudication", "geometry_gate", "n_bundles_pass_all_11"),
        None,
        dig(team, "geometry_half", "n_bundles_pass_all_11"))

    # ---- mega-cluster shares (lane value lives in the stand-ready record) ----
    stand_mega = {
        dig(q, "qid"): dig(q, "size_based_share")
        for q in dig(standready, "mega_cluster_disclosure_conformance",
                     "per_question", default=[]) or []
    }
    for qid in QIDS:
        add(f"mega_share.{qid}",
            None,
            stand_mega.get(qid),
            dig(team, "geometry_half", "per_bundle", qid, "mega_cluster",
                "largest_cluster_share"),
            "compared at round(...,4): lane published 4-dp, team records full precision (rounding rule frozen in the hypothesis)")

    # ---- identities ----------------------------------------------------
    add("identity.packet_json_sha256",
        dig(discharge, "packet", "packet_json_sha256"),
        dig(standready, "packet_byte_verification", "packet_json_sha256"),
        dig(team, "input_identity", "packet_json_sha256"))
    add("identity.manifest_sha256",
        dig(discharge, "packet", "manifest_sha256"),
        None,
        dig(team, "input_identity", "manifest_sha256"))
    for qid in QIDS:
        add(f"identity.bundle_sha256.{qid}",
            dig(discharge, "packet", "bundles", qid, "bundle_sha256"),
            dig(standready, "packet_byte_verification", "bundles", qid, "bundle_sha256"),
            dig(team, "input_identity", "bundle_raw_sha256", qid))

    # ---- frozen rules --------------------------------------------------
    add("rules.rules_label_sha256",
        dig(discharge, "frozen_bars", "rules_label_sha256"),
        dig(standready, "frozen_pin_verification", "RULES_LABEL.json"),
        dig(team, "frozen_rules", "rules_label_sha256"))
    add("rules.rules_geometry_sha256",
        dig(discharge, "frozen_bars", "rules_geometry_sha256"),
        dig(standready, "frozen_pin_verification", "RULES_GEOMETRY.json"),
        dig(team, "frozen_rules", "rules_geometry_sha256"))

    # ---- serve / owner flags ------------------------------------------
    add("serve.packet_admitted",
        dig(discharge, "serve_status", "packet_admitted"),
        dig(standready, "packet_admitted"),
        None,
        "the serve charter issues an outcome, not an admission flag; admission is Product's committed field")
    add("serve.ready_for_owner_session",
        dig(discharge, "serve_status", "ready_for_owner_session"),
        dig(standready, "ready_for_owner_session"),
        dig(team, "verdict", "owner_session_guard", "ready_for_owner_session"))
    add("serve.human_gate_ready",
        dig(discharge, "serve_status", "human_gate_ready"),
        None,
        dig(team, "verdict", "owner_session_guard", "human_gate_ready"))
    add("serve.owner_decision_required",
        dig(discharge, "serve_status", "owner_decision_required"),
        dig(standready, "owner_decision_required"),
        dig(team, "verdict", "owner_decision_required"))
    add("serve.do_not_serve_orders_stand",
        dig(discharge, "serve_status", "do_not_serve_orders_stand"),
        dig(standready, "do_not_serve_orders_stand"),
        None,
        "the serve charter states the same fact as outcome BOUNDED-NEGATIVE (the packet is not served) with non_vacuity.verdict_reachability.do_not_serve_control reachable=true, not as a boolean field; both DO-NOT-SERVE orders stand on both sides")

    # ---- battery / outcome (charter-separated, published as context) ----
    add("falsification_battery.status",
        dig(discharge, "falsification_battery", "status"),
        None,
        None,
        "battery status is this lane's own instrument state; the serve charter does not emit it")
    add("verdict.outcome",
        None,
        None,
        dig(team, "verdict", "outcome"),
        "the serve outcome belongs to the ACCEPTED serve-audit charter; this lane issues no serve outcome (charter separation)")
    return rows


def compare(rows: list[dict]) -> dict:
    """Fill match/comparability on every row; return headline + counts."""
    divergences: list[dict] = []
    n_match = n_not_comparable = 0
    for row in rows:
        lane = row["lane_discharge_39379766198"]
        team = row["team_serve_audit_39371834165"]
        alt = row["lane_stand_ready_39338699604"]
        if lane is None and alt is not None:
            row["lane_value_used"] = "lane_stand_ready_39338699604"
            left = alt
        else:
            row["lane_value_used"] = "lane_discharge_39379766198"
            left = lane
        if left is None and team is None:
            # Both sides publish the same null (e.g. support_rate with 0 scored
            # rows, never coerced to 1.0).  A shared null IS a comparison.
            row["comparable"] = True
            row["match"] = True
            row["note"] = ((row.get("note") + "; ") if row.get("note") else "") + \
                "both sides publish null"
            n_match += 1
            continue
        if left is None or team is None:
            row["comparable"] = False
            row["match"] = None
            n_not_comparable += 1
            continue
        if isinstance(left, float) or isinstance(team, float):
            equal = round(float(left), 4) == round(float(team), 4)
        else:
            equal = left == team
        row["comparable"] = True
        row["match"] = bool(equal)
        if equal:
            n_match += 1
        else:
            divergences.append({
                "quantity": row["quantity"],
                "lane_value": left,
                "team_value": team,
                "lane_source": row["lane_value_used"],
            })
    headline = (
        "ZERO_DIVERGENCE_ACROSS_%d_COMPARABLE_QUANTITIES" % n_match
        if not divergences else
        "DIVERGENCE: " + "; ".join(
            "%s lane=%r team=%r" % (d["quantity"], d["lane_value"], d["team_value"])
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


def identity_checks(hyp: dict, packet_dir: Path) -> dict:
    """Re-hash frozen inputs and packet bytes against the frozen pins."""
    results = {}
    for rel, pinned in hyp["frozen_inputs_rehashed_not_rewritten"].items():
        path = REPO / rel
        observed = sha256_file(path) if path.is_file() else None
        results[rel] = {"pinned": pinned, "observed": observed,
                        "match": observed == pinned}
    pins = hyp["packet_identity_pins"]
    for name, pinned in pins.items():
        if name == "packet_dir":
            continue
        path = packet_dir / name
        if name.startswith("de-") or name.startswith("fr-") or name.startswith("it-"):
            path = packet_dir / "questions" / name
        observed = sha256_file(path) if path.is_file() else None
        results[f"packet:{name}"] = {"pinned": pinned, "observed": observed,
                                     "match": observed == pinned}
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet-dir", default=str(DEFAULT_PACKET_DIR))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    t0 = time.time()

    hyp = load(HYP_PATH)
    discharge = load(DISCHARGE_PATH)
    standready = load(STANDREADY_PATH)
    team = load(VENDORED)
    prov = load(VENDORED_PROV)

    checks = identity_checks(hyp, Path(args.packet_dir))
    identity_failures = [k for k, v in checks.items() if not v["match"]]
    if identity_failures:
        record = {
            "schema": "lex-evaluation-serve-verdict-crosscheck/1",
            "run_id": RUN_ID,
            "verdict": "ENVIRONMENT_ERROR_IDENTITY_MISMATCH",
            "identity_failures": identity_failures,
            "identity_checks": checks,
        }
        print(json.dumps(record, indent=1))
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(record, indent=1), encoding="utf-8")
        return 2

    # vendored blob cross-verification when the source ref is reachable
    blob_check = {"performed": False}
    try:
        import subprocess
        ref = "origin/lab/frontier/frontier-packet-serve-audit"
        rel = "results/frontier/frontier-packet-serve-audit/VERDICT_39371834165.json"
        out = subprocess.run(
            ["git", "rev-parse", f"{ref}:{rel}"], cwd=REPO,
            capture_output=True, text=True, timeout=20)
        if out.returncode == 0:
            oid = out.stdout.strip()
            blob_check = {
                "performed": True,
                "ref": ref,
                "path": rel,
                "blob_oid_observed": oid,
                "blob_oid_pinned": prov["files"]["VERDICT_39371834165.json"]["git_blob_oid"],
                "match": oid == prov["files"]["VERDICT_39371834165.json"]["git_blob_oid"],
            }
        else:
            blob_check = {"performed": False,
                          "reason": "source ref not present in this checkout (ref-coverage artifact)"}
    except Exception as exc:  # pragma: no cover - defensive
        blob_check = {"performed": False, "reason": f"{type(exc).__name__}: {exc}"}
    if blob_check.get("performed") and not blob_check.get("match"):
        record = {
            "schema": "lex-evaluation-serve-verdict-crosscheck/1",
            "run_id": RUN_ID,
            "verdict": "ENVIRONMENT_ERROR_VENDORED_BLOB_DRIFT",
            "blob_check": blob_check,
        }
        print(json.dumps(record, indent=1))
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(record, indent=1), encoding="utf-8")
        return 2

    rows = extract_rows(discharge, standready, team)
    cmp_main = compare(rows)

    # ---- non-vacuity controls (in-memory perturbations) -----------------
    # Order matters: MUTATE the payload copy FIRST, THEN extract the rows.
    # (An earlier revision extracted before mutating and therefore detected
    # nothing - the controls failed and the instrument correctly exited 1.
    # That failure is preserved in the run history as evidence that the
    # controls are load-bearing, not decorative.)
    controls = []

    d2 = _deepcopy(discharge)
    d2["adjudication"]["label_gate"]["n_scored"] = 1
    rows2 = extract_rows(d2, standready, team)
    g2 = compare(rows2)
    controls.append({"name": "perturb_label_n_scored_0_to_1",
                     "expected_quantity": "label.n_scored",
                     "detected": any(d["quantity"] == "label.n_scored"
                                     for d in g2["divergences"]),
                     "n_divergent_after_perturbation": g2["n_divergent"]})

    d3 = _deepcopy(discharge)
    d3["adjudication"]["geometry_gate"]["per_bundle_counts"]["de-kapitalverletzung"] = 6
    rows3 = extract_rows(d3, standready, team)
    g3 = compare(rows3)
    controls.append({"name": "perturb_geometry_de_3_to_6",
                     "expected_quantity": "geometry.per_bundle_counts.de-kapitalverletzung",
                     "detected": any(d["quantity"] == "geometry.per_bundle_counts.de-kapitalverletzung"
                                     for d in g3["divergences"]),
                     "n_divergent_after_perturbation": g3["n_divergent"]})

    d4 = _deepcopy(discharge)
    d4["packet"]["packet_json_sha256"] = "0" * 64
    rows4 = extract_rows(d4, standready, team)
    g4 = compare(rows4)
    controls.append({"name": "perturb_packet_json_sha",
                     "expected_quantity": "identity.packet_json_sha256",
                     "detected": any(d["quantity"] == "identity.packet_json_sha256"
                                     for d in g4["divergences"]),
                     "n_divergent_after_perturbation": g4["n_divergent"]})

    s2 = _deepcopy(standready)
    for q in s2["mega_cluster_disclosure_conformance"]["per_question"]:
        if q.get("qid") == "de-kapitalverletzung":
            q["size_based_share"] = 0.9999
    rows5 = extract_rows(discharge, s2, team)
    g5 = compare(rows5)
    controls.append({"name": "perturb_standready_mega_share_de",
                     "expected_quantity": "mega_share.de-kapitalverletzung",
                     "detected": any(d["quantity"] == "mega_share.de-kapitalverletzung"
                                     for d in g5["divergences"]),
                     "n_divergent_after_perturbation": g5["n_divergent"],
                     "note": "proves the stand-ready-record-sourced rows are live too"})

    t2 = _deepcopy(team)
    t2["label_half"]["n_supported"] = 9
    rows6 = extract_rows(discharge, standready, t2)
    g6 = compare(rows6)
    controls.append({"name": "perturb_team_verdict_n_supported_0_to_9",
                     "expected_quantity": "label.n_supported",
                     "detected": any(d["quantity"] == "label.n_supported"
                                     for d in g6["divergences"]),
                     "n_divergent_after_perturbation": g6["n_divergent"],
                     "note": "proves the comparator detects divergence on the TEAM side, not only the lane side"})

    non_vacuity_ok = all(c["detected"] for c in controls)

    # ---- serve-verdict landing + superseded state sentence --------------
    superseded_sentence = "No serve verdict has landed."
    state = load(STATE_PATH) if STATE_PATH.is_file() else {}
    narrative = dig(state, "summary", "narrative", default="") or ""
    landing = {
        "serve_verdict_landed": True,
        "outcome": dig(team, "verdict", "outcome"),
        "team_run_id": "39371834165",
        "team_id": "frontier-packet-serve-audit",
        "audit_gate": "results/audit/frontier/frontier-packet-serve-audit/CYCLE_39371834165_GATE.json",
        "audit_gate_value": "PASS",
        "promote_commit": "95162685",
        "audit_commit_utc": "2026-10-20T05:23:51Z",
        "portfolio_status": _portfolio_status(),
        "owner_decision_required": dig(team, "verdict", "owner_decision_required"),
        "one_sentence_recommendation": dig(team, "verdict", "one_sentence_recommendation"),
        "superseded_state_sentence": {
            "verbatim": superseded_sentence,
            "where": "state/evaluation.json summary.narrative (written by run 39379766198)",
            "present_in_current_state": superseded_sentence in narrative,
            "correction": ("An independent serve verdict HAS landed and is promoted: "
                           "frontier-packet-serve-audit run 39371834165, gate=PASS "
                           "safe_to_integrate=true, promote commit 95162685, outcome "
                           "BOUNDED-NEGATIVE (the packet is not served; both DO-NOT-SERVE "
                           "orders stand). The sentence above is preserved verbatim as "
                           "history and superseded, never deleted."),
        },
    }

    # ---- discharge-time population pin refresh (re-hash, never edit) ----
    population_pin = {
        "refreshed_at_run": RUN_ID,
        "refresh_meaning": ("re-hashed and re-recorded AT DISCHARGE TIME under this run id, "
                            "per direction v60 'the stand-ready falsifier's population pin is "
                            "refreshed at discharge time, not before'. No frozen file, rubric, "
                            "incumbent or predicate is edited by this refresh."),
        "frozen_incumbent_population": dig(discharge, "adjudication", "label_gate",
                                           "incumbent_population"),
        "packet_scored_population": {
            "n_scored": dig(discharge, "adjudication", "label_gate", "n_scored"),
            "n_supported": dig(discharge, "adjudication", "label_gate", "n_supported"),
            "support_rate": dig(discharge, "adjudication", "label_gate", "support_rate"),
        },
        "team_scored_population_same_bytes": {
            "n_scored": dig(team, "label_half", "n_scored"),
            "n_supported": dig(team, "label_half", "n_supported"),
            "support_rate": dig(team, "label_half", "support_rate"),
        },
        "population_pinned_regression_verdict": dig(discharge, "adjudication", "label_gate",
                                                    "regression_verdict"),
        "not_applicable_is_not_a_pass": True,
        "frozen_files_edited": [],
        "rehash_proof": {
            "rules_label": checks["evaluation/frozen_bars/RULES_LABEL.json"],
            "rules_geometry": checks["evaluation/frozen_bars/RULES_GEOMETRY.json"],
            "verdict_contract": checks["evaluation/frozen_bars/VERDICT_CONTRACT.json"],
        },
    }

    # ---- expected divergence named by the team itself -------------------
    team_named = dig(team, "crosscheck", "divergence_headline", default=[]) or []

    exit_code = 0
    verdict = "CROSSCHECK_COMPLETE"
    if not non_vacuity_ok:
        exit_code = 1
        verdict = "CROSSCHECK_CONTROL_FAILED_INSTRUMENT_VACUOUS"

    record = {
        "schema": "lex-evaluation-serve-verdict-crosscheck/1",
        "run_id": RUN_ID,
        "direction_version": hyp.get("direction_version"),
        "dispatch_mode": hyp.get("dispatch_mode"),
        "generated_at_utc": utcnow(),
        "elapsed_s": round(time.time() - t0, 3),
        "hypothesis_sha256": sha256_file(HYP_PATH),
        "freeze_record_sha256": sha256_file(
            REPO / "evaluation/SERVE_VERDICT_CROSSCHECK_FREEZE_RECORD_V1.json"),
        "inputs": {
            "lane_discharge": {"path": str(DISCHARGE_PATH.relative_to(REPO)),
                               "sha256": sha256_file(DISCHARGE_PATH)},
            "lane_stand_ready": {"path": str(STANDREADY_PATH.relative_to(REPO)),
                                 "sha256": sha256_file(STANDREADY_PATH)},
            "vendored_team_verdict": {"path": str(VENDORED.relative_to(REPO)),
                                      "sha256": sha256_file(VENDORED),
                                      "blob_crosscheck": blob_check},
            "packet_dir": args.packet_dir,
        },
        "identity_checks": checks,
        "identity_all_match": True,
        "side_by_side": rows,
        "comparison": cmp_main,
        "expected_divergence_named_by_the_team": team_named,
        "serve_verdict_landing": landing,
        "population_pin_refresh": population_pin,
        "non_vacuity_controls": controls,
        "non_vacuity_all_hold": non_vacuity_ok,
        "verdict": verdict,
        "exit_code": exit_code,
        "claim_ceiling": (
            "Cross-check of this lane's PUBLISHED numbers against the independently "
            "ACCEPTED serve-audit team's recomputation on the same packet-of-record V3 "
            "bytes. It does NOT re-derive, edit or re-tune any threshold, bar, rubric, "
            "incumbent or predicate; does NOT certify LABEL_SOUND or GEOMETRY_SOUND; "
            "does NOT lift any DO-NOT-SERVE order; does NOT override the accepted "
            "BOUNDED-NEGATIVE serve verdict; and authorises NO owner question. "
            "human_gate_ready, machine_gate_ready, packet_admitted and "
            "ready_for_owner_session all stay false; owner_decision_required stays false."),
    }

    text = json.dumps(record, indent=1, sort_keys=False)
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return exit_code


def _deepcopy(obj):
    return json.loads(json.dumps(obj))


def _portfolio_status() -> dict:
    """Read the live control-plane portfolio when staged, else disclose fallback."""
    for candidate in (Path("/tmp/lex_control/state/frontier_portfolio.json"),
                      REPO / "state/frontier_portfolio.json"):
        if candidate.is_file():
            try:
                data = json.load(open(candidate, encoding="utf-8"))
                for team in data.get("teams", []):
                    if team.get("team_id") == "frontier-packet-serve-audit":
                        return {
                            "source": str(candidate),
                            "status": team.get("status"),
                            "promotion_status": team.get("promotion_status"),
                            "run_history_len": len(team.get("run_history") or []),
                        }
            except Exception:
                continue
    return {"source": None, "status": "TERMINATED (pinned at run 39381093325, "
            "state/frontier_portfolio.json on origin/main at dispatch)",
            "promotion_status": "PROMOTED", "run_history_len": None}


if __name__ == "__main__":
    sys.exit(main())
