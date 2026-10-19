#!/usr/bin/env python3
"""Demonstrator + patch emitter for the Frontier producer zero-delta defect.

Defect (evidence: runs 39182826179, 39184014244, 39180403192)
-------------------------------------------------------------
``.github/workflows/frontier-team.yml`` step "Validate Frontier producer delta
and state" decides ZERO_DELTA from the worktree/index only:

    if git diff --quiet && git diff --cached --quiet && [[ -z "$(git status --porcelain -uall)" ]]; then
      echo "::error::Frontier producer returned success with zero durable delta"
      exit 67
    fi

while the launcher ``.github/scripts/run-ox-with-retry.sh`` (START_HEAD at
line 163, guard at lines 213-217) also treats a MOVED HEAD as delta.  A
producer that self-commits (``git add -A && git commit``) therefore passes the
launcher guard (HEAD moved) but is then failed by the workflow validation
(worktree clean) with exit 67: two completed cycles were converted into
operational failures and fed the unbounded resume loop.  Producing nothing
fails the launcher; producing and self-committing fails workflow validation;
only producing WITHOUT committing passes -- an incoherent control plane.

This module is a READ-ONLY demonstrator: it extracts the shipped condition
verbatim from the workflow text, emits a minimal advisory unified diff that
ALSO counts a moved HEAD (without weakening the guard, and FAIL-SAFE when the
base head is unknown), and empirically discriminates shipped vs. proposed
predicate by running the REAL bash conditions in throwaway git repos.
``.github/`` is outside this Frontier team's write scope
(frontier-team.yml line 161 scope guard), so the patch is never applied here.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TEAM_ID = "frontier-query-concept-recall"
CHARTER_VERSION = 1
NETWORK_CALLS = 0
WORKFLOW_REL = ".github/workflows/frontier-team.yml"

CLAIM_CEILING = (
    "no artifact may assert that a map helps a jurist, that any authority is "
    "absent from the corpus, that any frozen bar is met or moved, or that any "
    "packet is fit to serve; usefulness remains the human product gate's "
    "question and admission remains fail-closed"
)

NOT_APPLIED_BY_THIS_TEAM = (
    ".github/ is outside the Frontier team write scope enforced by the "
    "frontier-team.yml scope-guard step (Enforce team scope, line 161); this "
    "team writes only under frontier/frontier-query-concept-recall/, "
    "tests/frontier/frontier-query-concept-recall/, results/, reports/ and "
    "state/frontier/query-concept-recall.json. The emitted patch is ADVISORY "
    "for the factory director / workflow owner to review and apply; this "
    "module and its tests never modify .github/."
)

ERROR_MESSAGE = "::error::Frontier producer returned success with zero durable delta"
EXIT_67_LINE = "exit 67"
SCOPE_GUARD_SIGNATURE = "Frontier crossed scope"

# Marker identifying the zero-delta predicate to extract.  Extraction still
# returns the VERBATIM condition bytes found in the file; if the workflow text
# no longer contains this exact predicate, extraction fails loudly rather than
# substituting a paraphrase.
CURRENT_PREDICATE_MARKER = (
    'if git diff --quiet && git diff --cached --quiet && '
    '[[ -z "$(git status --porcelain -uall)" ]]; then'
)

INIT_STEP_NAME = "Validate charter and initialize working base"
NEXT_STEP_NAME = "Mount accepted evidence"
BASE_ECHO_LINE = 'echo "LEX_BASE_HEAD=$(git rev-parse HEAD)" >> "$GITHUB_ENV"'

# Proposed condition design:
#   * head_unchanged OR base_unknown  -- the head check must also pass when
#     LEX_BASE_HEAD is unset, otherwise an unset base would silently DISABLE
#     the head comparison and turn the guard off;
#   * fail-safe: when LEX_BASE_HEAD is empty/unset we cannot prove delta, so
#     the "no delta" branch still fires (exit 67) on a clean tree.
# The ${LEX_BASE_HEAD:-} default also keeps this safe under the step's
# `set -u` (an unset base must not crash the step with an unbound-variable
# error; it must fail closed through exit 67).
PROPOSED_CONDITION = (
    '{ [[ -z "${LEX_BASE_HEAD:-}" ]] || [[ "$(git rev-parse HEAD)" == "${LEX_BASE_HEAD}" ]]; } '
    '&& git diff --quiet && git diff --cached --quiet && '
    '[[ -z "$(git status --porcelain -uall)" ]]'
)


def default_workflow_path() -> Path:
    return Path(__file__).resolve().parents[2] / WORKFLOW_REL


def _predicate_lines(workflow_text: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(workflow_text.splitlines(), start=1):
        if line.strip() == CURRENT_PREDICATE_MARKER:
            hits.append((lineno, line))
    return hits


def locate_current_predicate(workflow_text: str) -> tuple[int, str]:
    """Return (1-based line number, full verbatim line) of the zero-delta if."""
    hits = _predicate_lines(workflow_text)
    if len(hits) != 1:
        raise ValueError(
            f"expected exactly one zero-delta predicate matching "
            f"{CURRENT_PREDICATE_MARKER!r}, found {len(hits)}"
        )
    return hits[0]


def extract_current_condition(workflow_text: str) -> str:
    """Extract the VERBATIM shell condition of the zero-delta `if` (line 144).

    The returned string is the literal text between `if ` and `; then` as it
    appears in the file bytes -- never a paraphrase stored in this module.
    """
    _, line = locate_current_predicate(workflow_text)
    stripped = line.strip()
    if not stripped.startswith("if ") or not stripped.endswith("; then"):
        raise ValueError(f"unexpected predicate shape: {line!r}")
    return stripped[len("if "): -len("; then")].strip()


def extract_exit67_block(workflow_text: str) -> str:
    """Extract the verbatim `echo ::error ... / exit 67 / fi` block."""
    lineno, _ = locate_current_predicate(workflow_text)
    lines = workflow_text.splitlines()
    block: list[str] = []
    for line in lines[lineno:]:  # lines AFTER the `if ...; then` line
        block.append(line)
        if line.strip() == "fi":
            break
    text = "\n".join(block)
    if EXIT_67_LINE not in text or ERROR_MESSAGE not in text:
        raise ValueError("exit 67 block does not contain the required lines")
    return text


def _insert_base_echo(workflow_lines: list[str]) -> list[str]:
    init_idx = next(
        (i for i, l in enumerate(workflow_lines)
         if l.strip() == f"- name: {INIT_STEP_NAME}"),
        None,
    )
    if init_idx is None:
        raise ValueError(f"init step {INIT_STEP_NAME!r} not found")
    next_idx = next(
        (i for i in range(init_idx + 1, len(workflow_lines))
         if workflow_lines[i].strip().startswith("- name: ")),
        None,
    )
    if next_idx is None:
        raise ValueError("step following the init step not found")
    insert_at = next_idx
    while insert_at - 1 > init_idx and not workflow_lines[insert_at - 1].strip():
        insert_at -= 1
    indent = " " * (len(workflow_lines[insert_at - 1])
                    - len(workflow_lines[insert_at - 1].lstrip()))
    return (
        workflow_lines[:insert_at]
        + [f"{indent}{BASE_ECHO_LINE}"]
        + workflow_lines[insert_at:]
    )


def _replace_condition(workflow_lines: list[str]) -> list[str]:
    lineno, line = locate_current_predicate("\n".join(workflow_lines) + "\n")
    idx = lineno - 1
    indent = line[: len(line) - len(line.lstrip())]
    return (
        workflow_lines[:idx]
        + [f"{indent}if {PROPOSED_CONDITION}; then"]
        + workflow_lines[idx + 1:]
    )


def apply_proposed_edits(workflow_text: str) -> str:
    lines = workflow_text.splitlines(keepends=True)
    lines = _insert_base_echo(lines)
    lines = _replace_condition(lines)
    return "".join(lines)


def proposed_patch(workflow_path: Path | None = None) -> str:
    """Minimal git-style unified diff against the CURRENT workflow text."""
    path = Path(workflow_path) if workflow_path else default_workflow_path()
    original = path.read_text(encoding="utf-8")
    modified = apply_proposed_edits(original)
    body = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=f"a/{WORKFLOW_REL}",
            tofile=f"b/{WORKFLOW_REL}",
            n=3,
        )
    )
    return f"diff --git a/{WORKFLOW_REL} b/{WORKFLOW_REL}\n{body}"


def validate_patch(patch_text: str) -> list[str]:
    """Structural assertions on the emitted patch; [] means valid."""
    errors: list[str] = []
    if not patch_text.strip():
        return ["patch is empty"]
    lines = patch_text.splitlines()
    touched: set[str] = set()
    for line in lines:
        if line.startswith("diff --git "):
            for tok in line.split()[2:]:
                touched.add(tok[2:] if tok[:2] in ("a/", "b/") else tok)
        elif line.startswith("--- ") or line.startswith("+++ "):
            path = line[4:].split("\t")[0].strip()
            touched.add(path[2:] if path[:2] in ("a/", "b/") else path)
    if touched != {WORKFLOW_REL}:
        errors.append(f"patch touches {sorted(touched)!r}, expected only {WORKFLOW_REL!r}")

    def _is_payload(line: str) -> bool:
        return line.startswith(("+", "-")) and not line.startswith(("+++", "---"))

    added = [l for l in lines if _is_payload(l) and l.startswith("+")]
    deleted = [l for l in lines if _is_payload(l) and l.startswith("-")]
    kept = [
        l for l in lines
        if not _is_payload(l) and not l.startswith(("+++", "---", "diff ", "index ", "@@"))
    ]

    if not any("LEX_BASE_HEAD" in l for l in added):
        errors.append("patch does not add LEX_BASE_HEAD")
    if any(EXIT_67_LINE in l for l in deleted):
        errors.append("patch deletes exit 67")
    if not any(l[1:].strip() == EXIT_67_LINE for l in kept + added):
        errors.append("patch does not keep exit 67")
    if any(ERROR_MESSAGE in l for l in deleted):
        errors.append("patch deletes the ::error zero-delta message")
    if not any(ERROR_MESSAGE in l for l in kept + added):
        errors.append("patch does not keep the ::error zero-delta message")
    if any("git status --porcelain -uall" in l for l in kept + added) is False:
        errors.append("patch does not keep git status --porcelain -uall")
    if any(SCOPE_GUARD_SIGNATURE in l for l in deleted):
        errors.append("patch deletes the scope-guard line")
    return errors


# --------------------------------------------------------------------------
# Discrimination demo: run the REAL bash conditions, not a Python reimpl.
# --------------------------------------------------------------------------

_GIT_ENV_BASE = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_AUTHOR_NAME": "zero-delta-fix",
    "GIT_AUTHOR_EMAIL": "zero-delta-fix@local.invalid",
    "GIT_COMMITTER_NAME": "zero-delta-fix",
    "GIT_COMMITTER_EMAIL": "zero-delta-fix@local.invalid",
    "GIT_TERMINAL_PROMPT": "0",
}

_UNSET = object()


def _git(repo: Path, *args: str) -> str:
    env = dict(os.environ)
    env.update(_GIT_ENV_BASE)
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, env=env, timeout=30, check=True,
    )
    return result.stdout.strip()


def _make_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    (path / "f.txt").write_text("one\n", encoding="utf-8")
    _git(path, "add", "f.txt")
    _git(path, "commit", "-q", "-m", "commit 1")
    return path


def _eval_condition(condition: str, repo: Path, base_head) -> str:
    """Run the real condition under bash; return ZERO_DELTA or DELTA."""
    env = dict(os.environ)
    env.update(_GIT_ENV_BASE)
    if base_head is _UNSET:
        env.pop("LEX_BASE_HEAD", None)
    else:
        env["LEX_BASE_HEAD"] = str(base_head)
    script = (
        f'cd "{repo}" || exit 2\n'
        f"if {condition}; then echo ZERO_DELTA; else echo DELTA; fi\n"
    )
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True, text=True, env=env, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"condition evaluation failed rc={result.returncode}: "
            f"{result.stderr.strip()!r}"
        )
    verdict = result.stdout.strip().splitlines()[-1]
    if verdict not in ("ZERO_DELTA", "DELTA"):
        raise RuntimeError(f"unexpected verdict {verdict!r}")
    return verdict


def _scenario_producer_self_commit(root: Path):
    repo = _make_repo(root / "producer_self_commit")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "f.txt").write_text("two\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "commit 2 (producer self-commit)")
    return repo, base


def _scenario_true_zero_delta(root: Path):
    repo = _make_repo(root / "true_zero_delta")
    base = _git(repo, "rev-parse", "HEAD")
    return repo, base


def _scenario_uncommitted_work(root: Path):
    repo = _make_repo(root / "uncommitted_work")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "f.txt").write_text("one\ndirty\n", encoding="utf-8")
    return repo, base


def _scenario_staged_only_work(root: Path):
    repo = _make_repo(root / "staged_only_work")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "f.txt").write_text("one\nstaged\n", encoding="utf-8")
    _git(repo, "add", "f.txt")
    return repo, base


SCENARIOS = (
    ("producer_self_commit", _scenario_producer_self_commit),
    ("true_zero_delta", _scenario_true_zero_delta),
    ("uncommitted_work", _scenario_uncommitted_work),
    ("staged_only_work", _scenario_staged_only_work),
    ("missing_base", _scenario_producer_self_commit),
)

EXPECTED = {
    # defect reproduced: producer self-commits -> shipped fires exit 67
    "producer_self_commit": ("ZERO_DELTA", "DELTA"),
    # fix does not weaken: true zero delta still fires under both
    "true_zero_delta": ("ZERO_DELTA", "ZERO_DELTA"),
    # dirty worktree is delta under both predicates
    "uncommitted_work": ("DELTA", "DELTA"),
    # staged-but-uncommitted work is delta under both predicates
    "staged_only_work": ("DELTA", "DELTA"),
    # fail-safe: moved HEAD but unknown base -> proposed still fires exit 67
    "missing_base": ("ZERO_DELTA", "ZERO_DELTA"),
)


def discrimination_demo(worktree_dir: Path) -> dict:
    """Evaluate shipped vs. proposed predicate in real throwaway git repos."""
    workflow_text = default_workflow_path().read_text(encoding="utf-8")
    shipped = extract_current_condition(workflow_text)
    rows: list[dict] = []
    worktree_dir = Path(worktree_dir)
    worktree_dir.mkdir(parents=True, exist_ok=True)
    for name, builder in SCENARIOS:
        repo, base = builder(worktree_dir)
        base_head = _UNSET if name == "missing_base" else base
        shipped_verdict = _eval_condition(shipped, repo, _UNSET)
        proposed_verdict = _eval_condition(PROPOSED_CONDITION, repo, base_head)
        exp_shipped, exp_proposed = EXPECTED[name]
        rows.append({
            "scenario": name,
            "shipped": shipped_verdict,
            "proposed": proposed_verdict,
            "expected_shipped": exp_shipped,
            "expected_proposed": exp_proposed,
            "pass": shipped_verdict == exp_shipped and proposed_verdict == exp_proposed,
        })
    return {
        "shipped_condition": shipped,
        "proposed_condition": PROPOSED_CONDITION,
        "scenarios": rows,
        "all_pass": all(r["pass"] for r in rows),
    }


def workflow_sha256(path: Path | None = None) -> str:
    p = Path(path) if path else default_workflow_path()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def github_tree_sha256(root: Path | None = None) -> str:
    base = (Path(root) if root else default_workflow_path().parents[2]) / ".github"
    digest = hashlib.sha256()
    for f in sorted(p for p in base.rglob("*") if p.is_file()):
        digest.update(str(f.relative_to(base)).encode())
        digest.update(f.read_bytes())
    return digest.hexdigest()


def build_record(out_dir: Path) -> dict:
    workflow_path = default_workflow_path()
    before = workflow_sha256(workflow_path)
    tree_before = github_tree_sha256()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    lineno, full_line = locate_current_predicate(workflow_text)
    condition = extract_current_condition(workflow_text)
    exit_block = extract_exit67_block(workflow_text)
    patch = proposed_patch(workflow_path)
    validation_errors = validate_patch(patch)
    demo = discrimination_demo(Path(out_dir) / "worktrees")
    after = workflow_sha256(workflow_path)
    tree_after = github_tree_sha256()
    return {
        "charter_version": CHARTER_VERSION,
        "team_id": TEAM_ID,
        "network_calls": NETWORK_CALLS,
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "claim_ceiling": CLAIM_CEILING,
        "not_applied_by_this_team": NOT_APPLIED_BY_THIS_TEAM,
        "defect": {
            "workflow": WORKFLOW_REL,
            "predicate_line_number": lineno,
            "predicate_line": full_line,
            "current_condition": condition,
            "exit_67_block": exit_block,
            "launcher_contract": (
                ".github/scripts/run-ox-with-retry.sh lines 163, 213-217: "
                "delta = (HEAD moved) OR (worktree/index dirty)"
            ),
            "consequence": (
                "producer that self-commits passes the launcher guard but is "
                "failed by workflow validation with exit 67; producing "
                "nothing fails the launcher; only producing without "
                "committing passes -- two completed cycles "
                "(39182826179, 39184014244) were converted into operational "
                "failures and fed the unbounded resume loop"
            ),
        },
        "proposed_fix": {
            "base_echo_line": BASE_ECHO_LINE,
            "proposed_condition": PROPOSED_CONDITION,
            "fail_safe": (
                "If LEX_BASE_HEAD is unset the head comparison cannot prove "
                "delta, so the condition still treats a clean tree as "
                "zero-delta and fires exit 67; the guard is never silently "
                "turned off by a missing base. ${LEX_BASE_HEAD:-} also keeps "
                "the step's `set -u` from crashing before the guard runs."
            ),
            "does_not_weaken": (
                "The three existing worktree/index clauses are kept verbatim "
                "and ANDed with the head-unchanged requirement; exit 67 and "
                "the ::error message are kept verbatim; the scope guard is "
                "untouched."
            ),
        },
        "patch": patch,
        "patch_validation_errors": validation_errors,
        "patch_valid": not validation_errors,
        "discrimination": demo,
        "workflow_sha256_before": before,
        "workflow_sha256_after": after,
        "github_tree_sha256_before": tree_before,
        "github_tree_sha256_after": tree_after,
        "github_untouched": before == after and tree_before == tree_after,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--print", action="store_true", dest="do_print",
                        help="print the unified diff to stdout")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    record = build_record(out_dir)
    (out_dir / "zero_delta_fix.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "zero_delta_fix.patch").write_text(record["patch"], encoding="utf-8")
    if args.do_print:
        sys.stdout.write(record["patch"])
    if not record["github_untouched"]:
        print("::error::.github/ was modified; aborting", file=sys.stderr)
        return 1
    if not record["patch_valid"] or not record["discrimination"]["all_pass"]:
        print("::error::patch validation or discrimination demo failed",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
