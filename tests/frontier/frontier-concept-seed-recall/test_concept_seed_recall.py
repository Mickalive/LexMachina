"""Executable tests for the frontier-concept-seed-recall harness.

Zero network.  Zero model calls.  No writes outside the team namespace.

The team directory name contains a dash, so the modules are loaded by
``importlib`` rather than by an ``import`` statement.

Run with::

    python3 -m pytest tests/frontier/frontier-concept-seed-recall -q
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PKG = "frontier.frontier-concept-seed-recall"
nlcs = importlib.import_module(f"{PKG}.nlcs")
plan = importlib.import_module(f"{PKG}.plan")
replay = importlib.import_module(f"{PKG}.replay")
inputs = importlib.import_module(f"{PKG}.inputs")
harness = importlib.import_module(f"{PKG}.harness")
regression = importlib.import_module(f"{PKG}.regression")
contract = importlib.import_module(f"{PKG}.contract")
freeze_ordering = importlib.import_module(f"{PKG}.freeze_ordering")

TEAM_DIR = REPO_ROOT / "results/frontier/frontier-concept-seed-recall"
RULES = TEAM_DIR / "RULES.json"
MOUNTS_PRESENT = inputs.EVALUATION_MOUNT.is_dir() and inputs.PRODUCT_MOUNT.is_dir()
needs_mount = pytest.mark.skipif(
    not MOUNTS_PRESENT, reason="accepted read-only mounts are not present in this run")


# --------------------------------------------------------------------------- #
# NLCS-1: the frozen variant builder
# --------------------------------------------------------------------------- #
def test_deaccent_matches_the_accepted_audit_rule():
    sma, _, _ = inputs.load_evaluation_modules()
    for text in ("Überwachungspflicht", "Responsabilità del medico",
                 "résiliation du bail", "Kapitalverletzung"):
        assert nlcs.deaccent(text) == sma.deaccent(text)


def test_surface_form_recovers_the_accepted_orthography():
    q = ("Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung: wie weit "
         "geht der aktive Eingriff, und welche Entscheidungen begrenzen ihn gegenüber "
         "einer blossen Überwachungspflicht?")
    assert nlcs.surface_form("uberwachungspflicht", q) == "Überwachungspflicht"
    assert nlcs.surface_form("kapitalverletzung", q) == "Kapitalverletzung"


def test_morphological_rules_are_deterministic_and_known():
    assert nlcs.morph_variants("Überwachungspflicht", "de") == [
        "Überwachungspflicht", "Überwachungspflichten",
        "Ueberwachungspflicht", "Uberwachungspflicht"]
    assert nlcs.morph_variants("Kapitalverletzung", "de") == [
        "Kapitalverletzung", "Kapitalverletzungen"]
    assert nlcs.morph_variants("furto", "it") == ["furto", "furti"]
    assert nlcs.morph_variants("primaire", "fr") == ["primaire", "primaires"]
    assert nlcs.morph_variants("prouvées", "fr") == ["prouvées", "prouvees", "prouvée"]


def test_variant_is_a_sentence_that_still_contains_the_question():
    q = "Welche Pflichten hat der Arbeitgeber?"
    v = nlcs.build_variant(q, "de", "uberwachungspflicht")
    assert v["query"].startswith(q)
    assert "Überwachungspflicht" in v["query"] or v["concept"] in v["query"]
    assert v["query"].rstrip().endswith("?")
    assert v["template_id"] == "NLCS-1"


def test_variant_is_deterministic():
    args = ("Welche Pflichten hat der Arbeitgeber?", "de", "uberwachungspflicht")
    assert nlcs.build_variant(*args) == nlcs.build_variant(*args)


def test_unknown_language_is_refused_rather_than_guessed():
    with pytest.raises(ValueError):
        nlcs.morph_variants("x", "es")


def test_cap_is_a_prefix_of_the_accepted_under_covered_order():
    out = nlcs.build_unit_variants("Q text here about x", "de",
                                   ["alpha", "beta", "gamma"], 2)
    assert [v["concept"] for v in out] == ["alpha", "beta"]


# --------------------------------------------------------------------------- #
# the committed freeze
# --------------------------------------------------------------------------- #
def test_rules_file_is_committed_and_is_the_frozen_plan():
    assert RULES.is_file(), "RULES.json must be committed BEFORE any measurement"
    committed = json.loads(RULES.read_text(encoding="utf-8"))
    assert committed["charter_version"] == 1
    assert committed["template_id"] == "NLCS-1"
    assert committed["n_variants"] == len(
        [v for u in committed["units"] for v in u["variants"]])


def test_every_variant_string_is_declared_before_it_was_queried():
    committed = json.loads(RULES.read_text(encoding="utf-8"))
    for unit in committed["units"]:
        for v in unit["variants"]:
            assert v["query"].startswith(unit["question_text"].rstrip())
            assert v["surface_form"] in unit["question_text"] or v["concept"] == v["surface_form"]


def test_claim_ceiling_is_present_and_binding():
    committed = json.loads(RULES.read_text(encoding="utf-8"))
    ceiling = committed["claim_ceiling"]
    for phrase in ("map helps a jurist", "absent from the corpus", "fail-closed"):
        assert phrase in ceiling


def test_no_vacuity_void_clause_is_explicitly_not_inherited():
    committed = json.loads(RULES.read_text(encoding="utf-8"))
    assert "DOES NOT INHERIT" in committed["thresholds"]["no_vacuity_void_clause"]
    assert "TIE=>VOID" in committed["thresholds"]["no_vacuity_void_clause"]


def test_dedup_is_the_products_own_identity_order():
    rows = [{"decision_id": "a", "canonical_decision_id": "A"},
            {"decision_id": "b", "canonical_decision_id": "A"},
            {"decision_id": "c", "canonical_decision_id": None}]
    out, dd = harness.dedup_rows(rows)
    assert [r["decision_id"] for r in out] == ["a", "c"]
    assert dd["identity_keys"] == ["canonical_decision_id", "decision_id"]
    assert dd["merged_away"] == 1


def test_additive_union_never_drops_an_a0_row():
    a0 = [{"decision_id": f"a{i}", "canonical_decision_id": f"A{i}"} for i in range(5)]
    a1 = [{"decision_id": "a0", "canonical_decision_id": "A0"},
          {"decision_id": "n", "canonical_decision_id": "N"}]
    union, _ = harness.dedup_rows(a0 + a1)
    assert {r["decision_id"] for r in a0} <= {r["decision_id"] for r in union}
    assert len(union) == 6


def test_ids_digest_is_the_accepted_benchmark_digest():
    import hashlib
    rows = [{"decision_id": "x"}, {"decision_id": "y"}]
    expected = hashlib.sha256(
        json.dumps(["x", "y"], ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    assert harness._ids_sha256(rows) == expected


def test_cache_key_derivation_is_byte_identical_to_the_vendored_copy():
    params = {"query": "Kapitalverletzung", "limit": "50", "offset": "0",
              "sort": "relevance", "fields": "full", "include_pinpoint": "false"}
    assert replay._vendored_request_key("/decisions", params) == \
        replay.Searcher(read_only_cache_dirs=[], write_cache_dir=None,
                        allow_live=False).request_key("/decisions", params)


def test_search_params_carry_no_language_filter():
    p = replay.Searcher.search_params("q")
    assert "language" not in p
    assert p["limit"] == "50" and p["offset"] == "0"
    assert p["sort"] == "relevance" and p["fields"] == "full"


def test_offline_searcher_never_hits_the_network():
    s = replay.Searcher(read_only_cache_dirs=[], write_cache_dir=None, allow_live=False)
    rec = s.search("/decisions", s.search_params("nothing cached"), query_key="t")
    assert rec["status"] is None
    assert rec["n_results"] == 0
    assert rec["live_refused"]
    assert s.network_calls == 0


def test_per_search_budget_flag_is_measured_not_assumed():
    s = replay.Searcher(read_only_cache_dirs=[], write_cache_dir=None, allow_live=False,
                        per_search_budget_s=0.0)
    s.calls.append({"query_key": "x", "over_per_search_budget": True, "latency_seconds": 1.0,
                    "from_cache": True, "live_refused": None})
    rep = s.budget_report()
    assert rep["per_search_budget_breached"] is True
    assert rep["calls_over_per_search_budget"] == ["x"]


# --------------------------------------------------------------------------- #
# mount-dependent: accepted-input reuse
# --------------------------------------------------------------------------- #
@needs_mount
def test_every_accepted_input_rehashes_to_its_pinned_digest():
    digests = inputs.verify_digests()
    mismatched = {k: v for k, v in digests.items() if v["match"] is False}
    assert not mismatched, f"accepted input digest drift: {mismatched}"


@needs_mount
def test_frozen_retrieval_spec_digest_is_the_pinned_one():
    assert inputs.sha256_file(inputs.EVALUATION_MOUNT /
                              "evaluation/retrieval_gate/frozen_retrieval_benchmark.json") \
        == "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"


@needs_mount
def test_accepted_coverage_is_reproduced_exactly():
    repro = harness.reproduce_accepted()
    assert repro["coverage_reproduced"], "acceptance test (2): the accepted coverage "
    assert repro["headline_numbers_reproduced"], "acceptance test (2): the accepted "
    assert repro["improved_fr_it_cells"] == 0
    assert repro["reduced_under_covered_questions"] == 0
    de = repro["de_added_search"]
    assert de["recomputed"]["status"] == 200
    assert de["recomputed"]["n_results"] == 0


@needs_mount
def test_committed_plan_reproduces_from_the_accepted_inputs():
    committed = json.loads(RULES.read_text(encoding="utf-8"))
    derived = plan.build_plan(charter_version=1,
                              direction_version=committed.get("direction_version"))
    for key in committed:
        if key == "inputs":
            continue
        assert json.dumps(committed[key], ensure_ascii=False, sort_keys=True) == \
            json.dumps(derived.get(key), ensure_ascii=False, sort_keys=True), key


@needs_mount
def test_bundle_contract_is_read_from_the_accepted_mount_not_copied():
    c = regression.bundle_contract()
    assert c["REQUIRED_TOP"] and c["REQUIRED_DECISION"]
    assert c["source"].endswith("product/query/bundle.py")
    assert c["source_sha256"] == inputs.sha256_file(Path(c["source"]))


@needs_mount
def test_harness_refuses_to_run_on_a_tampered_freeze(tmp_path):
    committed = json.loads(RULES.read_text(encoding="utf-8"))
    committed["variant_construction"]["literals"]["de"]["JOIN"] = " !!! "
    bad = tmp_path / "RULES.json"
    bad.write_text(json.dumps(committed, ensure_ascii=False, indent=1, sort_keys=True),
                   encoding="utf-8")
    with pytest.raises(SystemExit):
        harness.run(0, tmp_path, allow_live=False, rules_path=bad)


@needs_mount
def test_offline_run_is_a_clean_bounded_negative_and_regresses_nothing(tmp_path):
    # the run reads its FROZEN rules from the committed team file; only its OUTPUT
    # goes to tmp_path, so a test can never mutate the freeze
    res = harness.run(0, tmp_path, allow_live=False, rules_path=RULES)
    assert res["baseline_reproduction"]["headline_numbers_reproduced"]
    assert res["regression_suite"]["all_passed"]
    assert res["frozen_gate_nonregression"]["no_regression"]
    assert res["measurement"]["budget"]["network_calls"] == 0
    assert res["verdict"]["controls"][
        "A2_blanked_reproduces_A0_on_every_measured_unit"] is True


@needs_mount
def test_rotated_control_never_raises_its_target():
    committed = json.loads(RULES.read_text(encoding="utf-8"))
    ordered = committed["units"]
    for i, u in enumerate(ordered):
        donor = plan_mod_next_targeted(ordered, u)
        assert donor is not None and donor["unit_id"] != u["unit_id"]


def plan_mod_next_targeted(ordered, unit):
    idx = next((n for n, u in enumerate(ordered) if u["unit_id"] == unit["unit_id"]), None)
    if idx is None:
        return None
    for step in range(1, len(ordered) + 1):
        cand = ordered[(idx + step) % len(ordered)]
        if cand.get("variants"):
            return cand
    return None


# --------------------------------------------------------------------------- #
# the published record of this run
# --------------------------------------------------------------------------- #
RUN_ID = 39237146851


def _published() -> dict:
    p = TEAM_DIR / f"harness_results_{RUN_ID}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


@pytest.mark.skipif(not (TEAM_DIR / f"harness_results_{RUN_ID}.json").is_file(),
                    reason="this run has no published results yet")
def test_published_record_satisfies_every_acceptance_test():
    res = _published()
    assert res["frozen_plan_reproduced_before_measurement"] is True
    assert res["baseline_reproduction"]["headline_numbers_reproduced"] is True
    assert res["frozen_gate_nonregression"]["no_regression"] is True
    assert res["regression_suite"]["all_passed"] is True
    c = res["verdict"]["controls"]
    assert c["A2_blanked_reproduces_A0_on_every_measured_unit"] is True
    assert c["A3_raised_coverage_or_recall_on_any_target"] is False
    assert res["verdict"]["outcome"] in ("OUTCOME_A_COMPONENT",
                                         "OUTCOME_B_BOUNDED_NEGATIVE")
    # the accepted predecessor is published BESIDE, never in place of
    assert res["verdict"]["accepted_predecessor_published_beside_not_instead_of"][
        "outcome"] == "OUTCOME_B_BOUNDED_NEGATIVE"


@pytest.mark.skipif(not (TEAM_DIR / f"integration_contract_{RUN_ID}.json").is_file(),
                    reason="this run has no published integration contract yet")
def test_integration_contract_states_the_required_disclosures():
    p = TEAM_DIR / f"integration_contract_{RUN_ID}.json"
    c = json.loads(p.read_text(encoding="utf-8"))
    assert c["acceptance_test_8_requirements"]["product_decides_and_records"]
    for key in ("if_adopted_and_the_concept_is_still_under_covered",
                "if_adopted_and_the_concept_is_covered",
                "if_declined", "standing_disclosure"):
        assert c["disclosure_text_by_outcome"][key]
    assert "retrieval signal, not proof of corpus absence" in \
        c["disclosure_text_by_outcome"]["if_adopted_and_the_concept_is_still_under_covered"]
    assert "map helps a jurist" in c["claim_ceiling"]
    assert c["exact_drop_in_path"]["seam"]
    assert c["additive_provenance_entry"]["channel"] == "nl_concept_seeded"
    assert c["measured_effect"]["frozen_gate_nonregression"]["frozen_files_modified"] == []


@pytest.mark.skipif(not (TEAM_DIR / "freeze_ordering.json").is_file(),
                    reason="freeze ordering not computed yet")
def test_freeze_ordering_is_recomputed_from_real_git_commit_times():
    fo = json.loads((TEAM_DIR / "freeze_ordering.json").read_text(encoding="utf-8"))
    assert fo["freeze_precedes_measurement"] is True
    assert fo["margin_seconds"] is not None and fo["margin_seconds"] > 0
    assert "no hand-written timestamp" in fo["method"]
    assert fo["evidence_state"] == "COMPLETE"
    assert fo["repository_is_shallow"] is False


# --------------------------------------------------------------------------- #
# The truncated-history defect: a shallow checkout must yield None, never False
# --------------------------------------------------------------------------- #
def _git_in(repo: Path, *args: str, env: dict | None = None) -> str:
    import subprocess
    base = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x",
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
            "PATH": "/usr/bin:/bin:/usr/local/bin"}
    base.update(env or {})
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, check=True, env=base).stdout


@pytest.fixture
def history_repo(tmp_path_factory):
    """A real git repo: RULES frozen, then a measurement committed after it.

    Shaped exactly like this team's real run so the truncated-history path is
    exercised against the same relative paths the module looks for.
    """
    root = tmp_path_factory.mktemp("hist")
    origin = root / "origin"
    team = origin / "results/frontier/frontier-concept-seed-recall"
    team.mkdir(parents=True)
    _git_in(origin, "init", "-q", "-b", "main")
    (team / "RULES.json").write_text('{"frozen": true}\n', encoding="utf-8")
    _git_in(origin, "add", "-A")
    _git_in(origin, "commit", "-q", "-m", "freeze RULES")
    _git_in(origin, "commit", "-q", "--allow-empty", "-m", "amend RULES",
            env={"GIT_AUTHOR_DATE": "2026-01-02T00:00:00Z",
                 "GIT_COMMITTER_DATE": "2026-01-02T00:00:00Z"})
    (team / "harness_results_1.json").write_text('{"measured": true}\n', encoding="utf-8")
    _git_in(origin, "add", "-A")
    _git_in(origin, "commit", "-q", "-m", "first measurement",
            env={"GIT_AUTHOR_DATE": "2026-01-03T00:00:00Z",
                 "GIT_COMMITTER_DATE": "2026-01-03T00:00:00Z"})
    return origin


def _shallow_clone(origin: Path, dest: Path) -> Path:
    import subprocess
    subprocess.run(["git", "clone", "-q", "--depth", "1", "file://" + str(origin),
                    str(dest)], capture_output=True, check=True)
    return dest


def test_full_history_gives_a_true_verdict(history_repo):
    rec = freeze_ordering.classify(1, repo=history_repo)
    assert rec["evidence_state"] == "COMPLETE"
    assert rec["repository_is_shallow"] is False
    assert rec["freeze_precedes_measurement"] is True
    # freeze is the MOST RECENT RULES commit (2026-01-02), measurement 2026-01-03
    assert rec["margin_seconds"] == 2 * 86400.0


def test_truncated_history_reports_none_and_never_false(history_repo, tmp_path):
    """THE REGRESSION.

    ``fetch-depth: 1`` is what every workflow in this repository does.  The old
    verifier read the grafted tip as a single commit and concluded the frozen
    rules were edited AFTER the first measurement -- a false accusation that
    would have invalidated a correct run.  Truncated history must yield None.
    """
    shallow = _shallow_clone(history_repo, tmp_path / "shallow")
    assert freeze_ordering.is_shallow(shallow) is True
    rec = freeze_ordering.classify(1, repo=shallow)
    assert rec["evidence_state"] == "INCOMPLETE_TRUNCATED_HISTORY"
    assert rec["freeze_precedes_measurement"] is None, (
        "a truncated checkout must never be reported as a freeze-ordering "
        "violation; absence of evidence is not evidence of post-hoc tuning")
    assert rec["margin_seconds"] is None
    assert rec["evidence_state_reasons"]
    assert any("shallow" in r for r in rec["evidence_state_reasons"])
    assert "--unshallow" in rec["reproduce"]


def test_unshallowing_recovers_the_true_verdict(history_repo, tmp_path):
    """The same clone, with history fetched, must reproduce the full-history truth."""
    import subprocess
    shallow = _shallow_clone(history_repo, tmp_path / "shallow2")
    assert freeze_ordering.classify(1, repo=shallow)["freeze_precedes_measurement"] is None
    subprocess.run(["git", "fetch", "-q", "--unshallow"], cwd=shallow,
                   capture_output=True, check=True)
    assert freeze_ordering.is_shallow(shallow) is False
    rec = freeze_ordering.classify(1, repo=shallow)
    assert rec["evidence_state"] == "COMPLETE"
    assert rec["freeze_precedes_measurement"] is True


def test_a_genuine_violation_still_reports_false(history_repo):
    """False must remain reachable for a REAL violation -- the fix is not a blanket True."""
    team = history_repo / "results/frontier/frontier-concept-seed-recall"
    (team / "RULES.json").write_text('{"frozen": false}\n', encoding="utf-8")
    _git_in(history_repo, "add", "-A")
    _git_in(history_repo, "commit", "-q", "-m", "post-hoc rules edit",
            env={"GIT_AUTHOR_DATE": "2026-02-01T00:00:00Z",
                 "GIT_COMMITTER_DATE": "2026-02-01T00:00:00Z"})
    rec = freeze_ordering.classify(1, repo=history_repo)
    assert rec["evidence_state"] == "COMPLETE"
    assert rec["freeze_precedes_measurement"] is False
    assert rec["margin_seconds"] < 0


def test_missing_commits_report_none_rather_than_false(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    _git_in(empty, "init", "-q", "-b", "main")
    _git_in(empty, "commit", "-q", "--allow-empty", "-m", "nothing here")
    rec = freeze_ordering.classify(1, repo=empty)
    assert rec["evidence_state"] == "INCOMPLETE_NO_COMMITS_FOUND"
    assert rec["freeze_precedes_measurement"] is None


def test_weaker_record_is_never_written_over_a_stronger_one(tmp_path, monkeypatch):
    """A later truncated run must not destroy an auditor's COMPLETE evidence."""
    monkeypatch.setattr(freeze_ordering, "TEAM_DIR", tmp_path)
    strong = {"evidence_state": "COMPLETE", "freeze_precedes_measurement": True,
              "margin_seconds": 345.0}
    (tmp_path / "freeze_ordering.json").write_text(json.dumps(strong), encoding="utf-8")
    weak = {"evidence_state": "INCOMPLETE_TRUNCATED_HISTORY",
            "freeze_precedes_measurement": None, "margin_seconds": None}
    guard = freeze_ordering._is_downgrade(weak, strong)
    assert guard and "refusing" in guard
    # and the stronger direction is allowed
    assert freeze_ordering._is_downgrade(strong, weak) is None


