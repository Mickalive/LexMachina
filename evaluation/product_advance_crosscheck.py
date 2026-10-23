#!/usr/bin/env python3
"""Product-advance cross-check — factory direction v63, ordered items (1) and (2).

WHY THIS INSTRUMENT EXISTS
--------------------------
The accepted product head advanced from fe219a19/7a70953e to ae854b6a (accept
product cycle 39909013473) while no accepted serve recommendation exists.  The
evaluation lane's v63 ordered work says the frozen checks must be re-executed
against the NEW shipped planner under a NEW run id when the product bytes move,
and that each of the product lane's four discharge/land status items must be
cross-checked as it lands.  This is a thin, offline cross-check that invokes the
already-accepted instruments unchanged and adds only:

* pin re-hashing against the new accepted product head;
* a byte-identity comparison of the V3 packet bundles against the accepted
  falsification record (so a product-advance change is never silently averaged
  into the old verdict);
* a re-freeze (V2/V3) of the shipped-planner and degradation-disclosure
  instruments with the new product pins and this run id, because those freezes
  name their product bytes and drift by design when the product advances;
* a currency check of the accepted live-answer reliability measurement;
* a pin-only check of the coverage-remediation cross-check (its pinned product
  code and evidence files are unchanged, so re-executing an offline replay adds
  no discriminating information and is not claimed);
* the orchestration diagnosis of the failed run this cycle resumes.

REUSE-FIRST
-----------
No measurement rule is re-implemented here:
* leg A calls ``evaluation.mapping_free_recall_falsifier.run()`` unchanged;
* leg B calls ``evaluation.shipped_planner_remedy_verification.run()`` unchanged
  through a new freeze record (same G1s-G4s, same C1s-C5s);
* leg C calls ``evaluation.degradation_disclosure_crosscheck_v2.run()`` unchanged
  through a new freeze record (same G1-G4, same C1-C6).

CLI
---
    python -m evaluation.product_advance_crosscheck \
        --run-id 39916358347 \
        --out results/evaluation/product_advance_crosscheck/39916358347.json \
        --report reports/evaluation/PRODUCT_ADVANCE_CROSSCHECK_39916358347.md

Exit codes: 0 pass, 1 product still falsified / material deliverable drift,
2 environment or vacuous (never a pass).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-product-advance-crosscheck/1"
RUN_ID = "39916358347"
DIRECTION_VERSION = 63
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")
ACCEPTED_PRODUCT_HEAD = "ae854b6a9ff4df4429d36725e364e721cb73096b"
ACCEPTED_LAB_EVALUATION_TIP = "95675eda62887ef043508caf31e22d6616849d39"

HYPOTHESIS_RELPATH = "evaluation/PRODUCT_ADVANCE_CROSSCHECK_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/PRODUCT_ADVANCE_CROSSCHECK_FREEZE_RECORD_V1.json"

ACCEPTED_A_RELPATH = "results/evaluation/counter_authority_surface_falsifier/39909449668.json"
ACCEPTED_B_RELPATH = "results/evaluation/shipped_planner_remedy_verification/39813664201.json"
ACCEPTED_C_RELPATH = "results/evaluation/degradation_disclosure_crosscheck/39820650174_v2.json"
ACCEPTED_D_RELPATH = "results/evaluation/coverage_remediation_crosscheck/39813664201.json"
ACCEPTED_E_RELPATH = "results/evaluation/answer_reliability_crosscheck/39827806011.json"

PLANNER_V2_HYP_RELPATH = "evaluation/SHIPPED_PLANNER_REMEDY_VERIFICATION_HYPOTHESIS_V2.json"
PLANNER_V2_FREEZE_RELPATH = "evaluation/SHIPPED_PLANNER_REMEDY_VERIFICATION_FREEZE_RECORD_V2.json"
DDC_V3_HYP_RELPATH = "evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_HYPOTHESIS_V3.json"
DDC_V3_FREEZE_RELPATH = "evaluation/DEGRADATION_DISCLOSURE_CROSSCHECK_FREEZE_RECORD_V3.json"

COVERAGE_FREEZE_RELPATH = "evaluation/COVERAGE_REMEDIATION_CROSSCHECK_FREEZE_RECORD_V1.json"
RELIABILITY_FREEZE_RELPATH = "evaluation/ANSWER_RELIABILITY_CROSSCHECK_FREEZE_RECORD_V1.json"

V3_QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
ACCEPTED_A_FAILED_GATES = {
    "mf::concept_coverage::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::fr-bail-entretien",
    "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
}


def leg_a_engine_path(run_id: str) -> Path:
    return (REPO_ROOT / "results/evaluation/mapping_free_recall_falsifier" /
            f"{run_id}_engine_mapping_free_recall_falsifier.json")


def leg_b_record_path(run_id: str) -> Path:
    return (REPO_ROOT / "results/evaluation/shipped_planner_remedy_verification" /
            f"{run_id}.json")


def leg_c_record_path(run_id: str) -> Path:
    return (REPO_ROOT / "results/evaluation/degradation_disclosure_crosscheck" /
            f"{run_id}.json")

EXIT_OK = 0
EXIT_FALSIFIED = 1
EXIT_ENV = 2

CLAIM_CEILING = (
    "This instrument establishes only whether the accepted evaluation findings still hold on "
    "the new accepted product head ae854b6a and whether the product's four ordered deliverable "
    "claims remain current. It is NOT a new counter-authority recall measurement (no probe is "
    "executed against OpenCaseLaw), NOT a serve recommendation, NOT a re-score of any frozen "
    "absolute bar (LABEL_SOUND and GEOMETRY_SOUND stay REPORTED-ONLY and unmet), NOT a "
    "jurist-usefulness claim and NOT a human-gate readiness claim. Both DO-NOT-SERVE orders "
    "stand; admission stays fail-closed; human_gate_ready, machine_gate_ready, packet_admitted "
    "and ready_for_owner_session stay false. It re-derives no threshold, bar, rubric or verdict "
    "contract, builds or re-scores no Frontier candidate, and runs no obsolete universal-174k "
    "benchmark."
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                    encoding="utf-8")


def _git(args: list[str], cwd: Path | None = None) -> str | None:
    try:
        proc = subprocess.run(["git", *args], cwd=str(cwd or REPO_ROOT),
                              capture_output=True, text=True, timeout=20)
        if proc.returncode != 0:
            return None
        return proc.stdout.strip() or None
    except Exception:  # pragma: no cover - environment disclosure only
        return None


def mount_head(mount: Path) -> str | None:
    return _git(["rev-parse", "HEAD"], cwd=mount)


def pin_map(root: Path, pins: dict[str, str]) -> dict[str, Any]:
    """Re-hash every pinned relative path under ``root``."""
    checks: list[dict[str, Any]] = []
    all_hold = True
    for rel, expected in sorted(pins.items()):
        path = root / rel
        if not path.is_file():
            checks.append({"path": rel, "status": "ABSENT", "expected": expected})
            all_hold = False
            continue
        actual = sha256_file(path)
        ok = actual == expected
        checks.append({"path": rel, "status": "ok" if ok else "DRIFT",
                       "expected": expected, "actual": actual})
        all_hold = all_hold and ok
    return {"all_hold": all_hold, "n": len(checks), "checks": checks}


def bundle_hashes(record: dict) -> dict[str, str]:
    """Extract {qid: bundle_sha256} from an engine record (per_question list)."""
    out: dict[str, str] = {}
    for row in record.get("per_question") or []:
        qid = str(row.get("qid") or "")
        digest = row.get("bundle_sha256")
        if qid and digest:
            out[qid] = str(digest)
    return out


def compare_bundle_hashes(new: dict[str, str], accepted: dict[str, str]) -> dict[str, Any]:
    qids = sorted(set(new) | set(accepted))
    rows = []
    identical = True
    for qid in qids:
        same = new.get(qid) == accepted.get(qid)
        identical = identical and same
        rows.append({"qid": qid, "identical": same,
                     "new": new.get(qid), "accepted": accepted.get(qid)})
    return {"identical": identical, "n_questions": len(qids), "questions": rows}


def _leg(leg: str, code: int, verdict: str, **extra: Any) -> dict:
    return {"leg": leg, "exit_code": code, "verdict": verdict, **extra}


def _write_leg_record(path: Path, record: dict) -> None:
    write_json(path, record)


# --------------------------------------------------------------------------- #
# leg A — mapping-free retrieval / counter-authority falsification
# --------------------------------------------------------------------------- #
def run_leg_a(run_id: str, mount: Path) -> dict:
    from evaluation import mapping_free_recall_falsifier as ENGINE

    out_path = leg_a_engine_path(run_id)
    code, rec = ENGINE.run(run_id, out_path, str(mount), REPO_ROOT, ("39319405429",))

    accepted = load_json(REPO_ROOT / ACCEPTED_A_RELPATH)
    comparison = compare_bundle_hashes(bundle_hashes(rec), bundle_hashes(accepted))
    failed = [g.get("gate") for g in rec.get("failed_gates") or []]
    same_failed = set(failed) == ACCEPTED_A_FAILED_GATES
    return _leg(
        "A_mapping_free_falsification", code, str(rec.get("verdict")),
        record_path=str(out_path.relative_to(REPO_ROOT)),
        reason=rec.get("reason"),
        accepted_record=ACCEPTED_A_RELPATH,
        product_mount_head=rec.get("product_mount_head"),
        n_gates=rec.get("n_gates"), n_failed=rec.get("n_failed"),
        failed_gates=failed,
        failed_gates_equal_accepted_set=same_failed,
        non_vacuity_all_hold=(rec.get("non_vacuity") or {}).get("all_hold"),
        input_drift=rec.get("input_drift"),
        bundle_byte_identity=comparison,
        claim_ceiling=rec.get("claim_ceiling"),
    )


# --------------------------------------------------------------------------- #
# leg B — shipped planner remedy (a)
# --------------------------------------------------------------------------- #
def run_leg_b(run_id: str, mount: Path) -> dict:
    from evaluation import shipped_planner_remedy_verification as SPA

    out_path = leg_b_record_path(run_id)
    saved_h, saved_f = SPA.HYPOTHESIS_PATH, SPA.FREEZE_PATH
    try:
        SPA.HYPOTHESIS_PATH = REPO_ROOT / PLANNER_V2_HYP_RELPATH
        SPA.FREEZE_PATH = REPO_ROOT / PLANNER_V2_FREEZE_RELPATH
        code, rec = SPA.run(run_id, mount)
    finally:
        SPA.HYPOTHESIS_PATH, SPA.FREEZE_PATH = saved_h, saved_f
    _write_leg_record(out_path, rec)
    return _leg(
        "B_shipped_planner_remedy", code, str(rec.get("verdict")),
        record_path=str(out_path.relative_to(REPO_ROOT)),
        reason=rec.get("reason"),
        freeze_record=PLANNER_V2_FREEZE_RELPATH,
        product_mount_head=rec.get("product_mount_head"),
        planner_sha256=(rec.get("product_mount_head") and
                        (mount / "product/query/adversarial_retrieval.py").is_file() and
                        sha256_file(mount / "product/query/adversarial_retrieval.py")),
        gate_failures=rec.get("gate_failures"),
        control_failures=rec.get("control_failures"),
        pins_before_ok=(rec.get("pins_before") or {}).get("all_ok"),
        pins_after_ok=(rec.get("pins_after") or {}).get("all_ok"),
        claim_ceiling=rec.get("claim_ceiling"),
    )


# --------------------------------------------------------------------------- #
# leg C — writer-abort degradation disclosure
# --------------------------------------------------------------------------- #
def _degradation_product_pins() -> dict[str, str]:
    from evaluation import degradation_disclosure_crosscheck as v1
    freeze = load_json(REPO_ROOT / DDC_V3_FREEZE_RELPATH)
    return dict(freeze.get("product_pins") or v1.PRODUCT_PINS)


def run_leg_c(run_id: str, mount: Path) -> dict:
    from evaluation import degradation_disclosure_crosscheck_v2 as DDC2

    out_path = leg_c_record_path(run_id)
    saved = (DDC2.RUN_ID, DDC2.FREEZE_PATH, DDC2.HYPOTHESIS_PATH, DDC2.PRODUCT_PINS)
    try:
        DDC2.RUN_ID = run_id
        DDC2.FREEZE_PATH = REPO_ROOT / DDC_V3_FREEZE_RELPATH
        DDC2.HYPOTHESIS_PATH = REPO_ROOT / DDC_V3_HYP_RELPATH
        DDC2.PRODUCT_PINS = _degradation_product_pins()
        code, rec = DDC2.run(run_id, mount)
    finally:
        (DDC2.RUN_ID, DDC2.FREEZE_PATH, DDC2.HYPOTHESIS_PATH,
         DDC2.PRODUCT_PINS) = saved
    _write_leg_record(out_path, rec)
    return _leg(
        "C_degradation_disclosure", code, str(rec.get("verdict")),
        record_path=str(out_path.relative_to(REPO_ROOT)),
        reason=rec.get("reason"),
        freeze_record=DDC_V3_FREEZE_RELPATH,
        product_mount_head=rec.get("product_mount_head"),
        gate_failures=rec.get("gate_failures"),
        control_failures=rec.get("control_failures"),
        product_pins_before_ok=(rec.get("product_pins_before") or {}).get("all_hold"),
        product_pins_after_ok=(rec.get("product_pins_after") or {}).get("all_hold"),
        claim_ceiling=rec.get("claim_ceiling"),
    )


# --------------------------------------------------------------------------- #
# leg D — coverage-remediation pins
# --------------------------------------------------------------------------- #
def run_leg_d(mount: Path) -> dict:
    freeze = load_json(REPO_ROOT / COVERAGE_FREEZE_RELPATH)
    product = pin_map(mount, freeze.get("product_pins") or {})
    repo = pin_map(REPO_ROOT, freeze.get("pins") or {})
    hold = bool(product["all_hold"] and repo["all_hold"])
    return _leg(
        "D_coverage_remediation_pins", EXIT_OK if hold else EXIT_FALSIFIED,
        "COVERAGE_PINS_STILL_HOLD" if hold else "COVERAGE_PIN_DRIFT",
        freeze_record=COVERAGE_FREEZE_RELPATH,
        accepted_crosscheck=ACCEPTED_D_RELPATH,
        product_pins=product, repo_pins=repo,
        note=("the pinned product code and evidence files are byte-identical, so the accepted "
              "offline replay is not re-executed and no new reach claim is issued"),
    )


# --------------------------------------------------------------------------- #
# leg E — live-answer reliability currency
# --------------------------------------------------------------------------- #
def run_leg_e(mount: Path) -> dict:
    freeze = load_json(REPO_ROOT / RELIABILITY_FREEZE_RELPATH)
    pins = freeze.get("product_pins") or {}
    rehash = pin_map(mount, pins)
    artifact_rel = [k for k in pins if k.startswith("results/product/answer_reliability/")]
    source_rel = [k for k in pins if k.startswith("product/")]
    artifact_ok = all(any(c["path"] == rel and c["status"] == "ok" for c in rehash["checks"])
                      for rel in artifact_rel)
    source_drift = [c["path"] for c in rehash["checks"]
                    if c["path"] in source_rel and c["status"] != "ok"]

    state_path = mount / "state/product.json"
    state_text = state_path.read_text(encoding="utf-8") if state_path.is_file() else ""
    disclaims = ("no live-answer reliability re-measurement" in state_text
                 or "live-answer reliability measurement has NOT run" in state_text
                 or "no live-answer reliability figure" in state_text)

    if not artifact_ok:
        status = "RELIABILITY_MEASUREMENT_MISSING_OR_DRIFTED"
        code = EXIT_FALSIFIED
    elif source_drift:
        status = "RELIABILITY_MEASUREMENT_STALE_ON_PRODUCT_ADVANCE"
        code = EXIT_FALSIFIED
    else:
        status = "RELIABILITY_MEASUREMENT_CURRENT"
        code = EXIT_OK

    return _leg(
        "E_answer_reliability_currency", code, status,
        freeze_record=RELIABILITY_FREEZE_RELPATH,
        accepted_crosscheck=ACCEPTED_E_RELPATH,
        measurement_artifact_pins_ok=artifact_ok,
        drifting_product_sources=source_drift,
        product_state_disclaims_remeasurement=disclaims,
        rehash=rehash,
        note=("the accepted 0.857 figure is not restated as current for head ae854b6a"
              if source_drift else "no source drift; the accepted measurement remains current"),
    )


# --------------------------------------------------------------------------- #
# orchestration diagnosis
# --------------------------------------------------------------------------- #
def orchestration_diagnosis(freeze: dict) -> dict:
    facts = dict(freeze.get("orchestration_facts_at_freeze") or {})
    snapshot_ref = facts.get("snapshot_team_ref")
    local = _git(["rev-parse", "origin/cycle/core/evaluation/39915124469/team"])
    subject = _git(["log", "-1", "--format=%s", "origin/cycle/core/evaluation/39915124469/team"])
    head = _git(["rev-parse", "HEAD"])
    lab = _git(["rev-parse", "origin/lab/evaluation"])
    accepted_tip = facts.get("accepted_lab_evaluation_tip") or ACCEPTED_LAB_EVALUATION_TIP
    facts.update({
        "snapshot_team_ref_local": local,
        "snapshot_team_subject_local": subject,
        "current_checkout_head": head,
        "lab_evaluation_ref_local": lab,
        "audit_ref_present": facts.get("audit_ref_for_39915124469") == "PRESENT",
        "snapshot_equals_prior_run_snapshot": bool(
            local and facts.get("prior_run_snapshot_team_ref")
            and local == facts["prior_run_snapshot_team_ref"]),
        "snapshot_equals_accepted_tip": bool(local and local == accepted_tip),
        "accepted_lab_evaluation_tip_used": accepted_tip,
    })
    if facts.get("audit_ref_for_39915124469") != "PRESENT":
        conclusion = "ZERO_DELTA_ORCHESTRATION_FAILURE"
        text = (
            "Run 39915124469 produced no producer commit: its team branch is byte-identical to "
            "the team snapshot of run 39910387854 (81b4f131), no audit branch exists, and the "
            "accepted lab/evaluation tip is 95675eda. The workflow's validation/write-scope "
            "steps never ran because the team step did not complete successfully; this is an "
            "orchestration/zero-delta failure, NOT a validation verdict and NOT a product or "
            "evidence defect. The valid completed producer work already on the snapshot "
            "(39909449668 falsification re-confirmation + 39910387854 audit-log recovery) is "
            "preserved and re-verified below, not overwritten."
        )
    else:
        conclusion = "AUDIT_REF_PRESENT_NEEDS_REVIEW"
        text = "An audit ref exists for 39915124469; re-read it before treating this as zero delta."
    return {
        "schema": "lex-evaluation-orchestration-diagnosis/1",
        "run_id": int(RUN_ID),
        "subject_of_resume": "39915124469",
        "conclusion": conclusion,
        "facts": facts,
        "assessment": text,
        "claim_ceiling": ("Git-ref and workflow-source facts only; producer job logs were not "
                          "downloadable unauthenticated (HTTP 403/rate limit), so the agent-side "
                          "failure class is inferred, never fabricated."),
    }


# --------------------------------------------------------------------------- #
# controls
# --------------------------------------------------------------------------- #
def control_pin_drift_detected(mount: Path, pins: dict[str, str]) -> dict:
    mutated = dict(pins)
    if not mutated:
        return {"holds": False, "why": "no pins to mutate"}
    key = sorted(mutated)[0]
    mutated[key] = "0" * 64
    altered = pin_map(mount, mutated)
    return {"holds": not altered["all_hold"], "mutated_pin": key,
            "detected": not altered["all_hold"]}


def control_bundle_mismatch_detected(new: dict[str, str]) -> dict:
    if not new:
        return {"holds": False, "why": "no bundle hashes to mutate"}
    accepted = dict(new)
    key = sorted(accepted)[0]
    accepted[key] = "0" * 64
    cmp = compare_bundle_hashes(new, accepted)
    return {"holds": not cmp["identical"], "mutated_qid": key,
            "detected": not cmp["identical"]}


def control_frozen_inputs_rehash(freeze: dict) -> dict:
    pins = dict(freeze.get("pins") or {})
    r = pin_map(REPO_ROOT, pins)
    return {"holds": r["all_hold"], "n_pins": r["n"], "checks": r["checks"]}


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #
def _wrong_run_id_record(run_id: str) -> dict:
    return {
        "schema": SCHEMA, "lane": "evaluation", "run_id": run_id,
        "direction_version": DIRECTION_VERSION,
        "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
        "reason": "run id does not match the frozen run_id_of_record",
        "frozen_run_id": RUN_ID,
        "claim_ceiling": CLAIM_CEILING,
    }


def run(run_id: str, mount: Path, out_dir: Path, report_dir: Path) -> tuple[int, dict]:
    if str(run_id) != RUN_ID:
        return EXIT_ENV, _wrong_run_id_record(str(run_id))

    if not (REPO_ROOT / HYPOTHESIS_RELPATH).is_file() or not (REPO_ROOT / FREEZE_RELPATH).is_file():
        return EXIT_ENV, {**_wrong_run_id_record(str(run_id)),
                          "reason": "hypothesis or freeze record absent"}
    if not mount.is_dir():
        return EXIT_ENV, {**_wrong_run_id_record(str(run_id)),
                          "reason": "accepted product mount absent", "mount": str(mount)}

    freeze = load_json(REPO_ROOT / FREEZE_RELPATH)
    hypothesis = load_json(REPO_ROOT / HYPOTHESIS_RELPATH)
    started = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    pins_before = pin_map(REPO_ROOT, freeze.get("pins") or {})
    if not pins_before["all_hold"]:
        return EXIT_ENV, {
            "schema": SCHEMA, "lane": "evaluation", "run_id": run_id,
            "direction_version": DIRECTION_VERSION,
            "verdict": "ENVIRONMENT_OR_VACUOUS", "exit_code": EXIT_ENV,
            "reason": "frozen repo input pin drift before execution",
            "pins_before": pins_before,
            "claim_ceiling": CLAIM_CEILING,
        }

    head_before = mount_head(mount)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    legs: dict[str, dict] = {}
    env_failure = False
    falsified = False

    def note(leg: dict) -> None:
        nonlocal env_failure, falsified
        if leg["exit_code"] == EXIT_ENV:
            env_failure = True
        elif leg["exit_code"] == EXIT_FALSIFIED:
            falsified = True

    for name, fn in (
        ("A_mapping_free_falsification", lambda: run_leg_a(run_id, mount)),
        ("B_shipped_planner_remedy", lambda: run_leg_b(run_id, mount)),
        ("C_degradation_disclosure", lambda: run_leg_c(run_id, mount)),
        ("D_coverage_remediation_pins", lambda: run_leg_d(mount)),
        ("E_answer_reliability_currency", lambda: run_leg_e(mount)),
    ):
        try:
            legs[name] = fn()
        except Exception as exc:  # a leg crash is an environment result, never a pass
            legs[name] = _leg(name, EXIT_ENV, "ENVIRONMENT_OR_VACUOUS",
                              error=f"{type(exc).__name__}: {exc}")
        note(legs[name])

    # local controls (non-vacuity of this wrapper's own logic)
    from evaluation import degradation_disclosure_crosscheck as v1
    product_pins = dict(freeze.get("product_pins") or v1.PRODUCT_PINS)
    c1 = control_pin_drift_detected(mount, product_pins)
    leg_a_new = {}
    try:
        eng = load_json(leg_a_engine_path(run_id))
        leg_a_new = bundle_hashes(eng)
    except Exception:
        pass
    c2 = control_bundle_mismatch_detected(leg_a_new)
    c3 = control_frozen_inputs_rehash(freeze)
    controls = {
        "C1_planted_product_pin_drift_is_detected": c1,
        "C2_planted_bundle_hash_mismatch_is_detected": c2,
        "C3_frozen_leg_inputs_exist_and_rehash": c3,
    }
    control_failures = [k for k, v in controls.items() if not v.get("holds")]

    pins_after = pin_map(REPO_ROOT, freeze.get("pins") or {})
    head_after = mount_head(mount)
    if not pins_after["all_hold"]:
        env_failure = True

    diagnosis = orchestration_diagnosis(freeze)

    if env_failure or control_failures:
        code, verdict = EXIT_ENV, "ENVIRONMENT_OR_VACUOUS"
    elif falsified:
        code = EXIT_FALSIFIED
        drift = [k for k, v in legs.items()
                 if v["exit_code"] == EXIT_FALSIFIED and k != "A_mapping_free_falsification"]
        verdict = ("PRODUCT_STILL_FALSIFIED_WITH_DELIVERABLE_DRIFT" if drift
                   else "PRODUCT_STILL_FALSIFIED")
    else:
        code, verdict = EXIT_OK, "PASS_NO_FALSIFICATION"

    headline = []
    for name, leg in legs.items():
        if leg["exit_code"] == EXIT_FALSIFIED:
            headline.append(f"{name}: {leg['verdict']}")
    if not headline:
        headline = [f"{name}: {leg['verdict']}" for name, leg in legs.items()]

    record = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": started,
        "verdict": verdict,
        "exit_code": code,
        "headline": headline,
        "hypothesis": {"path": HYPOTHESIS_RELPATH,
                       "sha256": sha256_file(REPO_ROOT / HYPOTHESIS_RELPATH)},
        "freeze_record": {"path": FREEZE_RELPATH,
                          "sha256": sha256_file(REPO_ROOT / FREEZE_RELPATH)},
        "instrument": {"path": "evaluation/product_advance_crosscheck.py",
                       "sha256": sha256_file(Path(__file__).resolve())},
        "product_mount": str(mount),
        "product_mount_head_before": head_before,
        "product_mount_head_after": head_after,
        "accepted_product_head_expected": ACCEPTED_PRODUCT_HEAD,
        "product_head_matches_expected": head_before == ACCEPTED_PRODUCT_HEAD,
        "legs": legs,
        "controls": controls,
        "control_failures": control_failures,
        "pins_before": pins_before,
        "pins_after": pins_after,
        "orchestration_diagnosis": diagnosis,
        "no_new_thresholds": True,
        "no_174k_benchmark_rerun": True,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "claim_ceiling": CLAIM_CEILING,
    }

    out_path = out_dir / f"{run_id}.json"
    write_json(out_path, record)
    _write_report(report_dir / f"PRODUCT_ADVANCE_CROSSCHECK_{run_id}.md", record, out_path)
    return code, record


def _write_report(path: Path, record: dict, out_path: Path) -> None:
    lines = [
        f"# Product-advance cross-check — run {record['run_id']}",
        "",
        f"- Combined verdict: **{record['verdict']}** (exit {record['exit_code']})",
        f"- Accepted product head expected: `{record['accepted_product_head_expected']}`",
        f"- Product mount head: `{record['product_mount_head_before']}` "
        f"(matches expected={record['product_head_matches_expected']})",
        f"- Direction: v{record['direction_version']}",
        f"- Machine record: `{out_path.relative_to(REPO_ROOT)}`",
        "",
        "## Headline",
        "",
    ]
    lines += [f"- {h}" for h in record.get("headline") or []]
    lines += ["", "## Legs", "", "| leg | exit | verdict | record |", "|---|---|---|---|"]
    for name, leg in record["legs"].items():
        rec = leg.get("record_path") or leg.get("freeze_record") or ""
        lines.append(f"| {name} | {leg['exit_code']} | {leg['verdict']} | `{rec}` |")

    a = record["legs"].get("A_mapping_free_falsification", {})
    lines += [
        "",
        "## Leg A — mapping-free retrieval / counter-authority",
        "",
        f"- Failed gates: {', '.join(a.get('failed_gates') or []) or 'none'}",
        f"- Failed set equals the accepted set: {a.get('failed_gates_equal_accepted_set')}",
        f"- Non-vacuity all hold: {a.get('non_vacuity_all_hold')}",
        f"- Input drift: {a.get('input_drift') or 'none'}",
        f"- V3 bundle bytes identical to accepted 39909449668: "
        f"{(a.get('bundle_byte_identity') or {}).get('identical')}",
    ]
    for row in (a.get("bundle_byte_identity") or {}).get("questions") or []:
        lines.append(f"  - {row['qid']}: identical={row['identical']} sha256={row['new']}")

    b = record["legs"].get("B_shipped_planner_remedy", {})
    c = record["legs"].get("C_degradation_disclosure", {})
    d = record["legs"].get("D_coverage_remediation_pins", {})
    e = record["legs"].get("E_answer_reliability_currency", {})
    lines += [
        "",
        "## Leg B — shipped planner remedy (a)",
        "",
        f"- Verdict: {b.get('verdict')} (exit {b.get('exit_code')})",
        f"- Gate failures: {b.get('gate_failures')}",
        f"- Control failures: {b.get('control_failures')}",
        f"- Pins before/after all ok: {b.get('pins_before_ok')} / {b.get('pins_after_ok')}",
        "",
        "## Leg C — writer-abort degradation disclosure",
        "",
        f"- Verdict: {c.get('verdict')} (exit {c.get('exit_code')})",
        f"- Gate failures: {c.get('gate_failures')}",
        f"- Control failures: {c.get('control_failures')}",
        f"- Product pins before/after all hold: "
        f"{c.get('product_pins_before_ok')} / {c.get('product_pins_after_ok')}",
        "",
        "## Leg D — query-coverage remediation pins",
        "",
        f"- Verdict: {d.get('verdict')} (exit {d.get('exit_code')})",
        f"- {d.get('note')}",
        "",
        "## Leg E — live-answer reliability currency",
        "",
        f"- Verdict: {e.get('verdict')} (exit {e.get('exit_code')})",
        f"- Measurement artifact pins ok: {e.get('measurement_artifact_pins_ok')}",
        f"- Drifting product sources: {e.get('drifting_product_sources')}",
        f"- Product state disclaims re-measurement: "
        f"{e.get('product_state_disclaims_remeasurement')}",
        f"- {e.get('note')}",
        "",
        "## Controls",
        "",
    ]
    for name, ctrl in record.get("controls", {}).items():
        lines.append(f"- {name}: holds={ctrl.get('holds')}")
    lines += [
        "",
        "## Orchestration diagnosis (run 39915124469)",
        "",
        f"- Conclusion: **{record['orchestration_diagnosis']['conclusion']}**",
        f"- {record['orchestration_diagnosis']['assessment']}",
        "",
        "## Claim ceiling",
        "",
        record["claim_ceiling"],
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "results/evaluation/product_advance_crosscheck"))
    ap.add_argument("--report-dir", default=str(REPO_ROOT / "reports/evaluation"))
    args = ap.parse_args(argv)
    code, record = run(args.run_id, Path(args.mount), Path(args.out_dir), Path(args.report_dir))
    print(json.dumps({
        "verdict": record.get("verdict"),
        "exit_code": code,
        "headline": record.get("headline"),
        "legs": {k: {"exit_code": v.get("exit_code"), "verdict": v.get("verdict")}
                 for k, v in (record.get("legs") or {}).items()},
        "control_failures": record.get("control_failures"),
        "product_mount_head": record.get("product_mount_head_before"),
    }, indent=1))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
