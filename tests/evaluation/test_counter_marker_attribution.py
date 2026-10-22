"""Tests for the V62 counter-marker attribution benchmark.

Plain pytest-style functions with no fixtures, so the lane's
``evaluation/no_pytest_runner.py`` shim can execute them in the producer
image where pytest is ABSENT.  Anything the shim cannot express is reported
UNSUPPORTED and counted NOT-RUN, never as passed.

The integration cases replay the COMMITTED cache read-only and write any
scratch record only under a tmp out path; they never rewrite a committed
claim-bearing record.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from evaluation import counter_marker_attribution as cma
from evaluation.query_map.bundle_producer import index_cache, read_cache

REPO = Path(__file__).resolve().parent.parent.parent
SPEC = REPO / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"
CACHE = REPO / "results/evaluation/retrieval_benchmark/cache"
ACCEPTED = REPO / "results/evaluation/query_map_cached_bundle_benchmark/39766474798.json"


def _spec():
    return json.loads(SPEC.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- class axis
def test_classify_row_both_on_marker_is_labelled():
    assert cma.classify_row(["n"], ["n"], ["l"], ["l"]) == "LABELLED"


def test_classify_row_limitation_absent_everywhere():
    assert cma.classify_row(["n"], ["n"], [], []) == "LIMITATION_LEXICON_ABSENT"


def test_classify_row_norm_absent_everywhere_limited_present():
    assert cma.classify_row([], [], ["l"], ["l"]) == "NORM_LEXICON_ABSENT"


def test_classify_row_norm_surface_miss():
    assert cma.classify_row([], ["n"], ["l"], ["l", "x"]) == "NORM_SURFACE_MISS"


def test_classify_row_limitation_surface_miss():
    assert cma.classify_row(["n"], ["n", "y"], [], ["l"]) == "LIMITATION_SURFACE_MISS"


def test_classify_row_both_surface_miss():
    assert cma.classify_row([], ["n"], [], ["l"]) == "BOTH_SURFACE_MISS"


def test_classify_row_both_lexicons_absent_is_limitation_absent_by_priority():
    """Both ABSENT_ROW: the frozen priority reports LIMITATION_LEXICON_ABSENT;
    the axis states remain visible to the caller via axis_state."""
    assert cma.classify_row([], [], [], []) == "LIMITATION_LEXICON_ABSENT"
    assert cma.axis_state([], []) == "ABSENT_ROW"


def test_class_priority_is_total_and_blindness_is_everything_after_labelled():
    assert cma.CLASS_PRIORITY[0] == "LABELLED"
    assert set(cma.BLINDNESS_CLASSES) == set(cma.CLASS_PRIORITY[1:])


# ---------------------------------------------------------------- token hits
def test_token_hits_uses_accepted_normalisation():
    hits = cma.token_hits("Art. 257d OR — RECHTSMISSBRAUCH prüft das Gericht", ["257d", "rechtsmissbrauch"])
    assert sorted(hits) == ["257d", "rechtsmissbrauch"]


def test_surface_text_joins_lists_and_scalars():
    row = {"title": "T", "statutes": ["Art. 102 StGB", "Art. 337 OR"], "regeste": None}
    txt = cma.surface_text(row, cma.EXTENDED_SURFACE_FIELDS)
    assert "Art. 102 StGB" in txt and "Art. 337 OR" in txt and "T" in txt


# ---------------------------------------------------------------- pool assembly
def test_assemble_pool_is_deterministic_and_dedups_by_core():
    spec = {
        "questions": [{"slug": "q", "queries": {"baseline": {"de": "x"}, "counter": {"de": "y"}},
                       "norm_tokens": ["n"], "limitation_tokens": ["l"]}],
        "id_match_rules": {"min_core_length": 6},
    }
    row_a = {"decision_id": "bge_1", "relevance_score": 0.5, "title": "A"}
    row_a2 = {"decision_id": "bge_1", "relevance_score": 0.9, "title": "A2"}
    row_b = {"decision_id": "bge_2", "relevance_score": 0.7, "title": "B"}

    def env(query):
        return {"url": f"https://x/?query={query}",
                "body": json.dumps({"results": [row_a, row_b] if query == "x" else [row_a2]})}

    index = {("q", "baseline", "de"): env("x"), ("q", "counter", "de"): env("y")}
    rows = cma.assemble_pool("q", index, spec)
    cores = [r["decision_id"] for r in rows]
    assert len(cores) == len(set(cores)) == 2
    # relevance desc
    assert rows[0]["decision_id"] == "bge_2"
    # first-wins: baseline row kept for the duplicate core
    kept = next(r for r in rows if r["decision_id"] == "bge_1")
    assert kept["_channel"] == "baseline" and kept["title"] == "A"


# ---------------------------------------------------------------- pins & vacuous path
def test_frozen_pins_match_the_committed_constants():
    assert cma.FROZEN_SPEC_SHA256 == "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
    assert cma.ACCEPTED_RECORD_SHA256 == \
        "5fd695aa243e9f47858e05fe2e1b3875cf9f6b7baa484802047539839c941708"


def test_main_is_vacuous_on_spec_pin_drift():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        bad_spec = tmp_path / "spec.json"
        bad_spec.write_text(json.dumps({"drifted": True}), encoding="utf-8")
        out = tmp_path / "out.json"
        rc = cma.main(["--spec", str(bad_spec), "--out", str(out), "--run-id", "test"])
        assert rc == cma.EXIT_VACUOUS
        rec = json.loads(out.read_text(encoding="utf-8"))
        assert rec["verdict"] == "NOT_MEASURED_VACUOUS"
        assert rec["controls"]["C1_spec_pin"]["holds"] is False


# ---------------------------------------------------------------- integration (read-only cache)
def test_parity_pool_sizes_and_marker_counts_reproduce_accepted_record():
    """C3 parity recomputed from the committed cache: must equal the accepted
    record's producer_meta and counter_authority_yield per question."""
    spec = _spec()
    index = index_cache(read_cache(CACHE), spec)
    accepted = json.loads(ACCEPTED.read_text(encoding="utf-8"))
    acc_yield = accepted["counter_authority_yield"]["per_question"]
    acc_meta = {q["slug"]: q["producer_meta"] for q in accepted["questions"]}
    for q in spec["questions"]:
        slug = q["slug"]
        rows = cma.assemble_pool(slug, index, spec)
        assert len(rows) == acc_meta[slug]["n_decisions"], slug
        n_labelled = sum(
            1 for r in rows
            if cma.marker_label(r, list(q["queries"]["norm_tokens"]),
                                list(q["queries"]["limitation_tokens"]))[0])
        assert n_labelled == acc_yield[slug], slug