def test_three_valued_contract_is_published_in_the_record():
    fo = json.loads((TEAM_DIR / "freeze_ordering.json").read_text(encoding="utf-8"))
    c = fo["three_valued_contract"]
    assert "NEVER reported as False" in c
    assert "post-hoc tuning" in c


@pytest.mark.skipif(not (TEAM_DIR / f"integration_contract_{RUN_ID}.json").is_file(),
                    reason="this run has no integration contract yet")
def test_contract_warns_the_auditor_about_the_shallow_clone_trap():
    """The false refutation this team nearly published must be documented for the
    next reader, or the next verifier will re-invent it."""
    c = json.loads((TEAM_DIR / f"integration_contract_{RUN_ID}.json")
                   .read_text(encoding="utf-8"))
    v = c["how_an_auditor_verifies_this"]
    assert "--unshallow" in v["step_1_fetch_full_history"]
    assert "FALSE REFUTATION" in v["note"]
    assert "NOT measurable" in v["step_2_the_trap"]
    assert "post-hoc tuning" in v["step_2_the_trap"]
    assert "None" in v["step_3_the_verifier_is_three_valued"]
    assert "evidence_state" in v["step_3_the_verifier_is_three_valued"]
    assert "freeze_ordering" in v["step_4_reproduce"]
    assert "311ac6d0913f22d3606d6fd4772271b00116629470741c4fc6a1bdb506cc928a" in \
        v["step_5_no_frozen_file_changed"]


