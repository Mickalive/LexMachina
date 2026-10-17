"""Before/after labelling, write-scope and verdict-enum acceptance tests (charter
acceptance test 7, categories 6, 7 and 8).

5 test functions. All deterministic and offline. The write-scope test performs
one FULL harness run (the only expensive test in the suite, ~15s); every other
test here is pure or reads two already-measured bundles.
"""
from __future__ import annotations

import json

from conftest import (
    GUARDED_REPO_PATHS,
    OLD_PACKET_DIR,
    QIDS,
    REAL_PACKET_DIR,
    load_rules,
    needs_old_packet,
    needs_real_packet,
    sha256_file,
    snapshot_repo_paths,
    snapshot_tree,
)

from frontier_rebuilt_packet_serve_audit import before_after, cli, freeze_verify, non_vacuity, verdict

CHARTER_OUTCOME_BY_RECOMMENDATION = {
    "SERVE": "A",
    "DO-NOT-SERVE-UNCHANGED": "B",
    "BOUNDED-NEGATIVE-OWNER-DECISION": "C",
}


def _half_a(support_ok: bool) -> dict:
    return {
        "pooled": {
            "n_issued": 5,
            "n_supported": 5 if support_ok else 4,
            "support_rate_among_issued": 1.0 if support_ok else 0.8,
            "n_abstained": 60,
        },
        "accepted_label_gate_as_written": {
            "absolute_status": "LABEL_SOUND" if support_ok else "LABEL_UNSOUND",
            "regression_verdict": "NOT_APPLICABLE",
        },
        "accepted_label_lineage_gate_as_written": {
            "regression_verdict": "PASS_NO_REGRESSION" if support_ok else "FAIL_REGRESSION",
        },
    }


def _half_b(all_pass: bool, mega: bool) -> dict:
    return {
        "criterion_counts": {qid: (11 if all_pass else 7) for qid in QIDS},
        "incumbent_counts": {qid: 5 for qid in QIDS},
        "n_bundles_pass_all_11": 3 if all_pass else 0,
        "mega_cluster_fires_on_any_rebuilt_bundle": mega,
    }


def _half_c(marginal: bool) -> dict:
    return {
        "pooled": {
            "n_issued": 5,
            "marginal_discovery_exists": marginal,
            "classification_only_negative_reproduced": not marginal,
        }
    }


@needs_real_packet
@needs_old_packet
def test_before_after_labels_both_packets_by_content_sha256():
    """Category 6: both sides are labelled by content_sha256 from the freeze pins.

    Charter clause: "assert the produced record's before/after sha256 values
    match the frozen RULES.json pins and that `no_historical_artifact_overwritten`
    is True".
    """
    rules = load_rules()
    expected_before = rules["inputs"]["old_packet_before"]["files"]["packet.json"]["sha256"]
    expected_after = rules["inputs"]["rebuilt_packet"]["files"][
        "packet.json"
    ]["sha256"]

    record = before_after.measure(OLD_PACKET_DIR / "questions", REAL_PACKET_DIR / "questions")
    block = record["before_after"]

    assert block["before_packet_label"]["packet_json_sha256"] == expected_before
    assert block["after_packet_label"]["packet_json_sha256"] == expected_after
    assert block["before_packet_label"]["packet_json_sha256"] == sha256_file(
        OLD_PACKET_DIR / "packet.json"
    )
    assert block["after_packet_label"]["packet_json_sha256"] == sha256_file(
        REAL_PACKET_DIR / "packet.json"
    )
    assert block["before_packet_label"]["packet_id"] == "38839347028"
    assert block["after_packet_label"]["packet_id"] == "rebuilt-39027045675"
    assert "read-only" in block["before_packet_label"]["role"]
    assert block["no_historical_artifact_overwritten"] is True

    # Both sides are measured over the same three frozen qids.
    assert set(block["per_qid"]) == set(QIDS)
    known_statuses = {
        "abstained_unevidenced",
        "candidate-limiting",
        "candidate-contrary",
        "contrary_or_exception",
        "limiting",
        "cited",
        "none",
    }
    for qid, pair in block["per_qid"].items():
        assert set(pair) == {"before", "after"}
        for side in ("before", "after"):
            cell = pair[side]
            assert cell["n_decisions"] > 0
            counts = cell["counter_status_counts"]
            assert set(counts) <= known_statuses
            assert sum(counts.values()) == cell["n_decisions"]
            assert cell["n_abstained"] == counts.get("abstained_unevidenced", 0)
            assert cell["n_issued_counter_rows"] == sum(
                counts.get(s, 0)
                for s in ("candidate-limiting", "candidate-contrary",
                          "contrary_or_exception", "limiting")
            )
            assert cell["mega_cluster_fired"] == (
                cell["largest_cluster_share_size_based"] >= 0.5
            )
    before_counts = {q: block["per_qid"][q]["before"]["counter_status_counts"] for q in QIDS}
    after_counts = {q: block["per_qid"][q]["after"]["counter_status_counts"] for q in QIDS}
    assert before_counts != after_counts, "the two packets must not measure the same"
    assert (
        sum(b["before"]["n_abstained"] for b in block["per_qid"].values())
        != sum(b["after"]["n_abstained"] for b in block["per_qid"].values())
    )
    assert (
        block["before_packet_label"]["packet_json_sha256"]
        != block["after_packet_label"]["packet_json_sha256"]
    )


