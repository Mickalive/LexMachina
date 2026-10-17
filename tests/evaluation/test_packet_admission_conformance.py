"""Packet-admission conformance gate: predicate semantics, binding, exit codes.

The gate under test asks whether direction v50's invariant is executably true:
no accepted product record may carry ready_for_owner_session/human_gate_ready
true while an accepted frozen bar is unmet.  Nothing here re-scores a rubric,
re-measures a Frontier candidate or asserts a new threshold.

Integration tests that need the accepted product mount SKIP when it is absent
(never fail): the core predicate, binding and exit-code semantics are covered
by mount-free unit tests so this file stays green in any container.
"""
import ast
import inspect
import json
from pathlib import Path

import pytest

from evaluation import packet_admission_conformance as pac

MOUNT = Path("/tmp/lex_accepted/product")
MOUNT_AVAILABLE = MOUNT.is_dir()
needs_mount = pytest.mark.skipif(not MOUNT_AVAILABLE, reason="accepted product mount absent")

REPO = Path(".")

# --------------------------------------------------------------------------- #
# N4: the frozen rubric identities the direction pins
# --------------------------------------------------------------------------- #
def test_rules_identity_rehashes_to_direction_pinned_shas():
    identity = pac.rules_identity()
    assert identity["rules_label_sha256"] == pac.EXPECTED_RULES_LABEL_SHA256
    assert identity["rules_geometry_sha256"] == pac.EXPECTED_RULES_GEOMETRY_SHA256
    assert identity["match"] is True


def test_vendored_and_gate_modules_are_byte_unchanged():
    """The two accepted gates this cycle must remain byte-identical."""
    from evaluation.frozen_bars.run_bar_gates import EXPECTED_BUNDLE_SHA256  # noqa: F401
    for name in ("label_gate.py", "geometry_gate.py", "run_bar_gates.py"):
        assert (REPO / "evaluation/frozen_bars" / name).is_file()


# --------------------------------------------------------------------------- #
# Frozen predicate: N1 must fire, N2/N3 must not
# --------------------------------------------------------------------------- #
def test_n1_positive_must_fire():
    assert pac._is_violation(True, True, False) is True


def test_n2_negative_must_not_fire():
    assert pac._is_violation(False, True, False) is False


def test_n3_negative_must_not_fire_not_a_tautology():
    assert pac._is_violation(True, False, False) is False


def test_n3b_persisted_block_rescues_under_the_frozen_rule():
    """Frozen metric includes 'no admission block on the record'."""
    assert pac._is_violation(True, True, True) is False


def test_non_vacuity_battery_all_hold_on_this_tree():
    battery = pac.non_vacuity_battery(pac.rules_identity())
    assert battery["all_hold"] is True
    assert battery["n_holding"] == battery["n_controls"] == 4


def test_battery_suppression_is_honest_about_a_broken_identity(monkeypatch):
    broken = dict(pac.rules_identity())
    broken["match"] = False
    battery = pac.non_vacuity_battery(broken)
    assert battery["all_hold"] is False
    assert [c["id"] for c in battery["controls"] if not c["holds"]] == ["N4_rules_identity"]


# --------------------------------------------------------------------------- #
# Claim walk and deterministic packet binding
# --------------------------------------------------------------------------- #
def test_walk_claims_finds_true_only_with_paths():
    obj = {"a": {"ready_for_owner_session": True, "n": 1},
           "b": [{"human_gate_ready": False}, {"ready_for_owner_session": True}]}
    hits = pac.walk_claims(obj)
    assert {(h["key"], h["json_path"]) for h in hits} == {
        ("ready_for_owner_session", "a.ready_for_owner_session"),
        ("ready_for_owner_session", "b.1.ready_for_owner_session"),
    }
    assert all(h["key"] in pac.CLAIM_KEYS for h in hits)


def test_bind_via_ancestors_uses_owning_object_first():
    root = {"v52": {"item": {"measured": {"ready_for_owner_session": True,
                                          "verify": "x --packet results/product/gate_packet/38812599575 -> ok"}}}}
    pid, how = pac._bind_via_ancestors(["v52", "item", "measured"], root)
    assert pid == "38812599575"
    assert how == "bound_via_enclosing_object"


