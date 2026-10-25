"""Map integrity: point = decision, and empty shells are disclosed.

Direction v68 / FAST-MVP cycle 40230559317.  The accepted business-judgment-rule
bundle of run 40227581597 rendered two BGE decisions as four points
(``bge_113 II 52`` beside ``bge_BGE_113_II_52``, and the same for 121 II 97)
and carried 13 rows with no local excerpt, none of which the summary named.
These tests pin the repair and the measurement that re-derives it from committed
bytes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(PRODUCT), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import offline_slice as ofs  # noqa: E402
import map_integrity_probe as mip  # noqa: E402
from product.query.bundle import (  # noqa: E402
    annotate_content_state,
    bundle_summary,
    content_coverage,
    content_state,
)
from product.query.pipeline import (  # noqa: E402
    _decision_identity,
    merge_duplicate_identities,
)

PROBE_ARTIFACT = ROOT / "results/product/map_integrity/CYCLE_40230559317.json"


def _bge(decision_id: str, **extra) -> dict:
    return {"decision_id": decision_id, "court": "bge", "rank": 1, **extra}


def test_bge_spelling_variants_share_one_identity():
    plain = _bge("bge_113 II 52", docket_number="113 II 52", citation="113 II 52")
    prefixed = _bge("bge_BGE_113_II_52", docket_number="BGE 113 II 52", citation="BGE 113 II 52")
    citation_only = {"decision_id": "bge_113_II_52", "court": "bge", "citation": "BGE 113 II 52"}
    assert _decision_identity(plain) == _decision_identity(prefixed)
    assert _decision_identity(plain) == _decision_identity(citation_only)
    assert _decision_identity(plain) == ("bge", "bge-113-ii-52")


def test_bge_aliases_merge_to_one_point_and_are_exported():
    rows = [
        _bge("bge_113 II 52", rank=40, docket_number="113 II 52", citation="113 II 52"),
        _bge("bge_BGE_113_II_52", rank=41, docket_number="BGE 113 II 52",
             citation="BGE 113 II 52"),
        _bge("bge_121 II 97", rank=50, docket_number="121 II 97", citation="121 II 97"),
        _bge("bge_BGE_121_II_97", rank=51, docket_number="BGE 121 II 97",
             citation="BGE 121 II 97"),
    ]
    kept, merges = merge_duplicate_identities(rows)
    assert len(kept) == 2
    # The kept alias is chosen by the deterministic row-strength rule; what the
    # map requires is one point per identity and an exported merge record.
    pairs = {
        frozenset({"bge_113 II 52", "bge_BGE_113_II_52"}),
        frozenset({"bge_121 II 97", "bge_BGE_121_II_97"}),
    }
    observed = {
        frozenset({merge["kept_decision_id"], *merge["merged_decision_ids"]})
        for merge in merges
    }
    assert observed == pairs
    assert all(merge["identity"]["court"] == "bge" for merge in merges)


def test_distinct_bge_decisions_and_egmr_are_not_merged():
    rows = [
        _bge("bge_BGE_113_II_52"),
        _bge("bge_BGE_113_II_53"),       # different page: different decision
        {"decision_id": "bge_egmr_20140121_23604_11", "court": "bge_egmr"},
    ]
    kept, merges = merge_duplicate_identities(rows)
    assert len(kept) == 3
    assert merges == []
    assert _decision_identity(rows[2]) is None


def test_docket_identity_dedupe_is_unchanged():
    rows = [
        {"decision_id": "bger_4A_1_2020", "court": "bger", "docket_number": "4A_1/2020"},
        {"decision_id": "bger_4A_1_2020_d20200101", "court": "bger",
         "docket_number": "4A_1/2020"},
    ]
    kept, merges = merge_duplicate_identities(rows)
    assert len(kept) == 1
    assert merges[0]["merged_decision_ids"] == ["bger_4A_1_2020"]


def test_content_state_is_measured_never_invented():
    rows = [
        {"decision_id": "full", "full_text": "text"},
        {"decision_id": "reg", "regeste": "regeste"},
        {"decision_id": "snip", "snippet": "extrait"},
        {"decision_id": "title", "title": "titre seul"},
        {"decision_id": "pointer"},
    ]
    states = [content_state(row) for row in rows]
    assert states == ["full_text", "regeste", "snippet", "snippet", "pointer"]
    coverage = content_coverage(rows)
    assert coverage["n_decisions"] == 5
    assert coverage["n_pointer_only"] == 1
    assert coverage["n_with_local_content"] == 4
    assert coverage["pointer_ids"] == ["pointer"]


def test_annotate_content_state_writes_rows_and_provenance():
    bundle = {
        "decisions": [
            {"decision_id": "a", "full_text": "text"},
            {"decision_id": "b"},
        ],
        "provenance": {},
    }
    annotate_content_state(bundle)
    assert [d["content_state"] for d in bundle["decisions"]] == ["full_text", "pointer"]
    assert bundle["provenance"]["content_coverage"]["n_pointer_only"] == 1
    assert bundle_summary(bundle)["content_coverage"]["pointer_ids"] == ["b"]


def test_offline_summary_separates_canonical_url_from_source_url():
    bundle = {
        "decisions": [
            {"decision_id": "a", "court": "bger", "language": "de", "rank": 1,
             "score": 1.0, "provenance": [], "snippet": "s", "cluster_id": 0,
             "x": 0.0, "y": 0.0, "counter_status": "none",
             "canonical_url": "https://mcp.opencaselaw.ch/entscheid/a",
             "source_url": None, "citation": "a"},
            {"decision_id": "b", "court": "bger", "language": "de", "rank": 2,
             "score": 0.9, "provenance": [], "snippet": "s", "cluster_id": 0,
             "x": 0.1, "y": 0.1, "counter_status": "none",
             "canonical_url": "https://mcp.opencaselaw.ch/entscheid/b",
             "source_url": "https://mcp.opencaselaw.ch/api/decisions/b", "citation": "b"},
        ],
        "clusters": [{"cluster_id": 0, "label": "C0"}],
        "answer": {"status": "ready", "cited_decision_ids": ["a"]},
        "provenance": {},
    }
    stats = ofs.summarise(bundle)
    assert stats["rows_with_canonical_url"] == 2
    assert stats["rows_with_source_url"] == 1
    assert stats["rows_with_source_link"] == 2
    assert stats["content_coverage"]["by_state"]["snippet"] == 2


def test_committed_family_has_no_duplicate_identity_and_names_pointer_rows():
    """Re-derive the committed measurement instead of trusting its JSON."""
    assert PROBE_ARTIFACT.is_file(), f"missing probe artifact: {PROBE_ARTIFACT}"
    published = json.loads(PROBE_ARTIFACT.read_text(encoding="utf-8"))
    assert published["success_met"] is True, published
    recomputed = mip.probe_paths([ROOT / p for p in published["bundle_paths"]])
    assert recomputed["n_bundles"] == published["n_bundles"] >= 4
    assert recomputed["n_decisions"] == published["n_decisions"]
    assert recomputed["n_duplicate_identity_groups"] == 0
    assert recomputed["n_duplicate_identity_groups"] == published["n_duplicate_identity_groups"]
    assert recomputed["n_pointer_only_rows"] == published["n_pointer_only_rows"]
    for bundle in recomputed["bundles"]:
        assert bundle["duplicate_groups"] == []
        assert bundle["content_coverage"]["n_decisions"] == bundle["n_decisions"]
        assert bundle["rows_with_canonical_url"] == bundle["n_decisions"]


def test_state_records_cycle_pointer_and_measured_delta():
    state = json.loads((ROOT / "state/product.json").read_text(encoding="utf-8"))
    assert state["direction_version"] == 68
    # The pointer advances when later cycles are accepted; validate the
    # both-halves invariant rather than freezing this cycle's literal.
    from product.state_contract import accepted_pointer_evidence
    pointer = accepted_pointer_evidence(state, ROOT)
    assert not pointer["problems"], pointer
    assert state["human_gate_ready"] is False
    assert state["machine_gate_ready"] is False
    assert state["continue_recommended"] is True
    block = state["cycle_40230559317_map_integrity"]
    published = json.loads(PROBE_ARTIFACT.read_text(encoding="utf-8"))
    assert block["run_id"] == "40230559317"
    assert block["measurements"]["n_duplicate_identity_groups"] == 0
    assert block["measurements"]["n_duplicate_identity_groups"] == published["n_duplicate_identity_groups"]
    assert block["measurements"]["n_pointer_only_rows"] == published["n_pointer_only_rows"]
    assert block["measurements"]["probe"] == "results/product/map_integrity/CYCLE_40230559317.json"