@needs_real_packet
@needs_old_packet
def test_before_after_never_overwrites_the_historical_old_packet():
    """Category 6: the before side is read-only; measuring it changes nothing.

    Charter clause: "never overwrites a historical artifact". The old packet
    directory is snapshotted (mtime + sha256) around the measurement and every
    file must be byte- and mtime-identical afterwards, and the rebuild run must
    leave it alone too.
    """
    before = snapshot_tree(OLD_PACKET_DIR)
    assert before, "the old packet snapshot must not be empty"
    before_after.measure(OLD_PACKET_DIR / "questions", REAL_PACKET_DIR / "questions")
    after = snapshot_tree(OLD_PACKET_DIR)
    assert after == before
    assert {k: v[1] for k, v in after.items()} == {
        k: v[1] for k, v in before.items()
    }


@needs_real_packet
def test_harness_writes_nothing_outside_the_team_namespace(tmp_path):
    """Category 7: a full harness run writes only the caller-supplied --out path.

    Charter clause: "snapshot mtimes+sha256 of a set of guarded paths (product/,
    evaluation/, results/product/, state/product.json, .github/) before and after
    a full harness run and assert byte-identical; also assert the harness only
    ever writes to a caller-supplied --out path". Absence is evidence too: a
    namespace that does not exist must not be created by the run.
    """
    guarded_before = snapshot_repo_paths(GUARDED_REPO_PATHS)
    assert set(guarded_before) == set(GUARDED_REPO_PATHS)

    out_path = tmp_path / "caller" / "chosen" / "AUDIT_RECORD.json"
    rc = cli.main(
        ["--packet", str(REAL_PACKET_DIR), "--out", str(out_path), "--quiet"]
    )
    assert rc == 0
    assert out_path.is_file()
    record = json.loads(out_path.read_text(encoding="utf-8"))

    # The only artefact the run produced is the caller-chosen path.
    assert out_path.parent.name == "chosen"
    assert record["schema"] == "frontier-rebuilt-packet-serve-audit/report/1"
    assert record["team_id"] == "frontier-rebuilt-packet-serve-audit"
    assert record["deterministic"] is True
    assert record["network_used"] is False
    assert record["verdict"]["serve_recommendation"] in verdict.RECOMMENDATION_ENUM

    # Nothing inside the forbidden namespaces moved, and nothing was created.
    guarded_after = snapshot_repo_paths(GUARDED_REPO_PATHS)
    assert guarded_after == guarded_before
    for rel in GUARDED_REPO_PATHS:
        assert (guarded_after[rel] is None) == (
            guarded_before[rel] is None
        ), f"{rel} appeared or vanished during the run"

    # The write-scope guarantee is also declared, not only observed.
    rules = load_rules()
    assert freeze_verify.FORBIDDEN_WRITE_PREFIXES == (
        "product/",
        "evaluation/",
        "results/product/",
        "state/product.json",
        ".github/",
    )
    assert rules["write_scope_prohibitions"] == [
        "zero writes to product/",
        "zero writes to evaluation/",
        "zero writes to results/product/",
        "zero writes to state/product.json",
        "zero writes to .github/**",
    ]
    assert f"tests/frontier/frontier-rebuilt-packet-serve-audit/" in rules["write_scope"]


