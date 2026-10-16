#!/usr/bin/env python3
"""Frozen tests for the evaluation-lane retrieval/counter-authority benchmark.

They pin the frozen sample (digest + freeze record + pre-execution ordering),
prove every gate CAN fail (a gate that cannot fail is not a benchmark), prove
not-measurable gates are never counted as passes, and prove the verdict is a
pure recomputable function of the run record.  Pure standard library + pytest.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from evaluation.retrieval_gate import (client, frozen, gates, id_hygiene,
                                       run_retrieval_benchmark)

REPO = Path(__file__).resolve().parents[2]
SPEC = frozen.load_frozen()
QUESTIONS = frozen.question_by_slug(SPEC)
RECORDS = REPO / "results" / "evaluation" / "retrieval_benchmark"


# --------------------------------------------------------------------------- #
# freeze discipline
# --------------------------------------------------------------------------- #


def test_frozen_spec_digest_pin():
    raw = frozen._PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == frozen.FROZEN_SHA256


def test_freeze_record_matches_pinned_digest_and_asserts_pre_execution():
    rec = frozen.freeze_record()
    assert rec["frozen_sha256"] == frozen.FROZEN_SHA256
    assert rec["frozen_before_execution"] is True
    assert rec["frozen_at"].endswith("Z")
    assert rec["run_id_at_freeze"] == "38939239917"
    assert "No frozen query text was executed" in rec["pre_freeze_disclosure"]


def test_frozen_question_set_and_budgets_exact():
    assert [q["slug"] for q in SPEC["questions"]] == [
        "rent-default",
        "corporate-criminal-liability",
        "business-judgment-rule",
        "petty-theft-dismissal",
    ]
    assert SPEC["direction_version"] == 49
    assert SPEC["top_k"] == {"baseline": 50, "counter": 30}
    assert SPEC["latency_budgets"]["per_search_seconds"] == 30.0
    assert SPEC["latency_budgets"]["full_pass_seconds"] == 240.0


def test_frozen_queries_carry_fr_de_it_and_tokens():
    for q in SPEC["questions"]:
        for channel in frozen.CHANNELS:
            for lang in frozen.LANGUAGES:
                text = q["queries"][channel][lang]
                assert text.strip(), (q["slug"], channel, lang)
                assert lang in ("fr", "de", "it")
        assert q["queries"]["norm_tokens"], q["slug"]
        assert q["queries"]["limitation_tokens"], q["slug"]


def test_authority_sets_are_reowned_from_the_frozen_reality_benchmark():
    """Parity: authority_ids == citation ∪ retrieval ids of the reality spec."""
    reality = json.loads((REPO / "evaluation" / "reality_gate"
                          / "frozen_benchmark.json").read_text(encoding="utf-8"))
    by_slug = {qq["slug"]: sorted({*(qq.get("required_citation_ids") or []),
                                   *(qq.get("required_retrieval_ids") or [])})
               for qq in reality["questions"]}
    for q in SPEC["questions"]:
        assert sorted(q["authority_ids"]) == by_slug[q["slug"]], q["slug"]
    assert QUESTIONS["business-judgment-rule"]["authority_ids"] == sorted([
        "bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013",
        "bger_4A_603_2014", "bger_4A_62_2024"])
    assert QUESTIONS["rent-default"]["authority_ids"] == []


def test_known_counter_ids_carry_provenance():
    n = 0
    for q in SPEC["questions"]:
        for row in q["known_counter_ids"]:
            assert set(row) >= {"id", "counter_status", "source_file", "snippet"}
            assert row["counter_status"] in ("limiting", "contrary_or_exception",
                                             "candidate-limiting", "candidate-contrary")
            n += 1
    assert n >= 20
    assert "label soundness" in SPEC["questions"][0]["known_counter_provenance"]


def test_builder_refuses_to_overwrite_the_frozen_spec():
    from evaluation.retrieval_gate import build_frozen_spec
    assert build_frozen_spec.main([]) == 2


# --------------------------------------------------------------------------- #
# id aliasing + normalization
# --------------------------------------------------------------------------- #


def test_alnum_core_maps_legacy_bge_ids_to_atf_and_citation_forms():
    frozen_core = frozen.alnum_core("bger_4A_219_2015")
    assert frozen_core == frozen.alnum_core("bge_4A 219/2015")
    assert frozen_core == frozen.alnum_core("BGE 4A 219/2015")
    assert frozen_core == "4a2192015"
    assert frozen.alnum_core("bge_BGE_142_IV_333") == frozen.alnum_core("BGE 142 IV 333")
    assert frozen.alnum_core("bge_BGE_142_IV_333") == frozen.alnum_core("bge_BGE 142 IV 333")
    assert frozen.alnum_core("bger_4A_219_2015") != frozen.alnum_core("bger_4A_259_2016")


def test_normalize_text_strips_search_markup_and_diacritics():
    assert "art. 257d co" in frozen.normalize_text("<mark>Art. 257d</mark> CO")
    assert frozen.normalize_text("Résiliation") == "resiliation"
    assert frozen.normalize_text("Kündigung") == "kundigung"


def test_row_cores_ignores_bare_shared_docket_without_court():
    a = gates.row_cores({"decision_id": "x_1", "court": "zh_obergericht",
                         "docket_number": "2010/25"})
    b = gates.row_cores({"decision_id": "y_2", "court": "lu_gerichte",
                         "docket_number": "2010/25"})
    assert not (a & b)


# --------------------------------------------------------------------------- #
# fixture records: one all-green, then one falsification per gate
# --------------------------------------------------------------------------- #


def _ids_sha(ids: list[str]) -> str:
    return hashlib.sha256(json.dumps(ids, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _row(decision_id: str, *, lang: str, text: str, court: str = "bge",
         docket: str = "", url: str | None = None) -> dict:
    return {
        "decision_id": decision_id,
        "canonical_decision_id": decision_id,
        "docket_number": docket,
        "citation_string_de": "",
        "citation_string_fr": "",
        "citation_string_it": "",
        "language": lang,
        "decision_date": "2015-01-01",
        "canonical_url": url or f"https://mcp.opencaselaw.ch/entscheid/{decision_id}",
        "court": court,
        "relevance_score": 1.0,
        "text_head": text[:600],
    }


#: per-slug rows that satisfy every measurable gate of the positive fixture
AUTH_ROWS = {
    "corporate-criminal-liability": ["bge_BGE 142 IV 333", "bger 6B 124/2016"],
    "business-judgment-rule": ["bge_4A 219/2015", "bge_4A 259/2016",
                               "bge_4A 626/2013", "bge_4A 603/2014", "bge_4A 62/2024"],
    "petty-theft-dismissal": ["bge_4A 228/2015", "bge_4A 177/2017"],
    "rent-default": [],
}
COUNTER_ROWS = {
    "rent-default": ["bge_BGE 117 II 415"],
    "corporate-criminal-liability": ["bger 6B 7/2014"],
    "business-judgment-rule": ["bge_BGE 139 III 24"],
    "petty-theft-dismissal": ["bge_BGE 124 III 25"],
}


def make_record(spec: dict, *, wall: float = 50.0) -> dict:
    """A record in which every measurable gate passes."""
    questions = frozen.question_by_slug(spec)
    queries = []
    for slug in frozen.SLUG_ORDER:
        question = questions[slug]
        norm = question["queries"]["norm_tokens"][0]
        limitation = question["queries"]["limitation_tokens"][0]
        for channel in frozen.CHANNELS:
            for lang in frozen.LANGUAGES:
                rows = []
                if channel == "baseline" and AUTH_ROWS[slug]:
                    rows = [_row(did, lang=lang,
                                 text=f"{norm} arrêt Urteil {did}")
                            for did in AUTH_ROWS[slug]]
                elif channel == "counter":
                    rows = [
                        _row(COUNTER_ROWS[slug][0], lang=lang,
                             text=f"{norm} {limitation} Ausnahme eccezione exception "
                                  f"{COUNTER_ROWS[slug][0]}"),
                    ]
                    if not AUTH_ROWS[slug]:
                        rows.append(_row("bge_BGE 119 II 147", lang=lang,
                                         text=f"{norm} reservation {limitation}"))
                if not rows:
                    rows = [_row(f"filler_{slug}_{lang}_{channel}", lang=lang,
                                 text=f"{norm} neutral context text",
                                 court="zh_gerichte",
                                 docket=f"{slug[:4].upper()}/{lang}/{channel}")]
                queries.append({
                    "query_key": f"{channel}:{slug}:{lang}",
                    "channel": channel, "slug": slug, "language": lang,
                    "query": question["queries"][channel][lang],
                    "limit": spec["top_k"][channel],
                    "url": spec["endpoint"] + "?query=fixture",
                    "status": 200, "attempts": 1, "latency_seconds": 1.0,
                    "error": None,
                    "raw_sha256": hashlib.sha256(
                        json.dumps(rows, sort_keys=True).encode()).hexdigest(),
                    "ids_sha256": _ids_sha([r["decision_id"] for r in rows]),
                    "n_results": len(rows),
                    "ids": [r["decision_id"] for r in rows],
                    "rows": rows,
                })
    replay = [{"query_key": q["query_key"], "status": 200,
               "raw_sha256": q["raw_sha256"], "ids_sha256": q["ids_sha256"],
               "cache_hit": True} for q in queries]
    return {
        "schema": "lex-retrieval-benchmark/1",
        "run_id": "fixture",
        "frozen_sha256": frozen.FROZEN_SHA256,
        "started_at": "2026-10-16T17:40:00Z",
        "pass_a_mode": gates.LIVE_PASS_MODE,
        "pass_a_wall_seconds": wall,
        "pass_b_wall_seconds": 1.0,
        "transport": {"n_queries": len(queries),
                      "n_ok": sum(1 for q in queries if q["status"] == 200),
                      "n_failed": sum(1 for q in queries if q["status"] != 200),
                      "failures": []},
        "queries": queries,
        "reproducibility": {"pass_b": replay, "all_identical": True},
    }


def _failed(record: dict) -> set[str]:
    return set(gates.evaluate(SPEC, record)["failed_gates"])


def test_positive_fixture_passes_every_measurable_gate():
    verdict = gates.evaluate(SPEC, make_record(SPEC))
    assert verdict["overall_pass"] is True, verdict["failed_gates"]
    assert verdict["n_failed"] == 0
    # rent-default has no frozen controlling-authority set: never a pass
    rent_auth = [g for g in verdict["gates"]
                 if g["gate"].startswith("authority::") and "rent-default" in g["gate"]]
    assert rent_auth and all(g["passed"] is None for g in rent_auth)
    assert verdict["n_not_measurable"] == 4


def test_gate_authority_recall_can_fail():
    rec = make_record(SPEC)
    for q in rec["queries"]:
        if q["slug"] == "business-judgment-rule" and q["channel"] == "baseline":
            q["rows"] = [_row("filler_bjr", lang=q["language"], text="business judgment rule",
                              court="zh_gerichte", docket=f"X/{q['language']}")]
            q["ids"] = ["filler_bjr"]
    failed = _failed(rec)
    assert "authority::baseline_recall::business-judgment-rule" in failed
    for lang in frozen.LANGUAGES:
        assert f"authority::baseline_lang_recall::business-judgment-rule::{lang}" in failed


def test_gate_norm_retrievable_can_fail():
    rec = make_record(SPEC)
    for q in rec["queries"]:
        if q["slug"] == "petty-theft-dismissal":
            for row in q["rows"]:
                row["text_head"] = "unrelated prose without the governing norm"
    assert "norm::retrievable::petty-theft-dismissal" in _failed(rec)


def test_gate_known_counter_recall_can_fail():
    rec = make_record(SPEC)
    for q in rec["queries"]:
        if q["slug"] == "corporate-criminal-liability":
            q["rows"] = [r for r in q["rows"]
                         if frozen.alnum_core(r["decision_id"])
                         != frozen.alnum_core("bger 6B 7/2014")]
            q["ids"] = [r["decision_id"] for r in q["rows"]]
            q["ids_sha256"] = _ids_sha(q["ids"])
    assert "counter::known_counter_recall::corporate-criminal-liability" in _failed(rec)


def test_gate_limiting_marker_can_fail_without_limitation_token():
    rec = make_record(SPEC)
    for q in rec["queries"]:
        if q["slug"] == "rent-default" and q["channel"] == "counter":
            for row in q["rows"]:
                row["text_head"] = "257d Mietvertrag Kündigung wegen Zahlungsverzug"
    assert "counter::limiting_marker_verified::rent-default" in _failed(rec)


def test_gate_source_validity_can_fail_on_bad_url_and_language():
    rec = make_record(SPEC)
    rec["queries"][0]["rows"][0]["canonical_url"] = "http://evil.example/entscheid"
    rec["queries"][1]["rows"][0]["language"] = "en"
    assert "source::rows_valid::rent-default" in _failed(rec)


def test_gate_duplicate_suppression_can_fail():
    rec = make_record(SPEC)
    q = next(q for q in rec["queries"] if q["channel"] == "counter")
    base = q["rows"][0]
    twin = copy.deepcopy(base)
    twin["decision_id"] = base["decision_id"].replace("bge_", "bger_").replace(" ", "_")
    q["rows"].append(twin)
    slug = q["slug"]
    assert f"duplicate::unique_ids::{slug}" in _failed(rec)


def test_gate_transport_can_fail():
    rec = make_record(SPEC)
    q = rec["queries"][5]
    q["status"], q["error"], q["rows"], q["ids"] = 500, "HTTP 500", [], []
    assert "transport::all_queries_ok" in _failed(rec)


def test_gate_per_search_latency_can_fail():
    rec = make_record(SPEC)
    rec["queries"][0]["latency_seconds"] = 45.0
    assert "latency::search_under_budget" in _failed(rec)


def test_gate_full_pass_latency_can_fail():
    rec = make_record(SPEC, wall=300.0)
    assert "latency::full_pass_under_budget" in _failed(rec)


# --------------------------------------------------------------------------- #
# replay/live separation (cycle 38945976309)
#
# A cached replay legitimately re-measures CONTENT (same raw bytes) but it does
# not measure wall-clock time.  Before this guard a plain ``--offline`` re-run of
# the SAME committed data turned the recorded falsifying failure
# ``latency::full_pass_under_budget`` (256.827s >= 240s) into a PASS, because
# ``pass_a_wall_seconds`` then held the cache-read wall time (~0.07s) and no gate
# looked at ``pass_a_mode``.  These tests pin the closed hole.
# --------------------------------------------------------------------------- #


def test_cached_replay_cannot_report_a_latency_pass():
    rec = make_record(SPEC, wall=0.07)
    rec["pass_a_mode"] = "offline_replay"
    for q in rec["queries"]:           # replayed rows carry no latency at all
        q["from_cache"] = True
        q["latency_seconds"] = None
    verdict = gates.evaluate(SPEC, rec)
    for gate in ("latency::search_under_budget", "latency::full_pass_under_budget"):
        assert gate in verdict["not_measurable_gates"], verdict
        assert gate not in verdict["failed_gates"]
        assert gate not in [g["gate"] for g in verdict["gates"] if g["passed"] is True]
        reason = verdict["not_measurable_reasons"][gate]
        assert "pass_a_mode" in reason and "live" in reason, reason


def test_cached_replay_does_not_hide_a_recorded_latency_failure():
    """The exact regression: replay of a slow live pass must not read green."""
    slow = make_record(SPEC, wall=256.827)
    live_verdict = gates.evaluate(SPEC, slow)
    assert "latency::full_pass_under_budget" in live_verdict["failed_gates"]

    replay = copy.deepcopy(slow)
    replay["pass_a_mode"] = "offline_replay"
    replay["pass_a_wall_seconds"] = 0.07
    replay_verdict = gates.evaluate(SPEC, replay)
    assert "latency::full_pass_under_budget" not in replay_verdict["failed_gates"]
    # ...and not a pass either: the verdict becomes not-measurable, never green.
    assert "latency::full_pass_under_budget" in replay_verdict["not_measurable_gates"]


def test_record_without_declared_pass_mode_is_not_measurable_for_latency():
    """Conservative default: an undeclared mode cannot certify a latency verdict."""
    rec = make_record(SPEC, wall=1.0)
    rec.pop("pass_a_mode")
    verdict = gates.evaluate(SPEC, rec)
    assert "latency::full_pass_under_budget" in verdict["not_measurable_gates"]
    assert "latency::full_pass_under_budget" not in verdict["failed_gates"]


def test_content_gates_still_work_from_a_cached_replay():
    """The guard is scoped: replay must NOT invalidate the content gates."""
    rec = make_record(SPEC, wall=0.07)
    rec["pass_a_mode"] = "offline_replay"
    for q in rec["queries"]:
        q["from_cache"] = True
        q["latency_seconds"] = None
    verdict = gates.evaluate(SPEC, rec)
    assert verdict["overall_pass"] is True, verdict["failed_gates"]
    live = gates.evaluate(SPEC, make_record(SPEC, wall=1.0))
    content = lambda v: sorted(g["gate"] for g in v["gates"]  # noqa: E731
                               if g["passed"] is True
                               and not g["gate"].startswith("latency::"))
    # identical content verdicts to the live run: only the two latency gates differ
    assert content(verdict) == content(live)
    assert content(verdict)                                   # not vacuously empty
    assert len(content(verdict)) == live["n_passed"] - 2


def test_gate_cached_reproducibility_can_fail():
    rec = make_record(SPEC)
    rec["reproducibility"]["pass_b"][0]["raw_sha256"] = "0" * 64
    rec["reproducibility"]["all_identical"] = False
    assert "reproducible::cached_second_pass_identical" in _failed(rec)


def test_reproducibility_not_measurable_when_no_replay_recorded():
    rec = make_record(SPEC)
    rec["reproducibility"] = {"pass_b": [], "all_identical": False}
    verdict = gates.evaluate(SPEC, rec)
    assert "reproducible::cached_second_pass_identical" in verdict["not_measurable_gates"]
    assert "reproducible::cached_second_pass_identical" not in verdict["failed_gates"]


def test_verdict_is_pure_and_deterministic():
    rec = make_record(SPEC)
    a = gates.evaluate(SPEC, rec)
    b = gates.evaluate(SPEC, copy.deepcopy(rec))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert gates.verdict_sha256(a) == gates.verdict_sha256(b)


# --------------------------------------------------------------------------- #
# runner behaviour (offline: no network needed)
# --------------------------------------------------------------------------- #


def test_query_plan_is_frozen_and_deterministic():
    plan = run_retrieval_benchmark.build_query_plan(SPEC)
    assert len(plan) == 24  # 4 questions x 3 languages x 2 channels
    assert plan[0]["query_key"] == "baseline:rent-default:fr"
    assert plan[-1]["query_key"] == "counter:petty-theft-dismissal:it"
    keys = [p["query_key"] for p in plan]
    assert len(keys) == len(set(keys))
    for item in plan:
        spec_q = QUESTIONS[item["slug"]]["queries"][item["channel"]][item["language"]]
        assert item["query"] == spec_q


def test_offline_run_with_empty_cache_exits_2_and_writes_no_record(tmp_path):
    """Empty input is an environment error, never a FAIL verdict."""
    out = tmp_path / "record.json"
    rc = run_retrieval_benchmark.main([
        "--offline", "--cache-dir", str(tmp_path / "cache"),
        "--out", str(out), "--run-id", "fixture",
    ])
    assert rc == 2
    assert not out.exists()


def test_rescore_rejects_record_frozen_by_another_spec(tmp_path):
    bad = tmp_path / "record.json"
    bad.write_text(json.dumps({"frozen_sha256": "0" * 64, "queries": []}),
                   encoding="utf-8")
    assert run_retrieval_benchmark.main(["--rescore", str(bad)]) == 3


def test_accepted_record_ordering_freeze_before_execution():
    """If a claim-bearing run record exists, the freeze record must predate it."""
    records = sorted(RECORDS.glob("*.json")) if RECORDS.is_dir() else []
    if not records:
        pytest.skip("no claim-bearing retrieval record in this checkout yet")
    freeze = frozen.freeze_record()
    for path in records:
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec.get("schema") != "lex-retrieval-benchmark/1":
            continue
        assert rec["frozen_sha256"] == frozen.FROZEN_SHA256
        assert rec["started_at"] > freeze["frozen_at"], (
            "execution started before the freeze record was written")


def test_accepted_record_reproduces_its_own_verdict():
    """A recorded verdict is recomputable from the record alone (byte-identical)."""
    records = sorted(RECORDS.glob("*.json")) if RECORDS.is_dir() else []
    checked = 0
    for path in records:
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec.get("schema") != "lex-retrieval-benchmark/1" or "verdict" not in rec:
            continue
        recomputed = gates.evaluate(SPEC, rec)
        assert json.dumps(recomputed, sort_keys=True) == json.dumps(
            rec["verdict"], sort_keys=True), path.name
        checked += 1
    if not checked:
        pytest.skip("no claim-bearing retrieval record in this checkout yet")


def test_extract_rows_drops_markup_and_keeps_id_evidence():
    body = {"results": [{
        "decision_id": "bge_4A 219/2015", "court": "bge",
        "canonical_decision_id": "bge_4A 219/2015", "docket_number": "4A 219/2015",
        "language": "fr", "decision_date": "2015-01-01",
        "canonical_url": "https://mcp.opencaselaw.ch/entscheid/bge_4A%20219/2015",
        "regeste": "Regeste <mark>Business Judgment Rule</mark> information",
        "snippet": "snippet <mark>information</mark> suffisante",
        "title": None, "citation_string_de": "BGE 4A 219/2015",
        "citation_string_fr": "ATF 4A 219/2015", "citation_string_it": "DTF 4A 219/2015",
        "relevance_score": 12.5,
    }]}
    rows = gates.extract_rows(body)
    assert len(rows) == 1
    assert "Business Judgment Rule" in rows[0]["text_head"]
    assert "<mark>" not in rows[0]["text_head"]
    matched = gates.match_authorities(["bger_4A_219_2015"], rows)
    assert matched == {"bger_4A_219_2015": "4a2192015"}


# --------------------------------------------------------------------------- #
# verdict purity across processes (regression for the PYTHONHASHSEED fix)
# --------------------------------------------------------------------------- #


def _claim_record_path() -> Path | None:
    if not RECORDS.is_dir():
        return None
    for path in sorted(RECORDS.glob("*.json")):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if rec.get("schema") == "lex-retrieval-benchmark/1" and "verdict" in rec:
            return path
    return None


def test_verdict_byte_identical_across_hash_seeds():
    """Regression: gate example ordering must not depend on PYTHONHASHSEED.

    An earlier version of gates.py iterated row_cores() sets directly, so
    the duplicate::unique_ids examples list order differed across processes
    (gate outcomes unchanged) and the recorded verdict was not a pure
    function of the record.  Recompute in fresh interpreters with different
    hash seeds and require byte-identical output.
    """
    path = _claim_record_path()
    if path is None:
        pytest.skip("no claim-bearing retrieval record in this checkout yet")
    code = (
        "import json,sys;"
        f"sys.path.insert(0, {str(REPO)!r});"
        "from evaluation.retrieval_gate import frozen, gates;"
        "spec = frozen.load_frozen();"
        f"rec = json.load(open({str(path)!r}, encoding='utf-8'));"
        "sys.stdout.write(json.dumps(gates.evaluate(spec, rec), "
        "ensure_ascii=False, sort_keys=True))"
    )
    outputs = []
    for seed in ("0", "1", "2"):
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = seed
        proc = subprocess.run([sys.executable, "-c", code], env=env,
                              capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stderr[-500:]
        outputs.append(proc.stdout)
    assert outputs[0] == outputs[1] == outputs[2], (
        "verdict differs across hash seeds: example ordering is not deterministic")
    stored = json.loads(path.read_text(encoding="utf-8"))["verdict"]
    assert json.loads(outputs[0]) == stored


def test_verdict_recompute_log_documents_ordering_fix():
    """Any post-hoc verdict recompute on a claim-bearing record must be logged
    and must state that gate outcomes were unchanged."""
    path = _claim_record_path()
    if path is None:
        pytest.skip("no claim-bearing retrieval record in this checkout yet")
    rec = json.loads(path.read_text(encoding="utf-8"))
    log = rec.get("verdict_recompute_log") or []
    assert log, "claim-bearing record must log any post-hoc verdict recompute"
    last = log[-1]
    assert last["gate_outcomes_unchanged"] is True
    assert "ordering only" in " ".join(last["changed_fields"]).lower()
    assert last["old_verdict_sha256"] != last["new_verdict_sha256"]
    assert "PYTHONHASHSEED" in last["reason"]


# --------------------------------------------------------------------------- #
# id hygiene (cycle 38945976309)
#
# A post-freeze measurement, deliberately kept OUT of the frozen verdict: the
# recorded 38939239917 verdict must stay byte-reproducible. It makes the lane
# state's "malformed-id detection" claim true with provenance instead of by
# assertion.
# --------------------------------------------------------------------------- #


def test_id_hygiene_flags_unresolved_placeholders_and_html_fragments():
    assert id_hygiene.id_defects({"decision_id": "ge_gerichte_[pjdoc 15442]"}) \
        == ["unresolved_placeholder_in_id"]
    # recorded verbatim from the run: the id is a slugified HTML fragment and the
    # docket_number it was built from is raw upstream markup
    assert id_hygiene.id_defects(
        {"decision_id": "ch_vb__td_class__metadataCell__150000044__td_",
         "docket_number": '<td class="metadataCell">150000044</td>'}) \
        == ["html_markup_in_docket"]
    assert id_hygiene.id_defects({"decision_id": ""}) == ["empty_id"]
    assert id_hygiene.id_defects({"decision_id": "bger_4A_228_2015",
                                  "docket_number": "4A 228/2015"}) == []


def test_id_hygiene_reproduces_the_recorded_defect_count():
    """Same six unusable ids the previous cycle reported, independently counted."""
    record = json.loads((RECORDS / "38939239917.json").read_text(encoding="utf-8"))
    report = id_hygiene.measure(record)
    assert report["n_distinct_defective_ids"] == 6, report["defective_ids"]
    assert report["defects_by_class"] == {
        "html_markup_in_docket": 1,
        "unresolved_placeholder_in_docket": 5,
        "unresolved_placeholder_in_id": 5,
    }, report["defects_by_class"]
    assert report["n_rows"] == 960
    # ...and the frozen duplicate gate still fails on the same record
    assert all(g["passed"] is False for g in report["frozen_duplicate_gate_status"])


def test_id_hygiene_cli_refuses_a_foreign_record(tmp_path):
    record = json.loads((RECORDS / "38939239917.json").read_text(encoding="utf-8"))
    record["frozen_sha256"] = "0" * 64
    foreign = tmp_path / "foreign.json"
    foreign.write_text(json.dumps(record), encoding="utf-8")
    assert id_hygiene.main(["--record", str(foreign)]) == 2
    assert id_hygiene.main(["--record", str(tmp_path / "absent.json")]) == 2


def test_id_hygiene_cli_refuses_empty_input(tmp_path):
    record = json.loads((RECORDS / "38939239917.json").read_text(encoding="utf-8"))
    record["queries"] = []
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps(record), encoding="utf-8")
    out = tmp_path / "out.json"
    assert id_hygiene.main(["--record", str(empty), "--out", str(out)]) == 2
    assert not out.exists()


def test_id_hygiene_cli_records_the_failure_and_exits_1(tmp_path):
    out = tmp_path / "hygiene.json"
    rc = id_hygiene.main(["--record", str(RECORDS / "38939239917.json"),
                          "--out", str(out)])
    assert rc == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["passed"] is False
    assert "POST-FREEZE" in report["tier"]


def test_record_latency_plausibility_catches_a_hand_edited_wall_time():
    """The mode flag binds what a record DECLARES; this binds what it carries."""
    record = json.loads((RECORDS / "38939239917.json").read_text(encoding="utf-8"))
    assert gates.record_latency_plausibility(record) == []
    forged = copy.deepcopy(record)
    forged["pass_a_wall_seconds"] = 0.067        # replay wall, live declaration
    problems = gates.record_latency_plausibility(forged)
    assert any("shorter than the sum" in p for p in problems), problems


def test_record_latency_plausibility_rejects_a_wall_beyond_the_record_span():
    record = json.loads((RECORDS / "38939239917.json").read_text(encoding="utf-8"))
    forged = copy.deepcopy(record)
    for q in forged["queries"]:                  # drop the per-search evidence
        q["latency_seconds"] = 0.0
    forged["pass_a_wall_seconds"] = 99999.0
    problems = gates.record_latency_plausibility(forged)
    assert any("started_at->generated_at span" in p for p in problems), problems


def test_record_latency_plausibility_is_out_of_scope_for_a_replay_record():
    record = json.loads((RECORDS / "38939239917.json").read_text(encoding="utf-8"))
    replay = copy.deepcopy(record)
    replay["pass_a_mode"] = "offline_replay"
    assert gates.record_latency_plausibility(replay) == []
