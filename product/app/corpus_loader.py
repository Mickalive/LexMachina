"""
LexMachina Corpus Loader
Loads canonical JSONL decisions from the corpus lane and provides
a clean interface for product use.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Iterator
from dataclasses import dataclass, field, asdict


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

    def load(self) -> int:
        """Load all JSONL files from corpus_dir. Returns count of loaded decisions."""
        if self._loaded:
            return len(self.decisions)

        jsonl_files = sorted(self.corpus_dir.glob("*.jsonl"))
        for jsonl_file in jsonl_files:
            self._load_jsonl(jsonl_file)

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
