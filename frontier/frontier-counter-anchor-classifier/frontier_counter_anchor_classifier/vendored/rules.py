"""Load the frozen rules and expose them read-only.

The harness refuses to run without ``--frozen-rules``.  The file's sha256 is
embedded in every report so any later edit to RULES.json (or to the generator
that produced it) is detectable, and ``verify_freeze.py`` proves from git commit
times that the file was committed before the first scoring run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .normalize import Normalizer


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class FrozenRules:
    path: str
    sha256: str
    data: dict[str, Any]

    # -- convenience accessors -----------------------------------------
    @property
    def lexicons(self) -> dict[str, Any]:
        return self.data["lexicons"]

    @property
    def rubric(self) -> dict[str, Any]:
        return self.data["rubric"]

    @property
    def anchors(self) -> dict[str, Any]:
        return self.data["question_anchors"]

    @property
    def verdict_rule(self) -> dict[str, Any]:
        return self.data["verdict_rule"]

    @property
    def non_vacuity(self) -> dict[str, Any]:
        return self.data["non_vacuity"]

    @property
    def normalizer(self) -> Normalizer:
        return Normalizer(self.data["normalization"])

    def marker_lexicon(self, language: str, variant: str = "primary") -> list[str]:
        """Counter-intent markers for a language.

        variant='primary' uses the product's own ADVERSARIAL_TERMS plus the
        frozen additions; variant='strict-no-product-vocabulary' drops the
        product's terms (pre-declared sensitivity analysis).
        """
        entry = self.lexicons["counter_intent_markers"].get(language) or {}
        terms = list(entry.get("frozen_additions") or [])
        if variant != "strict-no-product-vocabulary":
            terms = list(entry.get("product_adversarial_terms") or []) + terms
        return terms

    def anchor_profile(self, profile_key: str) -> dict[str, Any]:
        return self.anchors[profile_key]

    def input_by_relpath(self, relpath: str) -> dict[str, Any] | None:
        for entry in self.data["inputs"]:
            if entry["relpath_under_results_product"] == relpath:
                return entry
        return None

    def population_of(self, relpath: str) -> str:
        entry = self.input_by_relpath(relpath)
        return entry["population"] if entry else "unregistered"


def load_rules(path: str) -> FrozenRules:
    with open(path, "rb") as fh:
        payload = fh.read()
    data = json.loads(payload.decode("utf-8"))
    if data.get("schema") != "frontier-counter-label-integrity/rules/1":
        raise ValueError(f"unexpected rules schema: {data.get('schema')!r}")
    for key in ("rubric", "verdict_rule", "non_vacuity", "lexicons", "question_anchors"):
        if key not in data:
            raise ValueError(f"frozen rules missing required block: {key}")
    return FrozenRules(path=path, sha256=sha256_bytes(payload), data=data)


def rules_digest(payload: dict[str, Any]) -> str:
    """Canonical digest of a report payload (deterministic, key-sorted)."""
    return sha256_bytes(
        (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )