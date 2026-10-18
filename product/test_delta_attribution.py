#!/usr/bin/env python3
"""Per-CYCLE attribution of a collected-test delta, measured instead of typed.

Why this exists
---------------
Audit RF-1 of rejected product cycle 39144924680: the report of record's
regression table decomposed its own ``+21`` collected-test delta as ``+17 (the
predecessor cycle) + +4 (this cycle)``, attributing the +17 to the immediate
predecessor 39139648336. That attribution was false: the module it names was
added two cycles earlier, by commit ``db3891e`` in cycle 39128456801.

A prose attribution of a measured delta is the same defect class as the citation
count this chain already corrected twice (6 -> 5 in CYCLE_39139648336.md, 13 ->
17 in CYCLE_39128456801.md) and as direction v56's "+7 tests" against a measured
+10. Every occurrence was a number typed into prose instead of derived from the
measurement it summarises.

The audit's terminal condition for round 5 is explicit about what to do about
it: *"stop repairing prose and route the loop to a structural remedy (derive
report numbers at write time, or drop hand-written decompositions) rather than
opening a sixth round."* This module is that remedy. It measures the collected
count at the baseline commit, at every commit in between that touched the test
tree, and at the working tree, and it emits the decomposition AS A MACHINE-READABLE
STRING that the report quotes verbatim. The hand-written decomposition is gone.

It also refuses to publish, rather than publishing a decomposition that does not
close:

    sum(per-step collected deltas) == head_total - base_total

Usage
-----
    python3 product/test_delta_attribution.py --base 9727a45 --run-id <id> \
        --out results/product/regression/CYCLE_<id>_test_delta_attribution.json

``--head`` defaults to the WORKING TREE (not a commit), because the interesting
head is the tree this cycle ships before it is committed. Measurement is
collection-only (``pytest --collect-only``): this tool claims nothing about
pass/fail, so it must never spend a full suite run to do its job.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
#: Repository the measurement runs against. ``ROOT`` unless ``--root`` names
#: another one (the refusal controls run against a synthetic repository, which is
#: why this is not hard-wired into every helper).
GIT_ROOT = ROOT
TESTS_DIR = "product/tests"
COLLECTED_LINE = re.compile(r"(?P<n>\d+) tests? collected")
SCHEMA = "product-test-delta-attribution/1"


class RefuseToPublish(RuntimeError):
    """The measurement does not close. Publishing it would publish a defect."""


def _git(*args: str, cwd: Path | None = None) -> str:
    proc = subprocess.run(  # noqa: S603
        ["git", *args], cwd=str(cwd or GIT_ROOT), capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise RefuseToPublish(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _rev(ref: str) -> str:
    return _git("rev-parse", ref).strip()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_count(root: Path, tests_dir: str = TESTS_DIR) -> int:
    """Tests COLLECTED under ``tests_dir`` at ``root``. Nothing else.

    Collection-only by design: this tool attributes a count of tests, never a
    verdict about them. A full run here would also re-spend the regression
    measurement the round-4 audit explicitly fenced as "round 5 must NOT
    re-spend".
    """
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", tests_dir, "--collect-only", "-q",
         "-p", "no:cacheprovider"],
        cwd=str(root), capture_output=True, text=True, check=False,
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    for line in reversed(tail):
        m = COLLECTED_LINE.search(line)
        if m:
            return int(m.group("n"))
    raise RefuseToPublish(
        f"no collection count at {root}: last lines were {tail[-3:]!r}"
    )


def module_count(root: Path, module: str, tests_dir: str = TESTS_DIR) -> int:
    """Tests collected in ONE module (used for per-module attribution)."""
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", f"{tests_dir}/{module}", "--collect-only",
         "-q", "-p", "no:cacheprovider"],
        cwd=str(root), capture_output=True, text=True, check=False,
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    for line in reversed(tail):
        m = COLLECTED_LINE.search(line)
        if m:
            return int(m.group("n"))
    # A module that cannot be collected here is MEASURED AS ABSENT, not as 0:
    # reporting 0 would invent a delta of -N that was never observed.
    raise RefuseToPublish(f"module {module} did not report a collection count at {root}")


def _commit_meta(sha: str) -> dict[str, str]:
    raw = _git("show", "-s", "--format=%h%x1f%s%x1f%aI", sha).strip()
    short, subject, date = raw.split("\x1f")
    return {"commit": sha, "short": short, "subject": subject, "authored": date}


def _modules_touched(sha: str) -> tuple[list[str], list[str]]:
    """(added, modified) test modules in one commit, by git itself."""
    out = _git("show", "--name-status", "--format=", sha)
    added, modified = [], []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        if not path.startswith(TESTS_DIR + "/"):
            continue
        module = path.split("/")[-1]
        (added if status.startswith("A") else modified).append(module)
    return sorted(added), sorted(modified)


class _Worktree:
    """A detached worktree at one commit, removed again whatever happens."""

    def __init__(self, sha: str, parent: Path) -> None:
        self.sha = sha
        self.path = parent / sha[:12]

    def __enter__(self) -> Path:
        if self.path.exists():
            shutil.rmtree(self.path)
        _git("worktree", "add", "--detach", "-q", str(self.path), self.sha)
        return self.path

    def __exit__(self, *exc: object) -> None:
        try:
            _git("worktree", "remove", "--force", str(self.path))
        except RefuseToPublish:
            shutil.rmtree(self.path, ignore_errors=True)
        finally:
            shutil.rmtree(self.path, ignore_errors=True)
            _git("worktree", "prune")


def measure_working_tree(head_sha: str, head_total: int, tests_dir: str = TESTS_DIR,
                         module_count_at=None) -> dict[str, Any]:
    """Attribute the UNCOMMITTED collected-count delta to the modules git names.

    A cycle's in-flight tests are not a commit. Folding them into the committed
    range's arithmetic makes the committed decomposition unclosable; ignoring them
    hides a real number. So they are measured here, attributed to the untracked
    modules ``git status`` reports, and reconciled on their own terms: if the tree
    collects tests that no new module accounts for, ``reconciles`` is false and
    the caller refuses to publish rather than emit a decomposition that closes by
    coincidence.
    """
    root = Path(GIT_ROOT)
    status = _git("status", "--porcelain", "-uall", "--", tests_dir)
    changes: list[tuple[str, str]] = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2].strip(), line[3:].strip()
        if path.startswith(tests_dir + "/"):
            changes.append((code, path.split("/")[-1]))

    live_total = collect_count(root, tests_dir)
    per_module: dict[str, Any] = {}
    for code, module in sorted(changes):
        path = root / tests_dir / module
        if code == "??":
            try:
                after = module_count(root, module, tests_dir)
            except RefuseToPublish as exc:
                per_module[module] = {"git": code, "error": str(exc)}
                continue
            per_module[module] = {"git": code, "state_before": "ABSENT",
                                   "collected_before": 0, "collected_after": after,
                                   "delta": after}
            continue
        if not path.exists():
            per_module[module] = {"git": code, "state_before": "present",
                                   "collected_before": None, "collected_after": None,
                                   "delta": None,
                                   "note": "DELETED in the working tree; its committed tests "
                                           "are part of the committed range, not this delta"}
            continue
        try:
            after = module_count(root, module, tests_dir)
            before = (module_count_at(head_sha, module) if module_count_at else None)
        except RefuseToPublish as exc:
            per_module[module] = {"git": code, "error": str(exc)}
            continue
        per_module[module] = {
            "git": code,
            "state_before": "present",
            "collected_before": before,
            "collected_after": after,
            "delta": (None if not isinstance(before, int) else after - before),
        }

    measured_deltas = {k: v["delta"] for k, v in per_module.items()
                       if isinstance(v.get("delta"), int)}
    attributed = sum(measured_deltas.values())
    delta = live_total - head_total
    short = _commit_meta(head_sha)["short"]
    parts = " + ".join(f"{v:+d}" for v in measured_deltas.values()) or "+0"
    detail = ", ".join(f"{k}={v:+d}" for k, v in sorted(measured_deltas.items()))
    return {
        "measured": True,
        "head_commit": head_sha,
        "head_collected_total": head_total,
        "collected_total": live_total,
        "delta_vs_head_commit": delta,
        "uncommitted_test_modules": [
            {"git": code, "module": module, **(per_module.get(module) or {})}
            for code, module in sorted(changes)
        ],
        "attributed_delta": attributed,
        "attributed_by_module": measured_deltas,
        "reconciles": delta == attributed,
        "reconciliation_rule": (
            "the working-tree delta must equal the sum of the per-module collection deltas of "
            "every uncommitted test-module change git reports (new modules add their whole "
            "collected count; edited modules add what the edit collected). A conftest change, a "
            "plugin or a different pytest version can move collection with no module to blame; "
            "that leaves reconciles false and the tool REFUSES to publish rather than explaining "
            "the number away"),
        "decomposition_line": (
            f"working-tree collected delta {short} -> tree = {delta:+d} = {parts}  ({detail})"),
    }


def build_decomposition_line(
    base_short: str, observed_delta: int, steps: list[dict[str, Any]]
) -> str:
    """The one canonical sentence a report may quote. Pure, so it is testable.

    Kept as a function rather than an f-string inside ``attribution`` because the
    report of record quotes this line VERBATIM and ``test_report_artifact_
    arithmetic`` compares the report against it: if the wording lived inline,
    the two could drift and the check would compare a report to itself.
    """
    parts = " + ".join(
        f"{s['collected_delta_vs_previous_step']:+d}" for s in steps
    ) or "+0"
    per_commit = ", ".join(
        f"{s['short']}={s['collected_delta_vs_previous_step']:+d}" for s in steps
    )
    return (
        f"collected-test delta {base_short} -> head = {observed_delta:+d} = {parts}"
        f"  ({per_commit})"
    )


def attribution(base: str, head_mode: str, tests_dir: str = TESTS_DIR) -> dict[str, Any]:
    """Measure the collected-count decomposition from ``base`` to the head."""
    base_sha = _rev(base)
    base_meta = _commit_meta(base_sha)
    worktree_head = head_mode in ("WORKTREE", "worktree", ".")
    # The git RANGE always ends at a real commit. The working tree is the HEAD
    # commit plus this cycle's uncommitted delta, and it is measured separately
    # below, so the two are never conflated.
    range_end = "HEAD" if worktree_head else head_mode

    with tempfile.TemporaryDirectory(prefix="lex_delta_attr_") as tmp:
        tmp_path = Path(tmp)

        # Every commit in range that touched the test tree is a STEP. Commits
        # that did not touch it are skipped with a stated reason rather than
        # silently dropped: a commit could not have moved a test count.
        chain = [s for s in _git("log", "--reverse", "--format=%H", f"{base_sha}..{range_end}").split() if s]
        touched: dict[str, tuple[list[str], list[str]]] = {}
        for sha in chain:
            added, modified = _modules_touched(sha)
            if added or modified:
                touched[sha] = (added, modified)
        watch = sorted({m for pair in touched.values() for m in pair[0] + pair[1]})

        def measure(sha: str) -> dict[str, Any]:
            """Whole-suite collected count plus the watched modules' counts."""
            with _Worktree(sha, tmp_path) as root:
                present = {p.name for p in sorted((root / tests_dir).glob("test_*.py"))}
                out: dict[str, Any] = {
                    "collected_total": collect_count(root, tests_dir),
                    "modules_present": present,
                    "module_counts": {},
                }
                for module in watch:
                    if module not in present:
                        continue
                    try:
                        out["module_counts"][module] = module_count(root, module, tests_dir)
                    except RefuseToPublish as exc:
                        out["module_counts"][module] = f"UNMEASURED: {exc}"
                return out

        base_measured = measure(base_sha)
        base_total = base_measured["collected_total"]

        steps: list[dict[str, Any]] = []
        previous = base_measured
        previous_sha = base_sha
        for sha in chain:
            if sha not in touched:
                continue
            added, modified = touched[sha]
            current = measure(sha)
            per_module = {}
            for module in sorted(set(added) | set(modified)):
                before = previous["module_counts"].get(module)
                after = current["module_counts"].get(module)
                per_module[module] = {
                    "state_before": ("ABSENT" if before is None else "present"),
                    "state_after": ("ABSENT" if after is None else "present"),
                    "collected_before": before,
                    "collected_after": after,
                    "delta": (
                        None if not isinstance(before, int) or not isinstance(after, int)
                        else after - before
                    ),
                    "git": ("A" if module in added else "M"),
                }
            steps.append({
                **_commit_meta(sha),
                "modules_added": added,
                "modules_modified": modified,
                "collected_total": current["collected_total"],
                "collected_delta_vs_previous_step": current["collected_total"] - previous["collected_total"],
                "previous_measured_commit": previous_sha,
                "per_module": per_module,
            })
            previous, previous_sha = current, sha

        head_label = head_mode
        if worktree_head:
            head_sha = _rev("HEAD")
            head_measured = measure(head_sha)
            head_total = head_measured["collected_total"]
            head_label = f"head commit {_commit_meta(head_sha)['short']} (range endpoint)"
        else:
            head_sha = _rev(head_mode)
            with _Worktree(head_sha, tmp_path) as head_root:
                head_total = collect_count(head_root, tests_dir)
            head_label = head_mode

        step_total = sum(s["collected_delta_vs_previous_step"] for s in steps)
        observed_delta = head_total - base_total
        reconciles = step_total == observed_delta

        decomposition_line = build_decomposition_line(
            base_meta["short"], observed_delta, steps)

        def _module_count_at(sha: str, module: str) -> int:
            with _Worktree(sha, tmp_path) as root:
                return module_count(root, module, tests_dir)

        working_tree = (
            measure_working_tree(head_sha, head_total, tests_dir, _module_count_at)
            if worktree_head
            else {"measured": False,
                  "why": "head was named as a commit, so there is no uncommitted range to attribute"}
        )

    return {
        "schema": SCHEMA,
        "base": {**base_meta, "collected_total": base_total},
        "head": {"label": head_label, "commit": head_sha, "collected_total": head_total},
        "observed_collected_delta": observed_delta,
        "steps": steps,
        "step_deltas_sum": step_total,
        "reconciles": reconciles,
        "decomposition_line": decomposition_line,
        "working_tree": working_tree,
        "method": {
            "measurement": "pytest --collect-only -q (collection only; NO suite run, no pass/fail claim)",
            "step_selection": "git log --reverse base..head, keeping only commits whose name-status "
                              "touches product/tests/; a commit that touches no test module cannot move a "
                              "collected count and is skipped with this rule stated rather than silently",
            "attribution_rule": "a step's delta is the change in the whole-suite collected count across "
                                "that commit, attributed to the modules git says it added or modified",
            "per_module": "per-module counts are collected AFTER the commit; a module that cannot be "
                          "collected in this environment is recorded as an error, never as 0",
            "head_and_working_tree": (
                "the range ends at a COMMIT, so the committed decomposition always closes on its own; "
                "the uncommitted working tree is measured separately and attributed to the modules "
                "`git status` reports, because a cycle's in-flight tests are not a commit and must never "
                "be silently folded into a committed range's arithmetic"),
            "worktree_lifecycle": "one detached worktree per measured commit under a temporary directory, "
                                  "removed and pruned in a finally block; nothing outside it is touched",
        },
        "claim_ceiling": (
            "A collection-count attribution measured in THIS environment at THIS root. It says nothing "
            "about pass/fail (no suite was run), nothing about any other environment, and nothing about "
            "any frozen bar. It measures which commit moved a collected count, which is a statement about "
            "the git history of this repository, not about product behaviour."
        ),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pytest": _module_version("pytest"),
            "measured_at_root": str(GIT_ROOT),
        },
    }


