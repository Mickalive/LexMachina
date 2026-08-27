"""
LexMachina Corpus Loader
Loads canonical JSONL decisions from the corpus lane and provides
a clean interface for product use.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Iterator, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import hashlib

from .schema_validator import SchemaValidator, ValidationResult


@dataclass
class Decision:
    """Canonical decision object for product use."""
    decision_id: str
    court: str
    docket_number: str
    decision_date: str
    language: str
    full_text: str
    title: Optional[str] = None
    legal_area: Optional[str] = None
    branch: Optional[str] = None
    chamber: Optional[str] = None
    outcome: Optional[str] = None
    decision_type: Optional[str] = None
    bge_reference: Optional[str] = None
    cited_decisions: List[str] = field(default_factory=list)
    cited_laws: List[str] = field(default_factory=list)
    sachverhalt: Optional[str] = None
    erwaegungen: Optional[List[Dict]] = None
    dispositiv: Optional[str] = None
    text_length: int = 0
    provenance: Dict = field(default_factory=dict)

    def to_summary(self) -> Dict:
        """Return a compact summary for map display."""
        return {
            "decision_id": self.decision_id,
            "docket_number": self.docket_number,
            "decision_date": self.decision_date,
            "language": self.language,
            "title": self.title or self.docket_number,
            "legal_area": self.legal_area,
            "branch": self.branch,
            "chamber": self.chamber,
            "outcome": self.outcome,
            "text_length": self.text_length,
        }

    def to_full(self) -> Dict:
        """Return full decision details for inspection."""
        d = asdict(self)
        # Truncate full_text for API responses
        if len(d.get("full_text", "")) > 2000:
            d["full_text"] = d["full_text"][:2000] + "... [truncated]"
        return d


class CorpusLoader:
    """Loads and indexes canonical JSONL corpus files."""

    def __init__(self, corpus_dir: str):
        self.corpus_dir = Path(corpus_dir)
        self.decisions: Dict[str, Decision] = {}
        self._loaded = False
        self._user_import_count = 0
        self._user_import_dir = self.corpus_dir.parent / "user_imports"
        self._schema_validator = SchemaValidator()

    def load(self) -> int:
        """Load all JSONL files from corpus_dir and user imports. Returns count of loaded decisions."""
        if self._loaded:
            return len(self.decisions)

        jsonl_files = sorted(self.corpus_dir.glob("*.jsonl"))
        for jsonl_file in jsonl_files:
            self._load_jsonl(jsonl_file)

        # Also load any previously imported user corpus
        self.load_user_imports()

        self._loaded = True
        return len(self.decisions)

    def _load_jsonl(self, filepath: Path) -> None:
        """Load a single JSONL file."""
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    decision = self._parse_record(record)
                    if decision:
                        self.decisions[decision.decision_id] = decision
                except json.JSONDecodeError:
                    continue

    def _parse_record(self, record: Dict) -> Optional[Decision]:
        """Parse a JSONL record into a Decision object."""
        try:
            return Decision(
                decision_id=record.get("decision_id", ""),
                court=record.get("court", "bger"),
                docket_number=record.get("docket_number", ""),
                decision_date=record.get("decision_date", ""),
                language=record.get("language", "de"),
                full_text=record.get("full_text", ""),
                title=record.get("title"),
                legal_area=record.get("legal_area"),
                branch=record.get("branch"),
                chamber=record.get("chamber"),
                outcome=record.get("outcome"),
                decision_type=record.get("decision_type"),
                bge_reference=record.get("bge_reference"),
                cited_decisions=record.get("cited_decisions", []),
                cited_laws=record.get("cited_laws", []),
                sachverhalt=record.get("sachverhalt"),
                erwaegungen=record.get("erwaegungen"),
                dispositiv=record.get("dispositiv"),
                text_length=record.get("text_length", len(record.get("full_text", ""))),
                provenance=record.get("provenance", {}),
            )
        except Exception:
            return None

    def get(self, decision_id: str) -> Optional[Decision]:
        """Get a decision by ID."""
        return self.decisions.get(decision_id)

    def get_summary(self, decision_id: str) -> Optional[Dict]:
        """Get a decision summary by ID."""
        d = self.get(decision_id)
        return d.to_summary() if d else None

    def get_full(self, decision_id: str) -> Optional[Dict]:
        """Get full decision details by ID."""
        d = self.get(decision_id)
        return d.to_full() if d else None

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Simple text search across decisions."""
        query_lower = query.lower()
        results = []
        for d in self.decisions.values():
            if (query_lower in (d.full_text or "").lower() or
                query_lower in (d.title or "").lower() or
                query_lower in (d.docket_number or "").lower()):
                results.append(d.to_summary())
                if len(results) >= limit:
                    break
        return results

    def get_all_ids(self) -> List[str]:
        """Return all decision IDs in insertion order."""
        return list(self.decisions.keys())

    def get_all_summaries(self) -> List[Dict]:
        """Return summaries of all decisions."""
        return [d.to_summary() for d in self.decisions.values()]

    def get_all_decisions(self) -> List[Dict]:
        """Return full details of all decisions (for TF-IDF model building)."""
        return [d.to_full() for d in self.decisions.values()]

    def get_by_language(self, language: str) -> List[Dict]:
        """Get decisions filtered by language."""
        return [d.to_summary() for d in self.decisions.values() if d.language == language]

    def get_by_branch(self, branch: str) -> List[Dict]:
        """Get decisions filtered by branch."""
        return [d.to_summary() for d in self.decisions.values() if d.branch == branch]

    @property
    def size(self) -> int:
        return len(self.decisions)

    @property
    def languages(self) -> Dict[str, int]:
        """Count decisions by language."""
        counts = {}
        for d in self.decisions.values():
            counts[d.language] = counts.get(d.language, 0) + 1
        return counts

    @property
    def branches(self) -> Dict[str, int]:
        """Count decisions by branch."""
        counts = {}
        for d in self.decisions.values():
            b = d.branch or "unknown"
            counts[b] = counts.get(b, 0) + 1
        return counts

    @property
    def user_import_count(self) -> int:
        """Number of decisions loaded from user imports."""
        return self._user_import_count

    def import_records(self, records: List[Dict], strict_validation: bool = False) -> Dict:
        """Import user records into the corpus.

        Validates each record against the canonical schema, persists to
        a user-import JSONL file, and loads into the in-memory index.
        Returns import statistics.
        """
        if not self._loaded:
            self.load()

        # Ensure user import directory exists
        self._user_import_dir.mkdir(parents=True, exist_ok=True)

        imported = 0
        skipped = 0
        errors = []
        warnings = []
        imported_ids = []

        for i, record in enumerate(records):
            # Validate against schema
            result: ValidationResult = self._schema_validator.validate(record, strict=strict_validation)
            
            if not result.valid:
                errors.append(f"Record {i} ({record.get('decision_id', 'unknown')}): {'; '.join(result.errors)}")
                skipped += 1
                continue

            if result.warnings:
                warnings.append(f"Record {i} ({record.get('decision_id', 'unknown')}): {'; '.join(result.warnings)}")

            decision_id = result.normalized_record["decision_id"]
            if decision_id in self.decisions:
                skipped += 1
                continue

            # Create decision from normalized record
            decision = self._parse_record(result.normalized_record)
            if decision:
                self.decisions[decision.decision_id] = decision
                imported_ids.append(decision.decision_id)
                imported += 1
            else:
                errors.append(f"Record {i} ({decision_id}): failed to parse normalized record")
                skipped += 1

        # Persist imported records
        if imported > 0:
            import_file = self._user_import_dir / "user_corpus.jsonl"
            with open(import_file, "a", encoding="utf-8") as f:
                for did in imported_ids:
                    d = self.decisions[did]
                    record = {
                        "decision_id": d.decision_id,
                        "court": d.court,
                        "docket_number": d.docket_number,
                        "decision_date": d.decision_date,
                        "language": d.language,
                        "full_text": d.full_text,
                        "title": d.title,
                        "legal_area": d.legal_area,
                        "branch": d.branch,
                        "chamber": d.chamber,
                        "outcome": d.outcome,
                        "decision_type": d.decision_type,
                        "bge_reference": d.bge_reference,
                        "cited_decisions": d.cited_decisions,
                        "cited_laws": d.cited_laws,
                        "sachverhalt": d.sachverhalt,
                        "erwaegungen": d.erwaegungen,
                        "dispositiv": d.dispositiv,
                        "text_length": d.text_length,
                        "provenance": {**d.provenance, "source": "user_import"},
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

        self._user_import_count += imported

        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:20],
            "warnings": warnings[:20],
            "total_decisions": self.size,
            "imported_ids": imported_ids[:50],
        }

    def load_user_imports(self) -> int:
        """Load previously imported user corpus files."""
        if not self._user_import_dir.exists():
            return 0

        count = 0
        for jsonl_file in self._user_import_dir.glob("*.jsonl"):
            before = len(self.decisions)
            self._load_jsonl(jsonl_file)
            count += len(self.decisions) - before

        self._user_import_count += count
        return count

    def get_corpus_stats(self) -> Dict:
        """Get detailed corpus statistics including coverage."""
        return {
            "total_decisions": self.size,
            "languages": self.languages,
            "branches": self.branches,
            "user_imports": self._user_import_count,
            "canonical_decisions": self.size - self._user_import_count,
        }