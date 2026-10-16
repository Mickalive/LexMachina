"""Regression guard for the audit-required report correction of cycle 38831241913.

The independent audit of repair run 38831241913 returned gate=REVISE with two
required fixes, both of them **report text**: a sentence claiming
``bge_115 II 78`` was re-retrieved and cited a "real contrary passage", and a
sentence claiming ``bge_115 II 108`` was "now unlabelled".  The committed
bundles say both rows are simply absent, and the quoted BARBEY sentence was
never the row's cited ``counter_evidence`` — it only exists somewhere inside the
row's ``full_text`` in the OLD bundle.

Code and artifacts were sound; what was missing was a **check that a prose claim
about an artifact matches the artifact**.  These tests provide it:

* the row table is recomputed from the two bundle files, never from the report;
* the recomputation must agree with the recorded ``MEASUREMENT.json`` (so the two
  cannot silently drift);
* the two defective sentences must not reappear in the report, unstruck;
* ``passage_support`` must keep distinguishing "inside full_text" from "this is
  the cited evidence", which is the exact distinction the false claim collapsed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from product.query import row_tracking as rt

REPO = Path(__file__).resolve().parents[2]
OLD_DIR = REPO / "results/product/adversarial_retrieval/38828034436"
NEW_DIR = REPO / "results/product/adversarial_retrieval/38831241913"
REPORT = REPO / "reports/product/CYCLE_38831241913.md"
LANGS = ("de", "fr", "it")

#: The passage the report quoted as the "real contrary passage" of bge_115 II 78.
BARBEY_QUOTE = "il est douteux, contrairement à l'opinion de BARBEY"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _row(rows: list[dict], decision_id: str) -> dict:
    return next(r for r in rows if r["decision_id"] == decision_id)


@pytest.fixture(scope="module")
def fr_pairs() -> tuple[dict, dict]:
    return (_load(OLD_DIR / "bundle_fr.json"), _load(NEW_DIR / "bundle_fr_repaired.json"))


@pytest.fixture(scope="module")
def fr_rows(fr_pairs) -> list[dict]:
    return rt.track_all(*fr_pairs, relabel_rows=_load(NEW_DIR / "relabel_fr_old_rows.json"))


def test_bge_115_II_78_is_absent_from_the_repaired_fr_bundle(fr_rows):
    """The audit's required_fixes[0]: the row is not re-retrieved at all."""
    row = _row(fr_rows, "bge_115 II 78")
    assert row["in_old_bundle"] is True
    assert row["old_status"] == "candidate-contrary"
    assert row["in_repaired_bundle"] is False
    assert row["in_repaired_adversarial_rows"] is False
    assert row["repaired_status"] is None


def test_bge_115_II_108_is_absent_from_the_repaired_fr_bundle(fr_rows):
    """The audit's required_fixes[1]: 'now unlabelled' misdescribed an absence."""
    row = _row(fr_rows, "bge_115 II 108")
    assert row["in_old_bundle"] is True
    assert row["old_status"] == "candidate-limiting"
    assert row["in_repaired_bundle"] is False
    assert row["repaired_status"] is None


def test_the_barbey_passage_is_inside_the_old_full_text_but_was_never_cited(fr_pairs):
    """The quotation is real text and is NOT evidence for any label."""
    old, _new = fr_pairs
    row = rt.index_rows(old)["bge_115 II 78"]
    support = rt.passage_support(row, BARBEY_QUOTE)
    assert support["row_present"] is True
    assert support["in_full_text"] is True
    assert support["is_cited_evidence"] is False
    # and the evidence that WAS cited is the disposal sentence D2 removed
    assert "rejeté le recours" in str(row.get("counter_evidence"))


def test_passage_support_says_no_for_an_absent_row(fr_pairs):
    old, new = fr_pairs
    assert rt.passage_support(None, BARBEY_QUOTE) == {
        "row_present": False, "in_full_text": False, "is_cited_evidence": False,
    }
    assert rt.passage_support(rt.index_rows(new).get("bge_115 II 78"), BARBEY_QUOTE) == {
        "row_present": False, "in_full_text": False, "is_cited_evidence": False,
    }


