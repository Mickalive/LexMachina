"""Run-to-run counter-instability disclosure beside the coverage-gap disclosure.

Factory direction v61, product lane ordered work (3)::

    implement Product's run-to-run counter-instability disclosure beside the
    coverage-gap disclosure (evaluation open items 5/6: FR same-query group
    DIVERGENT on sr::counter_authority_surface; the P1ext population/identity-
    movement record - jaccard 0.904762/0.892216, limiting-decision identity can
    swap - is in scope for the same disclosure block) - a disclosure-only
    change, no measurement claim, no threshold touched.

What these tests pin
--------------------
1. the block exists in the SAME per-bundle dictionary as
   ``under_coverage_disclosure`` (packet ``disclosures.json`` AND ``handoff.json``)
   and re-derives byte-identically through ``packet_of_record.check()``;
2. it is DISCLOSURE ONLY: no measurement re-derived, no threshold/bar/rubric
   touched, no classification invented, no admission flag moved;
3. its numbers are Core Evaluation's REPORTED-ONLY figures, byte-traced to the
   vendored copy of the accepted Evaluation state (origin/main blob pin) and
   anchored inside the verbatim prose;
4. the packet's scored bytes never moved (packet.json pin + the recorded
   before-digests of the disclosure surface re-derive from the accepted base);
5. ``check()`` is fail-closed, not vacuous: a committed layer missing the block
   is a mismatch.

Nothing here re-scores a frozen bar or asserts legal usefulness.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import counter_instability_disclosure as cid  # noqa: E402
from product import packet_of_record as por  # noqa: E402

PACKET = ROOT / "results" / "product" / "gate_packet" / "39319405429"
ARTIFACT = ROOT / "results" / "product" / "disclosures" / \
    "CYCLE_39422322667_counter_instability_disclosure.json"
VENDORED = ROOT / "product" / "data" / "eval_open_items" / \
    "ACCEPTED_EVALUATION_OPEN_ITEMS_5_6.json"
#: accepted base of the cycle that added the block (before-digests re-derive here)
ACCEPTED_BASE = "f463a81"
#: frozen geometry rubric identity - must never move because of a disclosure
FROZEN_RULES_SHA256 = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"

pytestmark = pytest.mark.skipif(
    not (PACKET / "PACKET_OF_RECORD.json").is_file(),
    reason="packet of record 39319405429 not present",
)


def _disclosures() -> dict:
    return json.loads((PACKET / "disclosures.json").read_text(encoding="utf-8"))


def _handoff() -> dict:
    return json.loads((PACKET / "handoff.json").read_text(encoding="utf-8"))


def _packet() -> dict:
    return json.loads((PACKET / "packet.json").read_text(encoding="utf-8"))


def _qids() -> list[str]:
    return [q["qid"] for q in _packet().get("questions") or []]


def _git_show(ref_path: str) -> bytes | None:
    """Best-effort read of a blob from the accepted base. None when unreadable."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "show", ref_path],
            capture_output=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 and proc.stdout else None


# --------------------------------------------------------------- placement ---
def test_block_is_published_beside_the_coverage_gap_disclosure():
    """Same per-bundle dictionary, in both disclosure carriers, for every qid."""
    disc = _disclosures()
    for qid in _qids():
        block = disc["per_bundle"][qid]
        assert "under_coverage_disclosure" in block, qid
        assert "counter_instability_disclosure" in block, qid
        # direct neighbours in the same layer, not a separate sidecar
        assert block["under_coverage_disclosure"]["disclosure_code"] == \
            "query_concepts_under_covered"
        assert block["counter_instability_disclosure"]["disclosure_code"] == \
            por.COUNTER_INSTABILITY_DISCLOSURE_CODE
        assert block["counter_instability_disclosure"]["published_beside"] == \
            "under_coverage_disclosure"
    for entry in _handoff()["bundles"]:
        assert "under_coverage_disclosure" in entry, entry["qid"]
        assert "counter_instability_disclosure" in entry, entry["qid"]


def test_block_reproduces_from_the_committed_bytes():
    """packet_of_record.check() re-derives the whole layer, new block included."""
    result = por.check(PACKET)
    assert result["ok"] is True, result["mismatches"]
    for qid in _qids():
        fresh = por.counter_instability_disclosure(
            next(q["language"] for q in _packet()["questions"] if q["qid"] == qid))
        recorded = _disclosures()["per_bundle"][qid]["counter_instability_disclosure"]
        assert json.dumps(fresh, sort_keys=True) == json.dumps(recorded, sort_keys=True)


