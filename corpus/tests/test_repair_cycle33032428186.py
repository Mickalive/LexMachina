"""
Repair validation for rejected cycle 33032428186 + cycle 33506233167 round 1.
Fixes applied:
1. [REQUIRED] Add 'user_upload' to provenance.source enum in decision_schema.json
2. [OPTIONAL] Add 'partial_approval' and 'moot' to OUTCOME_MAP in normalize.py
3. [OPTIONAL] Reconcile state metrics (language_distribution, branch_distribution) with unique counts
4. [REQUIRED] Restore field_coverage to canonical validation_report_v14.json values (cycle 33506233167 R1)
"""
import json
import jsonschema
from pathlib import Path

from corpus.normalization.normalize import DecisionNormalizer
from corpus.acquisition.opencaselaw_client import DecisionRaw
from corpus.acquisition.user_import import UserCorpusImporter, UserImportConfig


def test_provenance_source_enum_includes_user_upload():
    """REQUIRED FIX: Verify user_upload is in provenance.source enum."""
    print("=" * 60)
    print("TEST: Provenance source enum includes 'user_upload'")
    print("=" * 60)

    with open("corpus/schema/decision_schema.json", "r") as f:
        schema = json.load(f)

    source_enum = (schema["properties"]["provenance"]["properties"]["source"]["enum"])
    assert "user_upload" in source_enum, (
        f"REQUIRED FIX MISSING: 'user_upload' not in provenance.source enum. "
        f"Enum: {source_enum}"
    )

    # Verify old values are still present
    for old in ["opencaselaw_api", "opencaselaw_parquet", "zenodo_scd", "bger_official"]:
        assert old in source_enum, f"Existing value '{old}' removed from enum"

    print(f"  Enum: {source_enum}")
    print("✓ Provenance source enum fix verified")
    return True


def test_user_import_schema_validation():
    """REQUIRED FIX: Verify user-imported decisions pass schema validation."""
    print("\n" + "=" * 60)
    print("TEST: User-imported decisions validate against schema")
    print("=" * 60)

    # Load schema
    with open("corpus/schema/decision_schema.json", "r") as f:
        schema = json.load(f)
    validator = jsonschema.Draft7Validator(schema)

    # Import a user decision
    importer = UserCorpusImporter()
    text = "Dies ist ein Testbeschluss mit genügend Text für die Validierung und Schemaüberprüfung. " * 5
    decision = importer.import_raw_text(text, {"decision_date": "2024-01-15", "language": "de"})

    assert decision is not None, "User import should produce a decision"
    assert decision["provenance"]["source"] == "user_upload"

    # Validate against schema — this was the failing path before the fix
    errors = list(validator.iter_errors(decision))
    assert not errors, f"User-imported decision fails schema validation: {errors}"

    print(f"  decision_id: {decision['decision_id']}")
    print(f"  provenance.source: {decision['provenance']['source']}")
    print("✓ User import schema validation passes")
    return True


def test_partial_approval_outcome_mapping():
    """OPTIONAL FIX: Verify 'partial_approval' maps to 'teilweise_gutgeheissen'."""
    print("\n" + "=" * 60)
    print("TEST: 'partial_approval' outcome mapping")
    print("=" * 60)

    normalizer = DecisionNormalizer()
    result = normalizer._map_outcome("partial_approval")
    assert result == "teilweise_gutgeheissen", (
        f"Expected 'teilweise_gutgeheissen', got '{result}'"
    )

    # Also verify the raw value produces a valid schema outcome
    assert result in ["gutgeheissen", "abgewiesen", "teilweise_gutgeheissen",
                       "erledigt", "nichteintreten", "zurueckgewiesen", "null"]

    print(f"  partial_approval -> {result}")
    print("✓ partial_approval outcome mapping verified")
    return True


def test_moot_outcome_mapping():
    """OPTIONAL FIX: Verify 'moot' maps to 'erledigt'."""
    print("\n" + "=" * 60)
    print("TEST: 'moot' outcome mapping")
    print("=" * 60)

    normalizer = DecisionNormalizer()
    result = normalizer._map_outcome("moot")
    assert result == "erledigt", (
        f"Expected 'erledigt', got '{result}'"
    )

    print(f"  moot -> {result}")
    print("✓ moot outcome mapping verified")
    return True


def test_state_metrics_consistency():
    """Verify state metrics are internally consistent (updated for v14 full-corpus structure)."""
    print("\n" + "=" * 60)
    print("TEST: State metrics internal consistency (full 174k corpus)")
    print("=" * 60)

    with open("state/corpus.json", "r") as f:
        state = json.load(f)

    metrics = state["metrics"]

    # Verify state top-level fields
    assert state["lane"] == "corpus"
    assert state["direction_version"] == 14
    assert state["evidence_tier"] in ("REPRODUCED", "ACCEPTED")
    assert state["cycle_status"] == "COMPLETED"

    # Verify canonical decision counts are consistent
    canonical_current = metrics["canonical_decisions_current"]
    canonical_normalized = metrics["canonical_decisions_normalized"]
    canonical_unique = metrics["canonical_unique_decision_ids"]

    assert canonical_current == canonical_normalized == canonical_unique, (
        f"canonical counts inconsistent: current={canonical_current}, "
        f"normalized={canonical_normalized}, unique={canonical_unique}"
    )
    assert canonical_current > 170000, (
        f"Expected >170k decisions, got {canonical_current}"
    )

    # Verify language distribution sums to total
    lang_sum = sum(metrics["language_distribution"].values())
    assert lang_sum == canonical_current, (
        f"language_distribution sum ({lang_sum}) != canonical_decisions_current ({canonical_current})"
    )

    # Verify year coverage is consistent
    year_cov = metrics["year_coverage"]
    assert year_cov["total_2000_2026"] + year_cov["total_pre_2000"] == canonical_current, (
        f"year_coverage totals ({year_cov['total_2000_2026']} + {year_cov['total_pre_2000']}) "
        f"!= canonical_decisions_current ({canonical_current})"
    )

    # Verify schema validation
    sv = metrics["schema_validation"]
    assert sv["total_validated"] == canonical_current
    assert sv["total_errors"] == 0

    # Verify citation resolver exists and has valid rate
    cr = metrics["citation_resolver"]
    assert 0.0 < cr["resolution_rate"] <= 1.0
    assert cr["resolved_total"] + cr["unresolved_total"] == cr["total_references_in_graph"]

    print(f"  canonical_decisions_current: {canonical_current}")
    print(f"  language_distribution sum: {lang_sum}")
    print(f"  year_coverage total: {year_cov['total_2000_2026']} + {year_cov['total_pre_2000']}")
    print(f"  schema_validation: {sv['total_validated']} validated, {sv['total_errors']} errors")
    print(f"  citation_resolution_rate: {cr['resolution_rate']:.4f}")
    print("✓ State metrics are consistent (full 174k corpus structure)")
    return True


