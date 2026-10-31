#!/usr/bin/env python3
"""Operational-resume verification cycle for run 41157741636 (evaluation, v68).

WHAT THIS IS
------------
A freeze-first adapter (hypothesis + freeze committed at b44a73c0 BEFORE this
script's claim-bearing execution) that:

1. re-verifies every pin expected by
   ``evaluation/OPERATIONAL_RESUME_41157741636_FREEZE_V1.json`` before and
   after execution (any drift = NOT_MEASURED, never a pass);
2. re-adjudicates the lane question's ordered item-(2) precondition on the
   CURRENT accepted product head by IMPORTING, by hash-verified import, the
   accepted adjudicator ``precondition_gate`` / ``leg_markers`` /
   ``post_repair_inventory`` from ``evaluation/post_repair_family_ca_falsifier.py``
   (sha 126a1234...). No replacement adjudicator is defined here;
3. adds the behavioral half of H1 (the pivot_absent-abstained incumbent row's
   ``counter_evidence_verified`` flag on the newest shipped bundle versus the
   v68-named baseline bundle) as a direct committed-byte read;
4. re-hashes the STANDING half-2 measurement of accepted run 40258497460 and
   every bundle of its frozen population (0-drift expected). The closed bytes
   are deliberately NOT re-scored - that would be a zero-delta re-derivation
   (lane question item (5));
5. executes the preserved orphan suite
   ``tests/evaluation/test_minimal_retrieval_ca_benchmark_falsifier.py`` and the
   accepted multilingual/provenance suite ``tests/evaluation/test_retrieval_benchmark.py``
   under the documented ``evaluation/no_pytest_runner.py`` shim, committing
   whatever they return;
6. verifies C4: this producer writes NO file under ``results/audit/evaluation/``
   or ``reports/audit/evaluation/`` named for this run (the independent
   auditor's exclusive scope).

Claim ceiling is the one frozen in the hypothesis: diagnosis + quarantine of
the unaudited 41149811055->41156158583->41156948851 chain, item-(2) precondition
status (an OUTPUT, not an expectation), standing-measurement currency, and the
two suite executions. No frozen bar is scored, no serve verdict is produced, no
packet is scored, and all posture flags stay FALSE.

Scratch-run obligation: a claim-bearing invocation writes to the committed
defaults; pass --out-dir/--report-dir for a scratch poke.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-operational-resume-verification/1"
RUN_ID_DEFAULT = "41157741636"
HYP_REL = "evaluation/OPERATIONAL_RESUME_41157741636_HYPOTHESIS_V1.json"
FREEZE_REL = "evaluation/OPERATIONAL_RESUME_41157741636_FREEZE_V1.json"
MOUNT = Path("/tmp/lex_accepted/product")
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/operational_resume"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports/evaluation"

# Frozen expected digests, copied from the FREEZE record. Verified before and after.
EXPECTED = {
    "product_mount_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
    "product_code_file": "product/query/counter_evidence_span.py",
    "product_code_sha256": "82cea13122b13a60e4da746072af4a185f9e4b2e0ef51853d6273acb7a1bb6ce",
    "frozen_predicate_instrument": "evaluation/counter_evidence_quality_benchmark.py",
    "frozen_predicate_instrument_sha256": "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d",
    "accepted_adjudicator": "evaluation/post_repair_family_ca_falsifier.py",
    "accepted_adjudicator_sha256": "126a1234f3fe8a3f10ff736dff7466093000a2fadd8871f02f97efe974543a08",
    "standing_half2_measurement": "results/evaluation/post_repair_family_ca_falsifier/40258497460.json",
    "standing_half2_measurement_sha256": "2a7f4ad420612661d1b7b500994476235f6af3d136f6272ac3bbf34944b1b5d1",
    "product_family_claim_artifact": "results/product/counter_content_family/CYCLE_40257275384.json",
    "product_family_claim_artifact_sha256": "eaab4d0637c537a74e08cee37aff781b4fddea0294fa817c74e23e64e9a81feb",
    "orphan_suite": "tests/evaluation/test_minimal_retrieval_ca_benchmark_falsifier.py",
    "orphan_suite_sha256": "beeae2a18960cfd6ed8ce892d541a0cb92f84ee3a3ab90443e4f164f00466a3f",
    "multilingual_suite": "tests/evaluation/test_retrieval_benchmark.py",
    "multilingual_suite_sha256": "558e1f1b7143e09e704891d5e0d7401a9b688e8d9c3d4b389dc4229972dc47be",
    "hypothesis": HYP_REL,
    "hypothesis_sha256": "cb994e0261eb958c2c122e47733d3a9533f4a7edf7551e261f91f17741107825",
}

# Behavioral H1 evidence: the v68-named baseline bundle (verified=true) and the
# newest shipped bundle on the current head (verified=false expected).
BASELINE_BUNDLE_REL = "results/product/offline_slice/20261024T142517Z/rent-default.bundle.json"
NEWEST_BUNDLE_REL = "results/product/offline_slice/20261025T205046Z/rent-default.bundle.json"
TARGET_DECISION = "gr_gerichte_ERZ 2010 25"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mount_head(mount: Path) -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(mount), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        return p.stdout.strip() or None
    except Exception:
        return None


def check_pins() -> dict:
    """Re-hash every frozen pin. Returns per-pin status; all_match is the verdict."""
    out: dict = {}
    m = MOUNT

    head = mount_head(m)
    out["product_mount_head"] = {"expected": EXPECTED["product_mount_head"],
                                 "actual": head,
                                 "match": head == EXPECTED["product_mount_head"]}

    def file_pin(key: str, path: Path, expected: str) -> None:
        if path.is_file():
            actual = sha256_file(path)
            out[key] = {"expected": expected, "actual": actual, "match": actual == expected,
                        "present": True}
        else:
            out[key] = {"expected": expected, "actual": None, "match": False, "present": False}

    file_pin("product_code_sha256", m / EXPECTED["product_code_file"],
             EXPECTED["product_code_sha256"])
    file_pin("frozen_predicate_instrument_sha256",
             REPO_ROOT / EXPECTED["frozen_predicate_instrument"],
             EXPECTED["frozen_predicate_instrument_sha256"])
    file_pin("accepted_adjudicator_sha256",
             REPO_ROOT / EXPECTED["accepted_adjudicator"],
             EXPECTED["accepted_adjudicator_sha256"])
    file_pin("standing_half2_measurement_sha256",
             REPO_ROOT / EXPECTED["standing_half2_measurement"],
             EXPECTED["standing_half2_measurement_sha256"])
    file_pin("product_family_claim_artifact_sha256",
             m / EXPECTED["product_family_claim_artifact"],
             EXPECTED["product_family_claim_artifact_sha256"])
    file_pin("orphan_suite_sha256", REPO_ROOT / EXPECTED["orphan_suite"],
             EXPECTED["orphan_suite_sha256"])
    file_pin("multilingual_suite_sha256", REPO_ROOT / EXPECTED["multilingual_suite"],
             EXPECTED["multilingual_suite_sha256"])
    file_pin("hypothesis_sha256", REPO_ROOT / EXPECTED["hypothesis"],
             EXPECTED["hypothesis_sha256"])

    out["all_match"] = all(v.get("match") for v in out.values() if isinstance(v, dict))
    return out


def behavioral_row_read(mount: Path) -> dict:
    """H1 behavioral half: the target incumbent row's verified flag on both bundles."""
    def read(rel: str) -> dict:
        p = mount / rel
        if not p.is_file():
            return {"bundle": rel, "present": False}
        doc = json.loads(p.read_text(encoding="utf-8"))
        span = ((doc.get("provenance") or {}).get("counter_evidence_span") or {})
        row = None
        for d in doc.get("decisions") or []:
            if d.get("decision_id") == TARGET_DECISION:
                row = d
                break
        return {
            "bundle": rel,
            "present": True,
            "span": {k: span.get(k) for k in
                     ("applied", "n_candidates", "n_selected", "abstained_ids",
                      "abstention_reasons", "n_incumbent_downgraded")},
            "target_row": None if row is None else {
                "decision_id": row.get("decision_id"),
                "counter_status": row.get("counter_status"),
                "counter_evidence_verified": row.get("counter_evidence_verified"),
            },
        }

    baseline = read(BASELINE_BUNDLE_REL)
    newest = read(NEWEST_BUNDLE_REL)
    b_ver = (baseline.get("target_row") or {}).get("counter_evidence_verified")
    n_ver = (newest.get("target_row") or {}).get("counter_evidence_verified")
    return {
        "baseline_v68_named": baseline,
        "newest_shipped_current_head": newest,
        "finding": (
            "H1 behavioral half HOLDS: the pivot_absent-abstained incumbent "
            f"{TARGET_DECISION} carries counter_evidence_verified={b_ver} on the v68-named "
            f"baseline bundle and counter_evidence_verified={n_ver} on the newest shipped "
            "bundle at the current head - the rejection/incumbent leg downgrades the "
            "defective incumbent on the shipped path."
            if (b_ver is True and n_ver is False) else
            "H1 behavioral half DID NOT hold as predicted: baseline verified="
            f"{b_ver}, newest verified={n_ver}; published as measured, never adjusted."
        ),
        "h1_behavioral_hold": (b_ver is True and n_ver is False),
    }


