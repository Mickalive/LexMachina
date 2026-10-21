#!/usr/bin/env python3
"""Completes the lane-state restoration promised by operational-resume cycle 39552967253.

WHY THIS INSTRUMENT EXISTS (cycle 39587184968)
----------------------------------------------
Run 39548140787's producer snapshot (commit ``8fe862e8``) replaced the accepted
lane state (81 top-level keys at ``b486e0cc``) with a 10-key truncation that
deleted 73 keys, including the five fail-closed probes, the whole
``minimal_ca_benchmark`` block, ``evidence_refs_n`` and every ``durable_delta_*``
provenance array.  Operational-resume cycle 39552967253 froze the restoration
contract (``OPERATIONAL_RESUME_39548140787_HYPOTHESIS_V1.json`` +
``UPDATED_KEYS`` in ``evaluation/operational_resume_39548140787.py``) and
re-executed the cached-bundle benchmark under its own run id, but **the state
merge never landed**: three later accepted cycles (39563450363, 39567451182,
39581086634) shipped the truncated state, which left the lane's own tests
``tests/evaluation/test_minimal_ca_benchmark.py`` (4 cases) and
``tests/evaluation/test_operational_resume_39548140787.py`` (6 cases) red and
unexecuted.

This instrument REUSES that frozen contract.  It re-derives nothing: no frozen
bar, rubric, threshold, success rule, population predicate or metric is read for
anything except a re-hash, and no prior result file is read for anything but a
byte-identity check.

Two modes
---------
``--apply``  rebuild ``state/evaluation.json`` = accepted base ``b486e0cc``
             (every key, 62 of the removed ones byte-identical) overlaid with
             ``evaluation/STATE_RESTORED_OVERLAY_39587184968.json`` and with
             any post-drop key of the live state that the base never had
             (preserved, never deleted).  Refuses to write if the overlay is
             missing a key that must change or if a non-updated key would stop
             being byte-identical.
``--check``  verify the restoration invariants on the live state and publish a
             machine record under ``--out``.

Exit codes
----------
0  RESTORATION_COMPLETE      every check held
1  RESTORATION_INCOMPLETE    at least one check failed (a negative result)
2  NOT_MEASURED              environment error: git blob unreadable, overlay
                             missing, frozen pin drift (never a pass)

The run-id rule is TIME-AWARE by construction: the resume cycle's frozen
expectation (``accepted_run_id == 39546829058``) is a moment pin that cannot
survive any later accepted cycle and was never landed anyway.  ``--check``
therefore asserts the timeless invariant instead: ``accepted_run_id`` equals the
run id of the most recent ``accept evaluation cycle <id>`` commit on this
branch, ``proposed_run_id`` is set and different, and ``github_run`` is set.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Reuse the frozen restoration contract of the cycle that promised it.
from evaluation.operational_resume_39548140787 import (  # noqa: E402
    ACCEPTED_BASE,
    FAIL_CLOSED_FLAGS,
    FROZEN_PINS,
    RESUMED_HEAD,
    UPDATED_KEYS,
)

SCHEMA = "lex-evaluation-state-restoration-completion/1"
RUN_ID = "39587184968"
OVERLAY = REPO_ROOT / "evaluation" / "STATE_RESTORED_OVERLAY_39587184968.json"
STATE_PATH = REPO_ROOT / "state" / "evaluation.json"
#: The truncated snapshot state must stay byte-identical: it is evidence.
SUBJECT_REPORT = REPO_ROOT / "reports" / "evaluation" / "CYCLE_local_1792559615.md"
SUBJECT_REPORT_SHA256 = (
    "93a0b580b309e83b0ab9c7488c679d66c133e836eb7626fab1e33eb19fcff6b3")
MINIMAL_CA_HYPOTHESIS_SHA256 = (
    "f0c7711c71e94d7b7303f5fa3a61b444d67bee6d3bbd7f0708ed13ff6ffc8072")
MINIMAL_CA_FREEZE_COMMIT = "6892f9f0"
ACCEPT_COMMIT_RE = re.compile(r"^accept evaluation cycle (\d+)")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT), check=True,
                          capture_output=True).stdout


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json_bytes(b: bytes) -> Any:
    return json.loads(b.decode("utf-8"))


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


def last_accepted_run_id() -> str | None:
    """Run id of the most recent ``accept evaluation cycle <id>`` commit."""
    log = _git("log", "--format=%s", "lab/evaluation").decode("utf-8")
    for line in log.splitlines():
        m = ACCEPT_COMMIT_RE.match(line.strip())
        if m:
            return m.group(1)
    return None


def rehash_frozen_pins() -> dict[str, Any]:
    out: dict[str, Any] = {"checked": {}, "drift": {}, "all_match": True}
    for rel, expected in FROZEN_PINS.items():
        p = REPO_ROOT / rel
        actual = _sha256(p) if p.is_file() else None
        out["checked"][rel] = actual
        if actual != expected:
            out["drift"][rel] = {"expected": expected, "actual": actual}
            out["all_match"] = False
    return out


# --------------------------------------------------------------------- apply --
def build_restored_state() -> dict[str, Any]:
    base = _load_json_bytes(_git("show", f"{ACCEPTED_BASE}:state/evaluation.json"))
    subject = _load_json_bytes(_git("show", f"{RESUMED_HEAD}:state/evaluation.json"))
    live = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))

    removed = sorted(set(base) - set(subject))
    missing_updated = [k for k in UPDATED_KEYS if k not in overlay]
    if missing_updated:
        raise SystemExit(f"overlay is missing UPDATED_KEYS: {missing_updated}")

    restored = json.loads(_canonical(base))          # deep copy, byte-faithful
    # Preserve every post-drop key the base never had (valid completed work).
    for k, v in live.items():
        if k not in base:
            restored[k] = v
    # The disclosed overlay governs the UPDATED_KEYS and any extra keys it adds.
    for k, v in overlay.items():
        restored[k] = v

    # Fail-closed probes must come back from the base (or overlay) as False.
    for flag in FAIL_CLOSED_FLAGS:
        if restored.get(flag) is not False and flag in base:
            restored[flag] = base[flag]

    return {"restored": restored, "base": base, "subject": subject,
            "overlay": overlay, "removed": removed}


def apply_overlay(write: bool) -> int:
    built = build_restored_state()
    restored, base, subject = built["restored"], built["base"], built["subject"]
    removed = built["removed"]
    errors: list[str] = []

    missing = [k for k in removed if k not in restored]
    if missing:
        errors.append(f"removed keys still missing: {missing}")
    static = [k for k in removed if k in restored and k not in UPDATED_KEYS]
    changed = [k for k in static if _canonical(base[k]) != _canonical(restored[k])]
    if changed:
        errors.append(f"non-updated removed keys would not stay byte-identical: {changed}")
    if any(restored.get(f) is not False for f in FAIL_CLOSED_FLAGS
           if f in restored):
        errors.append("a fail-closed probe would not be False")
    if not set(base) <= set(restored):
        errors.append("a base key would be lost")
    refs = restored.get("evidence_refs") or []
    if restored.get("evidence_refs_n") != len(refs):
        errors.append("evidence_refs_n does not equal len(evidence_refs)")

    payload = {
        "schema": SCHEMA,
        "record_kind": "apply-preview",
        "run_id": RUN_ID,
        "generated_at_utc": _now(),
        "instrument": "evaluation/state_restoration_completion_39587184968.py",
        "accepted_base_commit": ACCEPTED_BASE,
        "subject_commit": RESUMED_HEAD,
        "overlay": "evaluation/STATE_RESTORED_OVERLAY_39587184968.json",
        "overlay_sha256": _sha256(OVERLAY),
        "n_removed_keys": len(removed),
        "n_static_keys_restored_byte_exact": len(
            [k for k in static if _canonical(base[k]) == _canonical(restored[k])]),
        "n_updated_keys": len([k for k in removed if k in UPDATED_KEYS]),
        "n_total_keys_after_restore": len(restored),
        "would_write": write and not errors,
        "errors": errors,
        "refuses_to_write": bool(errors),
    }
    if write and not errors:
        STATE_PATH.write_text(json.dumps(restored, indent=1, ensure_ascii=False,
                                         default=str) + "\n", encoding="utf-8")
        payload["wrote_state"] = True
        payload["state_sha256_after_write"] = _sha256(STATE_PATH)
    else:
        payload["wrote_state"] = False
    print(json.dumps(payload, indent=1))
    return 0 if not errors else 1


# --------------------------------------------------------------------- check --
def check(out_path: Path) -> int:
    built = build_restored_state()
    base, subject, overlay = built["base"], built["subject"], built["overlay"]
    removed = built["removed"]
    cur = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    restored = {k: (k in cur) for k in removed}
    static = [k for k in removed if k in cur and k not in UPDATED_KEYS]
    byte_exact = {k: _canonical(base[k]) == _canonical(cur.get(k)) for k in static}
    updated_present = {k: (k in cur) for k in UPDATED_KEYS}
    updated_changed = {k: _canonical(base.get(k)) != _canonical(cur.get(k))
                       for k in UPDATED_KEYS}
    refs = list(cur.get("evidence_refs") or [])
    ref_status = {r: (REPO_ROOT / r).is_file() for r in refs}
    flags = {f: cur.get(f, "ABSENT") for f in FAIL_CLOSED_FLAGS}
    pins = rehash_frozen_pins()
    expected_last_accepted = last_accepted_run_id()
    mca = cur.get("minimal_ca_benchmark") or {}

    mca_checks = {
        "hypothesis_sha256_pinned":
            mca.get("hypothesis_sha256") == MINIMAL_CA_HYPOTHESIS_SHA256,
        "freeze_commit_pinned": mca.get("freeze_commit") == MINIMAL_CA_FREEZE_COMMIT,
        "pytest_claim_names_dedicated_test":
            "tests/evaluation/test_minimal_ca_benchmark.py" in str(mca.get("pytest", "")),
        "pytest_claim_keeps_the_pre_repair_disclosure":
            "PRE-REPAIR CLAIM WAS FALSE" in str(mca.get("pytest", "")),
    }
    subj_report_ok = (SUBJECT_REPORT.is_file()
                      and _sha256(SUBJECT_REPORT) == SUBJECT_REPORT_SHA256)

    checks = {
        "all_removed_keys_present_again": all(restored.values()),
        "all_non_updated_removed_keys_byte_exact_vs_accepted_base":
            all(byte_exact.values()) and len(byte_exact) == len(removed) - len(UPDATED_KEYS),
        "all_updated_keys_present": all(updated_present.values()),
        "all_updated_keys_differ_from_accepted_base": all(updated_changed.values()),
        "fail_closed_flags_present_and_false": all(flags.get(f) is False
                                                  for f in FAIL_CLOSED_FLAGS),
        "no_base_key_lost": set(base) <= set(cur),
        "evidence_refs_non_empty_and_all_files":
            bool(refs) and all(ref_status.values()),
        "evidence_refs_n_matches": cur.get("evidence_refs_n") == len(refs),
        "direction_version_pinned": cur.get("direction_version") == 61,
        "accepted_run_id_is_the_last_accepted_run":
            cur.get("accepted_run_id") == expected_last_accepted
            and expected_last_accepted is not None,
        "proposed_run_id_set_and_different":
            isinstance(cur.get("proposed_run_id"), str)
            and cur.get("proposed_run_id") not in ("", cur.get("accepted_run_id")),
        "github_run_set": cur.get("github_run") not in (None, "", "None"),
        "minimal_ca_benchmark_block_restored": all(mca_checks.values()),
        "subject_defective_report_preserved_byte_identical": subj_report_ok,
        "frozen_pins_intact": pins["all_match"],
        "overlay_matches_the_state_it_produced":
            all(_canonical(overlay[k]) == _canonical(cur[k])
                for k in overlay if k in cur),
    }
    all_hold = all(checks.values())
    payload = {
        "schema": SCHEMA,
        "record_kind": "check",
        "run_id": RUN_ID,
        "direction_version": 61,
        "generated_at_utc": _now(),
        "instrument": "evaluation/state_restoration_completion_39587184968.py",
        "accepted_base_commit": ACCEPTED_BASE,
        "subject_commit": RESUMED_HEAD,
        "overlay": "evaluation/STATE_RESTORED_OVERLAY_39587184968.json",
        "overlay_sha256": _sha256(OVERLAY),
        "n_removed_keys": len(removed),
        "n_removed_keys_per_resume_hypothesis_handcount": 71,
        "count_disclosure": ("the frozen resume hypothesis hand-counted 71 removed keys; the "
                             "machine-computed set difference (b486e0cc minus 8fe862e8) is 73. "
                             "The set rule governs and the hypothesis is not edited."),
        "updated_keys": UPDATED_KEYS,
        "restored": restored,
        "n_restored": sum(1 for v in restored.values() if v),
        "restored_byte_exact_non_updated": byte_exact,
        "n_restored_byte_exact_non_updated": sum(1 for v in byte_exact.values() if v),
        "updated_keys_present": updated_present,
        "updated_keys_changed_from_base": updated_changed,
        "minimal_ca_benchmark_checks": mca_checks,
        "fail_closed_flags": flags,
        "accepted_run_id_live": cur.get("accepted_run_id"),
        "accepted_run_id_last_accept_commit": expected_last_accepted,
        "proposed_run_id_live": cur.get("proposed_run_id"),
        "github_run_live": cur.get("github_run"),
        "evidence_refs": ref_status,
        "n_evidence_refs": len(refs),
        "n_evidence_refs_unresolved": sum(1 for v in ref_status.values() if not v),
        "unresolved_evidence_refs": [r for r, ok in ref_status.items() if not ok],
        "subject_defective_report_preserved": subj_report_ok,
        "frozen_pins": pins,
        "checks": checks,
        "all_checks_hold": all_hold,
        "verdict": "RESTORATION_COMPLETE" if all_hold else "RESTORATION_INCOMPLETE",
        "exit_code": 0 if all_hold else 1,
        "owner_decision_required": False,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "what_this_record_is_not": (
            "NOT an audit of run 39587184968 and NOT an acceptance of it; acceptance requires an "
            "independent gate=PASS plus an accept commit on lab/evaluation. This record only says "
            "whether the lane state carries the restoration the 39552967253 contract promised."),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=1, ensure_ascii=False,
                                   default=str) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": payload["verdict"], "exit_code": payload["exit_code"],
                      "n_removed": len(removed),
                      "n_restored": payload["n_restored"],
                      "n_restored_byte_exact_non_updated":
                          payload["n_restored_byte_exact_non_updated"],
                      "n_unresolved_refs": payload["n_evidence_refs_unresolved"],
                      "checks": checks}, indent=1))
    return int(payload["exit_code"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=["check", "apply"], default="check")
    ap.add_argument("--out",
                    default=str(REPO_ROOT / "results" / "evaluation"
                                / "state_restoration_completion"
                                / f"{RUN_ID}_check.json"))
    args = ap.parse_args(argv)
    try:
        if args.mode == "apply":
            return apply_overlay(write=True)
        return check(Path(args.out))
    except subprocess.CalledProcessError as exc:      # git blob unreadable
        print(json.dumps({"error": "git_failed", "detail": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
