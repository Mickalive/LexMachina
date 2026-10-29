#!/usr/bin/env python3
"""Pins the delta-substance classifier and the resumed run's cache-only delta.

Run 40783679367's TEAM job was fully green and persisted a 25-file committed
delta over its predecessor (``40772551540``'s team head ``d1f2356a``) — and not
one of those files is product code, test, report, state or a results artifact.
22 are query-cache envelopes whose only change is ``fetched_at``; 3 are
cache envelopes whose upstream ``citation_count`` moved (a live re-fetch).
``product/delta_substance.py`` makes that distinction mechanical so a cycle
with zero product work cannot be described as one with product work merely
because it touched files.

The real-range test is conditional on the predecessor ref being fetched (the
workflow mounts it), so this module is runnable on a bare checkout too.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import delta_substance as ds  # noqa: E402

PREDECESSOR_REF = (
    "refs/remotes/origin/cycle/core/product/40772551540/team"
)
SNAPSHOT_REF = (
    "refs/remotes/origin/cycle/core/product/40783679367/team"
)
RESUMED_DELTA_ARTIFACT = (
    ROOT / "results" / "product" / "orchestration"
    / "CYCLE_40783679367_delta_substance.json"
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=repo, text=True
    ).strip()


def _init_repo(tmp: Path) -> Path:
    tmp.mkdir()
    _git(tmp, "init", "-q")
    _git(tmp, "config", "user.email", "test@example.invalid")
    _git(tmp, "config", "user.name", "delta test")
    return tmp


def _write(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def test_real_snapshot_delta_is_cache_refresh_not_product_work():
    has_refs = True
    for ref in (PREDECESSOR_REF, SNAPSHOT_REF):
        try:
            ds._rev(ref)
        except ds.GitError:
            has_refs = False
    if not has_refs:
        return  # bare checkout: no predecessor/snapshot refs to inspect

    rec = ds.classify(PREDECESSOR_REF, SNAPSHOT_REF)
    assert rec["changed_files"] == 25
    assert rec["delta_substance"] == "CACHE_REFRESH"
    assert rec["product_work"] is False
    assert rec["cache_timestamp_only_count"] == 22
    assert rec["cache_content_count"] == 3
    assert rec["substantive_files"] == []
    assert rec["cache_manifest_covered_rewrites"] == []
    for path in rec["cache_timestamp_only"] + rec["cache_content"]:
        assert path.startswith("results/product/query_cache/")
        assert path.endswith(".json")

    # The committed artifact of record must agree with a fresh classification.
    if RESUMED_DELTA_ARTIFACT.is_file():
        stored = json.loads(RESUMED_DELTA_ARTIFACT.read_text(encoding="utf-8"))
        for key in ("changed_files", "delta_substance", "product_work",
                    "cache_timestamp_only_count", "cache_content_count"):
            assert stored[key] == rec[key], key


def test_cache_timestamp_only_is_not_product_work(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    envelope = (
        '{"body": "{\\"decision_id\\": \\"bge_1\\"}", '
        '"cache_version": 1, "fetched_at": __TS__, "key": "k", '
        '"path": "/decision/bge_1", "status": 200}\n'
    )
    rel = ("results/product/query_cache/aa/"
           "aa0000000000000000000000000000000000000000000000000000000000.json")
    _write(repo, rel, envelope.replace("__TS__", "1000"))
    base = _commit(repo, "base")
    _write(repo, rel, envelope.replace("__TS__", "2000"))
    head = _commit(repo, "refresh only")

    rec = ds.classify(base, head, repo_root=repo,
                      manifest_path=repo / "no-manifest.json")
    assert rec["changed_files"] == 1
    assert rec["delta_substance"] == "CACHE_ONLY"
    assert rec["product_work"] is False
    assert rec["cache_timestamp_only"] == [rel]


def test_cache_body_change_is_cache_refresh(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    rel = ("results/product/query_cache/bb/"
           "bb0000000000000000000000000000000000000000000000000000000000.json")
    _write(repo, rel, '{"body": "{\\"citation_count\\": 174}", '
                       '"fetched_at": 1000}\n')
    base = _commit(repo, "base")
    _write(repo, rel, '{"body": "{\\"citation_count\\": 172}", '
                       '"fetched_at": 2000}\n')
    head = _commit(repo, "content refresh")

    rec = ds.classify(base, head, repo_root=repo,
                      manifest_path=repo / "no-manifest.json")
    assert rec["delta_substance"] == "CACHE_REFRESH"
    assert rec["product_work"] is False
    assert rec["cache_content"] == [rel]


def test_product_code_change_is_substantive(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    _write(repo, "product/app/thing.py", "x = 1\n")
    base = _commit(repo, "base")
    _write(repo, "product/app/thing.py", "x = 2\n")
    head = _commit(repo, "code")

    rec = ds.classify(base, head, repo_root=repo,
                      manifest_path=repo / "no-manifest.json")
    assert rec["delta_substance"] == "SUBSTANTIVE"
    assert rec["product_work"] is True
    assert rec["substantive_files"] == ["product/app/thing.py"]


def test_state_and_report_changes_are_substantive(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    _write(repo, "state/product.json", "{}\n")
    _write(repo, "reports/product/R.md", "old\n")
    base = _commit(repo, "base")
    _write(repo, "state/product.json", '{"x": 1}\n')
    _write(repo, "reports/product/R.md", "new\n")
    head = _commit(repo, "state+report")

    rec = ds.classify(base, head, repo_root=repo,
                      manifest_path=repo / "no-manifest.json")
    assert rec["delta_substance"] == "SUBSTANTIVE"
    assert set(rec["substantive_files"]) == {
        "state/product.json", "reports/product/R.md"}


def test_empty_range_is_empty(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    _write(repo, "product/app/thing.py", "x = 1\n")
    base = _commit(repo, "base")
    rec = ds.classify(base, base, repo_root=repo,
                      manifest_path=repo / "no-manifest.json")
    assert rec["changed_files"] == 0
    assert rec["delta_substance"] == "EMPTY"
    assert rec["product_work"] is False


def test_manifest_covered_rewrite_is_published(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    rel = ("results/product/query_cache/cc/"
           "cc0000000000000000000000000000000000000000000000000000000000.json")
    manifest = repo / "manifest.json"
    _write(repo, rel, '{"body": "{}", "fetched_at": 1000}\n')
    _write(repo, "manifest.json",
           json.dumps({"entries": [{"path": rel}]}) + "\n")
    base = _commit(repo, "base")
    _write(repo, rel, '{"body": "{}", "fetched_at": 2000}\n')
    head = _commit(repo, "refresh")

    rec = ds.classify(base, head, repo_root=repo, manifest_path=manifest)
    assert rec["cache_manifest_covered_rewrites"] == [rel]


def test_cli_require_substantive_guard_on_resumed_range():
    """The guard returns 2 for the resumed run's cache-only delta."""
    for ref in (PREDECESSOR_REF, SNAPSHOT_REF):
        try:
            ds._rev(ref)
        except ds.GitError:
            return
    rec = ds.classify(PREDECESSOR_REF, SNAPSHOT_REF)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ds.main([
            "--base", PREDECESSOR_REF,
            "--head", SNAPSHOT_REF,
            "--require-substantive",
        ])
    assert rc == 2
    assert "product_work=False" in buf.getvalue()
