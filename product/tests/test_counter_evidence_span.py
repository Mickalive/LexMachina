"""Direction v65: verbatim counter-evidence span selection.

Locks the extract-verify-abstain seam that runs between the accepted
adversarial pass and the accepted frozen confirm-or-abstain gate:

1. spans preserve raw offsets and are byte-exact substrings (no newline rewrite);
2. a mutated quote is rejected;
3. on packet-of-record v3 the shipped guarded seam lifts emitted counter rows
   0 -> 1 (FR only, citing art. 257d CO) while every emitted quote is verbatim
   and verified;
4. the unguarded diagnostic lifts 0 -> 6, but those six include manually
   inspected off-topic spans (DE voting/water construction, FR rent/arbitration);
   the guard rejects them, so the unguarded arm is a diagnostic, not a claim;
5. the frozen gate is never re-tuned: rows it rejects remain abstained and are
   never dropped from the map;
6. the accepted anchor seam clears ``counter_evidence_verified`` on abstention;
7. the pipeline orders span selection before emission repair and anchor;
8. the seam is deterministic and has an off switch.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_evidence_span as ces  # noqa: E402
from product.query.counter_anchor import apply_anchor_labels  # noqa: E402
from product.query.counter_emission_repair import apply_counter_emission_repair  # noqa: E402

PACKET = ROOT / "results" / "product" / "gate_packet" / "39319405429" / "questions"
#: guarded shipped arm: (emitted, scored)
QIDS = {
    "de-kapitalverletzung": (0, 8),
    "fr-bail-entretien": (1, 8),
    "it-responsabilita-medica": (0, 4),
}
#: gate-only diagnostic (pre-guard), kept so the precision cost is visible
UNGUARDED_QIDS = {
    "de-kapitalverletzung": (2, 8),
    "fr-bail-entretien": (4, 8),
    "it-responsabilita-medica": (0, 4),
}


def _load(slug: str) -> dict:
    return json.loads((PACKET / f"{slug}.bundle.json").read_text(encoding="utf-8"))


def _chain(slug: str, *, span: bool, guard: str = "on") -> dict:
    b = copy.deepcopy(_load(slug))
    if span:
        b = ces.apply_verified_span_selection(
            b, qid=slug, mode="select",
            env={"LEXMACHINA_COUNTER_SPAN_GUARD": guard},
        )
    b = apply_counter_emission_repair(b)
    return apply_anchor_labels(b, qid=slug)


# --------------------------------------------------------------------------- #
# 1. span mechanics
# --------------------------------------------------------------------------- #

def test_sentence_spans_preserve_offsets_and_never_rewrite_newlines():
    text = "Ein erster Satz mit genug Laenge fuer den Span-Test. \nZweiter Satz mit einem\nZeilenumbruch und genug Laenge."
    spans = ces.sentence_spans(text)
    assert len(spans) == 2
    for s in spans:
        assert text[s.start:s.end] == s.quote, "the span is the raw slice"
        assert "\n" not in s.quote or "\n" in text
    assert "Zeilenumbruch" in spans[1].quote


def test_verify_span_rejects_mutation_and_wrong_offsets():
    text = "Die Kapitalverletzung ist nach Art. 321 OR nur begrenzt zu bejahen."
    spans = ces.sentence_spans(text)
    assert spans, "fixture must produce a span"
    s = spans[0]
    assert ces.verify_span(text, s.quote, s.start, s.end) is True
    mutated = s.quote[:-1] + ("X" if s.quote[-1] != "X" else "Y")
    assert ces.verify_span(text, mutated, s.start, s.end) is False
    assert ces.verify_span(text, s.quote, s.start + 1, s.end) is False
    assert ces.verify_span(text, s.quote, s.start, s.end + 1) is False


def test_empty_row_abstains_without_candidates():
    rules, _ = ces.load_frozen_rules()
    profile = ces.resolve_anchor_profile(rules, qid="de-kapitalverletzung")
    decide, _ = ces._import_component()
    assert profile is not None
    sel = ces.select_span(
        {"decision_id": "x", "counter_status": "candidate-limiting"},
        rules=rules, profile=profile, decide_label=decide,
    )
    assert sel.selected is False
    assert sel.n_candidates == 0


# --------------------------------------------------------------------------- #
# 2. packet-of-record v3 measurement
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("slug", sorted(QIDS))
def test_packet_span_selection_lifts_emitted_rows_and_verifies_every_quote(slug):
    expected_emitted, _ = QIDS[slug]
    baseline = _chain(slug, span=False)
    candidate = _chain(slug, span=True)
    bp = baseline["provenance"]["counter_anchor"]
    cp = candidate["provenance"]["counter_anchor"]
    assert bp["n_emitted"] == 0, "baseline emits none on this packet"
    assert cp["n_emitted"] == expected_emitted
    assert cp["n_scored"] == bp["n_scored"], "the population is unchanged"
    assert cp["n_emitted"] + cp["n_abstained"] == cp["n_scored"]
    by_id = {d["decision_id"]: d for d in candidate["decisions"]}
    for did in cp["emitted_ids"]:
        row = by_id[did]
        assert row["counter_evidence_verified"] is True
        span = row["counter_evidence_span"]
        assert span["selected"] is True and span["verified"] is True
        assert ces.verify_span(
            str(row.get(span["field"]) or ""), row["counter_evidence"],
            span["start"], span["end"],
        ), "emitted quote must be a byte-exact slice of the named field"
    assert len(candidate["decisions"]) == len(_load(slug)["decisions"]), "never drop rows"


@pytest.mark.parametrize("slug", sorted(UNGUARDED_QIDS))
def test_unguarded_diagnostic_is_pinned_and_not_the_shipped_arm(slug):
    expected_emitted, _ = UNGUARDED_QIDS[slug]
    candidate = _chain(slug, span=True, guard="off")
    cp = candidate["provenance"]["counter_anchor"]
    assert cp["n_emitted"] == expected_emitted
    assert candidate["provenance"]["counter_evidence_span"]["precision_guard"] is False


def test_guard_rejects_the_off_topic_quotes_from_the_unguarded_arm():
    rules, _ = ces.load_frozen_rules()
    profile = rules.anchors["fr-bail-entretien"]
    query = _load("fr-bail-entretien")["query"]
    guard = ces.guard_terms(profile, query)
    off_topic = [
        # rent increase
        "C'est ainsi qu'elle aurait dû tenir compte du renchérissement du coût "
        "de la vie également pour la période antérieure à la dernière "
        "modification du loyer, puisque dans ses quatre avis de hausse "
        "précédents le défendeur avait invoqué comme seul motif",
        # défaut de légitimation / rent fixing
        "B.A. et A.A. (défenderesses) ont conclu au rejet de la demande, pour "
        "défaut de légitimation passive de la première et abus de droit à "
        "invoquer le vice de forme dans la fixation du loyer initial",
        # arbitration / LDIP
        "À défaut d'une telle clause expresse - à laquelle on peut appliquer "
        "par analogie les critères posés par le Tribunal fédéral sur la base "
        "de l' art. 192 LDIP",
    ]
    for quote in off_topic:
        assert ces.span_passes_precision_guard(quote, guard) is False
    on_topic = (
        "A la lecture du courrier contenant l'avis comminatoire, le locataire "
        "(cf. art. 257d CO ) doit clairement comprendre que le bailleur se "
        "réserve la faculté de mettre un terme au bail"
    )
    assert ces.span_passes_precision_guard(on_topic, guard) is True


def test_guard_phrase_requires_exact_multi_word_query_span():
    guard = ces.guard_terms(
        {"pivot": []},
        "Résiliation du bail pour défaut d'entretien du bailleur",
    )
    assert guard["available"] is True and guard["statutes"] == []
    assert ces.span_passes_precision_guard(
        "Le bailleur invoque un défaut d'entretien du bailleur.", guard
    )
    # Same head noun, different complement: must not match.
    assert ces.span_passes_precision_guard(
        "Le défaut de légitimation passive est retenu.", guard
    ) is False


def test_frozen_gate_is_not_retuned_on_it_bundle():
    it = _chain("it-responsabilita-medica", span=True)
    cp = it["provenance"]["counter_anchor"]
    assert cp["n_emitted"] == 0, "the frozen gate still abstains where it cannot confirm"
    assert cp["abstention_reasons"] == {"pivot_absent": 4}
    assert cp["abstained_ids"], "abstained rows stay visible"
    assert all(
        d["counter_status"] == "abstained_unevidenced"
        for d in it["decisions"] if d["decision_id"] in cp["abstained_ids"]
    )


def test_anchor_abstention_clears_the_evidenced_flag():
    b = copy.deepcopy(_load("de-kapitalverletzung"))
    row = next(d for d in b["decisions"] if d.get("adversarial_retrieval_signal"))
    row["counter_status"] = "candidate-limiting"
    row["counter_evidence"] = "x" * 80
    row["counter_evidence_verified"] = True
    out = apply_anchor_labels(b, qid="de-kapitalverletzung")
    got = next(d for d in out["decisions"] if d["decision_id"] == row["decision_id"])
    assert got["counter_status"] == "abstained_unevidenced"
    assert got["counter_evidence_verified"] is False, (
        "a proposed quote the frozen gate rejects must not claim verbatim support"
    )


# --------------------------------------------------------------------------- #
# 3. determinism, idempotence, kill switch, wiring
# --------------------------------------------------------------------------- #

def test_selection_is_deterministic_and_idempotent():
    source = _load("fr-bail-entretien")
    a = ces.apply_verified_span_selection(copy.deepcopy(source), qid="fr-bail-entretien")
    b = ces.apply_verified_span_selection(copy.deepcopy(source), qid="fr-bail-entretien")
    assert a == b
    again = ces.apply_verified_span_selection(copy.deepcopy(a), qid="fr-bail-entretien")
    assert again["provenance"]["counter_evidence_span"]["n_selected"] == (
        a["provenance"]["counter_evidence_span"]["n_selected"]
    )


def test_kill_switch_is_a_noop():
    out = ces.apply_verified_span_selection(
        _load("de-kapitalverletzung"), qid="de-kapitalverletzung",
        env={ces.SPAN_ENV: "off"},
    )
    prov = out["provenance"]["counter_evidence_span"]
    assert prov["applied"] is False
    assert all("counter_evidence_span" not in d for d in out["decisions"])


def test_pipeline_runs_span_selection_before_emission_repair_and_anchor():
    src = (ROOT / "product" / "query" / "pipeline.py").read_text(encoding="utf-8")
    span_at = src.index("audited = apply_verified_span_selection(")
    repair_at = src.index("audited = apply_counter_emission_repair(audited)")
    anchor_at = src.index("audited = apply_anchor_labels(")
    assert span_at < repair_at < anchor_at


# --------------------------------------------------------------------------- #
# 4. ordered item 4 diagnosis artifact is pinned, not prose
# --------------------------------------------------------------------------- #

def test_absent_id_diagnosis_pins_head_exclusion_not_a_retrieval_miss():
    path = (
        ROOT / "results" / "product" / "counter_span"
        / "CYCLE_39986094168_absent_ids.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [r for leg in payload["legs"] for r in leg["rows"]]
    assert payload["summary"]["n_known_ids"] == 3
    assert payload["summary"]["n_in_reranked_pool"] == 3
    assert payload["summary"]["n_inside_top_n_cut"] == 0
    assert sorted(r["post_rerank_rank"] for r in rows) == [104, 118, 119]
    for r in rows:
        assert r["legal_anchor_score"] == 0.0
        assert r["query_similarity"] < 0.04
        assert r["inside_top_n_cut"] is False


# --------------------------------------------------------------------------- #
# 5. direction v67 P0: deterministic D2/D3/D4 content rejection is independent
#    of the frozen gate's abstention (accepted PATH_SCOPE_RESIDUAL defect)
# --------------------------------------------------------------------------- #

GR_LETTERHEAD = (
    "Kantonsgericht von Graubünden\n"
    "Dretgira chantunala dal Grischun\n"
    "Tribunale cantonale dei Grigioni\n"
    "________________________________________________"
)

URTEILSKOPF = (
    "Urteilskopf\n"
    "110 II 391\n"
    "75. Auszug aus dem Urteil der I. Zivilabteilung vom 10. April 1984 "
    "i.S. X. gegen Y. (Beschwerde)"
)


class _AbstainDecision:
    abstained = True
    label = "ABSTAIN"
    reason_code = "pivot_absent"
    uncertainty = 1.0


class _AbstainGate:
    """Frozen-gate stand-in that abstains on every span (pivot_absent)."""

    def __call__(self, row, rules, profile):
        return _AbstainDecision()


def _letterhead_row(evidence: str, *, language: str = "de") -> dict:
    return {
        "decision_id": "gr_gerichte_ERZ 2010 25",
        "language": language,
        "counter_status": "candidate-limiting",
        "counter_evidence": evidence,
        "counter_evidence_verified": True,
        "full_text": evidence + "\n\nErwägungen: Die Beschwerde ist unbegründet.\n",
        "snippet": "",
        "regeste": "",
    }


def test_letterhead_incumbent_is_rejected_even_when_frozen_gate_abstains():
    row = _letterhead_row(GR_LETTERHEAD)
    sel = ces.select_span(
        row, rules=None, profile={}, decide_label=_AbstainGate(),
        guard={"available": True}, precision_guard=False,
    )
    assert sel.selected is False
    assert sel.reason_code == "d2_letterhead_zone"
    assert sel.baseline_defect == "d2_letterhead_zone"
    # The gate is never consulted on a defective incumbent: it reports its own
    # abstention, not the frozen gate's pivot_absent.
    assert sel.baseline_label == "ABSTAIN"


def test_urteilskopf_head_run_is_rejected_as_d2():
    assert ces.passes_content_filter(URTEILSKOPF, _letterhead_row(URTEILSKOPF), 0) == (
        False, "d2_letterhead_zone",
    )


def test_substantive_body_span_near_document_start_is_not_falsely_rejected():
    body = (
        "Die Kündigung eines Mietverhältnisses setzt nach Art. 257d CO eine "
        "Mahnung voraus. Das Bundesgericht hat diese Voraussetzung mehrfach "
        "bestätigt."
    )
    row = _letterhead_row(body)
    ok, reason = ces.passes_content_filter(body, row, 0)
    assert ok is True, reason


def test_markup_residue_is_d3():
    row = _letterhead_row("Der <mark>Kündigung</mark> ging eine Mahnung voraus.")
    assert ces.passes_content_filter(row["counter_evidence"], row, 0) == (
        False, "d3_markup_residue",
    )


def test_language_marker_mismatch_is_d4():
    fr = (
        "Le bailleur peut résilier le bail pour retard de paiement; "
        "le recours et l'arrêt du Tribunal fédéral le confirment."
    )
    row = _letterhead_row(fr, language="de")
    assert ces.passes_content_filter(fr, row, 0) == (
        False, "d4_language_marker_mismatch",
    )


def test_shipped_offline_slice_clears_the_letterhead_row_end_to_end():
    import glob
    paths = sorted(glob.glob(str(
        ROOT / "results" / "product" / "offline_slice" / "*" / "rent-default.bundle.json"
    )))
    if not paths:
        pytest.skip("no offline slice bundle")
    bundle = json.loads(Path(paths[-1]).read_text(encoding="utf-8"))
    out = ces.apply_verified_span_selection(bundle, qid="rent-default", mode="select")
    prov = out["provenance"]["counter_evidence_span"]
    assert prov["applied"] is True
    assert "gr_gerichte_ERZ 2010 25" in prov["baseline_cleared_ids"]
    row = next(d for d in out["decisions"] if d["decision_id"] == "gr_gerichte_ERZ 2010 25")
    assert row["counter_evidence_verified"] is False
    assert row["counter_evidence"] == ""
    assert row["counter_evidence_quality_filter"]["reason_code"] == "d2_letterhead_zone"
