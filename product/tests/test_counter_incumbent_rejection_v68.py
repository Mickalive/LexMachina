"""Direction v68 P0 — stage-2 rejection/incumbent leg (scoped, no false rejects).

Run 40850096631 committed the bare statement "when the span seam abstains, the
incumbent must not remain verified" as an UNCONDITIONAL downgrade in
``apply_surface_span_confirmation``.  That closed the rejection leg for a
defective incumbent but also violated the ordered-work success rule: a
content-sound incumbent that the frozen gate had confirmed would be falsely
rejected merely because stage 2 abstained on a *different* span axis.

This test pins the scoped contract that replaces it:

1. stage-2 abstention + DEFECTIVE incumbent (frozen D1-D4 failure, e.g. the
   offset-0 letterhead zone) -> downgraded to explicitly-unevidenced, with a
   per-row BEFORE/AFTER record naming the frozen defect classes;
2. stage-2 abstention + CONTENT-SOUND incumbent -> LEFT VERIFIED and published
   in ``retained_content_sound`` (false reject count 0);
3. an incumbent the stage never iterated (no ``counter_surface_signal``) is
   still swept by the same deterministic predicates;
4. the provenance publishes ``n_downgraded`` / ``n_incumbent_downgraded`` and
   the frozen predicate provenance without editing the gate.

The instrument is deterministic and gate-free: no frozen bar, rubric,
threshold or scorer is imported, edited or re-scored here.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query import counter_evidence_span as ces  # noqa: E402

#: An append-only committed bundle whose provenance already carries a stage-2
#: abstention population, so this test does not need to re-run retrieval.
BUNDLE = (
    ROOT / "results" / "product" / "offline_slice" / "20261025T045400Z"
    / "rent-default.bundle.json"
)


def _load() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def _prov(bundle: dict) -> dict:
    return (bundle.get("provenance") or {}).get(
        "counter_evidence_span_surface") or {}


def _row(bundle: dict, decision_id: str) -> dict:
    return next(d for d in bundle["decisions"] if d["decision_id"] == decision_id)


def _first_abstention() -> tuple[dict, dict, dict]:
    doc = _load()
    entry = _prov(doc)["abstained"][0]
    return doc, entry, _row(doc, entry["decision_id"])


def _sound_quote(row: dict) -> str:
    """A verbatim sentence from the row that passes the frozen predicates."""
    text = str(row.get("full_text") or "")
    for match in re.finditer(r"[^.!?]{60,400}[.!?]", text):
        candidate = match.group(0).strip()
        offset = text.find(candidate)
        if ces.passes_content_filter(candidate, row, offset)[0]:
            return candidate
    raise AssertionError(f"no content-sound sentence in {row.get('decision_id')}")


def _defective_quote(row: dict) -> str:
    """An offset-0 court header: the accepted D2 letterhead-zone variant."""
    quote = str(row.get("full_text") or "")[:80]
    assert ces.frozen_content_defects(quote, row) == ["D2_letterhead_zone"], quote
    return quote


def test_stage2_abstention_downgrades_a_defective_verified_incumbent():
    doc, entry, row = _first_abstention()
    row["counter_evidence"] = _defective_quote(row)
    row["counter_evidence_verified"] = True
    out = ces.apply_surface_span_confirmation(doc)
    after = _row(out, entry["decision_id"])
    assert after.get("counter_evidence_verified") is False
    assert after.get("counter_evidence_unevidenced") is True
    assert after.get("counter_evidence_unevidenced_reason") == entry["reason_code"]
    prov = _prov(out)
    assert prov["n_downgraded"] >= 1
    record = next(r for r in prov["downgrades"]
                  if r["decision_id"] == entry["decision_id"])
    assert record["leg"] == "surface_abstention"
    assert record["before"]["counter_evidence_verified"] is True
    assert record["after"]["counter_evidence_verified"] is False
    assert "D2_letterhead_zone" in record["defects"]


def test_stage2_abstention_retains_a_content_sound_verified_incumbent():
    """Ordered-work success rule: no frozen-confirmed span is falsely rejected."""
    doc, entry, row = _first_abstention()
    quote = _sound_quote(row)
    row["counter_evidence"] = quote
    row["counter_evidence_verified"] = True
    out = ces.apply_surface_span_confirmation(doc)
    after = _row(out, entry["decision_id"])
    assert after.get("counter_evidence_verified") is True, (
        "a content-sound incumbent was falsely rejected by the abstention leg")
    assert after.get("counter_evidence") == quote
    assert after.get("counter_evidence_unevidenced") is not True
    prov = _prov(out)
    assert entry["decision_id"] in {
        r["decision_id"] for r in prov["retained_content_sound"]}
    assert entry["decision_id"] not in set(prov["downgraded_ids"])
    retained = next(r for r in prov["retained_content_sound"]
                    if r["decision_id"] == entry["decision_id"])
    assert retained["defects"] == []


def test_stage2_absent_incumbent_is_neither_downgraded_nor_retained():
    """No evidence is not defective evidence: leave the row untouched.

    The fresh surface population contains unverified rows with an empty
    incumbent.  Treating the frozen D1 empty predicate as a rejection made
    every such abstention claim ``incumbent_downgraded=True`` and wrote a
    ``counter_evidence_unevidenced`` reason even though the row never claimed
    verified evidence.  This pins the absent-vs-defective distinction.
    """
    doc, entry, row = _first_abstention()
    row["counter_evidence"] = ""
    row["counter_evidence_verified"] = False
    row.pop("counter_evidence_unevidenced", None)
    row.pop("counter_evidence_unevidenced_reason", None)
    out = ces.apply_surface_span_confirmation(doc)
    after = _row(out, entry["decision_id"])
    assert after.get("counter_evidence_verified") is False
    assert after.get("counter_evidence_unevidenced") is None
    assert after.get("counter_evidence_unevidenced_reason") is None
    prov = _prov(out)
    assert entry["decision_id"] not in set(prov["downgraded_ids"])
    assert entry["decision_id"] not in {
        r["decision_id"] for r in prov["retained_content_sound"]}
    record = next(r for r in prov["abstained"]
                  if r["decision_id"] == entry["decision_id"])
    assert record["incumbent_state"] == "absent"
    assert record["incumbent_downgraded"] is False
    assert ces._incumbent_content_failure({"counter_evidence": ""}) == (
        False, [], None)


def test_stage2_sweep_downgrades_an_uniterated_defective_incumbent():
    """A verified row with no surface signal is still covered (no gate needed)."""
    doc = _load()
    target = next(
        d for d in doc["decisions"]
        if not d.get("counter_surface_signal")
        and len(str(d.get("full_text") or "")) >= 100
    )
    did = target["decision_id"]
    row = _row(doc, did)
    row["counter_evidence"] = str(row.get("full_text") or "")[:80]
    row["counter_evidence_verified"] = True
    out = ces.apply_surface_span_confirmation(doc)
    after = _row(out, did)
    assert after.get("counter_evidence_verified") is False
    prov = _prov(out)
    record = next(r for r in prov["downgrades"] if r["decision_id"] == did)
    assert record["leg"] in ("incumbent_sweep", "surface_abstention")
    assert record["defects"]


def test_stage2_provenance_publishes_the_scoped_leg_without_touching_the_gate():
    doc, entry, row = _first_abstention()
    row["counter_evidence"] = _sound_quote(row)
    row["counter_evidence_verified"] = True
    out = ces.apply_surface_span_confirmation(doc)
    prov = _prov(out)
    for key in ("n_downgraded", "n_incumbent_downgraded", "downgraded_ids",
                "downgrades", "n_retained_content_sound",
                "retained_content_sound", "content_filter"):
        assert key in prov, key
    assert prov["content_filter"]["predicate_source_sha256"] == (
        ces.FROZEN_PREDICATE_SOURCE_SHA256)
    # the stage never writes a label on abstention
    for item in prov["abstained"]:
        after = _row(out, item["decision_id"])
        assert item["counter_status_unchanged"] == after.get("counter_status")
