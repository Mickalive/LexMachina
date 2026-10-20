"""OPERATIONAL RESUME regression guards (run 39426324296 vs published run 39422328377).

Deterministic, offline, read-only. Every published claim-bearing artifact must
remain byte-stable, the resume cycle must have reproduced it exactly, and the
frozen honesty invariants (state, rules, rubric, absolute bar) must hold as
published -- never as re-derived.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT, requires_accepted
from frontier_counter_label_emission.classifier_bridge import (
    verify_classifier_and_rubric,
)

RESULTS = REPO_ROOT / "results" / "frontier" / "frontier-counter-label-emission"
PUBLISHED_RUN = RESULTS / "run_39422328377"
RESUME_RUN = RESULTS / "run_39426324296"

STATE_PATH = REPO_ROOT / "state" / "frontier" / "frontier-counter-label-emission.json"
TEAM_RULES_PATH = REPO_ROOT / "frontier" / "frontier-counter-label-emission" / "RULES.json"
RULES_FROZEN_COMMIT = "d20a3edd"

# Computed NOW from the frozen team rules file and pinned here on purpose.
TEAM_RULES_SHA256_PIN = (
    "9837dec0137bc6f76a0b482d5f1e17d08d90d296136513acc12478d073439458"
)
# Frozen product rubric (RULES_LABEL.json) sha256 of record.
FROZEN_RUBRIC_SHA256_PIN = (
    "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
)
CLASSIFIER_ANCHOR_PIN = "d256e2749f4aef838ba51accd99512bff7ad5f61372225cbf997d2b1110b66b9"
CLASSIFIER_RUBRIC_PIN = "f43698da8b333d8c272eb3f064997a126caf47da202125520602d99a6cf01819"

BUNDLES = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
PUBLISHED_PINNED_FILES = (
    "ATTRIBUTION.json",
    "DETERMINISM.json",
    "EMISSION.json",
    "MEASUREMENT_SUMMARY.json",
    "NON_VACUITY.json",
)
NEVER_PASS_STATUSES = frozenset({"NOT_APPLICABLE", "NOT_MEASURED"})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _state_flag(state: dict, name: str):
    """Read a promotion flag from promotion_status or the top level, but not nowhere."""
    promotion_status = state.get("promotion_status") or {}
    if name in promotion_status:
        return promotion_status[name]
    assert name in state, f"state is missing {name!r}"
    return state[name]


def _committed_rules_blob() -> bytes | None:
    """Frozen rules bytes from the freeze commit, or None if the commit is absent."""
    try:
        proc = subprocess.run(
            ["git", "cat-file", "-p", f"{RULES_FROZEN_COMMIT}:frontier/"
                                      "frontier-counter-label-emission/RULES.json"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def test_published_run_artifacts_match_pinned_digests():
    """(1) run_39422328377 measurement artifacts are byte-identical to their pins."""
    digests = _load(PUBLISHED_RUN / "ARTIFACT_DIGESTS.json")
    assert sorted(digests) == sorted(PUBLISHED_PINNED_FILES)
    for name in PUBLISHED_PINNED_FILES:
        path = PUBLISHED_RUN / name
        assert path.is_file(), f"missing published artifact {name}"
        assert _sha256(path) == digests[name], f"{name} drifted from its published pin"


def test_resume_run_reproduces_published_bytes_exactly():
    """(2) run_39426324296 artifacts are byte-identical to the published digests."""
    published_digests = _load(PUBLISHED_RUN / "ARTIFACT_DIGESTS.json")
    resume_digests_path = RESUME_RUN / "ARTIFACT_DIGESTS.json"
    assert resume_digests_path.is_file(), "resume run has no ARTIFACT_DIGESTS.json"
    # The resume run must publish the very same digest manifest, byte for byte.
    assert resume_digests_path.read_bytes() == (PUBLISHED_RUN / "ARTIFACT_DIGESTS.json").read_bytes()
    resume_digests = _load(resume_digests_path)
    assert resume_digests == published_digests
    for name in PUBLISHED_PINNED_FILES:
        path = RESUME_RUN / name
        assert path.is_file(), f"resume run is missing {name}"
        assert _sha256(path) == published_digests[name], (
            f"resume artifact {name} is not byte-identical to the published record"
        )


def test_state_invariants_hold_at_test_time():
    """(3) charter v1 promoted/terminated state invariants, re-read at test time."""
    state = _load(STATE_PATH)
    assert state["charter_version"] == 1
    assert state["cycle_status"] == "PROMOTED"
    assert state["evidence_tier"] == "ACCEPTED"
    assert state["continue_recommended"] is False
    promotion_status = state["promotion_status"]
    assert promotion_status["outcome"] == "A_EMISSION_RECOVERED"
    assert _state_flag(state, "serve_recommendation") is None
    assert _state_flag(state, "human_gate_ready_touched") is False
    assert _state_flag(state, "owner_card") is False
    assert _state_flag(state, "ready_for_owner_session") is False


def test_frozen_team_rules_are_byte_stable():
    """(4) RULES.json sha256 is pinned now and matches the freeze commit when present."""
    actual = _sha256(TEAM_RULES_PATH)
    assert actual == TEAM_RULES_SHA256_PIN, "frozen team RULES.json bytes changed"
    _load(TEAM_RULES_PATH)  # must still be valid JSON
    committed = _committed_rules_blob()
    if committed is None:
        pytest.skip("freeze commit d20a3edd not available in this clone")
    assert committed == TEAM_RULES_PATH.read_bytes(), (
        "committed freeze bytes differ from the working-tree RULES.json"
    )


@requires_accepted
def test_frozen_rubric_pin_matches(rules_path: Path):
    """(5) RULES_LABEL.json sha256 equals the frozen pin of record."""
    assert _sha256(rules_path) == FROZEN_RUBRIC_SHA256_PIN


@requires_accepted
def test_classifier_critical_pins_verify():
    """(6) team bridge re-hashes the accepted classifier: ok, anchor + rubric pins."""
    rec = verify_classifier_and_rubric()
    assert rec["ok"] is True, rec
    assert rec["frozen_rules_ok"] is True
    assert rec["frozen_rules_sha256_actual"] == FROZEN_RUBRIC_SHA256_PIN
    actuals = {f["relpath"]: f["actual"] for f in rec["classifier_files"]}
    anchor = [v for k, v in actuals.items() if k.endswith("counter_anchor_classifier.py")]
    rubric = [v for k, v in actuals.items() if k.endswith("vendored/rubric.py")]
    assert anchor == [CLASSIFIER_ANCHOR_PIN], "critical anchor classifier pin mismatch"
    assert rubric == [CLASSIFIER_RUBRIC_PIN], "critical vendored rubric pin mismatch"


def test_integration_contract_is_complete():
    """(7) contract carries 4 product entries, the evaluation cross-check, invariants."""
    contract = _load(PUBLISHED_RUN / "INTEGRATION_CONTRACT.json")
    assert contract["schema"] == "frontier-counter-label-emission-integration-contract/1"
    assert contract["team_id"] == "frontier-counter-label-emission"
    assert contract["charter_version"] == 1
    assert contract["github_run_id"] == "39422328377"
    assert contract["promotion_outcome"] == "A_EMISSION_RECOVERED"

    product = contract["what_product_must_consume"]
    assert set(product) == {
        "1_attribution_record",
        "2_emission_module",
        "3_determinism_disclosure",
        "4_measurement_summary",
    }
    assert "file" in product["1_attribution_record"]
    assert "integration_point" in product["2_emission_module"]
    assert "file" in product["3_determinism_disclosure"]
    assert "file" in product["4_measurement_summary"]

    cross = contract["what_evaluation_must_cross_check"]
    assert set(cross) == {
        "input_hashes",
        "classifier_config",
        "absolute_bar",
        "determinism",
        "non_vacuity",
        "support_among_issued",
    }

    invariants = contract["invariants_this_team_never_breaks"]
    assert isinstance(invariants, list)
    assert len(invariants) == 7
    assert all(isinstance(item, str) and item for item in invariants)


def test_determinism_and_non_vacuity_records():
    """(8) published determinism identical>=3 runs and both non-vacuity controls."""
    determinism = _load(PUBLISHED_RUN / "DETERMINISM.json")["determinism"]
    non_vacuity = _load(PUBLISHED_RUN / "NON_VACUITY.json")["non_vacuity"]
    assert set(determinism) == set(BUNDLES)
    assert set(non_vacuity) == set(BUNDLES)
    for qid in BUNDLES:
        det = determinism[qid]
        assert det["identical"] is True, f"{qid} determinism not identical"
        assert det["n_runs"] >= 3, f"{qid} n_runs below the 3-run floor"
        assert det["differing_rows"] == []
        nv = non_vacuity[qid]
        assert nv["seeded_control"]["pass"] is True, f"{qid} seeded control failed"
        assert nv["negative_control"]["pass"] is True, f"{qid} negative control failed"
        assert nv["non_vacuity_pass"] is True, f"{qid} non-vacuity failed"


def test_absolute_bar_after_state_is_honest():
    """(9) after-state statuses as published; NOT_APPLICABLE/NOT_MEASURED never pass."""
    emission = _load(RESUME_RUN / "EMISSION.json")["emission"]
    assert set(emission) == set(BUNDLES)
    expected_after = {
        "de-kapitalverletzung": "LABEL_UNSOUND",
        "fr-bail-entretien": "LABEL_UNSOUND",
        "it-responsabilita-medica": "INSUFFICIENT_POPULATION",
    }
    for qid in BUNDLES:
        phases = emission[qid]
        after = phases["after"]["absolute_bar_status"]
        assert after["status"] == expected_after[qid], f"{qid} after status drifted"
        assert after["satisfied"] is False, f"{qid} after-state claims the bar is met"
        assert after["as_written"] is True
        assert after["absolute_bar"] == 1.0
        assert after["not_applicable_never_a_pass"] is True
        assert after["not_measured_never_a_pass"] is True
        for phase_name, payload in phases.items():
            if not isinstance(payload, dict):
                continue
            status = payload.get("absolute_bar_status")
            if not isinstance(status, dict):
                continue
            assert status["status"] in {
                "LABEL_UNSOUND",
                "INSUFFICIENT_POPULATION",
                "NOT_APPLICABLE",
                "NOT_MEASURED",
            }, f"{qid}/{phase_name} unexpected status {status['status']!r}"
            if status["status"] in NEVER_PASS_STATUSES:
                assert status["satisfied"] is False, (
                    f"{qid}/{phase_name} {status['status']} recorded as satisfied"
                )
