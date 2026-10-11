"""
LexMachina Schema Validator
Validates user-imported corpus records against the canonical decision schema.
Uses the JSON schema from corpus lane (decision_schema.json v1).
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import hashlib


@dataclass
class ValidationResult:
    """Result of schema validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    normalized_record: Optional[Dict] = None


class SchemaValidator:
    """
    Validates decision records against the LexMachina canonical schema.
    
    The schema is based on corpus/schema/decision_schema.json v1 from the corpus lane.
    Provides both strict validation and normalization for user imports.
    """
    
    # Required fields from schema
    REQUIRED_FIELDS = {
        "decision_id", "court", "docket_number", "decision_date", 
        "language", "full_text", "provenance"
    }
    
    # Valid enum values
    VALID_COURTS = {"bge", "bger", "bvger", "bstger", "bpatger", "bge_historical", "bge_egmr"}
    VALID_LANGUAGES = {"de", "fr", "it", "rm", "en"}
    VALID_BRANCHES = {"zivilrecht", "strafrecht", "oeffentliches_recht", "sozialversicherungsrecht", "null"}
    VALID_OUTCOMES = {"gutgeheissen", "abgewiesen", "teilweise_gutgeheissen", "erledigt", "nichteintreten", "zurueckgewiesen", "null"}
    VALID_DECISION_TYPES = {"Leitentscheid", "Endentscheid", "Zwischenentscheid", "Verfahrensentscheid", "null"}
    VALID_PROVENANCE_SOURCES = {"opencaselaw_api", "opencaselaw_parquet", "zenodo_scd", "bger_official", "user_upload"}
    
    def __init__(self, schema_path: Optional[str] = None):
        """Initialize validator with optional external schema file."""
        self.schema = None
        if schema_path and Path(schema_path).exists():
            with open(schema_path, "r") as f:
                self.schema = json.load(f)
    
    def validate(self, record: Dict, strict: bool = False) -> ValidationResult:
        """
        Validate a single decision record.
        
        Args:
            record: Decision record to validate
            strict: If True, enforce all schema constraints strictly
            
        Returns:
            ValidationResult with validation status, errors, warnings, and normalized record
        """
        errors = []
        warnings = []
        normalized = {}
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in record or record[field] is None:
                errors.append(f"Missing required field: {field}")
            else:
                normalized[field] = record[field]
        
        if errors:
            return ValidationResult(False, errors, warnings)
        
        # Validate decision_id format
        decision_id = record["decision_id"]
        if not isinstance(decision_id, str) or not decision_id:
            errors.append("decision_id must be a non-empty string")
        elif not self._validate_decision_id_format(decision_id):
            warnings.append(f"decision_id '{decision_id}' does not match expected pattern")
        normalized["decision_id"] = decision_id
        
        # Validate court
        court = record["court"]
        if court not in self.VALID_COURTS:
            if strict:
                errors.append(f"Invalid court: '{court}'. Must be one of {self.VALID_COURTS}")
            else:
                warnings.append(f"Unknown court: '{court}'")
        normalized["court"] = court
        
        # Validate docket_number
        docket = record["docket_number"]
        if not isinstance(docket, str):
            errors.append("docket_number must be a string")
        normalized["docket_number"] = docket
        
        # Validate decision_date
        date_str = record["decision_date"]
        if not self._validate_date(date_str):
            errors.append(f"Invalid decision_date format: '{date_str}'. Expected YYYY-MM-DD")
        normalized["decision_date"] = date_str
        
        # Validate language
        language = record["language"]
        if language not in self.VALID_LANGUAGES:
            if strict:
                errors.append(f"Invalid language: '{language}'. Must be one of {self.VALID_LANGUAGES}")
            else:
                warnings.append(f"Unknown language: '{language}'")
        normalized["language"] = language
        
        # Validate full_text
        full_text = record["full_text"]
        if not isinstance(full_text, str) or not full_text.strip():
            errors.append("full_text must be a non-empty string")
        normalized["full_text"] = full_text
        normalized["text_length"] = len(full_text)
        
        # Validate provenance
        provenance = record["provenance"]
        if not isinstance(provenance, dict):
            errors.append("provenance must be an object")
        else:
            prov_errors, prov_warnings = self._validate_provenance(provenance, strict)
            errors.extend(prov_errors)
            warnings.extend(prov_warnings)
        normalized["provenance"] = provenance
        
        # Optional fields with validation
        optional_fields = {
            "title": (str, None),
            "legal_area": (str, None),
            "branch": (self._validate_branch, None),
            "chamber": (str, None),
            "outcome": (self._validate_outcome, None),
            "decision_type": (self._validate_decision_type, None),
            "bge_reference": (str, None),
            "cited_decisions": (list, []),
            "cited_laws": (list, []),
            "sachverhalt": (str, None),
            "erwaegungen": (list, None),
            "dispositiv": (str, None),
        }
        
        for field, (validator, default) in optional_fields.items():
            if field in record and record[field] is not None:
                if isinstance(validator, type):
                    # Type validator (str, list, etc.)
                    if not isinstance(record[field], validator):
                        if strict:
                            errors.append(f"Field '{field}' must be of type {validator.__name__}")
                        else:
                            warnings.append(f"Field '{field}' has unexpected type")
                    normalized[field] = record[field]
                elif callable(validator):
                    # Custom validation function
                    val_errors, val_warnings, val_result = validator(record[field])
                    errors.extend(val_errors)
                    warnings.extend(val_warnings)
                    if val_result is not None:
                        normalized[field] = val_result
                    else:
                        normalized[field] = record[field]
                else:
                    normalized[field] = record[field]
            elif default is not None:
                normalized[field] = default
        
        # Handle text_length if not provided
        if "text_length" not in normalized:
            normalized["text_length"] = len(normalized.get("full_text", ""))
        
        # Ensure provenance has source=user_upload for user imports
        if normalized.get("provenance", {}).get("source") != "user_upload":
            normalized["provenance"]["source"] = "user_upload"
            if "content_hash" not in normalized["provenance"]:
                normalized["provenance"]["content_hash"] = hashlib.sha256(
                    normalized["full_text"].encode("utf-8")
                ).hexdigest()
            if "acquired_at" not in normalized["provenance"]:
                normalized["provenance"]["acquired_at"] = datetime.utcnow().isoformat() + "Z"
            if "source_version" not in normalized["provenance"]:
                normalized["provenance"]["source_version"] = "user_import"
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            normalized_record=normalized if len(errors) == 0 else None
        )
    
    def validate_batch(self, records: List[Dict], strict: bool = False) -> Tuple[List[ValidationResult], Dict]:
        """
        Validate a batch of records.
        
        Returns:
            Tuple of (list of ValidationResult, summary dict with counts)
        """
        results = []
        summary = {"valid": 0, "invalid": 0, "total_errors": 0, "total_warnings": 0}
        
        for record in records:
            result = self.validate(record, strict)
            results.append(result)
            if result.valid:
                summary["valid"] += 1
            else:
                summary["invalid"] += 1
            summary["total_errors"] += len(result.errors)
            summary["total_warnings"] += len(result.warnings)
        
        return results, summary
    
    def _validate_decision_id_format(self, decision_id: str) -> bool:
        """Validate decision_id matches expected pattern."""
        # Pattern from schema: ^[a-z]+_[A-Za-z0-9_./-]+$
        import re
        pattern = r"^[a-z]+_[A-Za-z0-9_./-]+$"
        return bool(re.match(pattern, decision_id))
    
    def _validate_date(self, date_str: str) -> bool:
        """Validate date string is in YYYY-MM-DD format."""
        if not isinstance(date_str, str):
            return False
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    def _validate_branch(self, value: Any) -> Tuple[List[str], List[str], Optional[str]]:
        """Validate branch field."""
        if not isinstance(value, str):
            return ["branch must be a string"], [], None
        if value not in self.VALID_BRANCHES:
            return [], [f"Unknown branch: '{value}'"], value
        return [], [], value
    
    def _validate_outcome(self, value: Any) -> Tuple[List[str], List[str], Optional[str]]:
        """Validate outcome field."""
        if not isinstance(value, str):
            return ["outcome must be a string"], [], None
        if value not in self.VALID_OUTCOMES:
            return [], [f"Unknown outcome: '{value}'"], value
        return [], [], value
    
    def _validate_decision_type(self, value: Any) -> Tuple[List[str], List[str], Optional[str]]:
        """Validate decision_type field."""
        if not isinstance(value, str):
            return ["decision_type must be a string"], [], None
        if value not in self.VALID_DECISION_TYPES:
            return [], [f"Unknown decision_type: '{value}'"], value
        return [], [], value
    
    def _validate_provenance(self, provenance: Dict, strict: bool) -> Tuple[List[str], List[str]]:
        """Validate provenance object."""
        errors = []
        warnings = []
        
        required_prov = {"source", "acquired_at", "source_version", "content_hash"}
        for field in required_prov:
            if field not in provenance:
                if strict:
                    errors.append(f"provenance missing required field: {field}")
                else:
                    warnings.append(f"provenance missing recommended field: {field}")
        
        if "source" in provenance:
            if provenance["source"] not in self.VALID_PROVENANCE_SOURCES:
                if strict:
                    errors.append(f"Invalid provenance source: '{provenance['source']}'")
                else:
                    warnings.append(f"Unknown provenance source: '{provenance['source']}'")
        
        if "content_hash" in provenance:
            if not isinstance(provenance["content_hash"], str) or len(provenance["content_hash"]) != 64:
                if strict:
                    errors.append("content_hash must be 64-character hex string")
                else:
                    warnings.append("content_hash should be 64-character SHA-256")
        
        return errors, warnings


