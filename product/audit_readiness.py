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
from product.state_contract import accepted_pointer_evidence  # noqa: E402

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
    "40500024808": {
        # Operational resume of 40499737748: team job failed at 'Run lane
        # cycle' after 16.0 s with exit 1 and no wrapper signature, logs 403,
        # so the mechanism is the UNOBSERVED/observed_steps kind and the
        # resumed snapshot equals its predecessor team head (zero delta).
        "resumed_run_id": "40499737748",
        "predecessor_run_id": "40493520783",
        "raw": ORCH / "CYCLE_40499737748_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40499737748_resume_diagnosis.json",
        "inherited_report": None,
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40500024808.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "mechanism_kind": "observed_steps",
        "delta_kind": "zero",
        "exit_code": 1,
        "changed_files": 0,
        "cycle_test": "product/tests/test_cycle_40500024808.py",
        "state_block": "cycle_40500024808_operational_resume",
    },
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
    "40429931848": {
        # Operational resume dispatched from main after the repair1 snapshot
        # (run 40427889739) was persisted.  The repair itself was not rejected:
        # the audit job's agent step SUCCEEDED, then the workflow's own gate
        # reader failed at write-scope enforcement ("auditor crossed scope",
        # exit 3), the persist step was skipped, and no audit ref exists.
        "resumed_run_id": "40427889739",
        "predecessor_run_id": "40423889401",
        "raw": ORCH / "CYCLE_40427889739_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40427889739_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40427889739_REPAIR1.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40429931848.md",
        "classification": "AUDIT_JOB_AUDIT_SCOPE_ENFORCEMENT_FAILED_NO_GATE",
        "mechanism_kind": "observed_audit_scope",
        "failed_job": "audit",
        "exit_code": 3,
        "audit_failed_step": "Enforce audit scope and read gate",
        "delta_kind": "committed",
        "changed_files": 8,
        "changed_paths_include": (
            "product/audit_readiness.py",
            "results/product/repair_40427889739/",
        ),
        "cycle_test": "product/tests/test_cycle_40429931848_resume.py",
        "state_block": "cycle_40429931848_operational_resume",
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
    "40423889401": {
        "resumed_run_id": "40423595480",
        # The snapshot is byte-identical to the accepted head produced by
        # 40284658455; it is a no-op resume, not a producer failure to repair.
        "predecessor_run_id": "40284658455",
        "raw": ORCH / "CYCLE_40423595480_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40423595480_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40284658455.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40423889401.md",
        # Fifth real failure mode: the team job failed at "Run lane cycle";
        # the public jobs API fixes the step conclusions but the logs endpoint
        # returned HTTP 403, so the log-level cause stays UNOBSERVED.  This is
        # the honest middle ground between an observed cause and no snapshot.
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "mechanism_kind": "observed_steps",
        "failed_job": "team",
        "delta_kind": "zero",
        "cycle_test": "product/tests/test_cycle_40423889401.py",
        "state_block": "cycle_40423889401_operational_resume",
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
    "40621019854": {
        "resumed_run_id": "40620804872",
        "predecessor_run_id": "40606019054",
        "raw": None,
        "resume_diag": ORCH / "CYCLE_40620804872_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40284658455.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40621019854.md",
        "classification": "RAW_SNAPSHOT_UNAVAILABLE",
        "mechanism_kind": "unobserved",
        "failed_job": "team",
        "delta_kind": "committed",
        "changed_files": 1,
        "changed_paths_include": ("state/product.json",),
        "cycle_test": "product/tests/test_cycle_40621019854.py",
        "state_block": "cycle_40621019854_operational_resume",
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40621019854.json",
        "content_family_expected": {
            "n_bundles": 50,
            "n_decisions": 5000,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "40626954469": {"alias_of": "40621019854"},
    "40640028819": {
        # Operational resume of 40639812991: the team job failed at 'Run
        # lane cycle' after 16.0 s with exit 1 and no wrapper signature
        # (the same observed_steps signature measured on 40499737748),
        # logs endpoint 403, and the always-run persist step published a
        # tree byte-identical to its predecessor 40639072630 (zero durable
        # delta).  The predecessor was itself a zero-delta rc-67 repair
        # after 40633276503's audit died at LEX_WORK_QUANTUM_EXPIRED.
        # The lineage sits 17 operational-resume commits ahead of the
        # accepted head 7be4480e, so the zero-delta reference is the
        # predecessor, not the accepted head.
        "resumed_run_id": "40639812991",
        "predecessor_run_id": "40639072630",
        "raw": ORCH / "CYCLE_40639812991_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40639812991_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40621019854.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40640028819.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "mechanism_kind": "observed_steps",
        "delta_kind": "zero",
        "exit_code": 1,
        "changed_files": 0,
        "cycle_test": "product/tests/test_cycle_40640028819.py",
        "state_block": "cycle_40640028819_operational_resume",
        "zero_delta_reference": (
            "its predecessor run 40639072630's team head 741e3989, which "
            "is 17 operational-resume commits ahead of the accepted head "
            "7be4480e"
        ),
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40640028819.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "40639812991": {"alias_of": "40640028819"},
    "40647341524": {"alias_of": "40640028819"},
    "40647622447": {"alias_of": "40640028819"},
    "40655643086": {
        # Operational resume of 40655374513: the team job failed at 'Run
        # lane cycle' after 17.0 s with no readable exit code (annotations
        # endpoint HTTP 404, logs endpoint HTTP 403), and the always-run
        # persist step published a tree byte-identical to its predecessor
        # 40654856196 (zero durable delta).  The predecessor died the same
        # way after 137.0 s; its predecessor 40647622447 was a producer
        # success whose independent audit failed the 'Independent audit'
        # step at exactly 2705 s — the documented ~2700 s work-quantum
        # signature.  The lineage now sits 19 commits ahead of the accepted
        # head 7be4480e, so the zero-delta reference is the predecessor,
        # not the accepted head.
        "resumed_run_id": "40655374513",
        "predecessor_run_id": "40654856196",
        "raw": ORCH / "CYCLE_40655374513_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40655374513_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40640028819.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40655643086.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "mechanism_kind": "observed_steps",
        "delta_kind": "zero",
        "exit_code": None,
        "changed_files": 0,
        "cycle_test": "product/tests/test_cycle_40655643086.py",
        "state_block": "cycle_40655643086_operational_resume",
        "zero_delta_reference": (
            "its predecessor run 40654856196's team head 9226a69d, which "
            "is 19 commits ahead of the accepted head 7be4480e"
        ),
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40655643086.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "40654856196": {"alias_of": "40655643086"},
    "40655374513": {"alias_of": "40655643086"},
    "40667295410": {
        # Operational resume of 40666994415: the team job failed at 'Run
        # lane cycle' after 17.0 s with no readable exit code (logs endpoint
        # HTTP 403, annotations HTTP 404), and the always-run persist step
        # republished the predecessor 40655643086's team head 7d411a69 (zero
        # durable delta).  The predecessor was a producer success whose
        # independent audit failed the 'Independent audit' step at exactly
        # 2705 s — the FOURTH audit-side ~2700 s work-quantum death in this
        # chain (with 40633276503 at 2704 s, 40640028819 and 40647622447)
        # — so the 20-commit lineage ahead of the accepted head 7be4480e
        # remains unadjudicated and the zero-delta reference is the
        # predecessor, not the accepted head.
        "resumed_run_id": "40666994415",
        "predecessor_run_id": "40655643086",
        "raw": ORCH / "CYCLE_40666994415_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40666994415_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40655643086.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40667295410.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "mechanism_kind": "observed_steps",
        "delta_kind": "zero",
        "exit_code": None,
        "changed_files": 0,
        "cycle_test": "product/tests/test_cycle_40667295410.py",
        "state_block": "cycle_40667295410_operational_resume",
        "zero_delta_reference": (
            "its predecessor run 40655643086's team head 7d411a69, which "
            "is 20 commits ahead of the accepted head 7be4480e"
        ),
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40667295410.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "40666994415": {"alias_of": "40667295410"},
    "40682733879": {
        # Operational resume of 40676629031: the team job failed at 'Run
        # lane cycle' after 2704.0 s with exit code 78.  Check-run annotations
        # are OBSERVED this cycle and read LEX_WORK_QUANTUM_EXPIRED
        # seconds=2700 — the FIRST TEAM-side quantum death of this lineage
        # (the four prior quantum-class deaths were audit-side at 2705 s).
        # The always-run persist step republished the predecessor
        # 40667295410's team head 96d79c7e (zero durable delta): the agent
        # consumed the full quantum without committing.  Countermeasure
        # adopted: commit-early strategy so a quantum death always leaves a
        # durable delta.
        "resumed_run_id": "40676629031",
        "predecessor_run_id": "40667295410",
        "raw": ORCH / "CYCLE_40676629031_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40676629031_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40667295410.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40682733879.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_QUANTUM",
        "failed_job": "team",
        "mechanism_kind": "observed",
        "delta_kind": "zero",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 0,
        "cycle_test": "product/tests/test_cycle_40682733879.py",
        "state_block": "cycle_40682733879_operational_resume",
        "zero_delta_reference": (
            "its predecessor run 40667295410's team head 96d79c7e, which "
            "is 21 commits ahead of the accepted head 7be4480e"
        ),
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40682733879.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    "40676629031": {"alias_of": "40682733879"},
    "40692326715": {
        # Operational resume of 40692326715: raw run/jobs snapshot unavailable
        # in this checkout; orchestration mechanism not observed. Team ref
        # origin/cycle/core/product/40692326715/team carries COMMITTED_DELTA
        # (9 files) over predecessor 40682733879's head 96d79c7e (including
        # product/audit_readiness.py, reports/tests for 40682733879, and a
        # query cache update). No independent audit gate and no accept
        # commit observed for this run; status UNADJUDICATED.
        "resumed_run_id": "40692326715",
        "predecessor_run_id": "40682733879",
        "raw": None,
        "resume_diag": ORCH / "CYCLE_40692326715_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40682733879.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40692326715.md",
        "classification": "RAW_SNAPSHOT_UNAVAILABLE",
        "failed_job": "unknown",
        "mechanism_kind": "unobserved",
        "delta_kind": "committed",
        "exit_code": None,
        "changed_files": 9,
        "cycle_test": "product/tests/test_cycle_40692326715.py",
        "state_block": "cycle_40692326715_operational_resume",
        "zero_delta_reference": None,
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40692326715.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    # Chain-tail registry (cycle 40718103891). These three runs are NOT
    # dossier targets; they are the machine-classified chain the resumed
    # snapshot must be auditable against. 40702698815's TEAM job SUCCEEDED
    # (committed 7-file delta 876d1a82) and its AUDIT "Independent audit"
    # step died at the 2700 s work quantum (exit 78, no gate) — the fifth
    # audit-quantum instance and the first with a committed public raw.
    # 40717159827 and 40717587477 are exit-1/16-17 s zero-delta team deaths
    # (observed_steps kind: which step failed is observed; the log-level
    # cause is UNOBSERVED and no provider mechanism is claimed — the
    # requirement-20 provider/early-exit class, not a product defect).
    "40702698815": {
        "resumed_run_id": "40702698815",
        "predecessor_run_id": "40692326715",
        "raw": ORCH / "CYCLE_40702698815_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40702698815_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40692326715.md",
        "current_report": None,
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "failed_job": "audit",
        "mechanism_kind": "observed",
        "delta_kind": "committed",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 7,
        "cycle_test": "product/tests/test_cycle_40718103891.py",
        "state_block": "cycle_40702698815_operational_resume",
        "zero_delta_reference": None,
        "content_family": None,
        "content_family_expected": None,
    },
    "40717159827": {
        "resumed_run_id": "40717159827",
        "predecessor_run_id": "40702698815",
        "raw": ORCH / "CYCLE_40717159827_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40717159827_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40692326715.md",
        "current_report": None,
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "mechanism_kind": "observed_steps",
        "delta_kind": "zero",
        "quantum_seconds": None,
        "exit_code": 1,
        "changed_files": 0,
        "cycle_test": "product/tests/test_cycle_40718103891.py",
        "state_block": "cycle_40717159827_operational_resume",
        "zero_delta_reference": (
            "its predecessor run 40702698815's team head 876d1a82, which "
            "is 25 commits ahead of the accepted head 7be4480e"
        ),
        "content_family": None,
        "content_family_expected": None,
    },
    "40717587477": {
        "resumed_run_id": "40717587477",
        "predecessor_run_id": "40717159827",
        "raw": ORCH / "CYCLE_40717587477_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40717587477_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40692326715.md",
        "current_report": None,
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "mechanism_kind": "observed_steps",
        "delta_kind": "zero",
        "quantum_seconds": None,
        "exit_code": 1,
        "changed_files": 0,
        "cycle_test": "product/tests/test_cycle_40718103891.py",
        "state_block": "cycle_40717587477_operational_resume",
        "zero_delta_reference": (
            "its predecessor run 40717159827's team head 876d1a82, which "
            "is 25 commits ahead of the accepted head 7be4480e"
        ),
        "content_family": None,
        "content_family_expected": None,
    },
    # Active cycle 40718103891: operational resume of the exit-1 zero-delta
    # death 40717587477. The dossier's resumed-diagnosis check validates the
    # RESUMED run's death (40717587477) exactly as observed_steps requires;
    # this cycle's own committed delta is registered in state/report/test.
    "40718103891": {
        "resumed_run_id": "40717587477",
        "predecessor_run_id": "40717159827",
        "raw": ORCH / "CYCLE_40717587477_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40717587477_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40692326715.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40718103891.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "mechanism_kind": "observed_steps",
        "delta_kind": "zero",
        "quantum_seconds": None,
        "exit_code": 1,
        "changed_files": 0,
        "zero_delta_reference": (
            "its predecessor run 40717159827's team head 876d1a82, which "
            "is 25 commits ahead of the accepted head 7be4480e"
        ),
        "cycle_test": "product/tests/test_cycle_40718103891.py",
        "state_block": "cycle_40718103891_operational_resume",
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40718103891.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    # Chain-tail registry entry for 40718103891's OWN death (added by cycle
    # 40726216925).  The key above stays what it was — the profile THAT run's
    # committed dossier used (resume of 40717587477's exit-1 death).  This
    # entry is the machine record that 40718103891's own team step then died
    # at the 2700 s work quantum (exit 78, LEX_WORK_QUANTUM_EXPIRED) AFTER
    # committing its full 19-file delta 7cf7a11e over predecessor head
    # 876d1a82; state validation, write scope, audit and gate were all
    # skipped.  Active profile for the resuming cycle 40726216925 is below.
    # Chain-tail registry entry for 40726216925's OWN death (added by cycle
    # 40737328834): its TEAM job was FULLY GREEN (every step success,
    # including state validation, write scope and persist) and its AUDIT
    # "Independent audit" step died at the 2700 s work quantum (exit 78,
    # LEX_WORK_QUANTUM_EXPIRED) after 2704.0 s — the EIGHTH quantum-class
    # death in this lineage and the SECOND audit-side one (after
    # 40702698815).  No audit branch and no gate exist; integrate was
    # skipped.  Active profile for the resuming cycle is "40737328834"
    # further below.
    "40726216925": {
        "resumed_run_id": "40718103891",
        "predecessor_run_id": "40717587477",
        "raw": ORCH / "CYCLE_40718103891_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40718103891_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40718103891.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40726216925.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "mechanism_kind": "observed",
        "delta_kind": "committed",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 19,
        "changed_paths_include": (
            "reports/product/CYCLE_40718103891.md",
            "results/product/audit_readiness/"
            "CYCLE_40718103891_audit_readiness.json",
            "state/product.json",
        ),
        "cycle_test": "product/tests/test_cycle_40726216925.py",
        "state_block": "cycle_40726216925_operational_resume",
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40718103891.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    # Active cycle 40737328834: operational resume of run 40726216925, whose
    # TEAM job was fully green (every step success, including state
    # validation, write scope and persist) and whose AUDIT "Independent
    # audit" step died at the 2700 s work quantum (exit 78,
    # LEX_WORK_QUANTUM_EXPIRED, OBSERVED via public check-run annotations)
    # after 2704.0 s; the gate step and the persist step were skipped, no
    # audit branch or gate exists, and integrate was skipped — the run is
    # UNADJUDICATED with an 8-file committed delta df6c81fb over predecessor
    # team head 7cf7a11e.  EIGHTH quantum-class death in this lineage, the
    # SECOND audit-side one after 40702698815.
    "40737328834": {
        "resumed_run_id": "40726216925",
        "predecessor_run_id": "40718103891",
        "raw": ORCH / "CYCLE_40726216925_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40726216925_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40726216925.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40737328834.md",
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "failed_job": "audit",
        "mechanism_kind": "observed",
        "delta_kind": "committed",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 8,
        "changed_paths_include": (
            "reports/product/CYCLE_40726216925.md",
            "results/product/audit_readiness/"
            "CYCLE_40726216925_audit_readiness.json",
            "state/product.json",
        ),
        "cycle_test": "product/tests/test_cycle_40737328834.py",
        "state_block": "cycle_40737328834_operational_resume",
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40718103891.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    # Cycle 40747546909: the lane re-dispatched a PRODUCER repair round right
    # after 40737328834's audit-side quantum death.  The producer correctly
    # found nothing to add to the already audit-ready snapshot 866ae3cb, so
    # HEAD was unchanged with an empty working tree and the workflow's rc-67
    # guard fired ("LEX_ZERO_DELTA_REPAIR", exit 67, OBSERVED via public
    # annotations); the run failed before state validation, write-scope and
    # audit, the team ref was persist-published byte-identical to
    # 40737328834's, and the run is UNADJUDICATED with ZERO durable delta.
    # Factory-wide requirement 10 binds: rc-67 means "the producer found
    # nothing to do" — an orchestration/dispatch fact, NOT a product defect.
    # No report of record was produced under this id (zero-delta); the
    # operational resume 40750177292 carries the chain record.
    "40747546909": {
        "resumed_run_id": "40737328834",
        "predecessor_run_id": "40726216925",
        "raw": ORCH / "CYCLE_40737328834_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40737328834_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40737328834.md",
        "current_report": None,
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "failed_job": "audit",
        "mechanism_kind": "observed",
        "delta_kind": "committed",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 7,
        "changed_paths_include": (
            "reports/product/CYCLE_40737328834.md",
            "results/product/audit_readiness/"
            "CYCLE_40737328834_audit_readiness.json",
            "state/product.json",
        ),
        "cycle_test": None,
        "state_block": "cycle_40747546909_operational_resume",
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40718103891.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    # Active cycle 40750177292: operational resume of the zero-delta
    # misroute 40747546909.  Resumed run = 40747546909 (rc-67
    # LEX_ZERO_DELTA_REPAIR, OBSERVED_ZERO_DELTA_REPAIR_GUARD_EXIT_67,
    # zero durable delta over 40737328834's team head 866ae3cb); the chain
    # ahead of accepted 7be4480e remains UNADJUDICATED pending the
    # INDEPENDENT AUDIT of the committed snapshot.  This cycle's binding
    # deliverable is the single-command bounded audit route
    # (product/audit_route.py + CYCLE_40750177292_AUDIT_ROUTE.json) built
    # after three consecutive audit-side quantum deaths.
    "40750177292": {
        "resumed_run_id": "40747546909",
        "predecessor_run_id": "40737328834",
        "raw": ORCH / "CYCLE_40747546909_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40747546909_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40737328834.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40750177292.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "mechanism_kind": "observed_zero_delta_guard",
        "delta_kind": "zero",
        "exit_code": 67,
        "cycle_test": "product/tests/test_cycle_40750177292.py",
        "state_block": "cycle_40750177292_operational_resume",
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40718103891.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    # Predecessor entry 40763434744: operational resume of run 40750177292,
    # whose TEAM job was fully green (all steps success incl. state
    # validation, write scope and persist) with a 13-file committed delta
    # 85dfea22 over predecessor team head 866ae3cb, and whose AUDIT
    # "Independent audit" step then died at the 2700 s work quantum (exit 78,
    # 2706.0 s, OBSERVED_QUANTUM_EXPIRED via public check-run annotations)
    # before writing any gate.  The gate and persist steps were skipped and
    # the run is UNADJUDICATED.  This was the FOURTH audit-side quantum death
    # on this lineage (after 40702698815, 40726216925, 40737328834) and the
    # first one whose tree already carried the bounded audit route; the
    # producer cannot observe whether the auditor consumed it (logs HTTP
    # 403), and the route-around is a named, git-resolved audit target plus
    # an intake file, never a verdict.
    "40763434744": {
        "resumed_run_id": "40750177292",
        "predecessor_run_id": "40747546909",
        "raw": ORCH / "CYCLE_40750177292_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40750177292_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40750177292.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40763434744.md",
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "failed_job": "audit",
        "mechanism_kind": "observed",
        "delta_kind": "committed",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 13,
        "changed_paths_include": (
            "product/audit_route.py",
            "reports/product/CYCLE_40750177292.md",
            "results/product/audit_readiness/"
            "CYCLE_40750177292_AUDIT_ROUTE.json",
            "state/product.json",
        ),
        "cycle_test": "product/tests/test_cycle_40763434744.py",
        "state_block": "cycle_40763434744_operational_resume",
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40718103891.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    # Active cycle 40772551540: operational resume of run 40763434744, whose
    # TEAM job was fully green (14-file committed delta 953c2e71 over
    # 85dfea22) and whose AUDIT "Independent audit" step then died at the
    # 2700 s work quantum (2704.0 s, exit 78, OBSERVED_QUANTUM_EXPIRED via
    # public check-run annotations) before writing any gate.  This is the
    # FIFTH audit-side quantum death on this lineage.  The repair this cycle
    # is the WORKSPACE CONTRACT in product/audit_route.py: the audit job's
    # CWD is the accepted-base checkout (which lacks audit_route.py and has
    # no pinned python deps), the producer snapshot is mounted at
    # /tmp/lex_team, and the brief/intake now prefix every command with
    # `cd /tmp/lex_team &&` and lead with product/bootstrap_query_env.sh.
    "40772551540": {
        "resumed_run_id": "40763434744",
        "predecessor_run_id": "40750177292",
        "raw": ORCH / "CYCLE_40763434744_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40763434744_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40763434744.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40772551540.md",
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "failed_job": "audit",
        "mechanism_kind": "observed",
        "delta_kind": "committed",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 14,
        "changed_paths_include": (
            "product/audit_route.py",
            "reports/product/CYCLE_40763434744.md",
            "state/product.json",
        ),
        "cycle_test": "product/tests/test_cycle_40772551540.py",
        "state_block": "cycle_40772551540_operational_resume",
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40718103891.json",
        "content_family_expected": {
            "n_bundles": 52,
            "n_decisions": 5200,
            "n_verified": 55,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    # Active cycle 40783679367: a fresh producer re-dispatch of the completed
    # producer snapshot after the fifth audit quantum death.  Its TEAM job was
    # fully green and persisted a 25-file committed delta c73d9d84 over
    # d1f2356a, but the delta is CACHE_REFRESH only (22 fetched_at-only cache
    # envelopes + 3 upstream citation_count drifts, 0 product code/test/
    # report/state/artifact, 0 manifest-covered); see
    # results/product/orchestration/CYCLE_40783679367_delta_substance.json.
    # Its AUDIT "Independent audit" step then died at the 2700 s work quantum
    # (2705.0 s, exit 78, OBSERVED_QUANTUM_EXPIRED via public check-run
    # annotations) before writing any gate.  This is the SIXTH audit-side
    # quantum death on this lineage.  The product repair this cycle is the
    # read-only delta-substance instrument, which makes cache churn
    # mechanically distinguishable from product work.
    "40783679367": {
        "resumed_run_id": "40783679367",
        "predecessor_run_id": "40772551540",
        "raw": ORCH / "CYCLE_40783679367_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40783679367_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40772551540.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40783679367.md",
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "failed_job": "audit",
        "mechanism_kind": "observed",
        "delta_kind": "committed",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 25,
        "changed_paths_include": ("results/product/query_cache/",),
        "cycle_test": "product/tests/test_cycle_40783679367.py",
        "state_block": "cycle_40783679367_operational_resume",
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40783679367.json",
        "content_family_expected": {
            "n_bundles": 55,
            "n_decisions": 5500,
            "n_verified": 64,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
    # Active cycle 40799296211: operational resume of run 40791850481
    # (itself repair round 0 of the unadjudicated cycle 40783679367).  The
    # resumed TEAM job was fully green and its own delta over the
    # repair base c73d9d84 is SUBSTANTIVE (17 files: audit_route/delta
    # instrument, two test modules, report, dossier/route/intake, two offline
    # slice bundles, the 58-bundle content family, raw/diagnosis and state) --
    # this is the completed 40783679367-cycle deliverable, not a cache
    # refresh (the 25-file CACHE_REFRESH belongs to the PRIOR run).  Its AUDIT
    # "Independent audit" step then died at the 2700 s work quantum (2705.0 s,
    # exit 78, OBSERVED_QUANTUM_EXPIRED via public check-run annotations)
    # before writing any gate.  Validation defect repaired by this resume: the
    # snapshot labelled every artifact with the repaired cycle id 40783679367,
    # so `audit_route.py` keyed to the dispatching run id named files that
    # did not exist.  The CURRENT run is 40799296211; this profile keys the
    # dossier to that id while keeping the resumed run as 40791850481.
    "40799296211": {
        "resumed_run_id": "40791850481",
        "predecessor_run_id": "40783679367",
        "raw": ORCH / "CYCLE_40791850481_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40791850481_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40783679367.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40799296211.md",
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "failed_job": "audit",
        "mechanism_kind": "observed",
        "delta_kind": "committed",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 17,
        "changed_paths_include": (
            "product/audit_readiness.py",
            "reports/product/CYCLE_40783679367.md",
            "results/product/orchestration/"
            "CYCLE_40783679367_resume_diagnosis.json",
            "state/product.json",
        ),
        "cycle_test": "product/tests/test_cycle_40799296211.py",
        "state_block": "cycle_40799296211_operational_resume",
        "content_family": ROOT / "results" / "product"
                          / "counter_content_family"
                          / "CYCLE_40799296211.json",
        "content_family_expected": {
            "n_bundles": 58,
            "n_decisions": 5800,
            "n_verified": 67,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
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
    "product/tests/test_audit_readiness_verify.py",
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
    elif mechanism_kind == "observed_audit_scope":
        # Sixth real failure mode, observed on run 40427889739: the audit
        # job's "Independent audit" agent step SUCCEEDED, then the workflow's
        # "Enforce audit scope and read gate" step failed (annotation "auditor
        # crossed scope:", exit 3).  The always-run persist step was skipped,
        # so no audit ref and no gate exist.  This is an AUDITOR write-scope
        # failure, not a product rejection, and it must not be described with
        # the producer-minted-gate wording of "observed_scope".
        mechanism = orch.get("mechanism") or {}
        audit = orch.get("audit") or {}
        exit_code = p("exit_code")
        failed_audit_step = p("audit_failed_step",
                              "Enforce audit scope and read gate")
        if mechanism.get("status") != "OBSERVED_AUDIT_SCOPE_ENFORCEMENT_FAILED":
            problems.append("mechanism_status")
        if mechanism.get("logs_available") is not False:
            problems.append("logs_available")
        if mechanism.get("logs_endpoint_status") != 403:
            problems.append("logs_endpoint_status")
        if mechanism.get("quantum_expired") is not False:
            problems.append("quantum_expired")
        if mechanism.get("exit_code") != exit_code:
            problems.append("exit_code")
        if audit.get("failed_step") != failed_audit_step:
            problems.append("audit_failed_step")
        if audit.get("gate_step") != "failure":
            problems.append("gate_step")
        if audit.get("persist_step") != "skipped":
            problems.append("persist_step")
        if audit.get("gate_file_written") is not False:
            problems.append("gate_file_written")
        if not audit.get("independent_audit_step_seconds"):
            problems.append("independent_audit_step_seconds")
        # Cross-check the raw snapshot the profile names: the agent step must
        # read success, the gate step failure, and the persist step skipped.
        # The public annotation must name the scope violation and exit code.
        if raw is not None and raw.is_file():
            raw_doc = _load(raw)
            raw_audit = next((j for j in raw_doc.get("jobs") or []
                              if j.get("name") == "audit"), None)
            steps = {s.get("name"): s.get("conclusion")
                     for s in (raw_audit or {}).get("steps") or []}
            if steps.get("Independent audit") != "success":
                problems.append("raw_audit_step_not_success")
            if steps.get(failed_audit_step) != "failure":
                problems.append("raw_gate_step_not_failure")
            if steps.get("Persist audit snapshot") != "skipped":
                problems.append("raw_persist_step_not_skipped")
            anns = ((raw_doc.get("annotations") or {})
                    .get(str((raw_audit or {}).get("id"))) or [])
            messages = " ".join(str(a.get("message") or "")
                                for a in anns if isinstance(a, dict))
            if "auditor crossed scope" not in messages.lower():
                problems.append("raw_scope_annotation_missing")
            if f"exit code {exit_code}" not in messages.lower():
                problems.append("raw_exit_annotation_missing")
        else:
            problems.append("raw_snapshot_missing")
    elif mechanism_kind == "observed_steps":
        # Fifth real failure mode, observed on run 40423595480: the public jobs
        # API fixes WHICH step failed (``Run lane cycle``) and that the always-
        # run persist step still published the tree, but the logs endpoint
        # returned HTTP 403 in this environment, so the log-level cause stays
        # UNOBSERVED.  Neither the quantum kind nor the scope kind describes
        # it, and the raw-free kind would deny the step facts that WERE
        # observed.
        mechanism = orch.get("mechanism") or {}
        team = orch.get("team") or {}
        if mechanism.get("status") != "UNOBSERVED":
            problems.append("mechanism_status")
        if mechanism.get("logs_available") is not False:
            problems.append("logs_available")
        if mechanism.get("logs_endpoint_status") != 403:
            problems.append("logs_endpoint_status")
        if mechanism.get("quantum_expired") is not False:
            problems.append("quantum_expired")
        if team.get("failed_step") != "Run lane cycle":
            problems.append("failed_step")
        if team.get("team_snapshot_persisted") is not True:
            problems.append("team_snapshot_persisted")
        if team.get("team_snapshot_persisted_after_failed_team_job") is not True:
            problems.append("team_snapshot_persisted_after_failure")
        if team.get("producer_state_validation_step_conclusion") != "skipped":
            problems.append("producer_state_validation")
        if (orch.get("audit") or {}).get("conclusion") != "skipped":
            problems.append("audit_not_skipped")
        if (orch.get("audit") or {}).get("gate_file_written") is not False:
            problems.append("gate_file_written")
        # Cross-check the raw snapshot the profile names: the failed step and
        # the always-run persist step must agree with the diagnosis.
        if raw is not None and raw.is_file():
            raw_doc = _load(raw)
            raw_team = next((j for j in raw_doc.get("jobs") or []
                             if j.get("name") == "team"), None)
            steps = {s.get("name"): s.get("conclusion")
                     for s in (raw_team or {}).get("steps") or []}
            if steps.get("Run lane cycle") != "failure":
                problems.append("raw_lane_cycle_not_failure")
            if steps.get("Persist team snapshot") != "success":
                problems.append("raw_persist_step_not_success")
        else:
            problems.append("raw_snapshot_missing")
    elif mechanism_kind == "observed_zero_delta_guard":
        # Seventh real failure mode, observed on run 40747546909: the lane
        # re-dispatched a PRODUCER repair round straight after run
        # 40737328834's audit-side quantum death; the producer correctly
        # found nothing to add to an already audit-ready snapshot, so HEAD
        # stayed unchanged with an empty working tree and the workflow's own
        # rc-67 guard fired, announced by the public annotations
        # "Process completed with exit code 67." + "LEX_ZERO_DELTA_REPAIR".
        # Factory-wide requirement 10 defines the signature: it means "the
        # producer found nothing to do", NOT a product defect and NOT a
        # verdict.  The cross-check pins the sentinel text in the raw
        # annotations so a future UNOBSERVED reclassification cannot pass.
        mechanism = orch.get("mechanism") or {}
        team = orch.get("team") or {}
        exit_code = p("exit_code", 67)
        if (mechanism.get("status")
                != "OBSERVED_ZERO_DELTA_REPAIR_GUARD_EXIT_67"):
            problems.append("mechanism_status")
        if mechanism.get("quantum_expired") is not False:
            problems.append("quantum_expired")
        if mechanism.get("exit_code") != exit_code:
            problems.append("exit_code")
        if team.get("failed_step") != "Run lane cycle":
            problems.append("failed_step")
        if team.get("team_snapshot_persisted_after_failed_team_job") is not True:
            problems.append("team_snapshot_persisted_after_failure")
        if (orch.get("audit") or {}).get("conclusion") != "skipped":
            problems.append("audit_not_skipped")
        if (orch.get("audit") or {}).get("gate_file_written") is not False:
            problems.append("gate_file_written")
        if raw is not None and raw.is_file():
            raw_doc = _load(raw)
            raw_team = next((j for j in raw_doc.get("jobs") or []
                             if j.get("name") == "team"), None)
            anns = ((raw_doc.get("annotations") or {})
                    .get(str((raw_team or {}).get("id"))) or [])
            messages = " ".join(str(a.get("message") or "")
                                for a in anns if isinstance(a, dict))
            if "LEX_ZERO_DELTA_REPAIR" not in messages:
                problems.append("raw_zero_delta_sentinel_missing")
            if f"exit code {exit_code}" not in messages.lower():
                problems.append("raw_exit_annotation_missing")
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
    elif mechanism_kind == "observed_audit_scope":
        summary = (f"Resumed run {resumed_id}: independent-audit agent step "
                   "succeeded, then the audit job failed at write-scope "
                   "enforcement ('auditor crossed scope', exit 3), the persist "
                   "step was skipped, no gate/audit ref exists, durable delta "
                   "present, run unadjudicated")
    elif mechanism_kind == "observed_steps":
        # The zero-delta tree is byte-identical to the PREDECESSOR's team
        # head.  For most historical profiles that predecessor was the
        # accepted head, but an operational-resume lineage can sit ahead of
        # the accepted head, and a summary that says otherwise would not
        # reproduce.  Profiles override ``zero_delta_reference``; the default
        # keeps the original wording byte-for-byte.
        zero_ref = p("zero_delta_reference", "the accepted head")
        summary = (f"Resumed run {resumed_id}: team job failed at 'Run lane "
                   "cycle' (jobs API observed; logs endpoint HTTP 403, so no "
                   "cause is asserted), always-run persist step published a "
                   f"tree byte-identical to {zero_ref}, zero durable "
                   "delta, run unadjudicated")
    elif mechanism_kind == "observed_zero_delta_guard":
        summary = (f"Resumed run {resumed_id}: rc-67 LEX_ZERO_DELTA_REPAIR "
                   "guard observed via public annotations (producer found "
                   "nothing to do — dispatch-routing fact, not a defect); "
                   "team ref carries zero durable delta over its "
                   "predecessor, run unadjudicated")
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
    if mechanism_kind == "observed_audit_scope":
        guard = ROOT / "product" / "audit_scope_guard.py"
        if guard.is_file():
            evidence.append(str(guard.relative_to(ROOT)))
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


def check_audit_namespace(run_id: str) -> dict[str, Any]:
    gate = ROOT / "results" / "audit" / "product" / f"CYCLE_{run_id}_GATE.json"
    report = (ROOT / "reports" / "audit" / "product"
              / f"CYCLE_{run_id}.md")
    pending = subprocess.run(
        ["git", "status", "--porcelain", "-uall"], cwd=str(ROOT),
        capture_output=True, text=True, check=False,
    ).stdout.splitlines()
    producer_audit = [line[3:] for line in pending
                      if line[3:].startswith(("results/audit/product/",
                                              "reports/audit/product/"))]
    ok = not gate.exists() and not report.exists() and not producer_audit
    return _check(
        "audit_namespace",
        "Producer wrote no auditor-namespace path and minted no gate",
        ok,
        {"gate_exists": gate.exists(), "report_exists": report.exists(),
         "pending_audit_paths": producer_audit},
        [str(gate.relative_to(ROOT)), str(report.relative_to(ROOT))],
    )


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
        # A zero-delta misroute profile (e.g. 40747546909) legitimately has
        # no cycle test of its own: the run committed nothing.  Passing
        # str(None) would look for a literal "None.py" and fail the dossier
        # for the wrong reason, so the absent case is a recorded skip.
        _cycle_test = p("cycle_test")
        if _cycle_test:
            checks.append(check_cycle_test(str(_cycle_test)))
        else:
            checks.append(_skip(
                "cycle_test",
                "Cycle test exists and is green",
                "no cycle test is claimed by this profile (zero-delta "
                "misroute run; the resume cycle's own test covers the "
                "chain)"))
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
    checks.append(check_audit_namespace(run_id))

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
    elif mechanism_kind == "observed_audit_scope":
        orch = resumed.get("orchestration") or {}
        audit = orch.get("audit") or {}
        c1_claim = (
            f"Run {resumed_id}'s 'Independent audit' agent step SUCCEEDED "
            f"({audit.get('independent_audit_step_seconds')} s), and the "
            f"audit job then died at "
            f"'{audit.get('failed_step', 'Enforce audit scope and read gate')}' "
            f"(exit {p('exit_code', 3)}) with the public check-run annotation "
            "'auditor crossed scope:'. The per-path list is not exposed in "
            "the public annotation and job logs are not downloadable here "
            "(HTTP 403). The always-run 'Persist audit snapshot' step was "
            "skipped, so no audit ref and no gate exists; the run is "
            "UNADJUDICATED. This is an AUDITOR write-scope failure, not a "
            "product rejection. product/audit_scope_guard.py makes the two "
            "allowed prefixes (results/audit/product/, reports/audit/product/) "
            "executable before handoff."
        )
        c1_artifacts = (
            ([str(raw.relative_to(ROOT))] if raw is not None else [])
            + [str(resume_diag.relative_to(ROOT)),
               "product/audit_scope_guard.py"])
    elif mechanism_kind == "observed_steps":
        orch = resumed.get("orchestration") or {}
        team = orch.get("team") or {}
        zero_ref_c1 = p("zero_delta_reference", "the accepted product head")
        c1_claim = (
            f"Run {resumed_id}'s team job failed at "
            f"'{team.get('failed_step', 'Run lane cycle')}' "
            f"({team.get('failed_step_seconds')} s after the step started), "
            "the producer-side state validation and write-scope steps were "
            "skipped, and the always-run persist step still published the "
            "tree. The public jobs API records those step conclusions, but "
            "the job-logs endpoint returned HTTP 403 here, so no provider, "
            "auth or timeout cause is asserted. The published tree is "
            f"byte-identical to {zero_ref_c1}, so the run had "
            "ZERO_DURABLE_DELTA and an audit could add nothing."
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
            "verify_committed_dossier": (
                "python3 product/audit_readiness.py --verify "
                "results/product/audit_readiness/"
                f"CYCLE_{run_id}_audit_readiness.json"
            ),
            "resumed_run_diagnosis": str(resume_diag.relative_to(ROOT)),
            "inherited_report": (str(Path(inherited).relative_to(ROOT))
                                 if inherited else None),
            "current_report": str(Path(
                p("current_report", CURRENT_REPORT)).relative_to(ROOT)),
            "current_cycle_test": f"python3 -m pytest {cycle_test} -q",
            "audit_cost_budget": (
                "MEASURED, so the ~2700 s audit work-quantum is not spent "
                "re-deriving what is already machine-checked: (a) the "
                "sub-second path is `--verify` above — it re-hashes the "
                "dossier's claim artifacts and completed in 0.061 s for the "
                "8 artifacts of the predecessor dossier "
                "CYCLE_40655643086_audit_readiness.json; (b) the full "
                "one-command regeneration runs the state contract, posture "
                "check, claim-artifact derivation, cycle test, progressive "
                "smoke and the bounded MVP core pytest set, and its per-check "
                "wall times are recorded in this dossier's own `checks[].seconds` "
                "fields (order of ~2 minutes total on the producing runner); "
                "(c) do NOT re-run the 153-bundle historical committed sweep — "
                "those D2=44/D3=31/D4=7 rows are preserved historical evidence "
                "under results/product/offline_slice/, not this snapshot's "
                "claim; the claim is the 52-bundle fixed-path family measured "
                "by product/content_family_probe.py in ~24 s. Prefer (a), then "
                "regenerate only the specific check whose hash fails."
            ),
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


def verify_dossier(dossier_path: Path) -> dict[str, Any]:
    """Re-hash a *committed* dossier's ``claim_artifacts`` against the tree.

    A dossier is generated once and then committed; if the report or state is
    edited afterwards the recorded hashes silently become stale (the exact
    defect that rejected cycle 40423889401).  Generation-time hashing cannot
    catch that, so this mode re-reads the committed dossier and compares every
    recorded digest with the bytes now on disk.  It fails closed on a missing
    artifact, a stale hash or a dossier without the claim_artifacts check.
    """
    path = Path(dossier_path)
    if not path.is_file():
        return {"ok": False, "dossier": str(path), "n_checked": 0,
                "problems": [{"path": str(path), "problem": "DOSSIER_MISSING"}]}
    rec = _load(path)
    check = next((c for c in rec.get("checks") or []
                  if c.get("id") == "claim_artifacts"), None)
    if check is None:
        return {"ok": False, "dossier": str(path), "n_checked": 0,
                "problems": [{"path": str(path),
                              "problem": "CLAIM_ARTIFACTS_CHECK_MISSING"}]}
    recorded = ((check.get("detail") or {}).get("sha256") or {})
    problems: list[dict[str, Any]] = []
    for rel, expected in sorted(recorded.items()):
        candidate = Path(rel)
        target = candidate if candidate.is_absolute() else ROOT / candidate
        if not target.is_file():
            problems.append({"path": rel, "problem": "MISSING"})
            continue
        actual = _sha256(target)
        if actual != expected:
            problems.append({"path": rel, "problem": "STALE",
                             "recorded": expected, "actual": actual})
    return {
        "ok": not problems,
        "dossier": str(path),
        "run_id": rec.get("run_id"),
        "generated_at": rec.get("generated_at"),
        "n_checked": len(recorded),
        "problems": problems,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id")
    ap.add_argument("--out")
    ap.add_argument("--verify", metavar="DOSSIER",
                    help="re-hash a committed dossier's claim artifacts and "
                         "exit non-zero on a missing/stale artifact")
    ap.add_argument("--direction-version", type=int,
                    default=DIRECTION_VERSION)
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--skip-smoke", action="store_true")
    ap.add_argument("--no-bootstrap", action="store_true",
                    help="probe the runtime but do not install the pinned pins")
    args = ap.parse_args(argv)
    if args.verify:
        if args.run_id or args.out:
            ap.error("--verify is exclusive with --run-id/--out")
        verdict = verify_dossier(Path(args.verify))
        print(json.dumps(verdict, indent=2))
        return 0 if verdict["ok"] else 1
    if not args.run_id or not args.out:
        ap.error("--run-id and --out are required unless --verify is used")
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
