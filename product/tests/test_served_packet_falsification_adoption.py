"""v55 SECOND ITEM: adopt the one Frontier verdict that measured THIS packet.

``frontier-served-packet-falsification`` (charter 1, team run 38880639079,
accept commit 464c45f, independent audit ``CYCLE_38880639079_GATE.json`` =
PASS / safe_to_integrate / ``required_fixes=[]``) is the first accepted
measurement of gate packet ``38839347028`` — the packet that will be served:

  * label half: 5 of 65 counter labels SUPPORTED by the row's own cited
    evidence -> ``LABEL_UNSOUND`` (frozen bar is absolute 1.0);
  * geometry half: 0 of 3 bundles pass all 11 criteria -> ``FAIL``;
  * promotion outcome A: ``DO-NOT-SERVE this packet unchanged``.

Factory direction v55, SECOND ITEM: *"product adopts that verdict as input and
does NOT wait for it."*  The product's own accepted state already prescribes
the mechanism: *"If Frontier later measures THIS packet's post-D2-fix labels or
the current geometry, harvest that verdict the same way and update the
snapshot; never re-measure labels or geometry in the product lane."*

These tests pin the adoption's load-bearing honesty:

  * the NEW verdict carries ``covers_this_packet=true`` (it is scoped to this
    packet) while the two PRE-FIX/PRE-REBUILD verdicts keep
    ``covers_this_packet=false`` (they are not scoped to it) — flipping either
    direction would lie about which artifact was measured;
  * the frozen packet ``38839347028`` is NOT rewritten by the adoption: its
    build-time ``disclosures.json`` still carries exactly the two earlier
    verdicts and its byte identity still verifies;
  * the owner card carries the verdict AND its claim ceiling — re-applying the
    team's own forbidden-construction patterns to the card text must find
    nothing, because adopting a verdict never licenses the product to assert
    that any specific decision is supporting, contrary or limiting.

Nothing here is a map-quality, discoverability or human-gate claim.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
PRODUCT = REPO_ROOT / "product"
if str(PRODUCT) not in sys.path:
    sys.path.insert(0, str(PRODUCT))

import frontier_verdict_adoption as fva  # noqa: E402

ACCEPTED_ROOT = Path("/tmp/lex_accepted/frontier")
PACKET = REPO_ROOT / "results" / "product" / "gate_packet" / "38839347028"


def _committed() -> dict:
    snap = fva.load_served_packet_falsification()
    assert snap is not None, (
        "the served-packet-falsification snapshot is not committed; run "
        "python product/frontier_verdict_adoption.py harvest-served-packet")
    return snap


def test_the_committed_snapshot_is_faithful_to_the_accepted_team():
    snap = _committed()
    assert snap["team_id"] == "frontier-served-packet-falsification"
    assert snap["team_run_id"] == "38880639079"
    assert snap["accept_commit"].startswith("464c45f")
    assert snap["status"] == "PROMOTED"
    assert snap["evidence_tier"] == "MEASURED"
    assert snap["cycle_status"] == "COMPLETE_NEGATIVE_RESULT"
    assert snap["covers_this_packet"] is True
    label, geometry = snap["label_half"], snap["geometry_half"]
    assert label["verdict"] == "LABEL_UNSOUND"
    assert label["n_scored"] == 65 and label["n_supported"] == 5
    assert label["direction_vs_baseline"] == "IMPROVED"
    assert geometry["verdict"] == "FAIL"
    assert geometry["n_bundles_pass"] == 0 and geometry["n_bundles"] == 3
    assert geometry["pass_counts"] == {"de-kapitalverletzung": 6,
                                       "fr-bail-entretien": 5,
                                       "it-responsabilita-medica": 5}
    assert "DO-NOT-SERVE" in snap["serve_recommendation"]
    assert snap["claim_ceiling"] and snap["forbidden_construction_patterns"]


def test_the_disclosure_scopes_each_verdict_to_the_artifact_it_measured():
    """The load-bearing honesty: TRUE for this packet, FALSE for the two that
    were measured on superseded artifacts."""
    d = fva.disclosure()
    assert d["published"] is True
    assert d["frontier_counter_label_integrity"]["covers_this_packet"] is False
    assert d["frontier_map_semantics"]["covers_this_packet"] is False
    spf = d["frontier_served_packet_falsification"]
    assert spf["published"] is True
    assert spf["covers_this_packet"] is True
    assert "38839347028" in spf["measured_packet"]
    assert spf["label_verdict"] == "LABEL_UNSOUND"
    assert spf["geometry_verdict"] == "FAIL"
    assert spf["n_scored"] == 65 and spf["n_supported"] == 5
    assert spf["n_bundles_pass"] == 0 and spf["n_bundles"] == 3
    assert "DO-NOT-SERVE" in spf["serve_recommendation"]


def test_harvest_fails_loudly_on_an_absent_mount():
    with pytest.raises(FileNotFoundError, match="served-packet-falsification verdict"):
        fva.harvest_served_packet_falsification(Path("/nonexistent/accepted"))


def test_harvest_refuses_a_state_that_was_never_promoted(tmp_path):
    root = tmp_path / "frontier" / fva.SPF_TEAM
    (root / fva.SPF_STATE.parent).mkdir(parents=True, exist_ok=True)
    (root / fva.SPF_INTEGRATION_CONTRACT.parent).mkdir(parents=True, exist_ok=True)
    (root / fva.SPF_CLAIM_CEILING.parent).mkdir(parents=True, exist_ok=True)
    (root / fva.SPF_STATE).write_text(json.dumps({"status": "RUN", "verdict": {}}),
                                      encoding="utf-8")
    (root / fva.SPF_INTEGRATION_CONTRACT).write_text("{}", encoding="utf-8")
    (root / fva.SPF_CLAIM_CEILING).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="not PROMOTED"):
        fva.harvest_served_packet_falsification(tmp_path / "frontier")


def test_the_snapshot_sources_match_the_accepted_mount_when_it_is_present():
    if not (ACCEPTED_ROOT.is_dir() and (ACCEPTED_ROOT / fva.SPF_TEAM).is_dir()):
        pytest.skip("accepted Frontier mounts not present in this cycle")
    snap = _committed()
    for entry in snap["source_files"]:
        path = Path(entry["path"])
        assert path.is_file(), path
        import hashlib
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], f"{path} changed since the harvest"


def test_the_owner_card_carries_the_verdict_and_its_claim_ceiling():
    import gate_packet as gp
    lines = gp._frontier_verdict_lines()
    text = "\n".join(lines)
    assert lines
    # the two earlier verdicts are unchanged on the card
    assert "LABEL_UNSOUND" in text and "NOT on this packet" in text
    assert "keep the shipped geometry" in text
    # the new one
    assert "MEASURED ON THIS PACKET" in text
    assert "run 38880639079" in text
    assert "5 of 65" in text
    assert "0 of 3" in text
    assert "DO-NOT-SERVE this packet unchanged" in text
    assert "human_gate_ready stays false" in text
    # Claim ceiling, machine-checked the same way the Frontier team checks it:
    # no construction may assert what some specific decision IS.
    snap = _committed()
    for pattern in snap["forbidden_construction_patterns"]:
        assert re.search(pattern, text, re.IGNORECASE) is None, (
            f"owner card violates the adopted claim ceiling: {pattern}")


def test_the_adoption_never_rewrites_the_frozen_packet():
    """The frozen packet keeps its own build-time disclosures; the adoption is
    card + product snapshot only, so byte identity still verifies."""
    disclosures = json.loads(
        (PACKET / "disclosures.json").read_text(encoding="utf-8"))
    adoption = disclosures["frontier_verdict_adoption"]
    assert adoption["published"] is True
    assert set(k for k in adoption
               if k.startswith("frontier_")) == {
        "frontier_counter_label_integrity", "frontier_map_semantics"}
    assert adoption["frontier_counter_label_integrity"]["covers_this_packet"] is False
    assert adoption["frontier_map_semantics"]["covers_this_packet"] is False
    # ... and the packet still verifies byte-for-byte.
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(PRODUCT / "gate_packet.py"), "verify",
         "--packet", str(PACKET)],
        capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert proc.returncode == 0, proc.stdout + proc.stderr
