"""Direction v68 P0 — rejection/incumbent leg of the counter-evidence path.

Pins the ordered-work contract with executable evidence:

1. the product content filter is BYTE-ALIGNED with the frozen D1-D4 predicates
   (constants copied verbatim; provenance carries the re-hashed REPORTED-ONLY
   source sha from the accepted falsifier hypothesis 40105794124);
2. on the shipped seam, the four decisions the accepted falsifier measured as
   content-defective are NO LONGER verified with defective content, and the one
   sound decision (bstger_SK.2023.49) STAYS verified/sound;
3. the no-frozen-anchor-profile path (petty-theft-dismissal) still runs the
   content-only rejection leg — a defective incumbent is never left verified
   just because the gate had no profile for the query;
4. provenance publishes per-row BEFORE/AFTER with reason_code and defects;
5. the precision-guard scope change (scan proposals only) is pinned, and the
   accepted packet-of-record v3 arm numbers stay unchanged (pinned separately
   in test_counter_evidence_span.py::QIDS).

No frozen gate, rubric, threshold or bar is imported, edited or re-tuned here.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "product"
for _p in (str(ROOT), str(PRODUCT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from product.query import counter_evidence_span as ces  # noqa: E402

#: (bundle, decision_id, expected frozen defect classes) — the accepted
#: falsifier population rows of run 40105794124 (defect_histogram
#: D2=2, D3=2, D4=1 over 4 distinct decisions, plus exactly 1 sound row).
DEFECTIVE = [
    ("results/product/offline_slice/20261024T142517Z/rent-default.bundle.json",
     "gr_gerichte_ERZ 2010 25", ["D2_letterhead_zone"]),
    ("results/product/offline_slice/20261023T121515Z/business-judgment-rule.bundle.json",
     "bge_BGE_110_II_391", ["D2_letterhead_zone"]),
    ("results/product/offline_slice/20261023T121518Z/petty-theft-dismissal.bundle.json",
     "ge_gerichte_CAPH_107_2004", ["D3_markup_residue"]),
    ("results/product/server_slice/20261023T224255Z/served.bundle.json",
     "bge_BGE_121_III_260",
     ["D3_markup_residue", "D4_language_marker_mismatch"]),
]
SOUND = (
    "results/product/offline_slice/20261023T121512Z/corporate-criminal-liability.bundle.json",
    "bstger_SK.2023.49",
)

#: Provenance pin: the accepted falsifier hypothesis's re-hashed REPORTED-ONLY
#: inputs (evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124_HYPOTHESIS_V1.json).
FROZEN_PREDICATE_SOURCE_SHA = (
    "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"
)
FROZEN_HYPOTHESIS_SHA = (
    "734a447dffd86a360a46ce9a804e3bb9f7eb224f9067777d78b62216e13e0881"
)


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _row(rel: str, did: str) -> tuple[dict, dict]:
    doc = _load(rel)
    row = next(d for d in doc["decisions"] if d.get("decision_id") == did)
    return doc, row


def _shipped_apply(doc: dict) -> dict:
    """The shipped call signature (qid from bundle provenance, default env)."""
    return ces.apply_verified_span_selection(
        copy.deepcopy(doc), qid=(doc.get("provenance") or {}).get("qid")
    )


# --------------------------------------------------------------------------- #
# 1. predicate alignment
# --------------------------------------------------------------------------- #

def test_frozen_predicate_constants_and_provenance_are_pinned():
    prov = ces.content_filter_provenance()
    assert ces.FROZEN_PREDICATE_SOURCE_SHA256 == FROZEN_PREDICATE_SOURCE_SHA
    assert ces.FROZEN_PREDICATE_HYPOTHESIS_SHA256 == FROZEN_HYPOTHESIS_SHA
    assert prov["predicate_source"] == "evaluation/counter_evidence_quality_benchmark.py"
    assert prov["letterhead_zone_offset_max"] == 400
    assert prov["min_marker_hits"] == 3
    assert prov["markup_tokens"] == ["<mark>", "</mark>", "<em>", "</em>",
                                     "<b>", "</b>", "<highlight>"]
    assert "never edits the" in prov["alignment"]
    # If the frozen source is present in this checkout, re-hash it for real.
    src = ROOT / "evaluation" / "counter_evidence_quality_benchmark.py"
    if src.is_file():
        assert hashlib.sha256(src.read_bytes()).hexdigest() == FROZEN_PREDICATE_SOURCE_SHA


def test_frozen_predicates_on_planted_defects():
    base = {"decision_id": "SYN", "language": "de", "full_text": "",
            "snippet": "", "regeste": ""}
    # D2: grounded in own full_text below offset 400
    row = dict(base, full_text="X" * 10 + "Kantonsgericht Graubuenden header")
    assert ces.frozen_content_defects(row["full_text"], row) == ["D2_letterhead_zone"]
    # same text below 400 but NOT grounded in full_text (snippet field): no D2
    row = dict(base, snippet="Kantonsgericht Graubuenden header")
    assert "D2_letterhead_zone" not in ces.frozen_content_defects(row["snippet"], row)
    # D2 does not fire at/after the frozen offset
    row = dict(base, full_text="y" * 400 + " Urteilskopf substantive text here")
    off = ces.ground_evidence(row["full_text"], row)[1]
    assert off == 0 and "D2_letterhead_zone" in ces.frozen_content_defects(row["full_text"], row)
    # D3 markup residue
    row = dict(base, snippet="<mark>Selon</mark> l'art. 337 CO")
    assert ces.frozen_content_defects(row["snippet"], row) == ["D3_markup_residue"]
    # D4 language mismatch: German evidence on an Italian decision
    ev = "Regeste Erwaegung Kuendigung Mietvertrag Bundesgericht Verfuegung"
    row = dict(base, language="it", full_text="pad " * 60 + ev)
    got = ces.frozen_content_defects(ev, row)
    assert "D4_language_marker_mismatch" in got
    # D1 empty
    assert ces.frozen_content_defects("  ", base) == ["D1_empty_evidence"]
    # a sound French counter-evidence row passes
    sound = ("Subsidiairement, les 4 versements suivants pour un montant "
             "total sur le compte no; cf. art. 102 CP ; la responsabilite "
             "penale de l'entreprise selon l'art. 102 CP est subsidiaire.")
    row = dict(base, language="fr", snippet=sound)
    assert ces.frozen_content_defects(sound, row) == []


# --------------------------------------------------------------------------- #
# 2. the four defective decisions and the one sound row, shipped path
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("rel,did,expected_defects", DEFECTIVE)
def test_defective_decision_is_no_longer_verified(rel, did, expected_defects):
    doc, before = _row(rel, did)
    assert before.get("counter_evidence_verified") is True, "BEFORE state of record"
    assert ces.frozen_content_defects(
        str(before.get("counter_evidence") or ""), before) == expected_defects

    out = _shipped_apply(doc)
    after = next(d for d in out["decisions"] if d.get("decision_id") == did)
    assert after.get("counter_evidence_verified") is False, (
        f"{did} must not remain verified with defective content")
    assert after.get("counter_evidence_unevidenced") is True
    assert after.get("counter_evidence_unevidenced_reason")
    # and the row stays visible (never dropped from the map)
    assert did in {d.get("decision_id") for d in out["decisions"]}
    # no verified row anywhere in the bundle carries a frozen content defect
    for r in out["decisions"]:
        if r.get("counter_evidence_verified") is True:
            assert ces.frozen_content_defects(
                str(r.get("counter_evidence") or ""), r) == [], (
                f"verified row {r.get('decision_id')} still content-defective")


def test_sound_row_stays_verified_and_sound():
    rel, did = SOUND
    doc, before = _row(rel, did)
    assert ces.frozen_content_defects(
        str(before.get("counter_evidence") or ""), before) == []
    out = _shipped_apply(doc)
    after = next(d for d in out["decisions"] if d.get("decision_id") == did)
    assert after.get("counter_evidence_verified") is True, (
        "the known sound row must stay verified/sound (ordered-work success rule)")
    assert ces.frozen_content_defects(
        str(after.get("counter_evidence") or ""), after) == []
    assert after.get("counter_evidence_unevidenced") is None
    retained = out["provenance"]["counter_evidence_span"]["retained_content_sound"]
    assert did in [r["decision_id"] for r in retained], (
        "the retention must be published, not silent")


def test_provenance_publishes_per_row_before_after_with_reason_and_defects():
    out = _shipped_apply(_load(DEFECTIVE[0][0]))
    prov = out["provenance"]["counter_evidence_span"]
    assert prov["applied"] is True
    assert prov["n_downgraded"] >= 1
    for rec in prov["downgrades"]:
        assert {"decision_id", "before", "after", "reason_code", "defects"} <= set(rec)
        assert rec["before"]["counter_evidence_verified"] is True
        assert rec["after"]["counter_evidence_verified"] is False
        assert rec["reason_code"]
        assert rec["defects"], "a downgrade record must name its frozen defect"
    cf = prov["content_filter"]
    assert cf["predicate_source_sha256"] == FROZEN_PREDICATE_SOURCE_SHA
    assert cf["frozen_hypothesis_sha256"] == FROZEN_HYPOTHESIS_SHA


def test_no_profile_bundle_still_downgrades_its_defective_incumbent():
    rel, did, _ = DEFECTIVE[2]  # petty-theft-dismissal: profile resolution is None
    doc, before = _row(rel, did)
    out = _shipped_apply(doc)
    prov = out["provenance"]["counter_evidence_span"]
    assert prov["applied"] is False, "no gate ran — never claim selection happened"
    assert prov["reason"] == "no_frozen_anchor_profile_for_query"
    assert prov["content_filter_applied"] is True
    assert prov["content_filter_leg"] == "content_only_no_anchor_profile"
    after = next(d for d in out["decisions"] if d.get("decision_id") == did)
    assert after.get("counter_evidence_verified") is False
    assert after.get("counter_evidence_unevidenced_reason") == "d3_markup_residue"
    assert did in prov["downgraded_ids"]


def test_geometry_ranks_and_row_count_are_untouched_by_the_leg():
    rel, _, _ = DEFECTIVE[3]
    doc = _load(rel)
    before_geo = {d["decision_id"]: (d.get("x"), d.get("y"), d.get("cluster_id"))
                  for d in doc["decisions"]}
    out = _shipped_apply(doc)
    assert len(out["decisions"]) == len(doc["decisions"])
    after_geo = {d["decision_id"]: (d.get("x"), d.get("y"), d.get("cluster_id"))
                 for d in out["decisions"]}
    assert before_geo == after_geo


# --------------------------------------------------------------------------- #
# 3. guard scope: proposals are guarded, the clean incumbent is exempt
# --------------------------------------------------------------------------- #

def _gate_confirmed_incumbent_row() -> dict:
    """A fr-bail row whose incumbent contains the profile pivot (art. 257d).

    ``full_text`` starts 500 chars of padded terminated SENTENCES before the
    incumbent, so the incumbent is a single verbatim candidate sentence AND is
    grounded at offset >= 400 (outside the frozen letterhead zone).
    """
    ev = ("Le bailleur invoque le defaut d'entretien du bail et le locataire "
          "ne peut resilier le bail que si le defaut est grave selon art "
          "257d CO dans la limite de la jurisprudence sur le bail.")
    return {
        "decision_id": "SYN_INCUMBENT",
        "counter_status": "candidate-limiting",
        "counter_evidence": ev,
        "counter_evidence_verified": True,
        "language": "fr",
        "full_text": ("Pad. " * 100) + ev + " La suite du texte se poursuit ici.",
        "snippet": "",
        "regeste": "",
    }


def test_precision_guard_does_not_veto_the_clean_confirmed_incumbent():
    rules, _ = ces.load_frozen_rules()
    profile = ces.resolve_anchor_profile(rules, qid="fr-bail-entretien")
    decide, _ = ces._import_component()
    # a deliberately failing guard (no matching statute / query phrase)
    failing_guard = {"available": True, "statutes": ["999zzz"],
                     "phrases": ["kein treffer hier"]}
    row = _gate_confirmed_incumbent_row()
    sel = ces.select_span(
        row, rules=rules, profile=profile, decide_label=decide,
        guard=failing_guard, precision_guard=True,
    )
    assert sel.selected is True, "content-clean confirmed incumbent is kept"
    assert sel.incumbent_guard_exempted is True, "the exemption is disclosed"
    assert sel.quote == row["counter_evidence"]
    # the same failing guard still vetoes a scan proposal (unchanged scope)
    row2 = dict(row, counter_evidence="")
    sel2 = ces.select_span(
        row2, rules=rules, profile=profile, decide_label=decide,
        guard=failing_guard, precision_guard=True,
    )
    assert sel2.selected is False, "scan proposals remain guarded"
    assert sel2.n_guard_rejected >= 1


def test_defective_incumbent_is_rejected_before_any_guard_consideration():
    rules, _ = ces.load_frozen_rules()
    profile = ces.resolve_anchor_profile(rules, qid="fr-bail-entretien")
    decide, _ = ces._import_component()
    row = _gate_confirmed_incumbent_row()
    # markup residue INSIDE the evidence string itself (frozen D3 checks the quote)
    row["counter_evidence"] = "<mark>" + row["counter_evidence"] + "</mark>"
    row["full_text"] = ("Pad. " * 100) + row["counter_evidence"] + " Suite."
    sel = ces.select_span(
        row, rules=rules, profile=profile, decide_label=decide,
        guard={"available": False}, precision_guard=False,
    )
    assert sel.selected is False
    assert sel.reason_code == "d3_markup_residue"


# --------------------------------------------------------------------------- #
# 4. fixture-mode end-to-end pin (ordered item 4)
# --------------------------------------------------------------------------- #

def test_fixture_mode_offline_slice_downgrades_the_known_letterhead_row():
    """The shipped fixture path (offline_slice.build_bundle) really runs the
    rejection leg: the trilingual Graubuenden letterhead row ends unverified
    and the bundle keeps its full clickable-map shape."""
    socket = __import__("socket")
    real_connect = socket.socket.connect
    socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("offline slice attempted network access"))
    try:
        import offline_slice as ofs
        bundle = ofs.build_bundle("rent-default", top_n=100, enrich=True)
    finally:
        socket.socket.connect = real_connect
    prov = (bundle.get("provenance") or {}).get("counter_evidence_span") or {}
    assert prov.get("applied") is True
    assert prov.get("content_filter", {}).get("predicate_source_sha256") == (
        FROZEN_PREDICATE_SOURCE_SHA)
    row = next(d for d in bundle["decisions"]
               if d.get("decision_id") == "gr_gerichte_ERZ 2010 25")
    assert row.get("counter_evidence_verified") is False
    assert row.get("counter_evidence_unevidenced") is True
    # every verified row in the freshly built bundle is content-sound
    for r in bundle["decisions"]:
        if r.get("counter_evidence_verified") is True:
            assert ces.frozen_content_defects(
                str(r.get("counter_evidence") or ""), r) == []
    # the map itself is intact: 100 rows, coordinates, clusters, source links
    assert len(bundle["decisions"]) == 100
    assert all(d.get("cluster_id") is not None for d in bundle["decisions"])
    assert all(d.get("canonical_url") for d in bundle["decisions"])