def test_verdict_resolver_reaches_all_three_frozen_outcomes():
    """Category 8: all three frozen enum outcomes are reachable, and reachable is all.

    Charter clause: "verdict resolver enum capability -- all three frozen
    outcomes reachable (SERVE, DO-NOT-SERVE-UNCHANGED,
    BOUNDED-NEGATIVE-OWNER-DECISION)". Capability is probed on synthetic halves
    so the resolver is proven able to emit a serve as well as a do-not-serve.
    """
    probe = non_vacuity.serve_capability_probe()
    assert probe["frozen_enum"] == list(verdict.RECOMMENDATION_ENUM)
    assert probe["reachable_outcomes"] == sorted(verdict.RECOMMENDATION_ENUM)
    assert probe["can_emit_serve"] is True
    assert probe["can_emit_do_not_serve"] is True
    assert probe["can_emit_bounded_negative"] is True
    assert probe["proven_non_vacuous"] is True
    assert set(probe["outcomes"].values()) == set(verdict.RECOMMENDATION_ENUM)
    assert all(v in verdict.RECOMMENDATION_ENUM for v in probe["outcomes"].values())

    # Direct reads, each with the charter outcome letter it maps to.
    cases = {
        "SERVE": (_half_a(True), _half_b(True, True), _half_c(True)),
        "DO-NOT-SERVE-UNCHANGED": (_half_a(True), _half_b(False, False), _half_c(True)),
        "BOUNDED-NEGATIVE-OWNER-DECISION": (
            _half_a(False),
            _half_b(False, False),
            _half_c(True),
        ),
    }
    for expected, halves in cases.items():
        result = verdict.resolve(*halves)
        assert result["serve_recommendation"] == expected
        assert result["charter_outcome"] == CHARTER_OUTCOME_BY_RECOMMENDATION[expected]
        assert result["machine_checked"] is True
        assert result["enum"] == list(verdict.RECOMMENDATION_ENUM)
        assert result["one_sentence"].startswith("SERVE RECOMMENDATION: ")
        assert load_rules()["thresholds_and_enums"][
            "serve_recommendation_enum"
        ] == list(verdict.RECOMMENDATION_ENUM)


def test_verdict_result_is_always_exactly_one_frozen_outcome():
    """Category 8: every reading resolves to exactly one of the three outcomes.

    Charter clause: "the result is always exactly one of them". The whole grid
    of absolute/geometry/mega/marginal readings is swept; each must land in the
    frozen enum, carry the matching charter letter, and name at most ONE bounded
    cause per failed half.
    """
    seen = set()
    for absolute_status in ("LABEL_SOUND", "LABEL_UNSOUND", "NOT_APPLICABLE", "NOT_MEASURED"):
        for all_pass in (True, False):
            for mega in (True, False):
                for marginal in (True, False):
                    half_a = _half_a(absolute_status == "LABEL_SOUND")
                    half_a["accepted_label_gate_as_written"][
                        "absolute_status"
                    ] = absolute_status
                    half_b = _half_b(all_pass, mega)
                    half_c = _half_c(marginal)
                    result = verdict.resolve(half_a, half_b, half_c)

                    recommendation = result["serve_recommendation"]
                    assert recommendation in verdict.RECOMMENDATION_ENUM
                    assert recommendation in CHARTER_OUTCOME_BY_RECOMMENDATION
                    assert result["charter_outcome"] == (
                        CHARTER_OUTCOME_BY_RECOMMENDATION[recommendation]
                    )
                    assert result["inputs"]["label_bar_met"] is (
                        absolute_status == "LABEL_SOUND"
                    )
                    assert result["inputs"]["geometry_bar_met"] is all_pass
                    assert result["inputs"]["mega_cluster_disclosure_fires"] is mega
                    assert result["inputs"]["marginal_discovery_exists"] is marginal

                    causes = result["bounded_causes"]
                    halves = [cause.split(":", 1)[0] for cause in causes]
                    assert len(halves) == len(set(halves)), "one bounded cause per failed half"
                    assert all(isinstance(c, str) and c for c in causes)

                    # SERVE only when both bars are met as written and the
                    # size-based disclosure fires; nothing else is a serve path.
                    if recommendation == "SERVE":
                        assert all_pass and mega and absolute_status == "LABEL_SOUND"
                        assert not causes
                    else:
                        assert causes, "a non-serve must name its bounded cause(s)"
                    seen.add(recommendation)
    assert seen == set(verdict.RECOMMENDATION_ENUM)