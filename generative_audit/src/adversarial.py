"""
Adversarial / counter-authority pass for generative audit.

After a provisional generated answer is produced, this module runs an
independent retrieval/generation pass whose objective is to find authorities
that could:
  - contradict the provisional conclusion;
  - narrow it;
  - distinguish the facts or legal issue;
  - reveal an exception;
  - show a minority or older line;
  - expose a language-specific branch;
  - undermine the apparent consensus.

These cases must be retained even when their initial relevance score is lower.

The pass is logically independent of the first answer generation pass.
It must not simply restate the first answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
import subprocess
import json
import re
from pathlib import Path

from .source_packing import DecisionBundle, Decision, CitationValidator


@dataclass
class AdversarialFinding:
    """A single adversarial finding surfaced by the independent pass."""
    decision_id: str
    title: str
    reason: str  # one of: "contradictory", "limiting", "distinguishing",
                 # "exception", "minority_line", "language_branch", "unclassified"
    evidence_refs: List[str] = field(default_factory=list)  # supporting text spans
    uncertainty: float = 1.0  # 0.0 = certain, 1.0 = uncertain
    confidence: float = 0.5  # model confidence in this classification


class AdversarialPass:
    """
    Independent counter-authority pass.

    Given a generated answer and a decision bundle, this pass finds
    authorities that challenge, limit, distinguish, or create exceptions
    to the answer.  The pass is intentionally separate from the
    answer-generation model call so that it provides an independent
    check.
    """

    def __init__(
        self,
        bundle: DecisionBundle,
        answer: str,
        model: Optional[str] = None,
        fixture_mode: bool = False,
        fixture_findings: Optional[List[AdversarialFinding]] = None,
        use_attestation: bool = True,
    ):
        self.bundle = bundle
        self.answer = answer
        self.model = model or self._select_model_from_health()
        self.fixture_mode = fixture_mode
        self.fixture_findings = fixture_findings or []
        self.use_attestation = use_attestation

    def _select_model_from_health(self) -> str:
        """Read model_health.json and return the preferred healthy model."""
        health_path = Path("/home/runner/work/LexMachina/LexMachina/state/model_health.json")
        if health_path.exists():
            try:
                with open(health_path) as f:
                    health = json.load(f)
                if health.get("healthy") and health.get("healthy_models"):
                    return health["healthy_models"][0]
            except Exception:
                pass
        return "opencode/nemotron-3.5-lightning-free"

    # ---- public API ----

    def run(self) -> List[AdversarialFinding]:
        """Run the adversarial pass and return a list of findings."""
        if self.fixture_mode:
            return self.fixture_findings or []

        return self._run_with_model()

    # ---- model-based execution ----

    def _run_with_model(self) -> List[AdversarialFinding]:
        """Run the adversarial pass using the model CLI."""
        prompt = self._build_prompt()
        try:
            raw = self._run_opencode(prompt)
            return self._parse_findings(raw)
        except Exception as e:
            # Model failure — return empty findings; the caller can
            # decide how to handle (fallback, degrade, etc.)
            return []

    def _build_prompt(self) -> str:
        """Build the adversarial prompt from the answer and bundle."""
        lines = []
        lines.append(
            "You are conducting an independent adversarial review of a generated "
            "legal answer.  Your task is to find decision authorities from the "
            "provided source bundle that could contradict, limit, distinguish, "
            "or create exceptions to the answer.  Do NOT simply restate the "
            "answer; instead surface cases that challenge it."
        )
        lines.append("")
        lines.append(f"Generated answer: {self.answer}")
        lines.append("")
        lines.append("Decision sources:")
        for dec in self.bundle.decisions:
            snippet = (dec.text or "")[:300]
            lines.append(
                f"  [{dec.decision_id}] {dec.title}: {snippet}"
            )
        lines.append("")
        lines.append("For each decision you surface, provide:")
        lines.append(
            "  1. The decision_id."
        )
        lines.append(
            "  2. A concise reason why this decision is adversarial, choosing "
            "from: contradictory, limiting, distinguishing, exception, "
            "minority_line, language_branch, unclassified."
        )
        lines.append(
            "  3. A brief evidence reference (1-2 sentence excerpt) from the "
            "decision text that supports the claimed reason."
        )
        lines.append(
            "  4. Assign an uncertainty score from 0.0 (certain) to 1.0 "
            "(highly uncertain) about the classification."
        )
        lines.append("")
        lines.append("Return a JSON list where each element has: "
                     "decision_id, title, reason, evidence_refs (list), uncertainty.")
        lines.append("")
        lines.append("If no adversarial authorities are found from this bundle, "
                     "return an empty JSON list [].")
        return "\n".join(lines)

    def _run_opencode(self, prompt: str) -> str:
        """Run opencode CLI with the given prompt."""
        try:
            result = subprocess.run(
                ["opencode", "run", "--model", self.model, "--agent", "model_probe",
                 prompt],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"opencode CLI failed (rc={result.returncode}): {result.stderr}"
                )
            return result.stdout.strip()
        except Exception as e:
            raise RuntimeError(f"Adversarial pass invocation error: {e}")

    def _parse_findings(self, raw: str) -> List[AdversarialFinding]:
        """Parse the model output into AdversarialFinding objects."""
        import json
        import re

        # Try to find JSON list in the output
        # Look for [...] pattern that looks like a JSON list
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not json_match:
            return []

        json_str = json_match.group(0)
        try:
            findings_data = json.loads(json_str)
        except json.JSONDecodeError:
            # Try to extract individual findings
            return self._parse_findings_fallback(json_str)

        if not isinstance(findings_data, list):
            return []

        findings = []
        for fd in findings_data:
            if not isinstance(fd, dict):
                continue
            decision_id = fd.get("decision_id", "")
            title = fd.get("title", decision_id)
            reason = fd.get("reason", "unclassified")
            evidence_refs = fd.get("evidence_refs", [])
            uncertainty = fd.get("uncertainty", 1.0)
            # Normalize reason
            valid_reasons = {
                "contradictory", "limiting", "distinguishing",
                "exception", "minority_line", "language_branch", "unclassified",
            }
            if reason not in valid_reasons:
                reason = "unclassified"
            # Validate that the decision_id is in the bundle
            if decision_id not in self.bundle.decision_ids:
                continue
            findings.append(
                AdversarialFinding(
                    decision_id=decision_id,
                    title=title,
                    reason=reason,
                    evidence_refs=evidence_refs if evidence_refs else [],
                    uncertainty=float(uncertainty),
                )
            )

        # Deduplicate by decision_id
        seen_ids: Set[str] = set()
        unique_findings = []
        for f in findings:
            if f.decision_id not in seen_ids:
                seen_ids.add(f.decision_id)
                unique_findings.append(f)

        return unique_findings

    def _parse_findings_fallback(self, json_str: str) -> List[AdversarialFinding]:
        """Fallback parsing when full JSON parse fails."""
        import re
        findings = []
        # Try to extract decision IDs and reasons via regex
        # This is a best-effort fallback
        id_pattern = r"decision_id['\"]?\s*:\s*['\"]?([A-Za-z0-9_-]+)"
        reason_pattern = r"reason['\"]?\s*:\s*['\"]?([A-Za-z0-9_]+)"

        decision_ids = re.findall(id_pattern, json_str)
        reasons = re.findall(reason_pattern, json_str)

        for did, reason in zip(decision_ids, reasons):
            valid_reasons = {
                "contradictory", "limiting", "distinguishing",
                "exception", "minority_line", "language_branch", "unclassified",
            }
            if reason not in valid_reasons:
                reason = "unclassified"
            # Validate that the decision_id is in the bundle
            if did not in self.bundle.decision_ids:
                continue
            findings.append(
                AdversarialFinding(
                    decision_id=did,
                    title=did,
                    reason=reason,
                    evidence_refs=[],
                    uncertainty=1.0,
                )
            )

        return findings