"""Tests for the product-owned generative-audit seam (``product/query/audit_seam.py``).

The seam must (a) raise only the live adversarial wall-clock budget,
(b) leave fixture/offline behaviour identical, (c) record exactly what it
changed, and (d) be idempotent so importing the pipeline twice cannot stack
wrappers.
"""
from __future__ import annotations

import sys
from pathlib import Path

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
    nemotron-3-ultra, which the 2026-10-16 health snapshot (run 38919946016)
    proves dead (tool probe exit 124).  Every dead entry left in the list
    burns a full provider timeout before the next model is tried.
    """
    info = audit_seam.apply()
    assert info["model_order"][0] == "opencode/mimo-v2.6-flash-free"
    assert list(paths.DEFAULT_FREE_MODELS) == audit_seam.MODEL_ORDER
    assert not (set(audit_seam.MODEL_ORDER) & set(audit_seam.KNOWN_DEAD_MODELS))


def test_seam_order_matches_oct16_healthy_pool():
    """The pinned order is exactly the snapshot-verified healthy pool."""
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

# Exact list the durable reality-check workflow writes into
# paths.DEFAULT_FREE_MODELS after the seam runs (workflow lines 63-67).
_WORKFLOW_OVERRIDE = [
    "opencode/nemotron-3-ultra-free",
    "opencode/nemotron-3.5-lightning-free",
    "opencode/space-bunny-free",
    "opencode/mimo-v2.6-flash-free",
]


def test_healthy_models_filters_dead_after_workflow_override():
    """Simulate the durable workflow's post-seam model-list override.

    The workflow re-assigns DEFAULT_FREE_MODELS with the two dead models
    first.  The seam's call-time wrapper must filter them out so the product
    never burns a provider timeout on a model the health snapshot proved dead.
    """
    audit_seam.apply()
    saved = list(paths.DEFAULT_FREE_MODELS)
    try:
        paths.DEFAULT_FREE_MODELS[:] = list(_WORKFLOW_OVERRIDE)
        result = paths.healthy_models()
        assert result == ["opencode/space-bunny-free", "opencode/mimo-v2.6-flash-free"]
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
        assert chosen == "opencode/space-bunny-free"  # first survivor of the override
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
