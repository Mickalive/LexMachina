"""Independent adversarial RETRIEVAL: contract tests (offline, no network, no model).

Context: the accepted, independently audited measurement
``frontier-adversarial-discoverability`` (audit CYCLE_38794235870, gate=PASS,
named verdict ``CLASSIFICATION_ONLY``) recorded that every counter-authority
row on three accepted bundles entered through a channel the initial broad pass
had already used.  These tests pin the product-owned fix: a second retrieval
route, built from the provisional answer, whose rows the initial pass never saw.

Every test here is deterministic and network-free.  The upstream route is
exercised through the accepted adapter's normalizer with a fake client, so the
channel bookkeeping and the evidence-gated labelling are tested without ever
touching OpenCaseLaw.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query import adversarial_retrieval as adv  # noqa: E402
from product.query.bundle import build_bundle, validate_bundle  # noqa: E402
from product.query.qmap import build_map  # noqa: E402

# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

ANSWER_DE = (
    "Der Mietvertrag endet durch Beendigung der Sache. Der Mietvertrag kann "
    "auch durch Kündigung beendet werden. Eine Teilkündigung des Mietvertrags "
    "wider Treu und Glauben ist nach der bundesgerichtlichen Rechtsprechung "
    "nur unter engen Voraussetzungen zulässig."
)


def _search_hit(did: str, *, docket: str, court: str = "bger", language: str = "de",
                regeste: str = "Mietvertrag", date: str = "2023-05-04") -> dict:
    return {
        "decision_id": did,
        "canonical_decision_id": did,
        "canonical_url": f"https://mcp.opencaselaw.ch/decisions/{did}",
        "source_url": f"https://opencaselaw.ch/decision/{did}",
        "court": court,
        "court_name": "Bundesgericht",
        "language": language,
        "decision_date": date,
        "docket_number": docket,
        "title": regeste,
        "regeste": regeste,
        "snippet": regeste,
        "citation_string_de": docket,
        "relevance_score": 0.5,
        "is_canonical": True,
    }


_THEMES = [
    "Mietvertrag und Nebenkostenabrechnung", "Kündigungsfrist und Wohnung",
    "Mieterhaftung für Schäden", "Mangelminderung und Ersatz", "Betriebskostenabrechnung",
    "Untermieter und Untermietvertrag", "Kaution und Rückgabe", "Mietzinserhöhung",
    "Baumängel und Minderung", "Renovierungspflicht", "Kündigungsschutz", "Verspätete Mietzahlung",
    "Nebenkostenabrechnung", "Mieterwechsel", "Mietvertrag", "Kündigung",
    "Nebenkosten", "Mietzins", "Mängel", "Rückgabe", "Kaution", "Vermieterhaftung",
]


def _map_bundle(n: int = 40, query: str = "Mietvertrag Kündigung") -> dict:
    decisions = []
    for i in range(n):
        did = f"bger_1A_{i}_2020"
        theme = _THEMES[i % len(_THEMES)]
        decisions.append({
            "decision_id": did,
            "court": "bger",
            "language": "de",
            "rank": i + 1,
            "score": 0.5 - i / 100,
            "provenance": f"ocl:search variant=v0 page=0 seed={did}",
            "snippet": (f"Entscheid {i}: {theme}. Die Vorinstanz wendte die "
                        f"Rechtsprechung zu {_THEMES[(i + 3) % len(_THEMES)]} an "
                        f"und entschied nach dem Massstab von {_THEMES[(i + 7) % len(_THEMES)]}."),
            "cluster_id": None,
            "x": None,
            "y": None,
            "counter_status": "none",
            "canonical_url": f"https://mcp.opencaselaw.ch/decisions/{did}",
            "citation": f"1A_{i}/2020",
            "docket_number": f"1A_{i}/2020",
            "channels": ["search"],
            "decision_date": "2020-01-01",
        })
    mapped, clusters, relations = build_map(decisions)
    return build_bundle(
        query=query,
        query_variants=[query],
        answer={"prose": "", "statements": [], "cited_decision_ids": [],
                "method": "pending_generative_audit", "model": "", "status": "pending"},
        decisions=[{**d, "counter_status": d.get("counter_status") or "none"} for d in mapped],
        clusters=clusters,
        relations=relations,
        provenance={
            "retrieval": {"candidate_channels": {"search": n, "search.language_filter": 4}},
        },
    )


class _FakeClient:
    """Minimal stand-in for ``OCLClient`` recording every call it receives."""

    def __init__(self, pages: dict[str, list[dict]]):
        self.pages = pages
        self.calls: list[dict] = []
        self.hydrated: set[str] = set()
        self.network_calls = 0
        self.cache_hits = 0
        self.budget = type("B", (), {"exhausted": False})()

    def search_page(self, *, query=None, limit=None, offset=0, stage=None, **kw):
        self.calls.append({"stage": stage, "query": query, "limit": limit})
        return {"results": self.pages.get(stage or "", [])}

    def get_decision(self, decision_id, *, full_text=True):
        self.hydrated.add(decision_id)
        return {"decision_id": decision_id,
                "full_text": _TEXT_BY_ID.get(decision_id, "Die Revision wird gutgeheissen.")}

    def stats(self):
        return {"network_calls": self.network_calls, "cache_hits": self.cache_hits}


_TEXT_BY_ID = {
    "bger_9Z_77_2019": (
        "Das Bundesgericht hat erwogen, dass der Mietvertrag und die "
        "Partieabweichung eine Ausnahme darstellt und der Vorbehalt der "
        "Parteien zu beachten ist. Die Ausnahme greift nur unter engen "
        "Voraussetzungen."
    ),
    "bger_9Z_78_2019": (
        "Die Vorinstanz vertritt eine abweichende Auffassung zum Mietvertrag; "
        "der Entscheid wurde abweichend begründet und im Ergebnis abgewiesen."
    ),
    "bger_9Z_79_2018": (
        "Eine Minderheitsmeinung wurde zum Mietvertrag ausdrücklich vertreten "
        "und in der älteren Rechtsprechung bereits angelegt."
    ),
    # no limitation marker anywhere -> must NOT be labelled
    "bger_9Z_80_2017": (
        "Die Revision wird gutgeheissen. Der Mietvertrag betrifft die Kalkulation "
        "der Nebenkosten und die Abrechnung nach Verbrauch."
    ),
}

#: The topic gate (audit D2) needs a topical vocabulary; the offline bundles
#: carry an empty answer prose, so the query words play that role.
_TOPIC = ["mietvertrag", "kündigung"]


@pytest.fixture()
def fake_client(monkeypatch):
    pages = {"adversarial": [
        _search_hit("bger_1A_7_2020", docket="1A_7/2020"),          # already on the map (id)
        _search_hit("bger_9Z_77_2019", docket="9Z_77/2019"),
        _search_hit("bger_9Z_78_2019", docket="9Z_78/2019"),
        _search_hit("bger_9Z_79_2018", docket="9Z_79/2018"),
        _search_hit("bger_9Z_80_2017", docket="9Z_80/2017"),
        {"no": "decision_id"},
    ]}
    client = _FakeClient(pages)
    monkeypatch.setattr(adv, "_client", lambda *a, **k: client)
    return client


# --------------------------------------------------------------------------
# 1. the probe plan is answer-derived, not query-derived
# --------------------------------------------------------------------------

def test_plan_is_answer_derived_not_query_derived():
    plan = adv.plan_adversarial_queries("Mietvertrag", ANSWER_DE)
    assert [p["intent"] for p in plan] == ["exception", "contrary", "minority", "older_line"]
    # the ANSWER's own vocabulary anchors every probe, not the question wording
    for probe in plan:
        assert set(probe["answer_terms_used"]) & set(probe["query"].split())
        assert probe["channel"].startswith("adversarial.")


def test_plan_probes_carry_the_intent_vocabulary():
    plan = adv.plan_adversarial_queries("Mietvertrag", ANSWER_DE)
    assert "ausnahme" in plan[0]["query"]
    assert "abweichend" in plan[1]["query"]
    assert "minderheit" in plan[2]["query"]
    # audit D1 (38828034436): the /1 probes carried ZERO Italian vocabulary
    # while the report claimed DE+FR+IT.  Every probe must now show an IT
    # marker term as well.
    assert "eccezione" in plan[0]["query"]
    assert "contrario" in plan[1]["query"]
    assert "minoranza" in plan[2]["query"]
    assert ("in passato" in plan[3]["query"]
            or "precedente giurisprudenza" in plan[3]["query"])


def test_plan_interleaves_de_fr_it_in_every_probe():
    for probe in adv.plan_adversarial_queries("Mietvertrag", ANSWER_DE):
        assert set(probe["intent_term_languages"]) == {"de", "fr", "it"}, probe["intent"]


def test_interleave_round_robins_languages():
    terms = [("de", "d1"), ("de", "d2"), ("fr", "f1"), ("it", "i1"), ("it", "i2")]
    assert adv.interleave_intent_terms(terms, 6) == ["d1", "f1", "i1", "d2", "i2"]
    assert adv.interleave_intent_terms(terms, 99) == ["d1", "f1", "i1", "d2", "i2"]


def test_plan_is_vacuous_on_an_empty_answer():
    """audit D4 (38828034436): the documented vacuous-pass guard must exist."""
    assert adv.plan_adversarial_queries("Mietvertrag", "") == []
    assert adv.plan_adversarial_queries("Mietvertrag", "   \n") == []


def test_pipeline_records_a_vacuous_pass_on_an_empty_answer():
    from product.query import pipeline
    bundle = _map_bundle(n=10)  # fixture answer prose is empty
    out = pipeline.adversarial_retrieval_pass(bundle, retrieval_mode="offline")
    prov = out["provenance"]["adversarial_retrieval"]
    assert prov["skipped"] is True
    assert "vacuous" in prov["skip_reason"]
    assert prov["n_new_rows"] == 0


def test_plan_changes_with_the_answer():
    a = adv.plan_adversarial_queries("Mietvertrag", ANSWER_DE)
    b = adv.plan_adversarial_queries("Mietvertrag", "Die Arbeitslosenversicherung endet mit Ablauf.")
    assert a[0]["query"] != b[0]["query"]


def test_plan_is_deterministic():
    assert adv.plan_adversarial_queries("x", ANSWER_DE) == adv.plan_adversarial_queries("x", ANSWER_DE)


def test_answer_key_terms_drops_stopwords_and_digits():
    terms = adv.answer_key_terms("Der Vertrag und die 12 franken für die Miete 2024")
    assert "vertrag" in terms and "miete" in terms
    assert "und" not in terms and "der" not in terms and "2024" not in terms


def test_product_channels_are_disjoint_from_adapter_channels():
    from ocl_adapter.normalize import (
        CHANNEL_CITE_IN, CHANNEL_CITE_OUT, CHANNEL_LANG, CHANNEL_LEADING,
        CHANNEL_LOOKUP, CHANNEL_SEARCH,
    )
    adapter_channels = {CHANNEL_SEARCH, CHANNEL_LANG, CHANNEL_LEADING,
                        CHANNEL_CITE_IN, CHANNEL_CITE_OUT, CHANNEL_LOOKUP}
    assert not adapter_channels & set(adv.ADVERSARIAL_CHANNELS)
    assert all(c.startswith("adversarial.") for c in adv.ADVERSARIAL_CHANNELS)


# --------------------------------------------------------------------------
# 2. the second route actually excludes what the initial pass already saw
# --------------------------------------------------------------------------

def test_fetch_excludes_ids_and_identities_already_on_the_map(fake_client):
    bundle = _map_bundle(n=40)
    existing_ids = {str(d["decision_id"]) for d in bundle["decisions"]}
    ids = set(existing_ids)
    identities = set()
    for d in bundle["decisions"]:
        docket = str(d["docket_number"])
        identities.add((str(d["court"]).lower(), docket.lower().replace("/", "")))
    plan = adv.plan_adversarial_queries("Mietvertrag", ANSWER_DE)
    out = adv.fetch_adversarial_candidates(
        "Mietvertrag", plan, mode="offline", exclude_ids=ids, exclude_identities=identities)
    new_ids = {str(c["decision_id"]) for c in out["candidates"]}
    assert "bger_1A_7_2020" not in new_ids, "an initial-pass decision must never re-enter"
    assert new_ids == {"bger_9Z_77_2019", "bger_9Z_78_2019",
                       "bger_9Z_79_2018", "bger_9Z_80_2017"}
    assert out["provenance"]["n_candidates"] == 4


def test_fetch_excludes_by_identity_when_the_id_differs(fake_client):
    """A citation edge and a search hit can carry the same decision under different ids."""
    bundle = _map_bundle(n=5)
    identities = {("bger", "1a72020")}
    out = adv.fetch_adversarial_candidates(
        "Mietvertrag", adv.plan_adversarial_queries("Mietvertrag", ANSWER_DE),
        mode="offline", exclude_ids=set(), exclude_identities=identities)
    assert "bger_1A_7_2020" not in {c["decision_id"] for c in out["candidates"]}


def test_fetch_uses_a_dedicated_stage_and_records_channels(fake_client):
    out = adv.fetch_adversarial_candidates(
        "Mietvertrag", adv.plan_adversarial_queries("Mietvertrag", ANSWER_DE),
        mode="offline", exclude_ids=set(), exclude_identities=set())
    assert fake_client.calls and all(c["stage"] == "adversarial" for c in fake_client.calls)
    assert all(c["channel"].startswith("adversarial.") for c in out["candidates"])
    assert set(out["provenance"]["channels"]) <= set(adv.ADVERSARIAL_CHANNELS)


def test_fetch_never_repeats_a_decision_across_probes(fake_client):
    out = adv.fetch_adversarial_candidates(
        "Mietvertrag", adv.plan_adversarial_queries("Mietvertrag", ANSWER_DE),
        mode="offline", exclude_ids=set(), exclude_identities=set())
    ids = [c["decision_id"] for c in out["candidates"]]
    assert len(ids) == len(set(ids))


def test_fetch_hydration_is_bounded(fake_client):
    out = adv.fetch_adversarial_candidates(
        "Mietvertrag", adv.plan_adversarial_queries("Mietvertrag", ANSWER_DE),
        mode="offline", exclude_ids=set(), exclude_identities=set(), hydrate_top=1)
    assert len(fake_client.hydrated) <= 1
    assert out["provenance"]["n_hydrated"] == len(fake_client.hydrated)


def test_fetch_survives_upstream_failure_and_reports_it(monkeypatch):
    class _Boom:
        budget = type("B", (), {"exhausted": False})()

        def search_page(self, **kw):
            raise RuntimeError("upstream 503")

        def stats(self):
            return {"network_calls": 0, "cache_hits": 0}

    monkeypatch.setattr(adv, "_client", lambda *a, **k: _Boom())
    out = adv.fetch_adversarial_candidates(
        "Mietvertrag", adv.plan_adversarial_queries("Mietvertrag", ANSWER_DE),
        mode="offline", exclude_ids=set(), exclude_identities=set())
    assert out["candidates"] == []
    assert out["provenance"]["failures"]
    assert "503" in json.dumps(out["provenance"]["failures"])


# --------------------------------------------------------------------------
# 3. classification is evidence-gated
# --------------------------------------------------------------------------

@pytest.mark.parametrize("intent,did,status", [
    ("exception", "bger_9Z_77_2019", "candidate-limiting"),
    ("contrary", "bger_9Z_78_2019", "candidate-contrary"),
    ("minority", "bger_9Z_79_2018", "contrary_or_exception"),
    ("older_line", "bger_9Z_79_2018", "candidate-limiting"),
])
def test_marker_in_own_text_authorises_a_counter_label(intent, did, status):
    got, evidence, markers = adv.classify_against_intent(
        _TEXT_BY_ID[did], intent, topic_terms=_TOPIC)
    assert got == status
    assert evidence, "a label must point at a verbatim sentence"
    assert markers


def test_no_marker_means_no_label():
    got, evidence, markers = adv.classify_against_intent(
        _TEXT_BY_ID["bger_9Z_80_2017"], "exception", topic_terms=_TOPIC)
    assert got is None and evidence == "" and markers == []


def test_label_requires_the_decisions_own_text():
    got, _, _ = adv.classify_against_intent("", "exception", topic_terms=_TOPIC)
    assert got is None


def test_topic_gate_refuses_offdomain_markers():
    """audit D2 off-domain: an Arbeitsvertrag decision must not be labelled
    inside a Mietvertrag/locazione research question."""
    text = ("Der Arbeitsvertrag kann ausserordentlich gekündigt werden. "
            "Die Kündigung stellt eine Ausnahme von der Vertragsfreiheit dar.")
    got, _, _ = adv.classify_against_intent(
        text, "exception", topic_terms=["mietvertrag", "locazione"])
    assert got is None, "no topical overlap -> no label"
    got2, evidence, _ = adv.classify_against_intent(
        text, "exception", topic_terms=["arbeitsvertrag"])
    assert got2 == "candidate-limiting" and evidence


def test_topic_gate_without_vocabulary_issues_no_label():
    """No answer/query vocabulary -> the pass keeps the row unlabelled rather
    than licensing from markers alone."""
    got, _, _ = adv.classify_against_intent(_TEXT_BY_ID["bger_9Z_77_2019"],
                                           "exception", topic_terms=[])
    assert got is None


def test_eintretens_boilerplate_never_licenses_a_label():
    """audit D2 boilerplate: the BGer admissibility formula must not carry a
    limiting label by itself."""
    text = ("Auf die Beschwerde des Mieters ist, unter Vorbehalt der genügenden "
            "Begründung, einzutreten. Im Übrigen wird die Beschwerde abgewiesen.")
    got, _, _ = adv.classify_against_intent(
        text, "exception", topic_terms=["mieter", "beschwerde"])
    assert got is None


def test_dismissal_narration_never_licenses_contrary():
    """audit D2 inverted: a rejected Berufung means the challenged ruling stood."""
    text = ("Die abweichende Auffassung der Vorinstanz wurde mit der Berufung "
            "des Vermieters abgewiesen; der Mietvertrag bleibt in Kraft.")
    got, _, _ = adv.classify_against_intent(
        text, "contrary", topic_terms=["mietvertrag", "vermieter"])
    assert got is None


def test_audit_inverted_examples_get_no_label():
    """The four affirmatively inverted rows of audit 38828034436, verbatim."""
    cases = [
        # bge_136 III 190 — "nicht entgegen" affirms the landlord may terminate
        ("Steht dem Recht des Vermieters nicht entgegen, den Mietvertrag zu "
         "kündigen.", ["mietvertrag", "vermieter"]),
        # bge_115 II 78 / bge_111 II 384 — recours rejected, judgment confirmed
        ("Le Tribunal fédéral a rejeté le recours et confirmé l'arrêt attaqué "
         "concernant le bail commercial.", ["bail", "commercial"]),
        # bge_123 III 124 — Berufung dismissed
        ("Die eidgenössische Berufung, welche vom Bundesgericht abgewiesen "
         "wird, betrifft den Mietvertrag.", ["mietvertrag"]),
    ]
    for text, topic in cases:
        got, _, _ = adv.classify_against_intent(text, "contrary", topic_terms=topic)
        assert got is None, f"inverted label licensed: {text!r}"


def test_markers_are_reported_from_the_evidence_sentence_only():
    """audit D2: counter_markers must not be the union over the whole text."""
    text = ("Ausgenommen von dieser Regelung sind die Nebenkosten. "
            "Der Mietvertrag bildet eine Ausnahme von der allgemeinen "
            "Kündigungsfreiheit.")
    got, evidence, markers = adv.classify_against_intent(
        text, "exception", topic_terms=["mietvertrag"])
    assert got == "candidate-limiting"
    assert "ausnahme" in markers
    assert "ausgenommen" not in markers, "markers outside the cited sentence must not be reported"
    assert "mietvertrag" in evidence.lower()


def test_bundle_topic_terms_prefers_the_answer_then_the_query():
    bundle = {"query": "Mietvertrag Kündigung", "answer": {"prose": ANSWER_DE}}
    terms = adv.bundle_topic_terms(bundle)
    # answer-derived terms lead; query tokens fill in
    assert "mietvertrag" in terms
    assert "kündigung" in terms
    assert adv.bundle_topic_terms({"query": "", "answer": {"prose": ""}}) == []


def test_bundle_topic_terms_bridges_languages_via_the_pool():
    """Swiss case law is trilingual: an Italian answer must still license a
    German BGE abstract that the initial pool already deemed on-topic."""
    pool = []
    for i in range(10):
        one_off = " Aufhebungsvereinbarung" if i == 0 else ""
        pool.append({"regeste": (f"Mietvertrag; Kündigung; Mietzins {i}. "
                                 f"Wohnraummieter Vermieter Mietverhältnis{one_off}")})
    bundle = {
        "query": "Quando può il locatore sciogliere il contratto di locazione?",
        "answer": {"prose": "Il locatore può disdetta il contratto di locazione "
                            "solo in casi eccezionali."},
        "decisions": pool,
    }
    terms = adv.bundle_topic_terms(bundle)
    assert "mietvertrag" in terms, "pool vocabulary must bridge IT answer -> DE decision"
    assert "contratto" in terms and "locazione" in terms, "answer terms lead"
    # a one-off token in a single decision must not become topical
    assert "aufhebungsvereinbarung" not in terms


# --------------------------------------------------------------------------
# 4. the pass joins the map without moving anything the jurist already sees
# --------------------------------------------------------------------------

def test_apply_appends_unseen_rows_and_freezes_rendered_geometry(fake_client):
    bundle = _map_bundle(n=40)
    before = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"], bool(d.get("is_outlier")))
              for d in bundle["decisions"]}
    fetched = adv.fetch_adversarial_candidates(
        bundle["query"], adv.plan_adversarial_queries(bundle["query"], ANSWER_DE),
        mode="offline",
        exclude_ids=set(before),
        exclude_identities=set())
    out = adv.apply_adversarial_pass(bundle, fetched["candidates"], fetched["provenance"])
    assert validate_bundle(out) == []
    after = {d["decision_id"]: (d["x"], d["y"], d["cluster_id"], bool(d.get("is_outlier")))
             for d in out["decisions"]}
    for did, geo in before.items():
        assert after[did] == geo, "an already-rendered point must never move"
    assert len(out["decisions"]) == len(before) + 4
    prov = out["provenance"]["adversarial_retrieval"]
    assert prov["n_new_rows"] == 4
    assert prov["n_counter_rows"] == 3, "three of four carry a real limitation marker"
    assert prov["channels"]


def test_apply_labels_only_marker_carrying_rows(fake_client):
    bundle = _map_bundle(n=40)
    fetched = adv.fetch_adversarial_candidates(
        bundle["query"], adv.plan_adversarial_queries(bundle["query"], ANSWER_DE),
        mode="offline", exclude_ids={d["decision_id"] for d in bundle["decisions"]},
        exclude_identities=set())
    out = adv.apply_adversarial_pass(bundle, fetched["candidates"], fetched["provenance"])
    by_id = {d["decision_id"]: d for d in out["decisions"]}
    assert by_id["bger_9Z_80_2017"]["counter_status"] == "none"
    assert by_id["bger_9Z_80_2017"]["counter_evidence"] == ""
    labelled = by_id["bger_9Z_77_2019"]
    assert labelled["counter_status"] == "candidate-limiting"
    assert labelled["counter_evidence_verified"] is True
    assert labelled["counter_evidence"].strip()


def test_apply_ranks_new_rows_after_the_conventional_list(fake_client):
    bundle = _map_bundle(n=40)
    max_initial = max(d["rank"] for d in bundle["decisions"])
    fetched = adv.fetch_adversarial_candidates(
        bundle["query"], adv.plan_adversarial_queries(bundle["query"], ANSWER_DE),
        mode="offline", exclude_ids={d["decision_id"] for d in bundle["decisions"]},
        exclude_identities=set())
    out = adv.apply_adversarial_pass(bundle, fetched["candidates"], fetched["provenance"])
    new_ids = set(out["provenance"]["adversarial_retrieval"]["new_row_ids"])
    new_ranks = [d["rank"] for d in out["decisions"] if d["decision_id"] in new_ids]
    assert all(r > max_initial for r in new_ranks)


def test_apply_records_counter_rows_outside_the_initial_channel_inventory(fake_client):
    bundle = _map_bundle(n=40)
    fetched = adv.fetch_adversarial_candidates(
        bundle["query"], adv.plan_adversarial_queries(bundle["query"], ANSWER_DE),
        mode="offline", exclude_ids={d["decision_id"] for d in bundle["decisions"]},
        exclude_identities=set())
    out = adv.apply_adversarial_pass(bundle, fetched["candidates"], fetched["provenance"])
    initial = set(out["provenance"]["retrieval"]["candidate_channels"])
    counter = [d for d in out["decisions"]
               if d.get("counter_status") in {"candidate-limiting", "candidate-contrary",
                                               "contrary_or_exception", "limiting"}]
    assert counter, "the pass must produce at least one labelled counter row"
    assert all(set(d["channels"]) - initial for d in counter), \
        "every counter row must carry a channel the initial retrieval never used"


def test_apply_is_a_noop_when_nothing_new_is_retrieved():
    bundle = _map_bundle(n=20)
    before = json.dumps(bundle["decisions"], sort_keys=True)
    out = adv.apply_adversarial_pass(bundle, [], {"probes": []})
    prov = out["provenance"]["adversarial_retrieval"]
    assert prov["attempted"] is False and prov["n_new_rows"] == 0
    assert json.dumps(out["decisions"], sort_keys=True) == before


def test_apply_does_not_mutate_the_input_bundle(fake_client):
    bundle = _map_bundle(n=40)
    snapshot = json.dumps(bundle, sort_keys=True)
    fetched = adv.fetch_adversarial_candidates(
        bundle["query"], adv.plan_adversarial_queries(bundle["query"], ANSWER_DE),
        mode="offline", exclude_ids={d["decision_id"] for d in bundle["decisions"]},
        exclude_identities=set())
    adv.apply_adversarial_pass(bundle, fetched["candidates"], fetched["provenance"])
    assert json.dumps(bundle, sort_keys=True) == snapshot


def test_pipeline_seam_degrades_without_raising(monkeypatch):
    """The whole pipeline seam must stay green even if the new route is dead."""
    from product.query import pipeline

    def _dead(*a, **k):
        raise RuntimeError("adversarial upstream unavailable")

    monkeypatch.setattr(pipeline, "fetch_adversarial_candidates", _dead)
    monkeypatch.setattr(pipeline, "run_generative_audit", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("no provider")))
    bundle = _map_bundle(n=30)
    out = pipeline.enrich_query_bundle(bundle, retrieval_mode="fixture",
                                       fixture_generation=True, evidence_count=0)
    assert validate_bundle(out) == []
    assert len(out["decisions"]) >= 30

# --------------------------------------------------------------------------
# 5. the measurement seam refuses to self-score
# --------------------------------------------------------------------------

def test_independence_check_refuses_without_the_accepted_mount(monkeypatch, tmp_path):
    """A self-scored metric is exactly the evidence the factory forbids."""
    import importlib
    mod = importlib.import_module("product.adversarial_independence_check")
    monkeypatch.setattr(mod, "TEAM_PACKAGE", tmp_path / "not-there")
    monkeypatch.setattr(mod, "DEFAULT_MOUNT", tmp_path / "not-there")
    with pytest.raises(SystemExit) as exc:
        mod.score({"decisions": [{"decision_id": "x"}], "clusters": [], "provenance": {}})
    assert "accepted frontier mount not found" in str(exc.value)


def test_independence_check_requires_a_real_population(tmp_path):
    import importlib
    mod = importlib.import_module("product.adversarial_independence_check")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"decisions": []}), encoding="utf-8")
    assert mod.main(["--bundle", str(bad)]) == 4
    assert mod.main(["--bundle", str(tmp_path / "missing.json")]) == 4
