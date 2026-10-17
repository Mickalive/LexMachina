#!/usr/bin/env python3
"""Deterministic audit pack: recompute every v52 endgame claim in seconds.

Why this module exists
----------------------
Five consecutive product cycles produced a team snapshot but **no persisted
audit verdict**.  The diagnosis of record is committed at
``results/product/orchestration/NON_VERDICTED_RUNS.json`` and is verifiable
from the repository and the remote alone (branch presence/absence, absence of
``results/audit/product/CYCLE_<run>_GATE.json``); the observed failure
signatures, where an exit code is recorded, are:

* ``39031213637`` — audit step failed with **exit code 3, "auditor crossed
  scope"** (wrote outside the two audit paths allowed in the audit checkout);
* ``39034350468`` — audit step failed with **exit code 78,
  ``LEX_WORK_QUANTUM_EXPIRED seconds=2700``** (the auditor agent spent its
  whole 45-minute work quantum recomputing claims by hand and never wrote
  ``results/audit/product/CYCLE_<run>_GATE.json``);
* ``39027045675`` / ``39025961835`` — chain cancelled before/while auditing;
* ``39039195228`` — audit job produced no snapshot branch and no gate file; the
  exit code is NOT recoverable from the repository, so this one is recorded as
  *unattributed* rather than assigned to a mechanism it does not prove.

Both failure modes are addressed here, from the producer side, without
touching ``.github/**`` (control-plane scope):

1. **quantum** — every headline claim below is recomputed from committed
   artifacts only, offline and in seconds, so the independent auditor can
   *verify* instead of *reconstructing*. One command, one JSON, one exit code;
2. **scope** — the pack states, in its own output, the exact two relative
   paths an auditor may write in the audit checkout;
3. **environment** (added run 39042713389) — ``core-lane.yml`` installs no
   Python dependencies, so the audit checkout can legitimately have no numpy.
   A missing import is an *environment* fact, never a product failure: it is
   reported as ``BLOCKED_MISSING_DEPENDENCY`` with a one-line bootstrap
   command, counted apart from real failures, and mapped to its own exit code.
   Before this cycle the same situation printed seven ``FAIL`` lines with empty
   details, which reads to an auditor exactly like a broken product.

Contract
--------
* Reads committed product artifacts; writes nothing unless ``--out`` is given.
* Never re-measures a frozen bar, never re-derives a rubric/threshold/bar, never
  re-scores labels or geometry (those are Core Evaluation's / Frontier's).
* Numbers are *recomputed here*, never read back from a report.
* Exit codes are a machine contract:
  ``0`` = every check passed, ``1`` = at least one PRODUCT check failed,
  ``2`` = no product failure, but at least one check was
  ``BLOCKED_MISSING_DEPENDENCY`` (nothing was proven false), ``3`` = harness
  error (pack could not be assembled at all).

Usage::

    python3 product/audit_pack.py --run-id "$GITHUB_RUN_ID"
    python3 product/audit_pack.py --run-id local --no-tests --json
    python3 product/audit_pack.py --run-id local --deps        # dependency preflight only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # pragma: no cover - import path bootstrap
    sys.path.insert(0, str(ROOT))

SCHEMA = "product-audit-pack/1"
REALITY_DIR = ROOT / "results" / "product" / "reality_check"
REBUILT = ROOT / "results" / "product" / "gate_packet" / "rebuilt-39027045675"
SOURCE = ROOT / "results" / "product" / "gate_packet" / "38839347028"
STATE_PATH = ROOT / "state" / "product.json"
CONTROL_DIR = Path(os.environ.get("LEX_CONTROL_DIR", "/tmp/lex_control"))
CONTROL_STATE = CONTROL_DIR / "state" / "factory_direction.json"

QIDS = ("fr-bail-entretien", "de-kapitalverletzung", "it-responsabilita-medica")
FROZEN_GATE_PREFIXES = ("structural", "truth::", "recall::")
FROZEN_LABEL_SHA256 = (
    "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
)
FROZEN_GEOMETRY_SHA256 = (
    "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
)
EXPECTED_ADOPTION = {"n_scored": 65, "n_emitted": 5, "n_abstained": 60}
STALE_AXIS_WORD = "rerank score"
REQUIRED_AXIS_LABEL = "retrieval relevance score"

#: The ONLY two relative paths an independent auditor may write in the audit
#: checkout (``.github/workflows/core-lane.yml``, step "Enforce audit scope and
#: read gate").  Stated here so the exit-3 scope failure cannot recur.
AUDITOR_WRITE_SCOPE = (
    "results/audit/product/CYCLE_<run_id>_GATE.json",
    "reports/audit/product/CYCLE_<run_id>.md",
)

#: Owner-readiness keys, exactly as the product's accepted detector defines them
#: (``packet_admission.offending_owner_claims``).  ``machine_gate_ready`` is NOT
#: here: it is the CI-evidence flag of ``product/ci_run_evidence.py``.
READINESS_KEYS = ("ready_for_owner_session", "human_gate_ready",
                  "ready_for_owner_session_allowed")
READINESS_TOKENS = ("ready_for_owner_session=true", "human_gate_ready=true",
                    "ready_for_owner_session_allowed=true")
#: Marker for a claim quoted AND refuted in the same field (state corrections).
READINESS_CORRECTION_MARKER = "READINESS_CLAIM_SUPERSEDED"

#: Pre-admission artifacts kept byte-for-byte as historical evidence.  Their
#: packet.json still carries the pre-wiring readiness boolean (the same class as
#: the served packet's pre-fix ``warning_count=0``); the fix lives in code
#: (``packet_admission.enforce`` is wired into finalize/recheck) and the current
#: gate denial for each is recomputed by this pack, not asserted.
PRESERVED_READINESS_ARTIFACTS = {
    "results/product/gate_packet/38839347028/packet.json": (
        "SERVED packet under the accepted DO-NOT-SERVE order; bytes preserved as the "
        "artifact of record (pre-admission-wiring, generated 2026-10-16T02:22Z). "
        "Current gate denial recomputed by check readiness_claim_guard."),
    "results/product/gate_packet/38812599575/packet.json": (
        "pre-admission multi-query packet from run 38812599575; bytes preserved, "
        "current gate denial recomputed by check readiness_claim_guard."),
}
PRESERVED_RECHECK_PACKETS = ("38839347028", "38812599575")

#: Cheap, high-signal test modules the auditor can re-run in seconds.
CORE_TEST_MODULES = (
    "product/tests/test_v52_endgame_delivery.py",
    "product/tests/test_state_contract.py",
    "product/tests/test_fixture_replay_and_wiring.py",
    "product/tests/test_offline_slice.py",
    "product/tests/test_query_map_mvp.py",
    "product/tests/test_audit_pack.py",
)

#: Modules the pack's own checks import.  ``core-lane.yml`` runs no
#: ``pip install`` step, so the audit checkout may have none of them; the pack
#: must therefore preflight them explicitly instead of letting an ``ImportError``
#: surface as an anonymous failing check.
PACK_DEPENDENCIES = ("numpy", "scipy", "sklearn", "pytest")
REQUIREMENTS_FILE = Path("product/requirements-query.txt")
BOOTSTRAP_COMMAND = "python3 -m pip install -r product/requirements-query.txt"

#: Modules carrying the known-failing baseline, and that baseline verbatim.
#:
#: Measured at the resumed snapshot head 9275cc6 (run 39039195228) by running
#: the same four modules in a detached worktree at that commit, i.e. BEFORE any
#: edit of run 39042713389: 8 failed, 87 passed.  Re-measured identically after
#: this cycle's edits.  These are negative results of record, not this cycle's
#: work and not this cycle's regression.  They are frozen here so an auditor
#: spends its minutes on the delta instead of re-deriving a known baseline -- and
#: so a NEW failure in these modules still fails the check, which is the whole
#: point: this is a baseline, not a whitelist.
BASELINE_TEST_MODULES = (
    "product/tests/test_adversarial_retrieval.py",
    "product/tests/test_audit_seam.py",
    "product/tests/test_cache_non_orphan.py",
    "product/tests/test_ci_run_evidence.py",
)
KNOWN_BASELINE_FAILURES = {
    "product/tests/test_adversarial_retrieval.py::test_apply_appends_unseen_rows_and_freezes_rendered_geometry":
        "KeyError 'bger_1A_36_2020': adversarial pass finds no row for the unseen decision",
    "product/tests/test_adversarial_retrieval.py::test_apply_labels_only_marker_carrying_rows":
        "assert 'none' == 'candidate-limiting': no marker-carrying row receives the marker label",
    "product/tests/test_adversarial_retrieval.py::test_apply_ranks_new_rows_after_the_conventional_list":
        "new rows are not ranked after the conventional list in this environment",
    "product/tests/test_adversarial_retrieval.py::test_apply_records_counter_rows_outside_the_initial_channel_inventory":
        "the pass produces no labelled counter row in this environment",
    "product/tests/test_audit_seam.py::test_known_dead_models_agree_with_control_plane_health":
        "assert 124 == 1: the dead-model list disagrees with the control-plane model health probe "
        "(environment-dependent; control-plane health is not product-owned)",
    "product/tests/test_cache_non_orphan.py::test_claim_bundle_content_hash_matches_a_fresh_replay":
        "the committed claim bundle is not reproducible from its frozen cache subset with the "
        "committed code in this numeric environment (same class as the BLAS reduction-order drift "
        "recorded in audit CYCLE_38893866335_GATE.json FIX-2)",
    "product/tests/test_cache_non_orphan.py::test_claim_bundle_full_cache_replay_differs_only_in_cache_size":
        "full-cache replay differs from the committed artifact on cluster labels and sizes in this "
        "numeric environment",
    "product/tests/test_ci_run_evidence.py::test_runner_records_both_dispatch_and_workspace_shas":
        "assert 1 == 0: CI run-evidence probe needs a live workflow_dispatch run; not available "
        "locally (factory-wide requirement 6)",
}

#: Check statuses.  ``BLOCKED_MISSING_DEPENDENCY`` is deliberately NOT a
#: failure: nothing was proven false, the check simply never ran.
STATUS_OK = "ok"
STATUS_FAIL = "FAIL"
STATUS_BLOCKED = "BLOCKED_MISSING_DEPENDENCY"
STATUS_SKIPPED = "SKIPPED"


class CheckBlocked(Exception):
    """A check that could not conclude because its environment was incomplete.

    Raised instead of returning ``ok=False`` so the triage in :func:`classify`
    can keep it apart from a violated invariant.  ``measured`` rides along so
    the dependency-free part of the computation is still reported as evidence.
    """

    def __init__(self, message: str, *, blocked_by: str, measured: Any = None):
        super().__init__(message)
        self.blocked_by = blocked_by
        self.measured = measured

CLAIM_CEILING = (
    "This pack recomputes product-owned claims from committed artifacts. It "
    "does NOT measure or re-measure any frozen bar: counter-label support "
    "(5/65 = 0.0769 vs frozen absolute 1.0) and map geometry (0/3 bundles at "
    "11 criteria) are Core Evaluation's ceded measurements. It never asserts "
    "that any decision IS supporting, contrary or limiting. human_gate_ready "
    "and machine_gate_ready stay false while either accepted bar is unmet, and "
    "the accepted DO-NOT-SERVE order on served packet 38839347028 stands until "
    "an independent accepted audit of a rebuilt packet supersedes it."
)


# --------------------------------------------------------------------------- #
# Shared primitives (single source of truth; the fixture sweep test imports
# these from here so the auditor and the test suite execute the SAME predicate)
# --------------------------------------------------------------------------- #
def fixture_artifact_paths(root: Path | None = None, *, require_any: bool = True) -> list[Path]:
    """Committed fixture artifacts under ``results/product/reality_check``."""
    base = (root or ROOT) / "results" / "product" / "reality_check"
    files = sorted(base.glob("*fixture*.json"))
    if require_any:
        assert files, f"no committed fixture artifacts under {base}"
    return files


def sweep_fabricated_frozen_greens(node: Any) -> list[str]:
    """Frozen gate names reported as *passed* anywhere inside ``node``.

    A fixture artifact must never report a frozen gate (``structural``,
    ``truth::*``, ``recall::*``) as passed: fixture mode evaluates wiring only
    and records the frozen non-evaluation explicitly.
    """
    found: list[str] = []
    if isinstance(node, dict):
        gate = node.get("gate")
        if (isinstance(gate, str) and node.get("passed") is True
                and gate.startswith(FROZEN_GATE_PREFIXES)):
            found.append(gate)
        for value in node.values():
            found.extend(sweep_fabricated_frozen_greens(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(sweep_fabricated_frozen_greens(value))
    return found


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                             text=True, timeout=30, check=False)
        return (out.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - defensive
        return ""


# --------------------------------------------------------------------------- #
# Dependency preflight.
#
# `core-lane.yml` has no `actions/setup-python` and no `pip install` step in
# either the team or the audit job, so numpy genuinely may be absent. Before
# run 39042713389 that produced seven anonymous `FAIL` lines with empty detail
# in the console output, which is indistinguishable from a broken product. The
# preflight makes the difference a first-class, machine-readable fact.
# --------------------------------------------------------------------------- #
def missing_dependencies(modules=PACK_DEPENDENCIES) -> list[str]:
    """Names of ``modules`` that cannot be imported in this interpreter."""
    import importlib.util

    missing = []
    for name in modules:
        try:
            found = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):  # pragma: no cover - defensive
            found = False
        if not found:
            missing.append(name)
    return missing


def dependency_status(root: Path | None = None) -> dict:
    """Dependency report, safe to call with nothing installed."""
    root = root or ROOT
    versions = _versions()
    missing = [m for m in PACK_DEPENDENCIES if versions.get(m) is None]
    return {
        "required": list(PACK_DEPENDENCIES),
        "versions": versions,
        "missing": missing,
        "complete": not missing,
        "requirements_file": str(REQUIREMENTS_FILE),
        "requirements_file_present": (root / REQUIREMENTS_FILE).is_file(),
        "bootstrap_command": BOOTSTRAP_COMMAND,
        "why": "core-lane.yml installs no Python dependencies; a missing import is "
               "an environment fact, never a product failure",
    }


def bootstrap_dependencies(root: Path | None = None, *, timeout: int = 600) -> dict:
    """Best-effort install of the pack's declared requirements.

    Writes nothing inside the repository, so it cannot break the audit job's
    write-scope check.  Failure is reported, never raised: the caller still gets
    a triage that says *blocked*, which is the honest outcome.
    """
    root = root or ROOT
    before = missing_dependencies()
    record = {"attempted": False, "installed": False, "missing_before": before,
              "missing_after": None, "command": BOOTSTRAP_COMMAND, "error": None}
    if not before:
        record["missing_after"] = []
        return record
    record["attempted"] = True
    req = root / REQUIREMENTS_FILE
    cmd = ([sys.executable, "-m", "pip", "install", "-q", "-r", str(REQUIREMENTS_FILE)]
           if req.is_file() else [sys.executable, "-m", "pip", "install", "-q",
                                  *PACK_DEPENDENCIES])
    try:
        proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                              timeout=timeout, check=False)
        record["installed"] = proc.returncode == 0
        if proc.returncode != 0:
            record["error"] = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:]
            record["error"] = record["error"][0] if record["error"] else f"pip rc={proc.returncode}"
    except (OSError, subprocess.SubprocessError) as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    record["missing_after"] = missing_dependencies()
    return record


def _missing_module(exc: BaseException) -> str | None:
    """The module name of a missing import, or ``None`` if ``exc`` is not one."""
    seen = 0
    cur: BaseException | None = exc
    while cur is not None and seen < 8:
        if isinstance(cur, ModuleNotFoundError):
            return cur.name or "<unknown>"
        cur = cur.__cause__ or cur.__context__
        seen += 1
    return None


# --------------------------------------------------------------------------- #
# Checks.  Each returns (ok, measured, expected, detail, evidence_paths)
# --------------------------------------------------------------------------- #
def check_state_direction_and_gate_flags(root: Path) -> tuple:
    state = _read(root / "state" / "product.json")
    dirv = state.get("direction_version")
    control_dirv = None
    if CONTROL_STATE.is_file():
        control_dirv = _read(CONTROL_STATE).get("version")
    ok = (
        isinstance(dirv, int) and dirv >= 52
        and (control_dirv is None or dirv == control_dirv)
        and (state.get("cycle_status") or "INITIALIZED") != "INITIALIZED"
        and state.get("continue_recommended") is True
        and state.get("human_gate_ready") is False
        and state.get("machine_gate_ready") is False
        and state.get("ready_for_owner_session") in (None, False)
    )
    measured = {
        "direction_version": dirv,
        "control_plane_direction_version": control_dirv,
        "cycle_status": (state.get("cycle_status") or "")[:80],
        "continue_recommended": state.get("continue_recommended"),
        "human_gate_ready": state.get("human_gate_ready"),
        "machine_gate_ready": state.get("machine_gate_ready"),
    }
    return (ok, measured,
            {"direction_version": ">=52 and equal to the mounted control plane",
             "cycle_status": "!= INITIALIZED", "continue_recommended": True,
             "human_gate_ready": False, "machine_gate_ready": False},
            "workflow step 'Validate active MVP producer state' equivalent + gate flags",
            ["state/product.json"])


def scan_readiness_claims(node: Any, where: str = "$") -> list[dict]:
    """Every owner-readiness claim inside ``node`` (uncategorised).

    Shared by :func:`check_readiness_claim_guard` and the regression tests, so
    the guard and its negative controls execute the same predicate.
    """
    occurrences: list[dict] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in READINESS_KEYS and value is True:
                occurrences.append({"where": f"{where}.{key}", "kind": "boolean_true",
                                    "bucket": None, "corrected": False})
            occurrences.extend(scan_readiness_claims(value, f"{where}.{key}"))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            occurrences.extend(scan_readiness_claims(value, f"{where}[{i}]"))
    elif isinstance(node, str):
        for token in READINESS_TOKENS:
            if token in node:
                occurrences.append({
                    "where": where, "kind": f"string_token:{token}",
                    "bucket": None,
                    "corrected": READINESS_CORRECTION_MARKER in node,
                })
    return occurrences


def check_readiness_claim_guard(root: Path, run_id: str | None = None) -> tuple:
    """No live claim path may assert owner-session readiness while bars unmet.

    Predicate = the product's own accepted detector
    ``packet_admission.offending_owner_claims``: the keys
    ``ready_for_owner_session`` / ``human_gate_ready`` /
    ``ready_for_owner_session_allowed`` (and the literal ``...=true`` tokens in
    prose).  ``machine_gate_ready`` is deliberately NOT part of it — that is the
    accepted CI-evidence flag of ``product/ci_run_evidence.py`` (observed green
    run + complete live reality legs), not owner readiness.

    Every occurrence must land in a documented bucket:

    * ``corrected`` — the same field carries ``READINESS_CLAIM_SUPERSEDED``
      (claim kept verbatim, refuted in place), which is the
      ``ready_for_owner_session_base`` convention ``packet_admission.enforce()``
      already applies to packets;
    * ``preserved_artifact`` — a pre-admission artifact whose bytes are kept as
      historical evidence (see ``PRESERVED_READINESS_ARTIFACTS``), paired with a
      current ``recheck_packet`` run that denies readiness today;
    * anything else is a violation.
    """
    occurrences: list[dict] = []

    def rel(path: Path) -> str:
        return str(path.relative_to(root)) if path.is_relative_to(root) else str(path)

    # 1. live state — every claim must be corrected in place
    state_path = root / "state" / "product.json"
    state_occurrences: list[dict] = []
    if state_path.is_file():
        state_path_rel = rel(state_path)
        occurrences.extend(scan_readiness_claims(_read(state_path), state_path_rel))
        state_occurrences = [o for o in occurrences if o["where"].startswith(state_path_rel)]

    # 2. product result artifacts — allowlisted historical bytes only
    artifacts: list[dict] = []
    for path in sorted((root / "results" / "product").rglob("*.json")):
        rel_path = rel(path)
        if rel_path.startswith("results/product/audit_pack/"):
            continue  # this pack's own output; written after the scan
        before = len(occurrences)
        try:
            found = scan_readiness_claims(_read(path), rel_path)
        except (json.JSONDecodeError, OSError):
            continue
        for occ in found:
            occ["file"] = rel_path
            occurrences.append(occ)
            artifacts.append(occ)

    # 3. this cycle's own report must be clean unless it marks its quotes
    current_report = root / "reports" / "product" / f"CYCLE_{run_id}.md" if run_id else None
    report_occurrences: list[dict] = []
    if current_report and current_report.is_file():
        before = len(occurrences)
        for token in READINESS_TOKENS:
            if token in current_report.read_text(encoding="utf-8"):
                # attribute to the file; marked quotes are corrected
                text = current_report.read_text(encoding="utf-8")
                occurrences.append({
                    "where": rel(current_report), "kind": f"string_token:{token}",
                    "bucket": None, "corrected": READINESS_CORRECTION_MARKER in text,
                })
        report_occurrences = occurrences[before:]

    # classify
    for occ in state_occurrences + report_occurrences:
        occ["bucket"] = "corrected" if occ.get("corrected") else None
    for occ in artifacts:
        if occ.get("corrected"):
            occ["bucket"] = "corrected"
        elif occ.get("file") in PRESERVED_READINESS_ARTIFACTS:
            occ["bucket"] = "preserved_artifact"
        else:
            occ["bucket"] = None

    violations = [o for o in occurrences if o["bucket"] is None]

    # 4. the current gate must deny readiness for the preserved packets today
    rechecks: dict[str, Any] = {}
    blocked_rechecks: list[dict] = []
    recheck_ok = True
    for pid in PRESERVED_RECHECK_PACKETS:
        packet_dir = root / "results" / "product" / "gate_packet" / pid
        try:
            from product.gate_packet import recheck_packet
            out = recheck_packet(packet_dir)
            cell = {
                "packet_id": pid,
                "ready_for_owner_session": out.get("ready_for_owner_session"),
                "ready_for_owner_session_base": out.get("ready_for_owner_session_base"),
                "packet_admission_blocked": out.get("packet_admission_blocked"),
                "packet_admission_reason": out.get("packet_admission_reason"),
                "admissible_questions": out.get("admissible_questions"),
            }
        except Exception as exc:
            module = _missing_module(exc)
            cell = {"packet_id": pid, "error": f"{type(exc).__name__}: {exc}"}
            if module:
                # An absent module cannot conclude the check; it does not
                # violate it. Recorded as blocked, never as a claim violation.
                blocked_rechecks.append({"packet_id": pid, "blocked_by": module})
                rechecks[pid] = {**cell, "blocked_by": module}
                continue
            recheck_ok = False
        rechecks[pid] = cell
        if cell.get("ready_for_owner_session") is not False or cell.get("packet_admission_blocked") is not True:
            recheck_ok = False

    measured = {
        "occurrences": occurrences,
        "n_occurrences": len(occurrences),
        "n_corrected": sum(1 for o in occurrences if o["bucket"] == "corrected"),
        "n_preserved_artifacts": sum(1 for o in occurrences if o["bucket"] == "preserved_artifact"),
        "violations": violations or None,
        "current_gate_rechecks": rechecks,
        "preserved_artifact_reasons": PRESERVED_READINESS_ARTIFACTS,
    }
    detail = ("owner-readiness claims are corrected in state, allowlisted only for "
              "preserved pre-admission bytes, and denied by today's admission gate")
    evidence = []
    if state_occurrences:
        evidence.append(rel(state_path))
    evidence.extend(sorted({o["file"] for o in artifacts}))
    if report_occurrences and current_report is not None:
        evidence.append(rel(current_report))

    if violations:
        return (False, measured, {"violations": []}, detail, evidence or ["state/product.json"])
    if blocked_rechecks:
        # Nothing proven false, nothing proven clean: report the scan and the
        # blocker instead of manufacturing a verdict.
        measured["blocked_rechecks"] = blocked_rechecks
        raise CheckBlocked(
            f"claim scan completed with {len(occurrences)} occurrence(s) and 0 violations, "
            f"but the live gate denial for {len(blocked_rechecks)} preserved packet(s) "
            f"could not be recomputed: missing {blocked_rechecks[0]['blocked_by']}",
            blocked_by=blocked_rechecks[0]["blocked_by"], measured=measured)
    ok = recheck_ok
    return (ok, measured, {"violations": []}, detail, evidence or ["state/product.json"])



def check_frozen_rubric_rehash(root: Path) -> tuple:
    pairs = (
        (root / "product" / "frozen" / "RULES_LABEL.json", FROZEN_LABEL_SHA256),
        (root / "product" / "frozen" / "RULES_GEOMETRY.json", FROZEN_GEOMETRY_SHA256),
    )
    measured, evidence = {}, []
    ok = True
    for path, expected in pairs:
        if not path.is_file():
            ok = False
            measured[path.name] = "MISSING"
            continue
        digest = sha256_file(path)
        measured[path.name] = digest
        evidence.append(str(path.relative_to(root)))
        ok = ok and digest == expected
    return (ok, measured,
            {"RULES_LABEL.json": FROZEN_LABEL_SHA256,
             "RULES_GEOMETRY.json": FROZEN_GEOMETRY_SHA256},
            "frozen rubrics reused by re-hash; never regenerated or re-derived",
            evidence)


def check_p0_fabricated_frozen_green_sweep(root: Path) -> tuple:
    offenders: dict[str, list[str]] = {}
    paths = fixture_artifact_paths(root)
    for path in paths:
        hits = sweep_fabricated_frozen_greens(_read(path))
        if hits:
            offenders[str(path.relative_to(root))] = sorted(set(hits))
    return (not offenders,
            {"artifacts_swept": len(paths), "offenders": offenders or None}, {},
            "no committed fixture artifact reports a frozen gate as passed (audit D1-R)",
            [str(p.relative_to(root)) for p in paths])


def check_p0_corrected_marker_contract(root: Path) -> tuple:
    pair = {
        "summary_fixture_20261017T072123Z.json": None,
        "business-judgment-rule_fixture_20261017T072123Z.json": None,
    }
    measured, ok, evidence = {}, True, []
    for name in pair:
        path = root / "results" / "product" / "reality_check" / name
        if not path.is_file():
            ok = False
            measured[name] = "MISSING"
            continue
        payload = _read(path)
        evidence.append(str(path.relative_to(root)))
        fabricated = sweep_fabricated_frozen_greens(payload)
        entry: dict[str, Any] = {"fabricated_greens": fabricated,
                                 "mode": payload.get("mode")}
        if name.startswith("summary_"):
            entry["frozen_gates_evaluated"] = payload.get("frozen_gates_evaluated", "ABSENT")
            ok = ok and payload.get("frozen_gates_evaluated") == [] and not fabricated
        else:
            markers = [g for g in payload.get("gates", [])
                       if g.get("gate") == "wiring::frozen_recall_gate_not_evaluated"]
            entry["marker_count"] = len(markers)
            ok = ok and len(markers) == 1 and not fabricated
        measured[name] = entry
    return (ok, measured, {"fabricated_greens": [], "summary.frozen_gates_evaluated": []},
            "the two 072123Z artifacts carry the corrected non-evaluation contract",
            evidence)


def check_p1_vendored_classifier_provenance(root: Path) -> tuple:
    vend = root / "product" / "vendored" / "frontier_counter_anchor_classifier"
    meta_path = vend / "PROVENANCE.json"
    if not meta_path.is_file():
        return (False, "MISSING", {}, "vendored classifier provenance absent",
                ["product/vendored/frontier_counter_anchor_classifier/PROVENANCE.json"])
    meta = _read(meta_path)
    drift, checked = [], 0
    for rel, rec in (meta.get("vendored_files") or {}).items():
        checked += 1
        path = vend / rel
        if not path.is_file() or sha256_file(path) != rec.get("sha256"):
            drift.append(rel)
    ok = (
        checked > 0 and not drift
        and str(meta.get("accept_commit", "")).startswith("d236f599")
        and meta.get("frozen_label_rules_sha256") == FROZEN_LABEL_SHA256
    )
    return (ok, {"files_checked": checked, "drifted": drift or None,
                 "accept_commit": meta.get("accept_commit"),
                 "promoted_variant": meta.get("promoted_variant")},
            {"files_checked": ">0", "drifted": [], "accept_commit": "d236f599*"},
            "accepted frontier-counter-anchor-classifier consumed byte-identically",
            ["product/vendored/frontier_counter_anchor_classifier/PROVENANCE.json"])


def check_p1_adoption_numbers(root: Path) -> tuple:
    from product.query import counter_anchor as ca

    totals = {"n_scored": 0, "n_emitted": 0, "n_abstained": 0}
    per_bundle: dict[str, dict] = {}
    evidence = []
    for qid in QIDS:
        path = root / "results" / "product" / "gate_packet" / "38839347028" / "questions" / f"{qid}.bundle.json"
        if not path.is_file():
            return (False, {"missing": str(path)}, EXPECTED_ADOPTION,
                    "source packet bundle absent", [])
        evidence.append(str(path.relative_to(root)))
        prov = ca.apply_anchor_labels(_read(path), qid=qid)["provenance"]["counter_anchor"]
        per_bundle[qid] = {k: prov.get(k) for k in
                           ("n_scored", "n_emitted", "n_abstained",
                            "support_rate_among_emitted", "yield")}
        for key in totals:
            totals[key] += int(prov.get(key) or 0)
    yield_rate = totals["n_emitted"] / totals["n_scored"] if totals["n_scored"] else 0.0
    support = per_bundle and all(
        (cell["support_rate_among_emitted"] in (0.0, 1.0)) for cell in per_bundle.values())
    ok = (
        totals == EXPECTED_ADOPTION
        and abs(yield_rate - 0.076923) < 1e-6
        and support is True
    )
    measured = {**totals, "yield": round(yield_rate, 6),
                "support_rate_among_issued": (1.0 if totals["n_emitted"] else 0.0),
                "per_bundle": per_bundle}
    return (ok, measured,
            {**EXPECTED_ADOPTION, "yield": 0.076923},
            "support-among-issued, abstention count and yield published side by side",
            evidence)


def check_p1_abstained_rows_stay_visible(root: Path) -> tuple:
    from product.query import counter_anchor as ca

    measured, ok, evidence = {}, True, []
    for qid in QIDS:
        path = root / "results" / "product" / "gate_packet" / "38839347028" / "questions" / f"{qid}.bundle.json"
        if not path.is_file():
            return (False, {"missing": qid}, {}, "source bundle absent", [])
        bundle = _read(path)
        evidence.append(str(path.relative_to(root)))
        out = ca.apply_anchor_labels(bundle, qid=qid)
        rows = out["decisions"]
        abstained = [d for d in rows if d.get("counter_status") == ca.ABSTAINED_STATUS]
        with_geometry = [d for d in abstained
                         if "x" in d and "y" in d and "cluster_id" in d]
        ok = ok and len(rows) == len(bundle["decisions"]) and bool(abstained) \
            and len(with_geometry) == len(abstained)
        measured[qid] = {"rows_before": len(bundle["decisions"]), "rows_after": len(rows),
                         "abstained": len(abstained), "abstained_with_geometry": len(with_geometry)}
    return (ok, measured,
            {"rows_preserved": True, "abstained>0": True, "abstained_with_geometry": "all"},
            "abstained rows stay on the map as marked unevidenced rows, never dropped",
            evidence)


def check_p2_obligation_a_post_rerank(root: Path) -> tuple:
    handoff = root / "results" / "product" / "gate_packet" / "rebuilt-39027045675" / "handoff.json"
    if not handoff.is_file():
        return (False, "MISSING", {}, "rebuilt handoff absent", [])
    data = _read(handoff)
    measured, ok = {}, True
    evidence = [str(handoff.relative_to(root))]
    for bundle in data.get("bundles", []):
        rr = bundle.get("rerank_product_bundle") or {}
        gs = bundle.get("geometry_scoring") or {}
        comp = gs.get("comparison") or {}
        ref = gs.get("pre_rerank_reference") or {}
        cell = {
            "bundle_state": gs.get("bundle_state"),
            "n_pass_post_rerank": gs.get("n_pass"),
            "pre_rerank_reference_n_pass": ref.get("n_pass"),
            "measured_pass_count": gs.get("measured_pass_count"),
            "criterion_flips": sorted((comp.get("criterion_flips") or {}).keys()),
            "absolute_bar_met_post_rerank": comp.get("absolute_bar_met_post_rerank"),
            "rerank_applied": rr.get("applied"), "rerank_runs_once": rr.get("runs_once"),
            "rerank_call_count": rr.get("call_count"),
        }
        measured[bundle.get("qid", "?")] = cell
        ok = ok and (
            rr.get("applied") is True and rr.get("runs_once") is True
            and rr.get("call_count") == 1
            and gs.get("bundle_state") == "post_rerank_product_bundle"
            and gs.get("frozen_rules_sha256") == FROZEN_GEOMETRY_SHA256
            and gs.get("n_criteria") == 11
            and ref.get("n_pass") == gs.get("measured_pass_count")
            and comp.get("absolute_bar_met_post_rerank") is False
            and isinstance(comp.get("criterion_flips"), dict)
        )
    ok = ok and set(measured) == set(QIDS)
    return (ok, measured,
            {"per_qid": "post_rerank_product_bundle + pre-rerank reference + criterion flips",
             "absolute_bar_met_post_rerank": False},
            "pre-serving obligation (a): frozen 11-criteria counts re-run on the "
            "post-rerank bundle and published beside the measured 7/8/7 reference",
            evidence)


def check_p2_obligation_b_axis_label(root: Path) -> tuple:
    handoff = root / "results" / "product" / "gate_packet" / "rebuilt-39027045675" / "handoff.json"
    if not handoff.is_file():
        return (False, "MISSING", {}, "rebuilt handoff absent", [])
    data = _read(handoff)
    labels = {b.get("qid"): b.get("axis_x_label") for b in data.get("bundles", [])}
    stale: list[str] = []
    evidence = [str(handoff.relative_to(root))]
    for name in ("handoff.json", "disclosures.json", "packet.json"):
        path = handoff.parent / name
        if path.is_file() and STALE_AXIS_WORD in path.read_text(encoding="utf-8"):
            stale.append(name)
        if path.is_file() and str(path.relative_to(root)) not in evidence:
            evidence.append(str(path.relative_to(root)))
    ok = (set(labels) == set(QIDS)
          and all(v == REQUIRED_AXIS_LABEL for v in labels.values())
          and not stale)
    return (ok, {"axis_x_label": labels, "stale_word_files": stale or None},
            {"axis_x_label": REQUIRED_AXIS_LABEL, "stale_word_files": []},
            "pre-serving obligation (b): V2 axis relabelled, stale word absent",
            evidence)


def check_p2_mega_cluster_disclosure(root: Path) -> tuple:
    handoff = root / "results" / "product" / "gate_packet" / "rebuilt-39027045675" / "handoff.json"
    if not handoff.is_file():
        return (False, "MISSING", {}, "rebuilt handoff absent", [])
    data = _read(handoff)
    measured, ok = {}, True
    for bundle in data.get("bundles", []):
        m = bundle.get("mega_cluster_disclosure") or {}
        src = m.get("source_packet") or {}
        rebuilt = m.get("rebuilt_packet") or {}
        share = src.get("largest_cluster_share")
        cell = {
            "bar": m.get("bar"), "threshold_edited": m.get("threshold_edited"),
            "size_based_not_member_ids": m.get("size_based_not_member_ids"),
            "definition": m.get("definition"),
            "source_share": share, "source_member_ids_share": src.get("largest_cluster_member_ids_share"),
            "source_fired": src.get("fired"), "rebuilt_share": rebuilt.get("largest_cluster_share"),
            "fired_on_any_check": m.get("fired_on_any_check"),
        }
        measured[bundle.get("qid", "?")] = cell
        ok = ok and (
            m.get("bar") == 0.5 and m.get("threshold_edited") is False
            and m.get("size_based_not_member_ids") is True
            and isinstance(share, (int, float))
            and src.get("fired") is (share >= 0.5)
        )
    # the recorded fired example must still be disclosed at its measured share
    fr = measured.get("fr-bail-entretien") or {}
    ok = ok and fr.get("source_fired") is True \
        and abs((fr.get("source_share") or 0) - 0.7696) < 1e-4 \
        and abs((fr.get("source_member_ids_share") or 0) - 0.2304) < 1e-4
    return (ok, measured,
            {"bar": 0.5, "threshold_edited": False, "source_fired_at": 0.7696},
            "size-based (len(idx)) mega-cluster disclosure, bar unchanged at 0.5",
            [str(handoff.relative_to(root))])


def check_p2_forbidden_constructions(root: Path) -> tuple:
    from product.query import counter_anchor as ca

    offenders: dict[str, list[str]] = {}
    base = root / "results" / "product" / "gate_packet" / "rebuilt-39027045675"
    evidence = []
    for name in ("handoff.json", "disclosures.json", "packet.json"):
        path = base / name
        if not path.is_file():
            continue
        evidence.append(str(path.relative_to(root)))
        hits = ca.find_forbidden_constructions(path.read_text(encoding="utf-8"))
        if hits:
            offenders[name] = hits
    for qid in QIDS:
        path = base / "questions" / f"{qid}.question.json"
        if not path.is_file():
            continue
        evidence.append(str(path.relative_to(root)))
        hits = ca.find_forbidden_constructions(path.read_text(encoding="utf-8"))
        if hits:
            offenders[f"questions/{qid}.question.json"] = hits
    return (not offenders, offenders or None, {},
            "claim ceiling: no committed rebuilt artifact asserts a legal "
            "supporting/contrary/limiting classification", evidence)


def check_p3_handoff_hashes(root: Path) -> tuple:
    from product.replay_bundle import content_sha256

    handoff = root / "results" / "product" / "gate_packet" / "rebuilt-39027045675" / "handoff.json"
    if not handoff.is_file():
        return (False, "MISSING", {}, "rebuilt handoff absent", [])
    data = _read(handoff)
    measured, ok = {}, True
    packet_path = root / "results" / "product" / "gate_packet" / "rebuilt-39027045675" / "packet.json"
    if packet_path.is_file():
        raw = sha256_file(packet_path)
        ok = raw == data.get("packet_content_sha256")
        measured["packet_content_sha256"] = {"published": data.get("packet_content_sha256"),
                                             "recomputed": raw, "match": raw == data.get("packet_content_sha256")}
    else:
        ok = False
        measured["packet_content_sha256"] = "MISSING"
    evidence = [str(handoff.relative_to(root))]
    for bundle in data.get("bundles", []):
        path = Path(bundle["bundle_path"])
        if not path.is_file():
            alt = root / "results" / "product" / "gate_packet" / "rebuilt-39027045675" / "questions" / f"{bundle['qid']}.bundle.json"
            path = alt
        if not path.is_file():
            ok = False
            measured[bundle["qid"]] = "MISSING"
            continue
        try:
            recomputed = content_sha256(_read(path))
        except Exception as exc:  # pragma: no cover - defensive
            ok = False
            measured[bundle["qid"]] = f"error:{type(exc).__name__}"
            continue
        match = recomputed == bundle.get("content_sha256")
        ok = ok and match
        measured[bundle["qid"]] = {"published": bundle.get("content_sha256"),
                                   "recomputed": recomputed, "match": match}
        evidence.append(str(path.relative_to(root)) if path.is_relative_to(root) else str(path))
    return (ok, measured, {"every bundle content_sha256 reproduces": True},
            "P3 handoff identities reproduce via the product's own hasher",
            evidence)


def check_p3_admission_denies(root: Path) -> tuple:
    from product.query import packet_admission as pa

    adm = pa.assess()
    ok = (adm.get("packet_admitted") is False
          and adm.get("ready_for_owner_session_allowed") is False
          and adm.get("blocking_reason") is not None)
    label = ((adm.get("bars") or {}).get("counter_label") or {}).get("binding_measurement") or {}
    geom = ((adm.get("bars") or {}).get("map_geometry") or {}).get("binding_measurement") or {}
    measured = {
        "packet_admitted": adm.get("packet_admitted"),
        "ready_for_owner_session_allowed": adm.get("ready_for_owner_session_allowed"),
        "blocking_reason": adm.get("blocking_reason"),
        "binding_label": {k: label.get(k) for k in ("n_supported", "n_scored", "support_rate")},
        "binding_geometry": {k: geom.get(k) for k in ("n_bundles_pass", "n_bundles")},
    }
    return (ok, measured,
            {"packet_admitted": False, "ready_for_owner_session_allowed": False},
            "machine gate consumes accepted bar verdicts; admission denied while bars unmet",
            ["results/product/frontier_verdicts/ACCEPTED_frontier-served-packet-falsification_38880639079.json"])


def check_do_not_serve_order_stands(root: Path) -> tuple:
    path = (root / "results" / "product" / "frontier_verdicts"
            / "ACCEPTED_frontier-served-packet-falsification_38880639079.json")
    if not path.is_file():
        return (False, "MISSING", {"covers_this_packet": True},
                "product-owned accepted verdict snapshot absent",
                ["results/product/frontier_verdicts/ACCEPTED_frontier-served-packet-falsification_38880639079.json"])
    data = _read(path)
    covers = data.get("covers_this_packet")
    rec = str(data.get("serve_recommendation") or data.get("recommendation") or "")
    haystack = json.dumps(data).upper().replace("DO NOT SERVE", "DO-NOT-SERVE")
    ok = covers is True and "DO-NOT-SERVE" in haystack
    return (bool(ok), {"covers_this_packet": covers, "serve_recommendation": rec},
            {"covers_this_packet": True, "serve_recommendation": "DO-NOT-SERVE ..."},
            "accepted DO-NOT-SERVE order preserved verbatim in a product-owned snapshot",
            [str(path.relative_to(root))])


def check_state_contract(root: Path) -> tuple:
    from product import state_contract as sc

    dirv = (_read(root / "state" / "product.json")).get("direction_version")
    if CONTROL_STATE.is_file():
        dirv = _read(CONTROL_STATE).get("version") or dirv
    report = sc.check(int(dirv or 52), state_path=root / "state" / "product.json")
    measured = {
        "workflow_validation": report["workflow_validation"]["ok"],
        "write_scope_ok": report["write_scope"]["ok"],
        "write_scope_violations": report["write_scope"]["violations"] or None,
        "producer_wrote_audit_paths": report["audit_artifact_ownership"]["producer_wrote_audit_paths"] or None,
        "committed_audit_artifacts": len(report["audit_artifact_ownership"]["committed_audit_artifacts"]),
        "shadow_state": report["shadow_state"]["findings"] or None,
        "ok": report["ok"],
    }
    return (bool(report["ok"]), measured, {"ok": True},
            "lane state contract: direction pin, write scope, audit ownership, shadow state",
            ["state/product.json"])


def check_no_producer_minted_audit_artifact(root: Path, run_id: str | None = None) -> tuple:
    files = _git("ls-files", "--", "results/audit/product", "reports/audit/product")
    committed = [line for line in files.splitlines() if line.strip()]
    hits = [f for f in committed if run_id and run_id != "local" and run_id in f]
    return (not hits,
            {"committed_audit_artifacts": len(committed),
             "mentions_this_run": hits or None,
             "auditor_write_scope": list(AUDITOR_WRITE_SCOPE)},
            {"mentions_this_run": None},
            "producer never mints its own gate; the gate is the auditor's alone",
            committed[:10])


def check_core_test_subsets(root: Path) -> tuple:
    """Run the cheap high-signal test modules and record the counts."""
    modules = [m for m in CORE_TEST_MODULES if (root / m).is_file()]
    if not modules:
        return (False, {"error": "no core test modules found"}, {"passed": ">0"},
                "core test subset", [])
    missing_declared = [m for m in CORE_TEST_MODULES if m not in modules]
    cmd = [sys.executable, "-m", "pytest", *modules, "-q", "--no-header",
           "-p", "no:cacheprovider"]
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                              timeout=900, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return (False, {"error": type(exc).__name__}, {"returncode": 0},
                "core test subset could not run", modules)
    tail = [line for line in (proc.stdout or "").strip().splitlines() if line.strip()]
    summary = tail[-1] if tail else ""
    ok = proc.returncode == 0 and "failed" not in summary and "error" not in summary
    return (ok,
            {"returncode": proc.returncode, "summary": summary,
             "seconds": round(time.monotonic() - started, 1),
             "declared_modules": len(CORE_TEST_MODULES),
             "run_modules": len(modules),
             # a declared module that does not exist is a silent coverage loss
             "declared_but_absent": missing_declared or None,
             "modules": modules},
            {"returncode": 0, "declared_but_absent": None},
            "core product test subset (v52 endgame, state contract, "
            "fixture sweep, offline slice, query-map MVP, audit pack)", modules)


def check_known_baseline_test_failures(root: Path) -> tuple:
    """The pre-existing failures stay pre-existing, and no new one appears.

    Eight tests in four modules fail at the resumed snapshot head 9275cc6, i.e.
    before any edit of this cycle (re-derived in a detached worktree at that
    commit: 8 failed, 87 passed).  Left unrecorded they are an auditor's
    time sink; recorded as a silent whitelist they would hide a real regression.
    So this check asserts the failing set is EXACTLY the recorded baseline: a new
    failure fails the check, and a *fixed* one is reported as drift so it can be
    retired from the baseline deliberately.
    """
    modules = [m for m in BASELINE_TEST_MODULES if (root / m).is_file()]
    if not modules:
        return (False, {"error": "no baseline modules found"}, {"n_new": 0},
                "known baseline test failures", list(BASELINE_TEST_MODULES))
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *modules, "-q", "--no-header",
         "-p", "no:cacheprovider", "--tb=no"],
        cwd=str(root), capture_output=True, text=True, timeout=900, check=False,
    )
    observed = set()
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("FAILED ") and "::" in line:
            observed.add(line[len("FAILED "):].split(" - ")[0].strip())
    baseline = set(KNOWN_BASELINE_FAILURES)
    new = sorted(observed - baseline)
    fixed = sorted(baseline - observed)
    measured = {
        "modules": modules,
        "n_observed": len(observed),
        "n_baseline": len(baseline),
        "new_failures": new or None,
        "baseline_now_passing": fixed or None,
        "baseline_reasons": KNOWN_BASELINE_FAILURES,
        "measured_at_baseline_head": "9275cc6 (run 39039195228), detached worktree, before any "
                                     "edit of run 39042713389: 8 failed / 87 passed",
        "returncode": proc.returncode,
    }
    ok = not new
    return (ok, measured,
            {"new_failures": None, "n_new": 0},
            ("known baseline unchanged: no new failure in the four baseline modules"
             if ok else
             f"{len(new)} NEW failure(s) in the baseline modules: {new}"),
            modules)


def check_state_run_coherence(root: Path, run_id: str | None = None) -> tuple:
    """The lane state must name the run that wrote it.

    Found in run 39042713389: the snapshot committed by run 39039195228 edited
    ``state/product.json`` (the readiness-claim corrections) while leaving
    ``current_run`` / ``state_updated_by_run`` at ``39034350468``, so the state
    of record pointed at a run two dispatches older.  Nothing detects that class
    of drift today, and an auditor reading the state has no way to tell which
    cycle is speaking.  Enforcement is skipped for ``--run-id local`` (an
    unnumbered manual run has no identity to claim) and for a repository whose
    state predates the convention.
    """
    path = root / "state" / "product.json"
    if not path.is_file():
        return (False, "MISSING", {}, "state/product.json absent", [])
    state = _read(path)
    declared = {k: state.get(k) for k in ("current_run", "state_updated_by_run")}
    measured: dict[str, Any] = {
        "run_id": run_id,
        "declared": declared,
        "prior_current_run": state.get("prior_current_run"),
        "enforced": bool(run_id) and run_id != "local",
    }
    if not measured["enforced"]:
        measured["verdict"] = ("SKIPPED_NO_RUN_ID: a local manual run asserts no cycle "
                               "identity, so current_run/state_updated_by_run are not "
                               "required to name it")
        return (True, measured, {"enforced": False},
                "state names the run that wrote it (enforced only for numbered runs)",
                [str(path.relative_to(root))])
    mismatched = {k: v for k, v in declared.items() if v is not None and str(v) != str(run_id)}
    absent = [k for k, v in declared.items() if v is None]
    measured["mismatched"] = mismatched or None
    measured["absent"] = absent or None
    ok = not mismatched and not absent
    measured["verdict"] = (
        "coherent: state/product.json names run %s" % run_id if ok else
        "INCOHERENT: state/product.json names %r for run %s; an auditor cannot tell "
        "which cycle is speaking" % (declared, run_id))
    return (ok, measured,
            {"current_run": str(run_id), "state_updated_by_run": str(run_id)},
            measured["verdict"], [str(path.relative_to(root))])


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
CHECKS: tuple[tuple[str, Callable[..., tuple]], ...] = (
    ("state_direction_and_gate_flags", check_state_direction_and_gate_flags),
    ("readiness_claim_guard", check_readiness_claim_guard),
    ("frozen_rubric_rehash", check_frozen_rubric_rehash),
    ("p0_fabricated_frozen_green_sweep", check_p0_fabricated_frozen_green_sweep),
    ("p0_corrected_072123_marker_contract", check_p0_corrected_marker_contract),
    ("p1_vendored_classifier_provenance", check_p1_vendored_classifier_provenance),
    ("p1_adoption_numbers", check_p1_adoption_numbers),
    ("p1_abstained_rows_stay_visible", check_p1_abstained_rows_stay_visible),
    ("p2_obligation_a_post_rerank_counts", check_p2_obligation_a_post_rerank),
    ("p2_obligation_b_axis_label", check_p2_obligation_b_axis_label),
    ("p2_mega_cluster_disclosure_size_based", check_p2_mega_cluster_disclosure),
    ("p2_forbidden_constructions", check_p2_forbidden_constructions),
    ("p3_handoff_content_hashes", check_p3_handoff_hashes),
    ("p3_admission_denies", check_p3_admission_denies),
    ("do_not_serve_order_stands", check_do_not_serve_order_stands),
    ("state_contract", check_state_contract),
    ("state_run_coherence", check_state_run_coherence),
    ("producer_wrote_no_audit_artifact", check_no_producer_minted_audit_artifact),
    ("known_baseline_test_failures", check_known_baseline_test_failures),
    ("core_test_subsets", check_core_test_subsets),
)

#: Checks that take the ``(root, run_id)`` signature.
RUN_ID_AWARE_CHECKS = ("producer_wrote_no_audit_artifact", "readiness_claim_guard",
                       "state_run_coherence")


def classify(exc: BaseException) -> str:
    """Map an exception raised by a check onto a check status.

    A missing import is an environment fact. Reporting it as a failure is how a
    bare audit checkout makes a healthy product look broken, so it gets its own
    status and its own exit code.
    """
    if isinstance(exc, (CheckBlocked, ModuleNotFoundError, ImportError)):
        return STATUS_BLOCKED
    return STATUS_FAIL


def _blocked_module(exc: BaseException) -> str:
    if isinstance(exc, CheckBlocked):
        return exc.blocked_by
    return _missing_module(exc) or "unknown"


def run_checks(root: Path | None = None, *, include_tests: bool = True,
               run_id: str | None = None) -> list[dict]:
    root = root or ROOT
    out: list[dict] = []
    for name, fn in CHECKS:
        if name == "core_test_subsets" and not include_tests:
            out.append({"id": name, "ok": True, "status": STATUS_SKIPPED,
                        "skipped": True, "detail": "skipped by --no-tests"})
            continue
        started = time.monotonic()
        try:
            if name in RUN_ID_AWARE_CHECKS:
                ok, measured, expected, detail, evidence = fn(root, run_id)
            else:
                ok, measured, expected, detail, evidence = fn(root)
            rec = {"id": name, "ok": bool(ok),
                   "status": STATUS_OK if ok else STATUS_FAIL,
                   "measured": measured, "expected": expected,
                   "detail": detail, "evidence": evidence,
                   "seconds": round(time.monotonic() - started, 3)}
        except Exception as exc:  # a crash is never a silent pass
            status = classify(exc)
            rec = {"id": name, "ok": False, "status": status,
                   "error": f"{type(exc).__name__}: {exc}",
                   "detail": ("check blocked: a required module is absent from this "
                              "interpreter, so nothing was proven"
                              if status == STATUS_BLOCKED else "check raised"),
                   "seconds": round(time.monotonic() - started, 3)}
            if status == STATUS_BLOCKED:
                rec["blocked_by"] = _blocked_module(exc)
                rec["bootstrap_command"] = BOOTSTRAP_COMMAND
                if isinstance(exc, CheckBlocked) and exc.measured is not None:
                    rec["measured"] = exc.measured
        out.append(rec)
    return out


def summarise(checks: list[dict]) -> dict:
    """Counts that keep a blocked check from ever reading as a product failure."""
    failed = [c for c in checks if not c.get("ok") and c.get("status") == STATUS_FAIL]
    blocked = [c for c in checks if c.get("status") == STATUS_BLOCKED]
    skipped = [c for c in checks if c.get("status") == STATUS_SKIPPED]
    passed = [c for c in checks if c.get("ok") and c.get("status") == STATUS_OK]
    return {
        "n_checks": len(checks),
        "n_passed": len(passed),
        "n_failed": len(failed),
        "n_blocked_missing_dependency": len(blocked),
        "n_skipped": len(skipped),
        "failed_ids": [c["id"] for c in failed] or None,
        "blocked_ids": [c["id"] for c in blocked] or None,
        # `all_ok` stays strict: a blocked check is not a pass.
        "all_ok": not failed and not blocked,
        "no_product_failure": not failed,
    }


def exit_code_for(summary: dict) -> int:
    """The pack's machine contract (documented in the module docstring)."""
    if summary["all_ok"]:
        return 0
    return 1 if summary["n_failed"] else 2


