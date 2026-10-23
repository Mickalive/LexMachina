"""Known-counter-authority fixture and frozen id matcher (product-owned).

Why this exists
---------------
Direction v63 ordered item 7(a) and the accepted cached counter-surface
falsification (anchor run 39838415410) both need the product to say how many
*known* counter authorities its own cached pools actually reach and signal.
The evaluation lane owns the frozen benchmark; this module owns a tiny,
read-only copy of its 28 ids plus the frozen id-match rule, so a product
measurement can run without importing evaluation code and without editing a
frozen artifact.

The rule is re-stated, not re-derived: the source sha256 is recorded in
``product/data/known_counter_authorities_v1.json`` and in every emitted
measurement.  The ids are a SAMPLE, never a recall ground truth.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "product" / "data" / "known_counter_authorities_v1.json"
SCHEMA = "product-known-counter-authorities/1"

#: Frozen ``id_match_rules.method``: strip repeated leading court tokens after
#: lowercasing and dropping every non-alphanumeric character.  Order matters:
#: the longest tokens are tried first.
_LEADING_COURT_RE = re.compile(r"^(?:bgestger|bstger|bger|bge|bg)+")
#: Frozen ``id_match_rules.min_core_length``: a core shorter than this is
#: never allowed to match (a short id would match too many unrelated rows).
MIN_CORE_LENGTH = 6
_ROW_ID_FIELDS = (
    "decision_id",
    "canonical_decision_id",
    "docket_number",
    "citation_string_de",
    "citation_string_fr",
    "citation_string_it",
)


def alnum_core(value: str) -> str:
    """Frozen alnum-core of an id/citation string."""
    core = re.sub(r"[^a-z0-9]", "", str(value or "").lower())
    return _LEADING_COURT_RE.sub("", core)


def row_id_cores(row: dict) -> set[str]:
    """All frozen alnum-cores a rendered row may answer to."""
    return {
        alnum_core(row.get(field))
        for field in _ROW_ID_FIELDS
        if str(row.get(field) or "").strip()
    }


def matches(frozen_id: str, row: dict) -> bool:
    """True when the frozen id's core equals any of the row's id cores."""
    want = alnum_core(frozen_id)
    if len(want) < MIN_CORE_LENGTH:
        return False
    return want in row_id_cores(row)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fixture(path: Path | None = None) -> dict:
    """Load and minimally validate the product fixture (never the evaluation file)."""
    fixture_path = Path(path) if path is not None else FIXTURE_PATH
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"unexpected fixture schema: {data.get('schema')!r}")
    questions = data.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise ValueError("fixture carries no questions")
    for slug, entry in questions.items():
        ids = (entry or {}).get("known_counter_ids")
        if not isinstance(ids, list) or not all(isinstance(x, str) and x for x in ids):
            raise ValueError(f"fixture question {slug!r} carries no id list")
    data["_fixture_path"] = str(fixture_path)
    data["_fixture_sha256"] = sha256_file(fixture_path)
    return data


def known_ids(fixture: dict, slug: str) -> list[str]:
    return list(((fixture.get("questions") or {}).get(slug) or {})
                .get("known_counter_ids") or [])


__all__ = [
    "FIXTURE_PATH",
    "MIN_CORE_LENGTH",
    "SCHEMA",
    "alnum_core",
    "known_ids",
    "load_fixture",
    "matches",
    "row_id_cores",
    "sha256_file",
]