def test_bind_via_ancestors_ambiguity_walks_up_not_down():
    """Two ids at the owning level => that level is ambiguous; root decides."""
    root = {"packet": "results/product/gate_packet/AAA/",
            "other": "see results/product/gate_packet/BBB/ too",
            "measured": {"ready_for_owner_session": True}}
    pid, how = pac._bind_via_ancestors(["measured"], root)
    assert pid is None
    assert how == "unbound_no_unique_gate_packet_id"


def test_bind_via_ancestors_unbound_when_no_unique_id_anywhere():
    pid, how = pac._bind_via_ancestors([], {"ready_for_owner_session": True})
    assert pid is None and how == "unbound_no_unique_gate_packet_id"


def test_packet_id_from_file_reads_gate_packet_dir():
    p = MOUNT / "results/product/gate_packet/38839347028/packet.json"
    assert pac._packet_id_from_file(p, MOUNT) == "38839347028"
    assert pac._packet_id_from_file(MOUNT / "state/product.json", MOUNT) is None


# --------------------------------------------------------------------------- #
# Metric evaluation: violation counting, unbound and incoherent buckets
# --------------------------------------------------------------------------- #
BAR_STATUS = {
    "P1": {"packet_id": "P1", "label_absolute_status": "LABEL_UNSOUND",
           "geometry_absolute_status": "GEOMETRY_UNSOUND", "label_n_scored": 9,
           "label_n_supported": 1, "geometry_per_bundle_counts": {}, "bars_unmet": True,
           "source": "synthetic", "recomputed_by_this_benchmark": False},
    "P2": {"packet_id": "P2", "label_absolute_status": "LABEL_SOUND",
           "geometry_absolute_status": "GEOMETRY_SOUND", "label_n_scored": 9,
           "label_n_supported": 9, "geometry_per_bundle_counts": {}, "bars_unmet": False,
           "source": "synthetic", "recomputed_by_this_benchmark": False},
}


def _claim(pid=None, block=False):
    return {"file": "x.json", "key": "ready_for_owner_session", "json_path": "r",
            "owning_object_path": "r", "packet_id": pid, "packet_binding": "synthetic",
            "admission_block_present_on_owning_record": block, "file_sha256": "0"}


def test_evaluate_counts_violation_only_when_bound_and_unmet():
    out = pac.evaluate_claims([_claim("P1")], BAR_STATUS)
    assert out["n_violations"] == 1
    assert out["violations"][0]["bar_status"]["bars_unmet"] is True
    assert out["violations"][0]["bar_status"]["recomputed"] is False


def test_evaluate_does_not_count_bars_met():
    out = pac.evaluate_claims([_claim("P2")], BAR_STATUS)
    assert out["n_violations"] == 0


def test_evaluate_reports_unbound_without_counting():
    out = pac.evaluate_claims([_claim(None)], BAR_STATUS)
    assert out["n_violations"] == 0
    assert out["n_unbound_claims_reported_not_counted"] == 1


def test_evaluate_reports_incoherent_claim_with_persisted_block():
    out = pac.evaluate_claims([_claim("P1", block=True)], BAR_STATUS)
    assert out["n_violations"] == 0
    assert out["n_incoherent_claims_reported_not_counted"] == 1


# --------------------------------------------------------------------------- #
# Module hygiene: stdlib-only, no Product import, no audit authoring
# --------------------------------------------------------------------------- #
def test_module_imports_no_product_code():
    source = inspect.getsource(pac)
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "product" not in imported


def test_module_never_authors_an_audit_artifact():
    source = inspect.getsource(pac)
    assert '"results/audit' not in source
    assert '"reports/audit' not in source


def test_hypothesis_is_frozen_and_predates_the_module():
    """RESEARCH_PROTOCOL step 4: the claim-bearing hypothesis is frozen first."""
    run = "39010105493"
    path = REPO / "results/evaluation/packet_admission_conformance" / f"FROZEN_HYPOTHESIS_{run}.json"
    assert path.is_file()
    hyp = json.loads(path.read_text())
    assert hyp["frozen_before_implementation"] is True
    assert hyp["frozen_before_execution"] is True
    assert hyp["success_rule_frozen"]["never_changed_after_execution"] is True
    assert "honest_pre_freeze_disclosure" in hyp


def test_frozen_hypothesis_names_the_pinned_bar_shas():
    hyp = json.loads(
        (REPO / "results/evaluation/packet_admission_conformance/FROZEN_HYPOTHESIS_39010105493.json")
        .read_text()
    )
    blob = json.dumps(hyp)
    assert pac.EXPECTED_RULES_LABEL_SHA256 in blob
    assert pac.EXPECTED_RULES_GEOMETRY_SHA256 in blob


