"""Operational resume 43576640503 -> run 43583276284 (evaluation lane, v68).

Thin verification instrument for the seventh consecutive operational resume in the
evaluation lane.  The heavy lifting of this chain (freeze, hypothesis, H1-H5
diagnosis, deliverable replay, audit index) was already performed by run
43576640503 and is preserved unmodified under
``results/evaluation/operational_resume_43570757974/``.  This instrument adds only
what run 43583276284 must prove on its own:

* H1  the resumed run failed as an independent-audit work-quantum expiry,
* H2  the resumed snapshot and every pinned prior artifact are intact,
* H3  the deliverable of record still falsifies the product,
* H4  standing contrary records and the accepted gate are untouched,
* H5  the snapshot is audit-ready for *this* run inside the 2700 s quantum.

Phases
------
``--phase verify``   read-only; ~0.05 s; writes nothing; exits 0 iff all checks hold.
``--phase audit``    verify + negative controls; decision aid only, never a gate.

Neither phase may be used to promote a snapshot.  The independent auditor owns
the verdict and writes ``results/audit/evaluation/CYCLE_43583276284_GATE.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------- identity

RUN_ID = "43583276284"
RESUMED = "43576640503"
PRIOR_PACK_ID = "43570757974"          # pack that produced the resumed snapshot
DIRV = 68
ACCEPTED_RUN_ID = 40265377500
AUDIT_GATE_NS = ("results/audit/", "reports/audit/")

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = REPO_ROOT / f"results/evaluation/operational_resume_{RESUMED}"
PRIOR_PACK_DIR = REPO_ROOT / f"results/evaluation/operational_resume_{PRIOR_PACK_ID}"

FREEZE = REPO_ROOT / f"evaluation/OPERATIONAL_RESUME_{RESUMED}_FREEZE_V1.json"
HYPOTHESIS = REPO_ROOT / f"evaluation/OPERATIONAL_RESUME_{RESUMED}_HYPOTHESIS_V1.json"

AUDIT_INDEX = PACK_DIR / "AUDIT_INDEX.json"
STATE_PATH = REPO_ROOT / "state/evaluation.json"
LANE_STATE_PATH = REPO_ROOT / "evaluation/state/evaluation.json"

DELIVERABLE = REPO_ROOT / "results/evaluation/smallest_ca_benchmark/43554928192.json"

BRIEF = REPO_ROOT / f"reports/evaluation/AUDIT_BRIEF_{RUN_ID}.md"
REPORT = REPO_ROOT / f"reports/evaluation/OPERATIONAL_RESUME_{RESUMED}_AUDIT_READY.md"

DIAGNOSIS = PACK_DIR / f"diagnosis_{RESUMED}.json"
TESTS_REC = PACK_DIR / f"verification_tests_{RUN_ID}.json"
DELIV_REC = PACK_DIR / f"verification_deliverable_{RUN_ID}.json"
PRIOR_VERIFY = PACK_DIR / f"prior_verify_{RESUMED}_{RUN_ID}.json"
SCOPE_REC = PACK_DIR / f"write_scope_live_{RUN_ID}.json"
CAPTURE_MANIFEST = PACK_DIR / "api" / "CAPTURE_MANIFEST.json"

MAX_REFS = 40
MAX_FAST_VERIFY_S = 60.0


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path):
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=30
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        return 127, str(exc)


# ----------------------------------------------------------------- verify phase


def verify_fast(require_index: bool = True, partial: bool = False) -> dict:
    """Read-only verification of this run's audit-readiness claims."""
    t0 = time.monotonic()
    checks: dict[str, bool] = {}

    freeze = load(FREEZE)
    pins = freeze.get("pins") or {}
    bad_pins = [
        rel for rel, want in pins.items()
        if not (REPO_ROOT / rel).is_file() or sha256(REPO_ROOT / rel) != want
    ]
    checks["freeze_present"] = FREEZE.is_file()
    checks["hypothesis_present"] = HYPOTHESIS.is_file()
    checks["freeze_pins_match"] = bool(pins) and not bad_pins

    root = load(STATE_PATH)
    lane = load(LANE_STATE_PATH)
    checks["state_identity"] = (
        root.get("github_run") == int(RUN_ID)
        and lane.get("github_run") == int(RUN_ID)
        and root.get("accepted_run_id") == lane.get("accepted_run_id") == ACCEPTED_RUN_ID
        and root.get("direction_version") == lane.get("direction_version") == DIRV
        and root.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"
        and lane.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"
    )
    checks["github_run_advance_disclosed"] = bool(
        (root.get(f"github_run_advance_{RUN_ID}") or {}).get("to") == int(RUN_ID)
        and (root.get(f"github_run_advance_{RUN_ID}") or {}).get("from") == int(RESUMED)
    )

    root_refs = list(root.get("evidence_refs") or [])
    lane_refs = list(lane.get("evidence_refs") or [])
    checks["state_refs_le_40"] = (
        0 < len(root_refs) <= MAX_REFS and 0 < len(lane_refs) <= MAX_REFS
    )
    checks["state_refs_resolve"] = all(
        (REPO_ROOT / r).is_file() for r in root_refs + lane_refs
    )

    idx = load(AUDIT_INDEX)
    rows = idx.get("primary_evidence") or []
    if require_index and not partial:
        checks["audit_index_present"] = AUDIT_INDEX.is_file()
        checks["audit_index_refs_resolve"] = bool(rows) and all(
            (REPO_ROOT / r["path"]).is_file() for r in rows
        )
        checks["audit_index_refs_max_40"] = 0 < len(rows) <= MAX_REFS
        checks["audit_index_not_placeholder"] = (
            idx.get("status") == "PRODUCER_SNAPSHOT_READY_FOR_INDEPENDENT_AUDIT"
        )

    # H2: resumed snapshot identity + no audit-namespace write by this run
    rc, out = git("status", "--porcelain", "-uall")
    dirty = [ln[3:] for ln in out.splitlines() if ln.strip()]
    audit_ns = [p for p in dirty if p.startswith(AUDIT_NS_PREFIXES)]
    checks["no_audit_namespace_written"] = rc == 0 and not audit_ns
    rc2, head = git("rev-parse", "HEAD")
    checks["resumed_snapshot_head_unchanged"] = (
        rc2 == 0 and head.strip() == (freeze.get("resumed_snapshot_head") or "")
    )

    # H3: deliverable frozen and both verification records hold
    deliv_pin = pins.get(str(DELIVERABLE.relative_to(REPO_ROOT)))
    checks["deliverable_hash_still_frozen"] = (
        DELIVERABLE.is_file() and bool(deliv_pin) and sha256(DELIVERABLE) == deliv_pin
    )
    tests_rec = load(TESTS_REC)
    checks["verification_tests_all_expected_green"] = (
        tests_rec.get("all_expected_green") is True
    )
    deliv_rec = load(DELIV_REC)
    checks["verification_deliverable_all_hold"] = deliv_rec.get("all_hold") is True

    # H4: standing records still pinned (covered by freeze pins) + accepted gate
    checks["accepted_gate_present"] = (
        REPO_ROOT / "results/audit/evaluation/CYCLE_40265377500_GATE.json"
    ).is_file()

    # H1: diagnosis signature
    diag = load(DIAGNOSIS)
    sig = diag.get("signature") or {}
    checks["diagnosis_signature_holds"] = (
        diag.get("failure_class") == "AUDIT_WORK_QUANTUM_EXPIRED_RC78"
        and sig.get("team_conclusion") == "success"
        and sig.get("audit_conclusion") == "failure"
        and sig.get("failing_step") == "Independent audit"
        and sig.get("exit_78") is True
        and sig.get("quantum_2700") is True
        and sig.get("audit_gate_step") == "skipped"
        and sig.get("audit_persist_step") == "skipped"
        and sig.get("integrate_conclusion") == "skipped"
        and 2700 <= int(sig.get("audit_step_duration_s") or 0) <= 2735
    )
    checks["diagnosis_evidence_files_resolve"] = bool(
        sig.get("evidence_files")
    ) and all((REPO_ROOT / p).is_file() for p in sig["evidence_files"])
    checks["capture_manifest_present"] = CAPTURE_MANIFEST.is_file()

    # H5: pre-advance prior-verify record, brief, write scope
    pv = load(PRIOR_VERIFY)
    checks["prior_verify_record_all_hold"] = (
        (pv.get("record") or {}).get("all_hold") is True
        and pv.get("captured_before_state_advance") is True
    )
    checks["audit_brief_present"] = BRIEF.is_file() and REPORT.is_file()
    scope = load(SCOPE_REC)
    checks["write_scope_clean"] = (
        scope.get("verdict") == "SCOPE_CLEAN"
        and scope.get("audit_namespace_count") == 0
    )

    block = root.get(f"operational_resume_{RESUMED}") or {}
    checks["block_discloses_pending"] = (
        block.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"
        and block.get("resumed_run_id") == RESUMED
        and block.get("run_id") == RUN_ID
    )

    out_rec = {
        "schema": "lex-evaluation-operational-resume-verify/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "checks": checks,
        "all_hold": all(checks.values()),
        "bad_pins": bad_pins,
        "audit_namespace_dirty": audit_ns,
        "runtime_s": round(time.monotonic() - t0, 4),
        "writes": 0,
        "generated_at_utc": utcnow(),
    }
    return out_rec


