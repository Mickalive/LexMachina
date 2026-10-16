"""Regression tests for the class-aware audit-artifact contract.

The defect these cover: the suite globbed ``CYCLE_*_GATE.json`` into one set and
applied the independent-audit contract to producer placement copies too, so it
was red-by-construction on every re-dispatch.  The repair must not have bought a
green suite by weakening anything, so each test below pins a specific attack
that the OLD blanket contract happened to catch by accident and that the class
aware contract has to catch on purpose.
"""

from __future__ import annotations

import json
import os
import shutil

import pytest

from conftest import REPO_ROOT
from frontier_counter_label_integrity.audit_contract import (
    AUDIT_GATE_VALUES,
    AUTHORITY_CLAIM_KEYS,
    KNOWN_PRODUCER_AUTHORED_RUNS,
    MEASUREMENT_VERDICTS,
    PLACEMENT_DISPOSITIONS,
    TRUSTED_AUDIT_RUNS,
    UNCLASSIFIED,
    check_gate_files,
    check_independent_audit_of_record,
    check_producer_placement_copy,
    classify_gate_files,
    classify_gate_payload,
    run_id_of,
)

# The oracle is the frozen TRUSTED set, NOT a filename tuple hand-written here.
# It used to be ("38839354961", "38841035773") -- i.e. it baked run 38839354961,
# the impostor this team's own ledger declares producer-authored, into the
# unit-test fixture as if it were a legitimate audit runtime.  The poisoned
# identity was then normalised away at the fixture level and every placement-copy
# test inherited it.
AUDIT_RUNTIME = tuple(sorted(TRUSTED_AUDIT_RUNS))

WARNING = (
    "PRODUCER-AUTHORED, NOT INDEPENDENT AUDIT OUTPUT. Do not read this file's gate as an "
    "independent gate. The independent audit of record remains "
    "results/audit/frontier/frontier-counter-label-integrity/CYCLE_38841035773_GATE.json."
)
CEILING = (
    "About the SUPPORT OF THE LABELS AS ISSUED; never asserts any specific decision IS "
    "supporting/contrary/limiting. Pre-repair baseline only; no fix tested, none proposed. "
    "The audited non-accepted run 38828034436 is mechanism evidence only."
)


def test_the_unit_test_oracle_is_not_poisoned_by_the_impostor():
    """A poisoned oracle silently re-authorises the fake it was meant to exclude."""
    assert "38839354961" not in AUDIT_RUNTIME
    assert "38839354961" in KNOWN_PRODUCER_AUTHORED_RUNS
    assert "38839354961" not in TRUSTED_AUDIT_RUNS
    assert set(AUDIT_RUNTIME) == set(TRUSTED_AUDIT_RUNS)