def test_field_coverage_matches_canonical():
    """REQUIRED FIX (cycle 33506233167 R1): Verify field_coverage matches canonical validation_report_v14.json.

    Prevents recurrence of state metadata inflation where cited_decisions was
    reported as 0.993 instead of the canonical 0.526, and outcome as 1.0
    instead of 0.505.
    """
    print("\n" + "=" * 60)
    print("TEST: field_coverage matches canonical validation_report_v14.json")
    print("=" * 60)

    with open("state/corpus.json", "r") as f:
        state = json.load(f)

    with open("corpus/normalization/canonical/validation_report_v14.json", "r") as f:
        vr = json.load(f)

    fc = state["metrics"]["field_coverage"]
    vr_rates = vr["field_coverage"]["fill_rates"]

    # Canonical values from validation_report_v14.json (sample_size=1000, seed=42)
    canonical_rates = {
        "full_text": vr_rates["full_text"]["rate"],
        "regeste": vr_rates["regeste"]["rate"],
        "cited_decisions": vr_rates["cited_decisions"]["rate"],
        "outcome": vr_rates["outcome"]["rate"],
        "legal_area": vr_rates["legal_area"]["rate"],
    }

    # Verify each field_coverage value matches canonical ground truth
    for field, expected_rate in canonical_rates.items():
        actual_rate = fc.get(field)
        assert actual_rate is not None, f"field_coverage missing field: {field}"
        assert abs(actual_rate - expected_rate) < 0.001, (
            f"field_coverage.{field} = {actual_rate} != canonical {expected_rate} "
            f"(from validation_report_v14.json)"
        )
        print(f"  {field}: {actual_rate} == {expected_rate} ✓")

    # Verify source identifies canonical provenance
    assert "validation_report_v14.json" in fc.get("source", ""), (
        f"field_coverage.source should reference validation_report_v14.json, "
        f"got: {fc.get('source')}"
    )
    print(f"  source: {fc.get('source')} ✓")

    print("✓ field_coverage matches canonical validation_report_v14.json")
    return True


def test_existing_schema_still_validates_yearly_data():
    """Regression: verify existing canonical data still validates."""
    print("\n" + "=" * 60)
    print("TEST: Existing canonical data still validates against schema")
    print("=" * 60)

    with open("corpus/schema/decision_schema.json", "r") as f:
        schema = json.load(f)
    validator = jsonschema.Draft7Validator(schema)

    total = 0
    errors_count = 0
    yearly_files = [
        "corpus/normalization/canonical/bge_2020.jsonl",
        "corpus/normalization/canonical/bge_2021.jsonl",
        "corpus/normalization/canonical/bge_2022.jsonl",
        "corpus/normalization/canonical/bge_2023.jsonl",
        "corpus/normalization/canonical/bge_2024.jsonl",
    ]

    for fpath in yearly_files:
        with open(fpath, "r") as f:
            for line in f:
                decision = json.loads(line.strip())
                errors = list(validator.iter_errors(decision))
                if errors:
                    errors_count += 1
                    print(f"  ERROR in {fpath}: {errors[0].message}")
                total += 1

    assert errors_count == 0, f"{errors_count}/{total} validation errors"
    print(f"  Validated {total} decisions, 0 errors")
    print("✓ Regression check passed")
    return True


def main():
    """Run all repair validation tests."""
    print("\n" + "#" * 60)
    print("# REPAIR VALIDATION: CYCLE 33032428186")
    print("# Required fix + optional improvements")
    print("#" * 60)

    results = {}
    results["provenance_enum"] = test_provenance_source_enum_includes_user_upload()
    results["user_import_validation"] = test_user_import_schema_validation()
    results["partial_approval_mapping"] = test_partial_approval_outcome_mapping()
    results["moot_mapping"] = test_moot_outcome_mapping()
    results["state_metrics"] = test_state_metrics_consistency()
    results["field_coverage_canonical"] = test_field_coverage_matches_canonical()
    results["regression_yearly"] = test_existing_schema_still_validates_yearly_data()

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print("\n" + "#" * 60)
    print(f"# REPAIR TEST RESULTS: {passed}/{total} PASSED")
    print("#" * 60)

    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")

    if passed == total:
        print("\n# ALL REPAIR TESTS PASSED")
    else:
        print(f"\n# {total - passed} REPAIR TESTS FAILED")

    return all(results.values())


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
