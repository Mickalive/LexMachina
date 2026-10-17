"""Marginal-discovery, mega-cluster and determinism acceptance tests (charter
acceptance test 7, categories 5, 9 and 10).

7 test functions. All deterministic and offline: synthetic bundles are built from
fixed literals, the pseudo-random-free code paths are the ones under test, and
the two real-packet tests carry an explicit skipif. No geometry scoring is
re-run here.
"""
from __future__ import annotations

import json

from conftest import QIDS, load_rules, needs_real_packet, REAL_PACKET_DIR

from frontier_rebuilt_packet_serve_audit import geometry_half, marginal_discovery, verdict

K = marginal_discovery.FROZEN_K


def _row(rank: int, raw: float, status: str) -> dict:
    return {
        "decision_id": f"dec-{rank:03d}",
        "rank": rank,
        "retrieval_score_raw": raw,
        "counter_status": status,
        "language": "de",
    }


def _rows_24() -> list:
    """24 rows whose initial-pool order is computed, not assumed.

    issued rows: rank 3 (high raw, visible, present in pool), rank 20 (the Kth
    list row, visible, present in pool), rank 21 (past K, absent, invisible),
    rank 2 (visible in the list but the LOWEST raw score, so absent from the
    initial-pool top-K -- list depth and pool membership are independent).
    """
    rows = [_row(rank, round(0.60 - rank * 0.001, 6), "none") for rank in range(1, 25)]
    by_rank = {r["rank"]: r for r in rows}
    by_rank[3].update(counter_status="candidate-limiting", retrieval_score_raw=0.98)
    by_rank[20].update(counter_status="candidate-contrary", retrieval_score_raw=0.99)
    by_rank[21].update(counter_status="contrary_or_exception", retrieval_score_raw=0.10)
    by_rank[2].update(counter_status="limiting", retrieval_score_raw=0.01)
    by_rank[7].update(counter_status="cited")
    by_rank[9].update(counter_status="abstained_unevidenced")
    return rows


def _rows_flat_tie() -> list:
    """21 rows with identical raw scores, listed worst-rank-first on purpose.

    With every retrieval_score_raw equal, only the documented rank-ASC tie-break
    fixes the initial-pool order, so the issued row that is LAST on disk must
    still be measured at pool position 21 (outside the top-K).
    """
    rows = [_row(rank, 0.5, "none") for rank in range(21, 0, -1)]
    for row in rows:
        if row["rank"] == 21:
            row["counter_status"] = "candidate-contrary"
        elif row["rank"] == 1:
            row["counter_status"] = "candidate-limiting"
    return rows


def _row_by_id(result: dict) -> dict:
    return {r["decision_id"]: r for r in result["per_row"]}


def test_marginal_discovery_ranks_at_or_below_k_are_visible_and_deeper_ranks_are_counter_only(
    write_bundle, tmp_path
):
    """Category 5: rank <= K is visible; rank > K is counter-only in the map.

    Charter clause: "an issued row at rank <= K is
    visible_in_list_top_k; rank > K is
    counter_only_in_map_effectively_invisible_in_list". 'cited' and abstained
    rows are never issued rows, so they appear in no per-row cell.
    """
    questions = tmp_path / "questions"
    write_bundle(questions, QIDS[0], _rows_24())
    result = marginal_discovery.measure_bundle(questions, QIDS[0], k=K)
    assert result["K"] == K == 20
    assert result["n_decisions"] == 24
    assert result["n_issued"] == 4
    rows = _row_by_id(result)

    at_k = rows["dec-020"]
    assert at_k["rank"] == K
    assert at_k["visible_in_list_top_k"] is True
    assert at_k["encountered_in_list_before_map"] is True
    assert at_k["counter_only_in_map_effectively_invisible_in_list"] is False
    assert at_k["absent_from_initial_pool_top_k"] is False

    near_top = rows["dec-003"]
    assert near_top["visible_in_list_top_k"] is True
    assert near_top["absent_from_initial_pool_top_k"] is False

    past_k = rows["dec-021"]
    assert past_k["rank"] > K
    assert past_k["visible_in_list_top_k"] is False
    assert past_k["counter_only_in_map_effectively_invisible_in_list"] is True
    assert past_k["absent_from_initial_pool_top_k"] is True
    assert past_k["initial_pool_position"] > K

    # Visible in the list yet absent from the retrieval pool: the two channels
    # are measured independently.
    low_raw = rows["dec-002"]
    assert low_raw["rank"] <= K
    assert low_raw["visible_in_list_top_k"] is True
    assert low_raw["absent_from_initial_pool_top_k"] is True
    assert low_raw["initial_pool_position"] == 24

    assert "dec-007" not in rows and "dec-009" not in rows
    assert result["n_absent_from_initial_top_k"] == 2
    assert result["n_invisible_in_list_top_k"] == 1
    assert result["marginal_discovery_exists"] is True


