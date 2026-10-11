"""
Provider abstraction for generative answer generation.

Supports:
  - Free OpenCode CLI model invocation (no owner-paid APIs required)
  - Deterministic fixture/mock mode for testing without model calls
  - Provider failure fallback to alternative free model
  - Citation-ID constraints: only decision IDs present in the source
    bundle may be cited; hallucinated IDs are programmatically rejected.

The provider interface is deliberately narrow: given a query and a
source bundle of validated decisions, produce a grounded answer with
citations that are a subset of the bundle's decision IDs.
"""

import json
import subprocess
import sys
import os
from typing import Any, Dict, List, Optional, Tuple

from .source_packing import CitationValidator, DecisionBundle


class ProviderResult:
    """Result of a provider call."""
    __slots__ = ("answer", "cited_decision_ids", "model_used", "token_count", "raw_output")

    def __init__(
        self,
        answer: str,
        cited_decision_ids: List[str],
        model_used: str,
        token_count: Optional[int] = None,
        raw_output: Optional[str] = None,
    ):
        self.answer = answer
        self.cited_decision_ids = cited_decision_ids
        self.model_used = model_used
        self.token_count = token_count
        self.raw_output = raw_output


class Provider:
    """
    Provider abstraction.

    Uses the opencode CLI with a free model for generation.  A deterministic
    fixture/mock mode is available for CI/test environments where no model
    invocation is desired.
    """

    # Preferred free models (in order of preference from model_health.json)
    FREE_MODELS = [
        "opencode/nemotron-3.5-lightning-free",
        "opencode/nemotron-3-ultra-free",
        "opencode/mimo-v2.6-flash-free",
        "opencode/ling-3.1-flash-free",
    ]

    def __init__(
        self,
        model: Optional[str] = None,
        fixture_mode: bool = False,
        fixture_answer: Optional[str] = None,
        fixture_cited_ids: Optional[List[str]] = None,
    ):
        self.fixture_mode = fixture_mode
        self.fixture_answer = fixture_answer or ""
        self.fixture_cited_ids = fixture_cited_ids or []
        # Select model: explicit override or first healthy free model
        if model:
            self.model = model
        elif fixture_mode:
            self.model = "fixture://generative-audit"
        else:
            self.model = self.FREE_MODELS[0]

    # ---- internal helpers ----

    def _run_opencode(self, prompt: str, model: Optional[str] = None) -> str:
        """Run opencode CLI with the given prompt and return the model output."""
        target_model = model or self.model
        try:
            result = subprocess.run(
                ["opencode", "run", "--model", target_model, "--agent", "model_probe",
                 f"Generate a legal answer to the following query. "
                 f"Produce a concise substantive answer. Query: {prompt}"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                # Try next model in preference on failure
                raise RuntimeError(
                    f"opencode CLI failed (rc={result.returncode}): {result.stderr}"
                )
            return result.stdout.strip()
        except Exception as e:
            raise RuntimeError(f"Provider invocation error: {e}")

    # ---- public API ----

    def generate(
        self,
        bundle: DecisionBundle,
        model_override: Optional[str] = None,
    ) -> ProviderResult:
        """
        Generate a sourced, grounded answer from a decision bundle.

        The returned answer cites ONLY decision IDs that are present in
        bundle.decision_ids.  Any hallucinated IDs are stripped by the
        post-generation citation validator.

        Returns a ProviderResult with the answer, cited decision IDs,
        and the model used.
        """
        if self.fixture_mode:
            return self._fixture_result(bundle)

        # Build the prompt: include query + decision summaries, constrain citations
        prompt = self._build_prompt(bundle)

        # Try the requested model; fall back through free models on failure
        last_error = None
        for attempt_model in [model_override or self.model] + self.FREE_MODELS:
            try:
                raw = self._run_opencode(prompt, model_override or attempt_model)
                return self._parse_output(raw, bundle)
            except Exception as err:
                last_error = err
                continue

        # All attempts failed — return a failure result
        return ProviderResult(
            answer="",
            cited_decision_ids=[],
            model_used=attempt_model or self.model,
            raw_output=f"ALL_MODEL_ATTEMPTS_FAILED: {last_error}",
        )

    def _build_prompt(self, bundle: DecisionBundle) -> str:
        """Build a prompt from the bundle that includes query + decision context."""
        lines = []
        lines.append("You are a legal research AI. Answer the Swiss legal question "
                      "using ONLY the provided decision sources below.")
        lines.append("")
        lines.append(f"Query: {bundle.query}")
        lines.append("")
        lines.append("Decision sources (each identified by a decision ID):")
        for dec in bundle.decisions:
            # Include a truncated snippet to keep prompts manageable
            snippet = (dec.text or "")[:500]
            lines.append(f"  [{dec.decision_id}] {snippet}")
        lines.append("")
        lines.append("Instructions:")
        lines.append(
            "  - Answer the legal question concisely and substantively."
        )
        lines.append(
            "  - Cite decision IDs from the sources above to support your propositions."
        )
        lines.append(
            "  - If a proposition is not supported by any source, mark it as uncertain."
        )
        lines.append(
            "  - Do NOT invent or cite decision IDs that are not in the source list."
        )
        lines.append(
            "  - Provide the answer in a single concise paragraph."
        )
        lines.append("")
        lines.append("Answer:")
        return "\n".join(lines)

    def _parse_output(self, raw: str, bundle: DecisionBundle) -> ProviderResult:
        """Parse the model output, extract the answer and cited decision IDs."""
        # Extract cited decision IDs from the output
        # Pattern: [DEC001], [DEC002], etc.
        import re
        cited_ids = re.findall(r"\[(\w+)\]", raw)

        # Validate: only keep IDs that are actually in the bundle
        valid_ids = CitationValidator.filter_valid_citations(cited_ids, bundle.decision_ids)

        # Extract the answer text (everything after "Answer:" or the first paragraph)
        answer = raw.split("Answer:")[-1].strip() if "Answer:" in raw else raw.strip()
        # Take only the first paragraph
        answer = answer.split("\n\n")[0].strip()

        # If no valid citations found but answer text exists, that's OK
        # (the citation validator will handle it in downstream validation)

        return ProviderResult(
            answer=answer,
            cited_decision_ids=valid_ids,
            model_used=self.model,
            raw_output=raw,
        )

    def _fixture_result(self, bundle: DecisionBundle) -> ProviderResult:
        """Return a deterministic fixture result for testing."""
        # Use the fixture answer if provided, otherwise construct from bundle
        answer = self.fixture_answer or f"Fixture answer for: {bundle.query}"
        # If fixture cited IDs are provided, filter them to valid ones
        valid_ids = [
            cid for cid in self.fixture_cited_ids if cid in bundle.decision_ids
        ]
        # Fallback: if no valid fixture IDs, use first bundle decision
        if not valid_ids and bundle.decisions:
            valid_ids = [bundle.decisions[0].decision_id]
        return ProviderResult(
            answer=answer,
            cited_decision_ids=valid_ids,
            model_used="fixture://generative-audit",
        )