"""Tests for the multi-query human-gate packet (direction v52, backlog item 3).

What is pinned here
-------------------
The packet is the thing the owner ceremony runs on, so the properties that keep
it honest are mechanical and testable:

1. the three questions are **pre-registered**: three real Swiss research tasks,
   one per language, pinned by digest, and the digest check actually refuses an
   edited manifest;
2. admissibility is **re-verified at run time** and refuses exactly the defects
   this lane has already been audited for - a citation that belongs to another
   decision, a shared citation string, synthetic content, a foreign source host,
   an answer that cites nothing or cites off-map, a null ``source_url`` on a
   hydrated row;
3. the packet emits **per-query drafts only**: the file it writes is refused by
   the accepted finalizer (exit 4), so it can never become human-gate evidence;
4. the **existing guards** in ``human_gate_finalize`` are exercised against each
   bundle: exit 3 for an unanswered session, exit 8 for a simulated record in the
   canonical directory and for an undeclared session there, and a clean accept
   path for a real answered session on that bundle;
5. **no frozen bundle is ever reused**: re-verification re-hashes the artifact
   and blocks a bundle that drifted since preflight;
6. **nothing claims the gate**: no artifact and no state written here says
   ``human_gate_ready`` or answers a gate question;
7. the page honours the packet's per-question deep link.

The end-to-end preflight runs against the deterministic offline fixture corpus,
so the whole chain executes in CI with no network.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))
sys.path.insert(0, str(ROOT))

import gate_packet as gp  # noqa: E402
import human_gate_session as runner  # noqa: E402
import human_gate_finalize as hgf  # noqa: E402
from product.query import gate_admissibility as ga  # noqa: E402

MACHINERY_MANIFEST = ROOT / "product" / "tests" / "fixtures" / "gate_packet_machinery_questions.json"
NODE = shutil.which("node")


# --------------------------------------------------------------------------- #
# fixtures: one real bundle, built once per module through the shipped pipeline
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def fixture_bundle() -> dict:
    """A real enriched bundle from the deterministic offline fixture corpus."""
    from query import run_query

    # fixture_generation=True keeps the offline answer deterministic
    # (model: fixture://generative-audit) instead of depending on a free model
    # subprocess being reachable, which would make these tests flaky.
    bundle = run_query("Kündigung Mietvertrag Mietrecht", top_n=100,
                       retrieval_mode="fixture", fixture_generation=True)
    assert bundle["decisions"], "fixture corpus produced no decisions"
    return bundle


@pytest.fixture(scope="module")
def packet(tmp_path_factory) -> Path:
    """Run the whole packet chain offline, once, and hand back the packet dir."""
    out_root = tmp_path_factory.mktemp("gate_packet")
    code = gp.main([
        "preflight", "--fixture", "--questions", str(MACHINERY_MANIFEST),
        "--run-id", "test-run", "--operator", "pytest", "--n", "100",
        "--out-root", str(out_root), "--quiet",
    ])
    assert code == 0, "offline preflight did not complete"
    return out_root / "test-run"


@pytest.fixture
def packet_copy(packet, tmp_path) -> Path:
    """A private, self-contained copy, for the tests that corrupt an artifact.

    ``packet.json`` stores absolute artifact paths, so the copy rewrites them to
    point at itself; otherwise a test that "corrupts its copy" would silently
    corrupt the module-scoped packet every later test reads.
    """
    target = tmp_path / "packet"
    shutil.copytree(packet, target)
    summary_path = target / "packet.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    for entry in summary["questions"]:
        for key in ("bundle_path", "question_path"):
            if entry.get(key):
                entry[key] = str(target / Path(entry[key]).relative_to(packet))
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# 1. the pre-registration
# --------------------------------------------------------------------------- #
def test_three_real_questions_one_per_language_are_pre_registered():
    manifest = gp.load_manifest()
    assert manifest["packet_id"] == "gate-packet-v1"
    questions = manifest["questions"]
    assert len(questions) == 3, "MP §12 asks for a small SET of real tasks; three is the packet"
    assert sorted(q["language"] for q in questions) == ["de", "fr", "it"]
    assert len({q["qid"] for q in questions}) == 3
    for q in questions:
        assert len(q["question"]) > 40, f"{q['qid']}: a real research task, not a keyword"
        # every question carries the hypothesis it is meant to test BEFORE results
        assert q["hypothesis"] and q["look_for"] and q["counter_authority_needed"]
        assert q["legal_area"]
    assert "SMALL SET" in manifest["authority"] or "small set" in manifest["authority"].lower()
    assert "success_rule" in manifest and "before results" in manifest["success_rule"].lower()


def test_the_success_rule_is_fixed_before_results():
    """No post-hoc loosening: the rule is about named authority, not a yes/no."""
    rule = gp.load_manifest()["success_rule"].lower()
    assert "pre-registered" in rule or "pre-registered" in rule
    assert "names at least one specific decision" in rule
    assert "does not count as a positive result" in rule


def test_editing_the_pre_registration_after_the_fact_is_refused(tmp_path, monkeypatch):
    manifest = gp.load_manifest()
    edited = dict(manifest)
    edited["questions"] = [dict(manifest["questions"][0])]
    edited["questions"][0]["question"] = "a question chosen after seeing the results"
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(edited, ensure_ascii=False), encoding="utf-8")
    # the pin covers the canonical path, so point the tool at the edited file
    monkeypatch.setattr(gp, "QUESTIONS_PATH", path)
    with pytest.raises(ValueError, match="pre-registration digest mismatch"):
        gp.load_manifest()


def test_the_committed_manifest_matches_its_pinned_digest():
    manifest = gp.load_manifest()
    assert manifest["_sha256"] == gp.PREREGISTERED_MANIFEST_SHA256


# --------------------------------------------------------------------------- #
# 2. run-time admissibility refuses what the audits found
# --------------------------------------------------------------------------- #
def test_a_real_enriched_fixture_bundle_is_admissible(fixture_bundle):
    verdict = ga.verify_bundle(fixture_bundle)
    assert verdict["admissible"], verdict["findings"]
    assert verdict["blocking_count"] == 0
    assert verdict["measured"]["n_decisions"] >= 100
    assert verdict["measured"]["answer_status"] in ("ready", "degraded")
    assert verdict["measured"]["content_sha256"]


def test_a_foreign_citation_on_a_citation_channel_row_is_refused(fixture_bundle):
    """The defect of run 38766812030, reproduced and refused.

    The failure mode is a citation-channel row carrying the CITED seed's own
    reference instead of its own, so the test uses the seed this bundle actually
    retrieved - not a made-up string that would pass vacuously.
    """
    from product.replay_bundle import citation_findings

    clean = citation_findings(fixture_bundle)
    assert not any(clean[k] for k in ("citation_duplicates", "citation_channel_seed_refs",
                                      "pending_shell_identity")), clean

    rows = [d for d in fixture_bundle["decisions"]
            if set(d.get("channels") or ()) & {"citation.incoming", "citation.outgoing"}]
    assert rows, "the fixture must contain citation-channel rows for this to mean anything"
    seed = (clean["citation_seeds_checked"] or ["bge_BGE_123_III_124"])[0]

    broken = copy.deepcopy(fixture_bundle)
    target = next(d for d in broken["decisions"] if d["decision_id"] == rows[0]["decision_id"])
    target["citation"] = seed  # the seed's own reference on another decision's row
    sibling = broken["decisions"][0]
    if sibling["decision_id"] == target["decision_id"]:  # make sure the string is shared
        sibling = broken["decisions"][1]
    sibling["citation"] = seed

    verdict = ga.verify_bundle(broken)
    assert not verdict["admissible"]
    codes = {f["code"] for f in verdict["findings"] if f["severity"] == "blocking"}
    assert "citation_channel_seed_refs" in codes
    assert "citation_duplicates" in codes


def test_two_rows_sharing_one_citation_string_are_refused(fixture_bundle):
    broken = copy.deepcopy(fixture_bundle)
    broken["decisions"][0]["citation"] = broken["decisions"][1]["citation"] or "SHARED"
    verdict = ga.verify_bundle(broken)
    assert not verdict["admissible"]
    assert "citation_duplicates" in {f["code"] for f in verdict["findings"]}


def test_synthetic_content_is_refused(fixture_bundle):
    broken = copy.deepcopy(fixture_bundle)
    broken["decisions"][0]["decision_id"] = "bge_BGE_test_0007_2024"
    verdict = ga.verify_bundle(broken)
    assert not verdict["admissible"]
    assert "synthetic_decision_ids" in {f["code"] for f in verdict["findings"]}


def test_a_foreign_source_host_is_refused(fixture_bundle):
    broken = copy.deepcopy(fixture_bundle)
    broken["decisions"][0]["canonical_url"] = "https://example.invalid/decision/1"
    verdict = ga.verify_bundle(broken)
    assert not verdict["admissible"]
    assert "foreign_source_host" in {f["code"] for f in verdict["findings"]}


def test_a_null_source_url_is_only_excused_on_an_unhydrated_shell(fixture_bundle):
    """Backlog item (2), machine-checked: the nulls are un-hydrated citation
    shells, NOT OpenCaseLaw omitting URLs - so a null on a hydrated row is a
    different, real defect and must block."""
    shells = [d for d in fixture_bundle["decisions"] if ga._is_citation_shell(d)]
    hydrated = [d for d in fixture_bundle["decisions"] if not ga._is_citation_shell(d)]
    assert shells and hydrated, "fixture must contain both kinds of row for this to mean anything"

    excused = copy.deepcopy(fixture_bundle)
    for row in excused["decisions"]:
        if ga._is_citation_shell(row):
            row["source_url"] = None
    verdict = ga.verify_bundle(excused)
    assert verdict["measured"]["source_url_null_rows"] == len(shells)
    assert verdict["measured"]["source_url_null_rows_explained_by_unhydrated_shells"] == len(shells)
    assert verdict["admissible"], "an un-hydrated shell with no source_url is the known, disclosed state"

    unjustified = copy.deepcopy(fixture_bundle)
    unjustified["decisions"][0]["source_url"] = None  # a hydrated row
    verdict = ga.verify_bundle(unjustified)
    assert not verdict["admissible"]
    assert "source_url_null_on_hydrated_row" in {f["code"] for f in verdict["findings"]}


def test_an_answer_that_cites_nothing_or_cites_off_map_is_refused(fixture_bundle):
    empty = copy.deepcopy(fixture_bundle)
    empty["answer"] = dict(empty["answer"], cited_decision_ids=[], status="ready")
    verdict = ga.verify_bundle(empty)
    assert "answer_cites_nothing" in {f["code"] for f in verdict["findings"]}

    off_map = copy.deepcopy(fixture_bundle)
    off_map["answer"] = dict(off_map["answer"], cited_decision_ids=["bge_BGE_999_999_1999"])
    verdict = ga.verify_bundle(off_map)
    assert "answer_cites_off_map_decision" in {f["code"] for f in verdict["findings"]}


def test_a_bundle_below_the_comparative_map_floor_is_refused(fixture_bundle):
    small = copy.deepcopy(fixture_bundle)
    small["decisions"] = small["decisions"][:20]
    small["clusters"] = [c for c in small["clusters"] if c.get("cluster_id") == 0][:1]
    verdict = ga.verify_bundle(small)
    assert "map_too_small" in {f["code"] for f in verdict["findings"]}


def test_map_semantics_limits_are_disclosed_not_claimed(fixture_bundle):
    """The frontier map-semantics findings are WARNINGS: disclosed to the jurist,
    never used to refuse a packet and never phrased as a map-quality claim."""
    mega = copy.deepcopy(fixture_bundle)
    for cluster in mega["clusters"]:
        cluster["member_ids"] = [d["decision_id"] for d in mega["decisions"]]
        # `size` is the definition the share is computed from (v54 R2): qmap.py
        # truncates member_ids at 50, so a cluster whose whole population is in
        # member_ids must also declare that population in `size`, otherwise the
        # two published definitions disagree and this test would only be
        # asserting one of them.
        cluster["size"] = len(mega["decisions"])
    verdict = ga.verify_bundle(mega)
    codes = {f["code"]: f for f in verdict["findings"]}
    assert "map_is_one_mega_cluster" in codes
    assert codes["map_is_one_mega_cluster"]["severity"] != "blocking"
    assert verdict["admissible"], "a disclosed map weakness does not block the packet"

    bare = copy.deepcopy(fixture_bundle)
    bare["relations"] = []
    verdict = ga.verify_bundle(bare)
    empty = next(f for f in verdict["findings"] if f["code"] == "no_relations_on_map")
    assert empty["severity"] != "blocking"


def test_a_bundle_with_no_counter_authority_discloses_it_rather_than_silently_shipping(fixture_bundle):
    bare = copy.deepcopy(fixture_bundle)
    for d in bare["decisions"]:
        d["counter_status"] = "none"
    verdict = ga.verify_bundle(bare)
    finding = next(f for f in verdict["findings"] if f["code"] == "no_counter_authority")
    assert finding["severity"] != "blocking"
    assert "gate question 3" in finding["detail"]


# --------------------------------------------------------------------------- #
# 3-6. the packet itself
# --------------------------------------------------------------------------- #
def test_preflight_produces_one_admissible_entry_per_question(packet):
    summary = json.loads((packet / "packet.json").read_text(encoding="utf-8"))
    assert summary["ok"], summary.get("blocked")
    assert summary["n_attempted"] == summary["n_questions"] == 3
    assert summary["blocked"] == []
    assert len(summary["admissible_questions"]) == 3
    assert summary["guards_all_ok"] is True
    # a fixture packet is never owner-ready, whatever else it shows
    assert summary["ready_for_owner_session"] is False
    assert summary["mode"] == "fixture"
    assert "NOT gate material" in summary["claim_ceiling"]


def test_each_question_carries_its_bundle_draft_and_disclosures(packet):
    summary = json.loads((packet / "packet.json").read_text(encoding="utf-8"))
    for entry in summary["questions"]:
        qfile = json.loads(Path(entry["question_path"]).read_text(encoding="utf-8"))
        assert qfile["record_type"] == "product-gate-packet-question"
        assert qfile["is_session_draft"] is False
        assert qfile["qid"] == entry["qid"]
        assert qfile["question"], "the draft names the question the owner is asked"
        assert qfile["bundle"]["n_decisions"] >= 100
        assert len(qfile["bundle"]["content_sha256"]) == 64
        assert qfile["deep_link"] and "q=" in qfile["deep_link"]
        assert "human_gate_session.py finalize" in qfile["finalize_command"]
        assert "--owner-session" in qfile["finalize_command"]
        assert set(qfile["gate_questions"]) == set(hgf.GATE_QUESTIONS)
        assert "answers" not in qfile, "a pre-registered question carries no jurist answer"


def test_the_packet_question_file_can_never_be_finalized_as_evidence(packet):
    """It is not a session draft, and the accepted finalizer refuses it (exit 4)."""
    summary = json.loads((packet / "packet.json").read_text(encoding="utf-8"))
    qfile = json.loads(Path(summary["questions"][0]["question_path"]).read_text(encoding="utf-8"))
    problems = hgf.validate_draft(qfile)
    assert problems, "a packet question file must not pass session-draft validation"
    assert any("record_type" in p for p in problems)
    with pytest.raises(hgf.FinalizeError) as excinfo:
        hgf.finalize(qfile, None, json.loads(Path(summary["questions"][0]["bundle_path"]).read_text()))
    assert excinfo.value.exit_code == 4


def test_the_existing_guards_are_exercised_for_every_bundle(packet):
    summary = json.loads((packet / "packet.json").read_text(encoding="utf-8"))
    for entry in summary["questions"]:
        qfile = json.loads(Path(entry["question_path"]).read_text(encoding="utf-8"))
        guards = qfile["guards"]
        assert guards["ok"], guards
        assert guards["packet_file_refused"]["exit_code"] == 4
        assert guards["simulated_probe"]["exit_code"] in (0, 3)
        assert guards["simulated_probe"]["simulated"] is True
        assert guards["simulated_probe"]["evidence_scan_admissible"] is True
        assert guards["simulated_into_canonical_refused"]["exit_code"] == 8
        assert guards["undeclared_into_canonical_refused"]["exit_code"] == 8
        assert guards["real_session_would_be_accepted"]["ok"] is True
        assert guards["real_session_would_be_accepted"]["exit_code"] == 0


def test_no_packet_artifact_writes_into_an_evidence_directory(packet):
    canonical = Path(hgf.CANONICAL_DIR_DEFAULT).resolve()
    simulated = Path(hgf.SIMULATED_DIR_DEFAULT).resolve()
    for path in packet.rglob("*"):
        resolved = path.resolve()
        assert resolved != canonical and canonical not in resolved.parents
        assert resolved != simulated and simulated not in resolved.parents


def test_no_packet_artifact_claims_the_gate_is_passed(packet):
    """No artifact in the packet is a session record or a gate verdict.

    The guard probe DOES report that the record it exercised in a temp directory
    was ``simulated: true`` - that is the proof, not the violation. What must not
    exist anywhere in the packet is a finalized session record or a gate claim.
    """
    for path in packet.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
        assert '"human_gate_ready": true' not in text
        assert "human gate passed" not in text.lower()
        records = payload if isinstance(payload, list) else [payload]
        for record in records:
            if not isinstance(record, dict):
                continue
            assert record.get("record_type") != "lex_human_gate_session", (
                f"{path.name} is a session record; the packet emits per-query drafts only"
            )
            assert record.get("status") not in ("finalized", "incomplete")
            assert "answers" not in record or not record.get("answers"), (
                f"{path.name} carries gate answers; only a jurist may write those"
            )


def test_recheck_reverifies_at_run_time_and_blocks_a_drifted_bundle(packet_copy):
    first = gp.recheck_packet(packet_copy)
    assert first["rechecked"] is True
    assert first["blocked_questions"] == []
    assert first["questions"], "a packet with no questions is not a packet"

    target = next(Path(q["bundle_path"]) for q in first["questions"])
    bundle = json.loads(target.read_text(encoding="utf-8"))
    bundle["decisions"][0]["citation"] = "TAMPERED"
    target.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    second = gp.recheck_packet(packet_copy)
    blocked = {q["qid"]: q for q in second["questions"] if not q["admissible"]}
    assert target.stem.split(".")[0] in blocked, "a bundle that drifted after preflight is blocked"
    codes = {f["code"] for f in blocked[target.stem.split(".")[0]]["verdict"]["findings"]}
    assert "bundle_drifted_since_preflight" in codes


def test_recheck_uses_the_packets_own_frozen_manifest(packet_copy):
    recheck = gp.recheck_packet(packet_copy)
    assert recheck["manifest_note"] is None
    assert recheck["manifest_sha256"] == json.loads(
        (packet_copy / "packet.json").read_text(encoding="utf-8")
    )["manifest_sha256"]


def test_recheck_refuses_a_packet_with_no_packet_json(tmp_path):
    with pytest.raises(FileNotFoundError):
        gp.recheck_packet(tmp_path)


def test_verify_cli_exits_nonzero_when_a_question_is_blocked(packet_copy):
    code = gp.main(["verify", "--packet", str(packet_copy), "--quiet"])
    assert code == 0
    entry = json.loads((packet_copy / "packet.json").read_text(encoding="utf-8"))["questions"][0]
    broken = copy.deepcopy(json.loads(Path(entry["bundle_path"]).read_text(encoding="utf-8")))
    broken["answer"] = dict(broken["answer"], cited_decision_ids=[])
    Path(entry["bundle_path"]).write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
    # the recheck also sees the content hash drift, so the question is blocked
    assert gp.main(["verify", "--packet", str(packet_copy), "--quiet"]) == 5


def test_card_prints_every_question_its_link_and_its_finalize_command(packet, capsys):
    code = gp.main(["card", "--packet", str(packet), "--quiet"])
    out = capsys.readouterr().out
    assert code == 0
    summary = json.loads((packet / "packet.json").read_text(encoding="utf-8"))
    for entry in summary["questions"]:
        assert entry["qid"] in out
        assert "open:" in out
        assert "human_gate_session.py finalize" in out
    assert "FIXTURE MODE" in out, "a fixture packet must announce that it is not gate material"
    for qid in hgf.GATE_QUESTIONS:
        assert qid in out


def test_the_guard_probe_writes_nothing_outside_a_temp_directory(packet, tmp_path, monkeypatch):
    written: list[Path] = []
    real_write = hgf.write_record

    def spy(record, out_dir):
        written.append(Path(out_dir))
        return real_write(record, out_dir)

    monkeypatch.setattr(hgf, "write_record", spy)
    entry = json.loads((packet / "packet.json").read_text(encoding="utf-8"))["questions"][0]
    bundle = json.loads(Path(entry["bundle_path"]).read_text(encoding="utf-8"))
    qfile = json.loads(Path(entry["question_path"]).read_text(encoding="utf-8"))
    guards = gp.probe_guards(bundle, qfile, run_id="test", operator="pytest")
    assert guards["ok"], guards
    assert written, "the simulated probe must actually exercise the write path"
    for path in written:
        assert str(path).startswith(str(Path(tmp_path).parent)) or "lex_gate_packet_probe_" in str(path)


@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
def test_a_packet_bundle_survives_the_real_export_and_finalize_chain(packet, tmp_path):
    """The packet's bundle must work with the ACTUAL export and finalize halves.

    The guard probe exercises the finalizer in memory.  This runs the other two
    halves the owner will use - the accepted switch's export through the real
    page (``product/export_session_draft.js``) and then
    ``human_gate_session.finish`` - against a packet bundle, as a SIMULATED
    record in a temp directory.  The repository's evidence directories are
    compared before and after: the rehearsal must not touch them.
    """
    import human_gate_evidence
    from pathlib import Path as _Path

    entry = json.loads((packet / "packet.json").read_text(encoding="utf-8"))["questions"][0]
    bundle_path = _Path(entry["bundle_path"])
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps({"q1": "partly", "q2": "yes", "q3": "partly", "q4": "yes"}),
                       encoding="utf-8")
    draft = tmp_path / "draft.json"

    before = {name: sorted(p.name for p in _Path(dir).glob("*"))
              for name, dir in (("canonical", human_gate_evidence.CANONICAL_DIR),
                                ("simulated", human_gate_evidence.SIMULATED_DIR))}

    proc = subprocess.run(
        [NODE, str(ROOT / "product" / "export_session_draft.js"),
         "--bundle", str(bundle_path), "--out", str(draft), "--answers", str(answers)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    exported = json.loads(draft.read_text(encoding="utf-8"))
    assert exported["record_type"] == "lex_human_gate_session"
    assert set(exported["answers"]) == set(hgf.GATE_QUESTIONS)

    out_dir = tmp_path / "simulated"
    code = runner.finish(
        draft, run_id="test-run", operator="pytest", bundle_path=bundle_path,
        out_dir=out_dir, simulated=True,
    )
    assert code == 0, "the real finalize chain refused a packet bundle"
    records = sorted(out_dir.glob("session_*.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_text(encoding="utf-8"))
    assert record["status"] == "finalized"
    assert record["simulated"] is True, "a machine rehearsal may never claim to be an owner session"
    assert record["bundle_hash_status"] == "verified"
    assert record["session_metrics"]["used_conventional_baseline"] is True

    after = {name: sorted(p.name for p in _Path(dir).glob("*"))
             for name, dir in (("canonical", human_gate_evidence.CANONICAL_DIR),
                               ("simulated", human_gate_evidence.SIMULATED_DIR))}
    assert after == before, "the rehearsal wrote into the repository evidence tree"


# --------------------------------------------------------------------------- #
# 7. the page honours the per-question deep link
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(NODE is None, reason="node runtime unavailable")
def test_the_real_page_boots_through_the_deep_link_and_keeps_the_export_seam(packet, fixture_bundle, tmp_path):
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(fixture_bundle, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [NODE, str(ROOT / "product" / "verify_query_page.js"), str(bundle_path), "?run_id=abc123"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "FAIL" not in proc.stdout
    assert "deep-link parameters parse" in proc.stdout
    assert "deep-link aware entry point" in proc.stdout


def test_query_html_exposes_the_deep_link_entry_point():
    """boot() is the only entry point: a deep link decides what opens, otherwise
    the previous local run resumes exactly as before."""
    html = (ROOT / "product" / "static" / "query.html").read_text(encoding="utf-8")
    assert "function boot()" in html
    assert 'p.get("run_id")' in html and 'p.get("q")' in html
    assert "window.__LEX_BOOT_PROMISE__=boot();" in html
    call = "await resumeLastRun();"
    assert call in html, "boot() still falls back to the last local run"
    assert html.index(call) > html.index("function boot()"), "resumeLastRun is called from boot()"

# --------------------------------------------------------------------------- #
# 8. the verdict roll-up: a fully passing LIVE packet must not crash
# --------------------------------------------------------------------------- #
def test_finalize_summary_handles_the_all_pass_live_case():
    """Regression for the crash that lost live run 38812599575's packet.

    ``ready_for_owner_session`` read ``summary["guards_all_ok"]`` before that
    key was written.  Python short-circuits, so only a packet where every
    question passed *and* the mode was live reached it - the single outcome the
    ceremony needs.  The 3/3 packet was produced, then lost to the KeyError.
    """
    passing = [
        {"qid": "a", "status": "admissible", "guards_ok": True},
        {"qid": "b", "status": "admissible", "guards_ok": True},
        {"qid": "c", "status": "admissible", "guards_ok": True},
    ]
    live = gp.finalize_summary({"questions": list(passing)}, 3, "live")
    assert live["ok"] is True
    assert live["admissible_questions"] == ["a", "b", "c"]
    assert live["guards_all_ok"] is True
    # v50 obligation (1): the two ACCEPTED frozen bars are a machine-readable
    # input of packet admission.  Both are unmet today (counter-label support
    # 5/65 against the absolute 1.0 bar; geometry 0/3 bundles passing all 11
    # criteria), so a live all-pass packet is NOT owner-ready even when every
    # guard passed.  This is the accepted DO-NOT-SERVE order, enforced at the
    # source instead of by discipline.
    assert live["ready_for_owner_session"] is False
    assert live["accepted_bars"]["all_bars_met"] is False
    blocked_by = live["ready_for_owner_session_blocked_by_bars"]
    assert blocked_by["would_have_been_ready"] is True
    assert set(blocked_by["unmet_bars"]) == {"counter_label_support", "map_geometry_semantics"}

    fixture = gp.finalize_summary({"questions": list(passing)}, 3, "fixture")
    assert fixture["ok"] is True
    assert fixture["ready_for_owner_session"] is False
    assert "NOT gate material" in fixture["fixture_note"]

    blocked = gp.finalize_summary(
        {"questions": passing[:2] + [{"qid": "c", "status": "blocked", "guards_ok": True}]},
        3, "live",
    )
    assert blocked["ok"] is False and blocked["blocked"] == ["c"]
    assert blocked["ready_for_owner_session"] is False


def test_finalize_summary_reaches_ready_only_when_both_bars_are_met(tmp_path):
    """Positive control for the bar gate: with both accepted bars met, a live
    all-pass packet is owner-ready again.  Without this control the bar gate
    could be silently sticky and every packet would stay blocked forever."""
    met_snapshot = {
        "team_run_id": "38880639079",
        "status": "PROMOTED",
        "measured_packet": "gate_packet/synthetic",
        "serve_recommendation": "SERVE (synthetic control only)",
        "label_half": {
            "verdict": "LABEL_SOUND", "n_scored": 65, "n_supported": 65,
            "support_rate": 1.0,
            "claim_text": f"rules sha {gp.bar_admission.LABEL_RULES_SHA256} all supported",
        },
        "geometry_half": {
            "verdict": "PASS", "n_bundles_pass": 3, "n_bundles": 3,
            "pass_counts": {"a": 11, "b": 11, "c": 11},
            "baseline_pass_counts": {"a": 11, "b": 11, "c": 11},
            "french_largest_share": 0.2, "french_bar": 0.6,
            "claim_text": f"rules sha {gp.bar_admission.GEOMETRY_RULES_SHA256} all pass",
        },
    }
    path = tmp_path / "ACCEPTED_BARS_synthetic.json"
    path.write_text(json.dumps(met_snapshot), encoding="utf-8")

    import product.query.bar_admission as ba
    bars = ba.accepted_bars(path)
    assert bars["all_bars_met"] is True and bars["unmet_bars"] == []

    passing = [{"qid": "a", "status": "admissible", "guards_ok": True}]
    before = ba.enforce_packet_admission(
        {"questions": list(passing), "ok": True, "guards_all_ok": True,
         "ready_for_owner_session": True}, path=path)
    assert before["ready_for_owner_session"] is True
    assert "ready_for_owner_session_blocked_by_bars" not in before


def test_finalize_summary_refuses_ready_when_a_guard_failed():
    passing = [{"qid": "a", "status": "admissible", "guards_ok": False}]
    out = gp.finalize_summary({"questions": passing}, 1, "live")
    assert out["ok"] is True          # admissibility passed ...
    assert out["guards_all_ok"] is False
    assert out["ready_for_owner_session"] is False, "... but the ceremony guards did not"