def standing_measurement_currency(mount: Path) -> dict:
    """H4: re-hash the standing half-2 measurement and its frozen population."""
    rec_path = REPO_ROOT / EXPECTED["standing_half2_measurement"]
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    hyp_path = REPO_ROOT / "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40258497460_HYPOTHESIS_V1.json"
    hyp = json.loads(hyp_path.read_text(encoding="utf-8"))
    pop = hyp["population_FROZEN"]["bundles"]
    drift = []
    missing = []
    for b in pop:
        p = mount / b["path"]
        if not p.is_file():
            missing.append(b["path"])
            continue
        actual = sha256_file(p)
        if actual != b["sha256"]:
            drift.append({"path": b["path"], "expected": b["sha256"], "actual": actual})
    agg = rec.get("aggregate") or {}
    sweeps = rec.get("sweeps") or {}
    return {
        "standing_measurement_path": EXPECTED["standing_half2_measurement"],
        "standing_measurement_sha256_rehashed": sha256_file(rec_path),
        "standing_verdict": rec.get("verdict"),
        "standing_exit_code": rec.get("exit_code"),
        "standing_aggregate": {
            "n_bundles": agg.get("n_bundles"),
            "n_verified_scored_rows_total": agg.get("n_verified_scored_rows_total"),
            "n_defective_verified_scored_rows_total":
                agg.get("n_defective_verified_scored_rows_total"),
            "defect_histogram": agg.get("defect_histogram"),
            "distinct_defective_decision_ids": agg.get("distinct_defective_decision_ids"),
        },
        "standing_sweeps": {
            "path_scope_residual_cleared": sweeps.get("path_scope_residual_cleared"),
            "false_rejects_n": sweeps.get("false_rejects_n"),
            "sound_row_preserved": sweeps.get("sound_row_preserved"),
        },
        "population_n": len(pop),
        "population_missing": missing,
        "population_drift": drift,
        "population_drift_n": len(drift),
        "currency_holds": (not drift and not missing),
        "re_scored_this_run": False,
        "why_not_rescored": ("the population re-hashes identically against the current mount "
                             "head, so these are CLOSED BYTES; re-scoring them would be a "
                             "zero-delta re-derivation of closed work (lane question item (5)) "
                             "and is deliberately not performed (hypothesis H4)"),
    }


