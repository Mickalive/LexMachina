"""Product-owned reproduction of the core-lane orchestration contract.

Why this module exists
----------------------
The v50 lane was interrupted twice by the *same* defect and the repair never
held:

* run 38548957828 — ``Validate active MVP producer state`` died because
  ``state/product.json`` still carried ``direction_version`` 48 while the run
  was dispatched with 49.
* run 38648548635 — the same step died again: the canonical file was still at
  ``direction_version`` 50 while the run was dispatched with 51, because the
  producer wrote a *shadow* copy at ``product/state/product.json`` (which is in
  lane write scope, so the shell scope check never saw it) instead of the
  workflow-validated ``state/product.json``.

Shell ``case`` globs cannot express "this file is inside the scope prefix but is
not the file the workflow reads". This module is the product's own executable
copy of the contract, so a cycle can fail its own test in seconds instead of
burning a 45-minute workflow quantum to learn the same thing.

What is reproduced (no gate logic is invented here)
---------------------------------------------------
1. ``Validate active MVP producer state`` — ``.github/workflows/core-lane.yml``
   runs ``jq -e '(.direction_version // -1) == $dirv and
   (.cycle_status // "INITIALIZED") != "INITIALIZED"' state/product.json`` and
   exits 68 (missing file) or 69 (assertion false).
2. ``Enforce lane write scope`` — the same workflow rejects any pending path
   outside ``product/``, ``tests/product/``, ``results/product/``,
   ``reports/product/``, ``state/product.json`` and ``data/product/``.
3. The audit-artifact contract: ``results/audit/<lane>/`` and
   ``reports/audit/<lane>/`` belong to the *independent auditor* only. A
   producer run that writes a ``CYCLE_<run>_GATE.json`` is self-minting an
   audit verdict, which is a forbidden fabrication even though the path never
   reaches the gate reader.

Usage
-----
    python product/state_contract.py --check --direction-version 51
    python product/state_contract.py --check --direction-version 51 --scope
    python product/state_contract.py --check --direction-version 51 --git-status
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
LANE = "product"

#: The file the workflow validates. Never write anywhere else.
CANONICAL_STATE = REPO_ROOT / "state" / f"{LANE}.json"
#: Factory direction mounted by the workflow (for default --direction-version).
FACTORY_STATE = REPO_ROOT / "state" / "factory_direction.json"
#: The workflow mounts the control plane from `main` here; the in-repo copy is
#: known to lag (observed v34 while the mounted control plane was v51 on
#: 2026-10-14) and is control-plane scope, so the mount is preferred.
MOUNTED_FACTORY_STATE = Path("/tmp/lex_control/state/factory_direction.json")

#: Path prefixes the workflow's ``Enforce lane write scope`` step accepts.
SCOPE_PATTERNS: tuple[str, ...] = (
    f"{LANE}/",
    f"tests/{LANE}/",
    f"results/{LANE}/",
    f"reports/{LANE}/",
    f"state/{LANE}.json",
    f"data/{LANE}/",
)

#: Paths inside the write scope that are nonetheless owned by another actor.
AUDIT_PREFIXES: tuple[str, ...] = (f"results/audit/{LANE}/", f"reports/audit/{LANE}/")

#: Shadow state files: lane-scope-legal, contract-violating copies of the
#: workflow-validated canonical state.
SHADOW_STATE_RELPATHS: tuple[str, ...] = (f"{LANE}/state/{LANE}.json",)


class StateContractError(RuntimeError):
    """Raised when the producer state cannot satisfy the workflow contract."""

    def __init__(self, message: str, exit_code: int = 69) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def load_state(path: Path = CANONICAL_STATE) -> dict:
    """Load the canonical state, reproducing the workflow's exit-68 branch."""
    if not path.is_file() or path.stat().st_size == 0:
        raise StateContractError(f"Missing {path}", exit_code=68)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise StateContractError(f"{path} is not valid JSON: {exc}", exit_code=69) from exc


