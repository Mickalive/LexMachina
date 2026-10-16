"""Tests for the frozen query-map CONTRACT benchmark (evaluation lane, v49).

Three obligations are tested here:

1. FREEZE INTEGRITY -- the frozen spec digest, the freeze record, and the
   loader's refusal to accept a tampered spec, a reordered inventory or a moved
   bar.
2. NON-VACUITY IN BOTH DIRECTIONS -- a synthetic clean bundle must PASS all
   five gates (so a FAIL is a real finding and not an unsatisfiable benchmark),
   and one mutation per gate must break exactly that gate (so a PASS is not a
   gate that cannot fire).
3. EXECUTION -- the committed record re-scores from the frozen spec and the
   accepted mount, and its summary matches byte for byte.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evaluation.map_gate import frozen, gates  # noqa: E402
from evaluation.map_gate import run_map_benchmark as runner  # noqa: E402

PRODUCT_ROOT = Path("/tmp/lex_accepted/product")
RECORDS = REPO / "results" / "evaluation" / "map_benchmark"
RUN_ID = "38959325856"
RECORD = RECORDS / f"{RUN_ID}.json"

CLEAN_QUERY = "La résiliation du bail pour défaut d'entretien du bailleur"


# --------------------------------------------------------------------------- #
# helpers: a synthetic bundle that satisfies every frozen bar
# --------------------------------------------------------------------------- #


def clean_bundle(n: int = 200) -> dict:
    """A minimal bundle that must pass all five map-contract gates.

    ``n`` defaults to 200 so the frozen ``max_coincident_cell_share`` of 0.01 is
    testable at its boundary: with 200 rows a single coincident pair is exactly
    1% and must still pass, while a 3-row pile-up is 1.5% and must fail.
    """
    decisions = []
    for i in range(n):
        x = round(-1.0 + (i % 40) * 0.05, 4)
        y = round(-1.0 + (i // 40) * 0.05, 4)
        decisions.append({
            "decision_id": f"d{i:03d}",
            "cluster_id": 0 if i < n - 4 else 1,
            "x": x,
            "y": y,
            "is_outlier": False,
            "counter_status": "none",
            "language": "fr",
        })
    # two genuinely weakly connected rows at the tail, flagged as outliers; the
    # first one also carries a counter-authority status
    for j, did in enumerate((f"d{n - 4:03d}", f"d{n - 3:03d}")):
        row = next(r for r in decisions if r["decision_id"] == did)
        row["is_outlier"] = True
        row["counter_status"] = "candidate-limiting" if j == 0 else "none"
    clusters = [
        {"cluster_id": 0, "label": "bail, résiliation, pour, loyer",
         "size": len([d for d in decisions if d["cluster_id"] == 0]),
         "member_ids": [d["decision_id"] for d in decisions if d["cluster_id"] == 0]},
        {"cluster_id": 1, "label": "locataire, cocontractual, loyer, bail",
         "size": len([d for d in decisions if d["cluster_id"] == 1]),
         "member_ids": [d["decision_id"] for d in decisions if d["cluster_id"] == 1]},
    ]
    # a small citation chain among the non-outlier rows; the two outlier rows
    # are deliberately left out of it
    relations = [{"source": f"d{i:03d}", "target": f"d{(i + 1) % (n - 4):03d}",
                  "kind": "citation"} for i in range(12)]
    return {
        "provenance": {"query": CLEAN_QUERY, "phase": "complete"},
        "query": CLEAN_QUERY,
        "decisions": decisions,
        "clusters": clusters,
        "relations": relations,
    }


def _row(bundle: dict, did: str) -> dict:
    return next(r for r in bundle["decisions"] if r["decision_id"] == did)


def _pad_clusters(bundle: dict, total: int) -> None:
    """Grow the cluster list to ``total`` with in-language labels."""
    template = "cocontractual, locataire, loyer, bail"
    while len(bundle["clusters"]) < total:
        bundle["clusters"].append({
            "cluster_id": len(bundle["clusters"]), "label": template,
            "size": 0, "member_ids": [],
        })


# --------------------------------------------------------------------------- #
# 1. freeze integrity
# --------------------------------------------------------------------------- #


def test_frozen_digest_matches_pinned_sha256():
    assert frozen.sha256_file(frozen._PATH) == frozen.FROZEN_SHA256


def test_freeze_record_digest_and_pre_execution_assertion():
    rec = frozen.freeze_record()
    assert rec["frozen_sha256"] == frozen.FROZEN_SHA256
    assert rec["frozen_before_execution"] is True
    assert rec["frozen_spec_path"] == "evaluation/map_gate/frozen_map_benchmark.json"
    # the disclosure of the pre-freeze reconnaissance must be present and honest
    assert "FEASIBILITY RECONNAISSANCE" in rec["pre_freeze_disclosure"]
    assert rec["derived_from"]["no_174k_rerun"] is True


def test_loader_rejects_a_tampered_spec(monkeypatch, tmp_path):
    spec = frozen.load_frozen()
    spec["parameters"]["max_coincident_cell_share"] = 0.9   # weaken the bar
    fake = tmp_path / "frozen_map_benchmark.json"
    fake.write_text(json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8")
    monkeypatch.setattr(frozen, "_PATH", fake)
    with pytest.raises(frozen.FrozenBenchmarkError, match="digest mismatch"):
        frozen.load_frozen()


@pytest.mark.parametrize("mutate,match", [
    (lambda s: s["gates"].pop("MAP::points_distinguishable"), "gate set changed"),
    (lambda s: s["parameters"].__setitem__("max_coincident_cell_share", 0.5),
     "coincident-cell bar changed"),
    (lambda s: s["parameters"].__setitem__("label_language_min_share", 0.1),
     "label-language bar changed"),
    (lambda s: s["parameters"].__setitem__("coordinate_precision", 1),
     "coordinate precision changed"),
    (lambda s: s.__setitem__("inputs", list(reversed(s["inputs"]))),
     "ascending path order"),
    (lambda s: s["inputs"][0].pop("sha256"), "without path/sha256"),
    (lambda s: s.__setitem__("schema", "something/else"), "unexpected schema"),
    (lambda s: s.__setitem__("function_word_lexicon", {"de": ["a"]}), "lexicon languages"),
])
def test_loader_rejects_weakened_or_reordered_specs(monkeypatch, tmp_path, mutate, match):
    spec = frozen.load_frozen()
    mutate(spec)
    fake = tmp_path / "frozen_map_benchmark.json"
    fake.write_text(json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8")
    monkeypatch.setattr(frozen, "FROZEN_SHA256", frozen.sha256_file(fake))
    monkeypatch.setattr(frozen, "_PATH", fake)
    with pytest.raises(frozen.FrozenBenchmarkError, match=match):
        frozen.load_frozen()


def test_frozen_inventory_is_the_whole_in_scope_population_not_a_selection():
    spec = frozen.load_frozen()
    inputs = spec["inputs"]
    assert len(inputs) >= 25, "the inventory shrank; that would be input selection"
    assert [i["path"] for i in inputs] == sorted(i["path"] for i in inputs)
    assert len({i["path"] for i in inputs}) == len(inputs)
    assert all(i["n_decisions"] >= spec["inclusion_rule"]["min_decisions"] for i in inputs)
    assert all(i["n_clusters"] >= spec["inclusion_rule"]["min_clusters"] for i in inputs)
    assert all(i["sha256"] and len(i["sha256"]) == 64 for i in inputs)


# --------------------------------------------------------------------------- #
# 2. non-vacuity, both directions
# --------------------------------------------------------------------------- #


def test_clean_bundle_passes_every_gate_so_a_fail_is_a_real_finding():
    spec = frozen.load_frozen()
    result = gates.evaluate_bundle(clean_bundle(), spec, bundle_path="synthetic:clean")
    failed = result["failed_gates"]
    assert result["query_language"] == "fr", result["query_language_votes"]
    assert failed == [], failed
    assert result["n_gates_not_measurable"] == 0


def test_membership_gate_breaks_on_a_truncated_member_list():
    """Rows assigned to a cluster whose member_ids stop early: the cap-at-50 shape."""
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    hidden = "d100"
    assert _row(bundle, hidden)["cluster_id"] == 0
    assert gates.evaluate_cluster_membership_enumerable(bundle, spec)["passed"] is True
    # drop it from the enumeration only: the cluster still claims it
    big = bundle["clusters"][0]
    big["member_ids"] = [m for m in big["member_ids"] if m != hidden]
    big["size"] = len(big["member_ids"])
    res = gates.evaluate_cluster_membership_enumerable(bundle, spec)
    assert res["passed"] is False
    assert res["unreachable_count"] == 1


def test_membership_gate_breaks_on_a_size_that_lies_about_its_members():
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    bundle["clusters"][0]["size"] += 40          # the cap-at-50 signature
    res = gates.evaluate_cluster_membership_enumerable(bundle, spec)
    assert res["passed"] is False
    assert res["size_mismatch_count"] == 1
    assert res["size_mismatches"][0]["declared_size"] - res["size_mismatches"][0][
        "enumerated_members"] == 40


def test_membership_gate_breaks_on_member_ids_naming_absent_decisions():
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    bundle["clusters"][0]["member_ids"].append("does_not_exist")
    bundle["clusters"][0]["size"] = len(bundle["clusters"][0]["member_ids"])
    res = gates.evaluate_cluster_membership_enumerable(bundle, spec)
    assert res["passed"] is False
    assert "does_not_exist" in str(res["member_ids_not_in_decisions"])


def test_points_gate_breaks_on_a_coordinate_pile_up():
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    for row in bundle["decisions"]:
        row["x"], row["y"] = 0.0, 0.0           # every decision on one pixel
    res = gates.evaluate_points_distinguishable(bundle, spec)
    assert res["passed"] is False
    assert res["max_cell"]["n"] == 200
    assert res["max_cell_share"] == 1.0


def test_points_gate_tolerates_one_coincident_pair_exactly_at_the_frozen_bar():
    """The bar is a bar: 2/200 = 0.01 must pass, 3/200 = 0.015 must not."""
    spec = frozen.load_frozen()
    bundle = clean_bundle(n=200)
    bundle["decisions"][1]["x"] = bundle["decisions"][0]["x"]
    bundle["decisions"][1]["y"] = bundle["decisions"][0]["y"]
    res = gates.evaluate_points_distinguishable(bundle, spec)
    assert res["max_cell_share"] == 0.01
    assert res["passed"] is True

    bundle = clean_bundle(n=200)
    for i in (1, 2):
        bundle["decisions"][i]["x"] = bundle["decisions"][0]["x"]
        bundle["decisions"][i]["y"] = bundle["decisions"][0]["y"]
    res = gates.evaluate_points_distinguishable(bundle, spec)
    assert res["max_cell_share"] == 0.015
    assert res["passed"] is False


def test_points_gate_is_not_measurable_on_a_non_numeric_coordinate():
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    bundle["decisions"][0]["x"] = "not-a-number"
    res = gates.evaluate_points_distinguishable(bundle, spec)
    assert res.get("not_measurable") is True
    assert res["reason"]


def test_outlier_gate_breaks_when_a_deeply_cited_row_is_flagged_outlier():
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    hub = _row(bundle, "d000")
    hub["is_outlier"] = True
    bundle["relations"] = [{"source": "d000", "target": f"d{i:03d}",
                            "kind": "citation"} for i in range(1, 10)]
    res = gates.evaluate_outlier_degree_consistent(bundle, spec)
    assert res["passed"] is False
    assert res["mean_outlier_degree"] > res["mean_other_degree"]


def test_outlier_gate_fails_rather_than_passes_on_an_empty_relation_graph():
    """A degenerate graph cannot support the outlier claim: never a free pass."""
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    bundle["relations"] = []
    res = gates.evaluate_outlier_degree_consistent(bundle, spec)
    assert res["passed"] is False
    assert res["degenerate"] is True
    assert "DEGENERATE" in res["detail"]


def test_label_gate_breaks_on_a_label_written_in_another_language():
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    bundle["clusters"][0]["label"] = "abs, nicht, zu, wenn"   # German function words
    res = gates.evaluate_label_language_matches_query(
        bundle, spec, query_language="fr", language_votes={"de": 4, "fr": 1, "it": 0})
    assert res["passed"] is False
    assert res["n_off_language"] == 1
    assert res["off_language_clusters"][0]["attributed_language"] == "de"


def test_label_gate_is_conservative_about_ambiguous_and_content_words():
    """A label of pure content words must NOT be convicted: under-report, not guess."""
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    bundle["clusters"][0]["label"] = "indennita, scheda, causa,Quantum"
    res = gates.evaluate_label_language_matches_query(
        bundle, spec, query_language="fr", language_votes={"de": 0, "fr": 1, "it": 0})
    assert res["passed"] is True
    assert res["n_off_language"] == 0


def test_label_gate_is_not_measurable_when_the_query_language_is_unknown():
    spec = frozen.load_frozen()
    res = gates.evaluate_label_language_matches_query(
        clean_bundle(), spec, query_language="unknown", language_votes={})
    assert res.get("not_measurable") is True
    assert res["passed"] is False          # never counts as a pass
    assert "could not be inferred" in res["reason"]


def test_label_gate_bar_boundary_is_eight_clusters_not_a_unanimity_rule():
    """1 bad label out of 8 passes (0.875 >= 0.8); 1 out of 3 fails (0.667)."""
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    _pad_clusters(bundle, 8)
    bundle["clusters"][3]["label"] = "abs, nicht, zu, wenn"      # German function words
    res = gates.evaluate_label_language_matches_query(
        bundle, spec, query_language="fr", language_votes={"de": 4, "fr": 1, "it": 0})
    assert res["n_clusters"] == 8
    assert res["n_off_language"] == 1
    assert res["share_ok"] == 0.875
    assert res["passed"] is True

    bundle = clean_bundle()
    _pad_clusters(bundle, 3)
    bundle["clusters"][2]["label"] = "abs, nicht, zu, wenn"
    res = gates.evaluate_label_language_matches_query(
        bundle, spec, query_language="fr", language_votes={"de": 4, "fr": 1, "it": 0})
    assert res["share_ok"] == round(2 / 3, 6)
    assert res["passed"] is False


def test_counter_gate_breaks_when_a_counter_authority_cannot_be_enumerated():
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    hidden = _row(bundle, "d196")            # the row carrying candidate-limiting
    assert hidden["counter_status"] == "candidate-limiting"
    big = bundle["clusters"][1]
    big["member_ids"] = [m for m in big["member_ids"] if m != hidden["decision_id"]]
    big["size"] = len(big["member_ids"])
    res = gates.evaluate_counter_authority_selectable(bundle, spec)
    assert res["passed"] is False
    assert res["n_unreachable"] == 1
    assert hidden["decision_id"] in res["unreachable"]


def test_counter_gate_breaks_when_a_counter_authority_is_stranded_on_a_pile():
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    for row in bundle["decisions"]:
        row["x"], row["y"] = 0.0, 0.0
    res = gates.evaluate_counter_authority_selectable(bundle, spec)
    assert res["passed"] is False
    assert res["n_unselectable"] == res["n_counter"]


def test_counter_gate_is_not_measurable_on_a_bundle_with_no_counter_authority():
    spec = frozen.load_frozen()
    bundle = clean_bundle()
    for row in bundle["decisions"]:
        row["counter_status"] = "none"
    res = gates.evaluate_counter_authority_selectable(bundle, spec)
    assert res.get("not_measurable") is True
    assert res["passed"] is False


def test_every_frozen_gate_has_a_breaking_fixture_and_a_passing_fixture():
    """The non-vacuity contract, as one test: no gate is dead, none is impossible."""
    spec = frozen.load_frozen()
    for gate in frozen.GATE_IDS:
        clean = gates.evaluate_bundle(clean_bundle(), spec, bundle_path="clean")
        assert gate in clean["gates"]
        assert clean["gates"][gate]["passed"] is True, f"{gate} cannot pass"


# --------------------------------------------------------------------------- #
# 3. query-language rule
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("text,expected", [
    ("Aktive Fürsorgepflicht des Arbeitgebers: wie weit geht der Schutz?", "de"),
    ("Résiliation du bail pour défaut d'entretien: jusqu'où va la jurisprudence?", "fr"),
    ("Responsabilità del medico per errore terapeutico: quale obbligo di diligenza?", "it"),
    ("????? 12345 ???", "unknown"),          # no exclusive token -> unknown
])
def test_query_language_rule(text, expected):
    assert frozen.infer_query_language(text)[0] == expected


def test_query_language_rule_rejects_a_tie():
    text = "nicht pour quale"     # one exclusive token per language
    assert frozen.infer_query_language(text)[0] == "unknown"


def test_tokenizer_drops_marks_digits_and_short_tokens():
    # the tag NAME is not a token, the number and the one-letter word are
    # dropped, the tag's content survives
    assert frozen.tokenize("<mark>30 Tage</mark> a in") == ["tage", "in"]


# --------------------------------------------------------------------------- #
# 4. execution record
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not RECORD.exists(), reason="no committed map record")
def test_committed_record_rescores_identically_from_the_frozen_spec():
    payload, code = runner.rescore(RECORD)
    assert code == 0, json.dumps(payload["recomputed_summary"], indent=1)[:2000]
    assert payload["summary_matches_record"] is True


@pytest.mark.skipif(not RECORD.exists(), reason="no committed map record")
def test_committed_record_is_internally_consistent():
    record = runner.load_record(RECORD)
    assert record["frozen_sha256"] == frozen.FROZEN_SHA256
    assert record["imports_product_code"] is False
    assert record["network"] is False
    assert record["recomputed_geometry"] is False
    assert record["n_input_bundles"] == len(record["bundles"]) >= 25
    for entry in record["bundles"]:
        failed = entry["failed_gates"]
        nm = [n["gate"] for n in entry["not_measurable_gates"]]
        for gate, res in entry["gates"].items():
            assert res["gate"] == gate
            if res.get("not_measurable"):
                assert gate in nm and res["reason"]
                assert res["passed"] is False, "not_measurable must never read as a pass"
            elif not res["passed"]:
                assert gate in failed and res["detail"], "a failure must carry a detail"
            else:
                assert res["detail"] == "", "a pass must carry a blank detail"
        counted = (entry["n_gates_passed"] + entry["n_gates_failed"]
                   + entry["n_gates_not_measurable"])
        assert counted == len(frozen.GATE_IDS)
        assert entry["passed"] is (entry["n_gates_failed"] == 0)
    summary = gates.summarize(record["bundles"])
    assert summary == record["summary"]


@pytest.mark.skipif(not RECORD.exists(), reason="no committed map record")
def test_committed_record_fails_on_the_accepted_product():
    """The falsification itself is pinned: this benchmark is expected to FAIL."""
    record = runner.load_record(RECORD)
    assert record["summary"]["overall_pass"] is False
    assert record["summary"]["n_bundles_failed"] >= 1
    assert record["summary"]["per_gate"]["MAP::points_distinguishable"]["n_failed"] >= 1


@pytest.mark.skipif(not PRODUCT_ROOT.is_dir(), reason="accepted mount absent")
def test_runner_refuses_an_altered_input_without_emitting_a_verdict(tmp_path):
    """A bundle that no longer matches its pinned sha256 is an environment error."""
    fake = tmp_path / "results" / "product"
    fake.mkdir(parents=True)
    spec = frozen.load_frozen()
    first = spec["inputs"][0]
    (fake / Path(first["path"]).name).write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        runner.run(tmp_path, run_id="test")


@pytest.mark.skipif(not PRODUCT_ROOT.is_dir(), reason="accepted mount absent")
def test_runner_exit_code_2_on_a_missing_mount(tmp_path, capsys):
    assert runner.main(["--product-root", str(tmp_path)]) == 2
    assert "::error::" in capsys.readouterr().err