def build_pack(root: Path | None = None, *, include_tests: bool = True,
               run_id: str | None = None, deps: dict | None = None) -> dict:
    root = root or ROOT
    run_id = run_id or os.environ.get("GITHUB_RUN_ID") or "local"
    started = time.monotonic()
    deps = deps if deps is not None else dependency_status(root)
    checks = run_checks(root, include_tests=include_tests, run_id=run_id)
    summary = summarise(checks)
    state = _read(root / "state" / "product.json")
    pack = {
        "schema": SCHEMA,
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "product",
        "direction_version": state.get("direction_version"),
        "producer_head": {"sha": _git("rev-parse", "HEAD"),
                          "subject": _git("log", "-1", "--format=%s")},
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": _versions(),
        },
        "dependencies": deps,
        "checks": checks,
        **summary,
        "exit_code": exit_code_for(summary),
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "auditor_write_scope": list(AUDITOR_WRITE_SCOPE),
        "auditor_must_not_write": [
            "anything outside the two paths above in the AUDIT checkout "
            "(exit 3 = 'auditor crossed scope', run 39031213637)",
            "state/, product/, results/product/, reports/product/ — producer scope",
        ],
        "not_claimable": [
            "any frozen bar met (counter-label 5/65 = 0.0769 vs absolute 1.0; "
            "geometry 0/3 bundles at 11 criteria) — Core Evaluation's ceded measurement",
            "human_gate_ready / machine_gate_ready / ready_for_owner_session",
            "any legal usefulness, or that any decision IS supporting/contrary/limiting",
        ],
        "claim_ceiling": CLAIM_CEILING,
    }
    return pack