def _module_version(module: str) -> str | None:
    try:
        mod = __import__(module)
        return getattr(mod, "__version__", "unknown")
    except Exception:
        return None


def cross_check(result: dict[str, Any], regression_artifact: Path | None) -> dict[str, Any]:
    """Compare the base total against a committed regression-scope artifact.

    Independent corroboration, not a dependency: the regression artifact measured
    a FULL run, this tool measured collection only. If they disagree, that is
    published as the finding rather than reconciled away.
    """
    if regression_artifact is None or not regression_artifact.exists():
        return {"status": "NOT_RUN", "why": "no regression-scope artifact supplied"}
    try:
        data = json.loads(regression_artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "UNREADABLE", "why": f"{type(exc).__name__}: {exc}"}
    art_base = (data.get("baseline_run") or {}).get("collected")
    art_head = (data.get("repaired_run") or {}).get("collected")
    art = regression_artifact
    try:
        artifact_path = str(art.resolve().relative_to(GIT_ROOT))
    except ValueError:
        artifact_path = str(art)
    return {
        "status": "COMPARED",
        "artifact": artifact_path,
        "artifact_sha256": hashlib.sha256(regression_artifact.read_bytes()).hexdigest(),
        "artifact_collected_baseline": art_base,
        "artifact_collected_head": art_head,
        "tool_collected_base": result["base"]["collected_total"],
        "tool_collected_head": result["head"]["collected_total"],
        "base_agrees": art_base == result["base"]["collected_total"],
        "head_agrees": art_head == result["head"]["collected_total"],
        "note": (
            "the artifact's head is the tree its OWN cycle shipped; this tool's head is "
            "the tree this cycle ships, so a head disagreement is expected exactly when "
            "this cycle added or removed tests. The base must agree: it is one named commit."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True,
                    help="baseline commit (must be the SAME commit the regression scope named)")
    ap.add_argument("--head", default="WORKTREE",
                    help="head commit, or WORKTREE (default) for the tree under test")
    ap.add_argument("--run-id", default=None, help="stamped into the artifact")
    ap.add_argument("--tests-dir", default=TESTS_DIR)
    ap.add_argument("--root", default=None,
                    help="repository to measure (default: the repo this module lives in). The "
                         "refusal controls point this at a synthetic repository.")
    ap.add_argument("--regression-artifact", default=None,
                    help="a committed regression-scope artifact to cross-check the base total against")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    global GIT_ROOT
    if args.root:
        GIT_ROOT = Path(args.root).resolve()

    try:
        result = attribution(args.base, args.head, args.tests_dir)
    except RefuseToPublish as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        print("nothing written; re-derive, do not publish an unclosed decomposition",
              file=sys.stderr)
        return 2

    result["cross_check"] = cross_check(
        result, Path(args.regression_artifact) if args.regression_artifact else None)
    if args.run_id:
        result["run_id"] = int(args.run_id)

    print(f"base    {result['base']['short']} ({result['base']['collected_total']} collected)")
    for step in result["steps"]:
        print(f"  step  {step['short']}  {step['collected_delta_vs_previous_step']:+d}"
              f"  {step['subject'][:70]}")
    print(f"head    {result['head']['collected_total']} collected")
    print(f"delta   {result['observed_collected_delta']:+d}")
    print(f"line    {result['decomposition_line']}")
    tree = result.get("working_tree") or {}
    if tree.get("measured"):
        print(f"tree    {tree['collected_total']} collected "
              f"({tree['delta_vs_head_commit']:+d} uncommitted)")
        print(f"tree    {tree['decomposition_line']}")

    if not result["reconciles"]:
        print("REFUSED: the per-step deltas do not sum to the observed total delta "
              f"({result['step_deltas_sum']} != {result['observed_collected_delta']}); "
              "nothing written", file=sys.stderr)
        return 2
    if tree.get("measured") and not tree["reconciles"]:
        print(f"REFUSED: the working tree collects {tree['collected_total']} tests, "
              f"{tree['delta_vs_head_commit']:+d} over the head commit, but its untracked "
              f"modules account for {tree['attributed_delta']:+d} "
              f"(uncommitted changes: {[m['module'] for m in tree['uncommitted_test_modules']]}); "
              "nothing written - commit the tests, or explain the collection change before "
              "publishing a decomposition", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out} sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    os.chdir(ROOT)
    raise SystemExit(main())