def workflow_validation(
    direction_version: int,
    state_path: Path = CANONICAL_STATE,
) -> tuple[bool, str]:
    """Exact Python equivalent of ``Validate active MVP producer state``.

    Returns ``(ok, message)``. ``ok=False`` means the workflow would exit 69.
    """
    try:
        state = load_state(state_path)
    except StateContractError as exc:
        return False, str(exc)

    actual_dirv = state.get("direction_version", -1)
    if not isinstance(actual_dirv, int) or isinstance(actual_dirv, bool):
        # jq: (.direction_version // -1) == $dirv is false for any non-number.
        return False, (
            f"{state_path}: direction_version must be the integer {direction_version}; "
            f"found {actual_dirv!r}"
        )
    if actual_dirv != direction_version:
        return False, (
            f"{state_path}: direction_version {actual_dirv} != run input {direction_version} "
            "(workflow exits 69). Write the canonical state file, not a copy."
        )
    status = state.get("cycle_status", "INITIALIZED")
    if status == "INITIALIZED":
        return False, f"{state_path}: cycle_status is still INITIALIZED (workflow exits 69)"
    return True, (
        f"{state_path}: direction_version={actual_dirv}, cycle_status={status!r} -> workflow step passes"
    )


def default_direction_version() -> int | None:
    """Direction version of the mounted factory control plane, if readable.

    The workflow passes ``inputs.direction_version`` explicitly; this is only a
    convenience default. The mounted control plane wins over the in-repo copy,
    because ``state/factory_direction.json`` inside a lane branch can lag the
    direction the run was actually dispatched with (observed v34 vs v51 on
    2026-10-14, run 38649613677).
    """
    for path in (MOUNTED_FACTORY_STATE, FACTORY_STATE):
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get("version")
        except json.JSONDecodeError:
            continue
        if isinstance(value, int):
            return value
    return None


def in_scope(path: str) -> bool:
    """Reproduce the workflow's ``case "$p" in ...`` lane-scope match."""
    p = path.strip()
    if not p:
        return True
    return any(p == pattern.rstrip("*") or p.startswith(pattern) for pattern in SCOPE_PATTERNS)


def scope_violations(paths: Iterable[str]) -> list[str]:
    """Pending paths the workflow's ``Enforce lane write scope`` would reject."""
    bad: list[str] = []
    for raw in paths:
        p = raw.strip()
        if not p:
            continue
        if not in_scope(p):
            bad.append(p)
    return bad


def git_status_paths(cwd: Path = REPO_ROOT) -> list[str]:
    """Parse ``git status --porcelain -uall`` exactly as the workflow does."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - defensive
        return []
    paths: list[str] = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        payload = line[3:]
        # Porcelain v1 "R  old -> new" rename form; the shell check would only
        # match the literal string, so mirror it rather than "fixing" it here.
        paths.append(payload)
    return paths


def audit_artifact_violations(paths: Iterable[str]) -> list[str]:
    """Producer writes into the independent auditor's artifact directories."""
    return [p.strip() for p in paths if p.strip().startswith(AUDIT_PREFIXES)]


def shadow_state_findings(repo_root: Path = REPO_ROOT) -> list[dict]:
    """Shadow copies of the canonical state, and whether they diverge.

    A shadow copy is a *silent* contract violation: ``product/state/product.json``
    satisfies the shell lane-scope check (it starts with ``product/``) while the
    workflow keeps reading and failing on ``state/product.json``.
    """
    findings: list[dict] = []
    for rel in SHADOW_STATE_RELPATHS:
        path = repo_root / rel
        if not path.is_file():
            continue
        canonical_rel = CANONICAL_STATE.relative_to(REPO_ROOT) if CANONICAL_STATE.is_relative_to(REPO_ROOT) else CANONICAL_STATE
        entry: dict = {
            "path": rel,
            "canonical_path": str(canonical_rel),
            "exists": True,
            "problem": "shadow copy of the workflow-validated state file",
        }
        try:
            shadow = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            entry["diverges"] = True
            entry["reason"] = "shadow state is not valid JSON"
            findings.append(entry)
            continue
        canonical_path = repo_root / rel.replace(f"{LANE}/state/", "state/")
        if not canonical_path.is_file():
            entry["diverges"] = True
            entry["reason"] = "canonical state file does not exist"
        else:
            canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
            entry["shadow_direction_version"] = shadow.get("direction_version")
            entry["canonical_direction_version"] = canonical.get("direction_version")
            entry["shadow_cycle_status"] = shadow.get("cycle_status")
            entry["canonical_cycle_status"] = canonical.get("cycle_status")
            entry["diverges"] = shadow != canonical
            entry["reason"] = "shadow state differs from the canonical state file"
        findings.append(entry)
    return findings


