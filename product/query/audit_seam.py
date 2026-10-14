"""Product-owned seam around the accepted generative-audit contract.

Why a seam instead of editing the Frontier component
----------------------------------------------------
``frontier/frontier-generative-audit`` is accepted evidence and sits outside
product write scope.  Two product-level knobs it deliberately leaves to its
caller were miscalibrated for the *current* healthy free-model pool:

1. **Adversarial wall-clock budget.** ``AdversarialPass`` defaults to 60 s per
   model attempt.  That default was tuned when ``opencode/space-bunny-free``
   (since removed from the healthy pool) routinely finished the bounded
   24-decision challenge inside the ceiling; the component's own comment
   records that lightning and ultra both hit 60 s on the same prompt.  On
   2026-10-14 every healthy model hit the ceiling (local rent-default leg,
   ``results/product/reality_check/``), which makes the *whole* reality leg
   fail even when the generated answer itself is correct.  Product spec §9A
   explicitly allows counter-authority updates to arrive later, so the fix is
   a larger budget, not a smaller prompt.

2. **Model ordering when the control-plane health snapshot is absent.**
   ``paths.healthy_models()`` falls back to ``DEFAULT_FREE_MODELS`` when
   ``state/model_health.json`` is not on the branch (it is a control-plane
   file and is deliberately not inside product write scope).  The fallback
   order is then the only lever, so the seam pins the order the factory health
   snapshot verified.

Everything the seam changes is recorded in bundle provenance under
``product_audit_seam`` so the independent auditor can see it rather than infer
it.  Fixture/offline mode is untouched: the same 60 s default only ever applied
to live subprocess calls.
"""
from __future__ import annotations

import inspect
import os
from typing import Any

DEFAULT_ADVERSARIAL_TIMEOUT_SECONDS = 180.0

#: Order verified by the 2026-10-14T13:50Z free-model health snapshot
#: (``/tmp/lex_control/state/model_health.json``: ultra, mimo, space-bunny, longcat).
MODEL_ORDER = [
    "opencode/nemotron-3-ultra-free",
    "opencode/mimo-v2.6-flash-free",
    "opencode/space-bunny-free",
    "opencode/longcat-2.5-preview-free",
]

_APPLIED: dict[str, Any] | None = None


def adversarial_timeout_seconds() -> float:
    raw = os.environ.get("LEX_ADVERSARIAL_TIMEOUT_SECONDS", "")
    try:
        value = float(raw) if raw else DEFAULT_ADVERSARIAL_TIMEOUT_SECONDS
    except ValueError:
        value = DEFAULT_ADVERSARIAL_TIMEOUT_SECONDS
    return max(30.0, value)


def apply() -> dict[str, Any]:
    """Install the seam (idempotent) and describe what it changed."""
    global _APPLIED
    if _APPLIED is not None:
        return dict(_APPLIED)

    from generative_audit import adversarial as adv_mod
    from generative_audit import paths

    original_init = adv_mod.AdversarialPass.__init__
    before_timeout = float(inspect.signature(original_init).parameters["timeout"].default)

    def _init_with_budget(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", adversarial_timeout_seconds())
        original_init(self, *args, **kwargs)

    adv_mod.AdversarialPass.__init__ = _init_with_budget  # type: ignore[method-assign]

    previous_order = list(paths.DEFAULT_FREE_MODELS)
    paths.DEFAULT_FREE_MODELS[:] = list(MODEL_ORDER)

    _APPLIED = {
        "applied": True,
        "adversarial_timeout_seconds": adversarial_timeout_seconds(),
        "adversarial_timeout_default_before": before_timeout,
        "model_order": list(MODEL_ORDER),
        "model_order_before": previous_order,
        "reason": (
            "counter-authority pass exceeded the 60s per-model ceiling on every "
            "healthy free model; product spec 9A allows late counter-authority "
            "updates, so the budget is raised rather than the evidence reduced"
        ),
    }
    return dict(_APPLIED)


def status() -> dict[str, Any]:
    return dict(_APPLIED) if _APPLIED else {"applied": False}


__all__ = ["apply", "status", "adversarial_timeout_seconds",
           "DEFAULT_ADVERSARIAL_TIMEOUT_SECONDS", "MODEL_ORDER"]
