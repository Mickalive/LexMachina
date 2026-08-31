"""
Hardened user corpus import pipeline for LexMachina corpus lane.

Features:
- Schema validation on input (pre-normalization, field-level detail)
- Cross-corpus deduplication against canonical corpus
- Map artifact persistence (manifest, decision index, content hash index, year index)
- Incremental import without full reprocessing
- Format auto-detection (JSONL, JSON, CSV, plain text directories)
- Error resilience (per-record, never fail the import)
- Full provenance tracking with import_id and source_filename
"""
import csv
import hashlib
import io
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import jsonschema

from corpus.normalization.normalize import DecisionNormalizer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _detect_format(input_path: str) -> str:
    """Auto-detect format from extension or directory."""
    if os.path.isdir(input_path):
        return "directory"
    ext = Path(input_path).suffix.lower()
    return {
        ".jsonl": "jsonl",
        ".json": "json",
        ".csv": "csv",
    }.get(ext, "jsonl")


# ---------------------------------------------------------------------------
# Schema validation (pre-normalization and post-normalization)
# ---------------------------------------------------------------------------

def _build_user_input_schema(full_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Build a user-input schema from the canonical schema.

    The canonical schema requires 'provenance' and other fields that only exist
    after normalization.  For pre-normalization validation we only check:
      - Fields the user *can* provide (type/format constraints).
      - A text-like field is present (full_text / text / content / decision_text).
    We drop 'provenance' from required and from properties so raw input passes
    if the essential data is present.
    """
    user_schema = json.loads(json.dumps(full_schema))

    # Remove provenance from required - users don't supply it
    req = user_schema.get("required", [])
    user_schema["required"] = [r for r in req if r != "provenance"]

    # Also drop text_length from required (computed by normalizer)
    user_schema["required"] = [r for r in user_schema["required"] if r != "text_length"]

    # Remove format constraints that are too strict for raw user input
    props = user_schema.get("properties", {})
    for field_name in ("decision_date", "publication_date", "source_url", "pdf_url"):
        if field_name in props:
            props[field_name].pop("format", None)

    # Allow decision_id to be absent (normalizer generates it)
    user_schema["required"] = [r for r in user_schema["required"] if r != "decision_id"]

    return user_schema


class InputValidator:
    """Validate raw user dicts against a user-input schema before normalization."""

    def __init__(self, schema_path: str):
        with open(schema_path, "r") as f:
            self._full_schema = json.load(f)
        self._user_schema = _build_user_input_schema(self._full_schema)
        self._user_validator = jsonschema.Draft7Validator(self._user_schema)

        # Post-normalization validator uses the full canonical schema
        self._canonical_validator = jsonschema.Draft7Validator(self._full_schema)

    def validate(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return list of error dicts for pre-normalization validation."""
        errors: List[Dict[str, Any]] = []
        for error in self._user_validator.iter_errors(record):
            errors.append({
                "path": list(error.absolute_path),
                "message": error.message,
                "validator": error.validator,
                "schema_path": list(error.absolute_schema_path),
            })
        # Additional semantic check: must have at least one text-like field
        text_fields = ("full_text", "text", "content", "decision_text")
        if not any(record.get(f) for f in text_fields):
            errors.append({
                "path": [],
                "message": "No text content found (expected one of: full_text, text, content, decision_text)",
                "validator": "text_presence",
                "schema_path": [],
            })
        return errors

    def validate_canonical(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate a normalized record against the full canonical schema."""
        errors: List[Dict[str, Any]] = []
        for error in self._canonical_validator.iter_errors(record):
            errors.append({
                "path": list(error.absolute_path),
                "message": error.message,
                "validator": error.validator,
                "schema_path": list(error.absolute_schema_path),
            })
        return errors


# ---------------------------------------------------------------------------
# Cross-corpus deduplication
# ---------------------------------------------------------------------------

class CrossCorpusDeduplicator:
    """Track content hashes across canonical corpus files and user imports."""

    def __init__(self):
        self._canonical_hashes: Set[str] = set()
        self._batch_hashes: Set[str] = set()

    # -- loading canonical ---------------------------------------------------
    def load_canonical_hashes(self, canonical_corpus_dir: str) -> int:
        """Scan all JSONL files under *canonical_corpus_dir* and load content
        hashes from provenance.content_hash. Returns count loaded."""
        count = 0
        corpus_path = Path(canonical_corpus_dir)
        if not corpus_path.exists():
            logger.warning("Canonical corpus dir not found: %s", canonical_corpus_dir)
            return 0
        for jsonl_file in corpus_path.glob("**/*.jsonl"):
            try:
                with open(jsonl_file, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                            h = rec.get("provenance", {}).get("content_hash")
                            if h:
                                self._canonical_hashes.add(h)
                                count += 1
                        except json.JSONDecodeError:
                            continue
            except Exception as exc:
                logger.warning("Failed to read %s: %s", jsonl_file, exc)
        logger.info("Loaded %d content hashes from canonical corpus", count)
        return count

    # -- loading existing user corpus ----------------------------------------
    def load_existing_user_hashes(self, output_jsonl_path: str) -> int:
        """Load hashes from an existing user corpus JSONL for incremental
        imports. Returns count loaded."""
        count = 0
        if not os.path.exists(output_jsonl_path):
            return 0
        try:
            with open(output_jsonl_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        h = rec.get("provenance", {}).get("content_hash")
                        if h:
                            self._canonical_hashes.add(h)
                            self._batch_hashes.add(h)
                            count += 1
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.warning("Failed to read existing user corpus %s: %s", output_jsonl_path, exc)
        logger.info("Loaded %d content hashes from existing user corpus", count)
        return count

    # -- checking ------------------------------------------------------------
    def is_cross_corpus_duplicate(self, content_hash: str) -> bool:
        return content_hash in self._canonical_hashes

    def is_self_duplicate(self, content_hash: str) -> bool:
        return content_hash in self._batch_hashes

    def register(self, content_hash: str) -> None:
        self._canonical_hashes.add(content_hash)
        self._batch_hashes.add(content_hash)


# ---------------------------------------------------------------------------
# Artifact persistence
# ---------------------------------------------------------------------------

class ArtifactManager:
    """Manage import artifacts: manifest, decision_index, content_hash_index,
    year_index."""

    def __init__(self, artifacts_dir: str):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.manifest_path = self.artifacts_dir / "manifest.json"
        self.decision_index_path = self.artifacts_dir / "decision_index.json"
        self.content_hash_index_path = self.artifacts_dir / "content_hash_index.json"
        self.year_index_path = self.artifacts_dir / "year_index.json"

    # -- loaders -------------------------------------------------------------
    def load_manifest(self) -> Dict[str, Any]:
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def load_decision_index(self) -> Dict[str, str]:
        if self.decision_index_path.exists():
            with open(self.decision_index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def load_content_hash_index(self) -> Dict[str, str]:
        if self.content_hash_index_path.exists():
            with open(self.content_hash_index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def load_year_index(self) -> Dict[str, List[str]]:
        if self.year_index_path.exists():
            with open(self.year_index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    # -- writers -------------------------------------------------------------
    def save_manifest(self, manifest: Dict[str, Any]) -> None:
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def save_decision_index(self, index: Dict[str, str]) -> None:
        with open(self.decision_index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def save_content_hash_index(self, index: Dict[str, str]) -> None:
        with open(self.content_hash_index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def save_year_index(self, index: Dict[str, List[str]]) -> None:
        with open(self.year_index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Hardened user importer
# ---------------------------------------------------------------------------

class HardenedUserImporter:
    """Production-ready user corpus importer with schema validation,
    cross-corpus deduplication, and artifact persistence."""

    def __init__(
        self,
        canonical_corpus_dir: str = "corpus/normalization/canonical",
        schema_path: str = "corpus/schema/decision_schema.json",
    ):
        self.canonical_corpus_dir = canonical_corpus_dir
        self.schema_path = schema_path
        self.normalizer = DecisionNormalizer(schema_path)
        self.input_validator = InputValidator(schema_path)
        self.deduplicator = CrossCorpusDeduplicator()

    # -- public API ----------------------------------------------------------

    def import_corpus(
        self,
        input_path: str,
        output_path: str,
        import_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Full import pipeline with all features.

        Returns a summary dict with counts and per-field stats.
        """
        import_id = import_id or f"import_{uuid.uuid4().hex[:12]}"
        import_timestamp = _now_iso()
        source_filename = os.path.basename(input_path)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Artifacts live alongside the output JSONL
        artifacts_dir = os.path.dirname(os.path.abspath(output_path))
        artifact_mgr = ArtifactManager(artifacts_dir)

        # Load existing indices for incremental import
        existing_decision_index = artifact_mgr.load_decision_index()
        existing_hash_index = artifact_mgr.load_content_hash_index()
        existing_year_index = artifact_mgr.load_year_index()

        # Cross-corpus dedup: load canonical + existing user corpus hashes
        self.deduplicator.load_canonical_hashes(self.canonical_corpus_dir)
        self.deduplicator.load_existing_user_hashes(output_path)

        # Auto-detect format
        fmt = _detect_format(input_path)

        # Collect decisions (streamed)
        decisions_iter = self._iter_input(input_path, fmt)

        # Process: validate, dedup, normalize
        summary = {
            "import_id": import_id,
            "import_timestamp": import_timestamp,
            "source_filename": source_filename,
            "source_format": fmt,
            "total_input": 0,
            "total_output": 0,
            "validation_errors": 0,
            "cross_corpus_duplicates": 0,
            "self_duplicates": 0,
            "normalization_failures": 0,
            "error_log": [],
            "by_year": {},
            "by_language": {},
            "by_format": {},
        }

        # We need to write output incrementally AND collect index data
        # Strategy: process all records, write valid ones to output, build indices
        valid_decisions: List[Dict[str, Any]] = []

        for raw_record, record_source_file in decisions_iter:
            summary["total_input"] += 1
            fmt_key = record_source_file or fmt
            summary["by_format"][fmt_key] = summary["by_format"].get(fmt_key, 0) + 1

            # 1. Schema validation (pre-normalization)
            validation_errors = self.input_validator.validate(raw_record)
            if validation_errors:
                summary["validation_errors"] += 1
                summary["error_log"].append({
                    "record": summary["total_input"],
                    "source": record_source_file,
                    "phase": "validation",
                    "errors": validation_errors,
                })
                continue

            # 2. Extract text for content hash
            full_text = (
                raw_record.get("full_text")
                or raw_record.get("text")
                or raw_record.get("content")
                or raw_record.get("decision_text")
                or ""
            )
            if not full_text or len(full_text.strip()) < 50:
                summary["validation_errors"] += 1
                summary["error_log"].append({
                    "record": summary["total_input"],
                    "source": record_source_file,
                    "phase": "validation",
                    "errors": [{"message": "full_text missing or too short"}],
                })
                continue

            ch = _content_hash(full_text)

            # 3. Cross-corpus dedup
            if self.deduplicator.is_cross_corpus_duplicate(ch):
                summary["cross_corpus_duplicates"] += 1
                summary["error_log"].append({
                    "record": summary["total_input"],
                    "source": record_source_file,
                    "phase": "dedup",
                    "errors": [{"message": "cross-corpus duplicate", "content_hash": ch}],
                })
                continue

            # 4. Self-dedup within batch
            if self.deduplicator.is_self_duplicate(ch):
                summary["self_duplicates"] += 1
                summary["error_log"].append({
                    "record": summary["total_input"],
                    "source": record_source_file,
                    "phase": "dedup",
                    "errors": [{"message": "self-duplicate within batch", "content_hash": ch}],
                })
                continue

            # 5. Normalization
            try:
                decision_id = raw_record.get("decision_id") or raw_record.get("id") or f"user_{ch[:16]}"
                decision_id = str(decision_id)

                from corpus.acquisition.opencaselaw_client import DecisionRaw
                raw = DecisionRaw(
                    decision_id=decision_id,
                    court=raw_record.get("court") or "bger",
                    decision_date=raw_record.get("decision_date") or raw_record.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    language=raw_record.get("language") or "de",
                    title=raw_record.get("title"),
                    regeste=raw_record.get("regeste"),
                    citation_string_de=raw_record.get("citation_string_de"),
                    canonical_url=raw_record.get("source_url") or raw_record.get("url") or f"user://{decision_id}",
                    full_text=full_text,
                    legal_area=raw_record.get("legal_area"),
                    chamber=raw_record.get("chamber"),
                    branch=raw_record.get("branch"),
                    proceeding_type=raw_record.get("proceeding_type"),
                    abstract_de=raw_record.get("abstract_de"),
                    abstract_fr=raw_record.get("abstract_fr"),
                    abstract_it=raw_record.get("abstract_it"),
                    outcome=raw_record.get("outcome"),
                    decision_type=raw_record.get("decision_type"),
                    bge_reference=raw_record.get("bge_reference"),
                    cited_decisions=raw_record.get("cited_decisions"),
                    cited_laws=raw_record.get("cited_laws"),
                    judges=raw_record.get("judges"),
                    source_url=raw_record.get("source_url"),
                    pdf_url=raw_record.get("pdf_url"),
                    publication_date=raw_record.get("publication_date"),
                    docket_number=raw_record.get("docket_number") or decision_id,
                    content_hash=ch,
                    sachverhalt=raw_record.get("sachverhalt"),
                    erwaegungen=raw_record.get("erwaegungen"),
                    dispositiv=raw_record.get("dispositiv"),
                    dispositiv_orders=raw_record.get("dispositiv_orders"),
                    preparatory_materials=raw_record.get("preparatory_materials"),
                    outgoing_citations=raw_record.get("outgoing_citations"),
                    incoming_citations=raw_record.get("incoming_citations"),
                )

                canonical = self.normalizer.normalize(raw, f"user_upload_{import_id}")
            except Exception as exc:
                summary["normalization_failures"] += 1
                summary["error_log"].append({
                    "record": summary["total_input"],
                    "source": record_source_file,
                    "phase": "normalization",
                    "errors": [{"message": str(exc)}],
                })
                continue

            if canonical is None:
                summary["normalization_failures"] += 1
                continue

            # 6. Provenance stamp
            canonical["provenance"]["source"] = "user_upload"
            canonical["provenance"]["import_id"] = import_id
            canonical["provenance"]["import_timestamp"] = import_timestamp
            canonical["provenance"]["source_filename"] = record_source_file or source_filename

            # 7. Register hash and persist
            self.deduplicator.register(ch)
            valid_decisions.append(canonical)

            did = canonical["decision_id"]
            year = canonical.get("decision_date", "unknown")[:4]
            lang = canonical.get("language", "unknown")

            summary["total_output"] += 1
            summary["by_year"][year] = summary["by_year"].get(year, 0) + 1
            summary["by_language"][lang] = summary["by_language"].get(lang, 0) + 1

            # Update indices
            existing_decision_index[did] = os.path.basename(output_path)
            existing_hash_index[ch] = did
            existing_year_index.setdefault(year, []).append(did)

        # --- Write output JSONL (append for incremental) --------------------
        write_mode = "a" if os.path.exists(output_path) else "w"
        with open(output_path, write_mode, encoding="utf-8") as fh:
            for decision in valid_decisions:
                fh.write(json.dumps(decision, ensure_ascii=False) + "\n")

        # --- Persist artifacts ----------------------------------------------
        # Update manifest (cumulative)
        prev_manifest = artifact_mgr.load_manifest()
        cumulative_count = prev_manifest.get("total_output", 0) + summary["total_output"]
        cumulative_input = prev_manifest.get("total_input", 0) + summary["total_input"]

        manifest = {
            "schema_version": "v1",
            "canonical_corpus_dir": self.canonical_corpus_dir,
            "import_history": prev_manifest.get("import_history", []),
            "total_input": cumulative_input,
            "total_output": cumulative_count,
            "last_import": {
                "import_id": import_id,
                "import_timestamp": import_timestamp,
                "source_filename": source_filename,
                "source_format": fmt,
                "input_count": summary["total_input"],
                "output_count": summary["total_output"],
                "validation_errors": summary["validation_errors"],
                "cross_corpus_duplicates": summary["cross_corpus_duplicates"],
                "self_duplicates": summary["self_duplicates"],
                "normalization_failures": summary["normalization_failures"],
            },
        }
        manifest["import_history"].append({
            "import_id": import_id,
            "timestamp": import_timestamp,
            "source": source_filename,
            "output_count": summary["total_output"],
        })

        artifact_mgr.save_manifest(manifest)
        artifact_mgr.save_decision_index(existing_decision_index)
        artifact_mgr.save_content_hash_index(existing_hash_index)
        artifact_mgr.save_year_index(existing_year_index)

        summary["artifacts_dir"] = str(artifact_mgr.artifacts_dir)
        summary["output_path"] = output_path

        logger.info(
            "Import %s complete: %d in, %d out, %d cross-corpus dups, %d self dups, %d errors",
            import_id,
            summary["total_input"],
            summary["total_output"],
            summary["cross_corpus_duplicates"],
            summary["self_duplicates"],
            summary["validation_errors"],
        )

        return summary

    def validate_import(self, output_path: str) -> Dict[str, Any]:
        """Validate an imported corpus against the full canonical schema and
        return stats."""
        stats: Dict[str, Any] = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "by_year": {},
            "by_language": {},
            "validation_errors": [],
        }

        with open(output_path, "r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                stats["total"] += 1
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    stats["invalid"] += 1
                    stats["validation_errors"].append({
                        "line": line_no,
                        "error": f"JSON parse error: {exc}",
                    })
                    continue

                errors = self.input_validator.validate_canonical(rec)
                if errors:
                    stats["invalid"] += 1
                    stats["validation_errors"].append({
                        "line": line_no,
                        "decision_id": rec.get("decision_id", "<missing>"),
                        "errors": errors,
                    })
                else:
                    stats["valid"] += 1

                year = rec.get("decision_date", "unknown")[:4]
                lang = rec.get("language", "unknown")
                stats["by_year"][year] = stats["by_year"].get(year, 0) + 1
                stats["by_language"][lang] = stats["by_language"].get(lang, 0) + 1

        return stats

    # -- private helpers -----------------------------------------------------

    def _iter_input(
        self, input_path: str, fmt: str
    ) -> Iterator[Tuple[Dict[str, Any], Optional[str]]]:
        """Yield (raw_record_dict, source_filename_or_None) tuples."""
        if fmt == "jsonl":
            yield from self._iter_jsonl(input_path)
        elif fmt == "json":
            yield from self._iter_json(input_path)
        elif fmt == "csv":
            yield from self._iter_csv(input_path)
        elif fmt == "directory":
            yield from self._iter_directory(input_path)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def _iter_jsonl(self, path: str) -> Iterator[Tuple[Dict[str, Any], Optional[str]]]:
        source = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line), source
                except json.JSONDecodeError as exc:
                    logger.warning("JSONL parse error in %s: %s", source, exc)
                    # Emit a minimal record so caller counts the error
                    yield {"_parse_error": str(exc), "full_text": ""}, source

    def _iter_json(self, path: str) -> Iterator[Tuple[Dict[str, Any], Optional[str]]]:
        source = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            logger.warning("JSON file %s did not contain an array or object", path)
            return
        for item in data:
            if isinstance(item, dict):
                yield item, source

    def _iter_csv(self, path: str) -> Iterator[Tuple[Dict[str, Any], Optional[str]]]:
        source = os.path.basename(path)
        with open(path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                yield dict(row), source

    def _iter_directory(self, dir_path: str) -> Iterator[Tuple[Dict[str, Any], Optional[str]]]:
        dirp = Path(dir_path)
        # Support .txt, .json, .jsonl, .csv inside the directory
        for file_path in sorted(dirp.iterdir()):
            if file_path.is_dir():
                continue
            ext = file_path.suffix.lower()
            fname = file_path.name
            try:
                if ext == ".txt":
                    text = file_path.read_text(encoding="utf-8")
                    filename_stem = file_path.stem
                    rec: Dict[str, Any] = {
                        "full_text": text,
                        "title": filename_stem,
                        "decision_id": f"user_{filename_stem}",
                        "court": "bger",
                        "docket_number": f"user_{filename_stem}",
                        "language": "de",
                    }
                    date_match = re.search(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})", filename_stem)
                    if date_match:
                        rec["decision_date"] = (
                            f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                        )
                    else:
                        # Default to unknown date so schema validation passes
                        rec["decision_date"] = "0001-01-01"
                    yield rec, fname
                elif ext == ".jsonl":
                    with open(file_path, "r", encoding="utf-8") as fh:
                        for line in fh:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                yield json.loads(line), fname
                            except json.JSONDecodeError:
                                yield {"_parse_error": "json decode", "full_text": ""}, fname
                elif ext == ".json":
                    with open(file_path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    if isinstance(data, dict):
                        data = [data]
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                yield item, fname
                elif ext == ".csv":
                    with open(file_path, "r", encoding="utf-8", newline="") as fh:
                        reader = csv.DictReader(fh)
                        for row in reader:
                            yield dict(row), fname
            except Exception as exc:
                logger.warning("Failed to read %s: %s", file_path, exc)
                yield {"_parse_error": str(exc), "full_text": ""}, fname


# ---------------------------------------------------------------------------
# Convenience CLI entry point
# ---------------------------------------------------------------------------

def run_hardened_import(
    input_path: str,
    output_path: str,
    canonical_corpus_dir: str = "corpus/normalization/canonical",
    schema_path: str = "corpus/schema/decision_schema.json",
) -> Dict[str, Any]:
    """Convenience function for CLI usage.

    >>> run_hardened_import("data/user_cases.jsonl", "corpus/user/user_cases.jsonl")
    """
    importer = HardenedUserImporter(
        canonical_corpus_dir=canonical_corpus_dir,
        schema_path=schema_path,
    )
    summary = importer.import_corpus(input_path, output_path)

    # Post-import validation
    val_stats = importer.validate_import(output_path)

    print("=" * 60)
    print(f"Hardened import complete  (import_id={summary['import_id']})")
    print(f"  Source           : {summary['source_filename']}")
    print(f"  Format           : {summary['source_format']}")
    print(f"  Total input      : {summary['total_input']}")
    print(f"  Total output     : {summary['total_output']}")
    print(f"  Validation errors: {summary['validation_errors']}")
    print(f"  Cross-corpus dups: {summary['cross_corpus_duplicates']}")
    print(f"  Self-duplicates  : {summary['self_duplicates']}")
    print(f"  Norm. failures   : {summary['normalization_failures']}")
    print(f"  By year          : {dict(sorted(summary['by_year'].items()))}")
    print(f"  By language      : {summary['by_language']}")
    print(f"  Artifacts dir    : {summary['artifacts_dir']}")
    print("-" * 60)
    print(f"Post-import validation:")
    print(f"  Total records    : {val_stats['total']}")
    print(f"  Valid            : {val_stats['valid']}")
    print(f"  Invalid          : {val_stats['invalid']}")
    if val_stats["validation_errors"]:
        print(f"  First 5 errors   :")
        for err in val_stats["validation_errors"][:5]:
            print(f"    {err}")
    print("=" * 60)

    summary["post_import_validation"] = val_stats
    return summary


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python user_import_hardened.py <input_path> <output_path> [canonical_corpus_dir] [schema_path]")
        print("  input_path  : JSONL, JSON, CSV file or directory of .txt/.json/.jsonl/.csv files")
        print("  output_path : Output JSONL file (artifacts written alongside it)")
        sys.exit(1)

    inp = sys.argv[1]
    out = sys.argv[2]
    canon = sys.argv[3] if len(sys.argv) > 3 else "corpus/normalization/canonical"
    schema = sys.argv[4] if len(sys.argv) > 4 else "corpus/schema/decision_schema.json"

    run_hardened_import(inp, out, canon, schema)
