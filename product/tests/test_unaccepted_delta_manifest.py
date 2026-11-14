"""Bounds for the unaccepted-delta manifest instrument.

The manifest is an inventory, not a verdict: these tests pin that it is
deterministic, that it separates product code from generated evidence, and
that it fails closed on an empty or non-fast-forward diff.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from product import unaccepted_delta_manifest as udm  # noqa: E402

ACCEPTED = "7be4480e"
SNAPSHOT = "5de296f8"


def _has(rev: str) -> bool:
    proc = subprocess.run(["git", "cat-file", "-e", f"{rev}^{{commit}}"],
                          cwd=str(ROOT), capture_output=True, text=True)
    return proc.returncode == 0


@pytest.mark.skipif(not (_has(ACCEPTED) and _has(SNAPSHOT)),
                    reason="accepted/snapshot commits are not local objects")
def test_manifest_separates_code_from_generated_evidence():
    m = udm.build_manifest(ACCEPTED, SNAPSHOT)
    assert m["schema"] == "product-unaccepted-delta-manifest/1"
    assert m["base_commit"].startswith(ACCEPTED)
    assert m["head_commit"].startswith(SNAPSHOT)
    assert m["merge_base"] == m["base_commit"]
    assert m["changed_files"] == 314
    assert m["by_status"] == {"A": 167, "M": 147}
    assert m["by_top_level"] == {
        "product": 20, "reports": 7, "results": 286, "state": 1,
    }
    assert m["deleted_paths"] == []

    code = {r["path"]: r["status"] for r in m["product_code_paths"]}
    assert code["product/query_app.py"] == "M"
    assert code["product/fetch_run_jobs_snapshot.py"] == "A"
    assert "product/tests/" not in "".join(code), (
        "product_code_paths must exclude test paths")
    tests = {r["path"] for r in m["test_paths"]}
    assert "product/tests/test_query_app_stage_guard.py" in tests
    assert m["generated_results"]["n_paths"] == 286
    assert "INVENTORY ONLY" in m["claim_ceiling"]


@pytest.mark.skipif(not (_has(ACCEPTED) and _has(SNAPSHOT)),
                    reason="accepted/snapshot commits are not local objects")
def test_manifest_is_deterministic():
    assert udm.build_manifest(ACCEPTED, SNAPSHOT) == (
        udm.build_manifest(ACCEPTED, SNAPSHOT))


@pytest.mark.skipif(not (_has(ACCEPTED) and _has(SNAPSHOT)),
                    reason="accepted/snapshot commits are not local objects")
def test_cli_check_passes_on_a_real_delta(tmp_path: Path):
    out = tmp_path / "manifest.json"
    rc = udm.main(["--base", ACCEPTED, "--head", SNAPSHOT,
                   "--out", str(out), "--check"])
    assert rc == 0
    assert json.loads(out.read_text())["changed_files"] == 314


def test_cli_fails_closed_on_empty_delta(tmp_path: Path):
    rc = udm.main(["--base", "HEAD", "--head", "HEAD",
                   "--out", str(tmp_path / "empty.json"), "--check"])
    assert rc == 1
    assert json.loads((tmp_path / "empty.json").read_text())["changed_files"] == 0
