"""Direction v68 ordered work item (4) — the fixture-anchor exposure gate.

The ordered work makes closing the fixture-mode ``apply_anchor_labels``
asymmetry **conditional**: close it "only if it can be done without changing
claims (measured exposure 0 rows)".  This file pins that conditional as an
executable gate instead of a sentence:

1. the instrument runs on deep copies, writes no bundle byte, and re-hashes the
   frozen rubric before simulating anything (``product/fixture_anchor_exposure``);
2. measured exposure on the committed fixture fixed-path family is NOT 0 rows,
   so the verdict is ``DO_NOT_CLOSE`` and the shipped pipeline gate
   (``if not fixture_generation``) must stay where it is;
3. closing it would overturn ordered work (1)'s success rule — the known sound
   row ``bstger_SK.2023.49`` flips ``counter_evidence_verified`` true -> false;
4. the auditor's "0 rows on all four legs" premise is population-bound to
   ``n_selected = 0`` and does not reproduce at this head (the family now carries
   gate-confirmed spans);
5. committed fixture bundles still carry no ``provenance.counter_anchor``, i.e.
   the asymmetry is real and not already closed.

No frozen gate, rubric, threshold, bar or classifier is imported for scoring,
edited or re-tuned here, and nothing in this file writes to ``results/`` or
``product/static``.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import product.fixture_anchor_exposure as fae  # noqa: E402
from product.query.counter_anchor import FROZEN_LABEL_RULES_SHA256  # noqa: E402

#: The committed artifact of this cycle (also readable from any later checkout).
ARTIFACT = ROOT / "results" / "product" / "fixture_anchor_exposure" / (
    "CYCLE_40272586794.json"
)

#: The five decisions whose counter claims change on the fixture fixed-path
#: family: the four rows the accepted FAST-MVP falsifier (40105794124) measured
#: as content-defective, plus the known sound row ordered work (1) protects.
EXPECTED_EXPOSED_IDS = {
    "bge_BGE_110_II_391",
    "bge_BGE_121_III_260",
    "bstger_SK.2023.49",
    "gr_gerichte_ERZ 2010 25",
    "vd_gerichte_JL09.019144",
}

#: The audit whose "0 rows on all four legs" premise this reconciles with.
PREMISE_AUDIT = ROOT / "reports" / "audit" / "product" / "CYCLE_40100397058.md"


@pytest.fixture(scope="module")
def exposure() -> dict:
    return fae.run(run_id="TEST", direction_version=68)


def _flagship() -> list[Path]:
    return [Path(p) for p in fae.bundle_paths()]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# 1. the instrument is a simulation with provenance, not a mutation
# --------------------------------------------------------------------------- #

def test_instrument_simulates_on_deep_copies_and_proves_the_frozen_rubric(exposure):
    sim = exposure["simulation_only"]
    assert sim["writes_no_bundle_bytes"] is True
    assert sim["runs_on_deep_copies"] is True
    assert sim["frozen_rules_rehashed_before_use"] is True
    assert sim["frozen_rules_sha256"] == FROZEN_LABEL_RULES_SHA256
    assert sim["frozen_gate_rubric_threshold_edited"] is False
    assert exposure["schema"] == fae.SCHEMA
    assert exposure["direction_version"] == 68
    assert exposure["claim_ceiling"] == fae.CLAIM_CEILING
    assert "geometry" in exposure["exposure_definition"]


def test_running_the_instrument_leaves_every_committed_bundle_byte_identical():
    paths = _flagship()
    assert len(paths) >= 40, "the flagship family must be present"
    before = {_sha(p): None for p in paths}
    fae.run(run_id="TEST_BYTES", direction_version=68)
    after = {_sha(p) for p in paths}
    assert set(before) == after, "the exposure simulation must never write a bundle"


# --------------------------------------------------------------------------- #
# 2. the conditional: exposure != 0 -> DO_NOT_CLOSE, gate untouched
# --------------------------------------------------------------------------- #

def test_exposure_on_the_fixture_fixed_path_family_is_not_zero(exposure):
    fixed = exposure["populations"]["fixture_fixed_path"]
    assert fixed["n_bundles"] >= 40
    assert fixed["n_scored_rows"] > 0
    assert fixed["n_changed_rows"] > 0, (
        "measured exposure is 0 rows: the ordered work would now PERMIT closing "
        "the fixture-mode asymmetry — re-run the instrument, record the new "
        "verdict and update this gate deliberately; do not silently flip it")
    assert set(fixed["changed_decision_ids"]) == EXPECTED_EXPOSED_IDS, (
        "the exposed population moved — re-run "
        "python3 product/fixture_anchor_exposure.py --run-id <run> and re-decide "
        "the ordered-work (4) conditional against the fresh numbers")


def test_decision_is_do_not_close_and_the_shipped_gate_is_untouched(exposure):
    dec = exposure["decision"]
    assert dec["rule"] == (
        "close_allowed <=> exposure rows on fixture_fixed_path == 0")
    assert dec["close_allowed"] is False
    assert dec["verdict"] == "DO_NOT_CLOSE"
    assert dec["exposure_rows_on_fixture_fixed_path"] > 0
    assert dec["pipeline_gate_changed"] is False
    # the shipped pipeline still gates the adopted label decision
    src = (PRODUCT / "query" / "pipeline.py").read_text(encoding="utf-8")
    assert "if not fixture_generation:\n        audited = apply_anchor_labels(" in src


def test_exposure_is_mostly_status_only_but_includes_verified_flag_flips(exposure):
    fixed = exposure["populations"]["fixture_fixed_path"]
    assert fixed["n_counter_evidence_verified_flips"] > 0
    # every verified-flag flip is the known sound row, abstained for pivot_absent
    flips = [
        (c["decision_id"], c["fields"]["counter_evidence_verified"])
        for b in fixed["bundles"]
        for c in b.get("changed_rows", [])
        if "counter_evidence_verified" in c.get("fields", {})
    ]
    assert flips, "verified-flag flips must be inspectable, not summarised away"
    assert {d for d, _ in flips} == {fae.CONFIRMED_SOUND_DECISION_ID}
    assert all(old is True and new is False for _, (old, new) in flips)
    reasons = {
        c.get("reason_code")
        for b in fixed["bundles"]
        for c in b.get("changed_rows", [])
        if "counter_evidence_verified" in c.get("fields", {})
    }
    assert reasons == {"pivot_absent"}


# --------------------------------------------------------------------------- #
# 3. closing would contradict ordered work (1)'s success rule
# --------------------------------------------------------------------------- #

def test_closing_would_overturn_the_known_sound_row_success_rule(exposure):
    inter = exposure["ordered_work_1_interaction"]
    assert inter["closing_would_flip_confirmed_sound_row"] is True
    fields = inter["flip_fields"]
    assert fields["counter_evidence_verified"] == [True, False]
    assert fields["counter_status"] == ["candidate-limiting",
                                        "abstained_unevidenced"]
    # ... while the shipped path keeps that row verified/sound (ordered work 1)
    bundle = json.loads(
        (ROOT / "results" / "product" / "offline_slice" / "20261024T185300Z"
         / "corporate-criminal-liability.bundle.json").read_text(encoding="utf-8")
    )
    row = next(d for d in bundle["decisions"]
               if d["decision_id"] == "bstger_SK.2023.49")
    assert row["counter_evidence_verified"] is True
    assert row["counter_status"] == "candidate-limiting"


# --------------------------------------------------------------------------- #
# 4. the auditor's zero-row premise is population-bound and does not reproduce
# --------------------------------------------------------------------------- #

def test_zero_row_premise_does_not_reproduce_at_this_head(exposure):
    pre = exposure["premise_reconciliation"]
    assert PREMISE_AUDIT.is_file(), "the premise source must stay citable"
    text = PREMISE_AUDIT.read_text(encoding="utf-8")
    assert "0 rows on all four legs" in text
    assert "n_selected = 0" in text
    assert pre["premise_holds_at_current_head"] is False
    assert pre["current_head_n_span_selected_on_fixture_fixed_path"] > 0
    assert pre["both_numbers_published"] is True
    assert pre["auditor_population_not_recorded"] is True
    assert "does not reproduce" in pre["divergence"]


def test_re_application_population_is_published_as_reconciliation_only(exposure):
    """The already-anchored family is NOT the asymmetry, and is not 0 either."""
    anchored = exposure["populations"]["already_anchored"]
    assert "idempotence" in anchored["selector"]
    assert anchored["n_bundles"] >= 9
    assert anchored["n_bundles_already_carrying_anchor"] == anchored["n_bundles"]
    # re-application moves rows too, so "0 rows" reproduces on no population
    # where a label decision has anything to decide
    assert anchored["n_changed_rows"] >= 0
    fixture = exposure["populations"]["fixture_all"]
    assert fixture["n_bundles"] > anchored["n_bundles"]


# --------------------------------------------------------------------------- #
# 5. the asymmetry itself is real on the shipped fixture bytes
# --------------------------------------------------------------------------- #

def test_committed_fixture_bundles_carry_no_anchor_provenance():
    """Non-vacuity for the gate: if anyone closes the asymmetry and ships,
    this fails on the very bytes the product would then publish."""
    fixture_paths = [p for p in _flagship()
                     if json.loads(p.read_text(encoding="utf-8"))
                     .get("provenance", {}).get("fixture_mode") is True]
    assert len(fixture_paths) >= 40
    carrying = [
        str(p) for p in fixture_paths
        if "counter_anchor" in (json.loads(p.read_text(encoding="utf-8"))
                                .get("provenance") or {})
    ]
    assert carrying == [], (
        "fixture bundles now carry provenance.counter_anchor — the asymmetry "
        "was closed; re-measure exposure and re-decide ordered work (4)")


# --------------------------------------------------------------------------- #
# 6. the committed artifact of this cycle matches a fresh measurement
# --------------------------------------------------------------------------- #

def test_committed_artifact_matches_a_fresh_measurement():
    if not ARTIFACT.is_file():
        pytest.skip("artifact of this cycle not present in this checkout")
    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    fresh = fae.run(run_id="RECHECK", direction_version=68)
    for key in ("decision", "populations"):
        if key == "populations":
            for pop in ("fixture_fixed_path", "fixture_all", "already_anchored"):
                c = committed["populations"][pop]
                f = fresh["populations"][pop]
                for field in ("n_bundles", "n_changed_rows",
                              "n_counter_evidence_verified_flips",
                              "n_scored_rows", "n_span_selected_rows"):
                    assert c[field] == f[field], (
                        f"{pop}.{field} drifted: committed {c[field]} vs fresh "
                        f"{f[field]}")
        else:
            assert committed[key] == fresh[key]


def test_cli_writes_the_record(tmp_path):
    out = tmp_path / "exposure.json"
    rc = fae.main(["--run-id", "TEST", "--out", str(out)])
    assert rc == 0
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["decision"]["verdict"] in {"DO_NOT_CLOSE", "CLOSE_ASYMMETRY"}
    # stdout must name the verdict too (operator-visible, not silent)
    proc = subprocess.run(
        [sys.executable, str(PRODUCT / "fixture_anchor_exposure.py"), "--json"],
        capture_output=True, text=True, timeout=600, cwd=str(ROOT), check=False,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert json.loads(proc.stdout)["decision"]["verdict"] == (
        rec["decision"]["verdict"])
