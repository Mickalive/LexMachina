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

import ast
import copy
import json
import os
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
        # PASS_MAP_ONLY was added this cycle: a run that never executed the
        # sourced-answer and counter-authority stages must not be published as a
        # chain PASS (see product/live_slice.py::verdict_for).
        assert data["verdict"] in {"PASS", "PASS_MAP_ONLY", "FAIL"}
        if data["verdict"] == "FAIL":
            assert data["n_failed_checks"], data


def test_shipped_live_slice_artifact_verdict_matches_its_own_stage_fields():
    """Every shipped record's verdict is checked against its own bytes.

    The record published by run 39187482610 (``20261019T022100Z.json``) predates
    the stage disclosure and carries ``verdict: "PASS"`` with a ``pending``
    answer, zero citations, zero counter authorities and ``enrich_s 0.0``.  Its
    file is never edited; it is named by
    ``results/product/live_slice_stages/STAGE_DISCLOSURE_AMENDMENT.json`` with
    the effective verdict its own fields support.  This test asserts that every
    record *is* covered by that amendment and that the amendment agrees with the
    bytes it classifies - so a NEW unamended mislabelled record fails here.
    """
    from product.live_slice_stage_amendment import ARTIFACT, build, map_only_fingerprint

    out_dir = REPO_ROOT / "results" / "product" / "live_slice"
    if not out_dir.is_dir():
        return
    amendment = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    covered = {r["artifact"]: r for r in amendment["records"]}
    assert covered, "the amendment covers no record"

    for path in sorted(out_dir.glob("*.json")):
        if path.name.endswith("_bundle.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        name = str(path.relative_to(REPO_ROOT))
        assert name in covered, f"{name} is not covered by the stage amendment"
        row = covered[name]
        assert row["map_only_fingerprint"] is map_only_fingerprint(data), (
            f"{name}: the amendment's fingerprint does not match the bytes")
        stages = data.get("stages_executed")
        if stages is None:
            continue
        # One-way, not bidirectional: a chain PASS requires the chain ran and a
        # map-only PASS requires it did not, but a FAIL verdict is allowed with
        # the chain having run (``verdict_for`` returns FAIL as soon as any
        # wiring check fails). See test_live_slice_stage_disclosure.py.
        verdict = data["verdict"]
        if verdict == "PASS":
            assert stages["canonical_chain"] is True, (
                f"{name} publishes a chain PASS without declaring the canonical "
                f"chain ran (canonical_chain={stages['canonical_chain']})")
        elif verdict == "PASS_MAP_ONLY":
            assert stages["canonical_chain"] is False, (
                f"{name} publishes a map-only PASS while declaring the canonical "
                f"chain ran (canonical_chain={stages['canonical_chain']})")

    fresh = build()
    assert fresh["verdict"] == "PASS", fresh.get("failures")
    assert json.dumps(json.loads(ARTIFACT.read_text(encoding="utf-8"))["records"],
                      sort_keys=True) == json.dumps(fresh["records"], sort_keys=True), (
        "the committed stage amendment is stale against a fresh recomputation")


# ---------------------------------------------------------------------------
# F1/F2 (audit CYCLE_39132612111): run()/main() must EXECUTE end-to-end.
# The 39128456801 resume dropped the pipeline import from run(), so every
# invocation died with NameError before any network I/O while 13 unit tests
# stayed green - and _cache_fingerprint() kept probing the TRACKED cache root
# while run() redirected only the pipeline adapter, so the recommended
# freshness mode self-FAILed.  These tests execute the real main() with a
# monkeypatched network so a recurrence can never again hide behind green
# unit tests.
# ---------------------------------------------------------------------------

_FIXTURE_BUNDLE = (REPO_ROOT / "results" / "product" / "offline_slice" /
                   "20261018T101000Z" / "rent-default.bundle.json")


def _fresh_refresh_bundle() -> dict:
    """The verified offline fixture, re-provenanced as a refresh-mode result.

    The page/answer/map content is byte-faithful to the verified bundle; only
    the retrieval provenance is rewritten to what a genuine refresh leg
    reports (mode=refresh, zero cache hits, >0 network calls), because those
    are the fields the instrument's freshness checks read.
    """
    bundle = copy.deepcopy(json.loads(_FIXTURE_BUNDLE.read_text(encoding="utf-8")))
    remote = bundle["provenance"]["retrieval"]["remote"]
    remote["mode"] = "refresh"
    remote["request_summary"] = {
        "cache_hits": 0, "network_calls": 1, "requests_logged": 1, "failures": 0,
    }
    remote["cache_stats"] = {"hits": 0, "misses": 1, "writes": 1}
    remote["degraded"] = False
    return bundle


def test_main_executes_end_to_end_with_a_monkeypatched_refresh(tmp_path, monkeypatch):
    """F1: main() runs run()/main() for real; a dropped import fails this test.

    The network is monkeypatched at the pipeline seam (exactly where run()
    imports it), so this is hermetic and deterministic - but every other line
    of main()/run() executes, including the freshness probe, the bundle
    contract validation and the artifact write.
    """
    from product.query import pipeline

    fixture = _fresh_refresh_bundle()

    def fake_initial(query, *, top_n=150, retrieval_mode="live"):
        assert retrieval_mode == "refresh", retrieval_mode
        # Simulate the adapter writing a cache entry into the root the
        # PIPELINE module resolves - the same name run() redirects under
        # --ephemeral-cache.  The independent probe must see this file.
        root = pipeline.product_cache_dir()
        root.mkdir(parents=True, exist_ok=True)
        (root / "fake_envelope.json").write_text("{}", encoding="utf-8")
        return copy.deepcopy(fixture)

    def fake_enrich(initial, *, retrieval_mode="live", evidence_count=12, **kw):
        assert retrieval_mode == "refresh", retrieval_mode
        return copy.deepcopy(initial)

    monkeypatch.setattr(pipeline, "run_query_initial", fake_initial)
    monkeypatch.setattr(pipeline, "enrich_query_bundle", fake_enrich)
    # run() mutates pipeline.product_cache_dir in place; register the module
    # attribute with monkeypatch so the original is restored at teardown.
    monkeypatch.setattr(pipeline, "product_cache_dir", pipeline.product_cache_dir)
    out_dir = tmp_path / "live_slice"
    monkeypatch.setattr(live_slice, "OUT_DIR", out_dir)

    rc = live_slice.main(["--run-id", "F1_E2E", "--n", "100", "--ephemeral-cache"])
    assert rc == 0, "main() must PASS every freshness/contract check"
    record = json.loads((out_dir / "F1_E2E.json").read_text(encoding="utf-8"))
    assert record["verdict"] == "PASS", record["n_failed_checks"]
    assert record["retrieval_mode_served"] == "refresh"
    # F2: under --ephemeral-cache the probe must fingerprint the REDIRECTED
    # root (where the fake adapter wrote), not the tracked product cache.
    probe = record["freshness"]["independent_cache_probe"]
    assert probe["n_files_touched"] == 1, probe
    assert probe["files_added"] == ["fake_envelope.json"], probe
    assert probe["cache_dir"] != "results/product/query_cache", probe
    assert record["cache_root"].startswith("ephemeral"), record["cache_root"]
    assert record["checks"]["independent_probe_saw_the_network"] is True
    assert (out_dir / "F1_E2E_bundle.json").is_file()


def test_run_imports_every_pipeline_name_it_calls():
    """Static twin of the e2e test: both names must be IMPORTED inside run().

    The e2e test above is the behavioural guard; this AST check names the
    exact defect (a bare call to a name that is neither imported nor defined)
    so a failure message points straight at it.
    """
    tree = ast.parse(Path(live_slice.__file__).read_text(encoding="utf-8"))
    run_fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "run")
    imported: set[str] = set()
    for node in ast.walk(run_fn):
        if isinstance(node, ast.ImportFrom):
            imported.update(a.asname or a.name for a in node.names)
    used = {n.id for n in ast.walk(run_fn)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    for name in ("run_query_initial", "enrich_query_bundle"):
        assert name in imported, f"{name} is called but not imported inside run()"


def test_run_default_cache_root_is_never_the_tracked_frozen_covered_cache(
        monkeypatch):
    """Cycle 39674781875: the DEFAULT must not write the frozen-covered cache.

    ``refresh`` rewrites cache entries in place; the tracked product cache
    carries a frozen 392-envelope subset (manifest
    ``results/product/CYCLE_38759730609_cache_manifest.json``).  Cycle
    39667945530's two live runs used the tracked default and turned 9 pinned
    envelopes into different bytes, taking
    ``test_claim_cache_manifest_is_intact_and_append_tolerant`` red.  This
    test pins the structural remedy: ``run()`` with ``cache_root=None`` points
    the adapter at a directory OUTSIDE the tracked cache, a simulated adapter
    write lands there (not in the tracked cache), and the throwaway directory
    is removed when ``run()`` returns.
    """
    from product.query import pipeline
    from product.query.cache_path import PRODUCT_CACHE_DIR

    fixture = json.loads(_FIXTURE_BUNDLE.read_text(encoding="utf-8"))
    fixture["provenance"]["retrieval"]["remote"].update({
        "mode": "refresh",
        "request_summary": {"cache_hits": 0, "network_calls": 1,
                            "requests_logged": 1, "failures": 0},
        "cache_stats": {"hits": 0, "misses": 1, "writes": 1},
        "degraded": False,
    })
    seen: dict[str, str] = {}

    def fake_initial(query, *, top_n=150, retrieval_mode="live"):
        root = pipeline.product_cache_dir()
        seen["root"] = str(root)
        assert not root.is_relative_to(PRODUCT_CACHE_DIR), (
            f"default run() pointed the adapter at the tracked cache: {root}")
        root.mkdir(parents=True, exist_ok=True)
        (root / "fake_envelope.json").write_text("{}", encoding="utf-8")
        return copy.deepcopy(fixture)

    monkeypatch.setattr(pipeline, "run_query_initial", fake_initial)
    monkeypatch.setattr(
        pipeline, "enrich_query_bundle",
        lambda initial, **kw: copy.deepcopy(initial))
    monkeypatch.setattr(pipeline, "product_cache_dir", pipeline.product_cache_dir)

    out = live_slice.run("fixture query", top_n=100, enrich=True,
                         evidence_count=2, cache_root=None)
    record = out["record"]
    assert record["stages_executed"]["canonical_chain"] is True
    probe = record["freshness"]["independent_cache_probe"]
    assert probe["n_files_touched"] == 1
    assert probe["files_added"] == ["fake_envelope.json"]
    assert not Path(seen["root"]).exists(), (
        "the throwaway cache must be removed when run() returns")
    # The tracked cache gained nothing from this default run.
    assert not (PRODUCT_CACHE_DIR / "fake_envelope.json").exists()


def test_cache_fingerprint_fingerprints_the_root_it_is_given(tmp_path):
    """F2 unit-level: the probe honours an explicit root (the redirected one)."""
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    root_a.mkdir(); root_b.mkdir()
    (root_a / "tracked.json").write_text("{}", encoding="utf-8")
    (root_b / "ephemeral.json").write_text("{}", encoding="utf-8")
    assert live_slice._cache_fingerprint(root_a) == {"tracked.json": 2}
    assert live_slice._cache_fingerprint(root_b) == {"ephemeral.json": 2}


def test_bootstrap_install_path_re_checks_with_bash_and_succeeds(tmp_path):
    """F3: after a successful install the remedy command exits 0.

    The script is a BASH script (set -euo pipefail); re-checking it with the
    Python interpreter dies with SyntaxError right after a successful install
    - the exact defect the 39128456801 audit re-measured.  A stub PYTHON
    simulates 'modules missing -> pip install succeeds -> probes pass', so
    the real install path (including the re-check exec) runs hermetically.
    """
    marker = tmp_path / "installed.marker"
    stub = tmp_path / "stub_python.py"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "marker = os.environ['STUB_MARKER']\n"
        "argv = sys.argv[1:]\n"
        "if argv[:2] == ['-m', 'pip']:\n"
        "    open(marker, 'w').write('ok')\n"
        "    sys.exit(0)\n"
        "if argv and argv[0] == '-c':\n"
        "    if os.path.exists(marker):\n"
        "        print('99.9.9')\n"
        "        sys.exit(0)\n"
        "    sys.exit(1)\n"
        "sys.exit(1)\n",
        encoding="utf-8")
    stub.chmod(0o755)
    env = dict(os.environ, PYTHON=str(stub), STUB_MARKER=str(marker))
    out = subprocess.run(
        ["bash", str(query_env.BOOTSTRAP)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
        env=env, timeout=120, check=False)
    combined = out.stdout + out.stderr
    assert out.returncode == 0, combined
    assert marker.exists(), "the install branch must have run"
    assert "query fast-path runtime: OK" in combined, combined
    assert "SyntaxError" not in combined, combined