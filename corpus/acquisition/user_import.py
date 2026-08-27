"""
User corpus import prototype.
Converts user-provided case law in various formats (JSON, JSONL, PDF-extracted text)
to LexMachina canonical schema with full provenance tracking.
"""
import hashlib
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator

import jsonschema

from corpus.normalization.normalize import DecisionNormalizer


@dataclass
class UserImportConfig:
    """Configuration for user corpus import."""
    schema_path: str = "corpus/schema/decision_schema.json"
    source_label: str = "user_upload"
    default_language: str = "de"
    default_court: str = "bger"
    min_text_length: int = 50


class UserCorpusImporter:
    """Import user-provided case law into canonical schema."""
    
    def __init__(self, config: Optional[UserImportConfig] = None):
        self.config = config or UserImportConfig()
        self.normalizer = DecisionNormalizer(self.config.schema_path)
        self.import_stats = {
            "total_input": 0,
            "total_output": 0,
            "validation_errors": 0,
            "by_format": {},
        }
    
    def import_jsonl(self, input_path: str) -> Iterator[Dict[str, Any]]:
        """Import from JSONL file where each line is a JSON decision."""
        self.import_stats["by_format"]["jsonl"] = self.import_stats["by_format"].get("jsonl", 0)
        
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.import_stats["total_input"] += 1
                try:
                    data = json.loads(line)
                    canonical = self._normalize_user_decision(data, "user_jsonl")
                    if canonical:
                        self.import_stats["total_output"] += 1
                        self.import_stats["by_format"]["jsonl"] += 1
                        yield canonical
                except json.JSONDecodeError:
                    self.import_stats["validation_errors"] += 1
                except Exception as e:
                    self.import_stats["validation_errors"] += 1
    
    def import_json(self, input_path: str) -> Iterator[Dict[str, Any]]:
        """Import from JSON file containing an array of decisions."""
        self.import_stats["by_format"]["json"] = self.import_stats["by_format"].get("json", 0)
        
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            data = [data]
        
        for item in data:
            self.import_stats["total_input"] += 1
            try:
                canonical = self._normalize_user_decision(item, "user_json")
                if canonical:
                    self.import_stats["total_output"] += 1
                    self.import_stats["by_format"]["json"] += 1
                    yield canonical
            except Exception as e:
                self.import_stats["validation_errors"] += 1
    
    def import_text_files(self, input_dir: str) -> Iterator[Dict[str, Any]]:
        """Import from directory of text files (one decision per file)."""
        self.import_stats["by_format"]["text_files"] = self.import_stats["by_format"].get("text_files", 0)
        
        input_path = Path(input_dir)
        for file_path in sorted(input_path.glob("*.txt")):
            self.import_stats["total_input"] += 1
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                
                # Infer metadata from filename
                filename = file_path.stem
                data = {
                    "full_text": text,
                    "title": filename,
                    "decision_id": f"user_{filename}",
                }
                
                # Try to extract date from filename (YYYY-MM-DD or YYYYMMDD patterns)
                date_match = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', filename)
                if date_match:
                    data["decision_date"] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                
                canonical = self._normalize_user_decision(data, "user_text")
                if canonical:
                    self.import_stats["total_output"] += 1
                    self.import_stats["by_format"]["text_files"] += 1
                    yield canonical
            except Exception as e:
                self.import_stats["validation_errors"] += 1
    
    def import_raw_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Import a single raw text with optional metadata."""
        self.import_stats["total_input"] += 1
        
        data = {
            "full_text": text,
            **(metadata or {}),
        }
        
        if "decision_id" not in data:
            data["decision_id"] = f"user_{hashlib.sha256(text.encode()).hexdigest()[:16]}"
        
        canonical = self._normalize_user_decision(data, "user_text")
        if canonical:
            self.import_stats["total_output"] += 1
            return canonical
        
        self.import_stats["validation_errors"] += 1
        return None
    
    def _normalize_user_decision(
        self,
        data: Dict[str, Any],
        source_type: str
    ) -> Optional[Dict[str, Any]]:
        """Normalize a user-provided decision dict to canonical schema."""
        from corpus.acquisition.opencaselaw_client import DecisionRaw
        
        # Map user fields to our schema
        full_text = (
            data.get("full_text") or 
            data.get("text") or 
            data.get("content") or
            data.get("decision_text") or
            ""
        )
        
        if not full_text or len(full_text.strip()) < self.config.min_text_length:
            return None
        
        # Generate content hash
        content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
        
        # Note: Deduplication is handled by normalizer.normalize() via seen_hashes.
        # Do NOT pre-add here or the normalizer will see it as a duplicate.
        
        # Build decision_id
        decision_id = data.get("decision_id") or data.get("id") or f"user_{content_hash[:16]}"
        
        # Parse date
        decision_date = data.get("decision_date") or data.get("date") or ""
        if not decision_date:
            decision_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Parse language
        language = data.get("language") or self.config.default_language
        if len(str(language)) > 2:
            lang_map = {"german": "de", "french": "fr", "italian": "it"}
            language = lang_map.get(str(language).lower(), self.config.default_language)[:2]
        
        # Create DecisionRaw
        raw = DecisionRaw(
            decision_id=str(decision_id),
            court=data.get("court") or self.config.default_court,
            decision_date=str(decision_date)[:10],
            language=str(language)[:2],
            title=data.get("title"),
            regeste=data.get("regeste"),
            citation_string_de=data.get("citation_string_de"),
            canonical_url=data.get("source_url") or data.get("url") or f"user://{decision_id}",
            full_text=full_text,
            legal_area=data.get("legal_area"),
            chamber=data.get("chamber"),
            branch=data.get("branch"),
            proceeding_type=data.get("proceeding_type"),
            abstract_de=data.get("abstract_de"),
            abstract_fr=data.get("abstract_fr"),
            abstract_it=data.get("abstract_it"),
            outcome=data.get("outcome"),
            decision_type=data.get("decision_type"),
            bge_reference=data.get("bge_reference"),
            cited_decisions=data.get("cited_decisions"),
            cited_laws=data.get("cited_laws"),
            judges=data.get("judges"),
            source_url=data.get("source_url"),
            pdf_url=data.get("pdf_url"),
            publication_date=data.get("publication_date"),
            docket_number=data.get("docket_number") or decision_id,
            content_hash=content_hash,
            sachverhalt=data.get("sachverhalt"),
            erwaegungen=data.get("erwaegungen"),
            dispositiv=data.get("dispositiv"),
            dispositiv_orders=data.get("dispositiv_orders"),
            preparatory_materials=data.get("preparatory_materials"),
            outgoing_citations=data.get("outgoing_citations"),
            incoming_citations=data.get("incoming_citations"),
        )
        
        try:
            # Override source in provenance
            canonical = self.normalizer.normalize(raw, f"{source_type}_{datetime.now(timezone.utc).strftime('%Y%m%d')}")
            if canonical:
                canonical["provenance"]["source"] = self.config.source_label
                return canonical
        except Exception:
            return None
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Return import statistics."""
        return dict(self.import_stats)