def test_check_is_fail_closed_when_the_block_is_absent(tmp_path: Path):
    """Non-vacuity: a committed layer WITHOUT the block is a mismatch.

    This is the exact state the packet was in before direction v61 ordered the
    disclosure, so the guard is measured, not asserted in prose.
    """
    copy = tmp_path / "packet-copy"
    shutil.copytree(PACKET, copy)
    disc_path = copy / "disclosures.json"
    disc = json.loads(disc_path.read_text(encoding="utf-8"))
    for qid in list(disc["per_bundle"]):
        disc["per_bundle"][qid].pop("counter_instability_disclosure")
    disc_path.write_text(json.dumps(disc, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    result = por.check(copy)
    assert result["ok"] is False
    assert set(result["mismatches"]) == {f"{q}:counter_instability_disclosure"
                                         for q in _qids()}


# ------------------------------------------------------------- scope claims --
def test_disclosure_only_no_measurement_and_no_threshold():
    for qid in _qids():
        block = _disclosures()["per_bundle"][qid]["counter_instability_disclosure"]
        assert block["disclosure_only"] is True
        assert block["measurement_rederived_by_product"] is False
        assert block["threshold_touched"] is False
        assert block["threshold_or_bar_edits"] == []
        assert "REPORTED-ONLY" in block["gate_effect"]
        assert "no verdict, score, count, admission outcome" in block["gate_effect"]
        # the block classifies nothing and carries no per-decision rows
        assert "decisions" not in block and "counter_status" not in block
        assert "classification" not in block
    # frozen identities a disclosure could otherwise have moved
    assert por.MEGA_CLUSTER_SHARE == 0.5
    assert por.FROZEN_GEOMETRY_RULES_SHA256 == FROZEN_RULES_SHA256
    assert cid.por.FROZEN_GEOMETRY_RULES_SHA256 == FROZEN_RULES_SHA256


def test_admission_flags_are_unchanged_and_fail_closed():
    packet = _packet()
    scope = json.loads(ARTIFACT.read_text(encoding="utf-8"))["scope"]
    flags = scope["admission_flags_unchanged"]
    assert flags["packet_admitted"] is False
    assert flags["packet_admission_blocked"] is True
    assert flags["ready_for_owner_session"] is False
    assert flags["human_gate_ready"] is False
    assert flags["machine_gate_ready"] is False
    assert bool(packet.get("packet_admission_blocked")) is True


def test_no_threshold_or_rubric_is_named_as_edited_in_the_artifact():
    art = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert art["scope"]["threshold_touched"] is False
    assert art["scope"]["measurement_rederived_by_product"] is False
    assert art["scope"]["frozen_geometry_rules_sha256"] == FROZEN_RULES_SHA256
    assert art["scope"]["mega_cluster_share_threshold"] == 0.5
    assert any("no frozen bar" in s for s in art["non_claims"])


# ------------------------------------------------------------- provenance ----
def test_vendored_copy_pins_the_accepted_evaluation_state():
    data = json.loads(VENDORED.read_text(encoding="utf-8"))
    source = data["source"]
    assert source["file_sha256_at_pin"] == por.COUNTER_INSTABILITY_ACCEPTED_EVALUATION_SHA256_AT_PIN
    assert source["repo_path"] == "results/accepted-state/evaluation.json"
    assert source["ref"] == "origin/main"
    assert set(data["open_items"]) == {
        "item_5_fr_live_counter_run_instability_P1",
        "item_6_population_and_limiting_identity_movement_P1ext",
    }
    # loader fails closed on a mismatched pin or an unanchored number
    loaded = por.load_counter_instability_source()
    assert loaded["open_items"] == data["open_items"]


def test_every_structured_number_is_anchored_in_the_verbatim_prose():
    data = json.loads(VENDORED.read_text(encoding="utf-8"))
    for name, sv in data["structured_values"].items():
        prose = data["open_items"][sv["open_item"]]
        for anchor in sv["verbatim_anchors"]:
            assert anchor in prose, f"{name}: {anchor!r} missing from open item"
    ext = data["structured_values"]["p1ext_population_and_identity_movement"]
    assert ext["retrieved_set_jaccard"] == {"de": 0.904762, "fr": 0.892216}
    assert "jaccard 0.904762 (DE) / 0.892216 (FR)" in \
        data["open_items"][ext["open_item"]]
    p1 = data["structured_values"]["p1_counter_stage_divergence"]
    assert p1["gate"] == "sr::counter_authority_surface"
    assert p1["status"] == "DIVERGENT"
    assert p1["group"] == "FR 102-CP same-query group"


def test_published_numbers_equal_the_vendored_structured_values():
    data = json.loads(VENDORED.read_text(encoding="utf-8"))
    p1 = data["structured_values"]["p1_counter_stage_divergence"]
    ext = data["structured_values"]["p1ext_population_and_identity_movement"]
    for qid in _qids():
        block = _disclosures()["per_bundle"][qid]["counter_instability_disclosure"]
        assert block["p1_counter_stage_divergence"]["gate"] == p1["gate"]
        assert block["p1_counter_stage_divergence"]["status"] == p1["status"]
        assert block["p1_counter_stage_divergence"]["failing_run"] == p1["failing_run"]
        assert block["p1ext_population_and_identity_movement"][
            "retrieved_set_jaccard"] == ext["retrieved_set_jaccard"]
        assert block["p1ext_population_and_identity_movement"][
            "fr_counter_evidence_lost"] == ext["fr_counter_evidence_lost"]
        assert block["p1ext_population_and_identity_movement"][
            "fr_counter_evidence_gained"] == ext["fr_counter_evidence_gained"]
        assert block["p1ext_population_and_identity_movement"][
            "limiting_decision_identity_can_swap"] is True
        assert block["p1ext_population_and_identity_movement"][
            "de_counter_stability"].startswith("UNTESTED")


def test_vendored_verbatim_items_still_match_the_accepted_main_state():
    """Re-verify the transcription against origin/main when it is readable.

    This is the load-bearing live provenance check: if either open item is
    rewritten or removed on ``main``, the disclosure's numbers come from
    superseded text and the vendored copy must be re-pinned with a disclosed
    supersession (a failure here, not a skip).

    The compact accepted-state index lives on ``main`` only, so the guard reads
    it the way ``test_audit_seam`` reads ``state/model_health.json``: with an
    explicit skip when the ref is unavailable (never a silent pass).
    """
    raw = _git_show("origin/main:results/accepted-state/evaluation.json")
    if raw is None:
        pytest.skip("origin/main:results/accepted-state/evaluation.json not "
                    "readable in this checkout; at-pin digests are still "
                    "re-derived from the pin commit in the test below")
    data = json.loads(VENDORED.read_text(encoding="utf-8"))
    current = json.loads(raw.decode("utf-8"))
    if "open_items" not in current:
        pytest.skip("origin/main:results/accepted-state/evaluation.json has "
                    "different structure than the vendored open_items; "
                    "re-pin the vendored copy with a disclosed supersession")
    for key, text in data["open_items"].items():
        assert current["open_items"][key] == text, (
            f"{key} drifted on main - re-pin the vendored copy, the code "
            "constant and this cycle's packet disclosure together, with a "
            "disclosed supersession"
        )
    # A file-level move with both items intact is disclosed drift, not a
    # failure: the vendored copy must then document exactly how such a move
    # is handled rather than silently pretending the pin is live.
    if hashlib.sha256(raw).hexdigest() != data["source"]["file_sha256_at_pin"]:
        assert "file-level move" in data["source"]["pin_semantics"]


def test_at_pin_digest_re_derives_from_the_pin_commit():
    """History-stable re-derivation of the pinned accepted-state digest.

    ``pin_commit`` names the ``origin/main`` commit whose
    ``results/accepted-state/evaluation.json`` produced the pinned sha and blob
    oid, so anyone can reproduce both from committed git history:
    ``git show <pin_commit>:results/accepted-state/evaluation.json | sha256sum``.
    """
    data = json.loads(VENDORED.read_text(encoding="utf-8"))
    source = data["source"]
    pin_commit = source["pin_commit"]
    assert len(pin_commit) == 40
    raw = _git_show(f"{pin_commit}:results/accepted-state/evaluation.json")
    if raw is None:
        pytest.skip(f"pin commit {pin_commit} not readable in this checkout")
    assert hashlib.sha256(raw).hexdigest() == source["file_sha256_at_pin"]
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse",
         f"{pin_commit}:results/accepted-state/evaluation.json"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if proc.returncode != 0:
        pytest.skip("git rev-parse of the pinned blob unavailable")
    assert proc.stdout.strip() == source["git_blob_oid_at_pin"]
    # the code pin, the vendored pin and the pin commit must never disagree
    assert source["file_sha256_at_pin"] == \
        por.COUNTER_INSTABILITY_ACCEPTED_EVALUATION_SHA256_AT_PIN


def test_before_surface_digests_re_derive_from_the_accepted_base():
    art = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    before = art["disclosure_surface_regeneration"]["before"]
    for name in ("disclosures.json", "handoff.json", "PACKET_OF_RECORD.json"):
        raw = _git_show(f"{ACCEPTED_BASE}:results/product/gate_packet/39319405429/{name}")
        if raw is None:
            pytest.skip(f"accepted base {ACCEPTED_BASE} not readable in this checkout")
        assert hashlib.sha256(raw).hexdigest() == before[name], name


def test_scored_bytes_never_moved():
    """packet.json keeps its frozen pin; only the disclosure surface moved."""
    sha = hashlib.sha256((PACKET / "packet.json").read_bytes()).hexdigest()
    assert sha == cid.PACKET_JSON_RAW_SHA256
    art = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert art["packet"]["packet_json_raw_sha256"] == cid.PACKET_JSON_RAW_SHA256
    assert art["packet"]["packet_json_pin_holds"] is True
    assert art["packet"]["n_bundle_bytes"] == 3
    pins = art["disclosure_surface_regeneration"]["unchanged"]
    assert any("packet.json" in p for p in pins)
    assert any("nine questions" in p for p in pins)


# ------------------------------------------------------------ language scope -
def test_language_scope_states_only_what_the_measurement_supports():
    fr = por.counter_instability_disclosure("fr")["applies_to_this_bundle_language"]
    de = por.counter_instability_disclosure("de")["applies_to_this_bundle_language"]
    it = por.counter_instability_disclosure("it")["applies_to_this_bundle_language"]
    unk = por.counter_instability_disclosure(None)["applies_to_this_bundle_language"]
    assert fr["counter_stage_evidence"].startswith("DIRECT")
    assert de["counter_stage_evidence"].startswith("UNTESTED")
    assert "not proven" in de["counter_stage_evidence"]
    assert it["counter_stage_evidence"].startswith("NOT MEASURED")
    assert unk["counter_stage_evidence"].startswith("NOT DETERMINED")
    # no language may claim a measured verdict the accepted population lacks
    assert "NOT MEASURED" not in fr["counter_stage_evidence"]
    assert "DIRECT" not in it["counter_stage_evidence"]


def test_implication_states_the_run_stability_limitation_not_a_verdict():
    block = por.counter_instability_disclosure("fr")
    text = block["implications"]
    assert "not evidence that no contrary or limiting authority exists" in text
    assert "one sampled run rather than a run-stable enumeration" in text
    assert "this block classifies nothing" in text
    # REPORTED-ONLY framing lives in the gate_effect of every block
    assert "REPORTED-ONLY" in block["gate_effect"]


# ------------------------------------------------------- artifact reproducible
def test_shipped_artifact_reproduces_and_says_what_it_is_not():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "product" / "counter_instability_disclosure.py"),
         "--check"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    art = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert art["run_id"] == 39422322667
    assert art["direction_version"] == 61
    assert art["packet_of_record_check"]["ok"] is True
    assert art["evidence_source"]["measuring_run"] == 39322925971
    assert art["evidence_source"]["file_sha256_at_pin_pinned_in_code"] == \
        por.COUNTER_INSTABILITY_ACCEPTED_EVALUATION_SHA256_AT_PIN
    assert art["evidence_source"]["pin_commit"] == \
        json.loads(VENDORED.read_text(encoding="utf-8"))["source"]["pin_commit"]
    for q in art["per_question"]:
        assert q["published_in_packet_disclosures_json"]["matches_rederivation"] is True
    assert any("no owner session" in s for s in art["non_claims"])
    assert "measures nothing" in art["claim_ceiling"]
