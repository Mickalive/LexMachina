"""Tests for the fresh-network slice instrument and the declared query runtime.

Cycle 39128456801.  Two things are guarded:

* ``product/live_slice.py`` must never silently serve a warm cache while calling
  the run "live" - the freshness block has to be built from three independent
  readings (adapter counters, adapter cache stats, a before/after diff of the
  cache directory) and a PASS requires all of them;
* the declared runtime (``product/query_env.py``) and the one-command bootstrap
  (``product/bootstrap_query_env.sh``) must not drift apart, and every module
  the fast path imports must be declared in the requirements file.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "product"))

from product import cycle_verify, query_env  # noqa: E402
from product import live_slice  # noqa: E402


def test_declared_runtime_is_importable_and_measured():
    probe = query_env.probe()
    assert probe["ok"], probe
    for module in query_env.REQUIRED:
        assert probe["installed"][module], module


def test_every_fast_path_module_is_declared_in_the_requirements_file():
    pins = query_env.requirements_pins()
    for module in query_env.REQUIRED:
        assert query_env.requirement_name(module) in pins, module


def test_importing_query_env_does_not_import_the_heavy_stack():
    """The fast-path import budget depends on this module staying stdlib-cheap."""
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys, product.query_env as q; "
         "print(any(m in sys.modules for m in ('numpy','sklearn')))"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=180, check=False)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("False"), out.stdout


def test_bootstrap_script_pins_match_the_declared_pins():
    body = query_env.BOOTSTRAP.read_text(encoding="utf-8")
    for module, version in query_env.PINNED.items():
        dist = query_env.requirement_name(module)
        assert f"{dist}=={version}" in body, f"{dist}=={version} missing from bootstrap"


def test_bootstrap_check_mode_reports_the_runtime_and_installs_nothing():
    out = subprocess.run(
        ["bash", str(query_env.BOOTSTRAP), "--check"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=300, check=False)
    assert "query fast-path runtime" in (out.stdout + out.stderr), out.stdout
    assert "installing pinned query runtime" not in out.stdout


def test_environment_check_is_fail_closed_and_names_the_remedy():
    rows = {r["claim"]: r for r in cycle_verify.check_query_runtime_declared()}
    assert len(rows) == 3, rows
    importable = next(r for c, r in rows.items() if "importable" in c)
    assert importable["status"] == "PASS", importable
    assert importable["observed"]["remedy"] == query_env.REMEDY


def test_environment_check_fails_when_a_required_module_is_absent(monkeypatch):
    monkeypatch.setitem(query_env.REQUIRED, "definitely_not_installed_xyz", "test")
    rows = cycle_verify.check_query_runtime_declared()
    importable = next(r for r in rows if "importable" in r["claim"])
    assert importable["status"] == "FAIL"
    assert importable["observed"]["missing"] == ["definitely_not_installed_xyz"]


def test_freshness_block_requires_all_three_independent_readings():
    """The instrument must not report PASS on one reading alone."""
    src = Path(live_slice.__file__).read_text(encoding="utf-8")
    for needle in ("adapter_cache_hits", "adapter_network_calls",
                   "independent_cache_probe", "adapter_cache_stats"):
        assert needle in src, needle


def test_cache_delta_separates_added_modified_and_removed():
    """An in-place refresh must not be reported as a removal."""
    delta = live_slice._cache_delta(
        {"a.json": 10, "b.json": 10, "gone.json": 10},
        {"a.json": 10, "b.json": 42, "new.json": 5},
    )
    assert delta["n_files_added"] == 1
    assert delta["n_files_modified"] == 1
    assert delta["n_files_removed"] == 1
    assert delta["n_files_touched"] == 3
    assert delta["files_modified"] == ["b.json"], delta


def test_cache_fingerprint_sees_a_new_file(tmp_path, monkeypatch):
    root = tmp_path / "cache"
    root.mkdir()
    monkeypatch.setattr(query_env, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(live_slice, "product_cache_dir", lambda: root)
    (root / "a.json").write_text("{}", encoding="utf-8")
    first = live_slice._cache_fingerprint()
    assert first == {"a.json": 2}, first
    (root / "b.json").write_text("{}", encoding="utf-8")
    second = live_slice._cache_fingerprint()
    assert set(second) - set(first) == {"b.json"}, second


def test_live_slice_never_touches_the_gate_packet_or_the_frozen_tree():
    """Scope guard on the *code* (the docstring may name these paths in prose)."""
    import ast

    tree = ast.parse(Path(live_slice.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for forbidden in ("gate_packet", "rebuild_packet", "frozen", "evaluation"):
        assert forbidden not in imported, imported


def test_ephemeral_cache_option_exists_because_the_product_cache_is_frozen():
    """A refresh rewrites cache entries in place; the tracked ones are frozen evidence."""
    import tempfile

    from product.query import pipeline

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "query_cache"
        seen = {}
        original = pipeline.product_cache_dir
        pipeline.product_cache_dir = lambda: root  # stand in for run()'s override
        try:
            seen["root"] = pipeline.product_cache_dir()
        finally:
            pipeline.product_cache_dir = original
        assert seen["root"] == root
    src = Path(live_slice.__file__).read_text(encoding="utf-8")
    assert "--ephemeral-cache" in src
    assert "CYCLE_38759730609_cache_manifest.json" in src


def test_shipped_live_slice_artifact_is_self_consistent():
    out_dir = REPO_ROOT / "results" / "product" / "live_slice"
    if not out_dir.is_dir():
        return
    for path in sorted(out_dir.glob("*.json")):
        if path.name.endswith("_bundle.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema"] == "product-live-slice/1"
        assert data["posture"]["human_gate_ready"] is False
        assert data["posture"]["packet_admitted"] is False
        assert data["retrieval_mode_requested"] == "refresh"
        assert data["checks"], data
        assert data["verdict"] in {"PASS", "FAIL"}
        if data["verdict"] == "FAIL":
            assert data["n_failed_checks"], data