def test_published_rules_bytes_are_unchanged_and_still_match_the_derived_plan():
    """The resume cycle fixed a verifier. It must not have touched the frozen rules."""
    import hashlib
    raw = RULES.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == \
        "311ac6d0913f22d3606d6fd4772271b00116629470741c4fc6a1bdb506cc928a"
    derived = plan.build_plan(charter_version=1, direction_version=None)
    committed = json.loads(raw.decode("utf-8"))
    for key in ("units", "template_id", "n_variants", "thresholds"):
        assert json.dumps(committed[key], ensure_ascii=False, sort_keys=True) == \
            json.dumps(derived[key], ensure_ascii=False, sort_keys=True)

@pytest.mark.skipif(not (TEAM_DIR / f"harness_results_{RUN_ID}.json").is_file(),
                    reason="this run has no published results yet")
def test_recovery_is_disclosed_not_over_read():
    """A recovered id must come with what 'recovered' does and does not mean."""
    res = _published()
    d = res["verdict"].get("recovery_disclosure") or {}
    assert d, "an OUTCOME_A on the recall axis must publish its recovery disclosure"
    assert "QUERY's language" in d["cell_semantics"]
    for aid, info in d["per_id"].items():
        assert "absent from THIS accepted per-language cell" in info["meaning_of_recovered"]
        assert "already_present_in_accepted_pools" in info
        assert "carried_by_candidate_rows" in info


@pytest.mark.skipif(not (TEAM_DIR / f"harness_results_{RUN_ID}.json").is_file(),
                    reason="this run has no published results yet")
def test_candidate_query_metadata_is_published_for_independent_rescoring():
    res = _published()
    md = res["candidate_query_metadata"]
    assert md, "candidate queries must be published so a gate re-scoring is auditable"
    for q in md:
        assert q["status"] == 200
        assert q["raw_sha256"] and q["ids_sha256"]
        assert "rows" not in q
    assert len(md) == len(res["measurement"]["per_unit"]["served::de-kapitalverletzung"]
                          ["A1_searches"]) + 12
