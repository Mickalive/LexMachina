"""Tests for the product-owned generative-audit seam (``product/query/audit_seam.py``).

The seam must (a) raise only the live adversarial wall-clock budget,
(b) leave fixture/offline behaviour identical, (c) record exactly what it
changed, and (d) be idempotent so importing the pipeline twice cannot stack
wrappers.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (
    str(ROOT / "product"),
    str(ROOT),
    str(ROOT / "frontier" / "frontier-generative-audit"),
    str(ROOT / "frontier" / "frontier-query-retrieval"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from generative_audit import adversarial as adv_mod  # noqa: E402
from generative_audit import paths  # noqa: E402

from query import audit_seam  # noqa: E402


def test_seam_raises_live_adversarial_budget_and_records_it():
    info = audit_seam.apply()
    assert info["applied"] is True
    assert info["adversarial_timeout_default_before"] == 60.0
    assert info["adversarial_timeout_seconds"] == 180.0
    assert "counter-authority" in info["reason"] and "60s" in info["reason"]

    instance = adv_mod.AdversarialPass(None, "answer text", fixture_mode=True)
    assert instance.timeout == 180.0


def test_explicit_caller_timeout_still_wins():
    audit_seam.apply()
    instance = adv_mod.AdversarialPass(None, "answer", fixture_mode=True, timeout=42.0)
    assert instance.timeout == 42.0


def test_env_override_is_clamped(monkeypatch):
    monkeypatch.setenv("LEX_ADVERSARIAL_TIMEOUT_SECONDS", "15")
    assert audit_seam.adversarial_timeout_seconds() == 30.0  # clamp floor
    monkeypatch.setenv("LEX_ADVERSARIAL_TIMEOUT_SECONDS", "240")
    assert audit_seam.adversarial_timeout_seconds() == 240.0
    monkeypatch.delenv("LEX_ADVERSARIAL_TIMEOUT_SECONDS")
    assert audit_seam.adversarial_timeout_seconds() == 180.0


def test_seam_pins_verified_free_model_order():
    """The pinned order must lead with a live model and contain no dead one.

    Regression for the ~316-469 s full-answer latency band (direction v49):
    the 2026-10-14 order led the adversarial fallback chain with
    nemotron-3-ultra, which control-plane ``state/model_health.json`` reports
    FAIL (exit 124) — the newest snapshot run 38938748669, 2026-10-16T17:22:22Z,
    as recomputed by the audit for run 38933507133.  (This docstring previously
    cited "run 38919946016", which exists nowhere in the repository; corrected
    in cycle 38939730386.)  Every dead entry left in the list burns a full
    provider timeout before the next model is tried.
    """
    info = audit_seam.apply()
    assert info["model_order"][0] == "opencode/mimo-v2.6-flash-free"
    assert list(paths.DEFAULT_FREE_MODELS) == audit_seam.MODEL_ORDER
    assert not (set(audit_seam.MODEL_ORDER) & set(audit_seam.KNOWN_DEAD_MODELS))


def test_seam_order_matches_oct16_healthy_pool():
    """The pinned order is the frozen fallback order for the current pool.

    Precision note (cycle 38939730386): mimo, space-bunny and longcat are the
    probe-verified healthy models; ``muse-spark`` is retained as an unprobed
    last-resort entry (control-plane probe stops at ``MAX_HEALTHY=4`` — audit
    observation O1, inherited from the base), not as a verified PASS.
    """
    assert list(audit_seam.MODEL_ORDER) == [
        "opencode/mimo-v2.6-flash-free",
        "opencode/space-bunny-free",
        "opencode/longcat-2.5-preview-free",
        "opencode/muse-spark-1.3-contributor-free",
    ]


def test_seam_is_idempotent():
    first = audit_seam.apply()
    wrapped_once = adv_mod.AdversarialPass.__init__
    second = audit_seam.apply()
    assert first == second
    assert adv_mod.AdversarialPass.__init__ is wrapped_once


def test_pipeline_applies_seam_and_exports_provenance():
    import query.pipeline as pipeline
    assert pipeline.AUDIT_SEAM["applied"] is True
    assert pipeline.AUDIT_SEAM["adversarial_timeout_seconds"] == audit_seam.adversarial_timeout_seconds()


def test_seam_survives_a_second_module_identity(monkeypatch):
    """Regression for run 38766812030 (collection KeyError: 'timeout').

    The suite loads the product tree under two module identities: ``query.*``
    (tests insert ``product/`` on sys.path) and ``product.query.*`` (package
    imports, used by product/tests/test_cache_non_orphan.py and any host that
    imports the app as a package).  The seam's idempotence state lives on the
    module object, so a fresh identity used to re-enter apply() while
    ``AdversarialPass.__init__`` was already wrapped, and
    ``inspect.signature`` then saw the wrapper's ``(*args, **kwargs)`` instead
    of ``timeout``.  The second application must record the same provenance,
    keep the pristine default and must NOT stack another wrapper.
    """
    audit_seam.apply()  # ensure the target is wrapped at least once
    wrapped_once = adv_mod.AdversarialPass.__init__
    monkeypatch.setattr(audit_seam, "_APPLIED", None)  # fresh module identity

    info = audit_seam.apply()

    assert info["applied"] is True
    assert info["already_wrapped_by_other_module_instance"] is True
    assert info["adversarial_timeout_default_before"] == 60.0
    assert info["adversarial_timeout_seconds"] == 180.0
    assert adv_mod.AdversarialPass.__init__ is wrapped_once, "seam stacked a second wrapper"

    instance = adv_mod.AdversarialPass(None, "answer", fixture_mode=True)
    assert instance.timeout == 180.0


# --- Dead-model filtering at call time (direction v49 durable-override fix) ---

# The durable reality-check workflow's post-seam model-list override.
# Kept as a literal here so the override can be simulated without a subprocess;
# parity with the workflow file itself is enforced fail-closed by
# test_reality_check.py::test_workflow_model_override_matches_durable_workflow,
# so this list going stale fails the suite instead of silently diverging.
_WORKFLOW_OVERRIDE = [
    "opencode/nemotron-3-ultra-free",
    "opencode/nemotron-3.5-lightning-free",
    "opencode/space-bunny-free",
    "opencode/mimo-v2.6-flash-free",
]


def test_healthy_models_filters_dead_after_workflow_override():
    """Simulate the durable workflow's post-seam model-list override.

    The workflow re-assigns DEFAULT_FREE_MODELS with the two nemotron models
    first.  The seam's call-time wrapper must filter out only the models in
    KNOWN_DEAD_MODELS (currently nemotron-3.5-lightning-free on adversarial-
    budget grounds; nemotron-3-ultra-free is now healthy per control-plane
    run 39239945934).
    """
    audit_seam.apply()
    saved = list(paths.DEFAULT_FREE_MODELS)
    try:
        paths.DEFAULT_FREE_MODELS[:] = list(_WORKFLOW_OVERRIDE)
        result = paths.healthy_models()
        # nemotron-3-ultra-free is now healthy; only nemotron-3.5-lightning-free is filtered
        assert result == [
            "opencode/nemotron-3-ultra-free",
            "opencode/space-bunny-free",
            "opencode/mimo-v2.6-flash-free",
        ]
        assert not (set(result) & set(audit_seam.KNOWN_DEAD_MODELS))
    finally:
        paths.DEFAULT_FREE_MODELS[:] = saved


def test_preferred_model_never_returns_dead_after_override():
    """preferred_model() must not lead with a dead model after the override."""
    audit_seam.apply()
    saved = list(paths.DEFAULT_FREE_MODELS)
    try:
        paths.DEFAULT_FREE_MODELS[:] = list(_WORKFLOW_OVERRIDE)
        chosen = paths.preferred_model()
        assert chosen not in audit_seam.KNOWN_DEAD_MODELS
        # nemotron-3-ultra-free is now the first healthy survivor
        assert chosen == "opencode/nemotron-3-ultra-free"
    finally:
        paths.DEFAULT_FREE_MODELS[:] = saved


def test_filtering_falls_back_to_model_order_when_all_dead():
    """If every configured model is dead, fall back to the verified healthy list."""
    audit_seam.apply()
    saved = list(paths.DEFAULT_FREE_MODELS)
    try:
        paths.DEFAULT_FREE_MODELS[:] = sorted(audit_seam.KNOWN_DEAD_MODELS)
        result = paths.healthy_models()
        assert result == list(audit_seam.MODEL_ORDER)
        assert paths.preferred_model() == audit_seam.MODEL_ORDER[0]
    finally:
        paths.DEFAULT_FREE_MODELS[:] = saved


def test_dead_model_wrapping_is_idempotent_across_module_identities(monkeypatch):
    """A second module identity must not stack healthy_models/preferred_model wrappers."""
    audit_seam.apply()
    healthy_once = paths.healthy_models
    preferred_once = paths.preferred_model
    monkeypatch.setattr(audit_seam, "_APPLIED", None)

    info = audit_seam.apply()

    assert info["applied"] is True
    assert info["healthy_models_wrapped"] is False  # already wrapped by the other identity
    assert info["preferred_model_wrapped"] is False
    assert paths.healthy_models is healthy_once, "seam stacked a second healthy_models wrapper"
    assert paths.preferred_model is preferred_once, "seam stacked a second preferred_model wrapper"

    # The single wrapper still filters dead models correctly.
    saved = list(paths.DEFAULT_FREE_MODELS)
    try:
        paths.DEFAULT_FREE_MODELS[:] = list(_WORKFLOW_OVERRIDE)
        assert set(paths.healthy_models()) & set(audit_seam.KNOWN_DEAD_MODELS) == set()
    finally:
        paths.DEFAULT_FREE_MODELS[:] = saved


# --- Exclusion basis vs the control-plane health snapshot (optional drift guard,
# recommended by the independent audit of cycle 38933925523) ----------------

def _load_control_plane_health() -> dict | None:
    """Best-effort read of control-plane ``state/model_health.json``.

    Checked in order: ``LEX_MODEL_HEALTH_PATH`` (how the non-vacuity fixtures
    point at their own copy), the file as it exists on this branch, then
    ``origin/main`` via ``git show`` — the control-plane file lives on ``main``
    and is deliberately absent from ``lab/product`` checkouts, so the test must
    be able to read it without requiring a merge.  Returns ``None`` when none
    is readable; the caller then skips rather than pretending to have checked.
    """
    raw = os.environ.get("LEX_MODEL_HEALTH_PATH", "")
    candidates = [Path(raw)] if raw else []
    candidates.append(ROOT / "state" / "model_health.json")
    for path in candidates:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(data, dict):
                return data
    try:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "show", "origin/main:state/model_health.json"],
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def test_known_dead_models_agree_with_control_plane_health():
    """No exclusion may contradict what the health snapshot actually reports.

    The independent audit of cycle 38933925523 found this file asserting, as
    machine-readable load-bearing provenance, that a nonexistent snapshot
    (``run 38919946016``) proved ``nemotron-3.5-lightning-free`` dead while the
    only real control-plane snapshot reports it PASS.  Two fail-closed checks
    prevent both halves of that defect recurring:

    1. every recorded exclusion basis must equal the snapshot's probe result
       for that model (a health refresh flips the recorded value -> failure),
       and a PASS-probed model may only stay excluded under a basis that is
       explicitly *not* tool-health;
    2. every model the snapshot reports FAIL (exit 124) that also sits in the
       pinned ``MODEL_ORDER`` fallback must be excluded — a refreshed dead
       model cannot silently re-enter the hot path.

    Skips (never silently passes) when no health snapshot is readable.
    """
    snapshot = _load_control_plane_health()
    if snapshot is None:
        pytest.skip("control-plane state/model_health.json not readable here")

    probes = {
        p.get("model"): p
        for p in snapshot.get("probe_results", [])
        if isinstance(p, dict) and p.get("model")
    }

    # 1a. recorded basis agrees with the snapshot probe, per excluded model.
    for model, basis in audit_seam.DEAD_MODEL_JUSTIFICATION.items():
        probe = probes.get(model)
        if probe is None:
            continue  # not probed (probe is capped) -> snapshot says nothing
        assert basis["control_plane_tool_probe"] == probe.get("tool_probe"), (
            f"{model}: seam records tool_probe "
            f"{basis['control_plane_tool_probe']!r} but the control-plane "
            f"snapshot (run {snapshot.get('last_checked_run_id')}) reports "
            f"{probe.get('tool_probe')!r} — update DEAD_MODEL_JUSTIFICATION "
            f"or the exclusion itself, never the claim alone"
        )
        if probe.get("tool_probe") == "FAIL":
            assert basis["control_plane_exit_code"] == probe.get("exit_code")
            assert model in audit_seam.KNOWN_DEAD_MODELS
        else:
            # PASS (or anything not FAIL): health does not justify exclusion,
            # so the recorded basis must say it is not tool-health based.
            assert basis["basis"] != "control_plane_tool_probe_fail", (
                f"{model}: excluded as a tool-probe failure while the "
                f"control-plane snapshot reports {probe.get('tool_probe')} "
                f"exit {probe.get('exit_code')}"
            )
            assert basis.get("control_plane_reported_healthy") is True, (
                f"{model}: exclusion must record explicitly that the newest "
                f"control-plane snapshot does NOT report it dead"
            )

    # 1b. the claims themselves are complete: an excluded model's record must
    # exist (KNOWN_DEAD_MODELS is derived from DEAD_MODEL_JUSTIFICATION, this
    # guards the derivation against being hand-broken).
    assert audit_seam.KNOWN_DEAD_MODELS == frozenset(audit_seam.DEAD_MODEL_JUSTIFICATION)

    # 2. a snapshot-FAIL(124) model must never sit in the pinned fallback order.
    for model in audit_seam.MODEL_ORDER:
        probe = probes.get(model)
        if probe and probe.get("tool_probe") == "FAIL" and probe.get("exit_code") == 124:
            raise AssertionError(
                f"{model} is reported dead (exit 124) by the control-plane "
                f"snapshot yet still sits in MODEL_ORDER — it would be handed "
                f"to every fallback chain as a healthy candidate"
            )
