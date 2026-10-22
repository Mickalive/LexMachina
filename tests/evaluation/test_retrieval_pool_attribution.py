"""Tests for ``evaluation/retrieval_pool_attribution.py`` (v62 retrieval-pool attribution).

These tests are OFFLINE.  They never touch the network: the instrument's
fetcher is injected, so the whole measurement path is exercised against a
synthetic mount, a synthetic accepted record and a synthetic OpenCaseLaw.

WHAT IS ASSERTED HERE (and nothing else)
-----------------------------------------
* the instrument uses the ACCEPTED concept rule and the ACCEPTED row-text
  projection (it imports them; the tests pin that behaviour against a manual
  computation, so a future edit that re-derives the rule is caught);
* the three frozen cause classes are discriminated correctly on synthetic
  bytes (BEYOND_PAGE0 / PAGE0_ONLY / NEVER);
* the served page-0 selection matches the product's own provenance string;
* the non-vacuity battery really fires: a failed control yields exit 2
  (NOT_MEASURED_VACUOUS), never a defect verdict;
* ``--offline`` never claims a measurement.

NO FROZEN RULE, THRESHOLD, PREDICATE OR SUCCESS RULE IS RE-DERIVED OR
RE-TUNED HERE.  Every expectation is either (a) the frozen hypothesis' own rule
committed before the claim-bearing run, or (b) a mechanical identity.
"""
from __future__ import annotations

import json
import sys
import tempfile
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import subject_match_audit as SMA  # noqa: E402
from evaluation import retrieval_pool_attribution as RPA  # noqa: E402

PACKET = "39319405429"
DE = "de-kapitalverletzung"
FR = "fr-bail-entretien"
IT = "it-responsabilita-medica"

DE_QUESTION = "Kapitalverletzung Überwachungspflicht?"
FR_QUESTION = "Défaut d'entretien du bailleur résiliation?"
IT_QUESTION = "Responsabilità del medico per errore terapeutico?"

#: The synthetic world uses the product's own page size so that the fidelity
#: control (Jaccard of the served and live page-0 id sets) is exercised with a
#: realistic denominator.
LIMIT = 10
NEUTRAL = "unrelated labour-law content"


def _row(decision_id: str, text: str, **extra) -> dict:
    row = {
        "decision_id": decision_id,
        "title": text,
        "regeste": "",
        "snippet": "",
        "full_text": "",
        "citation": "",
        "channels": ["search"],
        "provenance": "ocl:search variant=original:any:test01 page=0",
    }
    row.update(extra)
    return row


def _bundle(qid: str, question: str, rows: list[dict], *, limit: int = LIMIT,
            variant: str = "original:any:test01", total: int = 24) -> dict:
    return {
        "bundle_version": "test",
        "query": question,
        "decisions": rows,
        "clusters": [],
        "relations": [],
        "provenance": {
            "stages": ["search"],
            "searches": [{
                "stage": "search", "variant_id": variant, "kind": "original",
                "language_filter": None, "page": 0, "offset": 0, "limit": limit,
                "total": total, "total_is_lower_bound": True, "returned": limit,
                "has_more": True, "next_offset": limit,
                "result_set_id": "rs_test", "remote_degraded": False, "note": None,
            }],
            "targets": {"target": limit, "max_candidates": limit, "page_size": limit,
                        "max_pages_per_variant": 1, "max_requests": 1,
                        "target_reached": True, "pre_trim_candidates": limit,
                        "trimmed_to_max_candidates": False},
            "request_summary": {"requests_logged": 1, "cache_hits": 1, "network_calls": 0},
            "cache_stats": {"hits": 1, "misses": 0, "writes": 0, "n_keys": 1},
        },
    }


def _search_hit(decision_id: str, text: str, lang: str = "de") -> dict:
    return {
        "decision_id": decision_id,
        "language": lang,
        "court": "Bundesgericht",
        "docket_number": "1A.1/2020",
        "title": text,
        "regeste": text,
        "snippet": text,
        "citation_string_de": "Bundesgericht 1A.1/2020",
    }


def _fake_fetcher(pages: dict):
    """``pages`` maps a query text -> its ranked list of raw hits.

    The fake serves the slice the instrument asks for and reports
    ``has_more`` exactly like the live endpoint does, so the scan loop, the
    page budget and the pool-completeness control are all exercised.
    """

    def fetcher(url: str, timeout: float) -> dict:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        query = (params.get("query") or [""])[0]
        offset = int((params.get("offset") or ["0"])[0])
        limit = int((params.get("limit") or ["50"])[0])
        if "/decisions/" in parsed.path:
            return {"decision_id": "x", "full_text": ""}
        hits = list(pages.get(query, []))
        window = hits[offset:offset + limit]
        return {
            "total": len(hits),
            "total_is_lower_bound": True,
            "returned": len(window),
            "results": window,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < len(hits),
            "next_offset": offset + limit,
            "result_set_id": "rs_fake",
        }

    return fetcher


