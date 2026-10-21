"""Product-owned live answer provider: diagnosable, probed and budgeted.

Why this module exists
----------------------
Measured on 2026-10-21 (producer cycle 39667945530, live run against the
public OpenCaseLaw API, query "Kündigung Mietvertrag Mietrecht", 151
decisions), the canonical vertical slice ran end to end but its headline leg
— the **sourced generative answer** — silently degraded to the extractive
fallback:

* the answer stage burned **287.964 s** and returned ``status="degraded"``;
* the recorded cause was ``"all provider attempts failed: opencode CLI failed
  (rc=1): "`` — an **empty** diagnostic that names neither the model that
  failed nor the reason;
* the four candidate models in the pinned order behaved like this (measured
  per attempt, product run 39667945530):

  ================================  ==================  =========================
  model                             attempt outcome      cost
  ================================  ==================  =========================
  opencode/mimo-v2.6-flash-free     timeout @120 s      120 s burned
  opencode/space-bunny-free         CLI rc=1            ~2 s
  opencode/longcat-2.5-preview-free timeout @120 s      120 s burned
  opencode/muse-spark-1.3-…-free    CLI rc=1            ~2 s
  ================================  ==================  =========================

  The same model **does** answer the same prompt when it is given enough
  wall-clock: with a 300 s per-model budget
  ``opencode/mimo-v2.6-flash-free`` returned a properly sourced German answer
  in **182.2 s** with 6 cited decision IDs.  The shipped 120 s budget is
  therefore the reason the product ships an extractive dump instead of a
  generative answer.

Why the diagnostic was empty
----------------------------
``frontier/frontier-generative-audit/generative_audit/provider.py`` reports a
non-zero CLI exit as ``rc=<code>: <stderr tail>``.  The OpenCode CLI writes its
failure to **stdout** as a JSON event
(``{"type":"error","error":{"name":"UnknownError","data":{"message":"Unexpected
server error…","ref":"…"}}}``) and leaves stderr empty, so the product published
an empty cause.  The per-attempt list was then dropped a second time: the
degraded fallback in ``product/query/pipeline.py`` overwrites
``provenance.generative_audit`` with a four-key summary, so the attempt list
the component had built never reached the bundle.

What this module does (product-owned, no accepted component is modified)
-----------------------------------------------------------------------
1. **A diagnosable CLI runner.**  ``run_cli`` extracts the CLI's real error
   name/message/ref from the stdout event stream, distinguishes *timeout* from
   *hard failure* from *empty output*, and raises a structured
   ``AnswerProviderError``.  The cause is never empty again.
2. **A liveness probe.**  ``probe_models`` asks each candidate a fixed, tiny,
   deterministic question with a short budget.  Models that are dead today
   (server error / endpoint unavailable) fail in seconds instead of consuming a
   full answer budget; the probe records are published as provenance.
3. **A leg-level wall-clock budget.**  ``AnswerProviderBudget`` caps the whole
   answer leg, so the fallback chain cannot burn ``n_models × per-model
   timeout`` (288 s measured) when the first model is merely slow.

What it never does
------------------
* never invents an answer, a citation or a legal proposition — the fallback
  stays the extractive one, and the bundle keeps ``status="degraded"``;
* never changes a frozen rubric, bar or threshold (none is read here);
* never asserts that any decision IS supporting/contrary/limiting;
* never touches geometry, ranks, clusters or relations;
* never touches ``human_gate_ready`` / ``ready_for_owner_session`` / an owner
  card;
* never runs in fixture mode: the offline path is byte-identical.

Usage
-----
    from product.query.answer_provider import (
        AnswerProviderBudget, build_runner, probe_models, select_model,
    )
    records = probe_models(candidates)
    model = select_model(records)
    runner = build_runner(AnswerProviderBudget(total_s=420.0))
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

#: The probe question.  Fixed and tiny so it measures liveness, not quality.
PROBE_PROMPT = "Reply with exactly one word: OK"

#: Per-model wall clock for the probe.  Dead models fail in seconds; a live
#: model answers the probe in ~2 s (measured 2026-10-21).
DEFAULT_PROBE_TIMEOUT_S = 45.0

#: Per-model wall clock for the real answer.  Measured 2026-10-21: the
#: shipped 120 s budget timed out on a prompt that needed 182.2 s.
DEFAULT_ANSWER_TIMEOUT_S = 300.0

#: Wall clock for the whole answer leg (all candidate models together).
DEFAULT_LEG_BUDGET_S = 420.0

#: The CLI binary.  Overridable for tests and for alternative installations.
CLI_BINARY_ENV = "LEX_ANSWER_CLI_BINARY"
DEFAULT_CLI_BINARY = "opencode"


class AnswerProviderError(RuntimeError):
    """A live answer attempt failed, with a machine-readable cause.

    ``kind`` is one of:

    ``cli_error``       the CLI exited non-zero (its real reason is in
                        ``detail``; ``stderr_tail`` holds whatever it wrote
                        there);
    ``timeout``         the CLI exceeded the effective budget for this attempt;
    ``empty_output``    the CLI exited zero but produced no text;
    ``budget_exhausted`` the leg-level budget was already spent, so no further
                        CLI call was made.
    """

    def __init__(
        self,
        kind: str,
        model: str,
        detail: str = "",
        elapsed_s: float = 0.0,
        stderr_tail: str = "",
    ) -> None:
        self.kind = kind
        self.model = model
        self.detail = detail
        self.elapsed_s = elapsed_s
        self.stderr_tail = stderr_tail
        super().__init__(f"{kind} [{model}]: {detail or 'no detail reported'}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "model": self.model,
            "detail": self.detail,
            "elapsed_s": round(self.elapsed_s, 3),
            "stderr_tail": self.stderr_tail[-400:],
        }


@dataclass
class AnswerProviderBudget:
    """Wall-clock budget for the whole live answer leg.

    The frontier provider walks a fallback chain and gives every candidate the
    same per-model timeout.  With four candidates that is up to
    ``4 x timeout`` (288 s measured at the shipped 120 s timeout) even when the
    first model was the only one that could ever answer.  This budget makes
    the leg's cost bounded and observable.
    """

    total_s: float = DEFAULT_LEG_BUDGET_S
    started_at: float = field(default_factory=time.monotonic)

    def remaining_s(self) -> float:
        return max(0.0, self.total_s - (time.monotonic() - self.started_at))

    def elapsed_s(self) -> float:
        return max(0.0, time.monotonic() - self.started_at)


def cli_binary() -> str:
    return os.environ.get(CLI_BINARY_ENV, DEFAULT_CLI_BINARY) or DEFAULT_CLI_BINARY


def _events(stdout: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            out.append(event)
    return out


def extract_cli_error(stdout: str) -> dict[str, Any] | None:
    """Return the CLI's real failure reason from its stdout event stream.

    The OpenCode CLI reports failures as
    ``{"type":"error","error":{"name":…,"data":{"message":…,"ref":…}}}`` and
    leaves stderr empty, which is why the shipped runner published an empty
    cause.  This function returns ``{"name":…, "message":…, "ref":…}`` for the
    first error event, or ``None`` when the stream carries no error event.
    """
    for event in _events(stdout):
        if event.get("type") != "error":
            continue
        err = event.get("error")
        if not isinstance(err, dict):
            return {"name": "error", "message": json.dumps(err)[:400], "ref": ""}
        data = err.get("data")
        if not isinstance(data, dict):
            data = {}
        return {
            "name": str(err.get("name") or "error"),
            "message": str(data.get("message") or ""),
            "ref": str(data.get("ref") or ""),
        }
    return None


def extract_text(stdout: str) -> str:
    """Concatenate the CLI's ``text`` events (the component's own contract)."""
    chunks: list[str] = []
    for event in _events(stdout):
        if event.get("type") != "text":
            continue
        part = event.get("part")
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if text:
            chunks.append(str(text))
    out = "\n".join(chunks).strip()
    if out:
        return out
    # Some CLI versions print plain text when the JSON stream is empty.
    return (stdout or "").strip()


def run_cli(
    prompt: str,
    model: str,
    timeout_s: float,
    *,
    cwd: str | None = None,
    binary: str | None = None,
) -> str:
    """Run the OpenCode CLI once and return its text.

    Raises ``AnswerProviderError`` with a machine-readable cause.  The CLI is
    executed in an isolated temporary directory so no project agent/tool
    configuration can interfere with a pure text completion.
    """
    exe = binary or cli_binary()
    tmp_dir = tempfile.mkdtemp(prefix="lex-answer-")
    try:
        started = time.monotonic()
        try:
            proc = subprocess.run(
                [exe, "run", "--model", model, "--format", "json", prompt],
                capture_output=True,
                text=True,
                timeout=max(1.0, float(timeout_s)),
                cwd=cwd or tmp_dir,
            )
        except subprocess.TimeoutExpired as exc:
            raise AnswerProviderError(
                "timeout",
                model,
                detail=f"no answer within {float(timeout_s):.0f}s",
                elapsed_s=time.monotonic() - started,
            ) from exc
        except FileNotFoundError as exc:
            raise AnswerProviderError(
                "cli_error",
                model,
                detail=f"CLI binary not found: {exe}",
                elapsed_s=time.monotonic() - started,
            ) from exc
        elapsed = time.monotonic() - started
        if proc.returncode != 0:
            err = extract_cli_error(proc.stdout)
            if err:
                detail = f"{err['name']}: {err['message']}".strip()
                if err.get("ref"):
                    detail = f"{detail} (ref={err['ref']})"
            else:
                detail = f"exit code {proc.returncode} with no error event"
            raise AnswerProviderError(
                "cli_error",
                model,
                detail=detail,
                elapsed_s=elapsed,
                stderr_tail=(proc.stderr or "")[-800:],
            )
        out = extract_text(proc.stdout)
        if not out:
            raise AnswerProviderError(
                "empty_output",
                model,
                detail="CLI exited 0 but produced no text",
                elapsed_s=elapsed,
                stderr_tail=(proc.stderr or "")[-800:],
            )
        return out
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def probe_model(
    model: str,
    *,
    timeout_s: float = DEFAULT_PROBE_TIMEOUT_S,
    runner: Callable[[str, str, float], str] | None = None,
) -> dict[str, Any]:
    """Ask one candidate the fixed probe question and report the outcome.

    The record is honest about *what was measured*: liveness of this model on
    this day, with this probe, in this budget.  It says nothing about answer
    quality.
    """
    call = runner or run_cli
    started = time.monotonic()
    try:
        text = call(PROBE_PROMPT, model, float(timeout_s))
    except AnswerProviderError as exc:
        record = exc.to_dict()
        record.update({"alive": False, "probe_timeout_s": float(timeout_s)})
        return record
    except Exception as exc:  # noqa: BLE001 - a probe never raises
        return {
            "model": model,
            "alive": False,
            "kind": "probe_error",
            "detail": f"{type(exc).__name__}: {exc}"[:400],
            "elapsed_s": round(time.monotonic() - started, 3),
            "probe_timeout_s": float(timeout_s),
        }
    return {
        "model": model,
        "alive": True,
        "kind": "ok",
        "detail": "",
        "elapsed_s": round(time.monotonic() - started, 3),
        "probe_timeout_s": float(timeout_s),
        "probe_reply": (text or "")[:80],
    }


def probe_models(
    models: Sequence[str],
    *,
    timeout_s: float = DEFAULT_PROBE_TIMEOUT_S,
    runner: Callable[[str, str, float], str] | None = None,
    stop_at_first_alive: bool = True,
) -> list[dict[str, Any]]:
    """Probe the candidates in order and return one record per probed candidate.

    With ``stop_at_first_alive`` (the default) the probe stops at the first
    model that answers: the pinned order is tried from the front, and a live
    first candidate costs one tiny probe (measured ~2 s) instead of one probe
    per candidate (measured 55.4 s for four candidates on 2026-10-21).  The
    candidates that were NOT probed are named in the returned records as
    ``not_probed`` so the published record never implies a measurement that
    did not happen.
    """
    records: list[dict[str, Any]] = []
    remaining = [m for m in models if m]
    for index, model in enumerate(remaining):
        record = probe_model(model, timeout_s=timeout_s, runner=runner)
        records.append(record)
        if stop_at_first_alive and record.get("alive"):
            for skipped in remaining[index + 1:]:
                records.append({
                    "model": skipped,
                    "alive": None,
                    "kind": "not_probed",
                    "detail": "an earlier candidate answered the probe",
                    "elapsed_s": 0.0,
                    "probe_timeout_s": float(timeout_s),
                })
            break
    return records


def select_model(records: Iterable[dict[str, Any]]) -> str | None:
    """First candidate that probed alive, in probe order.

    The order of ``records`` is the pinned candidate order, so the selection
    is deterministic and does not depend on probe timing.
    """
    for record in records:
        if record.get("alive") and record.get("model"):
            return str(record["model"])
    return None


def build_runner(
    budget: AnswerProviderBudget | None = None,
    *,
    binary: str | None = None,
) -> Callable[[str, str, float], str]:
    """Build a ``Runner`` for the frontier provider.

    The returned callable has the component's signature
    ``(prompt, model, timeout) -> str`` and adds two properties the shipped
    runner lacked: a diagnosable failure cause and the leg-level budget.
    """

    def runner(prompt: str, model: str, timeout: float) -> str:
        leg = budget if budget is not None else AnswerProviderBudget()
        remaining = leg.remaining_s()
        if remaining <= 0:
            raise AnswerProviderError(
                "budget_exhausted",
                model,
                detail=f"answer-leg budget of {leg.total_s:.0f}s is spent",
                elapsed_s=leg.elapsed_s(),
            )
        effective = min(float(timeout), remaining)
        return run_cli(prompt, model, effective, binary=binary)

    return runner


def budget_from_env() -> AnswerProviderBudget:
    """Build the leg budget from the environment (defaults are the measured ones)."""
    total = os.environ.get("LEX_ANSWER_LEG_BUDGET_S", "")
    try:
        total_s = float(total) if total else DEFAULT_LEG_BUDGET_S
    except ValueError:
        total_s = DEFAULT_LEG_BUDGET_S
    return AnswerProviderBudget(total_s=total_s)


def answer_timeout_from_env() -> float:
    """Per-model wall clock for the answer call (measured floor: 182.2 s)."""
    raw = os.environ.get("LEX_ANSWER_TIMEOUT_S", "")
    try:
        value = float(raw) if raw else DEFAULT_ANSWER_TIMEOUT_S
    except ValueError:
        value = DEFAULT_ANSWER_TIMEOUT_S
    return max(30.0, value)


def probe_timeout_from_env() -> float:
    raw = os.environ.get("LEX_ANSWER_PROBE_TIMEOUT_S", "")
    try:
        value = float(raw) if raw else DEFAULT_PROBE_TIMEOUT_S
    except ValueError:
        value = DEFAULT_PROBE_TIMEOUT_S
    return max(5.0, value)
