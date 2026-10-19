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

3. **Dead-model filtering at call time (robust to external override).**
   Pinning ``DEFAULT_FREE_MODELS`` at apply time is necessary but not
   sufficient: the durable reality-check workflow re-assigns
   ``paths.DEFAULT_FREE_MODELS`` *after* the seam runs, listing
   ``nemotron-3-ultra-free`` (control-plane tool probe FAIL, exit 124) and
   ``nemotron-3.5-lightning-free`` first.  Every excluded entry left in the
   list becomes a fallback candidate that burns a full provider timeout
   (120 s answer / 180 s adversarial) before the next model is tried — the
   observed ~316-469 s full-answer latency band, and a direct breach of the
   300 s gate.  The seam therefore also wraps ``paths.healthy_models`` and
   ``paths.preferred_model`` so ``KNOWN_DEAD_MODELS`` are filtered out at
   call time, no matter what the caller last wrote into
   ``DEFAULT_FREE_MODELS``.  If filtering would empty the list, the wrapper
   falls back to ``MODEL_ORDER`` so a healthy model is always available.
   The two exclusions are **not** asserted to share one cause: each carries
   its own machine-readable basis in ``DEAD_MODEL_JUSTIFICATION`` (see
   below), because ``nemotron-3.5-lightning-free`` is *not* dead by tool
   probe — the newest control-plane snapshot reports it PASS.

