"""The live sourced-answer leg must be diagnosable, probed and budgeted.

Defect pinned (measured live, producer cycle 39667945530)
-----------------------------------------------------------
The canonical vertical slice ran end to end against the public OpenCaseLaw
API, but its headline leg — the sourced generative answer — degraded to the
extractive fallback after **287.964 s**, and the bundle recorded the cause as

    "all provider attempts failed: opencode CLI failed (rc=1): "

i.e. **no model and no reason**: the OpenCode CLI writes its failure to stdout
as a JSON event and leaves stderr empty, and the degraded path then dropped
the component's per-attempt list.  The same model answered the same prompt in
**182.2 s** when it was given a 300 s budget, so the shipped 120 s budget was
the reason the product shipped an extractive dump instead of a generative
answer.

These tests are offline and deterministic: the CLI is faked, no network, no
model, no paid inference.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from query import answer_provider as ap  # noqa: E402
from query import pipeline  # noqa: E402

QUERY = "Kündigung Mietvertrag Mietrecht"

CLI_ERROR_STDOUT = json.dumps({
    "type": "error",
    "error": {
        "name": "UnknownError",
        "data": {"message": "Unexpected server error. Check server logs for details.",
                 "ref": "err_e37a6642"},
    },
})


class _Proc:
    """Minimal stand-in for ``subprocess.CompletedProcess``."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# --------------------------------------------------------------------------
# 1. the real cause is never empty again
# --------------------------------------------------------------------------

def test_cli_error_is_read_from_the_stdout_event_stream():
    err = ap.extract_cli_error(CLI_ERROR_STDOUT)
    assert err is not None
    assert err["name"] == "UnknownError"
    assert "Unexpected server error" in err["message"]
    assert err["ref"] == "err_e37a6642"


def test_cli_error_is_none_when_the_stream_carries_no_error_event():
    assert ap.extract_cli_error('{"type":"text","part":{"text":"ok"}}') is None


def test_run_cli_reports_the_model_and_the_real_reason_not_an_empty_stderr(monkeypatch):
    """The shipped runner reported ``rc=1: `` (empty stderr) — the cause is lost."""
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["timeout"] = kwargs.get("timeout")
        return _Proc(returncode=1, stdout=CLI_ERROR_STDOUT, stderr="")

    monkeypatch.setattr(ap.subprocess, "run", fake_run)
    with pytest.raises(ap.AnswerProviderError) as excinfo:
        ap.run_cli("prompt", "opencode/mimo-v2.6-flash-free", 30.0)

    err = excinfo.value
    assert err.kind == "cli_error"
    assert err.model == "opencode/mimo-v2.6-flash-free"
    assert "UnknownError" in err.detail
    assert "Unexpected server error" in err.detail
    assert "err_e37a6642" in err.detail
    assert err.detail.strip() != ""
    assert seen["cmd"][:3] == ["opencode", "run", "--model"]


def test_run_cli_classifies_a_timeout_separately_from_a_hard_failure(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 0) or 0)

    monkeypatch.setattr(ap.subprocess, "run", fake_run)
    with pytest.raises(ap.AnswerProviderError) as excinfo:
        ap.run_cli("prompt", "opencode/slow-model", 12.0)
    assert excinfo.value.kind == "timeout"
    assert "12s" in excinfo.value.detail


def test_run_cli_classifies_empty_output(monkeypatch):
    monkeypatch.setattr(ap.subprocess, "run", lambda cmd, **kw: _Proc(0, stdout="", stderr=""))
    with pytest.raises(ap.AnswerProviderError) as excinfo:
        ap.run_cli("prompt", "opencode/quiet-model", 30.0)
    assert excinfo.value.kind == "empty_output"


def test_run_cli_returns_the_concatenated_text_events(monkeypatch):
    stdout = "\n".join([
        json.dumps({"type": "step_start"}),
        json.dumps({"type": "text", "part": {"text": "Frist von 30 Tagen."}}),
        json.dumps({"type": "text", "part": {"text": " Art. 257d."}}),
        json.dumps({"type": "step_finish"}),
    ])
    monkeypatch.setattr(ap.subprocess, "run", lambda cmd, **kw: _Proc(0, stdout=stdout))
    out = ap.run_cli("prompt", "opencode/mimo-v2.6-flash-free", 30.0)
    assert "Frist von 30 Tagen." in out
    assert "Art. 257d." in out


