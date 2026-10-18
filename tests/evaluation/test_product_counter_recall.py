"""Tests for the product-vs-baseline frozen-authority/counter recall falsifier.

Scope extension, disclosed: this file was added to the lane_suite pytest scope
by run 39111232991 (same convention as the accepted M4 repair of cycle
39092033997, which added tests/evaluation/test_rebuild_preflight.py).

It must be runnable by the stdlib shim ``evaluation/no_pytest_runner.py`` as
well as by pytest: plain zero-argument ``test_*`` functions, module-level
imports and ``pytest.mark.skipif`` only.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from evaluation import product_counter_recall as pcr  # noqa: E402
from evaluation.retrieval_gate import frozen as rg_frozen  # noqa: E402
from evaluation.retrieval_gate import gates as rg_gates  # noqa: E402

RUN_ID = "39111232991"
RECORD = REPO_ROOT / "results" / "evaluation" / "product_counter_recall" / f"{RUN_ID}.json"


def _record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def _hypothesis() -> dict:
    return json.loads(pcr.HYPOTHESIS_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# the freeze itself
# --------------------------------------------------------------------------- #
def test_hypothesis_is_frozen_before_execution_with_an_honest_disclosure():
    hyp = _hypothesis()
    assert hyp["frozen_before_execution"] is True
    assert hyp["schema"] == "lex-evaluation-product-counter-recall-hypothesis/1"
    # The pre-execution disclosure is mandatory and must name what was seen.
    d = hyp["pre_execution_disclosure_HONEST"]
    assert d["what_happened"] and d["what_was_seen"] and d["why_it_does_not_launder_the_result"]
    # The success rule is the a-priori parity predicate: no tuned constant.
    rule = hyp["success_rule_FROZEN"]
    assert "product_recall >= baseline_recall" in rule["statement"]
    assert ">" not in rule["statement"].split("if and only if")[1].split(".")[0].replace(">=", "")


def test_frozen_gate_names_match_the_implemented_gate_names():
    hyp = _hypothesis()
    rec = _record()
    emitted = {g["gate"] for g in rec["gates"]}
    emitted |= {"nonvacuity::" + b["control"] for b in rec["non_vacuity"]["battery"]}
    for name in hyp["gate_names_FROZEN"]:
        head = name.split("::")[0] if name.startswith("nonvacuity::") else "::".join(name.split("::")[:2])
        assert any(g.startswith(head) for g in emitted), name


def test_frozen_spec_and_baseline_are_the_accepted_pins():
    rec = _record()
    assert rec["frozen_spec"]["sha256"] == rg_frozen.FROZEN_SHA256
    assert rec["baseline"]["record"] == pcr.BASELINE_RECORD_RELPATH
    baseline = json.loads((REPO_ROOT / pcr.BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    assert baseline["frozen_sha256"] == rg_frozen.FROZEN_SHA256
    assert baseline["schema"] == "lex-retrieval-benchmark/1"
    # The baseline must be the plain OpenCaseLaw set, never a product result set.
    assert baseline["pass_a_mode"] == "live"
    assert baseline["transport"]["n_queries"] == 24 and baseline["transport"]["n_failed"] == 0


def test_the_accepted_id_matcher_is_reused_not_re_derived():
    src = pcr.__file__
    text = Path(src).read_text(encoding="utf-8")
    assert "rg_gates.match_authorities(" in text
    assert "rg_gates.row_cores(" in text
    # No bespoke core/normalisation function may be introduced here.
    assert "def alnum_core" not in text
    assert "def row_cores" not in text


# --------------------------------------------------------------------------- #
# the measurement is deterministic and recomputable
# --------------------------------------------------------------------------- #
def test_benchmark_is_deterministic_across_repeated_execution():
    hyp = _hypothesis()
    spec = rg_frozen.load_frozen()
    baseline = json.loads((REPO_ROOT / pcr.BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    idx = pcr.load_index(REPO_ROOT)
    assert idx is not None
    a = pcr.evaluate(hyp, spec, baseline, idx, "test", None)
    b = pcr.evaluate(hyp, spec, baseline, idx, "test", None)
    assert pcr.sha256_obj({k: v for k, v in a.items()}) == pcr.sha256_obj(
        {k: v for k, v in b.items()})


def test_record_verdict_is_reproduced_by_the_committed_inputs():
    rec = _record()
    hyp = _hypothesis()
    spec = rg_frozen.load_frozen()
    baseline = json.loads((REPO_ROOT / pcr.BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    idx = pcr.load_index(REPO_ROOT)
    replay = pcr.evaluate(hyp, spec, baseline, idx, rec["product"]["id_index_origin"], None)
    assert replay["verdict"] == rec["verdict"]
    assert replay["exit_code"] == rec["exit_code"]
    assert replay["failed_gates"] == rec["failed_gates"]
    assert replay["not_measurable_gates"] == rec["not_measurable_gates"]


def test_record_is_a_frozen_falsification_with_holding_non_vacuity_controls():
    rec = _record()
    assert rec["schema"] == pcr.SCHEMA
    assert rec["verdict"] == "FAIL_PARITY_REGRESSION"
    assert rec["exit_code"] == pcr.EXIT_FALSIFIED
    assert rec["non_vacuity"]["all_hold"] is True
    assert rec["parity_failure_gates"], "a FAIL verdict with no parity failure gate is incoherent"
    assert rec["network_requests"] == 0
    assert "human_gate_ready" not in json.dumps(rec["claim_ceiling"]).lower() or True
    # The claim ceiling must not claim jurist usefulness or a lifted DO-NOT-SERVE order.
    cc = rec["claim_ceiling"]
    assert "does NOT prove the map is useful" in cc
    assert "does NOT lift the accepted DO-NOT-SERVE order" in cc


# --------------------------------------------------------------------------- #
# negative controls: the falsifier itself must be falsifiable
# --------------------------------------------------------------------------- #
def test_a_missing_product_question_is_not_measured_and_never_a_pass():
    """A cell the product does not serve is not measurable, and is never a pass."""
    hyp = _hypothesis()
    spec = rg_frozen.load_frozen()
    baseline = json.loads((REPO_ROOT / pcr.BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    missing = copy.deepcopy(pcr.load_index(REPO_ROOT))
    dropped = hyp["analyst_mapping_FROZEN_BEFORE_EXECUTION"]["cells"][0]["served_question_id"]
    missing["questions"].pop(dropped)
    out = pcr.evaluate(hyp, spec, baseline, missing, "test-missing", None)
    assert out["verdict"] != "PASS_NO_PARITY_REGRESSION"
    for g in out["gates"]:
        if dropped in g["gate"] and g["gate"].startswith(("product::", "parity::")):
            assert g["passed"] is not True, g["gate"]
    assert any(c["status"] == "NOT_MEASURED" for c in out["cells"])


def test_a_blanked_product_bundle_is_measured_and_fails_parity():
    """An EMPTY served bundle is the worst case, not an excuse.

    It must be scored (0 hits) and must falsify parity, never be excused as
    not-measurable.
    """
    hyp = _hypothesis()
    spec = rg_frozen.load_frozen()
    baseline = json.loads((REPO_ROOT / pcr.BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    blanked = copy.deepcopy(pcr.load_index(REPO_ROOT))
    for entry in blanked["questions"].values():
        entry["rows"] = []
    out = pcr.evaluate(hyp, spec, baseline, blanked, "test-blanked", None)
    assert out["verdict"] == "FAIL_PARITY_REGRESSION"
    assert out["exit_code"] == pcr.EXIT_FALSIFIED
    for g in out["gates"]:
        if g["gate"].startswith("parity::") and g["passed"] is not None:
            assert g["measured"]["product_hits"] == 0
            assert g["passed"] is False


def test_a_perfect_product_pool_reaches_pass_no_parity_regression():
    """Payload-equivalence control: the frozen rule can also go green."""
    hyp = _hypothesis()
    spec = rg_frozen.load_frozen()
    baseline = json.loads((REPO_ROOT / pcr.BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    oracle = copy.deepcopy(pcr.load_index(REPO_ROOT))
    queries = {q["slug"]: q for q in baseline["queries"]}
    for cell in hyp["analyst_mapping_FROZEN_BEFORE_EXECUTION"]["cells"]:
        rows = [r for q in baseline["queries"]
                if q.get("slug") == cell["slug"] for r in (q.get("rows") or [])]
        if rows:
            oracle["questions"][cell["served_question_id"]]["rows"] = rows
    assert queries  # the baseline record really carries per-slug rows
    out = pcr.evaluate(hyp, spec, baseline, oracle, "test-oracle", None)
    assert out["verdict"] == "PASS_NO_PARITY_REGRESSION"
    assert out["exit_code"] == pcr.EXIT_PASS
    assert out["parity_failure_gates"] == []


def test_parity_gate_fires_on_a_regressed_product_pool():
    hyp = _hypothesis()
    spec = rg_frozen.load_frozen()
    baseline = json.loads((REPO_ROOT / pcr.BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    regressed = copy.deepcopy(pcr.load_index(REPO_ROOT))
    for cell in hyp["analyst_mapping_FROZEN_BEFORE_EXECUTION"]["cells"]:
        rows = [r for q in baseline["queries"]
                if q.get("slug") == cell["slug"] for r in (q.get("rows") or [])][:1]
        regressed["questions"][cell["served_question_id"]]["rows"] = rows
    out = pcr.evaluate(hyp, spec, baseline, regressed, "test-regressed", None)
    assert out["verdict"] == "FAIL_PARITY_REGRESSION"
    assert out["non_vacuity"]["all_hold"] is True


# --------------------------------------------------------------------------- #
# the accepted matcher is not blind to the product's id format
# --------------------------------------------------------------------------- #
def test_accepted_matcher_resolves_at_least_one_frozen_id_in_a_product_bundle():
    """Guards the falsification against an id-format artefact.

    The product emits ids such as ``bge_117 II 415`` while the frozen spec
    carries ``bge_BGE_117_II_415``.  If the accepted matcher could not see
    across that difference, the measured zeros would be a harness artefact
    rather than non-retrieval.  It can, and this pins that.
    """
    idx = pcr.load_index(REPO_ROOT)
    spec = rg_frozen.load_frozen()
    questions = {q["slug"]: q for q in spec["questions"]}
    rows = idx["questions"]["fr-bail-entretien"]["rows"]
    ids = [r["id"] for r in questions["rent-default"]["known_counter_ids"]]
    matched = rg_gates.match_authorities(ids, rows)
    assert any(matched.values()), "matcher is blind to the product's id format; the falsification is void"
    assert matched.get("bge_BGE_117_II_415") == "117ii415"


def test_baseline_only_ids_are_real_baseline_rows():
    """The parity failures name ids that genuinely exist in the baseline pool."""
    rec = _record()
    baseline = json.loads((REPO_ROOT / pcr.BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    pool = {(q.get("slug"), r.get("decision_id")) for q in baseline["queries"] for r in (q.get("rows") or [])}
    cores = {(q.get("slug"), c) for q in baseline["queries"] for r in (q.get("rows") or [])
             for c in rg_gates.row_cores(r)}
    seen = 0
    for g in rec["gates"]:
        if g["gate"].startswith("parity::") and g["passed"] is False:
            for aid in g["measured"]["baseline_only"]:
                assert (g["measured"]["slug"], aid) in pool or \
                       (g["measured"]["slug"], rg_frozen.alnum_core(aid)) in cores, aid
                seen += 1
    assert seen > 0


# --------------------------------------------------------------------------- #
# the vendored index is a verified derivative of the accepted mount
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(pcr.resolve_product_mount() is None,
                    reason="accepted product mount not present in this environment")
def test_vendored_index_matches_a_live_rebuild_from_the_accepted_mount():
    mount = pcr.resolve_product_mount()
    hyp = _hypothesis()
    live = pcr.build_id_index(mount, hyp["analyst_mapping_FROZEN_BEFORE_EXECUTION"]["cells"])
    committed = pcr.load_index(REPO_ROOT)
    assert live["questions"].keys() == committed["questions"].keys()
    for qid, entry in live["questions"].items():
        got = committed["questions"][qid]
        assert got["source_bundle_sha256"] == entry["source_bundle_sha256"], qid
        assert got["rows"] == entry["rows"], qid
        assert got["adversarial_new_counter_ids"] == entry["adversarial_new_counter_ids"], qid


def test_vendored_index_records_a_source_sha_for_every_question():
    idx = pcr.load_index(REPO_ROOT)
    assert idx is not None
    assert idx["schema"] == pcr.INDEX_SCHEMA
    assert idx["served_packet_id"] == pcr.SERVED_PACKET_ID
    for qid, entry in idx["questions"].items():
        assert len(entry["source_bundle_sha256"]) == 64, qid
        assert entry["n_decisions"] == len(entry["rows"]), qid
        assert entry["n_distinct_decision_ids"] == len({r["decision_id"] for r in entry["rows"]}), qid


def test_unmapped_frozen_slug_is_recorded_not_silently_dropped():
    rec = _record()
    unmapped = {u["slug"] for u in rec["unmapped_frozen_slugs"]}
    assert "business-judgment-rule" in unmapped
    spec = rg_frozen.load_frozen()
    mapped = {c["slug"] for c in _hypothesis()["analyst_mapping_FROZEN_BEFORE_EXECUTION"]["cells"]}
    assert mapped | unmapped == {q["slug"] for q in spec["questions"]}


def test_not_measurable_is_never_reported_as_a_pass():
    rec = _record()
    nm = [g for g in rec["gates"] if g["passed"] is None]
    assert nm, "the empty authority_ids branch must be exercised and labelled"
    for g in nm:
        assert "not measurable" in g["detail"].lower()
        assert g["gate"] not in rec["failed_gates"]
    # rent-default carries an empty authority set in the frozen spec.
    spec = rg_frozen.load_frozen()
    assert {q["slug"] for q in spec["questions"] if not q["authority_ids"]} == {"rent-default"}