"""Independent adversarial / counter-authority pass.

After a provisional answer exists, a logically independent second pass looks
for authorities in the same retrieved bundle that could:

  * contradict the provisional conclusion (contradictory)
  * narrow it (limiting)
  * distinguish the facts or legal issue (distinguishing)
  * reveal an exception (exception)
  * expose an older/minority line (minority_line)
  * reveal a language-specific branch (language_branch)

Independence is structural, not rhetorical: the pass uses a separate
model call with a separate prompt that never contains the first pass'
chain of thought, and it is instructed to surface *challenges only*.
Findings that carry no challenge reason are not dropped from the record
(information preservation / negative-result hygiene); they are classified
``unclassified``, which the status merge maps to ``counter_status="none"``
in the product — so an echo can never be *displayed* as a challenge.
``CHALLENGING_REASONS`` is the vocabulary that does count as a challenge and
is reported per run as ``n_challenging_findings``.

Every finding must cite a decision ID present in the bundle; unknown IDs
are rejected and recorded.  Every ``evidence_refs`` quote is subsequently
source-checked verbatim against the cited decision's retrieved text
(:mod:`generative_audit.evidence`); quotes that cannot be located are
rejected before they reach the product.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import paths
from .provider import ProviderError, Runner, resolve_runner
from .source_packing import DecisionBundle, normalize_id

VALID_REASONS = {
    "contradictory", "limiting", "distinguishing",
    "exception", "minority_line", "language_branch", "unclassified",
}

#: Reasons that genuinely challenge the answer (vs. restating it).
CHALLENGING_REASONS = {
    "contradictory", "limiting", "distinguishing",
    "exception", "minority_line", "language_branch",
}

UNCERTAINTY_WORDS = {"certain": 0.0, "low": 0.2, "medium": 0.5, "high": 0.8, "uncertain": 1.0}


@dataclass
class AdversarialFinding:
    """One counter-authority surfaced by the independent pass."""

    decision_id: str
    title: str = ""
    reason: str = "unclassified"
    evidence_refs: List[str] = field(default_factory=list)
    uncertainty: float = 1.0
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "title": self.title,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "uncertainty": round(float(self.uncertainty), 4),
            "confidence": round(float(self.confidence), 4),
        }


class AdversarialPass:
    """Independent counter-authority pass over a bundle + provisional answer."""

    def __init__(
        self,
        bundle: DecisionBundle,
        answer: str,
        model: Optional[str] = None,
        fixture_mode: bool = False,
        fixture_findings: Optional[List[AdversarialFinding]] = None,
        runner: Optional[Runner] = None,
        timeout: float = 180.0,
    ):
        self.bundle = bundle
        self.answer = answer or ""
        self.fixture_mode = fixture_mode
        self.fixture_findings = fixture_findings or []
        self.runner = resolve_runner(runner) if not fixture_mode else runner
        self.timeout = timeout
        self.model = model or ("fixture://generative-audit" if fixture_mode else paths.preferred_model())
        self.rejected_ids: List[str] = []
        self.last_error: Optional[str] = None
        self.last_raw: Optional[str] = None

    # ---- prompt ----

    def build_prompt(self) -> str:
        lines = [
            "You are an independent adversarial reviewer of a provisional legal "
            "answer. Your ONLY job is to find, among the retrieved decision "
            "sources, authorities that CHALLENGE the answer: contradictions, "
            "limitations, distinguishing facts, exceptions, older or minority "
            "lines, or language-specific branches.",
            "",
            f"Provisional answer under review: {self.answer}",
            "",
            "Retrieved decision sources:",
        ]
        for dec in self.bundle.decisions:
            snippet = " ".join((dec.text or "").split())[:400]
            lines.append(f"  [{dec.decision_id}] {dec.title}: {snippet}")
        lines += [
            "",
            "For each challenge report: decision_id, title, reason (one of "
            "contradictory|limiting|distinguishing|exception|minority_line|"
            "language_branch|unclassified), evidence_refs (short excerpts "
            "COPIED VERBATIM from that decision's text above — character for "
            "character, no paraphrase, no translation, no invention; "
            "paraphrases are rejected by the source checker), uncertainty "
            "(0.0 certain - 1.0 highly uncertain), confidence (0.0-1.0).",
            "",
            "Do NOT restate or endorse the answer; only surface challenges. "
            "Do NOT invent facts that are not in the retrieved text. "
            "Use no tools. Reply with ONLY a JSON array (no prose, no "
            "markdown fences). Example:",
            '[{"decision_id": "DEC-002", "title": "BGE …", "reason": '
            '"limiting", "evidence_refs": ["excerpt copied verbatim"], '
            '"uncertainty": 0.3, "confidence": 0.8}]',
            "",
            "If the retrieved sources contain no challenge, reply with [].",
        ]
        return "\n".join(lines)

    # ---- execution ----

    def run(self) -> List[AdversarialFinding]:
        findings, _info = self.run_with_info()
        return findings

    def run_with_info(self) -> Tuple[List[AdversarialFinding], Dict[str, Any]]:
        if self.fixture_mode:
            bundle_ids = {normalize_id(i) for i in self.bundle.decision_ids}
            kept = [f for f in self.fixture_findings if normalize_id(f.decision_id) in bundle_ids]
            self.rejected_ids = [
                f.decision_id for f in self.fixture_findings
                if normalize_id(f.decision_id) not in bundle_ids
            ]
            info = {
                "method": "fixture_adversarial_v2",
                "model": self.model,
                "n_findings": len(kept),
                "n_challenging_findings": sum(1 for f in kept if f.reason in CHALLENGING_REASONS),
                "n_rejected_ids": len(self.rejected_ids),
                "rejected_ids": list(self.rejected_ids),
                "independence": "fixture-injected findings, challenge-only",
            }
            return kept, info

        prompt = self.build_prompt()
        try:
            raw = self.runner(prompt, self.model, self.timeout)
        except Exception as exc:  # noqa: BLE001 - degrade to no findings
            self.last_error = str(exc)
            return [], {
                "method": "independent_llm_adversarial_v2",
                "model": self.model,
                "n_findings": 0,
                "error": self.last_error,
                "independence": "separate model call; failed closed",
            }

        self.last_raw = raw
        findings = self.parse_findings(raw)
        retries = 0
        if not findings and raw.strip() and not self.rejected_ids:
            # Live free models occasionally answer in prose instead of JSON.
            # One strict-format retry keeps the pass useful without weakening
            # the challenge-only objective.
            try:
                raw2 = self.runner(
                    self.build_prompt()
                    + "\n\nREMINDER: your entire reply must be ONE JSON array "
                    "starting with [ and ending with ]. No prose.",
                    self.model,
                    self.timeout,
                )
            except Exception as exc:  # noqa: BLE001
                self.last_error = str(exc)
                raw2 = ""
            if raw2:
                retries = 1
                self.last_raw = raw2
                findings = self.parse_findings(raw2)
                raw = raw2

        info = {
            "method": "independent_llm_adversarial_v2",
            "model": self.model,
            "n_findings": len(findings),
            "n_challenging_findings": sum(1 for f in findings if f.reason in CHALLENGING_REASONS),
            "n_rejected_ids": len(self.rejected_ids),
            "rejected_ids": list(self.rejected_ids),
            "reasons": sorted({f.reason for f in findings}),
            "retries": retries,
            "independence": "separate model call, challenge-only objective, unknown IDs rejected; "
                            "unclassified findings are kept in the record but map to counter_status "
                            "'none' so they are never displayed as challenges",
        }
        if not findings:
            # Preserve the negative result verbatim for auditability.
            info["raw_excerpt"] = (self.last_raw or "")[:1500]
        return findings, info

    # ---- parsing (deterministic, tested) ----

    def parse_findings(self, raw: str) -> List[AdversarialFinding]:
        """Deterministically parse model output into findings.

        Unknown decision IDs are rejected (and recorded in
        ``self.rejected_ids``); malformed reasons become ``unclassified``;
        uncertainty/confidence accept numbers or well-known words.
        """
        self.rejected_ids = []
        json_str = self._extract_json_array(raw)
        if json_str is None:
            return []

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return self._parse_findings_fallback(json_str)
        if not isinstance(data, list):
            return []

        findings: Dict[str, AdversarialFinding] = {}
        bundle_ids = {normalize_id(i) for i in self.bundle.decision_ids}
        for item in data:
            if not isinstance(item, dict):
                continue
            did = normalize_id(item.get("decision_id"))
            if not did:
                continue
            if did not in bundle_ids:
                if did not in self.rejected_ids:
                    self.rejected_ids.append(did)
                continue

            reason = str(item.get("reason") or "unclassified").strip().lower()
            if reason not in VALID_REASONS:
                reason = "unclassified"

            title = str(item.get("title") or "").strip() or did
            evidence = item.get("evidence_refs") or []
            if isinstance(evidence, str):
                evidence = [evidence]
            refs = [str(e).strip() for e in evidence if str(e).strip()][:6]

            candidate = AdversarialFinding(
                decision_id=did,
                title=title,
                reason=reason,
                evidence_refs=refs,
                uncertainty=_to_unit(item.get("uncertainty"), UNCERTAINTY_WORDS, default=1.0),
                confidence=_to_unit(item.get("confidence"), {"high": 0.9, "medium": 0.6, "low": 0.3}, default=0.5),
            )
            prev = findings.get(did)
            if prev is None or (candidate.uncertainty, -candidate.confidence) < (
                prev.uncertainty, -prev.confidence
            ):
                findings[did] = candidate
        return list(findings.values())

    @staticmethod
    def _extract_json_array(raw: str) -> Optional[str]:
        if not raw:
            return None
        fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
        if fenced:
            return fenced.group(1)
        start = raw.find("[")
        while start != -1:
            depth = 0
            in_str = False
            esc = False
            for idx in range(start, len(raw)):
                ch = raw[idx]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        candidate = raw[start:idx + 1]
                        if candidate.strip().startswith("[{") or candidate.strip() == "[]":
                            return candidate
                        break
            start = raw.find("[", start + 1)
        return None

    def _parse_findings_fallback(self, json_str: str) -> List[AdversarialFinding]:
        """Best-effort extraction when the array is not valid JSON."""
        ids = re.findall(r'"decision_id"\s*:\s*"([^"]+)"', json_str)
        reasons = re.findall(r'"reason"\s*:\s*"([^"]+)"', json_str)
        bundle_ids = {normalize_id(i) for i in self.bundle.decision_ids}
        out: Dict[str, AdversarialFinding] = {}
        for did, reason in zip(ids, reasons):
            did = normalize_id(did)
            if did not in bundle_ids:
                if did not in self.rejected_ids:
                    self.rejected_ids.append(did)
                continue
            reason = reason.strip().lower()
            if reason not in VALID_REASONS:
                reason = "unclassified"
            out.setdefault(
                did,
                AdversarialFinding(
                    decision_id=did, title=did, reason=reason,
                    evidence_refs=[], uncertainty=1.0, confidence=0.3,
                ),
            )
        return list(out.values())


def _to_unit(value: Any, word_map: Dict[str, float], default: float) -> float:
    if isinstance(value, str):
        v = word_map.get(value.strip().lower())
        if v is not None:
            return v
        value = value.strip()
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    return 0.0 if f < 0.0 else (1.0 if f > 1.0 else f)


__all__ = [
    "AdversarialFinding",
    "AdversarialPass",
    "VALID_REASONS",
    "CHALLENGING_REASONS",
    "ProviderError",
]