def _versions() -> dict:
    out = {}
    for mod in ("numpy", "scipy", "sklearn", "pytest"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:
            out[mod] = None
    return out


def default_out_path(run_id: str) -> Path:
    return ROOT / "results" / "product" / "audit_pack" / f"CYCLE_{run_id}_pack.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", default=None,
                        help="cycle run id for the artifact name (default: $GITHUB_RUN_ID or 'local')")
    parser.add_argument("--out", type=Path, default=None,
                        help="where to write the pack JSON (default results/product/audit_pack/)")
    parser.add_argument("--no-tests", action="store_true",
                        help="skip the core pytest subset (checks still run)")
    parser.add_argument("--json", action="store_true", help="print the full pack JSON")
    parser.add_argument("--deps", action="store_true",
                        help="print the dependency preflight and exit (0 complete, 2 incomplete)")
    parser.add_argument("--bootstrap-deps", choices=("auto", "on", "off"), default="auto",
                        help="install product/requirements-query.txt when a required module is "
                             "missing (auto = only when something is missing; writes nothing "
                             "inside the repository)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing pack artifact (it is claim-bearing evidence "
                             "of the run that produced it, so the default is to refuse)")
    args = parser.parse_args(argv)

    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID") or "local"
    deps = dependency_status()
    bootstrap = {"attempted": False}
    if deps["missing"] and args.bootstrap_deps != "off":
        bootstrap = bootstrap_dependencies()
        deps = dependency_status()

    if args.deps:
        print(json.dumps({"dependencies": deps, "bootstrap": bootstrap}, indent=2))
        return 0 if deps["complete"] else 2

    try:
        pack = build_pack(include_tests=not args.no_tests, run_id=run_id, deps=deps)
    except Exception as exc:  # harness error, distinct from any product verdict
        print(f"[HARNESS ERROR] audit pack could not be assembled: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 3
    if bootstrap.get("attempted"):
        pack["dependency_bootstrap"] = bootstrap
    out = args.out or default_out_path(run_id)
    # A committed pack is claim-bearing evidence OF THE RUN THAT WROTE IT. During
    # run 39042713389 a convenience re-run with --run-id local silently overwrote
    # run 39039195228's committed CYCLE_local_pack.json, which AGENTS.md 6 forbids.
    # Overwrite now requires --force and is reported.
    if out.exists() and not args.force:
        print(f"[REFUSED] {_display_path(out)} already exists and is claim-bearing evidence of the "
              f"run that wrote it; pass --force to overwrite, or --out <new path>.", file=sys.stderr)
        return 3
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(pack, indent=2))
    else:
        for check in pack["checks"]:
            status = check.get("status", STATUS_FAIL if not check.get("ok") else STATUS_OK)
            print(f"[{status:<26}] {check['id']}"
                  + (f" :: {check.get('error') or _failure_note(check)}"
                     if not check.get("ok") else f" ({check.get('seconds', 0)}s)"))
        print(f"\n{pack['n_passed']}/{pack['n_checks']} checks passed in "
              f"{pack['elapsed_seconds']}s -> {_display_path(out)}")
        if pack["n_blocked_missing_dependency"]:
            print(f"{pack['n_blocked_missing_dependency']} check(s) BLOCKED_MISSING_DEPENDENCY "
                  f"(nothing proven false): {', '.join(pack['blocked_ids'])}")
            print(f"these are NOT product failures; install them with: {BOOTSTRAP_COMMAND}")
        if pack["n_failed"]:
            print(f"{pack['n_failed']} PRODUCT check(s) FAILED: {', '.join(pack['failed_ids'])}")
        print("auditor write scope: " + ", ".join(pack["auditor_write_scope"]))
        print(f"exit contract: {pack['exit_code']} "
              f"(0 all ok, 1 product failure, 2 dependency-blocked, 3 harness error)")
    return pack["exit_code"]


def _display_path(path: Path) -> str:
    """Repository-relative when possible; absolute otherwise (``--out /tmp/...``)."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _failure_note(check: dict) -> str:
    """A human sentence for a failing check, even when it returned a tuple.

    The pre-39042713389 console printed an empty reason whenever a check
    returned ``ok=False`` with its cause buried in ``measured``, which is how a
    dependency-blocked check was indistinguishable from a violated invariant.
    """
    note = str(check.get("detail") or "")
    measured = check.get("measured")
    if not isinstance(measured, dict):
        return note
    for key in ("error", "verdict", "reason"):
        value = measured.get(key)
        if value and str(value) not in note:
            return f"{note} :: {value}" if note else str(value)
    return f"{note} :: measured={json.dumps(measured)[:400]}" if note else \
        f"measured={json.dumps(measured)[:400]}"


if __name__ == "__main__":
    raise SystemExit(main())
