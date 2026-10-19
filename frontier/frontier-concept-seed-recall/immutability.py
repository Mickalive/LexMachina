"""Fail-closed guard against overwriting committed claim-bearing artifacts.

Operational failure this exists to prevent (run 39241812486 of this same
charter): a resume cycle re-ran ``harness.py`` with the original run id, which
silently rewrote the *committed* historical record
``results/frontier/frontier-concept-seed-recall/harness_results_39237146851.json``
-- changing its sha256 from
``2f7da7816b089339742060744e5baad057fa8cd14022cd163ed04263c1d02a36``
to ``ebed6952d51e9ba42a07291866f0d5a2fe1022833b61bb102e85be9281b908b7``.
Only two ``wall_seconds`` fields changed -- no decision-bearing byte -- but the
constitution forbids overwriting historical claim-bearing results at all, and
a resume that rewrites the record it is supposed to verify destroys the very
artifact the audit chain depends on.

The rule enforced here is deliberately narrow and mechanical:

  * If the target path appears in the git index OR anywhere in ``git log
    --all`` history, it is a committed historical record and the write is
    REFUSED, always, with no escape hatch.  The caller must use a fresh
    ``--run-id`` (the current GitHub run id) and/or a scratch ``--out-dir``.
  * If the target path is untracked (a scratch directory, or a brand-new
    run-id file not yet committed) the write is allowed -- that is how the
    original measurement was produced and how verification replays are meant
    to run.
  * If git cannot be consulted at all and the file already exists on disk,
    the write is REFUSED (fail closed): absence of evidence that a file is
    historical is not evidence that it is safe to destroy.

``freeze_ordering.py`` already carried its own stronger/weaker guard; this
module covers the run-id-scoped result files, the integration contract and the
frozen RULES.json that that guard does not mention.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class OverwriteRefused(RuntimeError):
    """Raised when a write would destroy a committed historical record."""


def _git(args: list[str], repo: Path) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None


def is_committed_record(path: Path, *, repo: Path | None = None) -> bool:
    """True iff ``path`` is a committed historical record.

    "Committed" means present in the current index or reachable from any
    ref in ``git log --all -- <path>``.  A file that merely exists on disk in
    a scratch directory is NOT a committed record.
    """
    p = Path(path)
    root = Path(repo) if repo else REPO_ROOT
    if not (p.exists() or _path_in_index_or_history(p, root)):
        return False
    return _path_in_index_or_history(p, root)


def _path_in_index_or_history(p: Path, root: Path) -> bool:
    try:
        rel = str(p.resolve().relative_to(root.resolve()))
    except ValueError:
        # Outside the repo: fall back to a repo-relative guess from the
        # caller's perspective is impossible; treat as untracked scratch.
        return False
    ls = _git(["ls-files", "--error-unmatch", "--", rel], root)
    if ls is not None and ls.returncode == 0 and ls.stdout.strip():
        return True
    log = _git(["log", "--all", "--format=%H", "--", rel], root)
    if log is not None and log.returncode == 0 and log.stdout.strip():
        return True
    return False


def ensure_untracked(path: Path, *, what: str, repo: Path | None = None) -> None:
    """Refuse to overwrite a committed historical record; no-op otherwise.

    Raises :class:`OverwriteRefused` (a ``RuntimeError``) with an actionable
    message naming the fresh-run-id escape hatch.  Never modifies the file.
    """
    p = Path(path)
    root = Path(repo) if repo else REPO_ROOT
    if is_committed_record(p, repo=root):
        raise OverwriteRefused(
            f"REFUSING TO OVERWRITE COMMITTED HISTORICAL RECORD: {what} at {p} "
            "is present in git history or the index.  A verification or resume "
            "run must write to a FRESH --run-id (use the current GitHub run id) "
            "and/or a scratch --out-dir, and must publish its numbers BESIDE "
            "the historical record, never in place of it.  (This guard exists "
            "because resume run 39241812486 rewrote the two wall_seconds fields "
            "of the committed harness_results_39237146851.json; no decision-"
            "bearing byte changed, but the overwrite itself violated the "
            "non-overwrite rule and broke byte-level auditability.)")
    if p.exists() and _git_available_unreliable(root):
        # File exists on disk but git gave no signal either way -> fail closed.
        raise OverwriteRefused(
            f"REFUSING TO OVERWRITE EXISTING FILE WITH UNVERIFIABLE PROVENANCE: "
            f"{what} at {p} exists and git history could not be consulted; "
            "absence of evidence that it is historical is not evidence that it "
            "is safe to destroy.  Use a fresh --run-id or a new --out-dir.")


def _git_available_unreliable(root: Path) -> bool:
    """True when git could not be consulted (treat existing files as unsafe)."""
    probe = _git(["rev-parse", "--is-inside-work-tree"], root)
    return probe is None or probe.returncode != 0


__all__ = ["OverwriteRefused", "ensure_untracked", "is_committed_record"]