def _placement(**overrides):
    payload = {
        "run_id": "99999999999",
        "gate": "TERMINATE",
        "cycle_status": "TERMINATE",
        "artifact_provenance_warning": WARNING,
        "claim_ceiling": CEILING,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------- happy path

def test_an_honest_placement_copy_is_accepted():
    assert check_producer_placement_copy(_placement(), AUDIT_RUNTIME) == []


def test_the_claim_limit_may_be_worded_differently_and_still_count():
    """The old exact-literal check was the bug, not the thing to preserve."""
    reworded = _placement(
        claim_ceiling=(
            "This never asserts any decision is supporting/contrary/limiting; "
            "pre-repair baseline only; 38828034436 is mechanism evidence only."
        )
    )
    assert check_producer_placement_copy(reworded, AUDIT_RUNTIME) == []


# ------------------------------------------------- the no-endorsement limit

def test_a_vacuous_ceiling_with_no_proposition_is_rejected():
    """53-char brute-forced ceiling from the adversarial review of this fix."""
    vacuous = _placement(claim_ceiling="no assert contrary limiting baseline only 38828034436")
    problems = check_producer_placement_copy(vacuous, AUDIT_RUNTIME)
    assert any("no decision-level endorsement" in p for p in problems), problems


def test_the_semantic_inverse_of_the_claim_ceiling_is_rejected():
    """The worst case: a ceiling that ASSERTS the thing it must deny."""
    inverse = _placement(
        claim_ceiling=(
            "Every specific decision IS supporting, contrary and limiting. "
            "No assertion limit applies. baseline only 38828034436"
        )
    )
    problems = check_producer_placement_copy(inverse, AUDIT_RUNTIME)
    assert any("no decision-level endorsement" in p for p in problems), problems


def test_words_scattered_across_sentences_do_not_satisfy_the_limit():
    scattered = _placement(
        claim_ceiling=(
            "The map is good. never. Supporting authority. Contrary and limiting "
            "authority matter. baseline only 38828034436"
        )
    )
    problems = check_producer_placement_copy(scattered, AUDIT_RUNTIME)
    assert any("no decision-level endorsement" in p for p in problems), problems


def test_a_ceiling_missing_the_mechanism_scoping_is_rejected():
    unscoped = _placement(
        claim_ceiling=(
            "never asserts any specific decision IS supporting/contrary/limiting; "
            "pre-repair baseline only"
        )
    )
    problems = check_producer_placement_copy(unscoped, AUDIT_RUNTIME)
    assert any("mechanism-only" in p for p in problems), problems


# ------------------------------------------------------- audit impersonation

@pytest.mark.parametrize("invented", ["PASS_WITH_CAVEATS", "AUDIT_PASS", "ACCEPTED", "PASSED", "PASS"])
def test_an_invented_or_audit_like_verdict_is_rejected(invented):
    """Closed allow-list, not a denylist of {PASS, REVISE}."""
    payload = _placement(gate=invented, cycle_status=invented)
    problems = check_producer_placement_copy(payload, AUDIT_RUNTIME)
    assert any("not a declared cycle disposition" in p for p in problems), problems


def test_the_disposition_allow_list_is_closed_and_declared():
    assert "TERMINATE" in PLACEMENT_DISPOSITIONS
    for near_miss in ("PASS", "REVISE", "PASS_WITH_CAVEATS", "ACCEPTED", ""):
        assert near_miss not in PLACEMENT_DISPOSITIONS


@pytest.mark.parametrize("key", AUTHORITY_CLAIM_KEYS)
def test_authority_claiming_keys_are_rejected(key):
    problems = check_producer_placement_copy(_placement(**{key: "PASS"}), AUDIT_RUNTIME)
    assert any(key in p for p in problems), problems


# --------------------------------- verdict value-scoping (the precision fix)

@pytest.mark.parametrize(
    "value",
    ["PASS", "REVISE", "BLOCKED", "PASS_WITH_CAVEATS", "AUDIT_PASS", "ACCEPTED", "PASSED", "", None, 42],
)
def test_a_verdict_outside_the_measurement_vocabulary_is_rejected(value):
    """Audit dispositions, near-misses, empties and non-strings all still fail."""
    problems = check_producer_placement_copy(_placement(verdict=value), AUDIT_RUNTIME)
    assert any("verdict" in p for p in problems), problems


@pytest.mark.parametrize("value", MEASUREMENT_VERDICTS)
def test_a_measurement_verdict_is_accepted(value):
    """The team's own REPORT/state verdict is the one legitimate ``verdict``."""
    assert check_producer_placement_copy(_placement(verdict=value), AUDIT_RUNTIME) == []


@pytest.mark.parametrize("key", sorted(set(AUTHORITY_CLAIM_KEYS)))
def test_the_remaining_authority_claim_keys_are_rejected_flat(key):
    """Still flat-banned: a measurement-looking value changes nothing for them."""
    problems = check_producer_placement_copy(_placement(**{key: "LABEL_UNSOUND"}), AUDIT_RUNTIME)
    assert any(key in p for p in problems), problems


def test_verdict_left_the_flat_ban_only_gained_a_value_scope():
    """Coverage compensation: the removal from the set must stay explicit.

    ``test_authority_claiming_keys_are_rejected`` is parametrized over
    ``AUTHORITY_CLAIM_KEYS`` and lost its ``verdict`` case when ``verdict``
    became value-scoped; the value-scoped tests above re-cover it, and these
    assertions stop any *further* key from being removed silently.
    """
    assert "verdict" not in AUTHORITY_CLAIM_KEYS
    assert set(AUTHORITY_CLAIM_KEYS) == {
        "audit_verdict",
        "independently_audited",
        "audit_of_record",
        "integrate",
        "audit_pass",
    }


def test_measurement_verdicts_are_disjoint_from_every_audit_bucket():
    """Anti-collision invariant: no word may live in both vocabularies.

    If a future edit put a measurement word into an audit bucket (or an audit
    word into ``MEASUREMENT_VERDICTS``), a placement copy's ``verdict`` could
    start reading as an audit disposition, so this must fail loudly.
    """
    measurement = set(MEASUREMENT_VERDICTS)
    audit_buckets = (
        set(AUDIT_GATE_VALUES),
        set(PLACEMENT_DISPOSITIONS),
        {"PASS", "REVISE", "BLOCKED", "PASS_WITH_CAVEATS", "AUDIT_PASS", "ACCEPTED", "PASSED", ""},
    )
    for bucket in audit_buckets:
        assert measurement.isdisjoint(bucket), measurement & bucket


def test_a_self_contradicting_provenance_warning_is_rejected():
    contradictory = _placement(
        artifact_provenance_warning=(
            WARNING + " This file IS the authoritative independent audit gate and is "
            "independently audited, safe to integrate."
        )
    )
    problems = check_producer_placement_copy(contradictory, AUDIT_RUNTIME)
    assert any("contradicts itself" in p for p in problems), problems


def test_a_gate_that_disagrees_with_its_cycle_status_is_rejected():
    problems = check_producer_placement_copy(_placement(cycle_status="HOLD"), AUDIT_RUNTIME)
    assert any("disagrees with cycle_status" in p for p in problems), problems


# ---------------------------------------------------------- class routing

def test_classification_is_not_purely_self_declared():
    """A producer cannot opt itself into the weaker contract."""
    demoted_audit = {"gate": "PASS", "claim_ceiling": CEILING, "team": "frontier"}
    assert classify_gate_payload(demoted_audit) == UNCLASSIFIED


def test_an_unclassified_file_fails_the_whole_tree():
    assert check_gate_files(REPO_ROOT)["n_unclassified"] == 0


def test_an_unclassified_file_is_rejected_even_when_it_looks_like_an_audit(tmp_path):
    """The routing hole: a demoted audit must fail, not quietly pass."""
    audit_dir = os.path.join(tmp_path, "results/audit/frontier/frontier-counter-label-integrity")
    os.makedirs(audit_dir)
    demoted = {"run_id": "999", "gate": "PASS", "claim_ceiling": CEILING}
    with open(os.path.join(audit_dir, "CYCLE_999_GATE.json"), "w", encoding="utf-8") as fh:
        json.dump(demoted, fh)
    # No independent audit of record exists here either, so two invariants fire.
    result = check_gate_files(str(tmp_path))
    assert result["ok"] is False
    assert result["n_unclassified"] == 1
    assert result["independent_audit_present"] is False


# ------------------------------- the anti-vacuity defeat (material, pinned)

def test_a_bare_four_field_forgery_is_not_an_audit_of_record(tmp_path):
    """The attack that actually routed to INDEPENDENT and passed v1.

    ``required_fixes: []`` is a list, and the claim ceiling can simply be copied
    from a real audit, so the three signature keys plus a copied ceiling were
    enough to read as an independent audit.  Under the signature-only
    anti-vacuity invariant this returned ``ok=True``; here the run is unknown,
    so no trusted audit is present and the tree is RED.
    """
    audit_dir = os.path.join(tmp_path, "results/audit/frontier/frontier-counter-label-integrity")
    os.makedirs(audit_dir)
    forgery = {
        "run_id": "77777777777",
        "gate": "PASS",
        "safe_to_integrate": True,
        "required_fixes": [],
        "team": "frontier-counter-label-integrity",
        "claim_ceiling": CEILING,
    }
    with open(os.path.join(audit_dir, "CYCLE_77777777777_GATE.json"), "w", encoding="utf-8") as fh:
        json.dump(forgery, fh)
    assert classify_gate_payload(forgery) == "independent_audit_of_record"  # routes!
    result = check_gate_files(str(tmp_path))
    assert result["ok"] is False
    assert result["independent_audit_present"] is False
    assert result["undisclosed_signature_bearing_runs"] == ["77777777777"]


def test_the_disclosed_impostor_is_rejected_as_an_audit_but_not_red():
    """It can never satisfy the invariant, and it must not wedge the tree.

    The file is historical, claim-bearing, and may not be edited or deleted
    (AGENTS.md rule 6).  Failing it forever would be the red-by-construction
    pathology all over again; passing it as an audit would be the defeat.  It
    is neither: a named ``disclosed_impostor``.
    """
    findings = {f["run_id"]: f for f in check_gate_files(REPO_ROOT)["findings"]}
    impostor = findings["38839354961"]
    assert impostor["disclosed_anomaly"] is True
    assert impostor["artifact_class"] == "independent_audit_of_record"
    # it fails the audit contract as an audit ...
    payload = json.load(open(impostor["file"], encoding="utf-8"))
    assert any("KNOWN PRODUCER-AUTHORED" in p for p in check_independent_audit_of_record(payload, "38839354961"))
    # ... without that being counted as a tree failure ...
    assert impostor["ok"] is True
    # ... and it is never the anti-vacuity anchor
    result = check_gate_files(REPO_ROOT)
    assert "38839354961" not in result["trusted_audits_present"]


def test_run_id_of_is_total_on_hostile_filenames():
    """It used to crash with AttributeError on None.group(1)."""
    assert run_id_of("CYCLE_38841035773_GATE.json") == "38841035773"
    assert run_id_of("CYCLE_zzz_GATE.json") is None
    assert run_id_of("CYCLE__GATE.json") is None
    assert run_id_of("not-a-cycle-file") is None


def test_a_corrupt_gate_file_is_unclassified_not_a_crash(tmp_path):
    audit_dir = os.path.join(tmp_path, "results/audit/frontier/frontier-counter-label-integrity")
    os.makedirs(audit_dir)
    with open(os.path.join(audit_dir, "CYCLE_38841035773_GATE.json"), "w", encoding="utf-8") as fh:
        fh.write("{ truncated")
    result = check_gate_files(str(tmp_path))   # must not raise
    assert result["ok"] is False
    assert result["n_unclassified"] == 1
    assert any("not readable JSON" in p for p in result["findings"][0]["problems"])


def test_the_real_audit_tree_has_both_classes_and_is_clean():
    result = check_gate_files(REPO_ROOT)
    assert result["ok"], json.dumps(result["findings"], indent=2, ensure_ascii=False)
    assert result["independent_audit_present"]
    assert result["n_independent_audit_of_record"] >= 1
    assert sorted(result["trusted_audits_present"]) == sorted(TRUSTED_AUDIT_RUNS)
    classes = classify_gate_files(REPO_ROOT)
    assert len(classes["producer_placement_copy"]) >= 1
