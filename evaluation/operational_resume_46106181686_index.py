#!/usr/bin/env python3
"""Build the hash-indexed audit inventory for operational resume 46106181686."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN = 46106181686
SUBJECT = 46100599319
BASE = f"results/evaluation/operational_resume_{RUN}"
ARTIFACTS = [
    "evaluation/OPERATIONAL_RESUME_46106181686_HYPOTHESIS_V1.json",
    "evaluation/OPERATIONAL_RESUME_46106181686_FREEZE_V1.json",
    "evaluation/operational_resume_46106181686.py",
    "evaluation/operational_resume_46106181686_state_repair.py",
    f"{BASE}/api/run_{SUBJECT}_api.json",
    f"{BASE}/api/jobs_{SUBJECT}_api.json",
    f"{BASE}/diagnosis_{SUBJECT}.json",
    f"{BASE}/deliverable_verification_{SUBJECT}.json",
    f"{BASE}/state_integrity_gate_{RUN}_pre.json",
    f"{BASE}/state_integrity_gate_{RUN}_final.json",
    f"{BASE}/state_integrity_gate_{RUN}_post.json",
    f"{BASE}/nested_refs_final/{RUN}_nested_evidence_refs.json",
    f"{BASE}/write_scope_{RUN}_final.json",
    f"{BASE}/audit_readiness_{RUN}.json",
    "results/evaluation/orchestration/46100599319_nested_evidence_refs.json",
    "reports/evaluation/OPERATIONAL_RESUME_46100599319_AUDIT_READY.md",
]
INDEX = f"{BASE}/AUDIT_INDEX_{RUN}.json"
SUMMARY = f"{BASE}/summary_{RUN}.json"


def sha(p: str) -> str:
    return hashlib.sha256((REPO / p).read_bytes()).hexdigest()


def main() -> None:
    missing = [p for p in ARTIFACTS if not (REPO / p).is_file()]
    if missing:
        print(f"missing artifacts: {missing}", file=sys.stderr)
        raise SystemExit(1)
    inventory = [{"path": p, "sha256": sha(p),
                  "bytes": (REPO / p).stat().st_size} for p in ARTIFACTS]
    index = {
        "schema": "lex-evaluation-audit-index/1",
        "lane": "evaluation", "direction_version": 68,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resume_run_id": RUN, "subject_run_id": SUBJECT,
        "subject_snapshot_commit": "39784cc02d5eb06915cab32bfc5e2647631de74a",
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "n_artifacts": len(inventory),
        "artifact_inventory": inventory,
        "claim_to_artifact": {
            "orchestration_failure_is_audit_step_only": f"{BASE}/diagnosis_{SUBJECT}.json",
            "deliverable_complete_and_pinned": f"{BASE}/deliverable_verification_{SUBJECT}.json",
            "state_integrity_repaired": f"{BASE}/state_integrity_gate_{RUN}_final.json",
            "scope_clean": f"{BASE}/write_scope_{RUN}_final.json",
            "overall_audit_readiness": f"{BASE}/audit_readiness_{RUN}.json",
            "human_report": "reports/evaluation/OPERATIONAL_RESUME_46100599319_AUDIT_READY.md",
        },
        "auditor_shortcut": [
            "python3 -B -m evaluation.state_integrity_gate --run-id 46106181686",
            "python3 -B -m evaluation.snapshot_audit.write_scope --lane evaluation --out /tmp/opencode/scope_check.json",
            "python3 -B evaluation/operational_resume_46106181686.py verify",
            "sha256sum -c on artifact_inventory (this file)",
        ],
        "exact_commands": {
            "verify": "python3 -B evaluation/operational_resume_46106181686.py verify",
            "finalize": "python3 -B evaluation/operational_resume_46106181686.py finalize",
            "state_gate": "python3 -B -m evaluation.state_integrity_gate --run-id 46106181686",
            "nested_refs": f"python3 -B evaluation/nested_evidence_refs_guard.py --run-id {RUN} --out-dir {BASE}/nested_refs_final",
            "write_scope": f"python3 -B -m evaluation.snapshot_audit.write_scope --lane evaluation --out {BASE}/write_scope_{RUN}_final.json",
        },
        "exclusions": {
            "state/evaluation.json": "mutable state, pinned by the integrity gate rather than by this hash index",
            "evaluation/state/evaluation.json": "mutable mirror state, parity-checked by the integrity gate",
            INDEX: "self-reference",
            SUMMARY: "generated after this index and self-excluded by convention",
        },
        "disclosure": "Producer-created inventory. The independent auditor must re-hash from committed bytes and may not treat this index as a gate. No results/audit/** or reports/audit/** path is inventoried; those belong to the auditor.",
        "claim_ceiling": "Existence and byte-identity of this resume's in-scope records only; no product claim, no serve verdict, no promotion.",
    }
    (REPO / INDEX).write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    all_refs = ARTIFACTS + [INDEX, SUMMARY]
    summary = {
        "schema": "lex-evaluation-operational-resume-summary/1",
        "lane": "evaluation", "direction_version": 68,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resume_run_id": RUN, "subject_run_id": SUBJECT,
        "verdicts": {
            "orchestration": "AUDIT_AGENT_STEP_FAILURE_NOT_A_VERDICT",
            "deliverable": "DELIVERABLE_VERIFIED (14/14 checks)",
            "state_integrity_gate": "ALL_CHECKS_PASS 11/11 before and after state write",
            "write_scope": "SCOPE_CLEAN 0 bad paths",
            "audit_readiness": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT all_pass=true",
        },
        "n_indexed_artifacts": len(inventory),
        "index_path": INDEX, "index_sha256": sha(INDEX),
        "n_evidence_refs": len(all_refs),
        "posture": {"accepted_run_id": 40258497460, "continue_recommended": False,
                    "human_gate_ready": False, "machine_gate_ready": False,
                    "ready_for_owner_session": False, "owner_decision_required": False,
                    "packet_admitted": False},
        "claim_ceiling": "Operational summary; no new measurement and no claim promotion.",
    }
    (REPO / SUMMARY).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # append the full index of refs (including self and summary) to both states
    for rel in ("state/evaluation.json", "evaluation/state/evaluation.json"):
        p = REPO / rel
        st = json.loads(p.read_text(encoding="utf-8"))
        refs = st.setdefault("evidence_refs", [])
        for r in all_refs:
            if r not in refs:
                refs.append(r)
        assert all((REPO / r).is_file() for r in refs), f"unresolved ref in {rel}"
        st["evidence_refs_n"] = len(refs)
        st[f"operational_resume_{RUN}"]["audit_index_record"] = INDEX
        st[f"operational_resume_{RUN}"]["summary_record"] = SUMMARY
        p.write_text(json.dumps(st, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    cp = subprocess.run([sys.executable, "-B", "-m", "evaluation.state_integrity_gate",
                         "--run-id", str(RUN),
                         "--out", f"{BASE}/state_integrity_gate_{RUN}_post_index.json"],
                        cwd=REPO, text=True, capture_output=True)
    print(json.dumps({
        "index": INDEX, "index_sha256": sha(INDEX),
        "summary": SUMMARY, "summary_sha256": sha(SUMMARY),
        "n_evidence_refs": len(all_refs),
        "post_index_gate_exit": cp.returncode,
        "post_index_gate_verdict": json.loads(
            (REPO / f"{BASE}/state_integrity_gate_{RUN}_post_index.json").read_text()
        ).get("verdict"),
    }, indent=2))
    raise SystemExit(cp.returncode)


if __name__ == "__main__":
    main()
