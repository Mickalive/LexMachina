"""
Repair validation for rejected cycle 33032428186.
Fixes applied:
1. [REQUIRED] Add 'user_upload' to provenance.source enum in decision_schema.json
2. [OPTIONAL] Add 'partial_approval' and 'moot' to OUTCOME_MAP in normalize.py
3. [OPTIONAL] Reconcile state metrics (language_distribution, branch_distribution) with unique counts
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
    """OPTIONAL FIX: Verify state metrics are internally consistent (updated for repair round 1)."""
    print("\n" + "=" * 60)
    print("TEST: State metrics internal consistency (yearly-core vs all)")
    print("=" * 60)

    with open("state/corpus.json", "r") as f:
        state = json.load(f)

    metrics = state["metrics"]

    # Verify yearly-core metrics consistency (sum to 250)
    canonical_yearly = metrics["canonical_decisions_normalized_yearly_core"]
    lang_sum_yearly = sum(metrics["language_distribution_yearly_core"].values())
    year_sum_yearly = sum(metrics["year_distribution_yearly_core"].values())
    court_sum_yearly = sum(metrics["court_distribution_yearly_core"].values())
    branch_sum_yearly = sum(metrics["branch_distribution_yearly_core"].values())

    assert lang_sum_yearly == canonical_yearly, (
        f"language_distribution_yearly_core sum ({lang_sum_yearly}) != "
        f"canonical_decisions_normalized_yearly_core ({canonical_yearly})"
    )
    assert year_sum_yearly == canonical_yearly, (
        f"year_distribution_yearly_core sum ({year_sum_yearly}) != "
        f"canonical_decisions_normalized_yearly_core ({canonical_yearly})"
    )
    assert court_sum_yearly == canonical_yearly, (
        f"court_distribution_yearly_core sum ({court_sum_yearly}) != "
        f"canonical_decisions_normalized_yearly_core ({canonical_yearly})"
    )
    assert branch_sum_yearly == canonical_yearly, (
        f"branch_distribution_yearly_core sum ({branch_sum_yearly}) != "
        f"canonical_decisions_normalized_yearly_core ({canonical_yearly})"
    )

    # Verify full-corpus metrics consistency (sum to 1577)
    total_all = metrics["canonical_file_lines_total_all"]
    lang_sum_all = sum(metrics["language_distribution_all"].values())
    year_sum_all = sum(metrics["year_distribution_all"].values())
    court_sum_all = sum(metrics["court_distribution_all"].values())

    assert lang_sum_all == total_all, (
        f"language_distribution_all sum ({lang_sum_all}) != "
        f"canonical_file_lines_total_all ({total_all})"
    )
    assert year_sum_all == total_all, (
        f"year_distribution_all sum ({year_sum_all}) != "
        f"canonical_file_lines_total_all ({total_all})"
    )
    assert court_sum_all == total_all, (
        f"court_distribution_all sum ({court_sum_all}) != "
        f"canonical_file_lines_total_all ({total_all})"
    )

    # Verify unique ID counts
    assert metrics["canonical_unique_decision_ids_yearly_core"] == 250
    assert metrics["canonical_unique_decision_ids_all"] == 1215
    assert metrics["total_unique_across_all_canonical"] == 1215
    assert metrics["slice_1000_decisions"] == 1000
    assert metrics["slice_1000_overlap_with_yearly"] == 50

    # Verify parquet metrics corrected
    assert metrics["parquet_validated"] is False
    assert "parquet_file_size_mb" not in metrics
    assert "parquet_total_rows_estimate" not in metrics
    assert "parquet_sample_loaded" not in metrics

    # Verify citation graph metrics corrected
    assert metrics["citation_graph_edges"] == 0
    assert metrics["citation_graph_nodes_cited"] == 0

    print(f"  canonical_decisions_normalized_yearly_core: {canonical_yearly}")
    print(f"  language_distribution_yearly_core sum: {lang_sum_yearly}")
    print(f"  year_distribution_yearly_core sum: {year_sum_yearly}")
    print(f"  court_distribution_yearly_core sum: {court_sum_yearly}")
    print(f"  branch_distribution_yearly_core sum: {branch_sum_yearly}")
    print(f"  canonical_file_lines_total_all: {total_all}")
    print(f"  language_distribution_all sum: {lang_sum_all}")
    print(f"  year_distribution_all sum: {year_sum_all}")
    print(f"  court_distribution_all sum: {court_sum_all}")
    print(f"  parquet_validated: {metrics['parquet_validated']}")
    print(f"  citation_graph_edges: {metrics['citation_graph_edges']}")
    print("✓ State metrics are consistent (yearly-core and all populations separated)")
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
        "corpus/normalization/canonical/bger_2020.jsonl",
        "corpus/normalization/canonical/bger_2021.jsonl",
        "corpus/normalization/canonical/bger_2022.jsonl",
        "corpus/normalization/canonical/bger_2023.jsonl",
        "corpus/normalization/canonical/bger_2024.jsonl",
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
