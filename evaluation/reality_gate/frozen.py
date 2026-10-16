"""Frozen reality-gate benchmark definition (evaluation lane, direction v49).

FREEZE DISCIPLINE
-----------------
``frozen_benchmark.json`` is the frozen sample: hypothesis, query set,
assertions and success rules fixed BEFORE the benchmark was executed against
any product output.  Its SHA-256 is pinned in :data:`FROZEN_SHA256` and is
re-verified by the unit tests and by the runner before every execution, so a
weakened benchmark cannot be silently introduced: the lane under test does not
own this file's semantics.

Provenance: factory direction v49 ("encode and enforce the observed
reality-check failures") plus the product's own frozen reality legs
(``product/product/reality_check.py`` LEGS / truth gates at accepted packet
fdf1e386, evidence ``results/product/reality_check/``).  This is an
INDEPENDENT re-encoding owned by the evaluation lane.

Pure standard library: the evaluation harness deliberately does not import
Product code.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

FROZEN_SHA256 = "ff57f556c3755ab663766618ab7abe763f251e7add70cd8ed964141846d063c8"

_PATH = Path(__file__).resolve().parent / "frozen_benchmark.json"


class FrozenBenchmarkError(RuntimeError):
    """The frozen benchmark was tampered with or is structurally invalid."""


def load_frozen() -> dict:
    """Load and verify the frozen benchmark definition."""
    raw = _PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != FROZEN_SHA256:
        raise FrozenBenchmarkError(
            f"frozen benchmark digest mismatch: {digest} != {FROZEN_SHA256}. "
            "The frozen query set/assertions must not change after results; "
            "re-freeze deliberately with a new digest pin."
        )
    spec = json.loads(raw.decode("utf-8"))
    slugs = [q["slug"] for q in spec["questions"]]
    if len(slugs) != len(set(slugs)):
        raise FrozenBenchmarkError("duplicate slug in frozen benchmark")
    for q in spec["questions"]:
        for field in ("question", "language", "truth_gates",
                      "required_citation_ids", "required_retrieval_ids"):
            if field not in q:
                raise FrozenBenchmarkError(f"frozen question {q.get('slug')} missing {field}")
    return spec


def question_by_slug(spec: dict | None = None) -> dict[str, dict]:
    spec = spec or load_frozen()
    return {q["slug"]: q for q in spec["questions"]}


def normalize_text(value: object) -> str:
    """NFKD + strip diacritics + casefold + collapse whitespace.

    Identical normalization to the product's frozen reality gates
    (``product/reality_check.py:norm``), so phrase matching is comparable
    lane-to-lane.  NFKD does not decompose U+2019, which is why the frozen
    phrase lists carry both apostrophe variants explicitly.
    """
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())