def run_user_import(
    input_path: str,
    output_path: str,
    input_format: str = "auto",
    config: Optional[UserImportConfig] = None,
) -> Dict[str, Any]:
    """
    Run user corpus import pipeline.
    
    Args:
        input_path: Path to input file or directory
        output_path: Path to output JSONL file
        input_format: "jsonl", "json", "text", or "auto" (detect from extension)
        config: Import configuration
    
    Returns:
        Metrics dict
    """
    config = config or UserImportConfig()
    importer = UserCorpusImporter(config)
    
    # Auto-detect format
    if input_format == "auto":
        if os.path.isdir(input_path):
            input_format = "text"
        elif input_path.endswith(".jsonl"):
            input_format = "jsonl"
        elif input_path.endswith(".json"):
            input_format = "json"
        else:
            input_format = "jsonl"
    
    # Import based on format
    if input_format == "jsonl":
        decisions = importer.import_jsonl(input_path)
    elif input_format == "json":
        decisions = importer.import_json(input_path)
    elif input_format == "text":
        decisions = importer.import_text_files(input_path)
    else:
        raise ValueError(f"Unknown format: {input_format}")
    
    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for decision in decisions:
            f.write(json.dumps(decision, ensure_ascii=False) + "\n")
            count += 1
    
    stats = importer.get_stats()
    stats["output_path"] = output_path
    stats["output_count"] = count
    
    print(f"User import complete:")
    print(f"  Format: {input_format}")
    print(f"  Input: {stats['total_input']}")
    print(f"  Output: {stats['total_output']}")
    print(f"  Errors: {stats['validation_errors']}")
    print(f"  By format: {stats['by_format']}")
    
    return stats


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python user_import.py <input_path> <output_path> [format]")
        print("  format: jsonl, json, text, or auto (default: auto)")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    input_format = sys.argv[3] if len(sys.argv) > 3 else "auto"
    
    run_user_import(input_path, output_path, input_format)