def create_user_import_record(
    decision_id: str,
    court: str,
    docket_number: str,
    decision_date: str,
    language: str,
    full_text: str,
    **kwargs
) -> Dict:
    """
    Create a properly formatted user import record with auto-generated provenance.
    
    This is a convenience function for creating valid user import records
    that will pass schema validation.
    """
    content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    
    record = {
        "decision_id": decision_id,
        "court": court,
        "docket_number": docket_number,
        "decision_date": decision_date,
        "language": language,
        "full_text": full_text,
        "provenance": {
            "source": "user_upload",
            "acquired_at": datetime.utcnow().isoformat() + "Z",
            "source_version": "user_import",
            "content_hash": content_hash,
        }
    }
    
    # Add optional fields if provided
    optional_fields = [
        "title", "legal_area", "branch", "chamber", "outcome", 
        "decision_type", "bge_reference", "cited_decisions", 
        "cited_laws", "sachverhalt", "erwaegungen", "dispositiv"
    ]
    
    for field in optional_fields:
        if field in kwargs and kwargs[field] is not None:
            record[field] = kwargs[field]
    
    return record


if __name__ == "__main__":
    # Quick self-test
    validator = SchemaValidator()
    
    # Test valid record
    valid_record = create_user_import_record(
        decision_id="test_user_001",
        court="bger",
        docket_number="TEST-001/2024",
        decision_date="2024-01-15",
        language="de",
        full_text="Dies ist ein Testentscheid.",
        branch="strafrecht",
        outcome="gutgeheissen"
    )
    
    result = validator.validate(valid_record)
    print(f"Valid record: {result.valid}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
    
    # Test invalid record
    invalid_record = {
        "decision_id": "test_user_002",
        "court": "invalid_court",
        "docket_number": "TEST-002/2024",
        "decision_date": "invalid-date",
        "language": "xx",
        "full_text": "",
        "provenance": {}
    }
    
    result2 = validator.validate(invalid_record, strict=True)
    print(f"\nInvalid record: {result2.valid}")
    print(f"Errors: {result2.errors}")
    print(f"Warnings: {result2.warnings}")