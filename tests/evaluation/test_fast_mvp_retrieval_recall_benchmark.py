"""Contract tests for the FAST-MVP retrieval / counter-authority recall@K benchmark.

Everything here is OFFLINE over committed bytes: no network, no product import,
no TF-IDF fit, no universal-174k benchmark. The tests pin three things the
operational-resume cycle 40153908549 exists to guarantee:

1. the instrument is executable from the committed tree (the UnboundLocalError
   regression that made run 40153096228's record non-reproducible cannot come
   back);
2. the committed run record is internally consistent and publishes BOTH
   verdict readings required by the V1_2 amendment;
3. the F-3B disposition of the run-40152672734 artifact is provable by re-hash.

The full benchmark execution (about 70 s, needs the product mount) is exercised
by running the instrument itself; these tests deliberately do not re-run it, so
the lane suite stays fast.
"""
from __future__ import annotations

import ast
import hashlib
import json
import py_compile
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

INSTRUMENT = _REPO_ROOT / "evaluation/fast_mvp_retrieval_recall_benchmark.py"
HYPOTHESIS = _REPO_ROOT / "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1.json"
AMENDMENT_V11 = _REPO_ROOT / "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_1_AMENDMENT.json"
AMENDMENT_V12 = _REPO_ROOT / "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_2_AMENDMENT.json"
FREEZE = _REPO_ROOT / "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_FREEZE_V1.json"
SPEC = _REPO_ROOT / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"

RES = _REPO_ROOT / "results/evaluation/fast_mvp_retrieval_recall_benchmark"
RUN_ORIGINAL = RES / "40152672734.json"          # restored, measurement of record for that run
RUN_REHOMED = RES / "40153096228.json"           # verbatim re-home of the in-place rewrite
RUN_REHOMED_PROVENANCE = RES / "40153096228_PROVENANCE.json"
RUN_RESUMED = RES / "40153908549.json"           # reproducible measurement of this run

FREEZE_HYP_SHA = "a9fe256cea627c0bbc9ecd8e316f68b00b1911ab4e99bf0c294576b60cafe4f7"
FREEZE_SPEC_SHA = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
RESTORED_SHA = "ef039fbf8475de0a03003eb6c2190ca5e80a32f641ee23621e3061a7c68bbbd2"
REHOMED_SHA = "78f249803b1342a156644953866a90603f96147904fef5d9c29cf7196f623989"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_timing(cells: list[dict]) -> list[dict]:
    return [{k: v for k, v in c.items() if k != "rerank_seconds"} for c in cells]


def test_instrument_compiles_from_committed_tree():
    py_compile.compile(str(INSTRUMENT), doraise=True)


def test_disclosure_helpers_are_defined_before_their_first_use():
    """Regression guard for the UnboundLocalError that killed run 40153096228.

    ``run()`` called ``c3_ok_check`` / ``c4_ok_check`` before the ``def``
    statements, so the committed instrument raised UnboundLocalError at line 689
    and could not re-derive its own committed record.
    """
    tree = ast.parse(INSTRUMENT.read_text(encoding="utf-8"))
    run_fn = next(n for n in tree.body
                  if isinstance(n, ast.FunctionDef) and n.name == "run")
    first_def: dict[str, int] = {}
    calls: dict[str, list[int]] = {"c3_ok_check": [], "c4_ok_check": []}
    for node in ast.walk(run_fn):
        if isinstance(node, ast.FunctionDef) and node.name in calls:
            first_def.setdefault(node.name, node.lineno)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in calls:
                calls[node.func.id].append(node.lineno)
    assert set(first_def) == set(calls), first_def
    for name, lines in calls.items():
        assert lines, f"{name} is never called"
        assert first_def[name] < min(lines), (
            f"{name} defined at line {first_def[name]} but first called at line "
            f"{min(lines)}: the instrument would raise UnboundLocalError")


def test_freeze_pins_and_amendments_are_byte_stable():
    assert _sha(HYPOTHESIS) == FREEZE_HYP_SHA
    assert _sha(SPEC) == FREEZE_SPEC_SHA
    freeze = _record(FREEZE)
    assert freeze["hypothesis_sha256_at_freeze"] == FREEZE_HYP_SHA
    assert freeze["expected_pins_before_execution"]["frozen_spec_sha256"] == FREEZE_SPEC_SHA
    # both amendments must exist and must be the ones the instrument records
    assert AMENDMENT_V11.is_file() and AMENDMENT_V12.is_file()
    v12 = _record(AMENDMENT_V12)
    assert v12["amended_file_sha256"] == FREEZE_HYP_SHA
    assert v12["written_after_a_debugging_execution"] is True
    # the amendment must publish BOTH readings, not silently drop the original one
    assert "verdict_under_original_v1_c7_blocking" in v12["mandatory_publication"]


