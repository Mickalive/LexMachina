#!/usr/bin/env python3
"""Operational-resume state update for GitHub run 40209360877 (resume of 40204378896).

Scope of this file (lane write scope: evaluation/*, state/evaluation.json,
evaluation/state/evaluation.json): advance ONLY the run-identity fields and the
append-only evidence/resume blocks that this run owns. Nothing else is touched.

What it changes, and only this:
  * github_run                 40204378896 -> 40209360877  (both state files;
                               root/lane parity is a frozen gate check)
  * resumed_run_id             40198184759 -> 40204378896  (root, the run we
                               actually resume), with the outgoing value kept
                               append-only under resumed_run_id_previous_40209360877
  * operational_resume_of      40198184759 -> 40204378896  (root)
  * resume_chain               append 40209360877            (root)
  * next_recommendation        prepend the CURRENT RUN 40209360877 paragraph and
                               preserve the whole prior text verbatim after
                               "PRESERVED PRIOR TEXT:" (the established chain)
  * operational_resume_40209360877 block                   (both state files)
  * evidence_refs              append this run's artifacts   (both), with
                               evidence_refs_n re-derived from the list

What it deliberately does NOT change: accepted_run_id, direction_version,
evidence_tier, cycle_status, continue_recommended, human_gate_ready,
machine_gate_ready, the frozen protocol digest, any prior run's block, any
prior run's evidence ref, any file outside state/*.json.

Safety: both state files are verified to round-trip byte-identically through
json.dumps(indent=2, ensure_ascii=False) BEFORE the mutation, so the re-serialise
cannot silently reformat a claim-bearing file.

Run:  python3 evaluation/state_update_40209360877.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT_STATE = REPO / "state" / "evaluation.json"
LANE_STATE = REPO / "evaluation" / "state" / "evaluation.json"

RUN_ID = 40209360877
RESUMED = 40204378896
PREVIOUS_RESUMED = 40198184759
OUT = REPO / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
REPORT = REPO / "reports" / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md"

# This run's own artifacts. Every path here MUST exist by the time the state
# integrity gate and the nested-ref guard run against the updated state, so the
# script refuses to write anything if one of them is missing.
NEW_REFS = [
    "evaluation/OPERATIONAL_RESUME_40209360877_HYPOTHESIS_V1.json",
    "evaluation/OPERATIONAL_RESUME_40209360877_FREEZE_V1.json",
    "evaluation/operational_resume_40209360877.py",
    "evaluation/state_update_40209360877.py",
    f"results/evaluation/operational_resume_{RUN_ID}/diagnosis_{RESUMED}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/prior_pack_integrity_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/falsifier_replay_comparison_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/falsifier_replay/{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/falsifier_replay_postfreeze/{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/command_runtimes_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/state_integrity_gate_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/write_scope_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/write_scope_prestate_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/pytest_targeted_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/pytest_multilingual_provenance_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/nested_refs/{RUN_ID}_nested_evidence_refs.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/run_{RESUMED}_api.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/jobs_{RESUMED}_api.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/run_{RUN_ID}_api.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/jobs_40187594111_api.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/jobs_40192868113_api.json",
    f"results/evaluation/operational_resume_{RUN_ID}/api/jobs_40198184759_api.json",
    f"results/evaluation/operational_resume_{RUN_ID}/summary_{RUN_ID}.json",
    f"results/evaluation/operational_resume_{RUN_ID}/AUDIT_INDEX_{RUN_ID}.json",
    f"reports/evaluation/OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md",
]

NEXT_PARAGRAPH = (
    f"CURRENT RUN {RUN_ID} (operational resume of {RESUMED}): the resumed producer "
    f"snapshot 14b9e9cf is preserved - all 14 artifacts inventoried by the prior "
    "audit pack re-hash byte-identically (PACK_PRESERVED 5/5, including both frozen "
    "rule pins, the measurement of record 40182692670 and all 8 inputs this run froze before inspecting outcomes), and the prior pack's own "
    "claim-bearing report and records are untouched. The prior run's audit failure is "
    "diagnosed as ORCHESTRATION_WORK_QUANTUM_EXPIRED: the 'Independent audit' step took "
    "2704.0s on FOUR consecutive runs (40187594111, 40192868113, 40198184759, "
    f"{RESUMED}) against a 2700s work quantum in origin/main:.github/scripts/run-"
    "ox-with-retry.sh that is an exact multiple of its 15s poll; the gate and persist "
    "steps were skipped, integrate was skipped, no /audit ref exists for any of the "
    "four, so those runs issued NO verdict. Job logs are HTTP 403 without GH_TOKEN, so "
    "the mechanism is inference from public run metadata plus the checked-in wrapper, "
    "never a quoted log line; the class is recorded, .github/** is not edited from this "
    "lane. The frozen smallest falsifier replays and REPRODUCES (24/24 compared fields, "
    "failed gates byte-equal, input_drift=[], PRODUCT_FALSIFIED) - item (1) measurement "
    "unchanged. This run's own state passes state integrity (ALL_CHECKS_PASS 11/11), the "
    "nested-ref guard (0 unresolved) and write scope (SCOPE_CLEAN); the two shim "
    "re-executions of the lane's reuse-first test slices are SHIM_PASS (39 and 26 passed, "
    "0 failed, pytest absent in the producer image, unsupported never counted as passed). "
    "Item (2) remains NOT_YET_DISCRIMINATING. No new same-question cycle; "
    "continue_recommended=false; no 174k rerun; both DO-NOT-SERVE orders stand; "
    "admission fail-closed. The snapshot is AUDIT_READY_PENDING_INDEPENDENT_AUDIT. "
    "PRESERVED PRIOR TEXT: "
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> tuple[str, dict]:
    raw = path.read_text(encoding="utf-8")
    state = json.loads(raw)
    out = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
    if out != raw:
        sys.exit(f"REFUSING: {path} does not round-trip byte-identically; "
                 "a whole-file re-serialise would silently reformat a claim-bearing file")
    return raw, state


def main() -> int:
    missing = [r for r in NEW_REFS if not (REPO / r).is_file()]
    if missing:
        sys.exit("REFUSING: these referenced artifacts do not exist yet:\n  " +
                 "\n  ".join(missing))

    _, root = load(ROOT_STATE)
    _, lane = load(LANE_STATE)

    # ---- run identity (frozen parity: root and lane must agree) -------------
    if root.get("github_run") != RESUMED or lane.get("github_run") != RESUMED:
        sys.exit(f"REFUSING: expected github_run={RESUMED} in both files before the "
                 f"advance, got root={root.get('github_run')} lane={lane.get('github_run')}")
    for st in (root, lane):
        st["github_run"] = RUN_ID

    # ---- root-only narrative/identity fields -------------------------------
    if root.get("resumed_run_id") != PREVIOUS_RESUMED:
        sys.exit(f"REFUSING: expected resumed_run_id={PREVIOUS_RESUMED} before advance, "
                 f"got {root.get('resumed_run_id')!r}")
    root[f"resumed_run_id_previous_{RUN_ID}"] = PREVIOUS_RESUMED
    root["resumed_run_id"] = RESUMED
    root["operational_resume_of"] = RESUMED
    root["prior_resumed_run_id"] = PREVIOUS_RESUMED

    chain = root.setdefault("resume_chain", [])
    if RUN_ID not in chain:
        chain.append(RUN_ID)

    nr = root.get("next_recommendation") or ""
    prefix = f"CURRENT RUN {RUN_ID} (operational resume of {RESUMED}):"
    if nr.startswith(prefix):
        pass
    elif nr.startswith("CURRENT RUN "):
        root["next_recommendation"] = NEXT_PARAGRAPH + nr
    else:
        root["next_recommendation"] = NEXT_PARAGRAPH + nr

    # ---- the new claim block (both files) ---------------------------------
    def stable(name: str) -> str:
        """sha256 of a record inside this run's output directory."""
        return sha256(OUT / name)

    block = {
        "schema": "lex-evaluation-operational-resume/1",
        "run": RUN_ID,
        "run_under_resume": RESUMED,
        "prior_resume_run": RESUMED,
        "direction_version": 68,
        "base_snapshot_commit": "14b9e9cf9d8c4d88f378fd8ae4281d3cbb18c2f5",
        "prior_snapshot_commit": "251a6f5967c653d3ca93bf0a2d3ad7a1dd3f875e",
        "failure_class": "ORCHESTRATION_WORK_QUANTUM_EXPIRED",
        "failure_summary": (
            f"Run {RESUMED}'s producer team job succeeded and persisted snapshot "
            "14b9e9cf9d8c4d88f378fd8ae4281d3cbb18c2f5; its independent-audit job failed "
            "at step 'Independent audit' after 2704.0s (2700s wrapper quantum + ~4s step "
            "setup, quantum an exact multiple of the 15s poll), the gate and persist "
            "steps were skipped, integrate was skipped, and no /audit ref exists for any "
            "of the four consecutive 2704.0s runs, so no verdict was issued. This is an "
            "orchestration/provider-class starvation, not a producer failure, not a "
            "validation failure and not a product defect. Job logs are HTTP 403 without "
            "GH_TOKEN, so the mechanism is inference from public run metadata plus the "
            "checked-in wrapper, never a quoted log line. Control-plane fixes are "
            "RECORDED here, never edited from this lane (.github/**)."
        ),
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "evidence_tier": "EXPLORATORY",
        "diagnosis_record":
            f"results/evaluation/operational_resume_{RUN_ID}/diagnosis_{RESUMED}.json",
        "diagnosis_sha256": stable(f"diagnosis_{RESUMED}.json"),
        "prior_pack_integrity_record":
            f"results/evaluation/operational_resume_{RUN_ID}/prior_pack_integrity_{RUN_ID}.json",
        "prior_pack_integrity_sha256": stable(f"prior_pack_integrity_{RUN_ID}.json"),
        "falsifier_replay_comparison":
            f"results/evaluation/operational_resume_{RUN_ID}/falsifier_replay_comparison_{RUN_ID}.json",
        "falsifier_replay_comparison_sha256": stable(f"falsifier_replay_comparison_{RUN_ID}.json"),
        "falsifier_replay_status": "REPRODUCES",
        "hypothesis_record": "evaluation/OPERATIONAL_RESUME_40209360877_HYPOTHESIS_V1.json",
        "freeze_record": "evaluation/OPERATIONAL_RESUME_40209360877_FREEZE_V1.json",
        "instrument_record": "evaluation/operational_resume_40209360877.py",
        "producer_work_preserved": True,
        "snapshot_integrity": (
            "14/14 prior-audit-pack inventory artifacts byte-identical; 5/5 pack checks "
            "(snapshot is HEAD on branch operational-resume; frozen RULES_LABEL/"
            "RULES_GEOMETRY pins unchanged; measurement of record 40182692670 unchanged; "
            "all 8 inputs this run froze before inspecting outcomes still hash to their "
            "frozen values; accepted-cycle gate 40159747851 in tree). state/evaluation.json "
            "and evaluation/state/evaluation.json are deliberately excluded from byte "
            "identity: a resume necessarily advances them, and their prior bytes stay "
            "readable at 14b9e9cf."
        ),
        "verification": {
            "diagnosis": "DIAGNOSIS_CONFIRMED 11/11 checks",
            "prior_pack_integrity": "PACK_PRESERVED 5/5 checks",
            "falsifier_replay_comparison": (
                "REPRODUCES 24/24 compared fields byte-equal against the committed "
                "measurement of record; failed gate ids identical; input_drift=[]; "
                "PRODUCT_FALSIFIED (exit 1 = VERDICT_CONTRACT)"
            ),
            "state_integrity_gate": "ALL_CHECKS_PASS 11/11",
            "nested_evidence_refs": (
                "NESTED_REFS_RESOLVED with 0 unresolved; per-pass counts are in the "
                "record, which this run's final verify pass regenerates"
            ),
            "write_scope": "SCOPE_CLEAN, 0 bad entries (live mode)",
            "targeted_shim": (
                "SHIM_PASS 39 passed, 0 failed, 12 unsupported (NOT pytest; pytest is "
                "absent in the producer image and unsupported is never counted as passed)"
            ),
            "multilingual_provenance_shim": (
                "SHIM_PASS 26 passed, 0 failed, 2 unsupported; numpy import error and "
                "the class-based collection gap are disclosed, never counted as passes"
            ),
            "records_of_record": (
                "results/evaluation/operational_resume_40209360877/"
                "command_runtimes_40209360877.json and "
                "results/evaluation/operational_resume_40209360877/"
                f"AUDIT_INDEX_{RUN_ID}.json"
            ),
        },
        "posture": {
            "direction_version": 68,
            "accepted_run_id": 40159747851,
            "continue_recommended": False,
            "new_same_question_cycle": False,
            "universal_174k_rerun": False,
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "owner_decision_required": False,
            "do_not_serve_orders": "both stand",
            "item_1": "PRESENT_AND_VERIFIED, measurement unchanged",
            "item_2": "NOT_YET_DISCRIMINATING",
        },
        "network_call_disclosure": {
            "no_network_calls": False,
            "calls": [
                "HTTPS GET https://api.github.com/repos/Mickalive/LexMachina/actions/runs/"
                "<id>[/jobs] (public, unauthenticated) for runs 40187594111, 40192868113, "
                "40198184759, 40204378896 and 40209360877",
                "git ls-remote --heads origin refs/heads/cycle/core/evaluation/*/audit "
                "(five audit-ref probes)",
            ],
            "scope": (
                "public GitHub REST run/job metadata and ref existence probes only; no "
                "OpenCaseLaw, no retrieval corpus, no model, no benchmark data call"
            ),
            "why": (
                "the job-log endpoint returns HTTP 403 unauthenticated and GH_TOKEN is "
                "unset in this producer job, so step durations had to be derived from the "
                "public run metadata instead of from logs"
            ),
            "record": f"results/evaluation/operational_resume_{RUN_ID}/api/",
        },
        "control_plane_hardening_recorded_not_edited": [
            "Raise LEX_AGENT_QUANTUM_SECONDS for the independent_auditor agent, split the "
            "audit into a short first pass, or hand the auditor a pre-verified pack (this "
            "run publishes exactly that pack).",
            "Export per-step durations publicly, or grant the auditor an actions:read "
            "token, so the next starvation is log-quotable instead of inferred.",
        ],
        "report": f"reports/evaluation/OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md",
        "summary_record": f"results/evaluation/operational_resume_{RUN_ID}/summary_{RUN_ID}.json",
        "audit_index_record":
            f"results/evaluation/operational_resume_{RUN_ID}/AUDIT_INDEX_{RUN_ID}.json",
        "claim_ceiling": (
            "Operational-resume verification only. It preserves accepted cycle 40159747851, "
            "the 40105794124/40182692670 measurement and the prior pack byte-for-byte, keeps "
            "item (2) NOT_YET_DISCRIMINATING, moves no frozen bar, issues no serve verdict, "
            "lifts no DO-NOT-SERVE order, opens no new same-question cycle, runs no 174k "
            "benchmark, and creates no audit gate file (only the independent auditor does)."
        ),
    }

    for st in (root, lane):
        st[f"operational_resume_{RUN_ID}"] = block

    # ---- evidence refs (append-only, n re-derived) ------------------------
    added = []
    for st_name, st in (("root", root), ("lane", lane)):
        refs = st.setdefault("evidence_refs", [])
        for r in NEW_REFS:
            if r not in refs:
                refs.append(r)
                added.append((st_name, r))
        st["evidence_refs_n"] = len(refs)

    for path, state in ((ROOT_STATE, root), (LANE_STATE, lane)):
        text = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
        path.write_text(text, encoding="utf-8")
        # re-verify the canonical indent contract of the state integrity gate
        for i, line in enumerate(text.splitlines(), 1):
            if line.startswith('"evidence_refs": ['):
                sys.exit(f"canonical indent broken at {path}:{i}")

    print(json.dumps({
        "status": "STATE_UPDATED",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "github_run": {"root": root["github_run"], "lane": lane["github_run"]},
        "resume_chain_tail": root["resume_chain"][-3:],
        "evidence_refs_n": {"root": root["evidence_refs_n"],
                            "lane": lane["evidence_refs_n"]},
        "n_refs_added_per_file": len(NEW_REFS),
        "added_examples": added[:3],
        "next_recommendation_bytes": len(root["next_recommendation"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