# --------------------------------------------------------------------------- #
# Environment errors are exit 2, never a product verdict
# --------------------------------------------------------------------------- #
def test_missing_mount_is_environment_error(tmp_path):
    with pytest.raises(pac.EnvironmentError2):
        pac.collect_population(tmp_path / "nope")


def test_missing_bar_record_is_environment_error(tmp_path, monkeypatch):
    monkeypatch.setattr(pac, "_REPO_ROOT", tmp_path)
    with pytest.raises(pac.EnvironmentError2):
        pac.load_bar_status(tmp_path)


# --------------------------------------------------------------------------- #
# Integration (skip when the accepted product mount is absent)
# --------------------------------------------------------------------------- #
@needs_mount
def test_population_is_the_frozen_enumeration():
    claims, files = pac.collect_population(MOUNT)
    assert any(f.endswith("gate_packet/38839347028/packet.json") for f in files)
    assert "state/product.json" in files
    assert all(c["file_sha256"] for c in claims)


@needs_mount
def test_crosscheck_sources_agree_and_rehash_the_accepted_snapshot():
    crosscheck = pac.crosscheck_served_packet(MOUNT, pac.load_bar_status(REPO))
    assert crosscheck["sources_agree"] is True
    # accepted Frontier snapshot identity of record
    assert crosscheck["snapshot_sha256"] == (
        "511962a9232065667dc54a126f728a6da8dba1629752f4b81469d35a7e1a65e0"
    )


@needs_mount
def test_admission_block_is_absent_from_every_shipped_packet():
    presence = pac.admission_block_presence(MOUNT)
    assert presence["status"] == "MEASURED"
    for row in presence["packets"]:
        assert row["has_packet_admission"] is False
        assert row["has_packet_admission_blocked"] is False


@needs_mount
def test_product_own_gate_denies_readiness_black_box():
    """H5 positive control: the gate works; the defect class is non-application."""
    out = pac.run_product_admission_blackbox(MOUNT, enabled=True)
    assert out["status"] == "EXECUTED"
    assert out["returncode"] == 0
    assert out["ready_for_owner_session_allowed"] is False
    assert out["holds"] is True


@needs_mount
def test_full_run_is_deterministic_and_exit_agrees_with_verdict():
    rec1, code1 = pac.run("det-1", MOUNT, product_exec=False)
    rec2, code2 = pac.run("det-2", MOUNT, product_exec=False)
    strip = lambda r: {k: v for k, v in r.items()
                       if k not in ("run_id", "started_at_utc", "elapsed_s",
                                    "frozen_hypothesis")}
    assert strip(rec1) == strip(rec2)
    assert code1 == code2
    assert code1 in (0, 1)
    assert (rec1["verdict"] == "PACKET_ADMISSION_INVARIANT_VIOLATED") == (code1 == 1)
    assert rec1["violations_total"] == len(rec1["metric"]["violations"])
    assert rec1["served_packet_crosscheck"]["sources_agree"] is True
    assert rec1["non_vacuity_battery"]["all_hold"] is True


@needs_mount
def test_historical_falsification_reproduces_on_the_accepted_mount():
    """The accepted finding of record: the invariant is violated today.

    This asserts the CURRENT accepted state of the mount, not a permanent
    truth: if Product re-generates the shipped packets through the admission
    gate, this test is expected to go red and must be re-frozen with the new
    incumbents -- it is a measurement of record, not a product API contract.
    """
    rec, code = pac.run("39010105493", MOUNT, product_exec=False)
    assert code == 1
    assert rec["verdict"] == "PACKET_ADMISSION_INVARIANT_VIOLATED"
    assert {v["file"] for v in rec["metric"]["violations"]} == {
        "results/product/gate_packet/38812599575/packet.json",
        "results/product/gate_packet/38839347028/packet.json",
        "state/product.json",
    }


@needs_mount
def test_run_never_writes_an_audit_artifact(tmp_path):
    out = tmp_path / "rec.json"
    pac.main(["--run-id", "writes", "--mount", str(MOUNT), "--out", str(out),
              "--skip-product-exec"])
    assert out.is_file()
    assert not any((tmp_path / d).exists() for d in ("audit", "reports"))