def check(
    direction_version: int,
    state_path: Path = CANONICAL_STATE,
    paths: Sequence[str] | None = None,
) -> dict:
    """Full contract report: workflow assertion, write scope, audit ownership."""
    ok, message = workflow_validation(direction_version, state_path)
    pending = list(paths) if paths is not None else git_status_paths()
    scope_bad = scope_violations(pending)
    audit_bad = audit_artifact_violations(pending)
    shadow = shadow_state_findings()
    committed_audit = _committed_audit_artifacts()
    return {
        "lane": LANE,
        "direction_version": direction_version,
        "canonical_state_path": str(state_path.relative_to(REPO_ROOT))
        if state_path.is_relative_to(REPO_ROOT)
        else str(state_path),
        "workflow_validation": {"ok": ok, "message": message, "workflow_exit": 0 if ok else 69},
        "write_scope": {
            "checked_paths": len(pending),
            "ok": not scope_bad,
            "violations": scope_bad,
            "workflow_exit": 0 if not scope_bad else 3,
        },
        "audit_artifact_ownership": {
            "ok": not audit_bad,
            "producer_wrote_audit_paths": audit_bad,
            "committed_audit_artifacts": committed_audit,
            "workflow_exit": 0 if not audit_bad else 3,
        },
        "shadow_state": {"ok": not shadow, "findings": shadow},
        "ok": ok and not scope_bad and not audit_bad and not shadow,
    }


def _committed_audit_artifacts(repo_root: Path = REPO_ROOT) -> list[str]:
    """Audit artifacts already committed to the working tree (self-minted ones).

    These do not appear in ``git status`` (already committed), so the workflow
    scope check stays silent about them; they are reported so a passing gate can
    never promote a producer-authored ``CYCLE_<run>_GATE.json`` onto the
    accepted branch.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "--", f"results/audit/{LANE}", f"reports/audit/{LANE}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - defensive
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--direction-version",
        type=int,
        default=None,
        help="factory direction version this cycle was dispatched with "
        "(defaults to the mounted state/factory_direction.json version)",
    )
    parser.add_argument("--state", type=Path, default=CANONICAL_STATE)
    parser.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="explicit pending paths to check instead of reading git status",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the full contract check (default action; accepted for readability)",
    )
    parser.add_argument("--json", action="store_true", help="emit the machine-readable report")
    args = parser.parse_args(argv)

    dirv = args.direction_version
    if dirv is None:
        dirv = default_direction_version()
        if dirv is None:
            print("::error::no --direction-version and no readable state/factory_direction.json")
            return 2

    report = check(dirv, state_path=args.state, paths=args.paths)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        wv = report["workflow_validation"]
        print(f"[{'PASS' if wv['ok'] else 'FAIL'}] Validate active MVP producer state: {wv['message']}")
        ws = report["write_scope"]
        print(
            f"[{'PASS' if ws['ok'] else 'FAIL'}] Enforce lane write scope: "
            f"{ws['checked_paths']} path(s) checked"
            + ("" if ws["ok"] else f" -> {ws['violations']}")
        )
        ao = report["audit_artifact_ownership"]
        if ao["producer_wrote_audit_paths"] or ao["committed_audit_artifacts"]:
            print(
                f"[{'PASS' if ao['ok'] else 'FAIL'}] Independent audit artifact ownership: "
                f"pending={ao['producer_wrote_audit_paths']} committed={ao['committed_audit_artifacts']}"
            )
        sh = report["shadow_state"]
        if sh["findings"]:
            print(f"[FAIL] No shadow state copies allowed: {[f['path'] for f in sh['findings']]}")
    return 0 if report["ok"] else (68 if not report["workflow_validation"]["ok"] else 3)


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())