def test_marginal_discovery_initial_pool_uses_raw_score_desc_with_rank_asc_tie_break(
    write_bundle, tmp_path
):
    """Category 5: absent_from_initial_pool_top_k comes from the frozen ordering.

    Charter clause: "absent_from_initial_pool_top_k computed from
    retrieval_score_raw ordering with the documented tie-break" (raw DESC, then
    rank ASC). Every row shares one raw score, so the tie-break alone decides
    membership of the top-K.
    """
    questions = tmp_path / "questions"
    write_bundle(questions, QIDS[0], _rows_flat_tie())
    result = marginal_discovery.measure_bundle(questions, QIDS[0], k=K)
    rows = _row_by_id(result)
    assert result["n_issued"] == 2
    assert rows["dec-001"]["initial_pool_position"] == 1
    assert rows["dec-001"]["absent_from_initial_pool_top_k"] is False
    assert rows["dec-021"]["initial_pool_position"] == 21
    assert rows["dec-021"]["absent_from_initial_pool_top_k"] is True
    assert result["n_absent_from_initial_top_k"] == 1
    # The same reading holds without the harness wrapper's per-qid ordering.
    ordered = marginal_discovery._initial_pool_order({"decisions": _rows_flat_tie()})
    assert [r["rank"] for r in ordered] == list(range(1, 22))


def test_marginal_discovery_with_no_issued_rows_reproduces_no_negative(write_bundle, tmp_path):
    """Category 5: an empty issued set is neither discovery nor a reproduced negative.

    Charter clause: "empty issued set gives marginal_discovery_exists False and
    classification_only_negative_reproduced False (no_issued_rows_at_all True)".
    """
    questions = tmp_path / "questions"
    for qid in QIDS:
        write_bundle(
            questions,
            qid,
            [
                _row(1, 0.9, "none"),
                _row(2, 0.8, "cited"),
                _row(3, 0.7, marginal_discovery.ABSTAIN_MARKER),
            ],
        )
    result = marginal_discovery.measure(questions, k=K)
    pooled = result["pooled"]
    assert result["K"] == 20
    assert result["initial_pool_definition"] == "retrieval_score_raw DESC, rank ASC"
    assert result["list_definition"] == "rank ASC (post rerank_product_bundle)"
    assert all(b["n_issued"] == 0 for b in result["per_bundle"].values())
    assert pooled["n_issued"] == 0
    assert pooled["n_absent_from_initial_top_k"] == 0
    assert pooled["n_invisible_in_list_top_k"] == 0
    assert pooled["marginal_discovery_exists"] is False
    assert pooled["classification_only_negative_reproduced"] is False
    assert pooled["no_issued_rows_at_all"] is True

    # The CLASSIFICATION_ONLY negative only reproduces when issued rows exist and
    # every one of them was already both in the pool and in the list top-K.
    all_visible = tmp_path / "all_visible" / "questions"
    for qid in QIDS:
        write_bundle(all_visible, qid, [_row(rank, 1.0 - rank * 0.01, "candidate-limiting")
                                       for rank in range(1, 4)])
    reproduced = marginal_discovery.measure(all_visible, k=K)["pooled"]
    assert reproduced["n_issued"] == 3 * len(QIDS)
    assert reproduced["marginal_discovery_exists"] is False
    assert reproduced["classification_only_negative_reproduced"] is True
    assert reproduced["no_issued_rows_at_all"] is False


def test_marginal_discovery_is_deterministic_on_fixed_synthetic_bundles(write_bundle, tmp_path):
    """Category 9: the same pure function on the same bytes twice is identical.

    Charter clause: "running the same pure function twice yields identical
    output (e.g. marginal_discovery.measure or verdict.resolve on fixed dicts)".
    """
    questions = tmp_path / "questions"
    for qid in QIDS:
        write_bundle(questions, qid, _rows_24())
    first = marginal_discovery.measure(questions, k=K)
    second = marginal_discovery.measure(questions, k=K)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    half_c = {"pooled": dict(first["pooled"])}
    half_a = {
        "pooled": {"n_issued": 4, "n_supported": 4, "support_rate_among_issued": 1.0,
                   "n_abstained": 60},
        "accepted_label_gate_as_written": {"absolute_status": "LABEL_SOUND"},
    }
    half_b = {
        "criterion_counts": {qid: 11 for qid in QIDS},
        "n_bundles_pass_all_11": 3,
        "mega_cluster_fires_on_any_rebuilt_bundle": True,
    }
    assert json.dumps(verdict.resolve(half_a, half_b, half_c), sort_keys=True) == json.dumps(
        verdict.resolve(half_a, half_b, half_c), sort_keys=True
    )


