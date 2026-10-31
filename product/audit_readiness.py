#!/usr/bin/env python3
"""Bounded audit-readiness dossier for a resumed product snapshot.

Why this exists
---------------
Run 40196023042's producer finished cleanly and persisted a real delta, but its
independent audit died at ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` (exit 78)
before writing a gate.  The next auditor should not have to spend its own
quantum rediscovering the slice, the accepted pointer or which artifacts are
claim-bearing.  This module gives it one command that re-derives the snapshot's
claims on bounded inputs and records the exact evidence.

What it does
------------
* runs the product-owned state contract;
* checks the fail-closed posture and the accepted pointer;
* re-classifies the resumed run from its committed run/jobs snapshot;
* verifies the resumed run's committed diagnosis (quantum expiry, durable
  delta, unadjudicated status);
* hashes and structurally checks the claim-bearing artifacts (including the
  before/after bytes for the v68 rejection/incumbent leg);
* re-runs the shipped progressive query smoke over a real socket in fixture
  mode (no network, no paid inference);
* runs the bounded MVP core pytest set;
* confirms the producer wrote no auditor-namespace path and minted no gate.

It deliberately does NOT write ``results/audit/**``, mint a gate, score a
frozen bar, re-run a serve verdict, or label any run accepted/rejected.  Its
output is a dossier for the independent auditor, never a verdict.

Usage
-----
    python3 product/audit_readiness.py --run-id 40200882831 \\
        --out results/product/audit_readiness/CYCLE_40200882831_audit_readiness.json

    # fast mode while iterating (skip the two slow re-runs):
    python3 product/audit_readiness.py --run-id X --skip-tests --skip-smoke --out /tmp/x.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "product-audit-readiness/1"
DIRECTION_VERSION = 68
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from product import query_env  # noqa: E402
from product.state_contract import (  # noqa: E402
    accepted_pointer_evidence,
    load_state,
)

ORCH = ROOT / "results" / "product" / "orchestration"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40188639817.json")
# The default profile's pinned family measurement.  A newer profile may pin its
# own artifact/numbers; the report is always REPORTED-ONLY and the frozen
# predicates are never re-derived here.
CONTENT_FAMILY_EXPECTED = {
    "n_bundles": 29,
    "n_decisions": 2900,
    "n_verified": 20,
    "n_verified_defective": 0,
    "false_reject_count": 0,
}
BEFORE_BUNDLE = (ROOT / "results" / "product" / "offline_slice"
                 / "20261024T142517Z" / "rent-default.bundle.json")
AFTER_BUNDLE = (ROOT / "results" / "product" / "offline_slice"
                / "20261025T070356Z" / "rent-default.bundle.json")
STATE = ROOT / "state" / "product.json"

# --- run profiles -------------------------------------------------------
# The dossier was originally pinned to one snapshot (40196023042, resumed by
# 40200882831).  Every later operational resume needs the same bounded
# dossier, so the run-specific facts live in profiles instead of being
# re-derived per cycle.  A profile is selected by the --run-id argument
# (either the resuming run or the resumed snapshot) and falls back to
# ``DEFAULT_PROFILE_KEY`` so the original pinned behaviour is unchanged.
# Everything a profile does NOT override (posture, accepted pointer, frozen
# claim artifacts, MVP test set) is shared by design: those are accepted
# evidence, not per-run facts.
RESUMED_RUN_ID = "40196023042"          # default profile (kept for imports)
PREDECESSOR_RUN_ID = "40193974025"      # default profile (kept for imports)
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
RESUME_DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
# Default lane-cycle log-evidence artifact; the default profile's mechanism is
# an annotation-observed quantum expiry and does not consume it.  Profiles with
# mechanism_kind="observed_log" point at their own artifact.
LANE_CYCLE_LOG_EVIDENCE = (ORCH / "CYCLE_40263666190_lane_cycle_log_evidence.json")
INHERITED_REPORT = ROOT / "reports" / "product" / f"CYCLE_{PREDECESSOR_RUN_ID}.md"
CURRENT_REPORT = ROOT / "reports" / "product" / "CYCLE_40200882831.md"
DEFAULT_PROFILE_KEY = "40196023042"

PROFILES: dict[str, dict[str, Any]] = {
    "40196023042": {
        "resumed_run_id": "40196023042",
        "predecessor_run_id": "40193974025",
        "raw": ORCH / "CYCLE_40196023042_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40196023042_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40193974025.md",
        "current_report": ROOT / "reports" / "product" / "CYCLE_40200882831.md",
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "failed_job": "audit",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 9,
        "changed_paths_include": ("product/audit_step_diagnosis.py",),
        "cycle_test": "product/tests/test_cycle_40200882831.py",
        "state_block": "cycle_40200882831_operational_resume",
    },
    "40200882831": {"alias_of": "40196023042"},
    "40217792931": {
        "resumed_run_id": "40217792931",
        "predecessor_run_id": "40211497166",
        "raw": ORCH / "CYCLE_40217792931_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40217792931_resume_diagnosis.json",
        "inherited_report": None,
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40217792931.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 15,
        "changed_paths_include": ("results/product/offline_slice",),
        "cycle_test": "product/tests/test_cycle_40217792931.py",
        "state_block": "cycle_40217792931_operational_resume",
    },
    "40221519475": {"alias_of": "40217792931"},
    "40257275384": {
        "resumed_run_id": "40257275384",
        "predecessor_run_id": "40254231396",
        "raw": None,
        "resume_diag": ORCH / "CYCLE_40257275384_resume_diagnosis.json",
        "inherited_report": None,
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40257275384.md",
        "classification": "RAW_SNAPSHOT_UNAVAILABLE",
        "mechanism_kind": "unobserved",
        "delta_kind": "zero",
        "failed_job": None,
        "quantum_seconds": None,
        "exit_code": None,
        "changed_files": 0,
        "changed_paths_include": (),
        "cycle_test": "product/tests/test_cycle_40257275384.py",
        "state_block": "cycle_40257275384_operational_resume",
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
        "replay_summary": ROOT / "results" / "product" / "live_cache_replay"
                          / "CYCLE_40257275384" / "summary.json",
        "query_map_diagnosis": ROOT / "results" / "product"
                               / "query_map_diagnosis"
                               / "CYCLE_40257275384.json",
    },
    "40257469937": {
        "resumed_run_id": "40257469937",
        "predecessor_run_id": "40257275384",
        "raw": None,
        "resume_diag": ORCH / "CYCLE_40257469937_resume_diagnosis.json",
        "inherited_report": None,
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40257275384.md",
        "classification": "RAW_SNAPSHOT_UNAVAILABLE",
        "mechanism_kind": "unobserved",
        "delta_kind": "committed",
        "failed_job": "team",
        "quantum_seconds": None,
        "exit_code": None,
        "changed_files": 12,
        "changed_paths_include": ("product/live_cache_replay.py",),
        "cycle_test": "product/tests/test_cycle_40257275384.py",
        "state_block": "cycle_40257469937_operational_resume",
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
        "replay_summary": ROOT / "results" / "product" / "live_cache_replay"
                          / "CYCLE_40257275384" / "summary.json",
        "query_map_diagnosis": ROOT / "results" / "product"
                               / "query_map_diagnosis"
                               / "CYCLE_40257275384.json",
    },
    "40259640985": {
        "resumed_run_id": "40257469937",
        "predecessor_run_id": "40257275384",
        "raw": None,
        "resume_diag": ORCH / "CYCLE_40257469937_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40257275384.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40259640985.md",
        "classification": "RAW_SNAPSHOT_UNAVAILABLE",
        "mechanism_kind": "unobserved",
        "delta_kind": "committed",
        "failed_job": "team",
        "quantum_seconds": None,
        "exit_code": None,
        "changed_files": 12,
        "changed_paths_include": ("product/live_cache_replay.py",),
        "cycle_test": "product/tests/test_cycle_40259640985_resume.py",
        "state_block": "cycle_40259640985_operational_resume",
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
        "replay_summary": ROOT / "results" / "product" / "live_cache_replay"
                          / "CYCLE_40257275384" / "summary.json",
        "query_map_diagnosis": ROOT / "results" / "product"
                               / "query_map_diagnosis"
                               / "CYCLE_40257275384.json",
    },
    "40263666190": {
        "resumed_run_id": "40263483436",
        "predecessor_run_id": "40263308953",
        "raw": ORCH / "CYCLE_40263483436_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_40263483436_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40259640985.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40263666190.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        # Third mechanism kind: the logs endpoint answered HTTP 200, no work
        # quantum was reached, and the log-level cause is a model-gateway
        # request rejection classified by the lane-cycle log-evidence
        # artifact below.  The default kinds (quantum expiry / unobserved)
        # would both misreport this run.
        "mechanism_kind": "observed_log",
        "lane_cycle_log_evidence": ORCH
                                   / "CYCLE_40263666190_lane_cycle_log_evidence.json",
        "lane_cycle_classification": "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER",
        "upstream_signature": "unsupported_parameter",
        "upstream_detail": "Unrecognized request argument supplied: permissions.",
        "failed_step_seconds": 16.0,
        "mechanism_chain_note": (
            "The same log-evidence artifact records the two other attempts on "
            "this tree: 40263308953 hit the identical gateway rejection, and "
            "40262401687's agent hit the missing query runtime, exited 0 with "
            "an unchanged tree after ~526 s, and was rejected by the wrapper's "
            "zero-delta guard (LEX_ZERO_DELTA_REPAIR, exit 67; "
            "quantum_expired=false) - the runtime that this resume repairs."
        ),
        "delta_kind": "zero",
        "failed_job": "team",
        "quantum_seconds": None,
        "exit_code": 1,
        "changed_files": 0,
        "changed_paths_include": (),
        "cycle_test": "product/tests/test_cycle_40263666190_resume.py",
        "state_block": "cycle_40263666190_operational_resume",
        # No new counter-content family was measured this cycle; the accepted
        # pins from the last verified family run are consumed unchanged.
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
        "replay_summary": ROOT / "results" / "product" / "live_cache_replay"
                          / "CYCLE_40257275384" / "summary.json",
        "query_map_diagnosis": ROOT / "results" / "product"
                               / "query_map_diagnosis"
                               / "CYCLE_40257275384.json",
    },
    "40234815780": {
        "resumed_run_id": "40234815780",
        "predecessor_run_id": "40230559317",
        "raw": ORCH / "CYCLE_40234815780_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40234815780_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40230559317.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40234815780.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 8,
        "changed_paths_include": (
            "product/tests/test_counter_content_rejection_v68.py",
            "results/product/repair_40234815780/",
        ),
        "cycle_test": "product/tests/test_cycle_40234815780_resume.py",
        "state_block": "cycle_40234815780_operational_resume",
        # This resume's family artifact is newer than the default profile's.
        # Both are valid REPORTED-ONLY measurements; the profile pins the one
        # the current run's audit should consume, not a re-derived number.
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40230559317.json",
        "content_family_expected": {
            "n_bundles": 43,
            "n_decisions": 4300,
            "n_verified": 44,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "40284658455": {
        "resumed_run_id": "40283048553",
        "predecessor_run_id": "40278460732",
        "raw": ORCH / "CYCLE_40283048553_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_40283048553_resume_diagnosis.json",
        # No report was committed by the failed run; the report of record for
        # this resume is its own CYCLE_40284658455.md, and the last committed
        # producer report on the lineage is 40272586794's.
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40272586794.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40284658455.md",
        "classification": "TEAM_JOB_SCOPE_ENFORCEMENT_FAILED_NO_GATE",
        # Fourth real failure mode: the lane-cycle step SUCCEEDED and the
        # team job died at write-scope enforcement because the producer
        # minted results/audit/product/CYCLE_40278460732_GATE.json (a path
        # outside the producer allowlist).  Neither the quantum-expiry kind
        # nor the model-gateway kind describes it; both would misreport.
        "mechanism_kind": "observed_scope",
        "failed_job": "team",
        "quantum_seconds": None,
        "exit_code": 3,
        "lane_cycle_step_seconds": 827.0,
        "changed_files": 2,
        "changed_paths_include": (
            "results/audit/product/CYCLE_40278460732_GATE.json",
            "state/product.json",
        ),
        "cycle_test": "product/tests/test_cycle_40284658455.py",
        "state_block": "cycle_40284658455_operational_resume",
        # No new counter-content family this cycle: consume the accepted
        # fixed-path family pins unchanged (REPORTED-ONLY).
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
        "self_minted_gate": ROOT / "results" / "product" / "incidents"
                             / "self_minted_gate_40278460732_producer_"
                               "40283048553.QUARANTINED.json",
    },
    "41152471808": {
        "resumed_run_id": "41149776023",
        "predecessor_run_id": "40284658455",
        "raw": ORCH / "CYCLE_41149776023_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_41149776023_resume_diagnosis.json",
        # The failed run committed no report.  The report of record inherited by
        # this resume is the accepted producer report on the lineage; this
        # resume's own report is CYCLE_41152471808.md.
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40284658455.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_41152471808.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        # Fifth real failure mode: the LANE-CYCLE STEP ITSELF failed (not the
        # audit job, not write-scope enforcement, not a model-gateway
        # rejection).  The jobs snapshot is public, the step conclusions are
        # observable, the logs endpoint answers HTTP 403, no work quantum was
        # reached, and the team ref is byte-identical to the accepted base.
        "mechanism_kind": "observed_step_failure",
        "delta_kind": "zero",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": None,
        "lane_cycle_step_seconds": 1670.0,
        "changed_files": 0,
        "changed_paths_include": (),
        "cycle_test": "product/tests/test_cycle_41152471808.py",
        "state_block": "cycle_41152471808_operational_resume",
        # No new counter-content family was measured this cycle: consume the
        # accepted fixed-path family pins unchanged (REPORTED-ONLY).
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "41159331087": {
        "resumed_run_id": "41159162128",
        "predecessor_run_id": "41152471808",
        "raw": ORCH / "CYCLE_41159162128_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_41159162128_resume_diagnosis.json",
        # The resumed run 41159162128 committed no report (it died 17 s in), and
        # the predecessor 41152471808's own report is the record of the audit-
        # quantum death that left the snapshot unadjudicated.  Both are inherited;
        # this resume's report is CYCLE_41159331087.md.
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_41152471808.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_41159331087.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        # Sixth real failure mode, same shape as the fifth (41149776023) but with
        # an OBSERVED exit code: the LANE-CYCLE STEP failed 17 s in with exit
        # code 1, the logs endpoint is HTTP 403 for the reader, no work quantum
        # was reached, and the team ref is byte-identical to the accepted
        # snapshot.  Exit code 1 is not one of the wrapper's own named codes, so
        # it is reported as a generic passthrough with the innermost cause
        # UNOBSERVED; no model defect is asserted.
        "mechanism_kind": "observed_step_failure",
        "delta_kind": "zero",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 1,
        "lane_cycle_step_seconds": 17.0,
        "changed_files": 0,
        "changed_paths_include": (),
        "cycle_test": "product/tests/test_cycle_41159331087.py",
        "state_block": "cycle_41159331087_operational_resume",
        # No new counter-content family was measured this cycle: consume the
        # accepted fixed-path family pins unchanged (REPORTED-ONLY).
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "41162767461": {
        "resumed_run_id": "41162767461",
        "predecessor_run_id": "41159331087",
        "raw": ORCH / "CYCLE_41162767461_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_41162767461_resume_diagnosis.json",
        # The predecessor snapshot 41159331087 never wrote its own report: its
        # lane-cycle step died of quantum expiry at 2704 s and the workflow's
        # if: always() snapshot step committed the working tree.  This resume
        # restores that report of record (under its own run id, with an
        # authoring-correction header) and writes its own report.
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_41159331087.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_41163295014.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        # Seventh observed instance, same step-failure shape as 41149776023
        # and 41159162128 but with the wrapper's OWN zero-delta branch: the
        # lane-cycle step failed after 301 s and the public check-run
        # annotation carries exit code 67 AND the literal branch name
        # LEX_ZERO_DELTA_REPAIR.  The agent committed nothing (team ref is
        # byte-identical to the predecessor snapshot), the logs endpoint is
        # HTTP 403, and no innermost model cause is asserted.
        "mechanism_kind": "observed_step_failure",
        "delta_kind": "zero",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 67,
        "exit_code_meaning": "LEX_ZERO_DELTA_REPAIR",
        "lane_cycle_step_seconds": 301.0,
        "changed_files": 0,
        "changed_paths_include": (),
        "cycle_test": "product/tests/test_cycle_41163295014.py",
        "state_block": "cycle_41163295014_operational_resume",
        # No new counter-content family was measured this cycle: consume the
        # accepted fixed-path family pins unchanged (REPORTED-ONLY).
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "41168007766": {
        "resumed_run_id": "41168007766",
        "predecessor_run_id": "41163295014",
        "raw": ORCH / "CYCLE_41168007766_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_41168007766_resume_diagnosis.json",
        # The predecessor snapshot 41163295014 wrote its own report of record
        # (reports/product/CYCLE_41163295014.md), so there is NO inherited
        # report to hash; explicitly None prevents the shared default from
        # pulling an unrelated legacy report into this cycle's claim set.
        "inherited_report": None,
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_41168174298.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        # Eighth observed instance of the same step-failure shape. Unlike the
        # 41162767461 profile, the public annotation carries the GENERIC exit
        # code 1 (no wrapper branch name): the step ran 16 s, the logs endpoint
        # is HTTP 403, and no innermost cause is asserted. exit_code_meaning is
        # deliberately omitted so the dossier cannot imply a named branch.
        "mechanism_kind": "observed_step_failure",
        "delta_kind": "zero",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 1,
        "lane_cycle_step_seconds": 16.0,
        "changed_files": 0,
        "changed_paths_include": (),
        "cycle_test": "product/tests/test_cycle_41168174298.py",
        "state_block": "cycle_41168174298_operational_resume",
        # No new counter-content family was measured this cycle: consume the
        # accepted fixed-path family pins unchanged (REPORTED-ONLY).
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "41172772289": {
        "resumed_run_id": "41172772289",
        "predecessor_run_id": "41168174298",
        "raw": ORCH / "CYCLE_41172772289_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_41172772289_resume_diagnosis.json",
        # The predecessor 41168174298 wrote its own report of record, so this
        # profile inherits no report; None keeps the shared default from
        # pulling an unrelated legacy report into this run's claim set.
        "inherited_report": None,
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_41172922015.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        # Ninth observed instance of the same step-failure shape, and the same
        # generic exit 1 as 41168007766 / 41159162128: 16 s, no wrapper branch
        # name in the public annotation, logs endpoint HTTP 403, so the
        # innermost cause is UNOBSERVED. exit_code_meaning is deliberately
        # omitted so the dossier cannot imply a named branch.
        "mechanism_kind": "observed_step_failure",
        "delta_kind": "zero",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 1,
        "lane_cycle_step_seconds": 16.0,
        "changed_files": 0,
        "changed_paths_include": (),
        "cycle_test": "product/tests/test_cycle_41172922015.py",
        "state_block": "cycle_41172922015_operational_resume",
        # Ordered-work consumption only: the accepted fixed-path family pins
        # are read REPORTED-ONLY; nothing is re-measured this cycle.
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "41176811677": {
        "resumed_run_id": "41176811677",
        "predecessor_run_id": "41172922015",
        "raw": ORCH / "CYCLE_41176811677_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_41176811677_resume_diagnosis.json",
        # The resumed run 41176811677 committed no report (its lane-cycle step
        # died at the work quantum).  The last producer report on the resume
        # lineage is the predecessor's, and this resume's report is its own.
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_41172922015.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_41179957652.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        # Tenth observed instance, and the FIRST producer-side work-quantum
        # expiry on this lineage: the lane-cycle step ran 2705 s of a 2700 s
        # quantum and the public check-run annotation carries the literal
        # branch LEX_WORK_QUANTUM_EXPIRED seconds=2700 with exit code 78.
        # This is mechanism_kind="observed" (annotation-observed quantum
        # expiry), not "observed_step_failure": the 403 logs endpoint does not
        # matter because the quantum is stated by the annotation itself.
        "mechanism_kind": "observed",
        "delta_kind": "zero",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 0,
        "changed_paths_include": (),
        "cycle_test": "product/tests/test_cycle_41179957652.py",
        "state_block": "cycle_41179957652_operational_resume",
        # Ordered-work consumption only: the accepted fixed-path family pins
        # are read REPORTED-ONLY; nothing is re-measured this cycle.
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "41188733592": {
        "resumed_run_id": "41188733592",
        "predecessor_run_id": "41184474509",
        "raw": ORCH / "CYCLE_41188733592_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_41188733592_resume_diagnosis.json",
        # Neither 41184474509 nor 41188733592 committed a report.  The last
        # producer report on the lineage is 41179957652's, and this resume's
        # report is its own.
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_41179957652.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_41188877123.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        # Eleventh observed instance of the generic immediate step failure: the
        # lane-cycle step ran 17 s of a 2700 s quantum and exited 1 with no
        # wrapper branch name in the public annotation.  The logs endpoint is
        # HTTP 403, so the innermost cause stays UNOBSERVED and none is
        # asserted.  The predecessor 41184474509 DID commit a delta (its
        # audit-readiness artifact only) but its audit job then died at
        # LEX_WORK_QUANTUM_EXPIRED 2705 s / exit 78 with the gate reader
        # skipped, which is why the snapshot is unaudited rather than rejected.
        "mechanism_kind": "observed_step_failure",
        "delta_kind": "zero",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 1,
        "lane_cycle_step_seconds": 17.0,
        "changed_files": 0,
        "changed_paths_include": (),
        "cycle_test": "product/tests/test_cycle_41188877123.py",
        "state_block": "cycle_41188877123_operational_resume",
        # Ordered-work consumption only: the accepted fixed-path family pins
        # are read REPORTED-ONLY; nothing is re-measured this cycle.
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "41193519633": {
        "resumed_run_id": "41193519633",
        "predecessor_run_id": "41193345044",
        "raw": ORCH / "CYCLE_41193519633_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_41193519633_resume_diagnosis.json",
        # Neither 41193345044 nor 41193519633 committed anything (both team
        # refs are 98ca6621), so the last producer report on the lineage is
        # 41188877123's, and this resume's report is its own.
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_41188877123.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_41193662357.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        # Twelfth and thirteenth observed instances of the same immediate
        # lane-cycle step failure: both runs' lane-cycle step ran 16.0 s of a
        # 2700 s quantum and exited 1 with no wrapper branch name in the
        # public annotation, then state validation, write-scope enforcement,
        # audit and integrate were all skipped.  The logs endpoint answered
        # HTTP 403 "Must have admin rights to Repository." to this reader
        # (re-probed this cycle), so the log-level cause stays UNOBSERVED and
        # no cause is asserted.  The only OBSERVED mechanism with this exact
        # signature in this lane remains run 40263308953's model-gateway
        # request rejection (CYCLE_40263666190_lane_cycle_log_evidence.json);
        # it is a cited precedent, NOT an attribution for these two runs.
        "mechanism_kind": "observed_step_failure",
        "delta_kind": "zero",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 1,
        "lane_cycle_step_seconds": 16.0,
        "changed_files": 0,
        "changed_paths_include": (),
        "cycle_test": "product/tests/test_cycle_41193662357.py",
        "state_block": "cycle_41193662357_operational_resume",
        # Ordered-work consumption only: the accepted fixed-path family pins
        # are read REPORTED-ONLY; nothing is re-measured this cycle.
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "41193662357": {
        # First profile in this chain whose PRODUCER job fully succeeded and
        # whose AUDIT job then expired: the team job and both producer gates
        # passed, 15 files were committed over 98ca6621, and the independent
        # audit ran 2704.0 s of the 2700 s quantum before the wrapper returned
        # exit 78 (public annotation "LEX_WORK_QUANTUM_EXPIRED seconds=2700").
        # The durable delta is COMMITTED, not zero, so the run is a resumable
        # snapshot rather than a dead producer step.
        "resumed_run_id": "41193662357",
        "predecessor_run_id": "41193519633",
        "raw": ORCH / "CYCLE_41193662357_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_41193662357_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_41188877123.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_41193662357.md",
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "mechanism_kind": "observed",
        "delta_kind": "committed",
        "failed_job": "audit",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 15,
        "changed_paths_include": ("product/audit_readiness.py",
                                  "reports/product/CYCLE_41193662357.md"),
        "cycle_test": "product/tests/test_cycle_41193662357.py",
        "state_block": "cycle_41193662357_operational_resume",
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "41199556067": {
        # Self-dossier for the run that resumes 41193662357.  Every previous
        # audit in this chain looked for a dossier about the run whose snapshot
        # it was auditing, found only a dossier about the run that snapshot had
        # resumed, and burned the 2700 s quantum re-deriving the work.  This
        # profile makes `--run-id 41199556067` publish the audited run's own
        # report, cycle test and bounded plan while still cross-checking the
        # resumed run's diagnosis.
        "resumed_run_id": "41193662357",
        "predecessor_run_id": "41193519633",
        "raw": ORCH / "CYCLE_41193662357_team_step_raw.json",
        "resume_diag": ORCH / "CYCLE_41193662357_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_41193662357.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_41199556067.md",
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "mechanism_kind": "observed",
        "delta_kind": "committed",
        "failed_job": "audit",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 15,
        "changed_paths_include": ("product/audit_readiness.py",
                                  "reports/product/CYCLE_41193662357.md"),
        "cycle_test": "product/tests/test_cycle_41199556067.py",
        "state_block": "cycle_41199556067_operational_resume",
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40257275384.json",
        "content_family_expected": {
            "n_bundles": 49,
            "n_decisions": 4900,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    # No profile for 41193345044 on purpose: it is the predecessor in this
    # chain, not a dossier subject.  select_profile() fails closed on unknown
    # ids, and aliasing it here would publish 41193519633's claims under
    # 41193345044's id - the exact defect the fail-closed rule exists to stop.
}

# Active profile; empty means "the module constants above" (the original
# pinned run).  Set by run()/select_profile() only.
PROFILE: dict[str, Any] = {}


def select_profile(run_id: str) -> dict[str, Any]:
    """Resolve the dossier profile for ``run_id`` (aliases are followed).

    A dossier for the wrong run is worse than no dossier: it would re-derive
    another run's claims and label them with this run's id.  Unknown run ids
    therefore fail closed instead of silently inheriting the default profile.
    """
    key = str(run_id)
    prof = PROFILES.get(key)
    while isinstance(prof, dict) and "alias_of" in prof:
        prof = PROFILES.get(str(prof["alias_of"]))
    if prof is None:
        raise SystemExit(
            f"no audit-readiness profile for run {key}; refusing to fall back "
            f"to {DEFAULT_PROFILE_KEY} and publish another run's claims")
    return dict(prof)


def p(field: str, default: Any = None) -> Any:
    """Profile field with a fallback to the pinned module constants."""
    if field in PROFILE:
        return PROFILE[field]
    return default


def _report_paths() -> list[Path]:
    out = []
    for value in (p("inherited_report", INHERITED_REPORT),
                  p("current_report", CURRENT_REPORT)):
        if value is not None:
            out.append(Path(value))
    return out

MVP_CORE_TESTS = (
    "product/tests/test_query_map_mvp.py",
    "product/tests/test_server_query_api.py",
    "product/tests/test_offline_slice.py",
    "product/tests/test_progressive_smoke.py",
    "product/tests/test_adversarial_retrieval.py",
    "product/tests/test_counter_evidence_span.py",
    "product/tests/test_counter_content_rejection_v68.py",
    "product/tests/test_state_contract.py",
    "product/tests/test_progressive_query.py",
)

STATE_TIMEOUT_S = 180
SMOKE_TIMEOUT_S = 240
PYTEST_TIMEOUT_S = 600
D2_DECISION = "gr_gerichte_ERZ 2010 25"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str], timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                              text=True, timeout=timeout, check=False)
        return {
            "command": " ".join(cmd),
            "exit_code": proc.returncode,
            "seconds": round(time.monotonic() - started, 3),
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(cmd),
            "exit_code": None,
            "seconds": round(time.monotonic() - started, 3),
            "stdout_tail": (exc.stdout or b"").decode("utf-8", "replace")[-4000:]
            if isinstance(exc.stdout, bytes) else (exc.stdout or "")[-4000:],
            "stderr_tail": (exc.stderr or b"").decode("utf-8", "replace")[-4000:]
            if isinstance(exc.stderr, bytes) else (exc.stderr or "")[-4000:],
            "timed_out": True,
        }


def _check(check_id: str, title: str, ok: bool, detail: Any,
           evidence: list[str] | None = None,
           command: str | None = None, seconds: float | None = None,
           mandatory: bool = True) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": "PASS" if ok else "FAIL",
        "mandatory": mandatory,
        "detail": detail,
        "evidence": evidence or [],
        "command": command,
        "seconds": seconds,
    }


def _skip(check_id: str, title: str, reason: str,
          mandatory: bool = False) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": "SKIP",
        "mandatory": mandatory,
        "detail": reason,
        "evidence": [],
        "command": None,
        "seconds": None,
    }


def check_state_contract() -> dict[str, Any]:
    cmd = [sys.executable, "product/state_contract.py", "--check",
           "--direction-version", str(DIRECTION_VERSION), "--json"]
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                              text=True, timeout=STATE_TIMEOUT_S, check=False)
        exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - defensive
        exit_code = None
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        timed_out = True
    seconds = round(time.monotonic() - started, 3)
    report: dict[str, Any] = {}
    if stdout.strip():
        try:
            report = json.loads(stdout)
        except json.JSONDecodeError:
            report = {}
    ok = exit_code == 0 and bool(report.get("ok"))
    detail = {
        "timed_out": timed_out,
        "stderr_tail": stderr[-1000:],
        "workflow_validation": report.get("workflow_validation"),
        "write_scope": report.get("write_scope"),
        "audit_artifact_ownership": {
            "ok": (report.get("audit_artifact_ownership") or {}).get("ok"),
            "producer_wrote_audit_paths": (
                report.get("audit_artifact_ownership") or {}
            ).get("producer_wrote_audit_paths"),
        },
        "shadow_state": report.get("shadow_state"),
    }
    return _check("state_contract",
                  "Canonical state satisfies the workflow contract and lane scope",
                  ok, detail, ["state/product.json", "product/state_contract.py"],
                  " ".join(cmd), seconds)


def check_posture() -> dict[str, Any]:
    st = _load(STATE)
    expected = {
        "lane": "product",
        "direction_version": DIRECTION_VERSION,
        "continue_recommended": True,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
    }
    bad = {k: {"expected": v, "actual": st.get(k)}
           for k, v in expected.items() if st.get(k) != v}
    pointer = accepted_pointer_evidence(st, ROOT)
    ok = not bad and not pointer["problems"]
    return _check(
        "posture",
        "Fail-closed posture and an accepted pointer that still satisfies "
        "both halves of requirement 4",
        ok,
        {"mismatches": bad, "accepted_pointer": pointer},
        ["state/product.json"],
    )


def check_resumed_diagnosis() -> dict[str, Any]:
    raw = Path(p("raw")) if p("raw") else None
    resume_diag = Path(p("resume_diag", RESUME_DIAG))
    resumed_id = p("resumed_run_id", RESUMED_RUN_ID)
    predecessor = p("predecessor_run_id", PREDECESSOR_RUN_ID)
    classification = p("classification", "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    failed_job = p("failed_job", "audit")
    mechanism_kind = p("mechanism_kind", "observed")
    delta_kind = p("delta_kind", "committed")
    diag = _load(resume_diag)
    orch = diag.get("orchestration") or {}
    delta = diag.get("durable_delta") or {}
    adj = diag.get("adjudication") or {}
    problems = []
    if diag.get("run_id") != resumed_id:
        problems.append("run_id")
    if diag.get("predecessor_run_id") != predecessor:
        problems.append("predecessor_run_id")
    if orch.get("classification") != classification:
        problems.append("classification")

    if mechanism_kind == "observed":
        mechanism = orch.get("mechanism") or {}
        quantum_seconds = p("quantum_seconds", 2700)
        exit_code = p("exit_code", 78)
        if mechanism.get("status") != "OBSERVED_QUANTUM_EXPIRED":
            problems.append("mechanism_status")
        if mechanism.get("quantum_expired") is not True:
            problems.append("quantum_expired")
        if mechanism.get("quantum_seconds") != quantum_seconds:
            problems.append("quantum_seconds")
        if mechanism.get("exit_code") != exit_code:
            problems.append("exit_code")
        if (orch.get("audit") or {}).get("gate_file_written") is not False:
            problems.append("gate_file_written")
    elif mechanism_kind == "observed_log":
        # Third real-world failure mode, observed on runs 40263308953 and
        # 40263483436: the logs endpoint answered HTTP 200, the committed job
        # logs show the agent NEVER reached the work quantum, and the log-level
        # cause (a model-gateway rejection) is classified by the lane-cycle
        # log-evidence artifact rather than by check-run annotations.  A
        # dossier that could only say "quantum expiry" or "unobserved" would
        # misreport this run either way, so the third kind is first-class and
        # cross-checked against the evidence file it names.
        mechanism = orch.get("mechanism") or {}
        quantum_seconds = None
        exit_code = p("exit_code")
        if mechanism.get("status") != "OBSERVED_LOGS_AVAILABLE_NO_QUANTUM":
            problems.append("mechanism_status")
        if mechanism.get("logs_available") is not True:
            problems.append("logs_available")
        if mechanism.get("logs_endpoint_status") != 200:
            problems.append("logs_endpoint_status")
        if mechanism.get("quantum_expired") is not False:
            problems.append("quantum_expired")
        if (orch.get("audit") or {}).get("gate_file_written") is not False:
            problems.append("gate_file_written")
        evidence_path = Path(p("lane_cycle_log_evidence",
                               LANE_CYCLE_LOG_EVIDENCE))
        log_ev = _load(evidence_path) if evidence_path.is_file() else {}
        entry = (log_ev.get("runs") or {}).get(resumed_id) or {}
        if (entry.get("classification")
                != p("lane_cycle_classification",
                     "MODEL_UPSTREAM_REJECTED_REQUEST_PARAMETER")):
            problems.append("lane_cycle_classification")
        codes = entry.get("exit_codes") or []
        if exit_code is not None and exit_code not in codes:
            problems.append("lane_cycle_exit_codes")
        want_sig = p("upstream_signature")
        got_sig = (entry.get("upstream_error") or {}).get("signature")
        if want_sig and got_sig != want_sig:
            problems.append("upstream_signature")
        # The log parser must have separated workflow annotations from text
        # the agent merely *quoted*; a quantum marker seen only as a quote is
        # exactly the misclassification this evidence format exists to stop.
        markers = entry.get("markers") or {}
        if markers.get("quantum_expired") is not False:
            problems.append("log_evidence_quantum_marker")
        if not evidence_path.is_file():
            problems.append("lane_cycle_log_evidence_missing")
    elif mechanism_kind == "observed_scope":
        # Fourth real failure mode, observed on run 40283048553: the
        # lane-cycle agent step SUCCEEDED and the team job died at the
        # workflow's write-scope enforcement because the producer minted an
        # auditor-namespace gate file (results/audit/product/
        # CYCLE_<resumed_run>_GATE.json).  The raw run/jobs snapshot shows
        # the step conclusions directly; no quantum expired and no model
        # gateway was involved.  A quantum or gateway wording would
        # misreport the run, so the scope-enforcement kind is first-class.
        mechanism = orch.get("mechanism") or {}
        quantum_seconds = None
        exit_code = p("exit_code")
        if mechanism.get("status") != "OBSERVED_SCOPE_ENFORCEMENT_FAILED":
            problems.append("mechanism_status")
        if mechanism.get("logs_available") is not True:
            problems.append("logs_available")
        if mechanism.get("logs_endpoint_status") != 200:
            problems.append("logs_endpoint_status")
        if mechanism.get("quantum_expired") is not False:
            problems.append("quantum_expired")
        if mechanism.get("lane_cycle_step_conclusion") != "success":
            problems.append("lane_cycle_step_conclusion")
        if orch.get("failed_step") != "Enforce lane write scope":
            problems.append("failed_step")
        if mechanism.get("exit_code") != exit_code:
            problems.append("exit_code")
        if (orch.get("audit") or {}).get("gate_file_written") is not False:
            problems.append("gate_file_written")
        if (orch.get("audit") or {}).get("skipped") is not True:
            problems.append("audit_not_skipped")
        # Cross-check the raw snapshot the profile names: the lane-cycle
        # step must read success and the scope step failure there too.
        if raw is not None and raw.is_file():
            raw_doc = _load(raw)
            team = next((j for j in raw_doc.get("jobs") or []
                         if j.get("name") == "team"), None)
            steps = {s.get("name"): s.get("conclusion")
                     for s in (team or {}).get("steps") or []}
            if steps.get("Run lane cycle") != "success":
                problems.append("raw_lane_cycle_not_success")
            if steps.get("Enforce lane write scope") != "failure":
                problems.append("raw_scope_step_not_failure")
        else:
            problems.append("raw_snapshot_missing")
    elif mechanism_kind == "observed_step_failure":
        # Fifth real failure mode, observed on run 41149776023: the LANE-CYCLE
        # STEP itself failed (not the audit job, not write-scope enforcement,
        # not a model-gateway rejection).  The public jobs snapshot shows the
        # step conclusion and timestamps; the logs endpoint is HTTP 403 for the
        # reader, so the log-level cause is UNOBSERVED and no cause is asserted.
        # A quantum-expiry or scope wording would misreport the run.
        mechanism = orch.get("mechanism") or {}
        team = orch.get("team") or {}
        exit_code = p("exit_code")
        # Two honest encodings exist for this failure mode.  The enriched
        # resume artfacts say OBSERVED_LANE_CYCLE_STEP_FAILED because the STEP
        # conclusion is observed; the raw audit-step instrument (whose own
        # frozen contract keeps log-level mechanism UNOBSERVED on HTTP 403)
        # emits UNOBSERVED.  Both must carry the same canonical facts, so the
        # check reads the step fact from the team block when the artifact uses
        # the raw encoding instead of requiring a hand-authored alias.
        status = mechanism.get("status")
        if status not in ("OBSERVED_LANE_CYCLE_STEP_FAILED", "UNOBSERVED"):
            problems.append("mechanism_status")
        if mechanism.get("logs_available") is not False:
            problems.append("logs_available")
        if mechanism.get("logs_endpoint_status") != 403:
            problems.append("logs_endpoint_status")
        if mechanism.get("quantum_expired") is not False:
            problems.append("quantum_expired")
        failed_step = orch.get("failed_step") or team.get("failed_step")
        step_conclusion = mechanism.get("lane_cycle_step_conclusion")
        if failed_step == "Run lane cycle" and status == "UNOBSERVED":
            # The raw team block is the canonical record of the step
            # conclusion; a failed step is always selected there.
            step_conclusion = "failure"
        if step_conclusion != "failure":
            problems.append("lane_cycle_step_conclusion")
        if failed_step != "Run lane cycle":
            problems.append("failed_step")
        if mechanism.get("exit_code") != exit_code:
            problems.append("exit_code")
        # When the public annotation also NAMES the wrapper branch (67 =
        # LEX_ZERO_DELTA_REPAIR), the profile may pin that name.  A dossier
        # that recorded only the number would leave the most important fact -
        # the agent committed nothing - to prose.
        if p("exit_code_meaning") is not None and (
                mechanism.get("exit_code_meaning")
                != p("exit_code_meaning")):
            problems.append("exit_code_meaning")
        audit = orch.get("audit") or {}
        if audit.get("gate_file_written") is not False:
            problems.append("gate_file_written")
        audit_skipped = audit.get("skipped")
        if audit_skipped is None:
            audit_skipped = audit.get("conclusion") == "skipped"
        if audit_skipped is not True:
            problems.append("audit_not_skipped")
        # Cross-check the raw snapshot the profile names: the lane-cycle step
        # must read failure there and the two downstream producer steps must
        # read skipped.
        if raw is not None and raw.is_file():
            raw_doc = _load(raw)
            team = next((j for j in raw_doc.get("jobs") or []
                         if j.get("name") == "team"), None)
            steps = {s.get("name"): s.get("conclusion")
                     for s in (team or {}).get("steps") or []}
            if steps.get("Run lane cycle") != "failure":
                problems.append("raw_lane_cycle_not_failure")
            if steps.get("Validate active MVP producer state") != "skipped":
                problems.append("raw_state_validation_not_skipped")
            if steps.get("Enforce lane write scope") != "skipped":
                problems.append("raw_scope_step_not_skipped")
        else:
            problems.append("raw_snapshot_missing")
    else:
        # Raw-free resume: the public run/jobs snapshot is unavailable. The
        # only honest record is that the mechanism is unobserved; asserting a
        # status would invent a cause the committed evidence cannot show.
        quantum_seconds = None
        exit_code = None
        if orch.get("mechanism_unobserved") is not True:
            problems.append("mechanism_unobserved")
        if "mechanism" in orch:
            problems.append("mechanism_asserted_without_raw")
        if orch.get("raw_snapshot") is not None:
            problems.append("raw_snapshot_path_without_file")
        if raw is not None:
            problems.append("raw_profile_points_at_missing_snapshot")

    if delta_kind == "zero":
        changed_files = 0
        if delta.get("classification") != "ZERO_DURABLE_DELTA":
            problems.append("durable_delta")
        if delta.get("changed_files") != 0:
            problems.append("changed_files")
        if not delta.get("snapshot_head") or (
                delta.get("snapshot_head") != delta.get("predecessor_head")):
            problems.append("snapshot_head_not_equal_predecessor")
    else:
        changed_files = p("changed_files", 9)
        if delta.get("classification") != "COMMITTED_DELTA":
            problems.append("durable_delta")
        if delta.get("changed_files") != changed_files:
            problems.append("changed_files")
        paths_sample = delta.get("changed_paths_sample") or []
        for needle in p("changed_paths_include", ()):
            if not any(str(needle) in str(s) for s in paths_sample):
                problems.append(f"changed_paths_include:{needle}")

    if adj.get("status") != "UNADJUDICATED" or adj.get("accepted") is not False:
        problems.append("adjudication")

    if mechanism_kind == "observed":
        who = ("independent-audit" if failed_job == "audit"
               else "lane-cycle (producer)")
        summary = (f"Resumed run {resumed_id}: {who} work-quantum expiry "
                   "observed, durable delta present, run unadjudicated")
    elif mechanism_kind == "observed_log":
        summary = (f"Resumed run {resumed_id}: model-gateway request "
                   "rejection observed in the run's own job logs (no work "
                   "quantum reached), team ref carries zero durable delta "
                   "over its predecessor, run unadjudicated")
    elif mechanism_kind == "observed_scope":
        summary = (f"Resumed run {resumed_id}: lane-cycle agent step "
                   "succeeded, team job failed at write-scope enforcement "
                   "on a producer-minted auditor-namespace gate file (no "
                   "work quantum reached, audit skipped), durable delta "
                   "present, run unadjudicated")
    elif mechanism_kind == "observed_step_failure":
        # Derive the numbers from the profile instead of hard-coding the
        # 41149776023 values: a summary that always says "1670 s" would
        # misreport every later step failure, and this run's step failed at
        # 17 s with an observed exit code of 1.
        step_s = p("lane_cycle_step_seconds")
        exit_code = p("exit_code")
        step_clause = (f"after {step_s} s of a {p('quantum_seconds', 2700)} s quantum"
                       if step_s is not None else "before its work quantum expired")
        exit_clause = (f", exit code {exit_code} observed in the public check-run "
                       "annotation" if exit_code is not None else "")
        if p("exit_code_meaning") is not None:
            exit_clause += f" ({p('exit_code_meaning')})"
        summary = (f"Resumed run {resumed_id}: lane-cycle agent step FAILED "
                   f"{step_clause}{exit_clause}, producer-state validation and "
                   "write-scope enforcement were skipped, the logs endpoint "
                   "answered HTTP 403 (log-level cause unobserved), the team ref "
                   "carries zero durable delta over the accepted base, and the "
                   "run is unadjudicated")
    else:
        summary = (f"Resumed run {resumed_id}: raw run/jobs snapshot "
                   "unavailable (mechanism unobserved), team ref carries zero "
                   "durable delta over its predecessor, run unadjudicated")
    evidence = ([str(raw.relative_to(ROOT))] if raw is not None else [])
    evidence.append(str(resume_diag.relative_to(ROOT)))
    if mechanism_kind == "observed_log":
        ev = Path(p("lane_cycle_log_evidence", LANE_CYCLE_LOG_EVIDENCE))
        if ev.is_file():
            evidence.append(str(ev.relative_to(ROOT)))
    return _check(
        "resumed_diagnosis",
        summary,
        not problems,
        {"problems": problems, "failed_job": failed_job,
         "mechanism_kind": mechanism_kind,
         "delta_kind": delta_kind,
         "audit_step_seconds": (
             (orch.get("audit") or {}).get("independent_audit_step_seconds")),
         "failed_step_seconds": ((orch.get("team") or {}).get(
             "failed_step_seconds")),
         "changed_files": delta.get("changed_files"),
         "changed_paths_sample": delta.get("changed_paths_sample")},
        evidence,
    )


def _row(bundle: dict, decision_id: str) -> dict | None:
    return next((r for r in bundle.get("decisions") or []
                 if r.get("decision_id") == decision_id), None)


def check_claim_artifacts() -> dict[str, Any]:
    cf_path = Path(p("content_family", CONTENT_FAMILY))
    expected = dict(p("content_family_expected", CONTENT_FAMILY_EXPECTED))
    before_bundle = Path(p("before_bundle", BEFORE_BUNDLE))
    after_bundle = Path(p("after_bundle", AFTER_BUNDLE))
    d2_decision = str(p("d2_decision", D2_DECISION))
    raw_path = Path(p("raw")) if p("raw") else None
    paths = [
        cf_path, before_bundle, after_bundle,
        Path(p("resume_diag", RESUME_DIAG)),
        *_report_paths(), STATE,
    ]
    if raw_path is not None:
        paths.insert(3, raw_path)
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.is_file()]
    hashes = {str(p.relative_to(ROOT)): _sha256(p)
              for p in paths if p.is_file()}
    problems: list[str] = []
    detail: dict[str, Any] = {}

    if not problems and cf_path.is_file():
        cf = _load(cf_path)
        fp = (cf.get("fixed_path_family") or {}).get("totals") or {}
        try:
            for key in ("n_bundles", "n_decisions", "n_verified",
                        "n_verified_defective"):
                if fp.get(key) != expected[key]:
                    problems.append(f"fixed_path_family.{key}")
            if any(v != 0 for v in (fp.get("defect_histogram") or {}).values()):
                problems.append("fixed_path_family.defect_histogram")
            if cf.get("false_reject_count") != expected["false_reject_count"]:
                problems.append("false_reject_count")
            if not (cf.get("confirmed_set") or {}).get("still_verified"):
                problems.append("confirmed_sound_row")
            if not (cf.get("ordered_work_2_success_rule") or {}).get("met"):
                problems.append("ordered_work_2_success_rule")
            if not (cf.get("ordered_work_2_full_success_rule") or {}).get("met"):
                problems.append("ordered_work_2_full_success_rule")
            if any((cf.get("frozen_predicate_provenance") or {}).get(k) is None
                   for k in ("predicate_source_sha256", "frozen_hypothesis_sha256")):
                problems.append("frozen_predicate_provenance")
        except (TypeError, AttributeError, KeyError):
            problems.append("content_family_shape")
        detail["content_family"] = {
            "path": str(cf_path.relative_to(ROOT)),
            "expected": expected,
            "n_bundles": fp.get("n_bundles"),
            "n_decisions": fp.get("n_decisions"),
            "n_verified": fp.get("n_verified"),
            "n_verified_defective": fp.get("n_verified_defective"),
            "defect_histogram": fp.get("defect_histogram"),
            "false_reject_count": cf.get("false_reject_count"),
        }

    before = after = None
    if before_bundle.is_file() and after_bundle.is_file():
        before = _row(_load(before_bundle), d2_decision)
        after = _row(_load(after_bundle), d2_decision)
        if before is None:
            problems.append("before_row_missing")
        elif before.get("counter_evidence_verified") is not True:
            problems.append("before_row_not_verified")
        if after is None:
            problems.append("after_row_missing")
        else:
            if after.get("counter_evidence_verified") is not False:
                problems.append("after_row_still_verified")
            if after.get("counter_evidence_unevidenced_reason") != "pivot_absent":
                problems.append("after_row_reason")
        detail["d2_before_after"] = {
            "decision_id": d2_decision,
            "before_verified": (before or {}).get("counter_evidence_verified"),
            "after_verified": (after or {}).get("counter_evidence_verified"),
            "after_reason": (after or {}).get("counter_evidence_unevidenced_reason"),
        }
        for path, bundle in ((before_bundle, before), (after_bundle, after)):
            prov = ((_load(path).get("provenance") or {})
                    .get("counter_evidence_span") or {})
            if prov.get("applied") is not True:
                problems.append(f"{path.name}.span_not_applied")
            if prov.get("n_selected") != 0:
                problems.append(f"{path.name}.n_selected")

    return _check(
        "claim_artifacts",
        "Claim-bearing artifacts exist, hash, and re-derive the v68 "
        "before/after D2 rejection",
        not missing and not problems,
        {"missing": missing, "problems": problems, **detail,
         "sha256": hashes},
        [str(p.relative_to(ROOT)) for p in paths],
    )


def check_runtime_preflight(auto_bootstrap: bool = True) -> dict[str, Any]:
    """Fail closed on the fresh-runner dependency gap before running re-checks.

    ``core-lane.yml`` installs nothing, so a fresh team or audit runner reaches
    the slice with no numpy/sklearn/pytest.  The historical failure mode is
    ``ModuleNotFoundError: No module named 'numpy'`` (see
    ``results/product/reality_check/*missing-deps*.json``), which looks like a
    product defect to an auditor.  This check records the probe, applies the
    lane's own pinned bootstrap when needed, and re-probes.  It never weakens a
    test or a frozen bar; it only makes the runtime explicit.
    """
    before = query_env.probe()
    pytest_before = query_env.installed_version("pytest")
    action: dict[str, Any] | None = None
    after = before
    pytest_after = pytest_before
    if (not before["ok"] or pytest_before is None) and auto_bootstrap:
        action = _run(["bash", "product/bootstrap_query_env.sh"], 600)
        after = query_env.probe()
        pytest_after = query_env.installed_version("pytest")
    ok = bool(after["ok"]) and pytest_after is not None
    return _check(
        "runtime_preflight",
        "Pinned query runtime (numpy/sklearn/pytest) is present, bootstrapped "
        "with the lane's own free PyPI pins when missing",
        ok,
        {
            "before": {"ok": before["ok"], "missing": before["missing"],
                       "installed": before["installed"],
                       "pytest": pytest_before},
            "after": {"ok": after["ok"], "missing": after["missing"],
                      "installed": after["installed"],
                      "pytest": pytest_after},
            "bootstrap": action,
            "pins": dict(query_env.PINNED),
            "remedy": query_env.REMEDY,
            "workflow_gap": after["workflow_gap"],
        },
        ["product/bootstrap_query_env.sh", "product/query_env.py",
         "product/requirements-query.txt"],
        (action or {}).get("command"),
        (action or {}).get("seconds"),
    )


def check_cycle_test(cycle_test: str) -> dict[str, Any]:
    """Run the cycle test the snapshot's own report claims it added.

    A report that names a test file that was never committed is an
    audit-readiness defect: the next auditor spends its quantum discovering
    the path is absent.  This check proves the path exists and the test is
    green on the snapshot's own bytes.
    """
    path = ROOT / cycle_test
    if not path.is_file():
        return _check(
            "cycle_test",
            f"Cycle test {cycle_test} exists and is green",
            False,
            {"path": cycle_test, "present": False},
            [cycle_test],
        )
    cmd = [sys.executable, "-m", "pytest", cycle_test, "-q", "--maxfail=1"]
    run = _run(cmd, 300)
    text = run["stdout_tail"] + "\n" + run["stderr_tail"]
    passed = int((_PASSED_RE.search(text) or [0, 0])[1] or 0)
    failed = int((_FAILED_RE.search(text) or [0, 0])[1] or 0)
    errors = int((_ERROR_RE.search(text) or [0, 0])[1] or 0)
    ok = run["exit_code"] == 0 and passed > 0 and failed == 0 and errors == 0
    return _check(
        "cycle_test",
        f"Cycle test {cycle_test} exists and is green",
        ok,
        {"path": cycle_test, "present": True, "passed": passed,
         "failed": failed, "errors": errors,
         "timed_out": run["timed_out"]},
        [cycle_test], run["command"], run["seconds"],
    )


def check_progressive_smoke(run_id: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="lex_audit_smoke_") as td:
        out = Path(td) / "smoke.json"
        cmd = [sys.executable, "product/progressive_smoke.py",
               "--run-id", run_id, "--out", str(out)]
        run = _run(cmd, SMOKE_TIMEOUT_S)
        if not out.is_file():
            return _check("progressive_smoke",
                          "Shipped progressive API answers over a real socket",
                          False, {"run": run}, [], run["command"],
                          run["seconds"])
        art = _load(out)
    by_name = {c["check"]: c for c in art.get("checks") or []}
    problems = []
    if art.get("verdict") != "PASS":
        problems.append("verdict")
    if art.get("checks_passed") != art.get("checks_total"):
        problems.append("checks")
    if (by_name.get("start_first_page_nonempty") or {}).get("detail", 0) < 100:
        problems.append("first_page")
    if (by_name.get("start_has_clusters") or {}).get("detail", 0) < 5:
        problems.append("clusters")
    if (by_name.get("start_points_have_xy") or {}).get("detail") != "100/100":
        problems.append("coordinates")
    if (by_name.get("answer_has_citations") or {}).get("detail", 0) < 1:
        problems.append("citations")
    t = art.get("timings_s") or {}
    if t.get("server_boot_s", 99) >= 3.0:
        problems.append("server_boot_budget")
    if t.get("start_s", 99) >= 1.0:
        problems.append("cached_start_budget")
    return _check(
        "progressive_smoke",
        "Shipped progressive API answers over a real socket (fixture mode)",
        not problems,
        {"problems": problems, "verdict": art.get("verdict"),
         "checks": f"{art.get('checks_passed')}/{art.get('checks_total')}",
         "timings_s": t, "mode": art.get("mode")},
        [], run["command"], run["seconds"],
    )


_PASSED_RE = re.compile(r"(\d+) passed")
_FAILED_RE = re.compile(r"(\d+) failed")
_SKIPPED_RE = re.compile(r"(\d+) skipped")
_ERROR_RE = re.compile(r"(\d+) error")


def check_mvp_tests() -> dict[str, Any]:
    cmd = [sys.executable, "-m", "pytest", *MVP_CORE_TESTS, "-q",
           "--maxfail=1"]
    run = _run(cmd, PYTEST_TIMEOUT_S)
    text = run["stdout_tail"] + "\n" + run["stderr_tail"]
    passed = int((_PASSED_RE.search(text) or [0, 0])[1] or 0)
    failed = int((_FAILED_RE.search(text) or [0, 0])[1] or 0)
    errors = int((_ERROR_RE.search(text) or [0, 0])[1] or 0)
    skipped = int((_SKIPPED_RE.search(text) or [0, 0])[1] or 0)
    ok = run["exit_code"] == 0 and passed > 0 and failed == 0 and errors == 0
    return _check(
        "mvp_core_tests",
        "Bounded MVP core pytest set is green",
        ok,
        {"passed": passed, "failed": failed, "errors": errors,
         "skipped": skipped, "timed_out": run["timed_out"],
         "files": list(MVP_CORE_TESTS)},
        [], run["command"], run["seconds"],
    )


def audit_namespace_ids(run_id: str, resumed_run_id: str | None,
                        accepted_run_id: str | None) -> list[str]:
    """Run ids whose audit artifacts could only have been minted by a producer.

    The accepted pointer is deliberately excluded: its committed
    ``results/audit/product/CYCLE_<accepted>_GATE.json`` is auditor-owned
    evidence in the base snapshot, not something this producer wrote.  Before
    this helper existed, regenerating the dossier for an *accepted* run
    (``--run-id 40284658455`` while the profile resumed ``40283048553``)
    reported a false ``audit_namespace`` FAIL purely because the accepted gate
    was present in the tree.  That false FAIL is the only reason the
    41184474509 snapshot committed a FAIL dossier.
    """
    accepted = str(accepted_run_id or "").removeprefix("CYCLE_")
    ids: list[str] = []
    for rid in (str(run_id or ""), str(resumed_run_id or "")):
        if rid and rid != accepted and rid not in ids:
            ids.append(rid)
    return ids


def check_audit_namespace(run_id: str,
                          resumed_run_id: str | None = None) -> dict[str, Any]:
    try:
        accepted_run = str(load_state().get("accepted_run_id") or "")
    except Exception:  # pragma: no cover - state_contract check reports this
        accepted_run = ""
    checked = audit_namespace_ids(run_id, resumed_run_id, accepted_run)
    gates = {rid: (ROOT / "results" / "audit" / "product"
                   / f"CYCLE_{rid}_GATE.json") for rid in checked}
    reports = {rid: (ROOT / "reports" / "audit" / "product"
                     / f"CYCLE_{rid}.md") for rid in checked}
    pending = subprocess.run(
        ["git", "status", "--porcelain", "-uall"], cwd=str(ROOT),
        capture_output=True, text=True, check=False,
    ).stdout.splitlines()
    producer_audit = [line[3:] for line in pending
                      if line[3:].startswith(("results/audit/product/",
                                              "reports/audit/product/"))]
    suspects = [str(p.relative_to(ROOT))
                for p in list(gates.values()) + list(reports.values())
                if p.exists()]
    ok = not suspects and not producer_audit
    primary_gate = (ROOT / "results" / "audit" / "product"
                    / f"CYCLE_{run_id}_GATE.json")
    primary_report = (ROOT / "reports" / "audit" / "product"
                      / f"CYCLE_{run_id}.md")
    return _check(
        "audit_namespace",
        "Producer wrote no auditor-namespace path and minted no gate",
        ok,
        {"gate_exists": primary_gate.exists(),
         "report_exists": primary_report.exists(),
         "accepted_run_id": accepted_run,
         "checked_run_ids": checked,
         "suspect_paths": suspects,
         "pending_audit_paths": producer_audit},
        list(suspects) + [
            str(primary_gate.relative_to(ROOT)),
            str(primary_report.relative_to(ROOT)),
        ],
    )


def bounded_plan_for(checks: list[dict[str, Any]], resumed_id: str,
                     resume_diag: Path | None = None,
                     current_report: Path | None = None) -> dict[str, Any]:
    """Measured, ordered work list handed to the independent auditor.

    Why this exists: the audit job runs under the wrapper's 2700 s work
    quantum, and two product audits in this chain already died at 2705 s
    (``LEX_WORK_QUANTUM_EXPIRED``, exit 78) with the gate reader skipped, so
    the work was never adjudicated.  An auditor that starts without a budget
    discovers the budget by dying inside it.

    Each entry carries the duration **this run measured** for the same
    command, so a plan can be bounded before it is executed.  Durations are
    observations on this machine: they are a planning input, never a claim
    about another host, and no step, bar or check is added, removed or
    weakened by publishing them.
    """
    timed = [c for c in checks
             if isinstance(c.get("seconds"), (int, float))]
    unmeasured = [c for c in checks
                  if not isinstance(c.get("seconds"), (int, float))]
    # measured steps first, longest first (the expensive ones bound the plan);
    # unmeasured steps keep their natural order so nothing silently disappears.
    ordered = sorted(timed, key=lambda c: -float(c["seconds"])) + unmeasured
    total = round(sum(float(c["seconds"]) for c in timed), 3)
    skipped = [c["id"] for c in checks if c.get("status") == "SKIP"]
    largest = ({"id": max(timed, key=lambda c: float(c["seconds"]))["id"],
                "measured_seconds": max(float(c["seconds"]) for c in timed)}
               if timed else None)
    budget_s = 2700
    return {
        "purpose": (
            "Run the commands below in this order, read the two committed "
            "diagnosis artifacts, then write the gate. The durations are "
            "measured here so the plan fits the audit work quantum with "
            "margin instead of being discovered by a timeout."
        ),
        "audit_work_quantum_s": budget_s,
        "measured_seconds_total": total,
        "measured_seconds_margin_s": round(budget_s - total, 3),
        "within_quantum": bool(total < budget_s),
        "largest_single_step": largest,
        "steps": [
            {"id": c["id"], "status": c["status"],
             "command": c.get("command"),
             "measured_seconds": (float(c["seconds"])
                                  if isinstance(c.get("seconds"),
                                                (int, float)) else None)}
            for c in ordered
        ],
        "measured_step_count": len(timed),
        "unmeasured_steps": [c["id"] for c in unmeasured],
        "skipped_steps": skipped,
        "first_reads": [
            str(resume_diag.relative_to(ROOT)) if resume_diag else None,
            f"results/product/orchestration/CYCLE_{resumed_id}"
            "_team_step_raw.json",
            str(current_report.relative_to(ROOT)) if current_report else None,
        ],
        "not_required": (
            "Do not re-derive accepted evaluation 40070818687 / 40068038783 / "
            "40105794124 or the D2 profile 40089391202, and do not regenerate "
            "the offline/server slice family: those are consumed accepted "
            "findings pinned REPORTED-ONLY by the profile."
        ),
        "timing_claim_ceiling": (
            "Observations of one host for one dossier generation run. They "
            "are not a cross-machine guarantee and they score no bar."
        ),
    }


def run(run_id: str, direction_version: int = DIRECTION_VERSION,
        include_tests: bool = True, include_smoke: bool = True,
        auto_bootstrap: bool = True) -> dict[str, Any]:
    if direction_version != DIRECTION_VERSION:
        raise SystemExit(
            f"this snapshot was dispatched under direction v{DIRECTION_VERSION}; "
            f"got v{direction_version}"
        )
    PROFILE.clear()
    PROFILE.update(select_profile(run_id))
    resume_diag = Path(p("resume_diag", RESUME_DIAG))
    raw = Path(p("raw")) if p("raw") else None
    resumed_id = p("resumed_run_id", RESUMED_RUN_ID)
    predecessor = p("predecessor_run_id", PREDECESSOR_RUN_ID)
    failed_job = p("failed_job", "audit")
    mechanism_kind = p("mechanism_kind", "observed")
    delta_kind = p("delta_kind", "committed")
    resumed = _load(resume_diag)
    checks = [
        check_runtime_preflight(auto_bootstrap=auto_bootstrap),
        check_state_contract(),
        check_posture(),
        check_resumed_diagnosis(),
        check_claim_artifacts(),
    ]
    if include_tests:
        checks.append(check_cycle_test(str(p("cycle_test", ""))))
    else:
        checks.append(_skip("cycle_test",
                            "Cycle test exists and is green",
                            "skipped by --skip-tests"))
    if include_smoke:
        checks.append(check_progressive_smoke(run_id))
    else:
        checks.append(_skip("progressive_smoke",
                            "Shipped progressive API answers over a real socket",
                            "skipped by --skip-smoke"))
    if include_tests:
        checks.append(check_mvp_tests())
    else:
        checks.append(_skip("mvp_core_tests",
                            "Bounded MVP core pytest set is green",
                            "skipped by --skip-tests"))
    checks.append(check_audit_namespace(run_id, resumed_id))

    failed = [c["id"] for c in checks if c["status"] == "FAIL"]
    skipped = [c["id"] for c in checks if c["status"] == "SKIP"]
    overall = "FAIL" if failed else ("PASS" if not skipped else "PARTIAL")
    who = ("audit" if failed_job == "audit" else "team lane-cycle")
    before_bundle = Path(p("before_bundle", BEFORE_BUNDLE))
    after_bundle = Path(p("after_bundle", AFTER_BUNDLE))
    inherited = p("inherited_report", INHERITED_REPORT)
    cycle_test = p("cycle_test", "product/tests/test_cycle_40200882831.py")
    delta_files = ((resumed.get("durable_delta") or {}).get("changed_files"))
    cf_path = Path(p("content_family", CONTENT_FAMILY))
    cf_expected = dict(p("content_family_expected", CONTENT_FAMILY_EXPECTED))
    live_state = _load(STATE)

    # C1 wording follows the observed mechanism kind: the three real failure
    # modes this dossier has now measured are a work-quantum expiry, an
    # unobserved stop, and a model-gateway request rejection.  Wording all
    # three as "work quantum" would misreport the last one.
    if mechanism_kind == "observed_log":
        log_ev_path = Path(p("lane_cycle_log_evidence",
                             LANE_CYCLE_LOG_EVIDENCE))
        c1_claim = (
            f"Run {resumed_id}'s lane-cycle agent was rejected by the model "
            f"gateway on an unrecognized request parameter ("
            f"{p('upstream_signature', 'unsupported_parameter')!r}: "
            f"{p('upstream_detail', '')!r}) and exited {p('exit_code', 1)} "
            f"after {p('failed_step_seconds')} s, before the independent "
            "audit could run; observed from the run's own job logs "
            "(logs endpoint HTTP 200), not inferred, and no work quantum "
            "was reached. "
            + (p("mechanism_chain_note") or "")
        ).strip()
        c1_artifacts = (
            ([str(raw.relative_to(ROOT))] if raw is not None else [])
            + [str(resume_diag.relative_to(ROOT))]
            + ([str(log_ev_path.relative_to(ROOT))]
               if log_ev_path.is_file() else []))
    elif mechanism_kind == "observed_scope":
        c1_claim = (
            f"Run {resumed_id}'s lane-cycle agent step SUCCEEDED ("
            f"{p('lane_cycle_step_seconds', 0)} s of a 2700 s quantum) and "
            f"the producer state validation passed, but the team job died "
            f"at 'Enforce lane write scope' (exit "
            f"{p('exit_code', 3)}) because the producer minted "
            "results/audit/product/"
            f"CYCLE_{resumed_id}_GATE.json, a path outside the producer "
            "write scope; audit and integrate were therefore skipped and no "
            "auditor ever ran for that gate's named run. The minted file is "
            "preserved verbatim and quarantined as NON-PROMOTING by "
            "results/product/incidents/"
            "self_minted_gate_40278460732_producer_40283048553."
            "QUARANTINED.json. Observed from the run's own job records "
            "(logs endpoint HTTP 200), not inferred; no work quantum "
            "expired."
        )
        c1_artifacts = (
            ([str(raw.relative_to(ROOT))] if raw is not None else [])
            + [str(resume_diag.relative_to(ROOT))])
    elif mechanism_kind == "observed_step_failure":
        c1_claim = (
            f"Run {resumed_id}'s lane-cycle agent step FAILED after "
            f"{p('lane_cycle_step_seconds', 0)} s of a 2700 s work quantum; "
            "'Validate active MVP producer state' and 'Enforce lane write "
            "scope' were skipped, no audit ran, and the team ref is "
            "byte-identical to the accepted base (ZERO_DURABLE_DELTA). The "
            "public jobs snapshot shows the step conclusions and timestamps; "
            "the logs endpoint answered HTTP 403, so the log-level cause is "
            "UNOBSERVED and no cause is asserted."
        )
        c1_artifacts = (
            ([str(raw.relative_to(ROOT))] if raw is not None else [])
            + [str(resume_diag.relative_to(ROOT))])
    elif mechanism_kind == "observed":
        c1_claim = (
            f"Run {resumed_id}'s {who} agent ended on the workflow "
            f"work quantum ({p('quantum_seconds', 2700)} s, exit "
            f"{p('exit_code', 78)}) before an independent gate could "
            "be written; observed from the public check-run "
            "annotations, not inferred.")
        c1_artifacts = (
            ([str(raw.relative_to(ROOT))] if raw is not None else [])
            + [str(resume_diag.relative_to(ROOT))])
    else:
        c1_claim = (
            "No public run/jobs snapshot for run "
            f"{resumed_id} was available in the producer checkout, so "
            "the provider/auth/timeout mechanism is UNOBSERVED and no "
            "cause is asserted.")
        c1_artifacts = [str(resume_diag.relative_to(ROOT))]

    bounded = bounded_plan_for(
        checks, str(resumed_id),
        resume_diag if resume_diag.is_file() else None,
        Path(p("current_report", CURRENT_REPORT)))

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "run_id": str(run_id),
        "resumed_run_id": resumed_id,
        "predecessor_run_id": predecessor,
        "profile": "default" if resumed_id == RESUMED_RUN_ID else resumed_id,
        "direction_version": DIRECTION_VERSION,
        "overall_status": overall,
        "failed_checks": failed,
        "skipped_checks": skipped,
        "checks": checks,
        "resumed_run": {
            "classification": (resumed.get("orchestration") or {}).get(
                "classification"),
            "mechanism": ((resumed.get("orchestration") or {}).get("mechanism")
                          or {}).get("status"),
            "quantum_seconds": p("quantum_seconds"),
            "exit_code": p("exit_code"),
            "failed_job": failed_job,
            "durable_delta": (resumed.get("durable_delta") or {}).get(
                "classification"),
            "adjudication": (resumed.get("adjudication") or {}).get("status"),
        },
        "claims": [
            {"id": "C1",
             "claim": c1_claim,
             "check": "resumed_diagnosis",
             "artifacts": c1_artifacts},
            {"id": "C2",
             "claim": (
                 f"Run {resumed_id} persisted an {delta_files}-file durable "
                 f"delta over {predecessor} and is UNADJUDICATED."
                 if delta_kind != "zero" else
                 f"Run {resumed_id}'s team ref is byte-identical to its "
                 f"predecessor {predecessor}'s team ref: the resumed producer "
                 "added nothing (ZERO_DURABLE_DELTA) and the run is "
                 "UNADJUDICATED."
             ),
             "check": "resumed_diagnosis",
             "artifacts": [str(resume_diag.relative_to(ROOT))]},
            {"id": "C3",
             "claim": "The v68 rejection/incumbent leg flips the D2 letterhead "
                      "row from verified to unverified with reason pivot_absent.",
             "check": "claim_artifacts",
             "artifacts": [str(before_bundle.relative_to(ROOT)),
                           str(after_bundle.relative_to(ROOT)),
                           str(cf_path.relative_to(ROOT))]},
            {"id": "C4",
             "claim": f"The fixed-path family is {cf_expected['n_bundles']} "
                      f"bundles / {cf_expected['n_decisions']} decisions / "
                      f"{cf_expected['n_verified']} verified rows / "
                      f"{cf_expected['n_verified_defective']} "
                      "verified-and-defective, with the sound row retained "
                      "and 0 false rejects (REPORTED-ONLY measurement).",
             "check": "claim_artifacts",
             "artifacts": [str(cf_path.relative_to(ROOT))]},
            {"id": "C5",
             "claim": "The shipped progressive query slice still answers over a "
                      "real socket in fixture mode within the local budgets.",
             "check": "progressive_smoke",
             "artifacts": ["re-run to a temp path (no repository mutation)"]},
            {"id": "C6",
             "claim": "The bounded MVP core pytest set is green.",
             "check": "mvp_core_tests", "artifacts": list(MVP_CORE_TESTS)},
            {"id": "C7",
             "claim": "Posture is fail-closed and the accepted pointer "
                      f"({live_state.get('accepted_run_id')} / "
                      f"{str(live_state.get('accepted_commit') or '')[:9]}) "
                      "satisfies BOTH halves of requirement 4: a committed "
                      "PASS/safe gate and an accept commit.",
             "check": "posture", "artifacts": ["state/product.json"]},
            {"id": "C8",
             "claim": "This run minted no audit gate and wrote no "
                      "auditor-namespace path.",
             "check": "audit_namespace", "artifacts": []},
        ],
        "audit_entry_points": {
            "one_command": (
                "python3 product/audit_readiness.py --run-id "
                f"{run_id} --out /tmp/lex_audit_readiness.json"
            ),
            "resumed_run_diagnosis": str(resume_diag.relative_to(ROOT)),
            "inherited_report": (str(Path(inherited).relative_to(ROOT))
                                 if inherited else None),
            "current_report": str(Path(
                p("current_report", CURRENT_REPORT)).relative_to(ROOT)),
            "current_cycle_test": f"python3 -m pytest {cycle_test} -q",
            "not_required": (
                "Do not re-derive accepted evaluation 40070818687 / "
                "40068038783 / 40105794124 or the D2 profile 40089391202; "
                "they are consumed findings cited by the lane. Historical "
                "cycle tests that assert predecessor git refs are not part of "
                "this snapshot's claim set and may report REF_ABSENT in the "
                "audit worktree, which fetches only the accepted base and the "
                "current team ref."
            ),
        },
        "bounded_plan": bounded,
        "posture": {
            "audit_write_scope": "producer wrote only product-owned paths",
            "gate_minted": False,
            "frozen_bar_scored": False,
            "serve_verdict_rerun": False,
            "run_label": "UNADJUDICATED",
            "human_gate_ready": False,
            "machine_gate_ready": False,
        },
        "claim_ceiling": (
            "A bounded audit-readiness dossier, not an audit. It re-derives "
            "or hashes the snapshot's published claims and records the exact "
            "commands; it writes no gate, scores no frozen bar, re-runs no "
            "serve verdict, and labels no run accepted or rejected."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--direction-version", type=int,
                    default=DIRECTION_VERSION)
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--skip-smoke", action="store_true")
    ap.add_argument("--no-bootstrap", action="store_true",
                    help="probe the runtime but do not install the pinned pins")
    args = ap.parse_args(argv)
    rec = run(args.run_id, direction_version=args.direction_version,
              include_tests=not args.skip_tests,
              include_smoke=not args.skip_smoke,
              auto_bootstrap=not args.no_bootstrap)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "overall_status": rec["overall_status"],
        "failed_checks": rec["failed_checks"],
        "skipped_checks": rec["skipped_checks"],
        "checks": {c["id"]: c["status"] for c in rec["checks"]},
    }, indent=2))
    return 0 if rec["overall_status"] in ("PASS", "PARTIAL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
