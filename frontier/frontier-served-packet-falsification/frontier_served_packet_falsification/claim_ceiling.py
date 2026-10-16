"""Claim ceiling: this measurement never asserts that any specific decision
IS supporting, contrary or limiting. It reports the SUPPORT of the product's
own issued labels under a frozen rubric, and the SEMANTICS of the shipped
map geometry under a frozen rule. Those remain the product's labels and the
product's geometry: reported here, not endorsed, not re-assigned.

The machine-checked predicate rejects any authority-claiming construction
applied to a specific decision.
"""

from __future__ import annotations

import re
from typing import Any

# Constructs that would cross the claim ceiling if applied to a named decision.
_FORBIDDEN_PATTERNS = [
    re.compile(r"\bdecision\s+[A-Za-z0-9_.\-]+\s+is\s+(supporting|contrary|limiting)\b", re.I),
    re.compile(r"\bdecision\s+[A-Za-z0-9_.\-]+\s+is\s+not\s+(supporting|contrary|limiting)\b", re.I),
    re.compile(r"\b[A-Za-z0-9_.\-]+\s+is\s+(a\s+)?(supporting|contrary|limiting)\s+(authority|decision|case)\b", re.I),
    re.compile(r"\bwe\s+(classify|label|find)\s+[A-Za-z0-9_.\-]+\s+as\s+(supporting|contrary|limiting)\b", re.I),
    re.compile(r"\basserts?\s+that\s+[A-Za-z0-9_.\-]+\s+is\s+(supporting|contrary|limiting)\b", re.I),
]

CLAIM_CEILING = (
    "This measurement is about the SUPPORT OF THE LABELS AS ISSUED by the product's "
    "counter-authority pass, and about the SEMANTICS OF THE SHIPPED MAP GEOMETRY. "
    "It NEVER asserts that any specific decision IS supporting, contrary or limiting. "
    "Those remain the product's labels: reported here, not endorsed, not re-assigned. "
    "is_outlier, cluster placement, rank position and jurist findability are emitted "
    "as READ-ONLY CONTEXT only and are never a verdict of this charter."
)


def scan_for_violations(text: str) -> list[str]:
    """Return list of forbidden authority-claiming constructions in text."""
    hits: list[str] = []
    for pat in _FORBIDDEN_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append(m.group(0))
    return hits


def check_payload(payload: Any) -> dict[str, Any]:
    """Walk a JSON-like payload and flag any authority-claiming string."""
    violations: list[str] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, str):
            for hit in scan_for_violations(node):
                violations.append(f"{path}: {hit}")
        elif isinstance(node, dict):
            for k, v in node.items():
                _walk(v, f"{path}.{k}")
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                _walk(v, f"{path}[{i}]")

    _walk(payload, "$")
    return {
        "claim_ceiling": CLAIM_CEILING,
        "n_violations": len(violations),
        "violations": violations[:50],
        "pass": len(violations) == 0,
    }


def build_claim_ceiling_artifact() -> dict[str, Any]:
    return {
        "schema": "frontier-served-packet-falsification/claim-ceiling/1",
        "claim_ceiling": CLAIM_CEILING,
        "forbidden_construction_patterns": [p.pattern for p in _FORBIDDEN_PATTERNS],
        "note": (
            "Machine-checked by a test that rejects any authority-claiming construction "
            "applied to a specific decision, so this team can never be quoted as deciding "
            "any individual case."
        ),
    }