@needs_real_packet
def test_marginal_discovery_is_deterministic_on_the_real_packet():
    """Category 9 on real bytes: two reads of the shipped bundles agree exactly.

    Charter clause: the same determinism check on the packet under measurement
    (cheap half only -- no geometry scoring is re-run).
    """
    questions = REAL_PACKET_DIR / "questions"
    first = marginal_discovery.measure(questions, k=K)
    second = marginal_discovery.measure(questions, k=K)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["pooled"]["n_issued"] == sum(
        b["n_issued"] for b in first["per_bundle"].values()
    )
    for cell in first["per_bundle"].values():
        assert cell["K"] == 20
        assert [r["rank"] for r in cell["per_row"]] == sorted(
            r["rank"] for r in cell["per_row"]
        )


def test_size_based_mega_cluster_fires_at_the_frozen_bar_and_not_below():
    """Category 10: the disclosure fires at >= 0.5 and not below it.

    Charter clause: "size_based_mega_cluster fires at >= 0.5 and not below".
    The bar is the frozen one, not a threshold re-derived here.
    """
    assert geometry_half.MEGA_CLUSTER_BAR == 0.5
    assert load_rules()["thresholds_and_enums"]["mega_cluster_bar"] == 0.5

    decisions = [_row(rank, 1.0 - rank * 0.01, "none") for rank in range(1, 11)]
    at_bar = geometry_half.size_based_mega_cluster({
        "decisions": decisions,
        "clusters": [{"cluster_id": "c0", "size": 5, "member_ids": ["x"]},
                     {"cluster_id": "c1", "size": 5, "member_ids": ["y"]}],
    })
    assert at_bar["largest_cluster_size"] == 5
    assert at_bar["n_decisions"] == 10
    assert at_bar["largest_cluster_share"] == 0.5
    assert at_bar["bar"] == 0.5
    assert at_bar["fired"] is True
    assert at_bar["threshold_edited"] is False

    below = geometry_half.size_based_mega_cluster({
        "decisions": decisions,
        "clusters": [{"cluster_id": "c0", "size": 4, "member_ids": ["x"]},
                     {"cluster_id": "c1", "size": 4, "member_ids": ["y"]},
                     {"cluster_id": "c2", "size": 2, "member_ids": ["z"]}],
    })
    assert below["n_clusters"] == 3
    assert below["largest_cluster_share"] == 0.4
    assert below["fired"] is False

    # An empty cluster table measures nothing and fires nothing.
    none_fired = geometry_half.size_based_mega_cluster({"decisions": decisions})
    assert none_fired["fired"] is False
    assert none_fired["largest_cluster_share"] == 0.0


def test_mega_cluster_disclosure_uses_cluster_size_not_capped_member_ids():
    """Category 10: cluster['size'] decides, never the capped member_ids length.

    Charter clause: "size-based (cluster['size']), not member_ids length (capped
    at 50) -- construct a synthetic bundle where the two differ and assert the
    size-based reading is used". Both directions of disagreement are constructed:
    size says fire while member_ids does not, and member_ids says fire while size
    does not.
    """
    decisions = [_row(rank, 1.0 - rank * 0.01, "none") for rank in range(1, 11)]

    size_fires = geometry_half.size_based_mega_cluster({
        "decisions": decisions,
        "clusters": [
            {"cluster_id": "c0", "size": 7, "member_ids": ["a", "b"]},
            {"cluster_id": "c1", "size": 3, "member_ids": ["c", "d", "e", "f"]},
        ],
    })
    assert size_fires["largest_cluster_size"] == 7
    assert size_fires["largest_cluster_share"] == 0.7
    assert size_fires["largest_cluster_member_ids_share"] == 0.2
    assert size_fires["largest_cluster_member_ids_share"] < geometry_half.MEGA_CLUSTER_BAR
    assert size_fires["fired"] is True
    assert size_fires["size_based_not_member_ids"] is True
    assert "size" in size_fires["definition"] and "member_ids" not in size_fires["definition"]

    member_ids_would_fire = geometry_half.size_based_mega_cluster({
        "decisions": decisions,
        "clusters": [
            {"cluster_id": "c0", "size": 3, "member_ids": ["a", "b", "c", "d", "e", "f"]},
            {"cluster_id": "c1", "size": 3, "member_ids": ["g"]},
        ],
    })
    assert member_ids_would_fire["largest_cluster_share"] == 0.3
    assert member_ids_would_fire["largest_cluster_member_ids_share"] == 0.6
    assert member_ids_would_fire["fired"] is False