"""Frozen retrieval/counter-authority benchmark definition (evaluation lane, v49).

FREEZE DISCIPLINE
-----------------
``frozen_retrieval_benchmark.json`` fixes the query set (FR/DE/IT baseline +
counter queries for the four observed reality-check questions), the frozen
authority and known-counter sets, the norm/limitation token proxies, the
top-k, the latency budgets, the id-match rules and every gate's success rule
BEFORE any frozen query was executed against OpenCaseLaw.  Its SHA-256 is
pinned in :data:`FROZEN_SHA256` and re-verified by the unit tests and by the
runner before every execution, and ``FREEZE_RECORD.json`` carries the same
digest plus the pre-freeze probe disclosure, so ordering is auditable.

The authority sets are re-owned from the already-frozen reality benchmark
(``evaluation/reality_gate/frozen_benchmark.json``, sha ff57f556…); nothing in
that spec is modified here.  No 174k/global-geometry benchmark is involved.

Pure standard library; the evaluation harness does not import Product code.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

FROZEN_SHA256 = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"

_DIR = Path(__file__).resolve().parent
_PATH = _DIR / "frozen_retrieval_benchmark.json"
FREEZE_RECORD_PATH = _DIR / "FREEZE_RECORD.json"

SLUG_ORDER = [
    "rent-default",
    "corporate-criminal-liability",
    "business-judgment-rule",
    "petty-theft-dismissal",
]
LANGUAGES = ("fr", "de", "it")
CHANNELS = ("baseline", "counter")


class FrozenBenchmarkError(RuntimeError):
    """The frozen retrieval benchmark was tampered with or is structurally invalid."""


def load_frozen() -> dict:
    raw = _PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != FROZEN_SHA256:
        raise FrozenBenchmarkError(
            f"frozen retrieval benchmark digest mismatch: {digest} != {FROZEN_SHA256}. "
            "The frozen query set/thresholds must not change after results; "
            "re-freeze deliberately with a new digest pin."
        )
    spec = json.loads(raw.decode("utf-8"))
    _validate(spec)
    return spec


def _validate(spec: dict) -> None:
    if spec.get("schema") != "lex-frozen-retrieval-benchmark/1":
        raise FrozenBenchmarkError(f"unexpected schema {spec.get('schema')!r}")
    slugs = [q.get("slug") for q in spec.get("questions", [])]
    if slugs != SLUG_ORDER:
        raise FrozenBenchmarkError(f"question set changed: {slugs}")
    budgets = spec.get("latency_budgets") or {}
    if budgets.get("per_search_seconds") != 30.0 or budgets.get("full_pass_seconds") != 240.0:
        raise FrozenBenchmarkError(f"latency budgets changed: {budgets}")
    top_k = spec.get("top_k") or {}
    if top_k.get("baseline") != 50 or top_k.get("counter") != 30:
        raise FrozenBenchmarkError(f"top-k changed: {top_k}")
    for q in spec["questions"]:
        for field in ("queries", "authority_ids", "known_counter_ids",
                      "authority_set_provenance", "known_counter_provenance"):
            if field not in q:
                raise FrozenBenchmarkError(f"frozen question {q.get('slug')} missing {field}")
        material = q["queries"]
        for channel in CHANNELS:
            if sorted(material.get(channel, {})) != sorted(LANGUAGES):
                raise FrozenBenchmarkError(
                    f"{q.get('slug')}.{channel} must carry exactly fr/de/it")
            for lang in LANGUAGES:
                if not str(material[channel][lang]).strip():
                    raise FrozenBenchmarkError(
                        f"{q.get('slug')}.{channel}.{lang} query text is empty")
        if not material.get("norm_tokens"):
            raise FrozenBenchmarkError(f"{q.get('slug')} has no norm_tokens")
        if not material.get("limitation_tokens"):
            raise FrozenBenchmarkError(f"{q.get('slug')} has no limitation_tokens")


def question_by_slug(spec: dict | None = None) -> dict[str, dict]:
    spec = spec or load_frozen()
    return {q["slug"]: q for q in spec["questions"]}


def freeze_record() -> dict:
    """The pre-execution freeze record; its digest must match the spec digest."""
    if not FREEZE_RECORD_PATH.exists():
        raise FrozenBenchmarkError(f"missing freeze record: {FREEZE_RECORD_PATH}")
    rec = json.loads(FREEZE_RECORD_PATH.read_text(encoding="utf-8"))
    if rec.get("frozen_sha256") != FROZEN_SHA256:
        raise FrozenBenchmarkError(
            "freeze record digest does not match the pinned frozen digest "
            f"({rec.get('frozen_sha256')} != {FROZEN_SHA256})")
    if not rec.get("frozen_before_execution"):
        raise FrozenBenchmarkError("freeze record does not assert pre-execution freeze")
    return rec


def normalize_text(value: object) -> str:
    """NFKD + strip diacritics + casefold + collapse whitespace.

    Same normalization as the frozen reality benchmark (parity so token and
    phrase matching is comparable lane-to-lane).  ``<mark>`` highlight tags
    coming back from search snippets are stripped first, otherwise a marker
    would be split by markup.
    """
    text = str(value or "")
    text = _strip_markup(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())


def _strip_markup(text: str) -> str:
    """Drop HTML highlight tags (``<mark>…</mark>``) but KEEP their content.

    Search snippets are returned with ``<mark>`` highlighting; the tags must go
    before matching, while the marked text itself is exactly what we match on.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "<":
            j = text.find(">", i)
            if j == -1:          # unterminated tag: keep the rest verbatim
                out.append(text[i:])
                break
            i = j + 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def alnum_core(value: object) -> str:
    """Lowercase alnum-only core with repeated leading court tokens stripped."""
    raw = [ch for ch in str(value or "").casefold() if ch.isalnum()]
    core = "".join(raw)
    for _ in range(4):
        for token in ("bgestger", "bstger", "bger", "bge", "bg"):
            if core.startswith(token) and len(core) > len(token):
                core = core[len(token):]
                break
        else:
            break
    return core