@pytest.mark.parametrize("lang", LANGS)
def test_presence_and_channel_are_reported_separately(lang):
    """The definitional ambiguity that let the report slip: 're-retrieved' means
    'in the adversarial-channel rows', not 'on the map'.  DE proves the two
    differ: bge_136 III 190 is on the repaired DE map carrying candidate-limiting
    yet has no adversarial_channel."""
    rows = rt.track_all(_load(OLD_DIR / f"bundle_{lang}.json"),
                        _load(NEW_DIR / f"bundle_{lang}_repaired.json"),
                        relabel_rows=_load(NEW_DIR / f"relabel_{lang}_old_rows.json"))
    for row in rows:
        assert row["in_repaired_bundle"] >= row["in_repaired_adversarial_rows"]
        if row["in_repaired_adversarial_rows"]:
            assert row["re_retrieved_now"] is True
            assert row["repaired_adversarial_channel"]
    de = {r["decision_id"]: r for r in
          rt.track_all(_load(OLD_DIR / "bundle_de.json"), _load(NEW_DIR / "bundle_de_repaired.json"))}
    assert de["bge_136 III 190"]["in_repaired_bundle"] is True
    assert de["bge_136 III 190"]["in_repaired_adversarial_rows"] is False


@pytest.mark.parametrize("lang", LANGS)
def test_recomputation_agrees_with_the_recorded_measurement(lang):
    """MEASUREMENT.json cannot drift away from the bundles it was derived from."""
    rows = rt.track_all(_load(OLD_DIR / f"bundle_{lang}.json"),
                        _load(NEW_DIR / f"bundle_{lang}_repaired.json"),
                        relabel_rows=_load(NEW_DIR / f"relabel_{lang}_old_rows.json"))
    entry = _load(NEW_DIR / "MEASUREMENT.json")["bundles"][lang]
    check = rt.compare_with_measurement(rows, entry)
    assert check["differences"] == []
    assert check["agrees"] is True
    # nothing was skipped: every tracked id carried all four comparable fields
    assert check["not_compared"] == []
    assert check["n_recorded"] == len(rt.AUDIT_INVERTED_IDS)


def test_the_off_domain_row_is_reported_as_unrecorded_not_as_a_mismatch():
    rows = rt.track_all(_load(OLD_DIR / "bundle_fr.json"),
                        _load(NEW_DIR / "bundle_fr_repaired.json"),
                        relabel_rows=_load(NEW_DIR / "relabel_fr_old_rows.json"))
    check = rt.compare_with_measurement(rows, _load(NEW_DIR / "MEASUREMENT.json")["bundles"]["fr"])
    assert check["agrees"] is True
    assert check["tracked_but_not_recorded"] == ["bge_115 II 108"]


def test_a_deliberately_wrong_measurement_is_caught():
    """Negative control: the guard must fail when the recorded value is wrong."""
    rows = rt.track_all(_load(OLD_DIR / "bundle_fr.json"),
                        _load(NEW_DIR / "bundle_fr_repaired.json"))
    entry = _load(NEW_DIR / "MEASUREMENT.json")["bundles"]["fr"]
    entry["inverted_audit_rows_tracked"][1]["re_retrieved_now"] = True
    check = rt.compare_with_measurement(rows, entry)
    assert check["agrees"] is False
    assert check["differences"][0]["decision_id"] == "bge_115 II 78"
    assert check["differences"][0]["field"] == "re_retrieved_now"


def test_summarise_only_claims_presence_and_never_correctness():
    rows = rt.track_all(_load(OLD_DIR / "bundle_fr.json"),
                        _load(NEW_DIR / "bundle_fr_repaired.json"))
    summary = rt.summarise(rows)
    assert "bge_115 II 78" in summary["absent_from_repaired_bundle"]
    assert "bge_115 II 108" in summary["absent_from_repaired_bundle"]
    assert summary["carrying_a_counter_status_on_the_repaired_map"] == {"bge_136 III 190": "candidate-limiting"}
    assert "says a label is CORRECT" in summary["claim_ceiling"]


def test_the_report_no_longer_makes_either_false_claim():
    """The audit's required_fixes, as a standing guard.

    The corrected report quotes the false sentences inside a struck correction
    block, so the guard looks for the UNSTRUCK form: the false claim must never
    appear outside the correction.
    """
    text = REPORT.read_text(encoding="utf-8")
    strike = text.split("Correction — repair round 2", 1)
    assert len(strike) == 2, "the dated run-attributed correction block is missing"
    body, correction = strike
    for forbidden in (
        "is re-retrieved and\ncites a real contrary passage",
        "is now\nunlabelled",
    ):
        assert forbidden not in body, f"report body still makes a corrected claim: {forbidden!r}"
    # the correction states the truth about both rows
    assert "absent from" in correction and "all three repaired bundles" in correction
    assert "not present in the repaired FR bundle" in correction
    assert "never\n>    the cited evidence" in correction


def test_the_report_states_the_absence_it_can_now_derive():
    text = REPORT.read_text(encoding="utf-8")
    assert "All four\naudit-named inverted ids are absent from the repair bundles or evidence-relabelled" in text