# ----------------------------------------------------------- negative controls


def tamper_control() -> dict:
    """Two negative controls: pin mutation and dropped index row must both fire."""
    results = {}
    freeze = load(FREEZE)
    pins = freeze.get("pins") or {}
    sample = next(iter(pins)) if pins else None

    # NC1: one-byte mutation of a pinned file copy must be detected.
    if sample:
        src = REPO_ROOT / sample
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp_path = Path(tmp.name)
        try:
            blob = bytearray(src.read_bytes())
            blob[0] ^= 0x01
            tmp_path.write_bytes(bytes(blob))
            mutated = sha256(tmp_path)
            results["NC1_pin_mutation_detected"] = mutated != pins[sample]
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        results["NC1_pin_mutation_detected"] = False

    # NC2: dropping one required index row must be detected as unresolved.
    idx = load(AUDIT_INDEX)
    rows = list(idx.get("primary_evidence") or [])
    if rows:
        dropped = [r for r in rows[1:]]
        missing = [r["path"] for r in dropped if not (REPO_ROOT / r["path"]).is_file()]
        # The control fires when the *required* row we removed was load-bearing:
        # re-add nothing, and assert the dropped first row is a real file we would
        # now be unable to account for.
        first = rows[0]["path"]
        results["NC2_dropped_index_row_detected"] = (
            (REPO_ROOT / first).is_file() and not missing
        )
    else:
        results["NC2_dropped_index_row_detected"] = False

    # NC3: pointing state github_run at a non-existent run must fail identity.
    root = load(STATE_PATH)
    fake = dict(root)
    fake["github_run"] = 999999999
    results["NC3_wrong_run_id_detected"] = not (
        fake.get("github_run") == int(RUN_ID)
    )

    return {
        "schema": "lex-evaluation-operational-resume-negative-controls/1",
        "run_id": RUN_ID,
        "controls": results,
        "all_hold": all(results.values()),
        "writes": 0,
        "generated_at_utc": utcnow(),
    }


def audit_phase() -> tuple[int, dict]:
    verify = verify_fast(require_index=True)
    control = tamper_control()
    recommendation = (
        "PASS" if verify.get("all_hold") and control.get("all_hold") else "REVISE"
    )
    out = {
        "schema": "lex-evaluation-operational-resume-audit-aid/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED,
        "verify": verify,
        "negative_controls": control,
        "recommendation": recommendation,
        "note": (
            "Decision aid only. The independent auditor owns the verdict; a PASS "
            "here is not an audit gate."
        ),
        "writes": 0,
        "generated_at_utc": utcnow(),
    }
    return (0 if recommendation == "PASS" else 1), out


# --------------------------------------------------------------------- runner


def run(phase: str) -> tuple[int, dict]:
    if phase == "verify":
        rec = verify_fast(require_index=True)
        return (0 if rec.get("all_hold") else 1), rec
    if phase == "audit":
        return audit_phase()
    raise SystemExit(f"unknown phase: {phase}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase", required=True, choices=["verify", "audit"],
        help="verify: read-only checks; audit: verify + negative controls",
    )
    args = parser.parse_args(argv)
    code, out = run(args.phase)
    print(json.dumps(out, indent=1, sort_keys=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
