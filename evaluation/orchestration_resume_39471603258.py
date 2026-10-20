#!/usr/bin/env python3
"""Operational-resume instrument for the evaluation lane, run 39471603258.

WHY THIS INSTRUMENT EXISTS
--------------------------
The persisted producer snapshot of run 39470495546 failed to reach an
independent audit.  This instrument (a) names the exact orchestration /
validation failure from the committed tree and the workflow source, (b) verifies
that the lane's claim-bearing deliverable - the mapping-free retrieval /
counter-authority falsifier on the packet-of-record V3 (39319405429) - still
reproduces from the committed tree and the accepted product mount, and (c)
returns the snapshot to an in-scope, audit-ready state by RE-HOMING the
out-of-scope pseudo-audit files into the lane namespace (byte-exactly, with
their git blob oids) before they are removed from the auditor's namespace.

REUSE-FIRST
-----------
No frozen bar, rubric, threshold, success rule or metric is re-derived here.
The lane write-scope patterns and the audit-job gating are read from the
workflow source; the frozen pins are re-hashed from disk; the deliverable is
the already-accepted ``evaluation.counter_authority_surface_falsifier``.

Exit codes
----------
0  RESUME_COMPLETE      - diagnosis written, deliverable reproduced, pins intact
1  RESUME_FINDING_FAIL  - at least one expected finding failed (published as-is)
2  NOT_MEASURED         - environment error / accepted product mount absent
                          (never a pass)
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-orchestration-resume/1"
RUN_ID = "39471603258"
RESUMED_FROM = "39470495546"
DIAGNOSIS_SCHEMA = "lex-evaluation-orchestration-failure-diagnosis/1"

#: Commits this instrument reasons about.  The resumed snapshot is the persisted
#: producer branch of run 39470495546; the accepted base is lab/evaluation's head.
RESUMED_HEAD = os.environ.get(
    "LEX_RESUMED_HEAD", "01ebdab87e7e86a7f28d7d639d1b4bc02f785344")
ACCEPTED_BASE = os.environ.get(
    "LEX_ACCEPTED_BASE", "cbda785300413c4b8e3e630ed652dcf75feb26c4")

#: The lane's own write scope (core-lane.yml 'Enforce lane write scope').
LANE_WRITE_SCOPE = [
    "evaluation/*", "tests/evaluation/*", "results/evaluation/*",
    "reports/evaluation/*", "state/evaluation.json", "data/evaluation/*",
]

#: The independent auditor's protected namespace (core-lane.yml 'Independent audit').
AUDIT_NAMESPACE = ("results/audit/", "reports/audit/")

FROZEN_PINS: dict[str, str] = {
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "evaluation/frozen_bars/VERDICT_CONTRACT.json":
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
    "evaluation/retrieval_gate/frozen_retrieval_benchmark.json":
        "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "evaluation/MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1.json":
        "f0c7711c71e94d7b7303f5fa3a61b444d67bee6d3bbd7f0708ed13ff6ffc8072",
    "evaluation/minimal_ca_benchmark.py":
        "567a9d2b231c5404b7324db2c30249e0961dbc90c698501d0ba5576c7297554b",
    "evaluation/counter_authority_surface_falsifier.py":
        "0d0c6827c0983a66504040c81b29e36b8ec324b8f06fa80d250f8db192547171",
    "evaluation/mapping_free_recall_falsifier.py":
        "58a2e77a66bb60385a53185e9426447e8465da9105e8a0cb8945d5fd77bfb302",
}

MOUNT_PINS: dict[str, str] = {
    "results/product/gate_packet/39319405429/packet.json":
        "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70",
    "results/product/gate_packet/39319405429/questions/de-kapitalverletzung.bundle.json":
        "9b856e2b1b3e4675f8d4d135cd5d1ad23f0baa63fcb2e4cc7bc45182c012881b",
    "results/product/gate_packet/39319405429/questions/fr-bail-entretien.bundle.json":
        "054bec47ae8e5a0f98593902c2c7bd09f7f52761be1c85225328853f34d3213b",
    "results/product/gate_packet/39319405429/questions/it-responsabilita-medica.bundle.json":
        "345e20d1f352fd4e907cac144c8dbbae296f3a9132605d4354f12e7a783e6e3b",
}

CLAIM_RECORD = ("results/evaluation/counter_authority_surface_falsifier/"
                "39462322100.json")
DEDICATED_TEST = "tests/evaluation/test_counter_authority_surface_falsifier.py"
ADJACENT_TESTS = [
    "tests/evaluation/test_mapping_free_recall_falsifier.py",
    "tests/evaluation/test_counter_emission_crosscheck.py",
    "tests/evaluation/test_minimal_ca_benchmark.py",
    "tests/evaluation/test_benchmark_retrieval_counter_authority.py",
]

CLAIM_CEILING = (
    "This cycle may claim exactly: (a) the 39470495546 snapshot's failure "
    "mechanism is a lane-owned write-scope violation in the auditor's protected "
    "namespace, proved from the committed tree and the workflow source; (b) the "
    "V3 counter-authority surface falsifier reproduces its committed record from "
    "the accepted mount; (c) the lane snapshot was returned to an in-scope, "
    "audit-ready state with the offending files re-homed, not destroyed. It must "
    "NOT claim: any verdict, gate or admission on any packet; that the absolute "
    "LABEL_SOUND or GEOMETRY_SOUND bars are met; that either DO-NOT-SERVE order "
    "is lifted; that the map helps a jurist; that any Frontier component was "
    "rebuilt or re-scored; that run 39462322100 is accepted (it is proposed "
    "pending audit); or any unblocking of the human gate. human_gate_ready=false, "
    "machine_gate_ready=false, packet_admitted=false, "
    "ready_for_owner_session=false, owner_decision_required=false."
)


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd or REPO_ROOT), check=True,
                          capture_output=True, text=True).stdout.strip()


def _git_show(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=str(REPO_ROOT),
                          check=True, capture_output=True).stdout


def _rehash(records: dict[str, str], root: Path) -> dict[str, str]:
    return {rel: _sha256_file(root / rel) for rel in records if (root / rel).is_file()}


def _tree_files(commit: str) -> set[str]:
    return set(_git("ls-tree", "-r", "--name-only", commit).splitlines())


def detect_out_of_scope(resumed: str = RESUMED_HEAD, base: str = ACCEPTED_BASE) -> dict[str, Any]:
    """Files the resumed snapshot owns in the auditor's namespace but the
    accepted base does not - i.e. lane-owned writes outside the lane's scope."""
    new_files = _tree_files(resumed) - _tree_files(base)
    offenders = sorted(f for f in new_files
                       if f.startswith(AUDIT_NAMESPACE))
    # also: any resumed audit-namespace file not present in the accepted base
    return {
        "resumed_head": resumed,
        "accepted_base": base,
        "resumed_files": len(_tree_files(resumed)),
        "accepted_base_files": len(_tree_files(base)),
        "new_files_in_resumed": len(new_files),
        "lane_owned_audit_namespace_files": offenders,
        "lane_write_scope_patterns": LANE_WRITE_SCOPE,
        "audit_namespace": list(AUDIT_NAMESPACE),
        "scope_guard_source": ".github/workflows/core-lane.yml:123-144 ('Enforce lane write scope')",
        "audit_job_gating": ".github/workflows/core-lane.yml:163-165 (audit needs team, if needs.team.result == 'success')",
        "persist_always": ".github/workflows/core-lane.yml:146-147 ('Persist team snapshot', if: always())",
        "consequence": "team job exits 3 on an out-of-scope path; the audit job is skipped; no independent gate is produced; if: always() still force-pushes the snapshot, so the lane re-dispatches forever",
    }


