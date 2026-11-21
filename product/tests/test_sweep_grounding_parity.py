"""Sweep/seam predicate parity for the v68 rejection/incumbent leg.

The shipped seam-abstention leg already rejected an incumbent whose evidence is
defective under the frozen D1-D4 predicates OR not verbatim-grounded in one of
the row's own text fields.  The final incumbent sweep used only the D1-D4
predicates and skipped any row carrying a ``counter_evidence_span`` record, so
a stale span record or an ungrounded evidence string could survive with
``counter_evidence_verified=true``.  These tests pin the parity fix:

* the sweep rejects a defective incumbent even when a span record is present;
* the sweep rejects a non-empty ungrounded incumbent (same rule as the seam);
* a clean, verbatim-grounded, gate-confirmed incumbent WITH a span record is
  retained (no false rejection of a substantive confirmed span);
* the committed fixed-path family and the known sound row are unchanged.

No frozen gate, rubric, threshold, bar or predicate is edited here.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query import counter_evidence_span as ces  # noqa: E402

NO_PROFILE_QID = "petty-theft-dismissal"  # profile resolution is None (P0 test)


def _sweep(bundle: dict) -> dict:
    """Run the shipped entry point on a qid with no anchor profile (sweep-only)."""
    return ces.apply_verified_span_selection(
        copy.deepcopy(bundle), qid=NO_PROFILE_QID
    )


def _row(ev: str, **overrides) -> dict:
    row = {
        "decision_id": "SYN_SWEEP",
        "counter_status": "candidate-limiting",
        "counter_evidence": ev,
        "counter_evidence_verified": True,
        "language": "de",
        "full_text": "",
        "snippet": "",
        "regeste": "",
    }
    row.update(overrides)
    return row


def _bundle(row: dict) -> dict:
    return {"query": "synthetic", "provenance": {"qid": NO_PROFILE_QID},
            "decisions": [row]}


def test_sweep_rejects_defective_incumbent_even_with_span_record():
    ev = "Kantonsgericht Graubuenden Steuergeraicht erster Instanz Urteilskopf"
    row = _row(ev, full_text=ev, counter_evidence_span={"verified": True, "quote": ev})
    assert ces.frozen_content_defects(ev, row) == ["D2_letterhead_zone"]
    out = _sweep(_bundle(row))
    after = out["decisions"][0]
    assert after["counter_evidence_verified"] is False
    assert after["counter_evidence_unevidenced"] is True
    prov = out["provenance"]["counter_evidence_span"]
    assert prov["content_filter_leg"] == "content_only_no_anchor_profile"
    assert "SYN_SWEEP" in prov["downgraded_ids"]
    rec = prov["downgrades"][0]
    assert rec["reason_code"] == "d2_letterhead_zone"
    assert rec["defects"] == ["D2_letterhead_zone"]
    assert rec["grounded_in"] == "full_text"


def test_sweep_rejects_ungrounded_nonempty_incumbent():
    ev = "A verbatim quote that appears in no field of this decision record."
    row = _row(ev, full_text="Unrelated substantive decision text.", snippet="", regeste="")
    assert ces.frozen_content_defects(ev, row) == []  # D1-D4 clean
    assert ces.ground_evidence(ev, row)[0] is None
    out = _sweep(_bundle(row))
    after = out["decisions"][0]
    assert after["counter_evidence_verified"] is False
    rec = out["provenance"]["counter_evidence_span"]["downgrades"][0]
    assert rec["reason_code"] == "ungrounded_evidence"
    assert rec["grounded_in"] is None


def test_sweep_retains_clean_grounded_incumbent_with_span_record():
    ev = ("Le bailleur invoque le defaut d'entretien du bail et le locataire "
          "ne peut resilier le bail que si le defaut est grave selon art "
          "257d CO dans la limite de la jurisprudence sur le bail.")
    row = _row(ev, language="fr", full_text=("Pad. " * 100) + ev + " Suite.",
               counter_evidence_span={"verified": True, "quote": ev})
    out = _sweep(_bundle(row))
    after = out["decisions"][0]
    assert after["counter_evidence_verified"] is True
    assert after.get("counter_evidence_unevidenced") is None
    assert out["provenance"]["counter_evidence_span"]["n_downgraded"] == 0


def test_sweep_and_seam_share_one_content_predicate():
    # The same helper is called on both legs; verify it applies D1-D4 and the
    # grounding check together, without any model or network call.
    ev = "Kantonsgericht Graubuenden header"
    row = _row(ev, full_text=ev)
    failed, reason, defects, grounded = ces._incumbent_content_failure(ev, row)
    assert failed and reason == "d2_letterhead_zone"
    assert defects == ["D2_letterhead_zone"] and grounded == "full_text"
    ev2 = "not grounded anywhere"
    failed2, reason2, defects2, grounded2 = ces._incumbent_content_failure(
        ev2, _row(ev2, full_text="other text"))
    assert failed2 and reason2 == "ungrounded_evidence"
    assert defects2 == [] and grounded2 is None


def test_committed_fixed_path_family_keeps_zero_defective_verified_rows():
    import glob as _glob
    files = sorted(
        set(_glob.glob(str(ROOT / "results/product/offline_slice/**/*.bundle.json"),
                       recursive=True))
        | set(_glob.glob(str(ROOT / "results/product/server_slice/**/*.bundle.json"),
                         recursive=True))
    )
    assert len(files) >= 100
    n_verified = 0
    for path in files:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        if "decisions" not in doc:
            continue
        out = ces.apply_verified_span_selection(
            copy.deepcopy(doc), qid=(doc.get("provenance") or {}).get("qid"))
        for r in out["decisions"]:
            if r.get("counter_evidence_verified") is not True:
                continue
            n_verified += 1
            ev = str(r.get("counter_evidence") or "")
            assert ces.frozen_content_defects(ev, r) == [], (
                f"verified row {r.get('decision_id')} still content-defective")
            assert not (ev.strip() and ces.ground_evidence(ev, r)[0] is None), (
                f"verified row {r.get('decision_id')} is not verbatim-grounded")
    assert n_verified > 0