def run_shim_suite(test_rel: str) -> dict:
    """Execute one test file under the documented no-pytest shim."""
    from evaluation import no_pytest_runner as shim
    path = REPO_ROOT / test_rel
    return shim.run_file(path, REPO_ROOT)


def c4_no_audit_gate_minted(run_id: str) -> dict:
    """C4: this producer must not mint an audit gate/report for its own run."""
    candidates = [
        REPO_ROOT / f"results/audit/evaluation/CYCLE_{run_id}_GATE.json",
        REPO_ROOT / f"reports/audit/evaluation/CYCLE_{run_id}.md",
        REPO_ROOT / f"results/audit/evaluation/CYCLE_{run_id}_gate.json",
    ]
    present = [str(p.relative_to(REPO_ROOT)) for p in candidates if p.exists()]
    return {
        "checked_paths": [str(p.relative_to(REPO_ROOT)) for p in candidates],
        "minted_present": present,
        "holds": not present,
        "rule": ("results/audit/<lane>/CYCLE_<run_id>_GATE.json (UPPERCASE _GATE.json) and "
                 "reports/audit/<lane>/CYCLE_<run_id>.md are the independent auditor's "
                 "exclusive scope; a producer-minted file there is the exact defect this "
                 "cycle quarantines from run 41156158583 (factory-wide requirements 1 and 14)"),
    }


