"""
Test script to verify the acquisition and normalization pipeline.
Acquires a small test slice and validates against schema.
"""
import hashlib
import json
import jsonschema
from pathlib import Path
from corpus.acquisition.opencaselaw_client import acquire_test_slice, DecisionRaw
from corpus.normalization.normalize import run_normalization, load_raw_decisions


def test_acquisition():
    """Test acquiring a small slice of recent BGer decisions."""
    print("=" * 60)
    print("TEST: Acquisition of BGer decisions from 2024")
    print("=" * 60)

    raw_path = "corpus/acquisition/raw/bger_test_2024.jsonl"
    decisions = acquire_test_slice(
        output_path=raw_path,
        max_decisions=50,  # Small test slice
        date_from="2024-01-01",
        date_to="2024-12-31"
    )

    assert len(decisions) > 0, "Should have acquired at least some decisions"
    assert all(isinstance(d, DecisionRaw) for d in decisions), "All items should be DecisionRaw"
    assert all(d.court == "bger" for d in decisions), "All should be from BGer"
    assert all(d.decision_date >= "2024-01-01" for d in decisions), "All should be from 2024+"

    # Check that we have full text for most
    with_text = [d for d in decisions if d.full_text and len(d.full_text) > 100]
    print(f"Decisions with substantial full text: {len(with_text)}/{len(decisions)}")

    # Verify JSONL is readable
    loaded = load_raw_decisions(raw_path)
    assert len(loaded) == len(decisions), "JSONL round-trip should preserve count"

    print(f"✓ Acquisition test passed: {len(decisions)} decisions acquired")
    return decisions


def test_normalization(raw_decisions):
    """Test normalization to canonical schema."""
    print("\n" + "=" * 60)
    print("TEST: Normalization to canonical schema")
    print("=" * 60)

    # Write raw to temp file for normalization test
    raw_path = "corpus/acquisition/raw/bger_test_2024.jsonl"
    canonical_path = "corpus/normalization/canonical/bger_test_2024.jsonl"

    stats = run_normalization(
        input_path=raw_path,
        output_path=canonical_path,
        source_version="opencaselaw_api_2026-08-26_test"
    )

    assert stats.total_output > 0, "Should produce normalized output"
    assert stats.total_output <= stats.total_input, "Output should not exceed input"

    # Validate each canonical decision against schema
    with open("corpus/schema/decision_schema.json", "r") as f:
        schema = json.load(f)
    validator = jsonschema.Draft7Validator(schema)

    with open(canonical_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            decision = json.loads(line)
            errors = list(validator.iter_errors(decision))
            assert not errors, f"Decision {i} validation failed: {errors}"

            # Check required fields
            assert "decision_id" in decision
            assert "court" in decision
            assert "docket_number" in decision
            assert "decision_date" in decision
            assert "language" in decision
            assert "full_text" in decision
            assert "provenance" in decision
            assert "content_hash" in decision["provenance"]

    print(f"✓ Normalization test passed: {stats.total_output} canonical decisions validated")
    return stats


def test_deduplication():
    """Test that content-hash deduplication works."""
    print("\n" + "=" * 60)
    print("TEST: Deduplication by content hash")
    print("=" * 60)

    from corpus.normalization.normalize import DecisionNormalizer

    normalizer = DecisionNormalizer()

    # Create two identical raw decisions with valid schema values
    text = "This is a test decision text that is long enough to pass the minimum length check for normalization purposes and contains enough content to be valid."
    content_hash = hashlib.sha256(text.encode()).hexdigest()

    raw1 = DecisionRaw(
        decision_id="bger_BGE_140_III_86",
        court="bger",
        decision_date="2024-01-15",
        language="de",
        title="Test Decision 1",
        regeste=None,
        citation_string_de=None,
        canonical_url="https://example.com/1",
        full_text=text,
        content_hash=content_hash,
        branch="zivilrecht",
        outcome="gutgeheissen",
        decision_type="Leitentscheid"
    )
    raw2 = DecisionRaw(
        decision_id="bger_BGE_141_II_100",
        court="bger",
        decision_date="2024-01-16",
        language="de",
        title="Test Decision 2",
        regeste=None,
        citation_string_de=None,
        canonical_url="https://example.com/2",
        full_text=text,  # Same text = same hash
        content_hash=content_hash,
        branch="strafrecht",
        outcome="abgewiesen",
        decision_type="Endentscheid"
    )

    source_version = "test_version"
    norm1 = normalizer.normalize(raw1, source_version)
    norm2 = normalizer.normalize(raw2, source_version)

    assert norm1 is not None, "First should normalize"
    assert norm2 is None, "Second should be deduplicated"

    print("✓ Deduplication test passed")
    return True


def test_schema_completeness():
    """Verify schema covers all required fields for legal-distance/fractal-map lanes."""
    print("\n" + "=" * 60)
    print("TEST: Schema completeness for downstream lanes")
    print("=" * 60)

    with open("corpus/schema/decision_schema.json", "r") as f:
        schema = json.load(f)

    required_fields = schema.get("required", [])
    properties = schema.get("properties", {})

    # Fields needed by legal-distance lane
    legal_distance_fields = [
        "full_text", "legal_area", "chamber", "branch", "proceeding_type",
        "regeste", "cited_decisions", "cited_laws", "outcome", "decision_type",
        "bge_reference", "language", "decision_date"
    ]
    for field in legal_distance_fields:
        assert field in properties, f"Missing field for legal-distance: {field}"

    # Fields needed by fractal-map lane
    fractal_fields = [
        "decision_id", "court", "decision_date", "legal_area", "chamber"
    ]
    for field in fractal_fields:
        assert field in properties, f"Missing field for fractal-map: {field}"

    # Fields needed by evaluation lane
    eval_fields = [
        "provenance", "source_url", "docket_number"
    ]
    for field in eval_fields:
        assert field in properties, f"Missing field for evaluation: {field}"

    # content_hash is nested in provenance
    prov_props = properties.get("provenance", {}).get("properties", {})
    assert "content_hash" in prov_props, "Missing content_hash in provenance"

    # Provenance sub-fields
    prov_props = properties.get("provenance", {}).get("properties", {})
    assert "source" in prov_props
    assert "acquired_at" in prov_props
    assert "source_version" in prov_props
    assert "content_hash" in prov_props
    assert "raw_metadata" in prov_props

    print("✓ Schema completeness test passed")
    return True


def main():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("# CORPUS LANE PIPELINE TESTS")
    print("#" * 60)

    # Run tests
    raw_decisions = test_acquisition()
    test_normalization(raw_decisions)
    test_deduplication()
    test_schema_completeness()

    print("\n" + "#" * 60)
    print("# ALL TESTS PASSED")
    print("#" * 60)


if __name__ == "__main__":
    main()