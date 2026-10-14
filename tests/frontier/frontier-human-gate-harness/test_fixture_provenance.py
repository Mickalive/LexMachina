"""The frozen fixture and its provenance (reuse-first, no fabricated data)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _bootstrap import FIXTURE_DIR, FIXTURE_PATH, HARNESS_ROOT, PROVENANCE_PATH, load_fixture

from frontier_human_gate_harness.bundle_io import (CONVENTIONAL_FIELDS,
                                                   product_contract_errors,
                                                   validate_bundle_mirror)


def test_fixture_satisfies_both_bundle_contracts():
    if not FIXTURE_PATH.is_file():
        from unittest import SkipTest

        raise SkipTest(f"fixture missing: {FIXTURE_PATH}")
    bundle = load_fixture()
    assert validate_bundle_mirror(bundle) == []
    product_errors = product_contract_errors(bundle)
    if product_errors is not None:
        assert product_errors == [], product_errors
    assert len(bundle["decisions"]) >= 100
    ids = [d["decision_id"] for d in bundle["decisions"]]
    assert len(ids) == len(set(ids)), "duplicate decision_id in fixture"
    for decision in bundle["decisions"]:
        for field in CONVENTIONAL_FIELDS:
            assert field in decision, f"fixture decision lacks {field}"
    assert [d["rank"] for d in bundle["decisions"]] == list(
        range(1, len(bundle["decisions"]) + 1)), "fixture ranks must be 1..n in order"


def test_provenance_declares_source_regeneration_and_hash_semantics():
    prov = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    assert prov["fixture_file"] == FIXTURE_PATH.name
    assert prov["generator"].endswith("tools/make_fixture.py")
    assert prov["source_root_used"]
    assert prov["source_inputs_sha256"] and len(prov["source_inputs_sha256"]) == 64
    assert prov["accepted_source_branch"].startswith("lab/frontier/")
    assert "--check" in prov["how_to_regenerate"]
    assert set(prov["convention_fields_checked"]) >= set(CONVENTIONAL_FIELDS)
    import hashlib

    assert prov["fixture_file_sha256"] == hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
    assert prov["fixture_sha256"] == prov["fixture_file_sha256"]
    assert len(prov["bundle_canonical_sha256"]) == 64
    assert "hash_semantics" in prov and "canonical" in prov["hash_semantics"]
    generator = HARNESS_ROOT / "tools" / "make_fixture.py"
    assert prov["generator_sha256"] == hashlib.sha256(generator.read_bytes()).hexdigest()


def test_regeneration_is_byte_identical_offline():
    prov = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    source = Path(prov["source_root_used"])
    if not source.is_dir():
        from unittest import SkipTest

        raise SkipTest(f"accepted source fixtures not mounted: {source}")
    proc = subprocess.run([sys.executable, "tools/make_fixture.py", "--check"],
                          capture_output=True, text=True, cwd=str(HARNESS_ROOT), timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "byte-identical" in proc.stdout


def test_no_classification_or_reranking_is_claimed():
    bundle = load_fixture()
    statuses = {d["counter_status"] for d in bundle["decisions"]}
    assert statuses == {"unclassified"}, \
        f"fixture must claim no counter classification, saw {statuses}"
    notice = bundle["provenance"]["fixture_notice"]
    assert "unclassified" in notice and "no counter-authority classification" in notice
    assert "not product reranking" in notice
    assert "TEST geometry" in notice
    assert bundle["relations"] == []
    assert bundle["provenance"]["rules"]["counter_status"].startswith("literal 'unclassified'")


def test_dropped_and_empty_source_values_are_listed_not_filled():
    bundle = load_fixture()
    counts = bundle["provenance"]["counts"]
    assert counts["dropped_records_missing_source_key"] == len(counts["dropped_decision_ids"])
    assert "bge_BGE_118_II_50" in counts["dropped_decision_ids"], \
        "the record dropped for a missing language key must stay documented"
    ids = {d["decision_id"] for d in bundle["decisions"]}
    for dropped in counts["dropped_decision_ids"]:
        assert dropped not in ids, "a dropped record was silently re-added"

    empty = bundle["provenance"]["empty_conventional_values"]
    by_id = {d["decision_id"]: d for d in bundle["decisions"]}
    for field, decision_ids in empty.items():
        assert field in CONVENTIONAL_FIELDS
        for did in decision_ids:
            assert did in by_id, f"empty_conventional_values references dropped id {did}"
            assert by_id[did][field] == "", f"{did}.{field} listed empty but is not empty"
    # every empty value in the data must be declared (nothing hidden)
    for decision in bundle["decisions"]:
        for field in CONVENTIONAL_FIELDS:
            value = decision[field]
            if value == "" or value is None:
                listed = empty.get(field, [])
                assert decision["decision_id"] in listed, \
                    f"{decision['decision_id']}.{field} is empty but not declared"


def test_fixture_directory_contains_only_the_two_frozen_files():
    names = sorted(p.name for p in FIXTURE_DIR.iterdir() if p.is_file())
    assert names == ["FIXTURE_PROVENANCE.json", "query_result_bundle_kuendigung_101.json"], names
