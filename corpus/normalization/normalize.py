"""
Normalization pipeline: convert raw OpenCaseLaw decisions to LexMachina canonical schema.
Preserves provenance and enables reproducible corpus construction.
"""
import hashlib
import json
import jsonschema
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
from urllib.parse import urlparse

from corpus.acquisition.opencaselaw_client import DecisionRaw, OpenCaseLawClient, AcquisitionConfig


@dataclass
class NormalizationStats:
    """Statistics from a normalization run."""
    total_input: int = 0
    total_output: int = 0
    validation_errors: int = 0
    deduplicated: int = 0
    missing_full_text: int = 0
    missing_structure: int = 0
    missing_citations: int = 0
    by_language: Dict[str, int] = None
    by_year: Dict[str, int] = None
    by_court: Dict[str, int] = None
    by_branch: Dict[str, int] = None

    def __post_init__(self):
        if self.by_language is None:
            self.by_language = {}
        if self.by_year is None:
            self.by_year = {}
        if self.by_court is None:
            self.by_court = {}
        if self.by_branch is None:
            self.by_branch = {}


class DecisionNormalizer:
    """Normalize raw decisions to canonical schema with provenance."""

    def __init__(self, schema_path: str = "corpus/schema/decision_schema.json"):
        with open(schema_path, "r") as f:
            self.schema = json.load(f)
        self.validator = jsonschema.Draft7Validator(self.schema)
        self.seen_hashes = set()

    # Mapping dictionaries for API -> canonical values
    BRANCH_MAP = {
        "straf": "strafrecht",
        "zivil": "zivilrecht",
        "oeffentlich": "oeffentliches_recht",
        "sozialversicherung": "sozialversicherungsrecht",
        "null": "null"
    }

    OUTCOME_MAP = {
        "gutgeheissen": "gutgeheissen",
        "abgewiesen": "abgewiesen",
        "teilweise_gutgeheissen": "teilweise_gutgeheissen",
        "erledigt": "erledigt",
        "nichteintreten": "nichteintreten",
        "zurueckgewiesen": "zurueckgewiesen",
        "inadmissible": "nichteintreten",
        "dismissed": "abgewiesen",
        "approved": "gutgeheissen",
        "partially_approved": "teilweise_gutgeheissen",
        "null": "null"
    }

    DECISION_TYPE_MAP = {
        "Leitentscheid": "Leitentscheid",
        "Endentscheid": "Endentscheid",
        "Zwischenentscheid": "Zwischenentscheid",
        "Verfahrensentscheid": "Verfahrensentscheid",
        "null": "null"
    }

    def _parse_list_field(self, value: Any) -> List[str]:
        """Parse a field that may be a JSON string representation of a list."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            # Try to parse as JSON array
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except json.JSONDecodeError:
                pass
            # Fallback: split by comma
            return [v.strip() for v in value.split(",") if v.strip()]
        return [str(value)]

    def _map_branch(self, branch: Optional[str]) -> str:
        if not branch:
            return "null"
        branch_lower = branch.lower().strip()
        return self.BRANCH_MAP.get(branch_lower, "null")

    def _map_outcome(self, outcome: Optional[str]) -> str:
        if not outcome:
            return "null"
        outcome_lower = outcome.lower().strip()
        return self.OUTCOME_MAP.get(outcome_lower, "null")

    def _map_decision_type(self, dtype: Optional[str]) -> str:
        if not dtype:
            return "null"
        return self.DECISION_TYPE_MAP.get(dtype, "null")

    def _normalize_erwaegungen(self, erwaegungen: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """Normalize Erwägungen structure from API format to canonical format."""
        if not erwaegungen:
            return None
        normalized = []
        for e in erwaegungen:
            normalized.append({
                "e_number": e.get("e_number"),
                "depth": e.get("depth", 1),
                "parent": e.get("parent"),
                "text": e.get("text_excerpt") or e.get("text", ""),
                "text_chars": e.get("text_chars", len(e.get("text_excerpt", "") or e.get("text", "")))
            })
        return normalized

    def _normalize_citations(self, citations: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """Normalize citations to canonical format."""
        if not citations:
            return None
        normalized = []
        for c in citations:
            normalized.append({
                "target_decision_id": c.get("target_decision_id"),
                "target_ref": c.get("target_ref"),
                "target_type": c.get("target_type"),
                "docket_number": c.get("docket_number"),
                "court": c.get("court"),
                "decision_date": c.get("decision_date"),
                "mention_count": c.get("mention_count", 1),
                "confidence_score": c.get("confidence_score", 1.0)
            })
        return normalized

    def _normalize_incoming_citations(self, citations: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """Normalize incoming citations to canonical format."""
        if not citations:
            return None
        normalized = []
        for c in citations:
            normalized.append({
                "source_decision_id": c.get("source_decision_id"),
                "target_ref": c.get("target_ref"),
                "docket_number": c.get("docket_number"),
                "court": c.get("court"),
                "decision_date": c.get("decision_date"),
                "mention_count": c.get("mention_count", 1),
                "confidence_score": c.get("confidence_score", 1.0)
            })
        return normalized

    def _normalize_preparatory_materials(self, materials: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """Normalize preparatory materials (Botschaft references)."""
        if not materials:
            return None
        normalized = []
        for m in materials:
            normalized.append({
                "law": m.get("law"),
                "article": m.get("article"),
                "sr_number": m.get("sr_number"),
                "bbl_citations": m.get("bbl_citations", [])
            })
        return normalized

    def normalize(self, raw: DecisionRaw, source_version: str) -> Optional[Dict[str, Any]]:
        """Convert DecisionRaw to canonical schema. Returns None if should be skipped."""
        # Skip if no full text
        if not raw.full_text or len(raw.full_text.strip()) < 50:
            return None

        # Deduplication by content hash
        if raw.content_hash and raw.content_hash in self.seen_hashes:
            return None
        if raw.content_hash:
            self.seen_hashes.add(raw.content_hash)

        # Extract year for stats
        year = raw.decision_date[:4] if raw.decision_date else "unknown"

        # Map fields to canonical values
        branch = self._map_branch(raw.branch)
        outcome = self._map_outcome(raw.outcome)
        decision_type = self._map_decision_type(raw.decision_type)
        cited_decisions = self._parse_list_field(raw.cited_decisions)
        cited_laws = self._parse_list_field(raw.cited_laws)
        judges = self._parse_list_field(raw.judges)

        # Normalize structural fields
        erwaegungen = self._normalize_erwaegungen(raw.erwaegungen)
        outgoing_citations = self._normalize_citations(raw.outgoing_citations)
        incoming_citations = self._normalize_incoming_citations(raw.incoming_citations)
        preparatory_materials = self._normalize_preparatory_materials(raw.preparatory_materials)

        # Track missing data for stats
        has_structure = bool(raw.sachverhalt or raw.erwaegungen or raw.dispositiv)
        has_citations = bool(raw.outgoing_citations or raw.incoming_citations)

        # Build canonical decision
        canonical = {
            "decision_id": raw.decision_id,
            "court": raw.court,
            "docket_number": raw.docket_number or raw.decision_id,
            "decision_date": raw.decision_date,
            "publication_date": raw.publication_date,
            "language": raw.language,
            "title": raw.title,
            "legal_area": raw.legal_area,
            "chamber": raw.chamber,
            "branch": branch,
            "proceeding_type": raw.proceeding_type,
            "regeste": raw.regeste,
            "abstract_de": raw.abstract_de,
            "abstract_fr": raw.abstract_fr,
            "abstract_it": raw.abstract_it,
            "full_text": raw.full_text,
            "text_length": len(raw.full_text) if raw.full_text else 0,
            "outcome": outcome,
            "decision_type": decision_type,
            "bge_reference": raw.bge_reference,
            "cited_decisions": cited_decisions,
            "cited_laws": cited_laws,
            "judges": judges,
            "source_url": raw.source_url,
            "pdf_url": raw.pdf_url,
            "sachverhalt": raw.sachverhalt,
            "erwaegungen": erwaegungen,
            "dispositiv": raw.dispositiv,
            "dispositiv_orders": raw.dispositiv_orders,
            "preparatory_materials": preparatory_materials,
            "outgoing_citations": outgoing_citations,
            "incoming_citations": incoming_citations,
            "provenance": {
                "source": "opencaselaw_api",
                "acquired_at": datetime.now(timezone.utc).isoformat(),
                "source_version": source_version,
                "content_hash": raw.content_hash or hashlib.sha256(raw.full_text.encode()).hexdigest(),
                "api_endpoint": f"/api/decisions/{raw.decision_id}",
                "raw_metadata": {
                    "citation_string_de": raw.citation_string_de,
                    "canonical_url": raw.canonical_url,
                    "decision_id": raw.decision_id,
                    "court": raw.court,
                    "raw_branch": raw.branch,
                    "raw_outcome": raw.outcome,
                    "raw_decision_type": raw.decision_type,
                    "raw_cited_decisions": raw.cited_decisions,
                    "raw_cited_laws": raw.cited_laws,
                    "has_structure": has_structure,
                    "has_citations": has_citations,
                    "raw_sachverhalt_chars": len(raw.sachverhalt) if raw.sachverhalt else 0,
                    "raw_erwaegungen_count": len(raw.erwaegungen) if raw.erwaegungen else 0,
                    "raw_outgoing_citations": len(raw.outgoing_citations) if raw.outgoing_citations else 0,
                    "raw_incoming_citations": len(raw.incoming_citations) if raw.incoming_citations else 0
                }
            }
        }

        # Validate against schema
        errors = list(self.validator.iter_errors(canonical))
        if errors:
            raise ValueError(f"Validation failed for {raw.decision_id}: {errors}")

        return canonical

    def normalize_batch(
        self,
        raw_decisions: List[DecisionRaw],
        source_version: str
    ) -> Iterator[Dict[str, Any]]:
        """Normalize a batch of decisions, yielding valid ones."""
        for raw in raw_decisions:
            try:
                normalized = self.normalize(raw, source_version)
                if normalized:
                    yield normalized
            except Exception as e:
                print(f"Warning: Failed to normalize {raw.decision_id}: {e}")
                continue


def load_raw_decisions(jsonl_path: str) -> List[DecisionRaw]:
    """Load raw decisions from JSONL file."""
    from corpus.acquisition.opencaselaw_client import DecisionRaw
    decisions = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            decisions.append(DecisionRaw(**data))
    return decisions


def write_canonical_decisions(
    decisions: Iterator[Dict[str, Any]],
    output_path: str,
    stats: NormalizationStats
) -> NormalizationStats:
    """Write canonical decisions to JSONL and update stats."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for decision in decisions:
            f.write(json.dumps(decision, ensure_ascii=False) + "\n")
            stats.total_output += 1

            # Update stats
            lang = decision.get("language", "unknown")
            stats.by_language[lang] = stats.by_language.get(lang, 0) + 1

            year = decision.get("decision_date", "unknown")[:4]
            stats.by_year[year] = stats.by_year.get(year, 0) + 1

            court = decision.get("court", "unknown")
            stats.by_court[court] = stats.by_court.get(court, 0) + 1

            branch = decision.get("branch", "unknown")
            stats.by_branch[branch] = stats.by_branch.get(branch, 0) + 1

    return stats