def test_zero_yield_questions_stay_the_accepted_two():
    spec = _spec()
    index = index_cache(read_cache(CACHE), spec)
    zero = []
    for q in spec["questions"]:
        rows = cma.assemble_pool(q["slug"], index, spec)
        if not any(cma.marker_label(r, list(q["queries"]["norm_tokens"]),
                                    list(q["queries"]["limitation_tokens"]))[0] for r in rows):
            zero.append(q["slug"])
    assert zero == ["corporate-criminal-liability", "business-judgment-rule"]


def test_full_run_on_committed_cache_is_deterministic_and_offline():
    """Full instrument run into a tmp path: exit in {0,1}; controls all hold;
    zero network. Two runs produce identical per_question payloads."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        out1 = tmp_path / "r1.json"
        out2 = tmp_path / "r2.json"
        rc1 = cma.main(["--out", str(out1), "--run-id", "test"])
        rc2 = cma.main(["--out", str(out2), "--run-id", "test"])
        assert rc1 in (cma.EXIT_NO_BLINDSPOT, cma.EXIT_BLINDSPOT_ATTRIBUTED)
        assert rc1 == rc2
        r1 = json.loads(out1.read_text(encoding="utf-8"))
        r2 = json.loads(out2.read_text(encoding="utf-8"))
        assert r1["per_question"] == r2["per_question"]
        assert r1["network_calls"] == 0
        assert r1["drift"] == {}
        assert r1["controls"]["C1_spec_pin"]["holds"] is True
        assert r1["controls"]["C2_cache_parity"]["holds"] is True
        assert r1["controls"]["C3_accepted_record_parity"]["holds"] is True
        assert r1["controls"]["C4_bundle_agreement"]["holds"] is True
        assert r1["controls"]["C5_planted_detection"]["holds"] is True
        assert r1["controls"]["C6_known_counter_sets_nonempty"]["holds"] is True


def test_no_new_threshold_constant_in_instrument_source():
    src = (REPO / "evaluation/counter_marker_attribution.py").read_text(encoding="utf-8")
    for banned in ("MIN_RECALL", "RECALL_THRESHOLD", "SUPPORT_THRESHOLD",
                   "PASS_AT", "SCORE_CUTOFF", "MIN_SUPPORT"):
        assert banned not in src, banned


def test_extended_surface_never_labels_a_row():
    """The extended surface feeds only axis states; LABELLED requires both
    tokens ON the marker surface (title+regeste+snippet)."""
    row = {"title": "normtoken appears", "regeste": "", "snippet": "",
           "rule_statement": "limtoken appears only here"}
    # norm is ON_MARKER; limitation is EXTENDED_ONLY -> LIMITATION_SURFACE_MISS,
    # i.e. the extended surface SAW the limitation token but never labelled.
    assert cma.attribute_row(row, ["normtoken"], ["limtoken"])["class"] == "LIMITATION_SURFACE_MISS"
    row2 = {"title": "normtoken and limtoken", "regeste": "", "snippet": "",
            "rule_statement": "ignored"}
    assert cma.attribute_row(row2, ["normtoken"], ["limtoken"])["class"] == "LABELLED"
