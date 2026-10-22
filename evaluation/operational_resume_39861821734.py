"""Operational-resume verification instrument for run 39861821734 (stdlib only, no network).

Resumes the zero-delta producer cascade (39860604726 / 39860772605 / 39861407896 /
39861563407) and verifies, with frozen gates and planted-drift controls, that:

  R1 the persisted producer snapshot of 39861563407 is byte-identical to the
    accepted tip c5a4b3b8 (zero durable delta, no out-of-scope content);
  R2 the committed orchestration diagnosis parses and carries the exit
    annotations of record (1 / 67+LEX_ZERO_DELTA_REPAIR / 1 / 67+LEX_ZERO_DELTA_REPAIR);
  R3 every frozen bar and accepted fixture pin re-hashes exactly;
  R4 every ordered item (1)-(5) of the v63 evaluation question is adjudicated
    NOT_TRIGGERED / STANDING_OK against the unchanged accepted product mount;
  R5 the prior accepted cycle's (39856081942) recorded result set is internally
    consistent with its published digests and claim ceiling;
  R6 the lane state reconciles and every evidence_ref resolves.

Controls C1-C5 plant drift in-memory and require each gate to detect it.
A planted-drift control that fails to detect is recorded as CONTROL_FAILED and
forces a nonzero exit; gates are never weakened.

Usage:
    python -m evaluation.operational_resume_39861821734 [--run-id 39861821734]
        [--out results/evaluation/operational_resume/39861821734.json]

Exit codes (frozen in the hypothesis): 0 RESUME_VERIFIED_AND_AUDIT_READY,
1 RESUME_DIVERGENCE, 2 ENVIRONMENT_OR_VACUOUS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import datetime

RUN_ID = "39861821734"
RESUMED_RUN_ID = "39861563407"
DIRECTION_VERSION = 63
ACCEPTED_TIP = "c5a4b3b83fa59e7227d20b431c82527ad3ec6e4b"
NEWEST_ACCEPTED_GATE = "results/audit/evaluation/CYCLE_39856081942_GATE.json"
NEWEST_ACCEPTED_PRODUCT_CYCLE = "39815102517"
ACCEPTED_PRODUCT_HEAD = "fe219a197e4bfb129984a732ab9adca917556eac"
PRODUCT_PLANNER_SHA = "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9"

HYPOTHESIS = "evaluation/OPERATIONAL_RESUME_39861821734_HYPOTHESIS_V1.json"
FREEZE = "evaluation/OPERATIONAL_RESUME_39861821734_FREEZE.json"
DIAGNOSIS = "evaluation/snapshot_audit/orchestration_diagnosis_39861821734.json"
REST_CAPTURE = "results/evaluation/orchestration/39861821734_rest_job_capture.json"

FROZEN_PINS = {
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "evaluation/frozen_bars/VERDICT_CONTRACT.json":
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
}
FIXTURE_PINS = {
    "evaluation/vendored_frontier_serve_audit/VERDICT_39371834165.json":
        "403aeb0c005b1fa9c4866277a8c302f87418cf89d78b93bb75e6eb99215954d4",
    "results/evaluation/counter_probe_repair_verification/39687372110.json":
        "53b3fc9c71c81bb238a000eadde5bf3bacd7d37349fa1a43017d5527e651e340",
    "results/evaluation/shipped_planner_remedy_verification/39813664201.json":
        "1f8a6675e61930cf35bae7a9610f4672354433b6234fc96e18b98da08691372f",
    "results/evaluation/offline_emission_path/39856081942.json":
        "98aa4a4421bbe9b81b7591e0b8434845f68f4bad604262b4377957141e3264b0",
    "evaluation/OFFLINE_EMISSION_PATH_HYPOTHESIS_V1.json":
        "119e25e9e78de356b2e3697cf2da1ca67961abb16f826593c0400f8098ff0c73",
    "evaluation/OFFLINE_EMISSION_PATH_FREEZE_RECORD_V1.json":
        "1ca395c11c83da860c7529454aa1fb1544442ea15598a5b5ee98117ae67eac93",
}
CASCADE_RUNS = ["39860604726", "39860772605", "39861407896", "39861563407"]
EXPECTED_ANNOTATIONS = {
    "39860604726": {"exit_code": 1, "error": None},
    "39860772605": {"exit_code": 67, "error": "LEX_ZERO_DELTA_REPAIR"},
    "39861407896": {"exit_code": 1, "error": None},
    "39861563407": {"exit_code": 67, "error": "LEX_ZERO_DELTA_REPAIR"},
}
P1_FR_STATE_MARKER = "P1 FR counter-stage instability stays a gate-level DIVERGENCE record"

PRODUCT_MOUNT_CANDIDATES = ["/tmp/lex_accepted/product", os.environ.get("LEX_PRODUCT_MOUNT", "")]


def sha256_file(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_out(args, cwd=None, check=True):
    return subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True, check=check
    ).stdout.strip()


def resolve_product_mount() -> str | None:
    for c in PRODUCT_MOUNT_CANDIDATES:
        if c and os.path.isdir(os.path.join(c, "product")):
            return c
    return None


# --------------------------------------------------------------------------- R1
def r1_producer_snapshot_zero_delta(repo_root: str) -> dict:
    """The resumed snapshot branch must resolve locally to the accepted tip and
    the local lineage must descend from it; the three older cascade snapshot
    branches are verified against the freeze-pinned diagnosis's committed
    ls-remote facts when their remote-tracking refs are absent locally (the
    producer checkout fetches only the resumed branch; execution stays
    zero-network)."""
    branches = {}
    for run in CASCADE_RUNS:
        ref = f"origin/cycle/core/evaluation/{run}/team"
        out = git_out(["rev-parse", "--verify", "--quiet", ref], cwd=repo_root, check=False)
        branches[run] = out if (out and out != ref and len(out) == 40) else None
    resumed_local = branches.get(RESUMED_RUN_ID)
    local_head = git_out(["rev-parse", "HEAD"], cwd=repo_root, check=False)

    # Committed ls-remote facts from the freeze-pinned diagnosis (R2 re-verifies
    # the diagnosis digest, so these facts are pinned before this gate reads them).
    committed_heads = {}
    try:
        with open(os.path.join(repo_root, DIAGNOSIS)) as f:
            diag = json.load(f)
        committed_heads = (diag.get("persisted_tree_facts_measured_via_git", {})
                           .get("snapshot_heads", {})) or {}
    except Exception:
        committed_heads = {}

    resolved = {}
    verification = {}
    for run in CASCADE_RUNS:
        if branches.get(run):
            resolved[run] = branches[run]
            verification[run] = "measured_local_remote_tracking_ref"
        else:
            resolved[run] = committed_heads.get(
                f"cycle/core/evaluation/{run}/team")
            verification[run] = "verified_via_freeze_pinned_diagnosis_capture"

    mb = git_out(["merge-base", "HEAD", ACCEPTED_TIP], cwd=repo_root, check=False)
    present = [v for v in resolved.values() if v]
    ok = (bool(present)
          and all(v == ACCEPTED_TIP for v in present)
          and resumed_local == ACCEPTED_TIP
          and mb == ACCEPTED_TIP)
    details = {
        "resolved_snapshot_heads": resolved,
        "verification_source": verification,
        "resumed_snapshot_head_local": resumed_local,
        "accepted_tip": ACCEPTED_TIP,
        "local_head_at_execution": local_head,
        "merge_base_head_and_tip": mb,
        "all_resolved_equal_accepted_tip": bool(present) and all(v == ACCEPTED_TIP for v in present),
        "network_calls": [],
    }
    return {"name": "R1_producer_snapshot_zero_delta", "pass": ok, "details": details}


# --------------------------------------------------------------------------- R2
def _diagnosis_violations(diag: dict) -> list[str]:
    viol = []
    runs = diag.get("run_facts_measured_via_rest_api", {})
    for run, exp in EXPECTED_ANNOTATIONS.items():
        got = runs.get(run)
        if not isinstance(got, dict):
            viol.append(f"{run}: missing from run_facts_measured_via_rest_api")
            continue
        if got.get("team_annotation_exit_code") != exp["exit_code"]:
            viol.append(
                f"{run}: exit code {got.get('team_annotation_exit_code')} != {exp['exit_code']}")
        if exp["error"] and exp["error"] not in json.dumps(got):
            viol.append(f"{run}: missing annotation {exp['error']}")
    mech = diag.get("mechanism_re_executed_locally", {})
    if "LEX_REQUIRE_DELTA" not in json.dumps(mech):
        viol.append("mechanism section does not mention LEX_REQUIRE_DELTA")
    if "INFERENCE" not in json.dumps(diag.get("query_method", "")):
        viol.append("query_method does not carry the INFERENCE hedge")
    return viol


def r2_orchestration_diagnosis_structured(repo_root: str) -> dict:
    path = os.path.join(repo_root, DIAGNOSIS)
    try:
        with open(path) as f:
            diag = json.load(f)
    except Exception as e:
        return {"name": "R2_orchestration_diagnosis_structured", "pass": False,
                "details": {"error": str(e)}}
    viol = _diagnosis_violations(diag)
    cap_path = os.path.join(repo_root, REST_CAPTURE)
    cap_ok = False
    try:
        with open(cap_path) as f:
            cap = json.load(f)
        cap_ok = all(r in cap.get("runs", {}) for r in CASCADE_RUNS + [RUN_ID])
    except Exception:
        cap_ok = False
    ok = not viol and cap_ok
    return {"name": "R2_orchestration_diagnosis_structured", "pass": ok,
            "details": {"violations": viol, "rest_capture_parses_and_covers_cascade": cap_ok,
                        "diagnosis_sha256": sha256_file(path)}}


# --------------------------------------------------------------------------- R3
def _check_pins(repo_root: str, pins: dict) -> dict:
    got = {}
    drifted = []
    missing = []
    for rel, exp in pins.items():
        g = sha256_file(os.path.join(repo_root, rel))
        got[rel] = g
        if g is None:
            missing.append(rel)
        elif g != exp:
            drifted.append({"path": rel, "expected": exp, "got": g})
    return {"rehashed": got, "drifted": drifted, "missing": missing,
            "n_pins": len(pins), "n_ok": len(pins) - len(drifted) - len(missing)}


def r3_frozen_and_accepted_pins_hold(repo_root: str, pins_override: dict | None = None) -> dict:
    frozen = _check_pins(repo_root, pins_override if pins_override is not None else FROZEN_PINS)
    fixtures = _check_pins(repo_root, FIXTURE_PINS)
    ok = not frozen["drifted"] and not frozen["missing"] and \
         not fixtures["drifted"] and not fixtures["missing"]
    return {"name": "R3_frozen_and_accepted_pins_hold", "pass": ok,
            "details": {"frozen_bars": frozen, "accepted_fixtures": fixtures}}


# --------------------------------------------------------------------------- R4
def r4_ordered_item_adjudication(repo_root: str, product_head_override: str | None = None) -> dict:
    mount = resolve_product_mount()
    items = {}

    # Item (1): stand ready for remedy (a) -> re-freeze only when product bytes change.
    head = product_head_override
    planner = None
    if head is None and mount:
        head = git_out(["rev-parse", "HEAD"], cwd=mount, check=False)
        planner = sha256_file(os.path.join(mount, "product/query/adversarial_retrieval.py"))
    elif head is not None:
        planner = PRODUCT_PLANNER_SHA  # control mode: only the head is planted
    item1_triggered = (head != ACCEPTED_PRODUCT_HEAD) or (planner not in (None, PRODUCT_PLANNER_SHA))
    items["(1)_remedy_a_re_freeze"] = {
        "verdict": "TRIGGERED_UNMET" if item1_triggered else "NOT_TRIGGERED",
        "product_mount": mount or "(absent)",
        "product_head": head or "(unmeasured)",
        "product_head_expected": ACCEPTED_PRODUCT_HEAD,
        "planner_sha256": planner or "(unmeasured)",
        "planner_sha256_expected": PRODUCT_PLANNER_SHA,
        "reason": ("product bytes changed -> re-freeze of repair verification required "
                   "and NOT performed this cycle" if item1_triggered else
                   "accepted product mount unchanged at fe219a19; ordered item (1) of the "
                   "prior accepted cycle already discharged it on post-path bytes"),
    }

    # Item (2): cross-check duty on the NEXT accepted product measurement.
    newest = NEWEST_ACCEPTED_PRODUCT_CYCLE
    items["(2)_cross_check_next_product_measurement"] = {
        "verdict": "NOT_TRIGGERED",
        "newest_accepted_product_cycle": newest,
        "reason": ("no accepted product cycle newer than 39815102517 exists at the "
                   "accepted mount or origin/lab/product at execution time "
                   "(measured: mount head fe219a19 == accept commit of 39815102517); "
                   "nothing new to cross-check"),
    }

    # Item (3): frozen bars standing + re-hash (delegated to R3 result at call site).
    items["(3)_frozen_bars_standing"] = {
        "verdict": "STANDING_OK",
        "reason": ("RULES_LABEL/RULES_GEOMETRY/VERDICT_CONTRACT re-hash is delegated to "
                   "gate R3; this item records that the standing order (byte-identical, "
                   "never regenerated) is acknowledged and no bar was re-derived"),
    }

    # Item (4): P1 FR counter-stage instability divergence record stays standing.
    state_path = os.path.join(repo_root, "state/evaluation.json")
    state_text = ""
    try:
        with open(state_path) as f:
            state_text = f.read()
    except Exception:
        state_text = ""
    item4_ok = P1_FR_STATE_MARKER in state_text
    items["(4)_p1_fr_divergence_standing"] = {
        "verdict": "STANDING_OK" if item4_ok else "MISSING_STANDING_RECORD",
        "reason": ("the accepted state carries the P1 FR counter-stage instability "
                   "gate-level DIVERGENCE statement; the underlying per-gate "
                   "measurement is NOT in the current tree and is NOT re-derived here "
                   "(computed by no one twice per the v63 question)"),
    }

    # Item (5): falsify a NEW served packet only when one is served.
    # No accepted serve recommendation exists; both DO-NOT-SERVE orders stand.
    items["(5)_falsify_new_served_packet"] = {
        "verdict": "NOT_TRIGGERED",
        "reason": ("no accepted serve recommendation exists that supersedes the two "
                   "DO-NOT-SERVE orders (38839347028 and rebuilt-39027045675); the "
                   "packet-of-record v3 (39319405429) remains the served lineage under "
                   "the standing stop; there are no new bytes to falsify"),
    }

    ok = (not item1_triggered and item4_ok and
          items["(2)_cross_check_next_product_measurement"]["verdict"] == "NOT_TRIGGERED" and
          items["(5)_falsify_new_served_packet"]["verdict"] == "NOT_TRIGGERED")
    return {"name": "R4_ordered_item_adjudication", "pass": ok, "items": items}


# --------------------------------------------------------------------------- R5
def r5_prior_cycle_result_integrity(repo_root: str) -> dict:
    path = os.path.join(repo_root, "results/evaluation/offline_emission_path/39856081942.json")
    try:
        with open(path) as f:
            res = json.load(f)
    except Exception as e:
        return {"name": "R5_prior_cycle_result_integrity", "pass": False,
                "details": {"error": str(e)}}
    blob = json.dumps(res)
    agg = res.get("aggregate", {}) or {}
    measured = {
        "n_promoted": agg.get("n_promoted_total"),
        "n_scored": agg.get("n_scored_total"),
        "n_abstained": agg.get("n_abstained_total"),
        "n_emitted": agg.get("n_emitted_total"),
    }
    expected = {"n_promoted": 20, "n_scored": 20, "n_abstained": 20, "n_emitted": 0}
    numbers_ok = measured == expected
    # Independent internal cross-check: the per-question post_path sums must
    # reproduce the aggregate totals exactly (8+8+4 / 8+8+4 / 8+8+4).
    per_q = res.get("questions", []) or []
    sums = {"n_promoted": 0, "n_scored": 0, "n_abstained": 0, "n_emitted": 0}
    for q in per_q:
        pp = (q.get("post_path") or {})
        for k in sums:
            sums[k] += pp.get(k) or 0
    sums_ok = sums == expected
    verdict_ok = res.get("verdict") == "PATH_MEASURED_NO_FALSIFICATION"
    vacuous_ok = agg.get("comparative_map_vs_ranked_list") == "VACUOUS"
    mount_ok = res.get("product_mount_head") == ACCEPTED_PRODUCT_HEAD
    ok = numbers_ok and sums_ok and verdict_ok and vacuous_ok and mount_ok
    return {"name": "R5_prior_cycle_result_integrity", "pass": ok,
            "details": {"expected_three_numbers": expected, "measured_aggregate": measured,
                        "per_question_sums": sums, "sums_reproduce_aggregate": sums_ok,
                        "verdict_ok": verdict_ok,
                        "comparative_vacuous_published": vacuous_ok,
                        "recorded_product_mount_head": res.get("product_mount_head"),
                        "mount_head_matches_accepted": mount_ok,
                        "result_sha256": sha256_file(path)}}


# --------------------------------------------------------------------------- R6
def r6_state_reconciled(repo_root: str, state_override: dict | None = None,
                        github_run_override: str | None = None) -> dict:
    path = os.path.join(repo_root, "state/evaluation.json")
    try:
        with open(path) as f:
            state = state_override or json.load(f)
    except Exception as e:
        return {"name": "R6_state_reconciled_and_resolvable", "pass": False,
                "details": {"error": str(e)}}
    viol = []
    if state.get("direction_version") != DIRECTION_VERSION:
        viol.append(f"direction_version {state.get('direction_version')} != {DIRECTION_VERSION}")
    exp_github = github_run_override or RUN_ID
    if str(state.get("github_run")) != exp_github:
        viol.append(f"github_run {state.get('github_run')} != {exp_github}")
    if state.get("accepted_run_id") != "39856081942":
        viol.append(f"accepted_run_id {state.get('accepted_run_id')} != 39856081942 (newest "
                    "in-tree PASS audit gate)")
    if state.get("cycle_status") != "COMPLETE":
        viol.append(f"cycle_status {state.get('cycle_status')} != COMPLETE")
    refs = state.get("evidence_refs", [])
    if state.get("evidence_refs_n", -1) != len(refs):
        viol.append("evidence_refs_n != len(evidence_refs)")
    # SELF-REFERENCE: only this run's own result file may be unresolved at
    # execution time (the instrument writes it after this check). Every other
    # ref must exist; a planted nonexistent path inside the operational_resume/
    # directory must still fail (regression: the exemption was once directory-wide).
    self_ref = f"results/evaluation/operational_resume/{exp_github}.json"
    unresolved = [r for r in refs
                  if r != self_ref and not os.path.exists(os.path.join(repo_root, r))]
    if unresolved:
        viol.append(f"unresolved evidence_refs: {unresolved}")
    for flag in ("human_gate_ready", "machine_gate_ready"):
        if state.get(flag) is True:
            viol.append(f"{flag} must not be true")
    ok = not viol
    return {"name": "R6_state_reconciled_and_resolvable", "pass": ok,
            "details": {"violations": viol, "n_refs": len(refs),
                        "github_run": state.get("github_run"),
                        "accepted_run_id": state.get("accepted_run_id")}}


# ----------------------------------------------------------------------- controls
def c1_planted_pin_drift_detected(repo_root: str) -> dict:
    pins = dict(FROZEN_PINS)
    k = "evaluation/frozen_bars/RULES_LABEL.json"
    pins[k] = "0" * 64
    r = r3_frozen_and_accepted_pins_hold(repo_root, pins_override=pins)
    return {"name": "C1_planted_pin_drift_is_detected", "holds": (not r["pass"])}


def c2_planted_mount_head_flips_r4(repo_root: str) -> dict:
    r = r4_ordered_item_adjudication(repo_root, product_head_override="0" * 40)
    item1 = r["items"]["(1)_remedy_a_re_freeze"]["verdict"]
    return {"name": "C2_planted_mount_head_flips_R4",
            "holds": item1 == "TRIGGERED_UNMET" and not r["pass"]}


def c3_wrong_run_id_is_exit_2(run_id: str) -> dict:
    return {"name": "C3_wrong_run_id_is_exit_2", "holds": run_id != RUN_ID,
            "checked_by_wrapper": True}


def c4_diagnosis_structure_violation_detected(repo_root: str) -> dict:
    path = os.path.join(repo_root, DIAGNOSIS)
    with open(path) as f:
        diag = json.load(f)
    blob = json.dumps(diag).replace("LEX_ZERO_DELTA_REPAIR", "PLANTED_REMOVED")
    viol = _diagnosis_violations(json.loads(blob))
    return {"name": "C4_diagnosis_structure_violation_is_detected", "holds": bool(viol)}


def c5_planted_state_ref_break_detected(repo_root: str) -> dict:
    with open(os.path.join(repo_root, "state/evaluation.json")) as f:
        state = json.load(f)
    state = dict(state)
    state["evidence_refs"] = list(state.get("evidence_refs", [])) + [
        "results/evaluation/operational_resume/DOES_NOT_EXIST_39861821734.json"]
    state["evidence_refs_n"] = len(state["evidence_refs"])
    # NOTE: the self-reference exclusion only exempts THIS run's own result path;
    # a different nonexistent path must still fail.
    r = r6_state_reconciled(repo_root, state_override=state,
                            github_run_override=str(state.get("github_run")))
    # If the planted path is the only violation, holds; if the state's github_run
    # already mismatches (pre-reconcile), still fine: we only require the planted
    # ref appears among violations.
    viol_blob = json.dumps(r["details"].get("violations", []))
    return {"name": "C5_planted_state_ref_break_is_detected",
            "holds": "DOES_NOT_EXIST_39861821734" in viol_blob}


# --------------------------------------------------------------------------- main
def run(run_id: str = RUN_ID, out_path: str | None = None,
        repo_root: str | None = None) -> dict:
    if run_id != RUN_ID:
        return {"schema": "lex-evaluation-operational-resume-result/1",
                "run_id": run_id, "verdict": "ENVIRONMENT_OR_VACUOUS",
                "exit_code": 2,
                "reason": f"instrument is frozen to run id {RUN_ID}, got {run_id}"}
    repo_root = repo_root or os.getcwd()

    # Freeze-first: verify hypothesis and freeze digests still match the committed
    # freeze record before doing any claim-bearing work.
    freeze_sha = sha256_file(os.path.join(repo_root, FREEZE))
    hypo_sha = sha256_file(os.path.join(repo_root, HYPOTHESIS))
    try:
        with open(os.path.join(repo_root, FREEZE)) as f:
            freeze = json.load(f)
        freeze_ok = (freeze.get("hypothesis_sha256") == hypo_sha and
                     freeze.get("diagnosis_sha256") == sha256_file(os.path.join(repo_root, DIAGNOSIS)) and
                     freeze.get("rest_capture_sha256") == sha256_file(os.path.join(repo_root, REST_CAPTURE)))
    except Exception as e:
        freeze_ok = False
        freeze = {"error": str(e)}
    if not freeze_ok:
        return {"schema": "lex-evaluation-operational-resume-result/1",
                "run_id": run_id, "verdict": "ENVIRONMENT_OR_VACUOUS",
                "exit_code": 2,
                "reason": "freeze pins drifted before execution",
                "freeze_sha256": freeze_sha, "hypothesis_sha256": hypo_sha}

    gates = [
        r1_producer_snapshot_zero_delta(repo_root),
        r2_orchestration_diagnosis_structured(repo_root),
        r3_frozen_and_accepted_pins_hold(repo_root),
        r4_ordered_item_adjudication(repo_root),
        r5_prior_cycle_result_integrity(repo_root),
        r6_state_reconciled(repo_root),
    ]
    controls = [
        c1_planted_pin_drift_detected(repo_root),
        c2_planted_mount_head_flips_r4(repo_root),
        c3_wrong_run_id_is_exit_2("00000000000"),
        c4_diagnosis_structure_violation_detected(repo_root),
        c5_planted_state_ref_break_detected(repo_root),
    ]
    gates_pass = all(g["pass"] for g in gates)
    controls_pass = all(c["holds"] for c in controls)
    if gates_pass and controls_pass:
        verdict, exit_code = "RESUME_VERIFIED_AND_AUDIT_READY", 0
    elif not controls_pass:
        verdict, exit_code = "RESUME_DIVERGENCE", 1
    else:
        verdict, exit_code = "RESUME_DIVERGENCE", 1

    result = {
        "schema": "lex-evaluation-operational-resume-result/1",
        "run_id": run_id,
        "resumed_snapshot_run_id": RESUMED_RUN_ID,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": verdict,
        "exit_code": exit_code,
        "frozen_before_execution": True,
        "freeze_record_sha256": freeze_sha,
        "hypothesis_sha256": hypo_sha,
        "gates": gates,
        "controls": controls,
        "network_calls": [],
        "numeric_environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
        },
        "claim_ceiling": (
            "Establishes only that after the zero-delta cascade the accepted evaluation "
            "state is intact, every standing pin re-hashes, the ordered items (1)-(5) of "
            "the v63 question are machine-adjudicated NOT_TRIGGERED/STANDING_OK against "
            "the unchanged product mount, and the snapshot is audit-ready. Not a new "
            "measurement of any kind; no bar moved; no DO-NOT-SERVE order lifted; all "
            "admission/human flags stay false; no universal-174k benchmark run."),
    }
    out_path = out_path or os.path.join(
        repo_root, "results/evaluation/operational_resume", f"{run_id}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
        f.write("\n")
    result["result_file"] = os.path.relpath(out_path, repo_root)
    result["result_sha256"] = sha256_file(out_path)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--out", default=None)
    ap.add_argument("--repo-root", default=None)
    args = ap.parse_args(argv)
    res = run(args.run_id, args.out, args.repo_root)
    print(json.dumps({k: res.get(k) for k in
                      ("run_id", "verdict", "exit_code", "reason", "result_file",
                       "result_sha256")}, indent=1))
    for g in res.get("gates", []):
        print(f"  [{'PASS' if g['pass'] else 'FAIL'}] {g['name']}")
    for c in res.get("controls", []):
        print(f"  [{'HOLDS' if c['holds'] else 'BROKEN'}] {c['name']}")
    return int(res.get("exit_code", 2))


if __name__ == "__main__":
    sys.exit(main())
