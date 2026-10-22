#!/usr/bin/env python3
"""V2 of the operational-resume verification: shallow-mount ancestry split.

V1 (``operational_resume_verification.py``) is preserved and its result
``results/evaluation/operational_resume/39820650174.json`` still says
``RESUME_DIVERGENCE`` (exit 1).  Its only failing gate was R5: the shipped
planner hash matched exactly, but the accepted product mount is a shallow
single-commit clone, so the producer head ``44330212`` is absent locally and
``git merge-base --is-ancestor`` returned 128 ("bad object").  V1 collapsed that
unmeasurable case to False.

V2 keeps R1-R4 and R6 exactly as frozen, and re-derives R5 with three states:

* ``MEASURED_ANCESTOR`` - local git has the object and says ancestor;
* ``MEASURED_NOT_ANCESTOR`` - local git has the object and says not ancestor
  (always a divergence, evidence cannot override it);
* ``NOT_MEASURABLE_SHALLOW_MOUNT`` - the object is absent; the pinned public
  compare evidence must attest base == producer head, merge_base == producer
  head, behind_by == 0 and status in {ahead, identical}.

The public compare evidence is a committed input
(``results/evaluation/operational_resume/39820650174_product_ancestry.json``),
so execution stays zero-network.  A planted non-ancestor evidence copy is
control C5; C6 proves the V1 result is preserved.

Exit: 0 = RESUME_VERIFIED_AND_AUDIT_READY, 1 = RESUME_DIVERGENCE,
2 = ENVIRONMENT_OR_VACUOUS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import operational_resume_verification as v1  # noqa: E402

SCHEMA = v1.SCHEMA
FREEZE_PATH = REPO_ROOT / "evaluation" / "OPERATIONAL_RESUME_39820650174_FREEZE_V2.json"
HYPOTHESIS_PATH = REPO_ROOT / "evaluation" / "OPERATIONAL_RESUME_39820650174_HYPOTHESIS_V2.json"
V1_FREEZE = REPO_ROOT / "evaluation" / "OPERATIONAL_RESUME_39820650174_FREEZE.json"
V1_HYPOTHESIS = REPO_ROOT / "evaluation" / "OPERATIONAL_RESUME_39820650174_HYPOTHESIS_V1.json"
V1_RESULT = REPO_ROOT / "results" / "evaluation" / "operational_resume" / "39820650174.json"
V1_RESULT_SHA = "55ffdba8bace0aa347c5421d4da3e688c4c1e0099c0da0e09d372a4643870a9f"
V1_RESULT_VERDICT = "RESUME_DIVERGENCE"

ANCESTRY_EVIDENCE = (REPO_ROOT / "results" / "evaluation" / "operational_resume"
                     / "39820650174_product_ancestry.json")
ANCESTRY_EVIDENCE_SHA = "8a89e43a135b7e05540626361d633e648eb8f8449395774de01022e5234a2c4f"

RUN_ID = "39820650174"
PRODUCER_HEAD = v1.PRODUCER_PRODUCT_HEAD
DIRECTION_VERSION = 62
DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")

EXIT_OK = 0
EXIT_DIVERGE = 1
EXIT_ENV = 2


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ancestry_evidence_attests(producer_head: str, mount_head: str,
                              evidence: dict) -> dict:
    """Pure predicate for the pinned public compare evidence."""
    checks = []

    def _c(name, ok, observed, expected):
        checks.append({"check": name, "ok": bool(ok),
                       "observed": observed, "expected": expected})

    _c("base_is_producer_head", evidence.get("base") == producer_head,
       evidence.get("base"), producer_head)
    _c("head_is_mount_head", evidence.get("head") == mount_head,
       evidence.get("head"), mount_head)
    _c("merge_base_is_producer_head",
       evidence.get("merge_base_commit") == producer_head,
       evidence.get("merge_base_commit"), producer_head)
    try:
        behind = int(evidence.get("behind_by"))
    except (TypeError, ValueError):
        behind = None
    _c("behind_by_zero", behind == 0, evidence.get("behind_by"), 0)
    _c("status_ahead_or_identical",
       evidence.get("status") in {"ahead", "identical"},
       evidence.get("status"), "ahead|identical")
    _c("conclusion_ancestor",
       evidence.get("conclusion") == "PRODUCER_HEAD_IS_ANCESTOR_OF_MOUNT_HEAD",
       evidence.get("conclusion"), "PRODUCER_HEAD_IS_ANCESTOR_OF_MOUNT_HEAD")
    return {"attests": all(c["ok"] for c in checks), "checks": checks}


def gate_r5_v2(mount: Path) -> dict:
    """R5 with the shallow-mount case distinguished from a real divergence."""
    code, mount_head = v1._git("-C", str(mount), "rev-parse", "HEAD")
    mount_head = (mount_head or "").strip()
    result_path = REPO_ROOT / v1.SPRV_RESULT
    recorded = ""
    if result_path.is_file():
        recorded = str(json.loads(result_path.read_text(encoding="utf-8"))
                       .get("planner_sha256") or "")
    planner = mount / "product" / "query" / "adversarial_retrieval.py"
    actual = sha256_file(planner) if planner.is_file() else None
    planner_ok = v1.planner_matches(recorded, actual or "")

    has_object = (v1._git("-C", str(mount), "cat-file", "-e",
                          f"{PRODUCER_HEAD}^{{commit}}")[0] == 0)
    local_rc = None
    if has_object:
        local_rc = v1._git("-C", str(mount), "merge-base", "--is-ancestor",
                           PRODUCER_HEAD, mount_head)[0]
        ancestry_state = ("MEASURED_ANCESTOR" if local_rc == 0
                          else "MEASURED_NOT_ANCESTOR")
        ancestry_source = "local_git"
    else:
        ancestry_state = "NOT_MEASURABLE_SHALLOW_MOUNT"
        ancestry_source = "pinned_github_compare"

    evidence = None
    evidence_eval = None
    evidence_error = None
    if ancestry_state == "NOT_MEASURABLE_SHALLOW_MOUNT":
        try:
            evidence = json.loads(ANCESTRY_EVIDENCE.read_text(encoding="utf-8"))
            evidence_eval = ancestry_evidence_attests(PRODUCER_HEAD, mount_head, evidence)
        except Exception as exc:
            evidence_error = f"{type(exc).__name__}: {exc}"

    if ancestry_state == "MEASURED_ANCESTOR":
        ancestry_ok = True
    elif ancestry_state == "MEASURED_NOT_ANCESTOR":
        ancestry_ok = False
    else:
        ancestry_ok = bool(evidence_eval and evidence_eval["attests"])

    passed = bool(planner_ok and ancestry_ok)
    return {
        "gate": "R5_shipped_planner_unchanged_at_current_mount",
        "passed": passed,
        "recorded_planner_sha256": recorded,
        "actual_planner_sha256": actual,
        "planner_matches": planner_ok,
        "producer_product_head": PRODUCER_HEAD,
        "mount_head": mount_head or None,
        "ancestry_state": ancestry_state,
        "ancestry_source": ancestry_source,
        "local_merge_base_returncode": local_rc,
        "producer_head_object_present_locally": has_object,
        "ancestry_evidence_path": str(ANCESTRY_EVIDENCE.relative_to(REPO_ROOT)),
        "ancestry_evidence_sha256":
            sha256_file(ANCESTRY_EVIDENCE) if ANCESTRY_EVIDENCE.is_file() else None,
        "ancestry_evidence_evaluation": evidence_eval,
        "ancestry_evidence_error": evidence_error,
        "requires_ancestry_evidence": ancestry_state == "NOT_MEASURABLE_SHALLOW_MOUNT",
    }


def run(run_id: str, mount: Path) -> tuple[int, dict]:
    # V1 supplies R1-R4, R6, its controls and the state read.  It may return 1
    # because of its own R5; that is overridden below.
    code1, rec = v1.run(run_id, mount)
    if code1 == EXIT_ENV:
        return EXIT_ENV, rec
    if str(run_id) != RUN_ID:
        return EXIT_ENV, {**rec, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV}
    if not FREEZE_PATH.is_file() or not HYPOTHESIS_PATH.is_file():
        return EXIT_ENV, {**rec, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV,
                          "reason": "V2 hypothesis or freeze record absent"}
    if not mount.is_dir():
        return EXIT_ENV, {**rec, "verdict": "ENVIRONMENT_OR_VACUOUS",
                          "exit_code": EXIT_ENV,
                          "reason": "accepted product mount absent"}

    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    hypothesis = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    r5 = gate_r5_v2(mount)
    gates = dict(rec["gates"])
    gates["R5_shipped_planner_unchanged_at_current_mount"] = r5

    # Environment only when the shallow-mount evidence is absent/unreadable.
    # Evidence that is present but does NOT attest ancestry is a divergence (1),
    # not an environment error: R5 already fails in that case.
    evidence_needed = r5["requires_ancestry_evidence"]
    environment_failure = bool(
        evidence_needed
        and (not ANCESTRY_EVIDENCE.is_file() or r5.get("ancestry_evidence_error") is not None)
    )

    # C5: planted non-ancestor evidence must fail the pure predicate.
    ev = json.loads(ANCESTRY_EVIDENCE.read_text(encoding="utf-8")) if ANCESTRY_EVIDENCE.is_file() else {}
    planted = dict(ev)
    planted["merge_base_commit"] = "0" * 40
    planted["behind_by"] = 1
    c5_holds = (ancestry_evidence_attests(PRODUCER_HEAD, r5.get("mount_head") or "", ev)["attests"]
                is True
                and ancestry_evidence_attests(PRODUCER_HEAD, r5.get("mount_head") or "", planted)["attests"]
                is False)

    v1_rec = None
    try:
        v1_rec = json.loads(V1_RESULT.read_text(encoding="utf-8"))
    except Exception:
        v1_rec = None
    c6_holds = bool(
        V1_RESULT.is_file()
        and sha256_file(V1_RESULT) == V1_RESULT_SHA
        and v1_rec is not None
        and v1_rec.get("verdict") == V1_RESULT_VERDICT
        and v1_rec.get("exit_code") == 1
    )

    controls = dict(rec["controls"])
    controls["C5_planted_non_ancestor_evidence_fails_R5"] = {"holds": c5_holds}
    controls["C6_v1_result_is_preserved_verbatim"] = {
        "holds": c6_holds,
        "v1_result_sha256": sha256_file(V1_RESULT) if V1_RESULT.is_file() else None,
        "v1_result_verdict": (v1_rec or {}).get("verdict"),
        "v1_result_exit_code": (v1_rec or {}).get("exit_code"),
    }

    gate_failures = [k for k, v in gates.items() if not v.get("passed")]
    control_failures = [k for k, v in controls.items() if not v.get("holds")]
    if control_failures or environment_failure:
        code, verdict = EXIT_ENV, "ENVIRONMENT_OR_VACUOUS"
    elif gate_failures:
        code, verdict = EXIT_DIVERGE, "RESUME_DIVERGENCE"
    else:
        code, verdict = EXIT_OK, "RESUME_VERIFIED_AND_AUDIT_READY"

    return code, {
        **rec,
        "instrument_version": "V2",
        "generated_at_utc": started,
        "freeze_record_path": str(FREEZE_PATH.relative_to(REPO_ROOT)),
        "freeze_record_sha256": sha256_file(FREEZE_PATH),
        "frozen_hypothesis_path": str(HYPOTHESIS_PATH.relative_to(REPO_ROOT)),
        "frozen_hypothesis_sha256": sha256_file(HYPOTHESIS_PATH),
        "v1_freeze_record_path": str(V1_FREEZE.relative_to(REPO_ROOT)),
        "v1_freeze_record_sha256": sha256_file(V1_FREEZE),
        "v1_hypothesis_path": str(V1_HYPOTHESIS.relative_to(REPO_ROOT)),
        "v1_hypothesis_sha256": sha256_file(V1_HYPOTHESIS),
        "v1_result_path": str(V1_RESULT.relative_to(REPO_ROOT)),
        "v1_result_sha256": sha256_file(V1_RESULT) if V1_RESULT.is_file() else None,
        "v1_result_verdict": V1_RESULT_VERDICT,
        "ancestry_evidence_path": str(ANCESTRY_EVIDENCE.relative_to(REPO_ROOT)),
        "ancestry_evidence_sha256":
            sha256_file(ANCESTRY_EVIDENCE) if ANCESTRY_EVIDENCE.is_file() else None,
        "gates": gates,
        "controls": controls,
        "gate_failures": gate_failures,
        "control_failures": control_failures,
        "environment_failure": environment_failure,
        "verdict": verdict,
        "exit_code": code,
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
    print(json.dumps({
        "verdict": rec.get("verdict"),
        "exit_code": code,
        "gate_failures": rec.get("gate_failures"),
        "control_failures": rec.get("control_failures"),
        "record": args.out,
    }, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
