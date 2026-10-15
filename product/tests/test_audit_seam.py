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
    info = audit_seam.apply()
    assert info["model_order"][0] == "opencode/nemotron-3-ultra-free"
    assert list(paths.DEFAULT_FREE_MODELS) == audit_seam.MODEL_ORDER


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
