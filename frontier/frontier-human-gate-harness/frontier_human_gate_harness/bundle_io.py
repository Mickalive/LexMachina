"""query_result_bundle loading, contract validation and content hashing.

Reuse-first: the field contract below is a *mirror* of the accepted product
contract (``product/query/bundle.py`` and ``docs/product/QUERY_MAP_MVP.md``).
When the accepted product package is available on disk its validator is executed
too and the results are reported alongside the local mirror (see
:func:`product_contract_errors`); this team never modifies product code.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

TEAM_ID = "frontier-human-gate-harness"

BUNDLE_REQUIRED_TOP = ["bundle_version", "query", "query_variants", "answer",
                       "decisions", "clusters", "relations", "provenance"]
BUNDLE_REQUIRED_DECISION = ["decision_id", "court", "language", "rank", "score",
                            "provenance", "snippet", "cluster_id", "x", "y",
                            "counter_status", "canonical_url", "citation"]

#: Fields the charter stop rule names for a conventional ranked list.
STOP_RULE_FIELDS = ["rank", "court", "decision_date", "language", "citation", "canonical_url"]
#: Fields acceptance test (1) additionally requires to be rendered.
EXTRA_RENDER_FIELDS = ["decision_id", "snippet"]
CONVENTIONAL_FIELDS = STOP_RULE_FIELDS + EXTRA_RENDER_FIELDS

PRODUCT_CANDIDATES = [
    Path("/tmp/lex_accepted/core/product/product/query/bundle.py"),
    Path(__file__).resolve().parents[3] / "product" / "query" / "bundle.py",
]


class BundleError(ValueError):
    """Bundle cannot be loaded or violates the product bundle contract."""


class MissingBundleFieldError(BundleError):
    """Bundle lacks a field a conventional ranked list needs (charter TERMINATE rule)."""

    def __init__(self, fields: list[str]):
        self.fields = sorted(fields)
        super().__init__(
            "PRODUCT CONTRACT DEFECT: query_result_bundle lacks conventional "
            f"ranked-list field(s): {', '.join(self.fields)}. "
            "Charter stop rule: terminate and report the exact missing bundle "
            "field instead of inventing data."
        )


def canonical_json(obj: Any) -> str:
    """Single canonical JSON form used for every hash in this team."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def bundle_sha256(bundle: dict) -> str:
    return sha256_text(canonical_json(bundle))


def query_sha256(bundle_or_query: Any) -> str:
    query = bundle_or_query if isinstance(bundle_or_query, str) else bundle_or_query.get("query", "")
    return sha256_text(query or "")


def load_bundle(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise BundleError(f"bundle fixture not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BundleError(f"bundle is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BundleError(f"bundle must be a JSON object: {path}")
    return data


def validate_bundle_mirror(bundle: dict) -> list[str]:
    """Local mirror of the accepted product validator (same rules, same wording)."""
    errors = [f"missing top-level key: {k}" for k in BUNDLE_REQUIRED_TOP if k not in bundle]
    if errors:
        return errors
    if not isinstance(bundle.get("decisions"), list) or not bundle["decisions"]:
        return ["decisions must be a non-empty list"]
    ids: set[Any] = set()
    for i, d in enumerate(bundle["decisions"]):
        for key in BUNDLE_REQUIRED_DECISION:
            if key not in d:
                errors.append(f"decision[{i}] missing key: {key}")
        did = d.get("decision_id")
        if did in ids:
            errors.append(f"duplicate decision_id: {did}")
        ids.add(did)
    cited = set((bundle.get("answer") or {}).get("cited_decision_ids") or [])
    unknown = cited - ids
    if unknown:
        errors.append(f"answer cites unknown decision_ids: {sorted(unknown)}")
    for c in bundle.get("clusters", []):
        if "cluster_id" not in c or "label" not in c:
            errors.append(f"cluster missing id/label: {c}")
    return errors


def product_contract_errors(bundle: dict) -> list[str] | None:
    """Run the accepted product validator when it is on disk; None if unavailable."""
    for candidate in PRODUCT_CANDIDATES:
        if not candidate.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("_lex_accepted_query_bundle", candidate)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            validator = getattr(module, "validate_bundle", None)
            if callable(validator):
                return list(validator(bundle))
        except Exception:  # pragma: no cover - optional reuse path, never fatal
            continue
    return None


def missing_conventional_fields(bundle: dict) -> list[str]:
    """Conventional fields absent (as a key) from at least one rendered decision."""
    decisions = bundle.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        return list(CONVENTIONAL_FIELDS)
    missing: set[str] = set()
    for d in decisions:
        if not isinstance(d, dict):
            missing.update(CONVENTIONAL_FIELDS)
            continue
        for field in CONVENTIONAL_FIELDS:
            if field not in d:
                missing.add(field)
    return sorted(missing)


def require_conventional_fields(bundle: dict) -> None:
    """Charter TERMINATE rule: never invent a missing ranked-list field."""
    missing = missing_conventional_fields(bundle)
    if missing:
        raise MissingBundleFieldError(missing)


def load_and_check(path: str | Path) -> dict:
    """Load a bundle, enforce the conventional-field contract, return it."""
    bundle = load_bundle(path)
    require_conventional_fields(bundle)
    return bundle