def run_normalization(
    input_path: str,
    output_path: str,
    source_version: str,
    schema_path: str = "corpus/schema/decision_schema.json"
) -> NormalizationStats:
    """Run full normalization pipeline on a raw JSONL file."""
    print(f"Loading raw decisions from {input_path}...")
    raw_decisions = load_raw_decisions(input_path)

    stats = NormalizationStats()
    stats.total_input = len(raw_decisions)

    print(f"Normalizing {len(raw_decisions)} decisions...")
    normalizer = DecisionNormalizer(schema_path)

    normalized = normalizer.normalize_batch(raw_decisions, source_version)
    stats = write_canonical_decisions(normalized, output_path, stats)

    print(f"Normalization complete:")
    print(f"  Input: {stats.total_input}")
    print(f"  Output: {stats.total_output}")
    print(f"  Skipped (dedup/empty): {stats.total_input - stats.total_output}")
    print(f"  By language: {stats.by_language}")
    print(f"  By year: {dict(sorted(stats.by_year.items()))}")
    print(f"  By court: {stats.by_court}")
    print(f"  By branch: {stats.by_branch}")

    return stats


if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "corpus/acquisition/raw/bger_test_slice.jsonl"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "corpus/normalization/canonical/bger_test_slice.jsonl"
    source_version = sys.argv[3] if len(sys.argv) > 3 else "opencaselaw_api_2026-08-26"

    run_normalization(input_file, output_file, source_version)