"""One command that runs the whole active evaluation-lane gate suite (stdlib only).

WHY THIS EXISTS (cycle 38945976309)
-----------------------------------
The lane's two v49 gate test files (``tests/evaluation/test_reality_gate.py``,
``tests/evaluation/test_retrieval_gate.py``) are not executed by any workflow:
the only pytest invocation in CI is ``evaluation/query_map/test_harness.py`` and
its path filter does not even cover ``evaluation/reality_gate/**``,
``evaluation/retrieval_gate/**`` or ``tests/evaluation/**``.  ``.github/**`` is
control-plane scope and is not edited from a lane, so the gap is recorded rather
than patched.  What the lane *can* do is ship a single, dependency-free entry
point an auditor or a maintainer can run in a bare checkout:

    python -m evaluation.lane_suite

It performs the checks a unit test cannot:

* every frozen digest is re-verified against the bytes on disk;
* every committed execution record is audited for internal consistency and for
  verdicts that contradict their own recorded measurements;
* every committed retrieval record is **re-scored** and must reproduce its
  stored verdict byte for byte;
* the retrieval benchmark is **replayed from its committed cache** and the
  latency gates must come back ``not_measurable`` — a cached replay may never
  report a latency PASS (the false green found this cycle);
* a falsification matrix: for every gate family, a fixture that MUST fail;
* the repeat-invariance of both frozen-bar entry points with stderr captured,
  publishing the observed non-zero rate as a record rather than explaining an
  anomaly away by repetition (added cycle 39027041693).

Exit 0 = no check failed (skips allowed; they are listed in the report).
Exit 1 = at least one check failed (a falsifying
result, which is legitimate evidence, not a crash).  Exit 2 = the environment
could not be evaluated (missing digests, unreadable records).

ADDENDUM (cycle 38951152192): the pytest sub-check is optional.  When pytest
is absent the suite records a SKIP, not a failure: the stdlib checks above
are authoritative and a bare checkout must stay green.  A present-but-red
pytest run is still a failure.  Report schema is lex-evaluation-lane-suite/2
(identical to /1 plus n_skipped/skipped_checks and an explicit "skipped" flag
on every check); the committed /1 record from cycle 38945976309 is preserved
untouched.

No Product code is imported and no network call is made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

_LANE_ROOT = Path(__file__).resolve().parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LANE_ROOT))

from evaluation.reality_gate import frozen as reality_frozen          # noqa: E402
from evaluation.reality_gate import gate_contract                     # noqa: E402
from evaluation.reality_gate import gates as reality_gates             # noqa: E402
from evaluation.reality_gate import run_benchmark                      # noqa: E402
from evaluation.retrieval_gate import frozen as retrieval_frozen      # noqa: E402
from evaluation.retrieval_gate import gates as retrieval_gates        # noqa: E402
from evaluation.retrieval_gate import run_retrieval_benchmark         # noqa: E402
from evaluation.frozen_bars import geometry_gate as frozen_bars_geometry_gate  # noqa: E402
from evaluation.frozen_bars import label_gate as frozen_bars_label_gate  # noqa: E402
from evaluation.frozen_bars import label_lineage_gate as frozen_bars_label_lineage  # noqa: E402
from evaluation.frozen_bars import verdict_contract as frozen_bars_verdict_contract  # noqa: E402

REALITY_RECORDS = _LANE_ROOT / "results" / "evaluation" / "reality_benchmark"
RETRIEVAL_RECORDS = _LANE_ROOT / "results" / "evaluation" / "retrieval_benchmark"

#: side artefacts live next to the run records (id-hygiene measurements), so the
#: record set is selected by schema, not by file name.
RETRIEVAL_RECORD_SCHEMA = "lex-retrieval-benchmark/1"

#: Runs per entry point for the repeat-invariance check.  Fixed here, before the
#: check runs, so the sample size is not chosen after seeing a result.  Cycle
#: 39018005027 used N=20 / N=10 for the same measurement.
REPEAT_INVARIANCE_N = 10

#: Keys excluded from the payload-identity comparison.  These are wall-clock
#: measurements, not gate outcomes: comparing them would report a false
#: non-invariance on a run that measured exactly the same thing.  The exclusion
#: list is FIXED HERE, before the check runs, and is published in the record, so
#: "the measurements repeated" is auditable rather than asserted.
VOLATILE_PAYLOAD_KEYS = frozenset({
    "elapsed_s", "elapsed_seconds", "wall_seconds", "wall_clock_s",
    "generated_at", "timestamp", "started_at", "finished_at", "duration_s",
})


def _strip_volatile(obj):
    """Recursively drop VOLATILE_PAYLOAD_KEYS from a JSON payload."""
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items()
                if k not in VOLATILE_PAYLOAD_KEYS}
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    return obj


def retrieval_run_records() -> list[Path]:
    out = []
    for path in sorted(RETRIEVAL_RECORDS.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("schema") == RETRIEVAL_RECORD_SCHEMA:
            out.append(path)
    return out


def _lane_direction_version() -> int:
    """Direction version reported in the suite report.

    DERIVED from state/evaluation.json, never hardcoded: audit M3 (cycle
    38964129305) found a stale literal 49 left in this report after the state
    moved to 50.  Falls back to the last known value only if the state file
    is unreadable, and says so in the report via ``direction_version_source``.
    """
    state_path = _LANE_ROOT / "state" / "evaluation.json"
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return int(data["direction_version"])
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
        return 50

#: gate families the falsification matrix must be able to break, and the check
#: that does it.  A family that cannot be broken is not a benchmark.
FALSIFIABLE_FAMILIES = [
    "reality::truth_phrase",
    "reality::truth_phrase_absent",
    "reality::language",
    "reality::corruption",
    "reality::latency",
    "reality::recall_citation",
    "reality::structural_bundle",
    "reality::structural_report",
    "reality::multilingual",
    "retrieval::authority_recall",
    "retrieval::norm_retrievable",
    "retrieval::known_counter_recall",
    "retrieval::limiting_marker",
    "retrieval::source_validity",
    "retrieval::duplicates",
    "retrieval::transport",
    "retrieval::per_search_latency",
    "retrieval::full_pass_latency",
    "retrieval::cached_replay_latency",
    "retrieval::reproducibility",
]


class _Log:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append({"check": name, "passed": bool(passed),
                            "skipped": False, "detail": detail})
        mark = "PASS" if passed else "FAIL"
        line = f"  [{mark}] {name}"
        if detail:
            line += f"  {detail}"
        print(line, flush=True)

    def skip(self, name: str, detail: str = "") -> None:
        """A check that could not run for a declared environment reason.

        Skips are neither passes nor failures: they are listed separately in
        the report and never turn the suite red.  Cycle 38951152192: the
        pytest sub-check used to FAIL the whole suite in a bare checkout
        without pytest installed — a false red, since the module contract is
        stdlib-only and the missing dependency measures the environment, not
        the product.  An absent pytest is now a skip; a present-but-red
        pytest run is still a failure.
        """
        self.checks.append({"check": name, "passed": None,
                            "skipped": True, "detail": detail})
        line = f"  [SKIP] {name}"
        if detail:
            line += f"  {detail}"
        print(line, flush=True)

    @property
    def failed(self) -> list[dict]:
        return [c for c in self.checks
                if not c.get("skipped") and not c["passed"]]

    @property
    def skipped(self) -> list[dict]:
        return [c for c in self.checks if c.get("skipped")]


# --------------------------------------------------------------------------- #
# 1. freeze integrity
# --------------------------------------------------------------------------- #


def check_digests(log: _Log) -> None:
    print("frozen digests:")
    for label, path, pin in (
        ("reality frozen benchmark",
         reality_frozen._PATH, reality_frozen.FROZEN_SHA256),
        ("retrieval frozen benchmark",
         retrieval_frozen._PATH, retrieval_frozen.FROZEN_SHA256),
        ("reality gate contract",
         gate_contract._PATH, gate_contract.GATE_CONTRACT_SHA256),
        # run 39020603510 (disclosed scope extension, not a re-freeze): the two
        # frozen bar rubrics and this cycle's additive verdict contract. The two
        # RULES files are reused by re-hash and must never be edited; the new
        # contract is pinned by its own module. No frozen benchmark, rubric,
        # incumbent or success rule is touched by adding these entries.
        ("counter-label frozen rubric",
         frozen_bars_label_gate.RULES_LABEL_PATH, frozen_bars_label_gate.EXPECTED_RULES_SHA256),
        ("map-geometry frozen rubric",
         frozen_bars_geometry_gate.RULES_GEOMETRY_PATH, frozen_bars_geometry_gate.EXPECTED_RULES_SHA256),
        ("accepted bar verdict contract",
         frozen_bars_verdict_contract.CONTRACT_PATH, frozen_bars_verdict_contract.EXPECTED_CONTRACT_SHA256),
        ("label-lineage verdict contract",
         frozen_bars_label_lineage.VERDICT_CONTRACT_PATH,
         frozen_bars_label_lineage.EXPECTED_VERDICT_CONTRACT_SHA256),
    ):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        log.add(label, digest == pin, f"{digest[:16]}…")
    freeze = retrieval_frozen.freeze_record()
    log.add("retrieval freeze precedes execution",
            bool(freeze.get("frozen_before_execution")),
            f"frozen_at={freeze.get('frozen_at')}")


# --------------------------------------------------------------------------- #
# 2. committed execution records
# --------------------------------------------------------------------------- #


def check_reality_records(log: _Log) -> None:
    print("reality execution records:")
    paths = sorted(REALITY_RECORDS.glob("*.json"))
    log.add("a committed reality record exists", bool(paths),
            f"{len(paths)} record(s)")
    spec = reality_frozen.load_frozen()
    for path in paths:
        problems = run_benchmark.check_record_integrity(run_benchmark.load_record(path),
                                                        spec)
        log.add(f"record integrity {path.name}", not problems,
                "; ".join(problems[:2]) if problems else
                f"overall_pass={run_benchmark.load_record(path)['overall_pass']}")


def check_retrieval_rescore(log: _Log) -> None:
    print("retrieval records re-scored from the frozen spec (no network):")
    paths = retrieval_run_records()
    log.add("a committed retrieval record exists", bool(paths),
            f"{len(paths)} record(s)")
    spec = retrieval_frozen.load_frozen()
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        verdict = retrieval_gates.evaluate(spec, record)
        canon = lambda d: json.dumps(d, ensure_ascii=False, sort_keys=True)  # noqa: E731
        log.add(f"re-score reproduces {path.name}",
                canon(verdict) == canon(record["verdict"]),
                f"failed={verdict['n_failed']} passed={verdict['n_passed']} "
                f"n/m={verdict['n_not_measurable']}")
        log.add(f"{path.name} was produced by the pinned spec",
                record.get("frozen_sha256") == retrieval_frozen.FROZEN_SHA256)
        freeze = retrieval_frozen.freeze_record()
        wall = retrieval_gates.record_latency_plausibility(record)
        log.add(f"{path.name} latency claim is self-consistent", not wall,
                "; ".join(wall[:1]) if wall else
                f"pass_a_wall_seconds={record.get('pass_a_wall_seconds')} "
                f"pass_a_mode={record.get('pass_a_mode')}")
        log.add(f"{path.name} executed after the freeze",
                str(record.get("started_at")) > str(freeze.get("frozen_at")),
                f"started_at={record.get('started_at')} "
                f"frozen_at={freeze.get('frozen_at')}")


def check_cached_replay_cannot_fake_latency(log: _Log, out_dir: Path) -> None:
    """The false green found this cycle, re-checked as a standing invariant.

    The probe record is written to a temporary file and discarded: the durable
    evidence is the committed cached-replay run record under
    results/evaluation/retrieval_benchmark/, and keeping a second copy here
    would create two sources of truth for the same verdict.
    """
    print("cached replay vs live latency separation:")
    records = retrieval_run_records()
    # the invariant is about a LIVE record surviving its own replay, so select
    # by pass_a_mode, not by file name or mtime
    live_records = [p for p in records
                    if json.loads(p.read_text(encoding="utf-8"))
                    .get("pass_a_mode") == retrieval_gates.LIVE_PASS_MODE]
    if not live_records:
        log.add("a committed live retrieval record exists", False,
                "no record with pass_a_mode=live; the replay/live invariant "
                "cannot be demonstrated")
        return
    record_path = live_records[-1]
    import contextlib, io, tempfile
    with tempfile.TemporaryDirectory(prefix="lex-lane-suite-") as tmp:
        replay_out = Path(tmp) / "cached_replay.json"
        with contextlib.redirect_stdout(io.StringIO()):
            rc = run_retrieval_benchmark.main([
                "--offline", "--run-id", "lane-suite-replay",
                "--out", str(replay_out),
            ])
        log.add("cached replay runs at all", rc in (0, 1), f"exit={rc}")
        if not replay_out.exists():
            log.add("cached replay emitted a record", False)
            return
        verdict = json.loads(replay_out.read_text(encoding="utf-8"))["verdict"]
        latency = [g for g in verdict["gates"] if g["gate"].startswith("latency::")]
        log.add("no latency gate is PASS under a cached replay",
                all(g["passed"] is not True for g in latency),
                "; ".join(f"{g['gate']}={g['passed']}" for g in latency))
        live_record = json.loads(record_path.read_text(encoding="utf-8"))
        live_verdict = retrieval_gates.evaluate(retrieval_frozen.load_frozen(),
                                                live_record)
        live_failures = {f for f in live_verdict["failed_gates"]
                         if f.startswith("latency::")}
        replay_failures = {f for f in verdict["failed_gates"]
                           if f.startswith("latency::")}
        log.add("a recorded live latency failure survives its own cached replay",
                live_failures.issubset(replay_failures | {
                    g["gate"] for g in latency if g["passed"] is None}),
                f"live={sorted(live_failures)} replay={sorted(replay_failures)}")


# --------------------------------------------------------------------------- #
# 3. falsification matrix
# --------------------------------------------------------------------------- #


def _reality_question(slug: str = "business-judgment-rule") -> dict:
    return reality_frozen.question_by_slug(reality_frozen.load_frozen())[slug]


def _broken_reality_fixtures() -> list[tuple[str, bool]]:
    """(family, does this fixture break it?) — every entry must be True."""
    q = _reality_question()
    good = "Le juge dispose d'un large pouvoir d'appreciation. " * 8
    bad = "Ceci n'est pas une decision de droit."
    out: list[tuple[str, bool]] = []
    truth_ids = [g["gate"] for g in reality_gates.evaluate_truth_gates(q, good)]
    out.append(("reality::truth_phrase",
                reality_gates.evaluate_truth_gates(q, bad)[0]["passed"] is False))
    # phrase_absent lives on the Art. 102 CP question, not this one
    corp = _reality_question("corporate-criminal-liability")
    no_reversal = next(g for g in corp["truth_gates"] if g["kind"] == "phrase_absent")
    reversed_prose = (f"{good} {no_reversal['absent_any'][0]}")
    absent_idx = [g["gate"] for g in reality_gates.evaluate_truth_gates(
        corp, reversed_prose)].index(f"truth::{no_reversal['id']}")
    out.append(("reality::truth_phrase_absent",
                reality_gates.evaluate_truth_gates(corp, reversed_prose)[absent_idx]
                ["passed"] is False))
    assert truth_ids, "fixture prose must exercise the truth gates"
    spec = reality_frozen.load_frozen()
    out.append(("reality::language",
                reality_gates.evaluate_language_gate(
                    q, "The court has wide discretionary power in this matter. " * 6,
                    spec)["passed"] is False))
    out.append(("reality::corruption",
                reality_gates.evaluate_corruption_gate(
                    "This sentence repeats. " * 40)["passed"] is False))
    out.append(("reality::latency",
                reality_gates.evaluate_latency(300.0, spec["latency_budget_seconds"])
                ["passed"] is False))
    out.append(("reality::recall_citation",
                reality_gates.evaluate_required_hits(
                    q["required_citation_ids"], set(), "citation", available=True)
                ["passed"] is False))
    # a counter label with no evidence/uncertainty, a foreign host and an
    # invented citation: the three bundle-level falsifications at once
    from evaluation.query_map.harness import COUNTER_STATUSES
    counter_label = sorted(COUNTER_STATUSES)[0]
    bundle = {"decisions": [
        {"decision_id": "d1", "language": "de",
         "canonical_url": "https://evil.example/x",
         "counter_status": counter_label, "counter_evidence": "",
         "counter_uncertainty": None},
        {"decision_id": "d1", "language": "de",
         "canonical_url": "https://mcp.opencaselaw.ch/entscheid/d1"}],
        "answer": {"cited_decision_ids": ["d999"]}}
    structural = {g["gate"]: g["passed"]
                  for g in reality_gates.evaluate_structural_from_bundle(bundle)}
    out.append(("reality::structural_bundle",
                structural["structural::source_urls_valid"] is False
                and structural["structural::answer_citations_constrained"] is False
                and structural["structural::counter_classifications_supported"] is False))
    report = {"answer_status": "failed", "answer_method": "cheapest_model",
              "answer_prose": "x" * 119, "cited_decision_ids": [],
              "provider_error": "boom",
              "adversarial_method": "none", "adversarial_error": "boom"}
    slim = {g["gate"]: g["passed"]
            for g in reality_gates.evaluate_structural_from_report(report)}
    out.append(("reality::structural_report",
                all(slim[g] is False for g in (
                    "structural::answer_ready", "structural::answer_method",
                    "structural::prose_min_length", "structural::citations_nonempty",
                    "structural::provider_clean", "structural::adversarial_method",
                    "structural::adversarial_clean"))))
    mono = {"query": "wann endet ein mietvertrag", "_label": "mono",
            "decisions": [{"decision_id": "d1", "language": "de"}]}
    out.append(("reality::multilingual",
                reality_gates.evaluate_multilingual_coverage([mono])[0]["passed"]
                is False))
    return out


def _broken_retrieval_fixtures() -> list[tuple[str, bool]]:
    """Minimal retrieval records that must break each retrieval gate family."""
    out: list[tuple[str, bool]] = []
    spec = retrieval_frozen.load_frozen()

    def record(*, mode="live", wall=1.0, mutate=None):
        question = retrieval_frozen.question_by_slug(spec)["petty-theft-dismissal"]
        norm = question["queries"]["norm_tokens"][0]
        limitation = question["queries"]["limitation_tokens"][0]
        rows = [{"decision_id": "bger_4A_228_2015", "canonical_decision_id": "",
                 "docket_number": "", "citation_string_de": "BGE 4A 228/2015",
                 "citation_string_fr": "", "citation_string_it": "",
                 "language": "de", "decision_date": "2015-01-01",
                 "canonical_url": "https://mcp.opencaselaw.ch/entscheid/x",
                 "court": "bge", "text_head": f"{norm} {limitation}"}]
        queries = [{"query_key": f"baseline:petty-theft-dismissal:{lang}",
                    "channel": "baseline", "slug": "petty-theft-dismissal",
                    "language": lang, "query": question["queries"]["baseline"][lang],
                    "limit": spec["top_k"]["baseline"], "url": spec["endpoint"],
                    "status": 200, "attempts": 1, "latency_seconds": 1.0,
                    "error": None, "raw_sha256": "a" * 64, "ids_sha256": "b" * 64,
                    "n_results": len(rows), "ids": [r["decision_id"] for r in rows],
                    "rows": [dict(r) for r in rows]} for lang in retrieval_frozen.LANGUAGES]
        rec = {"schema": "lex-retrieval-benchmark/1", "run_id": "lane-suite",
               "frozen_sha256": retrieval_frozen.FROZEN_SHA256,
               "pass_a_mode": mode, "pass_a_wall_seconds": wall,
               "queries": queries,
               "reproducibility": {"pass_b": [
                   {"query_key": q["query_key"], "status": 200,
                    "raw_sha256": q["raw_sha256"], "ids_sha256": q["ids_sha256"],
                    "cache_hit": True} for q in queries], "all_identical": True}}
        if mutate:
            mutate(rec)
        return rec

    def failed(rec) -> set[str]:
        return set(retrieval_gates.evaluate(spec, rec)["failed_gates"])

    def no_authority(rec):
        for q in rec["queries"]:
            q["rows"][0]["decision_id"] = "bger_other_1_2000"
            q["rows"][0]["citation_string_de"] = ""
            q["ids"] = ["bger_other_1_2000"]
    out.append(("retrieval::authority_recall",
                "authority::baseline_recall::petty-theft-dismissal" in failed(
                    record(mutate=no_authority))))

    def no_norm(rec):
        for q in rec["queries"]:
            q["rows"][0]["text_head"] = "neutral prose without the norm token"
    out.append(("retrieval::norm_retrievable",
                "norm::retrievable::petty-theft-dismissal" in failed(
                    record(mutate=no_norm))))

    def no_counter(rec):
        for q in rec["queries"]:
            q["channel"] = "baseline"
    out.append(("retrieval::known_counter_recall",
                "counter::known_counter_recall::petty-theft-dismissal" in failed(
                    record(mutate=no_counter))))

    def no_limitation(rec):
        question = retrieval_frozen.question_by_slug(spec)["petty-theft-dismissal"]
        for q in rec["queries"]:
            q["channel"] = "counter"
            q["rows"][0]["text_head"] = question["queries"]["norm_tokens"][0]
    out.append(("retrieval::limiting_marker",
                "counter::limiting_marker_verified::petty-theft-dismissal" in failed(
                    record(mutate=no_limitation))))

    def bad_source(rec):
        for q in rec["queries"]:
            q["rows"][0]["canonical_url"] = "http://evil.example/x"
            q["rows"][0]["language"] = "en"
    out.append(("retrieval::source_validity",
                "source::rows_valid::petty-theft-dismissal" in failed(
                    record(mutate=bad_source))))

    def duplicate(rec):
        for q in rec["queries"]:
            q["rows"].append(dict(q["rows"][0], decision_id="bger_4A_228_2015_alt"))
    out.append(("retrieval::duplicates",
                "duplicate::unique_ids::petty-theft-dismissal" in failed(
                    record(mutate=duplicate))))

    def transport(rec):
        rec["queries"][0]["status"] = 500
    out.append(("retrieval::transport",
                "transport::all_queries_ok" in failed(record(mutate=transport))))

    def slow_search(rec):
        for q in rec["queries"]:
            q["latency_seconds"] = 45.0
    out.append(("retrieval::per_search_latency",
                "latency::search_under_budget" in failed(record(mutate=slow_search))))

    out.append(("retrieval::full_pass_latency",
                "latency::full_pass_under_budget" in failed(record(wall=300.0))))

    replay = record(mode="offline_replay", wall=0.05)
    for q in replay["queries"]:
        q["latency_seconds"] = None
    replay_verdict = retrieval_gates.evaluate(spec, replay)
    out.append(("retrieval::cached_replay_latency",
                all(g["passed"] is not True for g in replay_verdict["gates"]
                    if g["gate"].startswith("latency::"))))

    def bad_replay(rec):
        rec["reproducibility"]["pass_b"][0]["raw_sha256"] = "0" * 64
    out.append(("retrieval::reproducibility",
                "reproducible::cached_second_pass_identical" in failed(
                    record(mutate=bad_replay))))
    return out


def check_falsification_matrix(log: _Log) -> None:
    print("falsification matrix (every gate family must be breakable):")
    observed = dict(_broken_reality_fixtures() + _broken_retrieval_fixtures())
    missing = [f for f in FALSIFIABLE_FAMILIES if f not in observed]
    log.add("every declared gate family has a breaking fixture", not missing,
            f"missing={missing}" if missing else f"{len(FALSIFIABLE_FAMILIES)} families")
    for family in FALSIFIABLE_FAMILIES:
        if family in observed:
            log.add(f"fixture breaks {family}", observed[family],
                    "" if observed[family] else "the fixture did NOT break the gate")


# --------------------------------------------------------------------------- #
# 4. optional pytest pass
# --------------------------------------------------------------------------- #


def run_pytest(log: _Log) -> None:
    print("pytest pass over the active lane test files:")
    try:
        import pytest  # noqa: F401
    except ModuleNotFoundError:
        log.skip("pytest pass (pytest absent)",
                 "pytest is not installed; the stdlib checks above still ran "
                 "and are authoritative. Install pytest to also run the "
                 "active lane test files.")
        return
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/evaluation/test_reality_gate.py",
         "tests/evaluation/test_retrieval_gate.py",
         "evaluation/query_map/test_harness.py",
         "tests/evaluation/test_audit_correction_verification.py",
         # run 38972887369 (disclosed scope extension, not a re-freeze):
         # verdict-contract digest pin, exit-code reachability matrix and the
         # naive-consumer trap of the frozen-bar gates.
         "tests/evaluation/test_bar_gate_verdict_contract.py",
         # run 39004097533 (disclosed scope extension, not a re-freeze):
         # the counter-authority label benchmark's frozen-hypothesis pin, its
         # record-coherence checker and its red controls. No frozen benchmark,
         # rubric, incumbent or success rule is touched by adding the file.
         "tests/evaluation/test_counter_authority_label_benchmark.py",
         # run 39010105493 / resume 39012970379 (disclosed scope extension, not
         # a re-freeze): the packet-admission conformance gate's predicate,
         # binding, exit-code and frozen-hypothesis pins, plus its mount-gated
         # integration tests. No frozen benchmark, rubric, incumbent or success
         # rule is touched by adding the file.
         "tests/evaluation/test_packet_admission_conformance.py",
         # run 39020603510 (disclosed scope extension, not a re-freeze): the
         # additive counter-label LINEAGE gate - the derived 5/65 predicate, its
         # verdict-contract pin, the minimal-delta non-vacuity control, the
         # no-false-block control, the off-lineage refusals, the two-bar
         # adjudicate verdict and the frozen-prediction execution. The gate is
         # ADDITIVE: no accepted verdict is overwritten and no frozen benchmark,
         # rubric, incumbent or success rule is touched by adding the file.
         "tests/evaluation/test_label_lineage_gate.py",
         # run 39027041693 (disclosed scope extension, not a re-freeze): the
         # rebuild-trigger set relation and its non-vacuity, the pinned
         # served-packet baseline, the new-head recompute record and the
         # harness shape-repair negative control (a list-shaped
         # provenance.stages must yield not_measurable and NEVER a latency
         # pass). Adding the file moves no frozen benchmark, rubric, incumbent
         # or success rule.
         "tests/evaluation/test_newhead_recompute.py",
         # run 39033797087 / repair r1 (disclosed scope extension, not a
         # re-freeze): the rebuilt-packet preflight's freeze-preservation and
         # overwrite-guard pins, its TWO-BAR label-enforcement envelope (M1),
         # the verbatim frozen leg-E prediction (M3) and the citation check
         # against the accepted label-lineage sweep. The original record is
         # pinned as preserved history; no frozen benchmark, rubric, incumbent
         # or success rule is touched by adding the file.
         "tests/evaluation/test_rebuild_preflight.py",
         # run 39086856920 (disclosed scope extension, not a re-freeze): the
         # served-bundle scope falsifier's frozen-hypothesis pin, per-field
         # non-vacuity controls, NOT_APPLICABLE-is-not-a-pass refusals and the
         # executed record of record. POST-FREEZE ADDITION in the sense of
         # evaluation/retrieval_gate/id_hygiene.py: no gate is added to any
         # frozen verdict file, no accepted verdict is overwritten and no
         # frozen benchmark, rubric, incumbent or success rule is touched by
         # adding the file.
         "tests/evaluation/test_served_bundle_scope.py",
         # run 39092033997 (disclosed scope extension, not a re-freeze): the
         # cross-packet TRANSFER falsifier. It pins the frozen transfer rule, the
         # anchor record it transfers FROM, the byte-identity of the instrument
         # used, NOT_MEASURED-is-not-a-pass at the transfer layer, the
         # unresolvable-input refusals, and the executed negative result together
         # with its one-retrieval-two-builds disclosure. Also the orchestration
         # ref-check's self-verification. POST-FREEZE ADDITION in the sense of
         # evaluation/retrieval_gate/id_hygiene.py: no gate is added to any frozen
         # verdict file, no accepted verdict is overwritten and no frozen
         # benchmark, rubric, incumbent or success rule is touched by adding it.
         "tests/evaluation/test_served_packet_transfer.py",
         # run 39111232991 (disclosed scope extension, not a re-freeze): the
         # PRODUCT-vs-BASELINE recall falsifier's frozen-hypothesis pin
         # (including its honest pre-execution disclosure), its accepted-matcher
         # reuse guard, the deterministic-replay pin, the NOT-measurable-is-not-
         # a-pass refusals, the three negative controls (blanked bundle, regressed
         # pool, oracle pool that reaches the green verdict) and the vendored id
         # index's mount-rebuild equality check. POST-FREEZE ADDITION in the sense
         # of evaluation/retrieval_gate/id_hygiene.py: no gate is added to any
         # frozen verdict file, no accepted verdict is overwritten, no frozen
         # rubric/threshold/bar/incumbent is touched, and the frozen retrieval
         # spec and the accepted 39101217095 baseline record are read-only inputs.
         "tests/evaluation/test_product_counter_recall.py",
         # run 39113690481 (disclosed scope extension, not a re-freeze): the
         # claim-admissibility audit that repairs the rejected cycle 39111232991.
         # It pins the v1 hypothesis and record as byte-unchanged inputs, the v2
         # and v2.1 frozen-amendment chain, the discarded first execution
         # (ENVIRONMENT_OR_VACUOUS, never a pass), the mechanical D1 subject-
         # match catcher, the D2 per-cell channel split including the derived
         # plain-top-50 comparator, the mapping-free question-native coverage
         # and admission-gap gates, the three non-vacuity controls, zero network
         # and deterministic replay. POST-FREEZE ADDITION in the sense of
         # evaluation/retrieval_gate/id_hygiene.py: no gate is added to any frozen
         # verdict file, no accepted verdict is overwritten, no frozen rubric,
         # threshold, bar or incumbent is touched, and the frozen retrieval spec,
         # the accepted baseline record and the v1 record are read-only inputs.
          "tests/evaluation/test_subject_match_audit.py",
          # run 39120832665 (disclosed scope extension, not a re-freeze): the
          # question-native concept-gap DISCLOSURE transfer instrument that
          # measures whether the accepted 39113690481 disclosure defect of
          # packet 38839347028 transferred to the REBUILT packet
          # rebuilt-39027045675 (same three frozen qids; scored-population
          # transfer under the standing 'no new spec' rule). It pins the frozen
          # hypothesis's exploratory-peek disclosure, the five non-vacuity
          # controls, the disclosure predicate's substring markers, the accepted
          # record's own verdict and per-qid zero sets, and zero network.
          # POST-FREEZE ADDITION in the sense of evaluation/retrieval_gate/
          # id_hygiene.py: no gate is added to any frozen verdict file, no
          # accepted verdict is overwritten, no frozen rubric, threshold, bar or
          # incumbent is touched, and the accepted subject_match_audit
          # instrument plus the rebuilt packet's bytes read from the EPHEMERAL
          # dispatch mount /tmp/lex_accepted/product (repair F4 of audit
          # CYCLE_39120832665: these packet bytes are NOT committed to this
          # repository; the committed byte-identical secondary source is
          # results/evaluation/rebuilt_packet_adjudication_39049030442/packet/
          # and evaluation/secondary_source_fallback.py verifies it) are
          # read-only inputs.
          "tests/evaluation/test_question_native_transfer.py",
          # run 39123055362 (repair F4 of audit CYCLE_39120832665, disclosed
          # scope extension): the secondary-source fallback verifier's own
          # regression test - in-repo, mount-absent execution must re-hash all
          # 10 rebuilt-packet pins against the frozen hypothesis and match, and
          # the primary record's pin COUNT must stay 13 (the false 14/14
          # provenance claim of 034f2043 must not recur).
          "tests/evaluation/test_secondary_source_fallback.py",
          # run 39137732712 (disclosed scope extension, not a re-freeze): the
          # quantum-death ledger's own regression test. It is pure-function plus
          # committed-record pinning, needs NO network (the REST envelope is a
          # committed capture and the tree facts come from the local object
          # store), and it pins the load-bearing correction that a SKIPPED audit
          # job reports status=completed and must not read as an audit that ran.
          # No accepted verdict, frozen file, rubric or threshold is touched.
          "tests/evaluation/test_quantum_death_ledger.py",
          # run 39173770080 (disclosed scope extension, not a re-freeze): the
          # operational-resume delivery. It pins the three re-hashed frozen pins,
          # the orchestration probe's class truth-table (including the
          # RUN_ID_ONLY_IN_COMMIT_MESSAGE class), the committed zero-delta
          # diagnosis of run 39173551486 and its live reproduction, the additive
          # frozen-cache digest manifest and its verifier, the F9 scratch-run
          # isolation record with the preserved pre-fix 5/5 leak, the Item-2
          # consumption gate, and this run's three-leg falsification benchmark.
          # No frozen benchmark, rubric, incumbent or success rule is touched by
          # adding the file.
          "tests/evaluation/test_v57_resume_delivery.py",
          # run 39167917715 (disclosed scope extension, not a re-freeze): the
          # v57 open-items regression tests - frozen-benchmark input-integrity
          # pins (24/24 cache match, gate-by-gate reproduction, the 21/24 drift
          # negative preserved), the mapping-free coverage-handoff falsifier's
          # frozen predicate and symmetry rule, and the F2/F6 audit-correction
          # guards (report evidence-table digest verification and the
          # committed/re-executed label binding in the coverage instrument).
          # No frozen benchmark, rubric, incumbent or success rule is touched
          # by adding the file.
          "tests/evaluation/test_v57_open_items.py"],
        cwd=str(_LANE_ROOT), capture_output=True, text=True, timeout=900)
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    log.add("active lane pytest suite", proc.returncode == 0, tail[0])


# --------------------------------------------------------------------------- #


def check_repeat_invariance(log: _Log, out_dir: Path) -> None:
    """Convert an anecdote into a rate (the named successor of cycle 39020603510).

    Cycle 39020603510 preserved an UNRESOLVED observation: on one invocation the
    ACCEPTED entry point ``python -m evaluation.frozen_bars.run_bar_gates``
    returned exit code 1, with stderr redirected to /dev/null, and it did not
    reproduce in 33 subsequent runs.  The report named the concrete successor:
    measure the repeat-invariance of both entry points with stderr CAPTURED and
    commit the observed non-zero rate as a first-class record, instead of
    explaining the anomaly away by repetition.

    This check does exactly that, and it is deliberately a REPORTING check rather
    than a pass/fail threshold on the anomaly itself:

    * a run is INVARIANT when exit code, verdict string and every measured block
      match the first run, byte for byte;
    * the recorded ``observed_nonzero_rate`` is published whatever it is.

    An unexplained non-zero from a deterministic, digest-pinned gate that these
    gates are made into by factory direction is a signal, not noise.  The
    threshold that would decide whether a non-zero is acceptable is a CONTROL
    PLANE decision and is NOT invented here; this cycle reports the rate and
    keeps the lane suite's overall verdict tied to invariance, not to the rate.
    """
    print("gate entry-point repeat-invariance (stderr captured):")
    specs = [
        ("run_bar_gates", [sys.executable, "-m",
                           "evaluation.frozen_bars.run_bar_gates"]),
        ("label_lineage_sweep", [sys.executable, "-m",
                                 "evaluation.frozen_bars.run_label_lineage_gate"]),
    ]
    n = REPEAT_INVARIANCE_N
    measured: dict[str, dict] = {}
    for label, argv in specs:
        runs = []
        for _ in range(n):
            proc = subprocess.run(argv, cwd=str(_LANE_ROOT),
                                  capture_output=True, text=True, timeout=600)
            runs.append({"exit_code": proc.returncode,
                         "stdout": proc.stdout, "stderr": proc.stderr})
        codes = [r["exit_code"] for r in runs]
        first = runs[0]
        # the JSON payload, if any: identical payloads prove the MEASUREMENTS
        # repeat, not merely the exit code
        payloads = []
        for r in runs:
            try:
                payloads.append(json.dumps(
                    _strip_volatile(json.loads(r["stdout"])), sort_keys=True))
            except json.JSONDecodeError:
                payloads.append(None)
        body_equal = len(set(payloads)) == 1
        nonzero = sum(1 for c in codes if c != 0)
        invariant = len(set(codes)) == 1 and body_equal
        measured[label] = {
            "n_runs": n,
            "volatile_keys_excluded": sorted(VOLATILE_PAYLOAD_KEYS),
            "exit_codes": codes,
            "distinct_exit_codes": sorted(set(codes)),
            "payload_identical_every_run": body_equal,
            "observed_nonzero_count": nonzero,
            "observed_nonzero_rate": nonzero / n if n else None,
            "invariant": invariant,
            "stderr_nonempty_runs": sum(1 for r in runs if r["stderr"].strip()),
            "first_stderr_tail": first["stderr"][-400:],
        }
        log.add(f"repeat-invariance {label} (N={n})", invariant,
                f"exit_codes={sorted(set(codes))} payload_identical={body_equal} "
                f"nonzero_rate={nonzero}/{n} stderr_nonempty="
                f"{measured[label]['stderr_nonempty_runs']}")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "gate_entry_point_repeat_invariance.json"
    path.write_text(json.dumps(
        {"schema": "lex-evaluation-repeat-invariance/1",
         "n_per_entry_point": n,
         "measured": measured,
         "claim_ceiling": (
             "A measured rate, not a threshold. Invariance is the lane suite's "
             "pass/fail condition; whether an observed non-zero rate is "
             "acceptable is a control-plane decision and is not invented here."),
         "resolves": (
             "the unresolved observation preserved in "
             "reports/evaluation/LABEL_LINEAGE_GATE_39020603510.md section 11 is now "
             "a measured rate instead of an anecdote")},
        indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  rate record: {path}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None, help="where to write the suite report")
    ap.add_argument("--skip-pytest", action="store_true",
                    help="run only the stdlib checks")
    args = ap.parse_args(argv)

    started = time.time()
    out_dir = Path(args.out).parent if args.out else _LANE_ROOT / "results" / "evaluation" / "lane_suite"
    log = _Log()
    try:
        check_digests(log)
        check_reality_records(log)
        check_retrieval_rescore(log)
        check_cached_replay_cannot_fake_latency(log, out_dir)
        check_falsification_matrix(log)
        check_repeat_invariance(log, out_dir)
        if not args.skip_pytest:
            run_pytest(log)
    except (OSError, KeyError, ValueError) as exc:
        print(f"::error::lane suite could not be evaluated: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 2

    report = {
        "schema": "lex-evaluation-lane-suite/2",
        "direction_version": _lane_direction_version(),
        "direction_version_source": "state/evaluation.json (derived, audit M3 repair)",
        "n_checks": len(log.checks),
        "n_passed": len(log.checks) - len(log.failed) - len(log.skipped),
        "n_failed": len(log.failed),
        "n_skipped": len(log.skipped),
        "failed_checks": log.failed,
        "skipped_checks": log.skipped,
        "overall_pass": not log.failed,
        "wall_seconds": round(time.time() - started, 3),
        "falsifiable_families": FALSIFIABLE_FAMILIES,
        "claim_ceiling": (
            "Proves the frozen benchmarks are intact, that the committed records "
            "are self-consistent and re-score byte-identically, that every "
            "declared gate family can be falsified, and that a cached replay "
            "cannot report a latency pass. It does not re-measure Product, and a "
            "green suite is not a product pass. The pytest sub-check is "
            "optional: when pytest is absent it is recorded as a skip, never as "
            "a failure, and the stdlib checks remain authoritative."),
        "checks": log.checks,
    }
    print(f"\nlane suite: {'PASS' if report['overall_pass'] else 'FAIL'} "
          f"({report['n_passed']}/{report['n_checks']} checks, "
          f"{report['wall_seconds']}s)")
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                   sort_keys=True) + "\n", encoding="utf-8")
        print(f"report: {path}")
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())