Everything the seam changes is recorded in bundle provenance under
``product_audit_seam`` so the independent auditor can see it rather than infer
it.  Fixture/offline mode is untouched: the same 60 s default only ever applied
to live subprocess calls.
"""
from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_ADVERSARIAL_TIMEOUT_SECONDS = 180.0

#: Pinned fallback order for the current healthy free-model pool.
#:
#: Correction (cycle 38939730386, repair r1 of 38933925523): the original
#: comment here claimed a health snapshot "run 38919946016" proved four models
#: PASS and both nemotron models FAIL.  That run id does not exist anywhere in
#: this repository (no commit, tag, ref or blob), and the only model-health
#: artifact — control-plane ``state/model_health.json`` — says something
#: different.  Verified facts, per that artifact (newest snapshot run
#: 38938748669, ``last_checked_at`` 2026-10-16T17:22:22Z, on ``origin/main``
#: a16603c; the audit recomputed the immediately preceding run 38933507133 at
#: 16:40:57Z with the same probe results):
#:
#: * ``mimo-v2.6-flash-free``, ``space-bunny-free``, ``longcat-2.5-preview-free``
#:   — tool_probe PASS, exit 0 (probe-verified healthy);
#: * ``nemotron-3.5-lightning-free`` — tool_probe **PASS**, exit 0, and listed
#:   in ``healthy_models`` (NOT dead by tool probe);
#: * ``nemotron-3-ultra-free`` — tool_probe FAIL, exit 124 (the only FAIL);
#: * ``muse-spark-1.3-contributor-free`` — not probed at all (the control-plane
#:   probe stops at ``MAX_HEALTHY=4``), kept only as a last-resort fallback —
#:   independent audit observation O1, inherited from the base.
#:
#: Dead/excluded models are EXCLUDED, not demoted: ``healthy_models()`` returns
#: this list verbatim when the control-plane snapshot is absent from the branch,
#: so every excluded entry left in the list becomes a fallback candidate that
#: burns a full provider timeout (120 s answer / 180 s adversarial) before the
#: next model is tried.  Two such burns explain the observed ~316-469 s
#: full-answer latency band.
MODEL_ORDER = [
    "opencode/mimo-v2.6-flash-free",
    "opencode/space-bunny-free",
    "opencode/longcat-2.5-preview-free",
    "opencode/muse-spark-1.3-contributor-free",
]

#: Per-exclusion evidence.  Models excluded from every fallback chain keep the
#: **actual** basis for their exclusion machine-readable so no blanket
#: "proved dead" claim can drift away from its evidence again (the defect the
#: independent audit of cycle 38933925523 found in the previous wording of
#: this file).
#:
#: ``opencode/nemotron-3-ultra-free`` — **no longer excluded**: the newest
#: control-plane snapshot (run 39245649011, 2026-10-19T11:37:15Z) reports
#: tool_probe PASS / exit 0.  The previous exclusion (basis:
#: control_plane_tool_probe_fail, run 38938748669) was correct for that
#: snapshot; this update reflects the health refresh.  The model is not in
#: MODEL_ORDER and remains absent from the fallback chain by construction.
#:
#: ``opencode/nemotron-3.5-lightning-free`` — excluded on **two** grounds:
#: (a) adversarial-budget / hot-path-latency — the frontier component's own
#: comment records lightning hitting the 60 s bounded-challenge ceiling while
#: space-bunny completed
#: (``frontier/frontier-generative-audit/generative_audit/adversarial.py``:130-133),
#: and the only in-repo reality leg where lightning acted as ``answer_model``
#: (``results/product/reality_check/rent-default_live_20261014T113201Z.json``)
#: recorded ``timeout after 60s`` on the adversarial call and 281.065 s total
#: against the 300 s gate — a single confounded observation, cited as
#: observation and not as cause.  Both observations predate this seam's 180 s
#: budget; no committed artifact shows lightning completing the bounded
#: adversarial pass under the new budget, so the exclusion is conservative and
#: revocable: re-probe before treating it as permanent (carried as a product
#: backlog item in ``state/product.json``).  Three probe-verified healthy
#: models remain, so the exclusion costs no fallback depth the latency gate
#: can afford.
#: (b) tool health — the newest control-plane snapshot (run 39245649011,
#: 2026-10-19T11:37:15Z) reports tool_probe FAIL / exit 124 for this model.
#:
#: ``control_plane_tool_probe`` mirrors what the newest control-plane snapshot
#: reports for that model, so a health refresh that flips a probe result
#: without this record being updated is a test failure
#: (``test_audit_seam.py::test_known_dead_models_agree_with_control_plane_health``),
#: not a silent contradiction.  ``control_plane_run_id`` /
#: ``control_plane_checked_at`` record when the values were read from
#: ``state/model_health.json``; they are provenance, not asserted invariants.
DEAD_MODEL_JUSTIFICATION = {
    "opencode/nemotron-3.5-lightning-free": {
        "basis": "adversarial_budget_and_tool_probe_fail",
        "control_plane_tool_probe": "FAIL",
        "control_plane_exit_code": 124,
        "control_plane_reported_healthy": False,
        "control_plane_run_id": "39245649011",
        "control_plane_checked_at": "2026-10-19T11:37:15Z",
        "note": (
            "Excluded on adversarial-budget grounds (the bounded adversarial "
            "challenge hit its 60s ceiling for this model in the component's "
            "recorded evidence) AND tool health: the newest control-plane "
            "snapshot (run 39245649011, 2026-10-19T11:37:15Z) reports "
            "tool_probe FAIL exit 124.  The previous record mirrored run "
            "39239945934 (PASS); the guard "
            "test_known_dead_models_agree_with_control_plane_health enforces "
            "that this record tracks the newest snapshot, so a health refresh "
            "that flips a probe result is a test failure, not a silent "
            "contradiction."
        ),
    },
}

#: Models excluded from every fallback chain, so a future order refresh cannot
#: silently re-admit them.  Derived from ``DEAD_MODEL_JUSTIFICATION`` (single
#: source of truth: membership and basis cannot diverge).
KNOWN_DEAD_MODELS = frozenset(DEAD_MODEL_JUSTIFICATION)

_APPLIED: dict[str, Any] | None = None


def adversarial_timeout_seconds() -> float:
    raw = os.environ.get("LEX_ADVERSARIAL_TIMEOUT_SECONDS", "")
    try:
        value = float(raw) if raw else DEFAULT_ADVERSARIAL_TIMEOUT_SECONDS
    except ValueError:
        value = DEFAULT_ADVERSARIAL_TIMEOUT_SECONDS
    return max(30.0, value)


def control_plane_health_snapshot() -> dict[str, Any] | None:
    """Read control-plane ``state/model_health.json`` when it is readable.

    Read-only, no subprocess, never raises: returns ``None`` when the
    control-plane file is absent from this branch (the normal case for a
    ``lab/product`` checkout) or unreadable.  When present, the probe results
    for the excluded models are recorded verbatim so every bundle's provenance
    shows *what the health snapshot actually said at apply time* instead of a
    hand-asserted summary — the exact defect the independent audit of cycle
    38933925523 found.  ``LEX_MODEL_HEALTH_PATH`` overrides the location, which
    is how the consistency test exercises it without writing control-plane
    paths.
    """
    raw = os.environ.get("LEX_MODEL_HEALTH_PATH", "")
    if raw:
        path = Path(raw)
    else:
        path = Path(__file__).resolve().parents[2] / "state" / "model_health.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    probes = {
        p.get("model"): {
            "tool_probe": p.get("tool_probe"),
            "exit_code": p.get("exit_code"),
            "catalog_present": p.get("catalog_present"),
        }
        for p in data.get("probe_results", [])
        if p.get("model")
    }
    return {
        "run_id": data.get("last_checked_run_id"),
        "checked_at": data.get("last_checked_at"),
        "excluded_models": {m: probes.get(m) for m in sorted(KNOWN_DEAD_MODELS)},
    }


def apply() -> dict[str, Any]:
    """Install the seam (idempotent) and describe what it changed.

    Idempotence has to hold across *module identities*, not only across calls
    on one module object.  The suite loads the product tree twice (``query.*``
    via the tests' ``sys.path`` insert and ``product.query.*`` via the package
    path), so ``_APPLIED`` can be None in a freshly imported ``audit_seam``
    while ``generative_audit.adversarial.AdversarialPass.__init__`` is already
    wrapped by the other identity.  Run 38766812030 hit exactly that:
    collection of the new cache-non-orphan test raised ``KeyError: 'timeout'``
    because ``inspect.signature`` saw the wrapper's ``(*args, **kwargs)``
    instead of the original ``timeout`` parameter.  The wrapper therefore
    carries a reference to the pristine ``__init__``, and a second application
    records the same provenance without stacking another wrapper.
    """
    global _APPLIED
    if _APPLIED is not None:
        return dict(_APPLIED)

    from generative_audit import adversarial as adv_mod
    from generative_audit import paths

    current_init = adv_mod.AdversarialPass.__init__
    original_init = getattr(current_init, "_lex_original_init", current_init)
    already_wrapped = original_init is not current_init

    params = inspect.signature(original_init).parameters
    before_timeout = float(params["timeout"].default) if "timeout" in params else None

    if not already_wrapped:

        def _init_with_budget(self: Any, *args: Any, **kwargs: Any) -> None:
            kwargs.setdefault("timeout", adversarial_timeout_seconds())
            original_init(self, *args, **kwargs)

        _init_with_budget._lex_original_init = original_init  # type: ignore[attr-defined]
        adv_mod.AdversarialPass.__init__ = _init_with_budget  # type: ignore[method-assign]

    # --- Dead-model filtering at call time -------------------------------
    # Pinning DEFAULT_FREE_MODELS above is not sufficient: the durable
    # reality-check workflow re-assigns it after this seam runs.  These
    # wrappers filter KNOWN_DEAD_MODELS from the *result* of healthy_models()
    # at call time, so any external override of DEFAULT_FREE_MODELS becomes
    # harmless.  Idempotence uses the same _lex_original sentinel as the
    # __init__ wrapper so a second module identity cannot stack a wrapper.
    current_healthy = paths.healthy_models
    original_healthy = getattr(current_healthy, "_lex_original", current_healthy)
    healthy_already_wrapped = original_healthy is not current_healthy

    if not healthy_already_wrapped:

        def _healthy_models_filtered() -> list[str]:
            models = [m for m in original_healthy() if m not in KNOWN_DEAD_MODELS]
            return models if models else list(MODEL_ORDER)

        _healthy_models_filtered._lex_original = original_healthy  # type: ignore[attr-defined]
        paths.healthy_models = _healthy_models_filtered

    current_preferred = paths.preferred_model
    original_preferred = getattr(current_preferred, "_lex_original", current_preferred)
    preferred_already_wrapped = original_preferred is not current_preferred

    if not preferred_already_wrapped:

        def _preferred_model_safe(fallback: str | None = None) -> str:
            # paths.healthy_models is already the filtered wrapper at this
            # point, so this never returns a dead model.
            models = paths.healthy_models()
            if models:
                return models[0]
            if fallback and fallback not in KNOWN_DEAD_MODELS:
                return fallback
            return MODEL_ORDER[0]

        _preferred_model_safe._lex_original = original_preferred  # type: ignore[attr-defined]
        paths.preferred_model = _preferred_model_safe

    previous_order = list(paths.DEFAULT_FREE_MODELS)
    paths.DEFAULT_FREE_MODELS[:] = list(MODEL_ORDER)

    _APPLIED = {
        "applied": True,
        "adversarial_timeout_seconds": adversarial_timeout_seconds(),
        "adversarial_timeout_default_before": before_timeout,
        "already_wrapped_by_other_module_instance": already_wrapped,
        "model_order": list(MODEL_ORDER),
        "model_order_before": previous_order,
        "healthy_models_wrapped": not healthy_already_wrapped,
        "preferred_model_wrapped": not preferred_already_wrapped,
        "known_dead_models": sorted(KNOWN_DEAD_MODELS),
        # Machine-readable basis per exclusion (fix for the audit finding that
        # a blanket "proved dead" claim hid which model had which evidence),
        # plus the control-plane probe table verbatim when that file is present.
        "dead_model_justification": {
            m: dict(DEAD_MODEL_JUSTIFICATION[m]) for m in sorted(KNOWN_DEAD_MODELS)
        },
        "control_plane_health": control_plane_health_snapshot(),
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
           "control_plane_health_snapshot",
           "DEFAULT_ADVERSARIAL_TIMEOUT_SECONDS", "MODEL_ORDER",
           "KNOWN_DEAD_MODELS", "DEAD_MODEL_JUSTIFICATION"]
