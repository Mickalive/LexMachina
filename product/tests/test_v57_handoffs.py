"""Tests for this cycle's two handoff decisions (run 39185124744).

Two obligations are covered, and they are deliberately separate files' worth of
behaviour in one suite so that a false claim in one cannot be masked by a pass
in the other:

* ``product/eval_disclosure_handoff.py`` - direction v57 ordered work (4), the
  falsification handoff of the query-concept disclosure fix to Core Evaluation.
* ``product/frontier_recall_adoption.py`` - factory-wide requirement 21, the
  recorded adopt/decline decision on the accepted ``frontier-query-concept-recall``
  component.

Both modules are fail-closed by construction, so the negative controls here are
not decoration: a missing mount, a missing packet or a missing artifact must
produce a FAIL, never a quiet pass.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import eval_disclosure_handoff as h  # noqa: E402
from product import frontier_recall_adoption as a  # noqa: E402


# ---------------------------------------------------------------- handoff ---

def test_handoff_recomputes_from_the_committed_packet_bytes():
    rec = h.build()
    assert rec["failures"] == [], rec["failures"]
    assert rec["packet"]["packet_bytes_match_expected"] is True
    assert rec["packet"]["packet_raw_sha256_recomputed"] == h.PACKET_SHA256
    assert rec["summary"]["verdict"] == "PASS"


def test_handoff_fails_closed_on_a_wrong_expected_digest():
    rec = h.build(packet_sha256="0" * 64)
    assert rec["summary"]["verdict"] == "FAIL"
    assert any("raw sha256" in f for f in rec["failures"])


def test_handoff_fails_closed_on_a_missing_packet():
    rec = h.build(packet_dir=REPO_ROOT / "results" / "product" / "gate_packet" / "no-such-packet")
    assert rec["summary"]["verdict"] == "FAIL"
    assert any("missing" in f for f in rec["failures"])


def test_the_accepted_defect_is_visible_in_the_committed_bytes():
    """The 'before' record must really be self-contradictory on committed bytes.

    This is the defect the whole handoff exists to hand over, so it is asserted
    directly against the committed snapshot rather than against our own output.
    """
    rec = h.build()
    de = next(r for r in rec["questions"] if r["qid"] == "de-kapitalverletzung")
    assert de["before"]["query_concepts_under_covered"] == ["kapitalverletzung", "uberwachungspflicht"]
    assert de["before"]["warning_count"] == 0
    assert de["before"]["discloses_under_coverage"] is False
    assert de["inconsistent_before"] is True


def test_the_fix_is_disclosure_only_on_every_served_question():
    rec = h.build()
    for row in rec["questions"]:
        d = row["delta"]
        assert d["measurement_moved"] is False, row["qid"]
        assert d["blocking_count_before"] == d["blocking_count_after"], row["qid"]
        assert d["admissible_before"] == d["admissible_after"], row["qid"]
        assert row["disclosed_after"] is True, row["qid"]
    assert rec["summary"]["n_admission_changed"] == 0
    assert rec["summary"]["n_blocking_count_changed"] == 0


def test_the_disclosure_is_a_warning_and_names_every_under_covered_term():
    rec = h.build()
    de = next(r for r in rec["questions"] if r["qid"] == "de-kapitalverletzung")
    assert de["after"]["disclosure_severity"] == "warning"
    assert de["after"]["discloses_under_coverage"] is True
    codes = de["after"]["finding_codes"]
    assert h.DISCLOSURE_CODE in codes
    # the predicate reads the marker in the FINDING CODE, not in prose
    assert any("concept" in c and "under_covered" in c for c in codes)


def test_bundle_bytes_are_verified_against_the_recorded_content_sha():
    rec = h.build()
    for row in rec["questions"]:
        assert row["bundle_bytes_match_record"] is True, row["qid"]
        assert row["committed_content_sha256"] == row["bundle_content_sha256_recomputed"]


def test_handoff_envelope_carries_the_mapping_free_protocol_and_the_caveat():
    rec = h.build()
    env = h.handoff_envelope(rec, run_id="T", source_commit="C")
    assert env["falsification_protocol"]["mapping_free"] is True
    assert "analyst slug" in env["falsification_protocol"]["forbidden_in_this_check"]
    caveat = env["caveat_carried_verbatim_from_evaluation"].lower()
    assert "compound noun" in caveat
    assert "not a finding that authorities are absent" in caveat
    assert env["posture_unchanged"]["human_gate_ready"] is False
    assert env["posture_unchanged"]["owner_decision_required"] is False
    assert env["posture_unchanged"]["packet_admitted"] is False


def test_handoff_cli_exits_zero_on_the_real_tree():
    out = subprocess.run(  # noqa: S603
        [sys.executable, "product/eval_disclosure_handoff.py"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=900, check=False,
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert json.loads(out.stdout)["verdict"] == "PASS"


def test_evaluation_caveat_is_carried_wherever_the_finding_is_reported():
    """Requirement: the caveat travels with the report, not just the module."""
    from product.query import gate_admissibility

    src = Path(gate_admissibility.__file__).read_text(encoding="utf-8")
    assert "compound noun" in src
    assert "not proof that the authorities are absent" in src


# ------------------------------------------------------- adoption decision ---

def test_adoption_decision_is_reachable_against_the_mounted_team(mount_present):
    rec = a.inspect()
    if not mount_present:
        assert rec["decision"] == "DECISION_NOT_REACHABLE"
        assert rec["failures"]
        return
    assert rec["decision"] in ("ADOPT", "DECLINE")
    assert rec["failures"] == []


def test_adoption_decision_fails_closed_when_the_mount_is_absent(tmp_path):
    rec = a.inspect(tmp_path / "not-mounted")
    assert rec["mount_present"] is False
    assert rec["decision"] == "DECISION_NOT_REACHABLE"
    assert rec["reason"]


def test_adoption_decision_cli_exits_nonzero_without_a_mount(tmp_path):
    out = subprocess.run(  # noqa: S603
        [sys.executable, "product/frontier_recall_adoption.py", "--mount", str(tmp_path / "nope")],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=300, check=False,
    )
    assert out.returncode != 0
    assert json.loads(out.stdout)["decision"] == "DECISION_NOT_REACHABLE"


def test_adoption_numbers_are_copied_from_the_contract_not_typed(mount_present):
    if not mount_present:
        pytest.skip("frontier mount absent; the numbers cannot be read here")
    rec = a.inspect()
    contract = json.loads((Path(rec["mount_path"]) / a.CONTRACT_REL).read_text(encoding="utf-8"))
    n = rec["numbers_from_contract"]
    assert n["improved_fr_it_cells"] == contract["measured_outcome"]["improved_fr_it_cells"]
    cost = contract["runtime_cost"]["retrieval_cost"]
    assert n["n_calls_over_per_search_budget"] == cost["n_calls_over_per_search_budget"]
    assert n["max_per_search_seconds"] == cost["max_per_search_seconds"]
    assert n["bar_reachable_at_all"] == contract["structural_finding"]["bar_reachable_at_all"]


def test_a_decline_names_at_least_one_measured_reason(mount_present):
    if not mount_present:
        pytest.skip("frontier mount absent")
    rec = a.inspect()
    if rec["decision"] == "DECLINE":
        assert rec["decline_reasons"], "a decline without a reason is silence"
        assert "Nothing is adopted into product/" in rec["reason"]


def test_the_stale_nothing_to_adopt_reason_is_superseded_not_reused():
    """Requirement 21: the decision must name what it supersedes and why."""
    src = Path(a.__file__).read_text(encoding="utf-8")
    assert "DECLINE_NOW_NOTHING_TO_ADOPT" in src
    assert "39169296466" in src
    rec = a.inspect(Path("/tmp/opencode/definitely-not-mounted"))
    assert rec["decision"] == "DECISION_NOT_REACHABLE"


# ------------------------------------------------------------------ fixtures -

@pytest.fixture(scope="module")
def mount_present() -> bool:
    return Path(a.DEFAULT_MOUNT).is_dir()