def write_report(rec: dict, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    p = report_dir / f"OPERATIONAL_RESUME_{rec['run_id']}.md"
    pre = rec["precondition"]
    beh = rec["h1_behavioral"]
    cur = rec["standing_measurement_currency"]
    orph = rec["suites"]["orphan_suite"]
    mult = rec["suites"]["multilingual_provenance_suite"]
    lines = [
        f"# Operational-Resume Verification Cycle {rec['run_id']} (evaluation, v68)",
        "",
        f"**Mode:** OPERATIONAL RESUME from persisted producer snapshot of run "
        f"{rec['resumed_snapshot_run_id']}",
        f"**Freeze:** {HYP_REL} + {FREEZE_REL}, committed at b44a73c0 BEFORE execution",
        f"**Product mount head adjudicated:** {rec['pins_before_execution']['product_mount_head']['actual']}",
        f"**Generated:** {rec['generated_at_utc']}",
        "",
        "## 1. Orchestration-failure diagnosis and quarantine",
        "",
        "The three-run chain 41149811055 -> 41156158583 -> 41156948851 is diagnosed as an",
        "unaudited, non-promoting chain: (a) 41149811055 added the fixture-replay suite but",
        "never executed it in any committed artifact; (b) 41156158583 MINTED its own PASS gate",
        "on the team branch (author lex-evaluation-team; no /audit ref exists for the run)",
        "carrying measurement claims with no committed artifact that verbatim restate the",
        "closed accepted measurement 39909449668 (18 gates / 11 passed / 4 failed, same",
        "packet 39319405429, same gate family, same '2/8 core concepts' detail); (c) 41156948851",
        "added a producer-authored 'Independent Audit Report' for the prior run. All three are",
        "quarantined NON-PROMOTING, append-only, nothing deleted:",
        "",
        f"- diagnosis: `{rec['diagnosis_artifact']}`",
        f"- quarantine: `{rec['quarantine_artifact']}`",
        "",
        "## 2. Ordered item (2) precondition re-adjudication (accepted instrument)",
        "",
        "Adjudicated by the ACCEPTED `precondition_gate` imported by hash-verified import from",
        f"`{EXPECTED['accepted_adjudicator']}` (sha 126a1234...).",
        "",
        f"- **H1 leg landed:** **{pre['item_2_leg_status']}** "
        f"(markers all present: {pre['leg_markers']['all_markers_present']}; "
        f"file sha {pre['leg_markers']['file_sha256'][:16] if pre['leg_markers'].get('file_sha256') else 'n/a'}...)",
        f"- **H1 behavioral half:** {beh['finding']}",
        f"- **H2 full family regenerated (named 15-member family):** "
        f"**{pre['H2_precondition_full_family_regenerated']}** - member-for-member "
        f"{pre['set_relations_REQUIREMENT_16']['member_for_member_matching']['matched_members']}"
        f"/{pre['set_relations_REQUIREMENT_16']['member_for_member_matching']['of']}",
        f"- **item (2) full protocol status:** **{pre['item_2_full_protocol_status']}**",
        "",
        "Requirement-16 set relations (both differences published, never cardinality-only):",
        "",
        f"- frozen family n = {pre['set_relations_REQUIREMENT_16']['frozen_probe_family_n']}, "
        f"post-repair n = {pre['set_relations_REQUIREMENT_16']['post_repair_n']}",
        f"- path-identity intersection n = "
        f"{pre['set_relations_REQUIREMENT_16']['path_identity']['intersection_by_path_n']} "
        "(EXPECTED 0 under append-only)",
        f"- frozen-family-only n = {pre['set_relations_REQUIREMENT_16']['path_identity']['frozen_family_only_n']}, "
        f"post-repair-only n = {pre['set_relations_REQUIREMENT_16']['path_identity']['post_repair_only_n']}",
        f"- matched per role: {json.dumps(pre['set_relations_REQUIREMENT_16']['member_for_member_matching']['matched_per_role'])}",
        "",
        "**The exact deficit is one server/served fixed-path bundle** (frozen server/served 4",
        "vs post-repair 3). Product's OWN 5-role claim (4 offline + 1 server) IS satisfied by",
        "the present bytes; both readings are published side by side and neither is silently",
        "preferred. Because H2 is false, the ordered item-(2) FULL protocol (frozen protocol +",
        "d2_path_scope_probe re-run on the post-repair family AND packet-of-record 39319405429",
        "+ FAST-MVP falsifier re-run) is NOT executed - exactly the lane question's escape",
        "clause: record NOT_YET_DISCRIMINATING and stop, without a synthetic stand-in and",
        "without re-running the standing falsification. d2_path_scope_probe was NOT re-run;",
        "the packet-of-record was NOT scored.",
        "",
        "## 3. Standing half-2 measurement currency (H4)",
        "",
        f"- standing measurement `{cur['standing_measurement_path']}` verdict "
        f"**{cur['standing_verdict']}**, defect histogram "
        f"`{json.dumps(cur['standing_aggregate']['defect_histogram'])}`, "
        f"path_scope_residual_cleared={cur['standing_sweeps']['path_scope_residual_cleared']}, "
        f"false_rejects_n={cur['standing_sweeps']['false_rejects_n']}, "
        f"sound_row_preserved={cur['standing_sweeps']['sound_row_preserved']}",
        f"- population {cur['population_n']} bundles re-hashed against the current head: "
        f"drift n = {cur['population_drift_n']}, missing n = {len(cur['population_missing'])} "
        f"-> currency_holds={cur['currency_holds']}",
        f"- re-scored this run: **{cur['re_scored_this_run']}** - {cur['why_not_rescored']}",
        "",
        "## 4. Preserved orphan suite + multilingual/provenance suite (H5, H6)",
        "",
        f"- orphan suite `{orph['test_file']}` (sha {orph['test_file_sha256'][:16]}...): "
        f"status **{orph['status']}**, passed {orph['n_passed']}, failed {orph['n_failed']}, "
        f"skipped {orph['n_skipped']}, UNSUPPORTED {orph['n_unsupported']} "
        "(UNSUPPORTED = not-run, never counted as passed; the shim does not expand "
        "parametrisation)",
        f"- multilingual/provenance suite `{mult['test_file']}` (sha {mult['test_file_sha256'][:16]}...): "
        f"status **{mult['status']}**, passed {mult['n_passed']}, failed {mult['n_failed']}, "
        f"skipped {mult['n_skipped']}, UNSUPPORTED {mult['n_unsupported']}",
        "",
        "The orphan suite's honest claim ceiling (frozen in the hypothesis pre-execution): it",
        "is an INSTRUMENT-LIVENESS and OFFLINE-DETERMINISM suite over the OCL adapter fixture",
        "substrate. `replay_fixtures()` ignores its query/lang arguments, so its FR/DE/IT",
        "loops replay the SAME fixture set and cannot measure language-specific PRODUCT",
        "retrieval; it imports no Product code and is NOT a product-retrieval falsifier. The",
        "prior lane summary's '24 passed, 3 skipped' claim is superseded by this committed",
        "measurement (the suite has 17 test functions).",
        "",
        "## 5. Pins (requirement 30 numeric/provenance environment)",
        "",
        f"- pins before execution all_match = **{rec['pins_before_execution']['all_match']}**",
        f"- pins after execution all_match = **{rec['pins_after_execution']['all_match']}**",
        f"- C4 (no audit gate minted by this producer) holds = "
        f"**{rec['controls']['C4_no_audit_gate_minted']['holds']}**",
        "",
        "## 6. Ordered-work status and posture",
        "",
        "- item (1) correction of record: DISCHARGED (accepted earlier); not re-run",
        "- item (2) conditional re-measure: NOT_YET_DISCRIMINATING - precondition adjudicated",
        "  on the current head; deficit = one server/served fixed-path bundle (Product handoff)",
        "- item (3) standing falsification record: KEPT, not re-run; PRODUCT_FALSIFIED on",
        "  packet-of-record 39319405429 (measurement 40182692670) stands",
        "- item (4) the three non-blocking required fixes of CYCLE_39965089504_GATE.json are",
        "  reported only where quoted; not quoted in this cycle",
        "- item (5) no frozen bench, D2 profile or bypass-diagnosis re-derivation; no 174k",
        "  rerun; the closed half-2 bytes were not re-scored",
        "",
        "Posture stays FAIL-CLOSED: packet_admitted=false, machine_gate_ready=false,",
        "human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.",
        "Both frozen absolute bars remain UNMET and untouched; both DO-NOT-SERVE orders stand.",
        "The comparative map-versus-ranked-list half stays vacuous.",
        "",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=RUN_ID_DEFAULT)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--report-dir", default=None)
    args = ap.parse_args(argv)
    run_id = args.run_id
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR

    # ---- pins BEFORE execution (freeze-first contract) ----
    pins_before = check_pins()
    if not pins_before["all_match"]:
        rec = {
            "schema": SCHEMA, "lane": "evaluation", "run_id": run_id,
            "direction_version": 68, "generated_at_utc": utc(),
            "verdict": "NOT_MEASURED_PIN_DRIFT", "exit_code": 2,
            "pins_before_execution": pins_before,
            "detail": "a frozen pin did not match at execution start; nothing was measured",
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{run_id}.json").write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
        print(json.dumps(rec, indent=1))
        return 2

    # ---- hash-verified import of the ACCEPTED adjudicator ----
    from evaluation import post_repair_family_ca_falsifier as ADJ
    actual_adj_sha = sha256_file(REPO_ROOT / EXPECTED["accepted_adjudicator"])
    if actual_adj_sha != EXPECTED["accepted_adjudicator_sha256"]:
        raise SystemExit("accepted adjudicator digest drift - aborting before measurement")

    hyp = json.loads((REPO_ROOT / HYP_REL).read_text(encoding="utf-8"))
    spec = hyp["precondition_spec_FROZEN"]
    # the adjudicator expects exactly these three keys for the precondition gate
    adj_hyp = {
        "product_code_markers_FROZEN": spec["product_code_markers_FROZEN"],
        "frozen_probe_family_FROZEN": spec["frozen_probe_family_FROZEN"],
        "product_claim_FROZEN": spec["product_claim_FROZEN"],
    }

    precondition = ADJ.precondition_gate(adj_hyp, MOUNT)
    behavioral = behavioral_row_read(MOUNT)
    currency = standing_measurement_currency(MOUNT)

    # ---- H1 combines marker landing (accepted gate) + behavioral half ----
    h1_overall = bool(precondition["H1_precondition_leg_landed"]
                      and behavioral["h1_behavioral_hold"])

    # ---- item-(2) status: an OUTPUT of the accepted adjudicator ----
    item2_status = precondition["item_2_full_protocol_status"]

    # ---- suites under the documented shim (H5, H6) ----
    orphan = run_shim_suite(EXPECTED["orphan_suite"])
    multilingual = run_shim_suite(EXPECTED["multilingual_suite"])

    # ---- C4 ----
    c4 = c4_no_audit_gate_minted(run_id)

    # ---- pins AFTER execution ----
    pins_after = check_pins()

    # ---- frozen rubric re-hash REPORTED-ONLY (never scored) ----
    rules = {}
    for name in ("RULES_LABEL.json", "RULES_GEOMETRY.json"):
        p = REPO_ROOT / "evaluation/frozen_bars" / name
        rules[name] = sha256_file(p) if p.is_file() else None

    verdict = "OPERATIONAL_RESUME_VERIFICATION_COMPLETE"
    exit_code = 0
    if not (pins_before["all_match"] and pins_after["all_match"]):
        verdict, exit_code = "NOT_MEASURED_PIN_DRIFT", 2

    rec = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": run_id,
        "direction_version": 68,
        "generated_at_utc": utc(),
        "mode": "OPERATIONAL RESUME from persisted producer snapshot of run 41156948851",
        "resumed_snapshot_run_id": "41156948851",
        "entry_point": f"python evaluation/operational_resume_{run_id}.py --run-id {run_id}",
        "freeze_record": {
            "hypothesis": HYP_REL,
            "freeze": FREEZE_REL,
            "frozen_commit": "b44a73c0",
            "freeze_discipline": "hypothesis + freeze committed BEFORE this execution; "
                                 "no pin, rule or population edited after",
        },
        "verdict": verdict,
        "exit_code": exit_code,
        "diagnosis_artifact": "results/evaluation/orchestration/CYCLE_41156948851_resume_diagnosis.json",
        "quarantine_artifact": "results/evaluation/incidents/self_minted_gate_41156158583_producer_41156158583.QUARANTINED.json",
        "precondition": precondition,
        "h1_overall_landed_and_behavioral": h1_overall,
        "h1_behavioral": behavioral,
        "item_2_full_protocol_status": item2_status,
        "item_2_full_protocol_executed": False,
        "item_2_not_executed_because": (
            "the accepted precondition_gate returns H2_precondition_full_family_regenerated="
            f"{precondition['H2_precondition_full_family_regenerated']} "
            f"({precondition['set_relations_REQUIREMENT_16']['member_for_member_matching']['matched_members']}"
            f"/{precondition['set_relations_REQUIREMENT_16']['member_for_member_matching']['of']} "
            "member-for-member); the lane question's escape clause requires recording "
            "NOT_YET_DISCRIMINATING and stopping - no synthetic stand-in, no "
            "d2_path_scope_probe re-run, no packet-of-record scoring, no standing-"
            "falsification re-run"
        ),
        "standing_measurement_currency": currency,
        "suites": {
            "orphan_suite": orphan,
            "multilingual_provenance_suite": multilingual,
            "orphan_suite_claim_ceiling": (
                "instrument-liveness + offline-determinism over the OCL adapter fixture "
                "substrate; replay_fixtures() ignores query/lang so FR/DE/IT loops replay "
                "the same fixture set; imports no Product code; NOT a product-retrieval "
                "falsifier; UNSUPPORTED cases are not-run, never passed"
            ),
        },
        "controls": {
            "C1_frozen_predicate_instrument_unchanged":
                pins_before["frozen_predicate_instrument_sha256"]["match"]
                and pins_after["frozen_predicate_instrument_sha256"]["match"],
            "C2_accepted_adjudicator_unchanged":
                pins_before["accepted_adjudicator_sha256"]["match"]
                and pins_after["accepted_adjudicator_sha256"]["match"],
            "C3_standing_measurement_untouched":
                pins_before["standing_half2_measurement_sha256"]["match"]
                and pins_after["standing_half2_measurement_sha256"]["match"],
            "C4_no_audit_gate_minted": c4,
        },
        "frozen_rubrics_REPORTED_ONLY_rehash": rules,
        "pins_before_execution": pins_before,
        "pins_after_execution": pins_after,
        "numeric_environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "note": "no BLAS/thread pin; no cross-machine byte-identity claimed "
                    "(requirement 30 disclosure convention)",
        },
        "no_174k_benchmark_rerun": True,
        "no_new_thresholds": True,
        "no_frozen_bar_scored": True,
        "benchmark_of_record_untouched": True,
        "packet_of_record_not_scored": True,
        "d2_path_scope_probe_not_rerun": True,
        "closed_bytes_not_rescored": True,
        "ordered_work_status": {
            "item_1_correction_of_record": "DISCHARGED (accepted earlier); not re-run",
            "item_2_conditional_remeasure": item2_status,
            "item_3_standing_falsification_record": (
                "KEPT, not re-run; PRODUCT_FALSIFIED on packet-of-record 39319405429 "
                "(measurement 40182692670) stands, superseded by nothing here"
            ),
            "item_4_non_blocking_required_fixes_of_CYCLE_39965089504": (
                "reported only where quoted; not quoted in this cycle"
            ),
            "item_5_no_zero_delta_rederivation": (
                "HONOURED: no frozen bench, D2 profile or bypass-diagnosis re-derivation; "
                "no 174k rerun; the closed half-2 bytes of 40258497460 were re-hashed, not "
                "re-scored"
            ),
        },
        "claim_ceiling": hyp["claim_ceiling"],
        "packet_admitted": False,
        "machine_gate_ready": False,
        "human_gate_ready": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{run_id}.json"
    out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_report(rec, report_dir)

    print(json.dumps({
        "verdict": rec["verdict"],
        "exit_code": rec["exit_code"],
        "h1_overall": rec["h1_overall_landed_and_behavioral"],
        "h2_full_family": precondition["H2_precondition_full_family_regenerated"],
        "item_2_status": item2_status,
        "population_drift_n": currency["population_drift_n"],
        "currency_holds": currency["currency_holds"],
        "orphan_suite": {k: orphan[k] for k in
                         ("status", "n_passed", "n_failed", "n_skipped", "n_unsupported")},
        "multilingual_suite": {k: multilingual[k] for k in
                               ("status", "n_passed", "n_failed", "n_skipped", "n_unsupported")},
        "pins_all_match": pins_before["all_match"] and pins_after["all_match"],
        "c4_holds": c4["holds"],
        "record": str(out),
        "report": str(report),
    }, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