def _neutral_rows(n: int) -> list[dict]:
    return [_row(f"n{i}", NEUTRAL) for i in range(n)]


def _pages(de_hits: list, nonsense_hits: list | None = None) -> dict:
    """A complete fake corpus: the question's own ranked pool plus the two
    concept-only oracle queries plus the two cross-language questions."""
    return {
        DE_QUESTION: list(de_hits),
        "Kapitalverletzung": [_search_hit("p_kap", "Kapitalverletzung im Arbeitsrecht")],
        "Überwachungspflicht": [_search_hit("p_ueb", "Überwachungspflicht im Arbeitsrecht")],
        FR_QUESTION: [_search_hit("fr1", "defaut entretien bailleur resiliation")],
        IT_QUESTION: [_search_hit("it1", "responsabilita medico errore terapeutico")],
        RPA.NONSENSE_QUERY: list(nonsense_hits or []),
    }


def _build_world(tmp: Path, *, served_rows: list[dict]):
    """A synthetic accepted mount + accepted record."""
    mount = tmp / "product"
    qdir = mount / "results" / "product" / "gate_packet" / PACKET / "questions"
    qdir.mkdir(parents=True)
    (qdir / f"{DE}.bundle.json").write_text(json.dumps(_bundle(DE, DE_QUESTION, served_rows)))
    (qdir / f"{DE}.question.json").write_text(json.dumps({"qid": DE, "question": DE_QUESTION}))
    (qdir / f"{FR}.bundle.json").write_text(json.dumps(_bundle(
        FR, FR_QUESTION, [_row("fr1", "defaut entretien bailleur resiliation")])))
    (qdir / f"{FR}.question.json").write_text(json.dumps({"qid": FR, "question": FR_QUESTION}))
    (qdir / f"{IT}.bundle.json").write_text(json.dumps(_bundle(
        IT, IT_QUESTION, [_row("it1", "responsabilita medico errore terapeutico")])))
    (qdir / f"{IT}.question.json").write_text(json.dumps({"qid": IT, "question": IT_QUESTION}))

    repo = tmp / "repo"
    rec_dir = repo / "results" / "evaluation" / "mapping_free_recall_falsifier"
    rec_dir.mkdir(parents=True)
    concepts = SMA.question_concepts(DE_QUESTION)
    cov = RPA.coverage(served_rows, concepts)
    rec = {
        "schema": "lex-evaluation-mapping-free-recall-falsifier/1",
        "per_question": [{
            "qid": DE,
            "concepts": concepts,
            "concept_row_counts": cov["concept_row_counts"],
            "concepts_with_zero_rows": cov["concepts_with_zero_rows"],
        }],
    }
    (rec_dir / "39693031072.json").write_text(json.dumps(rec))
    return mount, repo


def _run_world(tmp: Path, pool_pages: dict, served_rows: list[dict]):
    mount, repo = _build_world(tmp, served_rows=served_rows)
    fetcher = _fake_fetcher(pool_pages)
    return RPA.run("test", None, str(mount), repo, max_pages=4, live=True,
                   fetcher=fetcher, sleep=lambda _s: None)


# --------------------------------------------------------------------------- #
# rule reuse
# --------------------------------------------------------------------------- #
def test_concept_rule_is_the_accepted_rule():
    concepts = RPA.SMA.question_concepts(DE_QUESTION)
    assert concepts == SMA.question_concepts(DE_QUESTION)
    assert "kapitalverletzung" in concepts
    assert "uberwachungspflicht" in concepts


def test_coverage_uses_the_accepted_row_projection():
    rows = [_row("a", "Kapitalverletzung im Arbeitsrecht"),
            _row("b", "unrelated text")]
    concepts = ["kapitalverletzung", "unrelated"]
    cov = RPA.coverage(rows, concepts)
    manual = {c: sum(1 for r in rows if c in SMA.deaccent(SMA.row_match_text(r)).lower())
              for c in concepts}
    assert cov["concept_row_counts"] == manual
    assert cov["concepts_with_zero_rows"] == []


def test_lexical_row_projection_uses_citation_string():
    raw = _search_hit("x1", "Kapitalverletzung")
    row = RPA.lexical_row(raw)
    assert row["decision_id"] == "x1"
    assert row["citation"] == "Bundesgericht 1A.1/2020"
    assert row["full_text"] == ""
    assert "kapitalverletzung" in SMA.deaccent(SMA.row_match_text(row)).lower()


def test_oracle_query_text_keeps_the_original_spelling():
    assert RPA.oracle_query_text(DE_QUESTION, "kapitalverletzung") == "Kapitalverletzung"
    assert RPA.oracle_query_text(DE_QUESTION, "uberwachungspflicht") == "Überwachungspflicht"