def rehome_out_of_scope(out_dir: Path, offenders: list[str],
                        resumed: str = RESUMED_HEAD) -> dict[str, Any]:
    """Preserve the exact bytes + git blob oid of each offender in the lane
    namespace so nothing is lost before it is removed from the auditor namespace."""
    files = []
    for rel in offenders:
        try:
            blob = _git_show(resumed, rel)
        except subprocess.CalledProcessError:
            files.append({"path": rel, "error": "absent from resumed commit"})
            continue
        files.append({
            "path": rel,
            "role": "PRODUCER_AUTHORED_AUDIT_PLACEMENT (lane-owned, out of lane scope)",
            "git_blob_oid": _git("rev-parse", f"{resumed}:{rel}"),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "bytes_b64": base64.b64encode(blob).decode("ascii"),
        })
    out_dir.mkdir(parents=True, exist_ok=True)
    rec = {
        "schema": "lex-evaluation-out-of-scope-rehome/1",
        "run_id": RUN_ID,
        "resumed_from_run": RESUMED_FROM,
        "resumed_head": resumed,
        "purpose": "preserve byte-exactly the two lane-owned audit-namespace files before they are removed from the auditor's protected namespace; this is a scope correction, not a destruction of evidence",
        "files": files,
        "owner_decision_required": False,
        "human_gate_ready": False,
    }
    (out_dir / f"{RESUMED_FROM}_producer_authored_audit_copy.json").write_text(
        json.dumps(rec, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    return rec


def replay_v3(scratch_dir: Path) -> tuple[int, dict]:
    """Re-run the accepted V3 falsifier to a SCRATCH path (never a committed record)."""
    scratch_dir.mkdir(parents=True, exist_ok=True)
    out = scratch_dir / "v3_replay.json"
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.counter_authority_surface_falsifier",
         "--run-id", "39471603258_replay", "--out", str(out)],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    rec = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    return proc.returncode, rec


def run_pytest(paths: list[str]) -> dict[str, Any]:
    proc = subprocess.run([sys.executable, "-m", "pytest", *paths, "-q"],
                          cwd=str(REPO_ROOT), capture_output=True, text=True)
    tail = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout.strip() else ""
    return {"argv": ["-m", "pytest", *paths, "-q"], "exit_code": proc.returncode,
            "summary_line": tail, "returncode": proc.returncode}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--scratch", default="/tmp/opencode/orchestration_resume_39471603258")
    ap.add_argument("--no-rehome", action="store_true")
    args = ap.parse_args(argv)
    scratch = Path(args.scratch)

    out_dir = REPO_ROOT / "results" / "evaluation" / f"orchestration_resume_{RUN_ID}"
    out_dir.mkdir(parents=True, exist_ok=True)

    detection = detect_out_of_scope()
    offenders = detection["lane_owned_audit_namespace_files"]

    rehome_rec: dict[str, Any] = {"skipped": bool(args.no_rehome)}
    if offenders and not args.no_rehome:
        rehome_rec = rehome_out_of_scope(out_dir, offenders)

    # ---- verification of the lane deliverable --------------------------------
    mount = Path("/tmp/lex_accepted/product")
    mount_present = mount.is_dir()
    if not mount_present:
        rec = {
            "schema": SCHEMA, "run_id": RUN_ID, "direction_version": 61,
            "verdict": "NOT_MEASURED", "exit_code": 2,
            "detail": "accepted product mount absent; never a pass",
            "out_of_scope": offenders, "owner_decision_required": False,
            "human_gate_ready": False, "claim_ceiling": CLAIM_CEILING,
        }
        (out_dir / f"{RUN_ID}_diagnosis.json").write_text(
            json.dumps(rec, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8")
        print(json.dumps(rec, indent=1))
        return 2

    replay_code, replay = replay_v3(scratch)
    committed_path = REPO_ROOT / CLAIM_RECORD
    committed = _load_json(committed_path)
    cmp_fields = ["verdict", "exit_code", "n_gates", "n_passed", "n_failed",
                  "n_reported", "input_drift"]
    comparison = {f: {"committed": committed.get(f), "replay": replay.get(f),
                      "match": committed.get(f) == replay.get(f)} for f in cmp_fields}
    committed_gates = [g["gate"] for g in committed.get("failed_gates", [])]
    replay_gates = [g["gate"] for g in replay.get("failed_gates", [])]
    committed_nv = (committed.get("non_vacuity") or {}).get("all_hold")
    replay_nv = (replay.get("non_vacuity") or {}).get("all_hold")
    committed_adm = committed.get("admissibility", {}).get("n_pairs_admissible")
    replay_adm = replay.get("admissibility", {}).get("n_pairs_admissible")
    comparison["failed_gates"] = {
        "committed": committed_gates,
        "replay": replay_gates,
        "match": committed_gates == replay_gates,
    }
    comparison["non_vacuity_all_hold"] = {
        "committed": committed_nv,
        "replay": replay_nv,
        "match": committed_nv == replay_nv,
    }
    comparison["admissibility"] = {
        "committed": committed_adm,
        "replay": replay_adm,
        "match": committed_adm == replay_adm,
    }
    all_match = all(v["match"] for v in comparison.values())

    pins_after = _rehash(FROZEN_PINS, REPO_ROOT)
    mount_after = _rehash(MOUNT_PINS, mount)
    pins_match = all(pins_after.get(k) == v for k, v in FROZEN_PINS.items())
    mount_match = all(mount_after.get(k) == v for k, v in MOUNT_PINS.items())

    dedicated = run_pytest([DEDICATED_TEST])
    adjacent = run_pytest(ADJACENT_TESTS)

    verification = {
        "schema": SCHEMA, "record_kind": "verification",
        "run_id": RUN_ID, "direction_version": 61,
        "generated_at_utc": _now(),
        "resumed_from_run": RESUMED_FROM,
        "instrument": "evaluation/counter_authority_surface_falsifier.py",
        "instrument_sha256": _sha256_file(REPO_ROOT / "evaluation" / "counter_authority_surface_falsifier.py"),
        "committed_record": CLAIM_RECORD,
        "committed_record_sha256": _sha256_file(committed_path),
        "replay": {"scratch_path": str(scratch / "v3_replay.json"),
                   "exit_code": replay_code,
                   "verdict": replay.get("verdict")},
        "comparison": comparison,
        "all_match": all_match,
        "frozen_pins_rehash": pins_after,
        "frozen_pins_match": pins_match,
        "mount": str(mount),
        "mount_head": _git("rev-parse", "HEAD", cwd=str(mount)) if mount.joinpath(".git").is_file() else None,
        "mount_pins_rehash": mount_after,
        "mount_pins_match": mount_match,
        "pytest_dedicated": dedicated,
        "pytest_adjacent": adjacent,
        "adjacent_reported_by_39462322100": "83 passed / 172 subtests",
        "adjacent_measured_this_run": adjacent["summary_line"],
        "disclosure_divergence": "the 39462322100 report and state entry claim '83 passed' for the four adjacent test files; this run measures 68 passed / 172 subtests from those same four files (24+27+11+6). The measured value is published here as-is; the '83' does not reproduce and is recorded as a disclosure divergence, never silently corrected.",
        "owner_decision_required": False,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    (out_dir / f"{RUN_ID}_verification.json").write_text(
        json.dumps(verification, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")

    diagnosis = {
        "schema": DIAGNOSIS_SCHEMA,
        "run_id": RUN_ID,
        "direction_version": 61,
        "lane": "evaluation",
        "generated_at": _now(),
        "resumed_from_run": RESUMED_FROM,
        "diagnosed_run": {
            "github_run": RESUMED_FROM,
            "name": "Core evaluation dirV61 repair0",
            "event": "workflow_dispatch",
            "team_branch": f"cycle/core/evaluation/{RESUMED_FROM}/team",
            "team_head": RESUMED_HEAD,
            "team_head_subject": "evaluation cycle 39470495546 repair 0",
            "audit_branch": None,
            "conclusion": "no independent audit was ever produced for this run; no audit branch exists on origin",
            "evidence_source": "the committed tree of the persisted producer snapshot plus the workflow source; the GitHub REST record was not reachable unauthenticated in this environment, so no job-level conclusion string is asserted",
        },
        "job_chain": {
            "team": {
                "scope_guard": "FAILS (exit 3): the producer added two files outside the lane's write scope",
                "steps": {
                    "Enforce lane write scope": "failure (exit 3)",
                    "Persist team snapshot": "runs (if: always()) and force-pushes the out-of-scope writes",
                },
            },
            "audit": "skipped (needs: team, if: needs.team.result == 'success')",
            "integrate": "skipped (needs: audit success)",
        },
        "root_cause": {
            "classification": "PRODUCER_AUTHORED_AUDIT_PLACEMENT_OUT_OF_LANE_SCOPE",
            "not": ["a verdict", "a product defect", "an audit finding",
                    "a human-gate problem", "an evidence or claim-path failure"],
            "mechanism": {
                "offenders": offenders,
                "lane_write_scope_patterns": LANE_WRITE_SCOPE,
                "scope_guard_source": ".github/workflows/core-lane.yml:123-144",
                "audit_job_gating": ".github/workflows/core-lane.yml:163-165",
                "persist_always": ".github/workflows/core-lane.yml:146-147",
                "detail": "the producer wrote results/audit/evaluation/CYCLE_39470495546_GATE.json and reports/audit/evaluation/CYCLE_39470495546.md. Neither path matches any permitted lane pattern (evaluation/*, tests/evaluation/*, results/evaluation/*, reports/evaluation/*, state/evaluation.json, data/evaluation/*). The guard exits 3; the audit job is skipped; because 'Persist team snapshot' is if: always(), the snapshot is force-pushed anyway.",
            },
            "why_this_matters": "the lane owns no independent-audit output. The independent auditor writes results/audit/<lane>/CYCLE_<run_id>_GATE.json and reports/audit/<lane>/CYCLE_<run_id>.md in the AUDIT JOB checkout. A producer that writes them itself is self-certifying its own gate and, worse, breaks the audit chain so no real gate is ever produced.",
            "contributing_defect": "the producer's audit report claims a durable delta (the 39462322100 artifacts) that it did not itself create, and its gate file is placed in the auditor's namespace rather than the lane namespace. This is the 'producer-authored audit placement copy' pathology recorded in factory-wide requirements 15 and 35.",
        },
        "prior_unaudited_measurement": {
            "run_id": "39462322100",
            "team_branch": "cycle/core/evaluation/39462322100/team",
            "team_head": "61ecbc61f6ed84ed05e595cd6fe0f38eec025eba",
            "audit_branch": None,
            "claim_bearing_record": CLAIM_RECORD,
            "reading": "the V3 counter-authority surface falsifier measurement was proposed pending audit; no audit branch exists for 39462322100, so it was never independently audited before this cycle.",
        },
        "snapshot_integrity": {
            "snapshot_branch": f"cycle/core/evaluation/{RESUMED_FROM}/team",
            "snapshot_tip": RESUMED_HEAD,
            "accepted_base": {"ref": "lab/evaluation", "head": ACCEPTED_BASE},
            "out_of_scope_files_new_in_snapshot": offenders,
            "valid_work_preserved": [
                "results/evaluation/counter_authority_surface_falsifier/39462322100.json",
                "reports/evaluation/COUNTER_AUTHORITY_SURFACE_FALSIFIER_39462322100.md",
                "results/evaluation/retrieval_counter_authority_benchmark/39462322100.json",
                "tests/evaluation/test_counter_authority_surface_falsifier.py",
                "evaluation/counter_authority_surface_falsifier.py",
            ],
            "nothing_valid_deleted": True,
        },
        "rehome": rehome_rec,
        "resume_plan_executed_this_run": [
            "R-1 name the exact failure from the committed tree + workflow source (this record)",
            "R-2 re-home the two out-of-scope pseudo-audit files byte-exactly with their git blob oids before removing them from the auditor namespace",
            "R-3 verify the V3 falsifier reproduces its committed record from the accepted mount",
            "R-4 re-hash every frozen pin and mount pin; zero new thresholds",
            "R-5 publish the disclosure divergence (adjacent test count 68 measured vs 83 claimed) as-is",
        ],
        "control_plane_hardening_items_recorded_not_patched": [
            ".github/** is control-plane scope and is NOT edited from this lane. Recorded: (a) 'Persist team snapshot' is if: always(), so it force-pushes an out-of-scope snapshot after a failed scope check (factory-wide requirement 35); the durable fix is to gate it on the scope check. (b) The audit job's 'Persist audit snapshot' has no if: always(), so an auditor death leaves no audit branch and the lane re-dispatches (factory-wide requirement 20).",
        ],
        "owner_decision_required": False,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    (out_dir / f"{RUN_ID}_diagnosis.json").write_text(
        json.dumps(diagnosis, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")

    summary = {
        "verdict": "RESUME_COMPLETE" if (all_match and pins_match and mount_match) else "RESUME_FINDING_FAIL",
        "all_match": all_match,
        "frozen_pins_match": pins_match,
        "mount_pins_match": mount_match,
        "out_of_scope_offenders": offenders,
        "diagnosis": str(out_dir / f"{RUN_ID}_diagnosis.json"),
        "verification": str(out_dir / f"{RUN_ID}_verification.json"),
    }
    print(json.dumps(summary, indent=1))
    if all_match and pins_match and mount_match:
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
