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

    The workflow re-assigns DEFAULT_FREE_MODELS with the two excluded models
    first (nemotron-3-ultra: tool probe FAIL 124; nemotron-3.5-lightning:
    control-plane PASS but excluded on adversarial-budget grounds — see
    ``DEAD_MODEL_JUSTIFICATION``).  The seam's call-time wrapper must filter
    both out so the product never burns a provider timeout on a fallback the
    exclusion records rule out.
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
    """Every exclusion must remain substantively justified by the live snapshot.

    The independent audit of cycle 38933925523 found this file asserting, as
    machine-readable load-bearing provenance, that a nonexistent snapshot
    (``run 38919946016``) proved ``nemotron-3.5-lightning-free`` dead while the
    only real control-plane snapshot reports it PASS.  Three fail-closed checks
    prevent both halves of that defect recurring, tuned to the SUBSTANCE the
    product depends on (is the model usable?) rather than volatile metadata
    (which non-zero exit code the unusable probe returned):

    1. a ``control_plane_tool_probe_fail`` basis requires the newest snapshot
       to actually report FAIL for that model — a snapshot that reports PASS
       contradicts the stated basis and must fail the test;
    2. a non-tool-health basis may never claim to be a tool-probe failure, and
       must record explicitly that health does not justify the exclusion
       (the record is as-of provenance, disclosed, never narrated away);
    3. no model the newest snapshot reports FAIL (any exit code — 1 and 124
       are the same unusable substance) may sit in the pinned ``MODEL_ORDER``
       fallback, where it would be handed to every fallback chain as healthy.

    Exit codes are deliberately NOT compared as invariants: the same FAILing
    model has been observed with exit 124 (timeout) and exit 1 (upstream
    error) across control-plane refreshes (runs 38938748669 and 38947845257).
    Any as-of divergence between the record and the newest snapshot is instead
    required to ship machine-readably in every bundle's provenance via
    ``dead_model_record_divergence()`` (asserted in
    ``test_apply_ships_the_health_record_divergence``).

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

    for model, basis in audit_seam.DEAD_MODEL_JUSTIFICATION.items():
        probe = probes.get(model)
        if probe is None:
            continue  # not probed (probe is capped) -> snapshot says nothing
        if basis["basis"] == "control_plane_tool_probe_fail":
            assert probe.get("tool_probe") == "FAIL", (
                f"{model}: excluded on the stated basis of a tool-probe failure "
                f"while the control-plane snapshot (run "
                f"{snapshot.get('last_checked_run_id')}) reports "
                f"{probe.get('tool_probe')!r} exit {probe.get('exit_code')} — "
                f"the basis is contradicted; re-probe and re-justify or drop "
                f"the exclusion, never the claim alone"
            )
            assert model in audit_seam.KNOWN_DEAD_MODELS
        else:
            # Health does not justify this exclusion on the record's own
            # terms; the record must say so explicitly — unless the newest
            # snapshot independently reports FAIL, in which case health would
            # justify it as well and the stale PASS record is disclosed via
            # dead_model_record_divergence() instead of failing here.
            assert probe.get("tool_probe") == "FAIL" or (
                basis.get("control_plane_reported_healthy") is True
            ), (
                f"{model}: excluded outside tool-health while the snapshot "
                f"reports {probe.get('tool_probe')!r} and the record does not "
                f"acknowledge that health does not justify the exclusion"
            )

    # the claims themselves are complete: an excluded model's record must
    # exist (KNOWN_DEAD_MODELS is derived from DEAD_MODEL_JUSTIFICATION, this
    # guards the derivation against being hand-broken).
    assert audit_seam.KNOWN_DEAD_MODELS == frozenset(audit_seam.DEAD_MODEL_JUSTIFICATION)

    # 3. a snapshot-FAIL model (any exit code) must never sit in MODEL_ORDER.
    for model in audit_seam.MODEL_ORDER:
        probe = probes.get(model)
        if probe and probe.get("tool_probe") == "FAIL":
            raise AssertionError(
                f"{model} is reported FAIL (exit {probe.get('exit_code')}) by "
                f"the control-plane snapshot yet still sits in MODEL_ORDER — "
                f"it would be handed to every fallback chain as a healthy candidate"
            )


# --------------------------------------------------------------------------
# divergence disclosure (repair r1 of 38948310517): a health refresh must be
# DISCLOSED in shipped provenance, never silently contradict the as-of record
# and never fail the suite merely for being newer.
# --------------------------------------------------------------------------


def test_apply_ships_the_health_record_divergence():
    """Every bundle's provenance carries the as-of-vs-newest comparison.

    The old guard pinned ``control_plane_exit_code``/``tool_probe`` equality
    against the NEWEST snapshot, so a refresh (ultra exit 124 -> 1, same FAIL)
    turned the suite red without any product contradiction — observed on
    snapshots 38938748669 / 38943488237 / 38947845257 in one day.  The fix is
    not to weaken the claim: the divergence is computed at apply time and
    shipped, and the SUBSTANTIVE checks (tool-probe basis requires FAIL;
    non-tool basis must acknowledge health does not justify exclusion) remain
    fail-closed in the test above.
    """
    prov = audit_seam.apply()
    div = prov.get("dead_model_record_divergence")
    assert isinstance(div, dict), "apply() must ship the divergence block"
    assert "snapshot_readable" in div and "differences" in div
    if div["snapshot_readable"]:
        assert isinstance(div["differences"], dict)
        for model, diff in div["differences"].items():
            assert model in audit_seam.KNOWN_DEAD_MODELS
            assert set(diff) <= {"tool_probe", "exit_code"}
            for side in diff.values():
                assert set(side) == {"record", "snapshot"}


def test_divergence_helper_flags_only_actual_differences(monkeypatch, tmp_path):
    """A same-run snapshot produces no differences; a refreshed exit code does.

    Non-vacuity in both directions: identical values -> empty (so the block is
    not decorative), flipped exit code -> recorded (so a real refresh cannot
    hide), flipped tool_probe -> recorded (so a dead-model revival cannot hide).
    """
    ultra = "opencode/nemotron-3-ultra-free"
    lightning = "opencode/nemotron-3.5-lightning-free"

    def _snap(ultra_exit: int, lightning_probe: str, lightning_exit: int) -> dict:
        return {
            "last_checked_run_id": "99999999999",
            "last_checked_at": "2026-10-16T23:59:59Z",
            "probe_results": [
                {"model": ultra, "tool_probe": "FAIL", "exit_code": ultra_exit,
                 "catalog_present": True},
                {"model": lightning, "tool_probe": lightning_probe,
                 "exit_code": lightning_exit, "catalog_present": True},
            ],
        }

    # (a) identical probe facts as the as-of record -> no differences at all.
    same = _snap(ultra_exit=audit_seam.DEAD_MODEL_JUSTIFICATION[ultra]["control_plane_exit_code"],
                 lightning_probe="PASS", lightning_exit=0)
    div = audit_seam.dead_model_record_divergence(
        {"run_id": same["last_checked_run_id"], "checked_at": same["last_checked_at"],
         "excluded_models": {ultra: same["probe_results"][0],
                             lightning: same["probe_results"][1]}})
    assert div["differences"] == {}, div["differences"]
    assert div["same_run"] is False  # record pins run 38947845257, fixture 999...

    # (b) ultra exit flips 1 <-> 124, same FAIL: only the exit code diverges
    # and the tool-probe substance does not — this is the exact refresh that
    # used to fail the suite (audit O1 on snapshot 38943488237).
    refreshed = _snap(ultra_exit=124, lightning_probe="PASS", lightning_exit=0)
    div = audit_seam.dead_model_record_divergence(
        {"run_id": refreshed["last_checked_run_id"],
         "checked_at": refreshed["last_checked_at"],
         "excluded_models": {ultra: refreshed["probe_results"][0],
                             lightning: refreshed["probe_results"][1]}})
    assert set(div["differences"]) == {ultra}
    assert set(div["differences"][ultra]) == {"exit_code"}
    assert div["differences"][ultra]["exit_code"] == {
        "record": audit_seam.DEAD_MODEL_JUSTIFICATION[ultra]["control_plane_exit_code"],
        "snapshot": 124,
    }

    # (c) lightning flips PASS -> FAIL: the tool-probe substance diverges and
    # must be disclosed (the exclusion itself stays correct either way).
    revived = _snap(ultra_exit=1, lightning_probe="FAIL", lightning_exit=124)
    div = audit_seam.dead_model_record_divergence(
        {"run_id": revived["last_checked_run_id"],
         "checked_at": revived["last_checked_at"],
         "excluded_models": {ultra: revived["probe_results"][0],
                             lightning: revived["probe_results"][1]}})
    assert set(div["differences"]) == {lightning}
    assert "tool_probe" in div["differences"][lightning]
    assert div["differences"][lightning]["tool_probe"] == {"record": "PASS", "snapshot": "FAIL"}


def test_divergence_helper_handles_unreadable_snapshot():
    div = audit_seam.dead_model_record_divergence(None) if (
        audit_seam.control_plane_health_snapshot() is None
    ) else audit_seam.dead_model_record_divergence(
        {"run_id": "x", "checked_at": "y", "excluded_models": {}})
    assert "snapshot_readable" in div and "differences" in div
    assert set(div["differences"]) <= set(audit_seam.KNOWN_DEAD_MODELS)
