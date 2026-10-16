"""Frozen query-map CONTRACT benchmark definition (evaluation lane, v49).

FREEZE DISCIPLINE
-----------------
``frozen_map_benchmark.json`` fixes the input inventory (the COMPLETE set of
accepted product bundles matching a mechanical inclusion rule, each with a
pinned sha256), the trilingual function-word lexicon, the tokenizer, the query
language inference rule and every gate's success rule BEFORE any of those
bundles was scored by a gate.  Its SHA-256 is pinned in :data:`FROZEN_SHA256`
and re-verified by the unit tests, by the runner before every execution and by
``python -m evaluation.lane_suite``.

``FREEZE_RECORD.json`` carries the same digest plus an explicit pre-freeze
disclosure of the feasibility reconnaissance that preceded it, so the ordering
is auditable rather than asserted.

This benchmark is deliberately NOT the accepted Frontier geometry rubric
(``RULES_GEOMETRY.json``, sha256 a7452748…, adopted by this lane as metrics
B1/B2).  It measures the map CONTRACT -- enumerability, point distinguishability,
outlier-flag consistency, label language and counter-authority reachability --
which the Frontier rubric does not test and which no gate in this repository
tested before cycle 38959325856.

Pure standard library.  The evaluation lane does not import Product code and
makes no network call.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

FROZEN_SHA256 = "7f3e7cb1515baec5f55a3191d115ffe71b2ef28057a8d4e68930ece45f8090a4"

_DIR = Path(__file__).resolve().parent
_PATH = _DIR / "frozen_map_benchmark.json"
FREEZE_RECORD_PATH = _DIR / "FREEZE_RECORD.json"

LANGUAGES = ("de", "fr", "it")

GATE_IDS = (
    "MAP::cluster_membership_enumerable",
    "MAP::points_distinguishable",
    "MAP::outlier_degree_consistent",
    "MAP::label_language_matches_query",
    "MAP::counter_authority_selectable",
)

_TOKEN_RE = re.compile(r"[^a-z0-9]+")


class FrozenBenchmarkError(RuntimeError):
    """The frozen map-contract benchmark was tampered with or is invalid."""


def normalize_text(value: object) -> str:
    """NFKD + strip diacritics + casefold + collapse whitespace.

    Same normalization as the frozen reality and retrieval benchmarks, so
    token comparisons stay comparable lane-to-lane.  ``<mark>…</mark>`` search
    highlight tags are stripped but their content is kept, exactly as the
    frozen reality benchmark does, so a markup wrapper can never become a
    token.
    """
    text = _strip_markup(str(value or ""))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())


def _strip_markup(text: str) -> str:
    """Drop HTML highlight tags (``<mark>…</mark>``) but KEEP their content."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == "<":
            j = text.find(">", i)
            if j == -1:
                out.append(text[i:])
                break
            i = j + 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def tokenize(value: object) -> list[str]:
    """Frozen tokenizer: alphanumeric runs >= 2 chars, pure digits dropped."""
    return [tok for tok in _TOKEN_RE.split(normalize_text(value))
            if len(tok) > 1 and not tok.isdigit()]


def load_frozen() -> dict:
    raw = _PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != FROZEN_SHA256:
        raise FrozenBenchmarkError(
            f"frozen map benchmark digest mismatch: {digest} != {FROZEN_SHA256}. "
            "The frozen input inventory, lexicon or thresholds must not change "
            "after results; re-freeze deliberately with a new digest pin."
        )
    spec = json.loads(raw.decode("utf-8"))
    _validate(spec)
    return spec


def _validate(spec: dict) -> None:
    if spec.get("schema") != "lex-frozen-map-contract-benchmark/1":
        raise FrozenBenchmarkError(f"unexpected schema {spec.get('schema')!r}")
    inputs = spec.get("inputs") or []
    if not inputs:
        raise FrozenBenchmarkError("frozen input inventory is empty")
    paths = [b.get("path") for b in inputs]
    if paths != sorted(paths):
        raise FrozenBenchmarkError("frozen input inventory is not in ascending path order")
    if len(set(paths)) != len(paths):
        raise FrozenBenchmarkError("frozen input inventory contains duplicate paths")
    for b in inputs:
        if not b.get("sha256") or not b.get("path"):
            raise FrozenBenchmarkError(f"input without path/sha256: {b!r}")
    if tuple(sorted(spec.get("gates") or {})) != tuple(sorted(GATE_IDS)):
        raise FrozenBenchmarkError(f"gate set changed: {sorted(spec.get('gates') or {})}")
    params = spec.get("parameters") or {}
    if params.get("coordinate_precision") != 4:
        raise FrozenBenchmarkError("coordinate precision changed")
    if params.get("max_coincident_cell_share") != 0.01:
        raise FrozenBenchmarkError("coincident-cell bar changed")
    if params.get("label_language_min_share") != 0.8:
        raise FrozenBenchmarkError("label-language bar changed")
    lex = spec.get("function_word_lexicon") or {}
    if sorted(lex) != sorted(LANGUAGES):
        raise FrozenBenchmarkError(f"lexicon languages changed: {sorted(lex)}")
    for lang in LANGUAGES:
        if not lex.get(lang):
            raise FrozenBenchmarkError(f"lexicon for {lang} is empty")


def attribution(spec: dict | None = None) -> dict[str, frozenset[str]]:
    """token -> frozenset of languages it belongs to.

    A word listed under two languages is multi-language and can never, on its
    own, condemn a cluster label: only a word belonging to exactly one of
    de/fr/it is admissible language evidence.
    """
    spec = spec or load_frozen()
    lex = spec.get("function_word_lexicon") or {}
    out: dict[str, frozenset[str]] = {}
    for lang in LANGUAGES:
        for word in lex.get(lang, ()):
            out[word] = out.get(word, frozenset()) | {lang}
    return {word: frozenset(langs) for word, langs in out.items()}


def infer_query_language(text: object, spec: dict | None = None) -> tuple[str, dict]:
    """Frozen query-language rule. Returns ``(language, votes)``.

    ``language`` is ``"unknown"`` when no language collects an exclusive token
    or when the top count is tied; language-dependent gates are then
    ``not_measurable`` with a reason and never count as passes.
    """
    spec = spec or load_frozen()
    attr = attribution(spec)
    votes = {lang: 0 for lang in LANGUAGES}
    for token in tokenize(text):
        langs = attr.get(token)
        if langs and len(langs) == 1:
            votes[next(iter(langs))] += 1
    top = max(votes.values())
    if top == 0:
        return "unknown", votes
    winners = [lang for lang, count in votes.items() if count == top]
    if len(winners) != 1:
        return "unknown", votes
    return winners[0], votes


def bundle_specs(spec: dict | None = None) -> list[dict]:
    spec = spec or load_frozen()
    return list(spec.get("inputs") or [])


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
