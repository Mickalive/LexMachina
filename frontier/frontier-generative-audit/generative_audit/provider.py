"""Provider abstraction: free no-owner-cost model paths + fixture mode.

Development paths (acceptance test 1):
  1. ``default_cli_runner``  — OpenCode CLI (``opencode run``), free models from
     ``state/model_health.json``.  Verified working inside CI for this cycle.
  2. ``openai_compatible_runner`` — any local OpenAI-compatible server
     (Ollama / LM Studio / vLLM) via ``LEX_OPENAI_BASE_URL`` (+ optional
     ``LEX_OPENAI_API_KEY``).  Zero owner cost, documented local mode.
  3. Fixture mode — deterministic, offline, used by the frozen test suite.

All real paths funnel through the same post-generation validator:
cited IDs are constrained to the retrieved bundle, hallucinated IDs are
reported AND redacted from the surfaced prose.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import paths
from .opencaselaw import PostGenerationValidator
from .source_packing import (
    DecisionBundle,
    CitationValidator,
    extract_citation_ids,
    redact_unknown_citations,
)

#: runner(prompt, model, timeout) -> raw assistant text
Runner = Callable[[str, str, float], str]


class ProviderError(RuntimeError):
    """Raised when a provider backend cannot produce output."""


def default_cli_runner(prompt: str, model: str, timeout: float = 180.0) -> str:
    """Run the OpenCode CLI with a free model and return raw assistant text.

    Executes in an isolated temp directory so no project agent/tool config
    can interfere with a pure text-completion request.  ``--format json``
    yields a stable event stream; only ``text`` events are concatenated.
    """
    with tempfile.TemporaryDirectory(prefix="lex-genaudit-") as tmp:
        proc = subprocess.run(
            [
                "opencode", "run",
                "--model", model,
                "--format", "json",
                prompt,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tmp,
        )
    if proc.returncode != 0:
        raise ProviderError(f"opencode CLI failed (rc={proc.returncode}): {proc.stderr[-800:]}")

    chunks: List[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text":
            part = event.get("part") or {}
            text = part.get("text")
            if text:
                chunks.append(text)
    out = "\n".join(chunks).strip()
    if not out:
        # Fallback: some opencode versions print plain text when json fails.
        out = proc.stdout.strip()
    if not out:
        raise ProviderError("opencode CLI returned empty output")
    return out


def openai_compatible_runner(prompt: str, model: str, timeout: float = 180.0) -> str:
    """Chat-completions call against any OpenAI-compatible local server.

    Configure with environment variables:
      ``LEX_OPENAI_BASE_URL``  e.g. http://127.0.0.1:11434/v1  (Ollama)
      ``LEX_OPENAI_MODEL``     overrides the requested model id when set
      ``LEX_OPENAI_API_KEY``   optional (many local servers ignore it)
    """
    import urllib.request

    base = os.environ.get("LEX_OPENAI_BASE_URL", "").rstrip("/")
    if not base:
        raise ProviderError("LEX_OPENAI_BASE_URL not set (no local OpenAI-compatible server configured)")
    model_id = os.environ.get("LEX_OPENAI_MODEL") or model
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('LEX_OPENAI_API_KEY', 'lex-local')}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(f"unexpected chat-completions response shape: {exc}")
    if not content or not str(content).strip():
        raise ProviderError("local model returned empty content")
    return str(content).strip()


def resolve_runner(runner: Optional[Runner] = None) -> Runner:
    """Pick a real backend: explicit runner > CLI > OpenAI-compatible."""
    if runner is not None:
        return runner
    backend = os.environ.get("LEX_GENAUDIT_BACKEND", "cli").strip().lower()
    if backend in ("openai", "openai-compatible", "local"):
        return openai_compatible_runner
    return default_cli_runner


class ProviderResult:
    """Result of one generation call (success or recorded failure)."""

    __slots__ = (
        "answer", "cited_decision_ids", "model_used", "raw_output",
        "validation_report", "error", "redacted_citation_ids", "attempts",
    )

    def __init__(
        self,
        answer: str,
        cited_decision_ids: List[str],
        model_used: str,
        raw_output: Optional[str] = None,
        validation_report: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        redacted_citation_ids: Optional[List[str]] = None,
        attempts: Optional[List[Dict[str, str]]] = None,
    ):
        self.answer = answer
        self.cited_decision_ids = cited_decision_ids
        self.model_used = model_used
        self.raw_output = raw_output
        self.validation_report = validation_report or {}
        self.error = error
        self.redacted_citation_ids = redacted_citation_ids or []
        self.attempts = attempts or []

    @property
    def ok(self) -> bool:
        return not self.error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "cited_decision_ids": self.cited_decision_ids,
            "model_used": self.model_used,
            "error": self.error,
            "redacted_citation_ids": self.redacted_citation_ids,
            "validation_report": self.validation_report,
            "attempts": self.attempts,
        }


class Provider:
    """Provider-agnostic sourced answer generation with citation constraints."""

    def __init__(
        self,
        model: Optional[str] = None,
        fixture_mode: bool = False,
        fixture_answer: Optional[str] = None,
        fixture_cited_ids: Optional[List[str]] = None,
        use_attestation: Optional[bool] = None,
        runner: Optional[Runner] = None,
        timeout: float = 180.0,
    ):
        self.fixture_mode = fixture_mode
        self.fixture_answer = fixture_answer or ""
        self.fixture_cited_ids = fixture_cited_ids or []
        self.use_attestation = use_attestation
        self.runner = resolve_runner(runner) if not fixture_mode else runner
        self.timeout = timeout
        if model:
            self.model = model
        elif fixture_mode:
            self.model = "fixture://generative-audit"
        else:
            self.model = paths.preferred_model()

    # ---- prompt construction ----

    def build_prompt(self, bundle: DecisionBundle) -> str:
        # The full bundle remains the citation-validation boundary, but dumping
        # 100+ weak lexical hits into the answer model diluted the strongest
        # authorities. Product reranking places the best legal evidence first.
        prompt_decisions = list(bundle.decisions[:36])
        lines = [
            "You are a legal research assistant answering a Swiss case-law "
            "question using ONLY the retrieved decision sources listed below.",
            "",
            f"Query: {bundle.query}",
            "",
            f"Retrieved decision sources: {len(prompt_decisions)} highest-ranked "
            f"of {len(bundle.decisions)} retrieved decisions.",
        ]
        for dec in prompt_decisions:
            snippet = " ".join((dec.text or "").split())[:700]
            lines.append(f"  [{dec.decision_id}] {dec.title}: {snippet}")
        lines += [
            "",
            "Instructions:",
            "  - Answer every distinct sub-question in the query. If a statute "
            "contains different paragraphs/alternatives (for example al. 1 "
            "versus al. 2), state each branch separately and do not collapse them.",
            "  - Prefer Federal Supreme Court/BGE holdings over lower-court "
            "decisions when both directly address the same proposition.",
            "  - A source that merely mentions a statute or topic is not enough "
            "to support a proposition; rely on sources that actually address it.",
            "  - Give a concise structured answer (normally 2-5 short paragraphs).",
            "  - Support propositions by citing sources as [DECISION_ID], "
            "using ONLY the retrieved IDs listed above.",
            "  - Right after a [DECISION_ID] marker, add the official Swiss "
            "citation shown in the source list in parentheses (e.g. "
            "[bge_78_II_230] (BGE 78 II 230)) so the citation can be "
            "independently attested by OpenCaseLaw.",
            "  - Quote the source verbatim (in its own language) when you "
            "state what a decision held.",
            "  - Never invent, guess or extrapolate a decision ID.",
            "  - Mark propositions not supported by the sources as uncertain "
            "instead of filling gaps from general model knowledge.",
            "  - Do not use any tools; reply with the answer text only.",
            "",
            "Answer:",
        ]
        return "\n".join(lines)

    # ---- generation ----

    def generate(self, bundle: DecisionBundle, model_override: Optional[str] = None) -> ProviderResult:
        if self.fixture_mode:
            return self._fixture_result(bundle)

        prompt = self.build_prompt(bundle)
        primary = model_override or self.model
        candidates: List[str] = []
        for m in [primary, *self._fallback_models(exclude=primary)]:
            if m and m not in candidates:
                candidates.append(m)

        attempts: List[Dict[str, str]] = []
        last_error: Optional[Exception] = None
        for attempt_model in candidates:
            try:
                raw = self.runner(prompt, attempt_model, self.timeout)
                result = self._parse_output(raw, bundle, model_used=attempt_model)
                result.attempts = attempts
                return result
            except Exception as exc:  # noqa: BLE001 - record and fall through
                last_error = exc
                attempts.append({"model": attempt_model, "error": str(exc)})

        return ProviderResult(
            answer="",
            cited_decision_ids=[],
            model_used="",
            raw_output=f"ALL_MODELS_FAILED: {last_error}",
            error=f"all provider attempts failed: {last_error}",
            attempts=attempts,
            validation_report={
                "mode": "failed",
                "valid_citations": [],
                "hallucinated_ids": [],
                "unverified_ids": [],
                "verified_ids": [],
            },
        )

    def _fallback_models(self, exclude: Optional[str] = None) -> List[str]:
        return [m for m in paths.healthy_models() if m != exclude]

    def _parse_output(self, raw: str, bundle: DecisionBundle, model_used: str) -> ProviderResult:
        cited_raw = extract_citation_ids(raw)
        locally_valid = CitationValidator.filter_valid_citations(cited_raw, bundle.decision_ids)
        hallucinated = CitationValidator.hallucinated_ids(cited_raw, bundle.decision_ids)

        validator = PostGenerationValidator(bundle, use_attestation=self.use_attestation)
        final_cited, report = validator.validate_and_filter(locally_valid)
        report["hallucinated_ids"] = hallucinated
        report["redacted_citation_ids"] = hallucinated

        # Preserve the complete model answer. The previous implementation
        # split on the first blank line, which silently reduced structured
        # multi-paragraph legal answers to a heading or opening sentence.
        answer = raw.split("Answer:", 1)[-1].strip() if "Answer:" in raw else raw.strip()
        clean_answer, _removed = redact_unknown_citations(answer, bundle.decision_ids)

        return ProviderResult(
            answer=clean_answer,
            cited_decision_ids=final_cited,
            model_used=model_used,
            raw_output=raw,
            validation_report=report,
            redacted_citation_ids=hallucinated,
        )

    def _fixture_result(self, bundle: DecisionBundle) -> ProviderResult:
        answer = self.fixture_answer or f"Fixture answer for: {bundle.query}"
        valid_ids = CitationValidator.filter_valid_citations(self.fixture_cited_ids, bundle.decision_ids)
        if not valid_ids and bundle.decisions:
            valid_ids = [bundle.decisions[0].decision_id]
        report = {
            "mode": "strict_local",
            "valid_citations": valid_ids,
            "hallucinated_ids": [],
            "unverified_ids": list(valid_ids),
            "verified_ids": [],
            "local_bundle_ids": list(bundle.decision_ids),
        }
        return ProviderResult(
            answer=answer,
            cited_decision_ids=valid_ids,
            model_used="fixture://generative-audit",
            validation_report=report,
        )
