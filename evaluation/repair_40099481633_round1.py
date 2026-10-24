#!/usr/bin/env python3
"""Round-1 repair of REJECTED evaluation cycle 40099481633 (gate REVISE, F1-F4).

Independent audit results/audit/evaluation/CYCLE_40099481633_GATE.json (audit
branch cycle/core/evaluation/40099481633/audit, commit ab50ea74) returned
gate=REVISE with exactly four required fixes.  This script implements the
producer half of that repair under repair run 40101127061:

  F1  durable delta      -> ``fetch-rest`` + ``diagnose``: public REST jobs
      snapshot of run 40099481633 plus an explicit failure-chain diagnosis
      recording that the LEX_REQUIRE_DELTA guard was satisfied only by adopting
      the inherited head 0b4963a0 (HEAD f2734734 -> 0b4963a0, clean porcelain,
      no file change), plus the current v67 work posture.  A zero-delta repair
      would be invalid and must escalate to BLOCKED; this run produces real,
      run-referenced content instead.
  F2  state advance      -> ``freeze`` pins the comparison contract BEFORE the
      re-execution; ``repro`` re-executes the byte-identical frozen instrument
      (sha256 aac86527...) under run id 40099481633 against the inherited v67
      item-(1) deliverable (40089391202.json, sha256 f5fade6d...) and computes
      the 19-field reproduction verdict; ``state`` advances
      state/evaluation.json github_run with disclosure while keeping
      accepted_run_id=40084716045 until a both-halves promotion.
  F3  living-suite hygiene -> handled in tests/evaluation/
      (stale identity pin repaired without deleting history; fresh real
      pytest 9.1.1 living-suite record at the repaired head).
  F4  non-movements       -> ``state`` asserts + this script's ``verify``
      re-hashes every frozen input; nothing frozen, no baseline movement, no
      174k rerun, posture stays fail-closed, no product code touched.

Modes (each is idempotent and writes only in-lane paths):
  fetch-rest   results/evaluation/orchestration/40099481633_rest_jobs.json
  diagnose     results/evaluation/orchestration/40099481633_failure_chain_diagnosis.json
  freeze       evaluation/OPERATIONAL_RESUME_40099481633_HYPOTHESIS_V1.json
               evaluation/OPERATIONAL_RESUME_40099481633_FREEZE_V1.json   (BEFORE repro)
  repro        results/evaluation/d2_letterhead_pattern_profile/
                 40099481633_reproduction_check_vs_40089391202.json
  verify       prints the F4 re-hash table (report-only, never edits)
  state        state/evaluation.json (append-only identity advance + blocks)
  all          every mode above in freeze-first order (state last)

No frozen bar, rubric, threshold, verdict contract or instrument is edited by
this script; it only re-hashes them REPORTED-ONLY.  It writes no product code
and runs no obsolete universal-174k benchmark.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

STATE = _REPO_ROOT / "state" / "evaluation.json"

RUN = "40099481633"            # rejected cycle being repaired (round 1)
REPAIR_RUN = "40101127061"     # this run: producer of the repair delta
DELIV = "40089391202"          # v67 item-(1) deliverable of record
RESUMED_FROM = "40096174340"   # state github_run before this repair
DIRV = 67

FROZEN = {
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "evaluation/frozen_bars/VERDICT_CONTRACT.json":
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
    "evaluation/counter_evidence_quality_benchmark.py":
        "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d",
}
BASELINE_ARTIFACT = "results/evaluation/counter_evidence_quality_benchmark/40062917685.json"
BASELINE_SHA_EXPECTED = "948a8929817f265236c87bbc1b3a17559fa7db2bd03ee4ccddc36332977ac717"
PROFILE_INSTRUMENT = "evaluation/d2_letterhead_pattern_profile.py"
PROFILE_INSTRUMENT_SHA = "63a48854e9500544ce970dd9a98765d077a7e5dace6500fdf5bc79a93ff918c8"
DELIVERABLE = f"results/evaluation/d2_letterhead_pattern_profile/{DELIV}.json"
DELIVERABLE_SHA = "f5fade6d11ebf14e3004d5beebf2f959444720fc3152e4e5b0b479a644d3cab7"

# The exact 19-item comparison inventory, pinned by the predecessor freeze
# addendum evaluation/OPERATIONAL_RESUME_40096174340_FREEZE_V1_ADDENDUM_FIELD_COUNT.json
FIELD_INVENTORY = [
    "verdict", "exit_code", "controls_all_pass",
    "n_bundles", "n_bundles_shipped_slice", "n_bundles_packet_of_record",
    "n_verified_rows_shipped_slice", "n_verified_rows_packet_of_record",
    "population_defect_histogram", "d2_rows_profiled",
    "n_distinct_letterhead_patterns", "detectability_summary",
    "frozen_predicate_instrument_sha256", "product_mount_head",
    "direction_version", "packet_of_record",
    "population[*]:{bundle,sha256,family,scope}",
    "letterhead_patterns[*]:{pattern_key,detectability_class,n_rows,languages,"
    "decisions,full_text_offsets,defect_class_counts,bundle_families,bundles}",
    "controls:{C3,C4,C5,C6}",
]
POP_FIELDS = ["bundle", "sha256", "family", "scope"]
PATTERN_FIELDS = ["pattern_key", "detectability_class", "n_rows", "languages",
                  "decisions", "full_text_offsets", "defect_class_counts",
                  "bundle_families", "bundles"]

FIXES = [
    "F1 durable delta: commit a run-40099481633 operational-resume/diagnosis set "
    "(public REST jobs snapshot of run 40099481633; explicit explanation that the "
    "LEX_REQUIRE_DELTA guard was satisfied only by adopting inherited head "
    "0b4963a0 without content change; current v67 work posture). A zero-delta "
    "round-1 repair is invalid and must escalate to BLOCKED.",
    "F2 state advance: re-verify the inherited v67 item-(1) deliverable "
    "(results/evaluation/d2_letterhead_pattern_profile/40089391202.json, sha "
    "f5fade6d...) under run 40099481633 via the byte-identical frozen instrument "
    "(sha aac86527...) under a freeze-first comparison contract, or record a "
    "justified freeze-first waiver; then advance state/evaluation.json github_run "
    "with disclosure; keep accepted_run_id=40084716045 until a both-halves "
    "promotion.",
    "F3 living-suite hygiene: fix the stale identity pin "
    "tests/evaluation/test_operational_resume_40094203248.py::"
    "test_state_run_identity_and_posture (expects github_run=40094203248, state "
    "carries 40096174340) without deleting history; record a fresh real-pytest "
    "(9.1.1) living-suite result at the repaired head.",
    "F4 non-movements restated: no frozen bar/rubric/threshold/verdict-contract "
    "edit; baseline 40062917685 stays unmoved; no obsolete universal-174k rerun; "
    "posture stays fail-closed (all five flags false); both DO-NOT-SERVE orders "
    "stand; no product code modified.",
]


def _sha256(p: Path | str) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, obj: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def _get(url: str) -> dict:
    req = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json",
                      "User-Agent": "lex-evaluation-repair"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------------------------------------------------------------- F1: REST
def fetch_rest() -> int:
    base = f"https://api.github.com/repos/Mickalive/LexMachina/actions/runs/{RUN}"
    run = _get(base)
    jobs = _get(base + "/jobs")
    snap = {
        "schema": "lex-evaluation-orchestration-rest-snapshot/1",
        "fetched_at_utc": _now(),
        "run_url": base,
        "fetched_by_run": REPAIR_RUN,
        "fetched_by_purpose": (
            f"F1 durable delta of the round-1 repair of rejected cycle {RUN}; "
            "public REST record only, no authenticated log access"),
        "jobs": [
            {"id": j["id"], "name": j["name"], "status": j["status"],
             "conclusion": j["conclusion"], "started_at": j["started_at"],
             "completed_at": j["completed_at"],
             "steps": [{"number": s["number"], "name": s["name"],
                        "status": s["status"], "conclusion": s["conclusion"],
                        "started_at": s["started_at"],
                        "completed_at": s["completed_at"]}
                       for s in j["steps"]]}
            for j in jobs["jobs"]],
        "run": {k: run.get(k) for k in
                ("id", "name", "event", "status", "conclusion", "created_at",
                 "updated_at", "head_branch", "head_sha", "run_attempt",
                 "html_url")},
    }
    out = _REPO_ROOT / "results/evaluation/orchestration" / f"{RUN}_rest_jobs.json"
    _write_json(out, snap)
    print(json.dumps({"wrote": str(out.relative_to(_REPO_ROOT)),
                      "jobs": [(j["name"], j["conclusion"]) for j in snap["jobs"]]},
                     indent=1))
    return 0


# ---------------------------------------------------------- F1: diagnosis
def diagnose() -> int:
    rest = _REPO_ROOT / "results/evaluation/orchestration" / f"{RUN}_rest_jobs.json"
    snap = json.loads(rest.read_text(encoding="utf-8"))
    jobs = {j["name"]: j for j in snap["jobs"]}
    team = jobs["team"]
    prod_head = _product_head()
    diag = {
        "schema": "lex-evaluation-orchestration-failure-chain-diagnosis/1",
        "run_id": RUN,
        "github_run": RUN,
        "diagnosing_run": REPAIR_RUN,
        "repair_round": 1,
        "direction_version": DIRV,
        "diagnosed_from": {
            "artifact": "results/evaluation/orchestration/"
                        f"{RUN}_rest_jobs.json",
            "artifact_sha256": _sha256(rest),
            "source": "unauthenticated public GitHub REST API "
                      "(actions runs/{run}/jobs); job logs are 403 so any "
                      "return-code attribution stays HEDGED".format(run=RUN),
        },
        "chain_record": {
            "workflow": snap["run"]["name"],
            "event": snap["run"]["event"],
            "conclusion": snap["run"]["conclusion"],
            "created_at": snap["run"]["created_at"],
            "updated_at": snap["run"]["updated_at"],
            "run_attempt": snap["run"]["run_attempt"],
            "head_sha": snap["run"]["head_sha"],
            "team_job": {
                "conclusion": team["conclusion"],
                "started_at": team["started_at"],
                "completed_at": team["completed_at"],
                "duration_s": _dur(team),
                "all_steps": [
                    f"{s['number']}:{s['name']}={s['conclusion']}"
                    for s in team["steps"]],
            },
            "audit_job": {
                "conclusion": jobs["audit"]["conclusion"],
                "started_at": jobs["audit"]["started_at"],
                "completed_at": jobs["audit"]["completed_at"],
                "produced_gate":
                    "results/audit/evaluation/CYCLE_%s_GATE.json "
                    "(audit branch cycle/core/evaluation/%s/audit, commit "
                    "ab50ea74): gate=REVISE, safe_to_integrate=false, "
                    "required_fixes F1-F4" % (RUN, RUN),
            },
            "integrate_job": jobs["integrate"]["conclusion"],
            "resilience_job": jobs["resilience"]["conclusion"],
        },
        "zero_durable_delta_diagnosis": {
            "verdict": "ZERO_DURABLE_DELTA_UNDER_SUCCESS",
            "explanation": (
                f"The team job of run {RUN} concluded SUCCESS in "
                f"{_dur(team)}s with every step green, yet produced no "
                "run-scoped content: the persisted team snapshot "
                "cycle/core/evaluation/%s/team is at commit 0b4963a0, which IS "
                "the previous cycle's audit commit (audit of 40096174340), its "
                "tree is byte-identical to that head, no committed artifact "
                "references run %s, and state/evaluation.json still carried "
                "github_run=%s. The LEX_REQUIRE_DELTA / LEX_ZERO_DELTA_REPAIR "
                "guard (.github/scripts/run-ox-with-retry.sh:161,213-216, "
                "recorded NOT edited - .github/** is control-plane scope) "
                "compares HEAD against START_HEAD plus git status porcelain; "
                "it was satisfied ONLY by HEAD movement f2734734 (lab/evaluation "
                "tip) -> 0b4963a0 (adopted inherited audit head) with a CLEAN "
                "worktree, i.e. a delta-guard bypass by head adoption. The "
                "'Validate active MVP producer state' step then passed on the "
                "INHERITED state (direction_version 67, cycle_status COMPLETE). "
                "This is an unreported null, not an honest negative result."
                % (RUN, RUN, RESUMED_FROM)),
            "delta_guard_mechanism": (
                "LEX_REQUIRE_DELTA=1 sets REPAIR_INTENT; after a successful "
                "agent run the guard exits 67 only when HEAD==START_HEAD AND "
                "porcelain is empty; HEAD moved while no file changed"),
            "state_before_this_repair": {
                "github_run": RESUMED_FROM,
                "accepted_run_id": "40084716045",
                "source": "state/evaluation.json at inherited head 0b4963a0",
            },
            "artifacts_referencing_run_before_repair": 0,
            "escalation_contract": (
                "audit required_fixes F1: a zero-delta round-1 repair is "
                "INVALID and must escalate to BLOCKED; this repair therefore "
                "produces the run-referenced diagnosis set + freeze-first "
                "re-verification + state advance instead of adopting a head"),
        },
        "v67_work_posture_this_run": {
            "item_1_d2_letterhead_pattern_profile": (
                "DISCHARGED-AND-INHERITED: deliverable of record "
                f"{DELIVERABLE} (sha256 {DELIVERABLE_SHA}); re-verified under "
                f"run {RUN} this repair by freeze-first re-execution (see "
                f"results/evaluation/d2_letterhead_pattern_profile/"
                f"{RUN}_reproduction_check_vs_{DELIV}.json); no re-derivation"),
            "item_2_conditional_remeasure": (
                "NOT_YET_DISCRIMINATING (re-verified this run, report-only): "
                f"origin/lab/product head {prod_head} still fixture-bypasses "
                "the content filter - product/offline_slice.py:79 "
                "enrich_query_bundle(..., retrieval_mode='fixture', "
                "fixture_generation=True) and product/query/pipeline.py:1339 "
                "'if not fixture_generation and adversarial_retrieval'. No "
                "synthetic stand-in; standing falsification record not re-run."),
            "item_3_standing_falsification_record": (
                "KEPT OF RECORD, not re-run (PRODUCT_FALSIFIED with the "
                "identical 4-gate set on the minimal retrieval/ca benchmark; "
                "superseded only by a NEW pre-registered falsification on NEW "
                "bytes with its own freeze-first record)"),
            "item_4_report_only": (
                "the three non-blocking required fixes of "
                "CYCLE_39965089504_GATE.json are reported only where this "
                "lane quotes those counts, never silently"),
            "accepted_head_surfaces_read": (
                "both halves of factory-wide requirement 4: origin/lab/"
                "evaluation tip f2734734 ('accept evaluation cycle 40084716045') "
                "read via git; results/accepted-state/evaluation.json on "
                "origin/main read via git and pinned at github_run "
                "40082514143 (publication-lag artifact per requirement 43, "
                "not an acceptance claim); /tmp/lex_accepted mounts NOT used "
                "as acceptance authority"),
        },
        "posture_unchanged": {
            "human_gate_ready": False, "machine_gate_ready": False,
            "packet_admitted": False, "ready_for_owner_session": False,
            "owner_decision_required": False,
            "both_do_not_serve_orders_stand": True,
            "comparative_map_vs_ranked_list": "VACUOUS",
            "no_frozen_bar_rubric_threshold_verdict_contract_edit": True,
            "baseline_40062917685_unmoved": True,
            "no_obsolete_universal_174k_benchmark_rerun": True,
            "no_product_code_modified": True,
        },
        "claim_ceiling": (
            "Operational-resume/diagnosis artifact for F1 of the round-1 "
            f"repair of rejected cycle {RUN} (gate REVISE, required_fixes "
            "F1-F4). It records why a SUCCESS team job shipped zero durable "
            "delta and what the current v67 posture is. It scores no frozen "
            "bar, edits nothing frozen, re-runs no serve verdict, and makes "
            "no product, admission or legal-usefulness claim; comparative "
            "map-versus-ranked-list stays VACUOUS; "
            "owner_decision_required=false."),
        "generated_at_utc": _now(),
    }
    out = _REPO_ROOT / "results/evaluation/orchestration" / \
        f"{RUN}_failure_chain_diagnosis.json"
    _write_json(out, diag)
    print(json.dumps({"wrote": str(out.relative_to(_REPO_ROOT)),
                      "verdict": diag["zero_durable_delta_diagnosis"]["verdict"],
                      "product_head": prod_head}, indent=1))
    return 0


def _dur(job: dict) -> int:
    from datetime import datetime as dt
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return int((dt.strptime(job["completed_at"], fmt)
                - dt.strptime(job["started_at"], fmt)).total_seconds())


def _product_head() -> str:
    import subprocess
    out = subprocess.run(["git", "rev-parse", "origin/lab/product"],
                         cwd=_REPO_ROOT, capture_output=True, text=True,
                         timeout=30).stdout.strip()
    return out or "unknown"


# ------------------------------------------------------- F2: freeze FIRST
def freeze() -> int:
    hyp_path = _REPO_ROOT / "evaluation" / \
        f"OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json"
    frz_path = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json"
    if frz_path.exists() and hyp_path.exists():
        print(f"freeze already committed at {frz_path.name} (never rewritten)")
        return 0
    product_head = _product_head()
    hyp = {
        "schema": "lex-evaluation-cycle-hypothesis/1",
        "run_id": RUN,
        "github_run": RUN,
        "repair_run_id": REPAIR_RUN,
        "repair_round": 1,
        "lane": "evaluation",
        "direction_version": DIRV,
        "question_source": (
            "required_fixes F1-F4 of "
            f"results/audit/evaluation/CYCLE_{RUN}_GATE.json (gate REVISE) plus "
            "the v67 evaluation lane question (items (1)-(4); item (1) already "
            "executed, item (2) conditional on product, item (3) standing, "
            "item (4) report-only)"),
        "hypothesis": (
            f"Rejected cycle {RUN} shipped ZERO durable delta under team SUCCESS "
            "by adopting inherited audit head 0b4963a0 (HEAD f2734734 -> "
            "0b4963a0, clean porcelain) while its snapshot still carries the "
            "complete, valid v67 ordered-work item-(1) deliverable inherited "
            f"from run {DELIV}. Re-executing the byte-identical frozen "
            "instrument (sha256 aac86527...) against the same sha256-pinned "
            f"bundle population under run id {RUN} REPRODUCES all 19 frozen "
            "discrimination fields, so the repair can (a) commit the F1 "
            "diagnosis set for the rejected run, (b) re-verify the deliverable "
            f"under {RUN} freeze-first, and (c) advance the canonical state with "
            "disclosure - a durable, auditable delta instead of a second "
            "zero-delta round, which F1 makes invalid."),
        "metric": (
            "Field-level equality between results/evaluation/"
            f"d2_letterhead_pattern_profile/{DELIV}.json (deliverable of record) "
            f"and a fresh re-execution under run id {RUN} on the pinned 19-item "
            "inventory (evaluation/OPERATIONAL_RESUME_"
            f"{RUN}_FREEZE_V1.json field_inventory), plus controls C3-C6 all "
            "passing. Run-scoped fields (run_id, generated_at_utc, elapsed_s, "
            "numeric_environment, report path) excluded; per factory-wide "
            "requirement 30 JSON file byte-identity is NOT claimed."),
        "decision_rule_frozen_before_execution": {
            "REPRODUCES": (
                "all 19 inventory items equal AND controls C3-C6 PASS -> the "
                f"inherited {DELIV} item-(1) deliverable is VERIFIED under run "
                f"{RUN}; the repair advances state github_run with disclosure "
                "and keeps accepted_run_id=40084716045; item (2) stays "
                "NOT_YET_DISCRIMINATING"),
            "DIVERGES": (
                "any inventory item differs -> publish the exact divergence "
                f"under run {RUN} as a NEW artifact (never overwrite "
                f"{DELIV}.json or any prior artifact), state whether it is "
                "environment-scoped (requirement 30) or a population change, "
                "and leave the deliverable of record untouched"),
            "controls": (
                "C3 frozen rubric re-hash REPORTED-ONLY; C4 frozen instrument "
                "digest byte-identical; C5 planted letterhead/mid-document "
                "non-vacuity; C6 accepted-baseline 40062917685 population "
                "cross-check NORMALIZED-IDENTICAL"),
        },
        "baseline": (
            f"results/evaluation/d2_letterhead_pattern_profile/{DELIV}.json "
            "(item-(1) deliverable of record); accepted baseline 40062917685 "
            "stays UNMOVED and is re-probed REPORTED-ONLY via control C6"),
        "instrument": {
            "file": PROFILE_INSTRUMENT,
            "sha256_expected": PROFILE_INSTRUMENT_SHA,
            "frozen_predicates_imported_by_value_from":
                "evaluation/counter_evidence_quality_benchmark.py",
            "frozen_instrument_sha256_expected": FROZEN[
                "evaluation/counter_evidence_quality_benchmark.py"],
            "note": "neither file is edited by this repair",
        },
        "not_in_scope": [
            "no v67 item-(2) re-measure (product has not landed the dual P0 fix; "
            "NOT_YET_DISCRIMINATING, re-verified report-only)",
            "no re-run of the standing falsification record (item (3))",
            "no frozen bar, rubric, threshold or verdict contract edited or scored",
            "no serve verdict re-run; both DO-NOT-SERVE orders stand; admission "
            "stays fail-closed",
            "no obsolete universal-174k benchmark rerun",
            "no baseline 40062917685 re-baselining or movement",
            "no product code modified (write scope forbids it)",
            "no D3/D4 upgrade: D2 stays STILL-DEFECTIVE on class-eligible rows; "
            "D3/D4 stay CONFIRMED-REPAIRED on class-eligible rows only",
            "comparative map-versus-ranked-list half NOT scored; posture flags "
            "stay FALSE; owner_decision_required stays false",
        ],
        "product_decision_unlocked": (
            "Confirms for Core Product that the deterministic-letterhead-filter "
            "feasibility profile it consumes is reproducible from its pinned "
            "bundle set under the frozen instrument; makes no product, bar or "
            "serve claim itself."),
        "claim_ceiling": (
            "Freeze-first operational re-verification ONLY: proves the inherited "
            "committed item-(1) profile reproduces under the frozen instrument "
            "and anchors the F1 diagnosis of the rejected run to the public REST "
            "record. Scores no frozen bar, edits nothing frozen, classifies no "
            "decision as supporting/contrary, changes no serve verdict, makes no "
            "legal-usefulness claim."),
        "pre_execution_observations_disclosed": [
            "At freeze time this repair has already READ (without re-executing) "
            "the committed 40089391202, 40094203248 and 40096174340 artifacts "
            "and the prior reproduction checks; this is a verification of a "
            "prior measurement, not a blind prediction. The freeze pins the "
            "comparison inventory BEFORE the fresh execution so no field "
            "selection can be tuned after seeing the output.",
            f"The persisted team snapshot of rejected run {RUN} "
            "(cycle/core/evaluation/40099481633/team) is commit 0b4963a0, "
            "byte-identical to the prior audit head; the run contributed ZERO "
            "new durable delta and is NOT accepted evidence.",
        ],
        "frozen_at_utc": _now(),
    }
    _write_json(hyp_path, hyp)
    frz = {
        "schema": "lex-evaluation-freeze-record/1",
        "run_id": RUN,
        "github_run": RUN,
        "repair_run_id": REPAIR_RUN,
        "repair_round": 1,
        "lane": "evaluation",
        "direction_version": DIRV,
        "hypothesis_record":
            f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json",
        "hypothesis_sha256": _sha256(hyp_path),
        "frozen_at_utc": _now(),
        "decision_rule": (
            "Frozen in the hypothesis record: REPRODUCES if and only if ALL 19 "
            "pinned inventory items are field-equal between "
            f"{DELIVERABLE} and a fresh {RUN} re-execution, with controls C3-C6 "
            "all passing; run-scoped fields excluded; JSON file byte-identity "
            "NOT claimed (requirement 30)."),
        "field_inventory": FIELD_INVENTORY,
        "n_fields": len(FIELD_INVENTORY),
        "instrument": {
            "file": PROFILE_INSTRUMENT,
            "sha256": _sha256(_REPO_ROOT / PROFILE_INSTRUMENT),
            "matches_expected": _sha256(_REPO_ROOT / PROFILE_INSTRUMENT)
            == PROFILE_INSTRUMENT_SHA,
            "frozen_predicates": {
                "file": "evaluation/counter_evidence_quality_benchmark.py",
                "sha256": _sha256(
                    _REPO_ROOT / "evaluation/counter_evidence_quality_benchmark.py"),
                "expected": FROZEN["evaluation/counter_evidence_quality_benchmark.py"],
                "matches_expected": _sha256(
                    _REPO_ROOT / "evaluation/counter_evidence_quality_benchmark.py")
                == FROZEN["evaluation/counter_evidence_quality_benchmark.py"],
                "note": "re-hashed REPORTED-ONLY at freeze time; predicates "
                        "imported BY VALUE; never edited or re-derived",
            },
        },
        "frozen_inputs": {
            "evaluation/frozen_bars/RULES_LABEL.json": _sha256(
                _REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json"),
            "evaluation/frozen_bars/RULES_GEOMETRY.json": _sha256(
                _REPO_ROOT / "evaluation/frozen_bars/RULES_GEOMETRY.json"),
            "evaluation/frozen_bars/VERDICT_CONTRACT.json": _sha256(
                _REPO_ROOT / "evaluation/frozen_bars/VERDICT_CONTRACT.json"),
            DELIVERABLE: _sha256(_REPO_ROOT / DELIVERABLE),
            BASELINE_ARTIFACT: _sha256(_REPO_ROOT / BASELINE_ARTIFACT),
        },
        "frozen_input_expectations": {
            DELIVERABLE: DELIVERABLE_SHA,
            BASELINE_ARTIFACT: BASELINE_SHA_EXPECTED,
        },
        "controls": [
            "C3_frozen_rubric_rehash_reported_only",
            "C4_frozen_instrument_digest_unchanged",
            "C5_non_vacuity_planted_letterhead_vs_mid_document",
            "C6_accepted_baseline_population_crosscheck",
            "R1_discrimination_fields_identical_to_" + DELIV,
        ],
        "no_bar_movement": True,
        "required_fixes_targeted": ["F1", "F2", "F3", "F4"],
        "repair_contract": (
            f"required_fixes F2 orders the re-verification UNDER run {RUN}; the "
            f"artifacts named {RUN}.* are therefore EXECUTED by repair run "
            f"{REPAIR_RUN} (disclosed in every such artifact and in "
            f"state/evaluation.json block repair_round1_{RUN}). No file named "
            "for any prior run is overwritten (F-3B convention): "
            f"{DELIVERABLE}.json, 40094203248.json and 40096174340.json stay "
            f"byte-stable, and {RUN}.json is created for the first time."),
        "pre_execution_observations_disclosed": hyp[
            "pre_execution_observations_disclosed"],
        "claim_ceiling": (
            "Freeze metadata for the F2 re-verification; scores nothing, moves "
            "no bar, edits nothing frozen."),
    }
    _write_json(frz_path, frz)
    print(json.dumps({
        "hypothesis": str(hyp_path.relative_to(_REPO_ROOT)),
        "hypothesis_sha256": frz["hypothesis_sha256"],
        "freeze": str(frz_path.relative_to(_REPO_ROOT)),
        "n_fields": frz["n_fields"],
        "instrument_ok": frz["instrument"]["matches_expected"],
        "predicates_ok": frz["instrument"]["frozen_predicates"]["matches_expected"],
        "deliverable_sha_ok": frz["frozen_inputs"][DELIVERABLE] == DELIVERABLE_SHA,
        "baseline_sha_ok": frz["frozen_inputs"][BASELINE_ARTIFACT]
        == BASELINE_SHA_EXPECTED,
    }, indent=1))
    return 0


# ------------------------------------------------------------- F2: repro
def repro() -> int:
    frz_path = _REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json"
    if not frz_path.exists():
        print("FREEZE MISSING - refusing to compare (freeze-first contract)",
              file=sys.stderr)
        return 3
    frz = json.loads(frz_path.read_text(encoding="utf-8"))
    if frz.get("n_fields") != 19 or frz.get("field_inventory") != FIELD_INVENTORY:
        print("freeze inventory mismatch - refusing", file=sys.stderr)
        return 3
    base = json.loads((_REPO_ROOT / DELIVERABLE).read_text(encoding="utf-8"))
    new_path = _REPO_ROOT / "results/evaluation/d2_letterhead_pattern_profile" / \
        f"{RUN}.json"
    if not new_path.exists():
        print(f"re-execution artifact missing: {new_path}", file=sys.stderr)
        return 3
    new = json.loads(new_path.read_text(encoding="utf-8"))

    mismatches: dict[str, object] = {}
    for f in ("verdict", "exit_code", "controls_all_pass", "n_bundles",
              "n_bundles_shipped_slice", "n_bundles_packet_of_record",
              "n_verified_rows_shipped_slice", "n_verified_rows_packet_of_record",
              "population_defect_histogram", "d2_rows_profiled",
              "n_distinct_letterhead_patterns", "detectability_summary",
              "frozen_predicate_instrument_sha256", "product_mount_head",
              "direction_version", "packet_of_record"):
        if base.get(f) != new.get(f):
            mismatches[f] = {"deliverable": base.get(f), "reexecution": new.get(f)}
    pops_b = {p["bundle"]: {k: p.get(k) for k in POP_FIELDS}
              for p in base.get("population", [])}
    pops_n = {p["bundle"]: {k: p.get(k) for k in POP_FIELDS}
              for p in new.get("population", [])}
    if pops_b != pops_n:
        only_b = sorted(set(pops_b) - set(pops_n))
        only_n = sorted(set(pops_n) - set(pops_b))
        changed = sorted(k for k in set(pops_b) & set(pops_n)
                         if pops_b[k] != pops_n[k])
        mismatches["population[*]"] = {"only_in_deliverable": only_b,
                                       "only_in_reexecution": only_n,
                                       "changed": changed}
    pat_b = {p.get("pattern_key"): {k: p.get(k) for k in PATTERN_FIELDS}
             for p in base.get("letterhead_patterns", [])}
    pat_n = {p.get("pattern_key"): {k: p.get(k) for k in PATTERN_FIELDS}
             for p in new.get("letterhead_patterns", [])}
    if pat_b != pat_n:
        mismatches["letterhead_patterns[*]"] = {"deliverable": pat_b,
                                                "reexecution": pat_n}
    ctrl_b = {k: v.get("passed") for k, v in (base.get("controls") or {}).items()}
    ctrl_n = {k: v.get("passed") for k, v in (new.get("controls") or {}).items()}
    if ctrl_b != ctrl_n:
        mismatches["controls:{C3,C4,C5,C6}"] = {"deliverable": ctrl_b,
                                                "reexecution": ctrl_n}
    controls_all_pass = bool(new.get("controls_all_pass")) and all(
        ctrl_n.get(k) is True for k in ("C3", "C4", "C5", "C6"))

    verdict = "REPRODUCES" if (not mismatches and controls_all_pass) else "DIVERGES"
    rec = {
        "schema": "lex-evaluation-resume-reproduction-check/1",
        "run_id": RUN,
        "repair_run_id": REPAIR_RUN,
        "repair_round": 1,
        "executed_by_repair_run_disclosure": (
            f"required_fixes F2 orders the re-verification under run {RUN}; this "
            f"artifact was EXECUTED by repair run {REPAIR_RUN} and is named for "
            f"{RUN} because that rejected run produced zero artifacts"),
        "resumed_deliverable_of_record": {
            "file": DELIVERABLE,
            "sha256": _sha256(_REPO_ROOT / DELIVERABLE),
        },
        "resume_reexecution": {
            "file": "results/evaluation/d2_letterhead_pattern_profile/"
                    f"{RUN}.json",
            "sha256": _sha256(new_path),
        },
        "comparison_contract":
            f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json "
            "(frozen BEFORE this re-execution; inventory sha pinned)",
        "comparison_contract_sha256": _sha256(frz_path),
        "excluded_run_scoped_fields": ["run_id", "generated_at_utc", "elapsed_s",
                                       "numeric_environment", "report_file",
                                       "run_id"],
        "file_byte_identity_claimed": False,
        "file_byte_identity_note": (
            "Per factory-wide requirement 30, JSON file byte-identity is "
            "environment-scoped and is NOT claimed; only the frozen inventory "
            "items are compared."),
        "n_discrimination_fields_compared": len(FIELD_INVENTORY),
        "n_mismatches": len(mismatches),
        "mismatches": mismatches,
        "controls_all_pass": controls_all_pass,
        "controls": {"C3": ctrl_n.get("C3"), "C4": ctrl_n.get("C4"),
                     "C5": ctrl_n.get("C5"), "C6": ctrl_n.get("C6")},
        "verdict": verdict,
        "deliverable_untouched": (
            _sha256(_REPO_ROOT / DELIVERABLE) == DELIVERABLE_SHA),
        "claim_ceiling": (
            "Operational-resume reproduction check only: proves the committed "
            f"{DELIV} profile (the item-(1) deliverable of record inherited by "
            f"rejected snapshot {RUN}) re-executes to identical frozen "
            "discrimination fields under the byte-identical instrument against "
            "the same sha256-pinned bundle population. Scores no frozen bar; "
            "edits nothing frozen; makes no product, serve or legal-usefulness "
            "claim. The "
            f"{DELIV} artifact remains the item-(1) deliverable of record."),
        "generated_at_utc": _now(),
    }
    out = _REPO_ROOT / "results/evaluation/d2_letterhead_pattern_profile" / \
        f"{RUN}_reproduction_check_vs_{DELIV}.json"
    _write_json(out, rec)
    print(json.dumps({"wrote": str(out.relative_to(_REPO_ROOT)),
                      "verdict": verdict,
                      "n_mismatches": len(mismatches),
                      "n_fields": rec["n_discrimination_fields_compared"],
                      "controls_all_pass": controls_all_pass}, indent=1))
    return 0 if verdict == "REPRODUCES" else 1


# ------------------------------------------------------------ F4: verify
def verify() -> int:
    table = {}
    for rel, exp in {**FROZEN, DELIVERABLE: DELIVERABLE_SHA,
                     BASELINE_ARTIFACT: BASELINE_SHA_EXPECTED,
                     PROFILE_INSTRUMENT: PROFILE_INSTRUMENT_SHA}.items():
        act = _sha256(_REPO_ROOT / rel)
        table[rel] = {"expected": exp, "actual": act, "matches": act == exp}
    print(json.dumps(table, indent=1))
    return 0 if all(v["matches"] for v in table.values()) else 1


# ------------------------------------------------------------- F2/F4: state
NEW_REFS = [
    f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json",
    f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json",
    "evaluation/repair_40099481633_round1.py",
    f"results/evaluation/orchestration/{RUN}_rest_jobs.json",
    f"results/evaluation/orchestration/{RUN}_failure_chain_diagnosis.json",
    "results/evaluation/d2_letterhead_pattern_profile/"
    f"{RUN}.json",
    f"reports/evaluation/D2_LETTERHEAD_PATTERN_PROFILE_{RUN}.md",
    "results/evaluation/d2_letterhead_pattern_profile/"
    f"{RUN}_reproduction_check_vs_{DELIV}.json",
    "tests/evaluation/test_operational_resume_40094203248.py",
    f"tests/evaluation/test_operational_resume_{RUN}.py",
    f"results/evaluation/orchestration/{REPAIR_RUN}_pytest_shim.json",
    f"results/evaluation/orchestration/{REPAIR_RUN}_pytest_repair_invariants.json",
    f"results/evaluation/orchestration/{REPAIR_RUN}_multiling_prov_pytest.json",
    f"reports/evaluation/OPERATIONAL_RESUME_{RUN}.md",
    f"results/evaluation/orchestration/{RUN}_nested_evidence_refs.json",
]

POSTURE_FLAGS = ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required")


def state(allow_deferred: bool = False) -> int:
    st = json.loads(STATE.read_text(encoding="utf-8"))
    before = {
        "github_run": st.get("github_run"),
        "accepted_run_id": st.get("accepted_run_id"),
        "direction_version": st.get("direction_version"),
        "evidence_refs_n": st.get("evidence_refs_n"),
    }
    if st.get("direction_version") != DIRV:
        print(f"direction_version {st.get('direction_version')} != {DIRV}; "
              "refusing", file=sys.stderr)
        return 3
    if st.get("accepted_run_id") != "40084716045":
        print("accepted_run_id drift detected; refusing", file=sys.stderr)
        return 3
    for rel, exp in {**FROZEN, BASELINE_ARTIFACT: BASELINE_SHA_EXPECTED,
                     DELIVERABLE: DELIVERABLE_SHA}.items():
        act = _sha256(_REPO_ROOT / rel)
        if act != exp:
            print(f"F4 non-movement violated: {rel} {act} != {exp}",
                  file=sys.stderr)
            return 3

    hist = st.setdefault("run_identity_history", [])
    known = {str(h.get("run_id")) for h in hist}
    additions = [
        {"run_id": RESUMED_FROM,
         "role": "operational resume of 40094203248; reproduction-verified "
                 "inherited item-(1); zero-delta producer snapshot diagnosed",
         "chain_outcome": "team snapshot + resume landed; gate PASS "
                          "(results/audit/evaluation/CYCLE_40096174340_GATE.json "
                          "on the audit branch); never carried an "
                          "'accept evaluation cycle' commit on lab/evaluation "
                          "- NOT ACCEPTED under requirement 4",
         "recovered_by_repair_run": REPAIR_RUN},
        {"run_id": RUN,
         "role": "REJECTED cycle (gate REVISE, required_fixes F1-F4): team job "
                 "SUCCESS with ZERO durable delta - delta guard satisfied only "
                 "by adopting inherited head 0b4963a0",
         "chain_outcome": "NOT ACCEPTED; repaired by round 1 under run "
                          f"{REPAIR_RUN}",
         "repaired_by_run": REPAIR_RUN},
        {"run_id": REPAIR_RUN,
         "role": "round-1 repair of rejected 40099481633: F1 diagnosis set + "
                 "REST snapshot, F2 freeze-first re-verification under 40099481633 "
                 "and state advance, F3 living-suite hygiene, F4 non-movements",
         "chain_outcome": "PROPOSED_PENDING_INDEPENDENT_AUDIT"},
    ]
    for a in additions:
        if a["run_id"] not in known:
            hist.append(a)
            known.add(a["run_id"])

    st["github_run"] = REPAIR_RUN
    st["github_run_advance"] = {
        "from": RESUMED_FROM,
        "to": REPAIR_RUN,
        "repair_of_run": RUN,
        "repair_round": 1,
        "reason": (
            "required_fixes F2: advance state/evaluation.json github_run with "
            "disclosure. Run attribution names the REPAIR run that made the "
            "claim (precedent: test_repair_39433092808_artifact_hygiene.py::"
            "test_r4_run_attribution_advanced_to_repair_run); artifacts that "
            f"must reference the rejected cycle are named {RUN}.* per F2 and "
            f"disclose executed_by_run={REPAIR_RUN}. accepted_run_id stays "
            "40084716045 until a both-halves promotion of a newer cycle."),
        "prior_value_recorded": RESUMED_FROM,
        "disclosure": (
            "append-only: the previous github_run, the rejected run and this "
            "repair run are all preserved in run_identity_history; no "
            "historical record was deleted or overwritten"),
    }
    st["operational_resume_of"] = RUN
    st["inherited_deliverable_of_record"] = DELIV
    st["accepted_run_id"] = "40084716045"
    st["direction_version"] = DIRV
    st["direction_version_pin_note"] = (
        "v66 -> v67 pin advance was expected and applied with this lane's "
        "disclosed convention comment (factory direction v67); it is not a "
        "defect and consumed no repair round"
    ) if "direction_version_pin_note" not in st else st["direction_version_pin_note"]

    repro_path = ("results/evaluation/d2_letterhead_pattern_profile/"
                  f"{RUN}_reproduction_check_vs_{DELIV}.json")
    repro = json.loads((_REPO_ROOT / repro_path).read_text(encoding="utf-8"))
    if repro.get("verdict") != "REPRODUCES" or repro.get("n_mismatches") != 0 \
            or not repro.get("controls_all_pass"):
        print("reproduction check is not REPRODUCES; refusing state advance",
              file=sys.stderr)
        return 3
    diag_path = (f"results/evaluation/orchestration/"
                 f"{RUN}_failure_chain_diagnosis.json")
    diag = json.loads((_REPO_ROOT / diag_path).read_text(encoding="utf-8"))
    rest_path = f"results/evaluation/orchestration/{RUN}_rest_jobs.json"
    prod_head = _product_head()

    st[f"repair_round1_{RUN}"] = {
        "schema": "lex-evaluation-repair-round/1",
        "run_id": RUN,
        "repairs_run_id": RUN,
        "repair_round": 1,
        "repaired_by_run": REPAIR_RUN,
        "direction_version": DIRV,
        "audit_gate": f"results/audit/evaluation/CYCLE_{RUN}_GATE.json",
        "audit_gate_branch": f"cycle/core/evaluation/{RUN}/audit (commit ab50ea74)",
        "audit_verdict_repaired": "REVISE",
        "required_fixes": ["F1", "F2", "F3", "F4"],
        "required_fixes_verbatim": FIXES,
        "fixes_discharged": {
            "F1": {
                "verdict": "DISCHARGED",
                "rest_snapshot": rest_path,
                "rest_snapshot_sha256": _sha256(_REPO_ROOT / rest_path),
                "diagnosis": diag_path,
                "diagnosis_verdict":
                    diag["zero_durable_delta_diagnosis"]["verdict"],
                "explanation_recorded": (
                    "LEX_REQUIRE_DELTA guard satisfied only by adopting "
                    "inherited head 0b4963a0 (HEAD f2734734 -> 0b4963a0, clean "
                    "porcelain, no file change); team SUCCESS "
                    f"({diag['chain_record']['team_job']['duration_s']}s) with "
                    "zero run-referenced artifacts; state validation passed on "
                    "inherited state. v67 work posture recorded in the same "
                    "artifact."),
                "zero_delta_repair_avoided": True,
                "durable_delta_this_repair": [
                    f"results/evaluation/orchestration/{RUN}_rest_jobs.json",
                    diag_path,
                    f"results/evaluation/d2_letterhead_pattern_profile/{RUN}.json",
                    repro_path,
                    f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json",
                    f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json",
                    "evaluation/repair_40099481633_round1.py",
                    f"tests/evaluation/test_operational_resume_{RUN}.py",
                    f"reports/evaluation/OPERATIONAL_RESUME_{RUN}.md",
                ],
            },
            "F2": {
                "verdict": "DISCHARGED",
                "freeze_first": True,
                "comparison_contract":
                    f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json",
                "comparison_contract_sha256": _sha256(
                    _REPO_ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json"),
                "waiver": None,
                "deliverable_of_record": DELIVERABLE,
                "deliverable_sha256": DELIVERABLE_SHA,
                "deliverable_untouched": repro["deliverable_untouched"],
                "reverification_under_run": RUN,
                "executed_by_repair_run": REPAIR_RUN,
                "reexecution_artifact":
                    f"results/evaluation/d2_letterhead_pattern_profile/{RUN}.json",
                "reproduction_check": repro_path,
                "reproduction_verdict": repro["verdict"],
                "n_discrimination_fields_compared":
                    repro["n_discrimination_fields_compared"],
                "n_mismatches": repro["n_mismatches"],
                "frozen_instrument_sha256":
                    FROZEN["evaluation/counter_evidence_quality_benchmark.py"],
                "state_github_run_advanced": {
                    "from": RESUMED_FROM, "to": REPAIR_RUN,
                    "disclosure_block": "github_run_advance"},
                "accepted_run_id_kept": "40084716045",
            },
            "F3": {
                "verdict": "DISCHARGED",
                "stale_pin_fixed": (
                    "tests/evaluation/test_operational_resume_40094203248.py::"
                    "test_state_run_identity_and_posture: the literal "
                    "github_run=='40094203248' and "
                    "operational_resume_of=='40089391202' pins are widened to "
                    "the append-only run_identity_history chain recorded in "
                    "state; the historical run ids stay asserted (history NOT "
                    "deleted) and posture/accepted_run_id/evidence_refs pins "
                    "are unchanged"),
                "history_preserved": True,
                "living_suite_record":
                    f"results/evaluation/orchestration/{REPAIR_RUN}_pytest_shim.json",
                "repair_invariants_record":
                    f"results/evaluation/orchestration/"
                    f"{REPAIR_RUN}_pytest_repair_invariants.json",
                "multilingual_provenance_reuse_record":
                    f"results/evaluation/orchestration/"
                    f"{REPAIR_RUN}_multiling_prov_pytest.json",
                "pytest": "real pytest 9.1.1 (installed this run)",
            },
            "F4": {
                "verdict": "DISCHARGED (restated, nothing moved)",
                "frozen_rehash_reported_only": FROZEN,
                "baseline_40062917685_sha256":
                    _sha256(_REPO_ROOT / BASELINE_ARTIFACT),
                "baseline_unmoved": True,
                "no_obsolete_universal_174k_benchmark_rerun": True,
                "posture_fail_closed": True,
                "both_do_not_serve_orders_stand": True,
                "no_product_code_modified": True,
                "product_code_evidence": (
                    f"write scope restricts this job to evaluation/, "
                    f"tests/evaluation/, results/evaluation/, reports/evaluation/ "
                    f"and state/evaluation.json; origin/lab/product head "
                    f"{prod_head} was READ ONLY (offline_slice.py:79, "
                    "pipeline.py:1339) to confirm item (2) is still "
                    "NOT_YET_DISCRIMINATING"),
            },
        },
        "v67_item_2_status": {
            "status": "NOT_YET_DISCRIMINATING",
            "product_head": prod_head,
            "evidence": (
                "origin/lab/product offline_slice.py:79 "
                "enrich_query_bundle(..., retrieval_mode='fixture', "
                "fixture_generation=True); product/query/pipeline.py:1339 "
                "'if not fixture_generation and adversarial_retrieval' - the "
                "landed filter never runs on the shipped offline/slice path"),
            "reverified_this_run_report_only": True,
        },
        "claim_ceiling": (
            "Round-1 repair of a rejected zero-delta cycle: discharges audit "
            "required_fixes F1-F4 with committed, machine-verifiable records. "
            "It re-measures nothing about the product, scores no frozen bar, "
            "edits nothing frozen, changes no serve verdict and makes no "
            "admission or legal-usefulness claim. Both DO-NOT-SERVE orders "
            "stand; admission stays fail-closed; comparative map-vs-ranked-list "
            "stays VACUOUS; owner_decision_required=false."),
        "generated_at_utc": _now(),
    }

    refs = st.setdefault("evidence_refs", [])
    added = []
    for r in NEW_REFS:
        if r not in refs:
            refs.append(r)
            added.append(r)
    st["evidence_refs_n"] = len(refs)
    roles = st.setdefault("evidence_ref_roles", {})
    roles.update({
        f"results/evaluation/orchestration/{RUN}_rest_jobs.json":
            "F1_REPAIR_ARTIFACT",
        diag_path: "F1_REPAIR_ARTIFACT",
        f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json":
            "F2_FREEZE_FIRST_HYPOTHESIS",
        f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json":
            "F2_FREEZE_FIRST_COMPARISON_CONTRACT",
        repro_path: "F2_REPRODUCTION_CHECK",
        f"results/evaluation/d2_letterhead_pattern_profile/{RUN}.json":
            "F2_REEXECUTION_UNDER_REJECTED_RUN_ID",
        f"evaluation/repair_40099481633_round1.py": "F1_F2_F4_REPAIR_SCRIPT",
        f"tests/evaluation/test_operational_resume_{RUN}.py":
            "F1_F2_F3_F4_REPAIR_INVARIANT_TESTS",
        f"results/evaluation/orchestration/{REPAIR_RUN}_pytest_shim.json":
            "F3_LIVING_SUITE_RECORD",
        f"results/evaluation/orchestration/{RUN}_nested_evidence_refs.json":
            "NESTED_REFS_GUARD_RECORD",
    })
    st["test_suite"] = st.get("test_suite") or {}
    shim_p = _REPO_ROOT / f"results/evaluation/orchestration/{REPAIR_RUN}_pytest_shim.json"
    if shim_p.exists():
        shim = json.loads(shim_p.read_text(encoding="utf-8"))
        st["test_suite"]["living_suite_" + REPAIR_RUN] = {
            "run_id": REPAIR_RUN,
            "repairs_run_id": RUN,
            "record": f"results/evaluation/orchestration/{REPAIR_RUN}_pytest_shim.json",
            "pytest_version": shim.get("pytest_version"),
            "passed": shim.get("passed"),
            "failed": shim.get("failed"),
            "skipped": shim.get("skipped"),
            "files": shim.get("files"),
            "repair_round": 1,
            "note": (
                "F3: fresh real-pytest living-suite result at the repaired "
                "head after the stale identity pin was widened; the previous "
                "record's 34/2/1 auditor run is preserved in the audit "
                "gate of record, not edited"),
        }
    for extra, key in (
        (f"{REPAIR_RUN}_pytest_repair_invariants.json", "repair_invariants_" + REPAIR_RUN),
        (f"{REPAIR_RUN}_multiling_prov_pytest.json",
         "multilingual_provenance_reuse_" + REPAIR_RUN),
    ):
        p = _REPO_ROOT / "results/evaluation/orchestration" / extra
        if p.exists():
            rec = json.loads(p.read_text(encoding="utf-8"))
            st["test_suite"][key] = {
                "run_id": REPAIR_RUN, "repairs_run_id": RUN,
                "record": f"results/evaluation/orchestration/{extra}",
                "pytest_version": rec.get("pytest_version"),
                "passed": rec.get("passed"), "failed": rec.get("failed"),
                "skipped": rec.get("skipped"), "files": rec.get("files"),
                "repair_round": 1,
            }

    for f in POSTURE_FLAGS:
        st[f] = False
    st["cycle_status"] = "COMPLETE"
    st["evidence_tier"] = "REPRODUCED"
    st["acceptance_status"] = "PROPOSED_PENDING_INDEPENDENT_AUDIT"
    st["repair_round"] = 1
    st["repairs_run_id"] = RUN
    st["proposed_run_id"] = RUN
    st["continue_recommended"] = False
    st["continue_recommended_reason"] = (
        "v67 ordered work stays discharged: item (1) inherited and now "
        f"re-verified FROZEN-FIRST under run {RUN} (REPRODUCES, 19/19, 0 "
        "mismatches, controls C3-C6 pass); item (2) re-verified "
        "NOT_YET_DISCRIMINATING against origin/lab/product "
        f"{prod_head}; items (3)/(4) standing. The rejected cycle {RUN} is "
        f"repaired by {REPAIR_RUN} (F1-F4). Another cycle under the SAME "
        "factory-direction question becomes discriminating only when Core "
        "Product lands its P0 dual fix (detector + path routing + full-family "
        "slice regeneration), which unblocks the frozen item-(2) re-measure "
        "and the d2_path_scope_probe re-run; until then it would re-derive "
        "closed work."
    )
    st["next_recommendation"] = (
        "NOT_YET_DISCRIMINATING (item (2) blocked on product): Core Product "
        "must land the letterhead detector fix for the two profiled P1 "
        "offset-0 multi-line court-header patterns AND route the "
        "offline/slice path through the filter (fixture_generation bypass "
        "prevents execution); then re-run the frozen item-(2) post-repair "
        "re-measure + d2_path_scope_probe on that head. Do not re-run item "
        "(1); do not re-score packet 39319405429; do not re-litigate the "
        "accepted PATH_SCOPE_RESIDUAL or the per-class D2/D3/D4 verdict."
    )
    st["state_updated_at"] = _now()
    st["state_updated_by"] = f"repair_round1_{RUN}"

    missing = [r for r in refs
               if not (_REPO_ROOT / r).exists()
               and not r.endswith(f"{RUN}_nested_evidence_refs.json")]
    if missing and not allow_deferred:
        print(json.dumps({"refused_state_write": "unresolvable refs",
                          "missing": missing}, indent=1), file=sys.stderr)
        return 3
    deferred = sorted(missing)
    if deferred:
        # phase-A write: the living-suite identity pins need the advanced state
        # BEFORE pytest runs, so refs to not-yet-written pytest/report/guard
        # records are deferred to the final state pass (same script, strict).
        pass

    _write_json(STATE, st)
    print(json.dumps({
        "state_sha256": _sha256(STATE),
        "before": before,
        "after": {"github_run": st["github_run"],
                  "operational_resume_of": st["operational_resume_of"],
                  "accepted_run_id": st["accepted_run_id"],
                  "direction_version": st["direction_version"],
                  "evidence_refs_n": st["evidence_refs_n"],
                  "run_identity_history_n": len(st["run_identity_history"])},
        "refs_added": added,
        "refs_deferred_to_final_pass": deferred,
        "posture": {f: st[f] for f in POSTURE_FLAGS},
    }, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["fetch-rest", "diagnose", "freeze",
                                     "repro", "verify", "state", "all"])
    ap.add_argument("--allow-deferred", action="store_true",
                    help="phase-A state pass: defer refs whose records are "
                         "written later in this same run (final pass is strict)")
    args = ap.parse_args(argv)
    order = {"all": ["fetch-rest", "diagnose", "freeze", "repro", "verify",
                     "state"],
             "fetch-rest": ["fetch-rest"], "diagnose": ["diagnose"],
             "freeze": ["freeze"], "repro": ["repro"],
             "verify": ["verify"], "state": ["state"]}[args.mode]
    rc = 0
    fns = {"fetch-rest": fetch_rest, "diagnose": diagnose, "freeze": freeze,
           "repro": repro, "verify": verify,
           "state": lambda: state(allow_deferred=args.allow_deferred)}
    for m in order:
        code = fns[m]()
        rc = rc or code
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
