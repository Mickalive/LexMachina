#!/usr/bin/env python3
"""Operational-resume verification for evaluation run 39820650174.

Why this exists
---------------
Evaluation run 39813664201 (direction v62) committed two complete, freeze-first
measurements and then died on the 45-minute agent work quantum (rc-78):

* ``results/evaluation/shipped_planner_remedy_verification/39813664201.json``
  (ordered item 1: the landed remedy-(a) planner, verified on the recorded
  bundle population); and
* ``results/evaluation/coverage_remediation_crosscheck/39813664201.json``
  (ordered item 2: the product's 24-text coverage remediation, replayed
  offline through the shipped code).

Run 39820233238 was dispatched as an operational resume of that snapshot and
failed with ``LEX_ZERO_DELTA_REPAIR`` (exit 67): its snapshot branch is
byte-identical to the producer branch, so it added no measurement and no state
repair.  This run resumes again.  It must verify the producer's completed work
rather than restart it, and repair the state the producer left stale.

What this instrument verifies (frozen in the hypothesis/freeze pair)
--------------------------------------------------------------------
R1 snapshot identity and lane scope
R2 both producer freeze-record pin maps still hold on disk
R3 both producer results are internally consistent with their own artifacts
R4 the coverage reach unions recompute with no reach loss
R5 the shipped planner the producer verified is still the shipped planner at
   the current accepted product mount
R6 this run's two evaluation state files are reconciled, resolvable and
   fail-closed

Exit codes (frozen contract)
----------------------------
0  RESUME_VERIFIED_AND_AUDIT_READY
1  RESUME_DIVERGENCE
2  ENVIRONMENT_OR_VACUOUS  (never a product verdict)

This is a verification of already-committed evidence, not a new measurement of
retrieval or counter-authority quality.  It touches no frozen bar, rubric,
benchmark or verdict contract, and it runs no universal-174k benchmark.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "lex-evaluation-operational-resume-verification/1"
FREEZE_PATH = REPO_ROOT / "evaluation" / "OPERATIONAL_RESUME_39820650174_FREEZE.json"
HYPOTHESIS_PATH = REPO_ROOT / "evaluation" / "OPERATIONAL_RESUME_39820650174_HYPOTHESIS_V1.json"

RUN_ID = "39820650174"
RESUMED_SNAPSHOT_RUN_ID = "39820233238"
PRODUCER_RUN_ID = "39813664201"
SNAPSHOT_COMMIT = "c87a33bcfc5cfd81fdbfb1c2b2f540e8a1c65ad3"
ACCEPTED_BASE_COMMIT = "57ad380ec5d6c7422c4817b018e5c18a4e029158"
PRODUCER_PRODUCT_HEAD = "443302120a5b7221d8bb5c605848b29eb68bca19"
EXPECTED_PLANNER_SHA = "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9"
FROZEN_SPEC = "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"
FROZEN_SPEC_SHA = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"

DIRECTION_VERSION = 62
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")

SPRV_RESULT = "results/evaluation/shipped_planner_remedy_verification/39813664201.json"
CRC_RESULT = "results/evaluation/coverage_remediation_crosscheck/39813664201.json"
CRC_FRESH = "results/evaluation/coverage_remediation_crosscheck/39813664201_fresh_offline_replay.json"
PRODUCT_LIVE = "results/product/coverage_replay/LOCAL_LIVE_COVERAGE2_live.json"
PRODUCT_OFFLINE = "results/product/coverage_replay/LOCAL_OFFLINE_VERIFY_offline.json"

ROOT_STATE = "state/evaluation.json"
LANE_STATE = "evaluation/state/evaluation.json"

SCOPE_PREFIXES = (
    "evaluation/",
    "tests/evaluation/",
    "results/evaluation/",
    "reports/evaluation/",
)

ALLOWED_SNAPSHOT_EXTRA = (
    "state/evaluation.json",
)

EXIT_OK = 0
EXIT_DIVERGE = 1
EXIT_ENV = 2


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60
        )
        return proc.returncode, (proc.stdout or "").strip()
    except Exception as exc:  # pragma: no cover - defensive
        return 1, repr(exc)


def _rehash(pins: dict[str, str], root: Path) -> dict:
    """Re-hash a path -> digest map.  Pure; the control tampers with its input."""
    checks = []
    ok = True
    for rel, expected in sorted(pins.items()):
        path = root / rel
        if not path.is_file():
            checks.append({"path": rel, "status": "ABSENT", "expected": expected})
            ok = False
            continue
        actual = sha256_file(path)
        good = actual == expected
        ok = ok and good
        checks.append({
            "path": rel,
            "status": "ok" if good else "DRIFT",
            "expected": expected,
            "actual": actual,
        })
    return {"all_hold": ok, "n_checks": len(checks), "checks": checks}


def recompute_union(record: dict) -> list[str]:
    out: set[str] = set()
    for row in record.get("per_text") or []:
        for did in row.get("all_frozen_ids_reached") or []:
            out.add(str(did))
    return sorted(out)


def union_matches_count(record: dict) -> dict:
    union = recompute_union(record)
    recorded = record.get("n_frozen_ids_reached")
    return {
        "recomputed_n": len(union),
        "recorded_n": recorded,
        "match": len(union) == int(recorded if recorded is not None else -1),
        "union": union,
    }


def planner_matches(recorded: str, actual: str) -> bool:
    return str(recorded or "") == str(actual or "")


def _no_network_guard():
    """Context manager that makes any socket creation fail and counts attempts."""

    class _Guard:
        attempts = 0

        def __enter__(self):
            self._orig = socket.socket
            guard = self

            def _blocked(*_a, **_kw):
                guard.attempts += 1
                raise RuntimeError("NO_NETWORK_VERIFICATION_INSTRUMENT")

            socket.socket = _blocked  # type: ignore[assignment]
            return self

        def __exit__(self, *_exc):
            socket.socket = self._orig  # type: ignore[assignment]
            return False

    return _Guard()


def _newest_audited_gate() -> str | None:
    gate_dir = REPO_ROOT / "results" / "audit" / "evaluation"
    ids = []
    if gate_dir.is_dir():
        for p in gate_dir.glob("CYCLE_*_GATE.json"):
            mid = p.name[len("CYCLE_"):-len("_GATE.json")]
            if mid.isdigit():
                ids.append(mid)
    return str(max(ids, key=int)) if ids else None


# --------------------------------------------------------------------------- #
# gates
# --------------------------------------------------------------------------- #


def gate_r1_snapshot_identity_and_scope() -> dict:
    code, resolved = _git("rev-parse", "--verify", f"{SNAPSHOT_COMMIT}^{{commit}}")
    exists = code == 0 and resolved == SNAPSHOT_COMMIT
    base_exists = _git("rev-parse", "--verify", f"{ACCEPTED_BASE_COMMIT}^{{commit}}")[0] == 0
    is_ancestor = (
        _git("merge-base", "--is-ancestor", ACCEPTED_BASE_COMMIT, SNAPSHOT_COMMIT)[0] == 0
        if base_exists else False
    )
    _c, names = _git("diff", "--name-only", f"{ACCEPTED_BASE_COMMIT}..{SNAPSHOT_COMMIT}")
    paths = [p for p in names.splitlines() if p.strip()]
    out_of_scope = [
        p for p in paths
        if not p.startswith(SCOPE_PREFIXES) and p not in ALLOWED_SNAPSHOT_EXTRA
    ]
    # Optional identity check against the producer branch tip, when the ref is
    # present in this clone (it may be absent in a read-only audit checkout).
    code_ref, ref_sha = _git("rev-parse", "--verify",
                             f"origin/cycle/core/evaluation/{PRODUCER_RUN_ID}/team")
    ref_identity = None
    if code_ref == 0 and ref_sha:
        ref_identity = ref_sha == SNAPSHOT_COMMIT
    passed = bool(exists and is_ancestor and not out_of_scope)
    return {
        "gate": "R1_snapshot_identity_and_scope",
        "passed": passed,
        "snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_commit_exists": exists,
        "accepted_base": ACCEPTED_BASE_COMMIT,
        "accepted_base_exists": base_exists,
        "snapshot_descends_from_accepted_base": is_ancestor,
        "n_paths_in_producer_delta": len(paths),
        "out_of_scope_paths": out_of_scope,
        "producer_branch_ref_resolvable": ref_identity is not None,
        "producer_branch_equals_snapshot": ref_identity,
    }


def gate_r2_freeze_pins_hold(freeze: dict) -> dict:
    pins = dict(freeze.get("pins") or {})
    return {
        "gate": "R2_freeze_pins_hold",
        "passed": False,  # set by run()
        "pins": _rehash(pins, REPO_ROOT),
    }


def gate_r3_recorded_results_internally_consistent() -> dict:
    checks: list[dict] = []
    passed = True

    def _check(name: str, ok: bool, observed=None, expected=None) -> None:
        nonlocal passed
        passed = passed and bool(ok)
        checks.append({"check": name, "ok": bool(ok),
                       "observed": observed, "expected": expected})

    for rel, expected_verdict in (
        (SPRV_RESULT, "SHIPPED_PLANNER_MATCHES_VERIFIED_REMEDY"),
        (CRC_RESULT, "COVERAGE_EVIDENCE_REPRODUCES"),
    ):
        p = REPO_ROOT / rel
        if not p.is_file():
            _check(f"{rel}:present", False, "absent", "file")
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        _check(f"{rel}:verdict", rec.get("verdict") == expected_verdict,
               rec.get("verdict"), expected_verdict)
        _check(f"{rel}:exit_code", rec.get("exit_code") == 0,
               rec.get("exit_code"), 0)
        gates = rec.get("gates") or {}
        gate_vals = list(gates.values()) if isinstance(gates, dict) else list(gates)
        all_gates = bool(gate_vals) and all(
            (g.get("passed") if isinstance(g, dict) else bool(g)) for g in gate_vals
        )
        _check(f"{rel}:all_gates_passed", all_gates,
               [g.get("passed") if isinstance(g, dict) else g for g in gate_vals], "all true")
        controls = rec.get("controls") or {}
        ctrl_vals = list(controls.values()) if isinstance(controls, dict) else list(controls)
        all_ctrl = bool(ctrl_vals) and all(
            (c.get("holds") if isinstance(c, dict) else bool(c)) for c in ctrl_vals
        )
        _check(f"{rel}:all_controls_hold", all_ctrl,
               [c.get("holds") if isinstance(c, dict) else c for c in ctrl_vals], "all true")
        # Recorded digests must name the files they claim.
        for key, digest_key in (
            ("freeze_record_path", "freeze_record_sha256"),
            ("frozen_hypothesis_path", "frozen_hypothesis_sha256"),
        ):
            claimed = rec.get(key)
            digest = rec.get(digest_key)
            if claimed:
                fp = REPO_ROOT / claimed
                actual = sha256_file(fp) if fp.is_file() else None
                _check(f"{rel}:{digest_key}", actual is not None and actual == digest,
                       {"path": claimed, "actual": actual}, digest)
        if rec.get("pins_before") is not None:
            _check(f"{rel}:pins_before", bool(rec["pins_before"].get("all_ok")),
                   rec["pins_before"].get("all_ok"), True)
        if rec.get("pins_after") is not None:
            _check(f"{rel}:pins_after", bool(rec["pins_after"].get("all_ok")),
                   rec["pins_after"].get("all_ok"), True)
    # The coverage record must name the committed fresh-replay artifact and its digest.
    crc = REPO_ROOT / CRC_RESULT
    fresh = REPO_ROOT / CRC_FRESH
    if crc.is_file() and fresh.is_file():
        rec = json.loads(crc.read_text(encoding="utf-8"))
        meta = rec.get("fresh_replay_meta") or {}
        _check("coverage:fresh_artifact_digest",
               meta.get("artifact_sha256") == sha256_file(fresh),
               {"recorded": meta.get("artifact_sha256"), "actual": sha256_file(fresh)},
               meta.get("artifact_sha256"))
        _check("coverage:fresh_network_calls_zero",
               int((rec.get("fresh_offline") or {}).get("n_network_calls") or 0) == 0,
               (rec.get("fresh_offline") or {}).get("n_network_calls"), 0)
    else:
        _check("coverage:fresh_artifact_present", False, "absent", "file")
    return {
        "gate": "R3_recorded_results_internally_consistent",
        "passed": passed,
        "checks": checks,
    }


def gate_r4_coverage_unions_recompute(mount: Path) -> dict:
    checks: list[dict] = []
    passed = True

    def _check(name: str, ok: bool, observed=None, expected=None) -> None:
        nonlocal passed
        passed = passed and bool(ok)
        checks.append({"check": name, "ok": bool(ok),
                       "observed": observed, "expected": expected})

    fresh_path = REPO_ROOT / CRC_FRESH
    result_path = REPO_ROOT / CRC_RESULT
    if not fresh_path.is_file() or not result_path.is_file():
        return {"gate": "R4_coverage_unions_recompute_without_reach_loss",
                "passed": False, "checks": [{"check": "inputs_present", "ok": False}]}

    fresh = json.loads(fresh_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    fresh_check = union_matches_count(fresh)
    _check("fresh_union_recomputes", fresh_check["match"],
           fresh_check["recomputed_n"], fresh_check["recorded_n"])

    for name, rel in (("committed_live", PRODUCT_LIVE), ("committed_offline", PRODUCT_OFFLINE)):
        p = mount / rel
        if not p.is_file():
            _check(f"{name}:present", False, "absent", rel)
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        chk = union_matches_count(rec)
        _check(f"{name}:union_recomputes", chk["match"],
               chk["recomputed_n"], chk["recorded_n"])
        if name == "committed_offline":
            missing = sorted(set(chk["union"]) - set(fresh_check["union"]))
            _check("fresh_superset_of_committed_offline", not missing, missing, [])
    # The producer's recorded counts must agree with the re-derived ones.
    rec_fresh = result.get("fresh_offline") or {}
    _check("result_fresh_count_agrees", rec_fresh.get("n_frozen_ids_reached") == fresh_check["recomputed_n"],
           rec_fresh.get("n_frozen_ids_reached"), fresh_check["recomputed_n"])
    return {
        "gate": "R4_coverage_unions_recompute_without_reach_loss",
        "passed": passed,
        "checks": checks,
    }


def gate_r5_shipped_planner_unchanged(mount: Path) -> dict:
    result_path = REPO_ROOT / SPRV_RESULT
    if not result_path.is_file():
        return {"gate": "R5_shipped_planner_unchanged_at_current_mount",
                "passed": False, "reason": "producer result absent"}
    result = json.loads(result_path.read_text(encoding="utf-8"))
    recorded = str(result.get("planner_sha256") or "")
    planner = mount / "product" / "query" / "adversarial_retrieval.py"
    actual = sha256_file(planner) if planner.is_file() else None
    same = planner_matches(recorded, actual or "")
    # The producer measured at product head 44330212; it must still be an
    # ancestor of the current mount head.  A mount without git metadata (e.g.
    # an exported tarball) yields reported-only ancestry rather than a failure.
    code, mount_head = _git("-C", str(mount), "rev-parse", "HEAD")
    ancestry = None
    if code == 0 and mount_head:
        ancestry = _git("-C", str(mount), "merge-base", "--is-ancestor",
                        PRODUCER_PRODUCT_HEAD, mount_head)[0] == 0
    passed = same and (ancestry is not False)
    return {
        "gate": "R5_shipped_planner_unchanged_at_current_mount",
        "passed": passed,
        "recorded_planner_sha256": recorded,
        "actual_planner_sha256": actual,
        "planner_matches": same,
        "producer_product_head": PRODUCER_PRODUCT_HEAD,
        "mount_head": mount_head or None,
        "producer_head_is_ancestor_of_mount_head": ancestry,
    }


def gate_r6_state_reconciled_and_resolvable() -> dict:
    checks: list[dict] = []
    passed = True

    def _check(name: str, ok: bool, observed=None, expected=None) -> None:
        nonlocal passed
        passed = passed and bool(ok)
        checks.append({"check": name, "ok": bool(ok),
                       "observed": observed, "expected": expected})

    root_p = REPO_ROOT / ROOT_STATE
    lane_p = REPO_ROOT / LANE_STATE
    if not root_p.is_file() or not lane_p.is_file():
        return {"gate": "R6_state_reconciled_and_resolvable", "passed": False,
                "checks": [{"check": "state_files_present", "ok": False}]}
    root = json.loads(root_p.read_text(encoding="utf-8"))
    lane = json.loads(lane_p.read_text(encoding="utf-8"))
    _check("state_files_identical", root == lane)
    _check("github_run_is_this_run", str(root.get("github_run")) == RUN_ID,
           root.get("github_run"), RUN_ID)
    _check("direction_version", root.get("direction_version") == DIRECTION_VERSION,
           root.get("direction_version"), DIRECTION_VERSION)
    newest = _newest_audited_gate()
    _check("accepted_run_is_newest_in_tree_gate",
           newest is not None and str(root.get("accepted_run_id")) == newest,
           root.get("accepted_run_id"), newest)
    refs = root.get("evidence_refs") or []
    _check("evidence_refs_n_matches", root.get("evidence_refs_n") == len(refs),
           root.get("evidence_refs_n"), len(refs))
    missing = [r for r in refs if not (REPO_ROOT / str(r).split(" ")[0].rstrip(",")).is_file()]
    _check("evidence_refs_resolve", not missing, missing, [])
    flags = ("human_gate_ready", "machine_gate_ready", "packet_admitted",
             "ready_for_owner_session")
    for f in flags:
        _check(f"flag_false:{f}", root.get(f) is False, root.get(f), False)
    # owner_decision_required may be absent in older state; if present it must be false.
    if "owner_decision_required" in root:
        _check("flag_false:owner_decision_required",
               root.get("owner_decision_required") is False,
               root.get("owner_decision_required"), False)
    return {
        "gate": "R6_state_reconciled_and_resolvable",
        "passed": passed,
        "checks": checks,
    }


# --------------------------------------------------------------------------- #
# controls
# --------------------------------------------------------------------------- #


def controls(freeze: dict, mount: Path) -> dict:
    out: dict[str, dict] = {}

    # C1: a planted pin drift must be detected.
    pins = dict(freeze.get("pins") or {})
    if pins:
        tampered = dict(pins)
        first = sorted(tampered)[0]
        tampered[first] = "0" * 64
        detected = _rehash(tampered, REPO_ROOT)["all_hold"] is False
    else:
        detected = False
    out["C1_planted_pin_drift_is_detected"] = {"holds": detected}

    # C2: a planted reach loss must be detected.
    fresh_p = REPO_ROOT / CRC_FRESH
    if fresh_p.is_file():
        rec = json.loads(fresh_p.read_text(encoding="utf-8"))
        before = union_matches_count(rec)["match"]
        mutated = json.loads(json.dumps(rec))
        removed = None
        for row in mutated.get("per_text") or []:
            ids = row.get("all_frozen_ids_reached") or []
            if ids:
                removed = ids.pop()
                break
        after = union_matches_count(mutated)["match"]
        detected = bool(before and not after and removed is not None)
    else:
        detected = False
    out["C2_planted_reach_loss_is_detected"] = {"holds": detected}

    # C3: a planted planner mismatch must be detected.
    out["C3_planted_planner_mismatch_is_detected"] = {
        "holds": not planner_matches(EXPECTED_PLANNER_SHA, "0" * 64)
    }

    # C4 is exercised by the run-id entry contract; record it as held only when
    # the frozen record carries this run id (the run() path enforces the rest).
    out["C4_wrong_run_id_is_exit_2"] = {
        "holds": str(freeze.get("run_id_of_record")) == RUN_ID
    }
    return out


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #


def run(run_id: str, mount: Path) -> tuple[int, dict]:
    if not FREEZE_PATH.is_file() or not HYPOTHESIS_PATH.is_file():
        return EXIT_ENV, {
            "schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_OR_VACUOUS",
            "exit_code": EXIT_ENV, "reason": "hypothesis or freeze record absent",
        }
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    hypothesis = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    if str(freeze.get("run_id_of_record")) != str(run_id):
        return EXIT_ENV, {
            "schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_OR_VACUOUS",
            "exit_code": EXIT_ENV,
            "reason": "run id does not match the frozen run_id_of_record",
            "expected_run_id": freeze.get("run_id_of_record"),
        }
    if not mount.is_dir():
        return EXIT_ENV, {
            "schema": SCHEMA, "run_id": run_id, "verdict": "ENVIRONMENT_OR_VACUOUS",
            "exit_code": EXIT_ENV, "reason": "accepted product mount absent",
            "mount": str(mount),
        }

    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _no_network_guard() as guard:
        r2 = gate_r2_freeze_pins_hold(freeze)
        r2["passed"] = bool(r2["pins"]["all_hold"])
        gates = {
            "R1_snapshot_identity_and_scope": gate_r1_snapshot_identity_and_scope(),
            "R2_freeze_pins_hold": r2,
            "R3_recorded_results_internally_consistent": gate_r3_recorded_results_internally_consistent(),
            "R4_coverage_unions_recompute_without_reach_loss": gate_r4_coverage_unions_recompute(mount),
            "R5_shipped_planner_unchanged_at_current_mount": gate_r5_shipped_planner_unchanged(mount),
            "R6_state_reconciled_and_resolvable": gate_r6_state_reconciled_and_resolvable(),
        }
        ctrl = controls(freeze, mount)
    network_attempts = guard.attempts

    gate_failures = [k for k, v in gates.items() if not v.get("passed")]
    control_failures = [k for k, v in ctrl.items() if not v.get("holds")]
    if control_failures:
        code, verdict = EXIT_ENV, "ENVIRONMENT_OR_VACUOUS"
    elif gate_failures:
        code, verdict = EXIT_DIVERGE, "RESUME_DIVERGENCE"
    else:
        code, verdict = EXIT_OK, "RESUME_VERIFIED_AND_AUDIT_READY"

    env = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "network_attempts": network_attempts,
    }
    for mod in ("numpy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = None

    return code, {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": DIRECTION_VERSION,
        "resumed_snapshot_run_id": RESUMED_SNAPSHOT_RUN_ID,
        "producer_snapshot_run_id": PRODUCER_RUN_ID,
        "snapshot_commit": SNAPSHOT_COMMIT,
        "accepted_base_commit": ACCEPTED_BASE_COMMIT,
        "generated_at_utc": started,
        "freeze_record_path": str(FREEZE_PATH.relative_to(REPO_ROOT)),
        "freeze_record_sha256": sha256_file(FREEZE_PATH),
        "frozen_hypothesis_path": str(HYPOTHESIS_PATH.relative_to(REPO_ROOT)),
        "frozen_hypothesis_sha256": sha256_file(HYPOTHESIS_PATH),
        "mount": str(mount),
        "product_mount_head": _git("-C", str(mount), "rev-parse", "HEAD")[1] or None,
        "verdict": verdict,
        "exit_code": code,
        "gate_failures": gate_failures,
        "control_failures": control_failures,
        "gates": gates,
        "controls": ctrl,
        "environment": env,
        "network_calls": 0,
        "claim_ceiling": hypothesis["claim_ceiling"],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    code, rec = run(args.run_id, Path(args.mount))
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                     encoding="utf-8")
    summary = {
        "verdict": rec.get("verdict"),
        "exit_code": code,
        "gate_failures": rec.get("gate_failures"),
        "control_failures": rec.get("control_failures"),
        "record": args.out,
    }
    print(json.dumps(summary, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