def test_resumed_record_is_internally_consistent():
    rec = _record(RUN_RESUMED)
    assert rec["run_id"] == "40153908549"
    assert rec["direction_version"] == 68
    assert rec["n_controls"] == len(rec["controls"])
    assert rec["n_controls_passed"] == sum(1 for c in rec["controls"] if c["passed"])
    assert rec["failed_controls"] == []
    by_gate = {c["gate"]: c for c in rec["controls"]}
    # every blocking control passes; the reported-only duplicate leg does not
    for blocking in ("C1_frozen_spec_digest", "C2_cache_raw_sha_rehash",
                     "C5_non_vacuity", "C6_deterministic_rerank",
                     "C7a_source_validity_blocking",
                     "C3_empty_ranking_zeroes_metric",
                     "C4_oracle_ordering_reaches_achievable_ceiling"):
        assert by_gate[blocking]["passed"] is True, blocking
    assert by_gate["C7b_duplicates_reported_only"]["passed"] is False
    assert by_gate["C7b_duplicates_reported_only"]["measured"]["reported_only"] is True
    # exit code and verdict agree
    assert rec["verdict"] == "PRODUCT_FALSIFIED_RECALL_LOSS"
    assert rec["exit_code"] == 1
    # both readings are published (V1_2 mandatory_publication (b))
    orig = rec["verdict_under_original_v1_c7_blocking"]
    assert orig["verdict"] == "NOT_MEASURED_VACUOUS"
    assert orig["exit_code"] == 2
    # freeze pins re-verified inside the record
    assert rec["rehash_before_execution"]["hypothesis_matches_freeze_pin"] is True
    assert rec["rehash_before_execution"]["spec_matches_pin"] is True
    assert rec["rehash_after_execution"]["hypothesis_unchanged"] is True
    assert rec["rehash_after_execution"]["spec_unchanged"] is True
    assert {a["file"] for a in rec["amendments"]} == {
        "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_1_AMENDMENT.json",
        "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_2_AMENDMENT.json"}
    # offline / scope discipline
    assert rec["network_calls"] == 0
    assert rec["deterministic_offline_only"] is True
    assert rec["no_universal_174k_benchmarks"] is True
    assert rec["human_gate_ready"] is False
    claim = rec["claim"]
    assert claim["n_discriminating_cells"] == 10
    assert claim["rule_a_no_cell_loss"] is False
    assert claim["rule_b_aggregate"] is False
    assert claim["rule_c_language"] is False
    assert claim["aggregate"]["all"]["product_hits"] == 15
    assert claim["aggregate"]["all"]["input_hits"] == 17
    assert {c["query_key"] for c in claim["losses_by_cell"]} == {
        "baseline:business-judgment-rule:de", "counter:petty-theft-dismissal:fr"}


def test_claim_side_is_identical_across_all_three_artifacts():
    """The three artifacts differ only in control bookkeeping and timing."""
    original = _record(RUN_ORIGINAL)
    rehomed = _record(RUN_REHOMED)
    resumed = _record(RUN_RESUMED)
    for other in (rehomed, resumed):
        assert other["claim"] == original["claim"]
        assert _strip_timing(other["cells"]) == _strip_timing(original["cells"])
        assert other["frozen_hypothesis_sha256"] == original["frozen_hypothesis_sha256"]
        assert other["frozen_spec_sha256"] == original["frozen_spec_sha256"]
        assert other["amendments"] == original["amendments"]
        # both later records carry the original-rule reading required by V1_2
        assert (other["verdict_under_original_v1_c7_blocking"]["verdict"]
                == "NOT_MEASURED_VACUOUS")
    # The restored record is the run-40152672734 measurement, executed BEFORE the
    # C7 split was implemented in code: it has no original-rule key and keeps the
    # original V1 verdict. The two V1_2 readings carry the amended verdict.
    assert "verdict_under_original_v1_c7_blocking" not in original
    assert original["verdict"] == "NOT_MEASURED_VACUOUS"
    assert rehomed["verdict"] == "PRODUCT_FALSIFIED_RECALL_LOSS"
    assert resumed["verdict"] == "PRODUCT_FALSIFIED_RECALL_LOSS"
    # only the resumed record has self-consistent control counters
    assert original["n_controls"] == len(original["controls"])
    assert resumed["n_controls"] == len(resumed["controls"])
    # and it is precisely the stale counter that the re-homed copy preserves
    assert rehomed["n_controls"] != len(rehomed["controls"])


def test_f3b_disposition_is_provable_by_rehash():
    prov = _record(RUN_REHOMED_PROVENANCE)
    assert _sha(RUN_ORIGINAL) == RESTORED_SHA
    assert _sha(RUN_REHOMED) == REHOMED_SHA
    assert prov["restored_artifact"]["sha256"] == _sha(RUN_ORIGINAL)
    assert prov["restored_artifact"]["pre_rewrite_sha256_recomputed"] == _sha(RUN_ORIGINAL)
    assert prov["restored_artifact"]["overwritten_sha256_before_restoration"] == _sha(RUN_REHOMED)
    assert prov["re_homed_artifact"]["sha256"] == _sha(RUN_REHOMED)
    assert prov["superseding_reproducible_measurement"]["run_id"] == 40153908549
    # nothing was deleted: all three artifacts and the sidecar exist
    for p in (RUN_ORIGINAL, RUN_REHOMED, RUN_REHOMED_PROVENANCE, RUN_RESUMED):
        assert p.is_file(), p


def test_gate_helper_nests_measured_keywords():
    """Documented schema: _gate() puts every keyword under ``measured``."""
    sys.path.insert(0, str(_REPO_ROOT))
    from evaluation.fast_mvp_retrieval_recall_benchmark import _gate  # noqa: E402
    g = _gate("G", True, "detail", reported_only=True, offenders=[1])
    assert set(g) == {"gate", "passed", "detail", "measured"}
    assert g["measured"] == {"reported_only": True, "offenders": [1]}