def test_served_page0_rows_selection_uses_the_products_own_provenance():
    rows = [
        {"decision_id": "a", "provenance": "ocl:search variant=original:any:test01 page=0"},
        {"decision_id": "b", "provenance": "ocl:search variant=original:any:test01 page=1"},
        {"decision_id": "c", "provenance": "ocl:search variant=language_filter:it:abc page=0"},
    ]
    picked = RPA.served_page0_rows({"decisions": rows}, "original:any:test01")
    assert [r["decision_id"] for r in picked] == ["a"]


# --------------------------------------------------------------------------- #
# cause classification
# --------------------------------------------------------------------------- #
def test_beyond_page0_class_is_detected():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        served = _neutral_rows(LIMIT)
        de_hits = [_search_hit(f"n{i}", NEUTRAL) for i in range(LIMIT)]
        de_hits += [_search_hit(f"n{i}", NEUTRAL) for i in range(LIMIT, LIMIT + 2)]
        de_hits += [_search_hit("p_kap_hit", "Kapitalverletzung im Arbeitsrecht")]
        de_hits += [_search_hit("p_ueb_hit", "Überwachungspflicht im Arbeitsrecht")]
        code, record = _run_world(tmp, _pages(de_hits), served)
        assert record["verdict"] == RPA.VERDICT_DEFECT, record.get("attribution")
        assert code == RPA.EXIT_DEFECT
        classes = {pc["concept"]: pc["cause_class"] for pc in record["attribution"]["per_concept"]}
        assert classes["kapitalverletzung"] == RPA.CAUSE_BEYOND_PAGE0
        assert classes["uberwachungspflicht"] == RPA.CAUSE_BEYOND_PAGE0


def test_never_covered_class_is_detected():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        served = _neutral_rows(LIMIT)
        de_hits = [_search_hit(f"n{i}", NEUTRAL) for i in range(LIMIT + 2)]
        code, record = _run_world(tmp, _pages(de_hits), served)
        assert record["verdict"] == RPA.VERDICT_DEFECT
        assert code == RPA.EXIT_DEFECT
        classes = {pc["concept"]: pc["cause_class"] for pc in record["attribution"]["per_concept"]}
        assert classes["kapitalverletzung"] == RPA.CAUSE_NEVER


def test_page0_only_class_is_detected():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # The served bundle drops the one row of the fetched page 0 that
        # carries the concept -> an ASSEMBLY defect, not a budget defect.
        served = _neutral_rows(LIMIT - 1)
        de_hits = [_search_hit(f"n{i}", NEUTRAL) for i in range(LIMIT - 1)]
        de_hits += [_search_hit("p_kap_hit", "Kapitalverletzung im Arbeitsrecht")]
        de_hits += [_search_hit(f"m{i}", NEUTRAL) for i in range(3)]
        code, record = _run_world(tmp, _pages(de_hits), served)
        assert record["verdict"] == RPA.VERDICT_DEFECT, record.get("attribution")
        classes = {pc["concept"]: pc["cause_class"] for pc in record["attribution"]["per_concept"]}
        assert classes["kapitalverletzung"] == RPA.CAUSE_PAGE0_ONLY
        assert code == RPA.EXIT_DEFECT


# --------------------------------------------------------------------------- #
# controls
# --------------------------------------------------------------------------- #
def test_failed_control_yields_vacuous_not_a_defect():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        served = _neutral_rows(LIMIT)
        de_hits = [_search_hit(f"n{i}", NEUTRAL) for i in range(LIMIT)]
        de_hits += [_search_hit("p_kap_hit", "Kapitalverletzung im Arbeitsrecht")]
        # the nonsense control now returns a row -> c2 must fail
        code, record = _run_world(tmp, _pages(de_hits, nonsense_hits=[_search_hit("n1", "noise")]), served)
        assert code == RPA.EXIT_VACUOUS
        assert record["verdict"] == RPA.VERDICT_VACUOUS
        assert record["non_vacuity"]["controls"]["c2_nonsense_query_zero_rows"]["holds"] is False


def test_unreachable_oracle_is_vacuous():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        served = _neutral_rows(LIMIT)
        de_hits = [_search_hit(f"n{i}", NEUTRAL) for i in range(LIMIT + 2)]
        pages = _pages(de_hits)
        pages["Kapitalverletzung"] = [_search_hit("p_kap", "still unrelated")]
        pages["Überwachungspflicht"] = [_search_hit("p_ueb", "still unrelated")]
        code, record = _run_world(tmp, pages, served)
        assert code == RPA.EXIT_VACUOUS
        assert record["verdict"] == RPA.VERDICT_VACUOUS
        assert record["non_vacuity"]["controls"]["c7_oracle_concept_reachable"]["holds"] is False


def test_offline_mode_never_claims_a_measurement():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        mount, repo = _build_world(tmp, served_rows=_neutral_rows(LIMIT))
        code, record = RPA.run("test", None, str(mount), repo, live=False)
        assert code == RPA.EXIT_VACUOUS
        assert record["verdict"] == RPA.VERDICT_VACUOUS
        assert record["live_measurement"] is False