def test_run_cli_reports_a_missing_binary_instead_of_raising_oserror(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(ap.subprocess, "run", fake_run)
    with pytest.raises(ap.AnswerProviderError) as excinfo:
        ap.run_cli("prompt", "opencode/mimo-v2.6-flash-free", 30.0)
    assert excinfo.value.kind == "cli_error"
    assert "not found" in excinfo.value.detail


# --------------------------------------------------------------------------
# 2. the probe skips dead models instead of burning an answer budget
# --------------------------------------------------------------------------

def test_probe_marks_dead_models_and_selects_the_first_live_one():
    def fake_runner(prompt, model, timeout):
        if model == "opencode/space-bunny-free":
            raise ap.AnswerProviderError("cli_error", model, "UnknownError: server error")
        return "OK"

    records = ap.probe_models(
        ["opencode/space-bunny-free", "opencode/mimo-v2.6-flash-free",
         "opencode/longcat-2.5-preview-free"],
        runner=fake_runner,
    )
    assert [r["model"] for r in records] == [
        "opencode/space-bunny-free",
        "opencode/mimo-v2.6-flash-free",
        "opencode/longcat-2.5-preview-free",
    ]
    assert records[0]["alive"] is False
    assert records[0]["kind"] == "cli_error"
    assert "UnknownError" in records[0]["detail"]
    assert records[1]["alive"] is True
    assert ap.select_model(records) == "opencode/mimo-v2.6-flash-free"


def test_probe_stops_at_the_first_live_candidate_and_names_the_rest_as_not_probed():
    """Probing every candidate cost 55.4 s on 2026-10-21; the happy path must
    cost one tiny probe, and the unprobed candidates must be named as such."""
    probed: list[str] = []

    def fake_runner(prompt, model, timeout):
        probed.append(model)
        return "OK"

    records = ap.probe_models(
        ["opencode/mimo-v2.6-flash-free", "opencode/space-bunny-free"],
        runner=fake_runner,
    )
    assert probed == ["opencode/mimo-v2.6-flash-free"], "the probe stops at the first answer"
    assert records[0]["alive"] is True
    assert records[1]["alive"] is None
    assert records[1]["kind"] == "not_probed"
    assert ap.select_model(records) == "opencode/mimo-v2.6-flash-free"


def test_probe_never_raises_and_reports_an_unexpected_error():
    def fake_runner(prompt, model, timeout):
        raise RuntimeError("boom")

    records = ap.probe_models(["opencode/x"], runner=fake_runner)
    assert records[0]["alive"] is False
    assert records[0]["kind"] == "probe_error"
    assert "boom" in records[0]["detail"]
    assert ap.select_model(records) is None


def test_probe_uses_the_fixed_probe_question_and_the_given_budget():
    seen = {}

    def fake_runner(prompt, model, timeout):
        seen["prompt"] = prompt
        seen["timeout"] = timeout
        return "OK"

    ap.probe_model("opencode/mimo-v2.6-flash-free", timeout_s=17.0, runner=fake_runner)
    assert seen["prompt"] == ap.PROBE_PROMPT
    assert seen["timeout"] == 17.0


# --------------------------------------------------------------------------
# 3. the leg budget is bounded
# --------------------------------------------------------------------------

def test_leg_budget_stops_further_cli_calls(monkeypatch):
    def fake_run(cmd, **kwargs):  # pragma: no cover - must never be reached
        raise AssertionError("the CLI must not be called once the budget is spent")

    monkeypatch.setattr(ap.subprocess, "run", fake_run)
    budget = ap.AnswerProviderBudget(total_s=0.0)
    runner = ap.build_runner(budget)
    with pytest.raises(ap.AnswerProviderError) as excinfo:
        runner("prompt", "opencode/mimo-v2.6-flash-free", 300.0)
    assert excinfo.value.kind == "budget_exhausted"


def test_runner_never_exceeds_the_remaining_leg_budget(monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["timeout"] = kwargs.get("timeout")
        return _Proc(0, stdout=json.dumps({"type": "text", "part": {"text": "ok"}}))

    monkeypatch.setattr(ap.subprocess, "run", fake_run)
    budget = ap.AnswerProviderBudget(total_s=30.0)
    runner = ap.build_runner(budget)
    runner("prompt", "opencode/mimo-v2.6-flash-free", 300.0)
    assert seen["timeout"] <= 30.0


def test_runner_uses_the_smaller_of_the_requested_and_remaining_budget(monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["timeout"] = kwargs.get("timeout")
        return _Proc(0, stdout=json.dumps({"type": "text", "part": {"text": "ok"}}))

    monkeypatch.setattr(ap.subprocess, "run", fake_run)
    runner = ap.build_runner(ap.AnswerProviderBudget(total_s=600.0))
    runner("prompt", "opencode/mimo-v2.6-flash-free", 42.0)
    assert seen["timeout"] == 42.0


# --------------------------------------------------------------------------
# 4. the pipeline publishes the diagnostics and never fabricates an answer
# --------------------------------------------------------------------------

def _first(n=60):
    from query import run_query_first_page

    bundle = run_query_first_page(QUERY, top_n=n, retrieval_mode="fixture")
    return bundle


def test_degraded_fallback_publishes_the_answer_provider_diagnostics():
    bundle = _first()
    diagnostics = {"probe": [{"model": "opencode/x", "alive": False}], "selected_model": None}
    out = pipeline._extractive_degraded_fallback(
        bundle, "RuntimeError: boom", max_cites=4, diagnostics=diagnostics
    )
    ga = out["provenance"]["generative_audit"]
    assert ga["degraded"] is True
    assert ga["product_answer_provider"]["probe"][0]["alive"] is False
    assert out["answer"]["status"] == "degraded"
    assert out["answer"]["cited_decision_ids"], "the extractive fallback still cites"


def test_live_answer_uses_the_probed_model_and_publishes_the_probe(monkeypatch):
    """The live path probes, picks a live model and records the attempt list."""
    captured = {}

    def fake_probe(models, timeout_s=None, runner=None):
        captured["candidates"] = list(models)
        return [
            {"model": models[0], "alive": False, "kind": "cli_error", "detail": "dead today"},
            {"model": models[1], "alive": True, "kind": "ok", "detail": ""},
        ]

    def fake_run_generative_audit(work, **kwargs):
        captured["provider"] = kwargs.get("provider")
        captured["kwargs"] = kwargs
        out = json.loads(json.dumps(work))
        cited = out["decisions"][0]["decision_id"]
        out["answer"] = {
            "prose": f"Die Frist beträgt 30 Tage [{cited}].",
            "cited_decision_ids": [cited],
            "status": "ready",
            "method": "fake",
        }
        out.setdefault("provenance", {})["generative_audit"] = {
            "model": "opencode/mimo-v2.6-flash-free",
            "provider_error": None,
            "provider_attempts": [{"model": "opencode/mimo-v2.6-flash-free", "error": ""}],
        }
        return out

    monkeypatch.setattr(pipeline, "probe_models", fake_probe)
    monkeypatch.setattr(pipeline, "run_generative_audit", fake_run_generative_audit)

    out = pipeline.enrich_query_bundle(
        _first(), retrieval_mode="fixture", fixture_generation=False, adversarial_retrieval=False
    )

    provider = captured["provider"]
    assert provider is not None
    assert provider.model == captured["candidates"][1], "the probed, live model is used"
    ga = out["provenance"]["generative_audit"]
    assert ga["product_answer_provider"]["selected_model"] == captured["candidates"][1]
    assert len(ga["product_answer_provider"]["probe"]) == 2
    assert ga["product_answer_provider"]["provider_attempts"]
    assert out["answer"]["status"] == "ready"


def test_no_live_model_probed_alive_degrades_with_the_probe_record(monkeypatch):
    """Fail closed: no fabricated answer, and the reason is published."""
    monkeypatch.setattr(
        pipeline, "probe_models",
        lambda models, timeout_s=None, runner=None: [
            {"model": m, "alive": False, "kind": "cli_error", "detail": "server error"}
            for m in models
        ],
    )
    called = {"n": 0}

    def fake_run_generative_audit(work, **kwargs):  # pragma: no cover - must not run
        called["n"] += 1
        raise AssertionError("no model call may be made when no candidate is alive")

    monkeypatch.setattr(pipeline, "run_generative_audit", fake_run_generative_audit)

    out = pipeline.enrich_query_bundle(
        _first(), retrieval_mode="fixture", fixture_generation=False, adversarial_retrieval=False
    )

    assert called["n"] == 0
    assert out["answer"]["status"] == "degraded"
    ga = out["provenance"]["generative_audit"]
    assert ga["degraded"] is True
    assert "no candidate free model" in ga["provider_error"]
    assert ga["product_answer_provider"]["probe"], "the probe record survives the degraded path"
    assert ga["product_answer_provider"]["selected_model"] is None


def test_fixture_mode_never_probes_or_calls_the_cli(monkeypatch):
    """The offline path must stay byte-identical: no probe, no CLI."""
    monkeypatch.setattr(
        pipeline, "probe_models",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("fixture mode must not probe")),
    )
    out = pipeline.enrich_query_bundle(_first(), retrieval_mode="fixture", fixture_generation=True)
    assert out["answer"]["status"] == "ready"
    ga = out["provenance"].get("generative_audit", {})
    assert "product_answer_provider" not in ga, "fixture mode publishes no live-provider diagnostics"
