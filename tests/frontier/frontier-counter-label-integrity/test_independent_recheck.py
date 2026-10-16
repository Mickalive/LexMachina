"""Independent adversarial re-scoring of the primary population.

This module deliberately does NOT import the team's rubric or normaliser.  It is
a second, independently written implementation of the frozen rubric, used to try
to REFUTE the committed result: if the two implementations disagree on any of the
seven primary rows, this test fails and the verdict is withheld.

It shares only what it must share: the frozen lexicon/threshold file and the
bundle bytes.
"""

from __future__ import annotations

import json
import re
import unicodedata

import pytest

PRIMARY_BUNDLES = (
    ("de-kapitalverletzung", "de-kapitalverletzung"),
    ("fr-bail-entretien", "fr-bail-entretien"),
    ("it-responsabilita-medica", "it-responsabilita-medica"),
)

EXPECTED_PRIMARY = {
    "zh_bezirksgericht_buelach_AH240008": "OFF-DOMAIN",
    "zh_obergericht_LA190008": "OFF-DOMAIN",
    "zh_obergericht_LA250006": "OFF-DOMAIN",
    "ge_gerichte_4A_286_2015": "UNBACKED",
    "ti_gerichte_13.2019.12": "BOILERPLATE-ONLY",
    "ti_gerichte_16.2021.24": "FRAGMENT",
    "ti_gerichte_12.2025.23": "UNBACKED",
}


def _fold(text: str, digraphs: bool = True) -> str:
    s = unicodedata.normalize("NFKC", str(text or "")).replace("\u00ad", "").lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    if digraphs:
        for a, b in (("ue", "u"), ("oe", "o"), ("ae", "a")):
            s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def _stems(text: str) -> list[str]:
    out = []
    for tok in re.split(r"[^0-9a-z]+", _fold(text)):
        if not tok:
            continue
        for suf in ("ungen", "ung", "heit", "keit", "lich", "isch", "ieren", "en", "er", "es", "e", "s"):
            if tok.endswith(suf) and len(tok) - len(suf) >= 4:
                tok = tok[: -len(suf)]
                break
        out.append(tok)
    return out


def _marker_hit(hay: list[str], marker: str) -> bool:
    want = _stems(marker)
    if len(want) == 1:
        return want[0] in hay
    return any(hay[i:i + len(want)] == want for i in range(len(hay) - len(want) + 1))


def _anchor_hit(hay: list[str], anchor: str) -> bool:
    want = _stems(anchor)
    if len(want) > 1:
        return any(hay[i:i + len(want)] == want for i in range(len(hay) - len(want) + 1))
    return any(len(t) >= 5 and len(a) >= 5 and t[:5] == a[:5] for t in hay for a in want)


def _rx(text: str, patterns) -> list[str]:
    return [p for p in patterns if re.search(p, text, re.IGNORECASE)]


def _classify(row: dict, lex: dict, anchors: dict) -> tuple[str, str]:
    lang = row["language"]
    ev = str(row.get("counter_evidence") or "")
    ev_rx = _fold(ev, digraphs=False)
    ev_tok = _stems(ev)
    ctx_tok = _stems(" ".join(x for x in (ev, row.get("title"), row.get("regeste")) if x))
    ev_title_tok = _stems(" ".join(x for x in (ev, row.get("title")) if x))

    markers = list(lex["counter_intent_markers"][lang].get("product_adversarial_terms") or []) + \
        list(lex["counter_intent_markers"][lang].get("frozen_additions") or [])
    m_hits = sorted({m for m in markers if _marker_hit(ev_tok, m)})
    inv = _rx(ev_rx, lex["polarity_inversion"][lang])
    proc = _rx(ev_rx, lex["procedural_formula"][lang])
    outc = _rx(ev_rx, lex["procedural_outcome_words"][lang])
    ptr = _rx(_fold(ev).strip(), lex["fragment_pointer"])
    domain_ev_title = sorted({a for a in anchors["domain"] if _anchor_hit(ev_title_tok, a)})
    pivot_ctx = sorted({a for a in anchors["pivot"] if _anchor_hit(ctx_tok, a)})
    lang_ok = lang in anchors["expected_languages"]

    if not ev.strip():
        return "UNBACKED", "evidence_absent"
    if ptr:
        return "FRAGMENT", "pointer_only"
    if proc and not m_hits:
        return "BOILERPLATE-ONLY", "procedural_formula_no_intent"
    if inv:
        return "INVERTED", "polarity_inverted"
    if not pivot_ctx or not lang_ok:
        return "OFF-DOMAIN", "pivot_absent"
    if not m_hits:
        return "UNBACKED", "no_intent_marker"
    if not domain_ev_title:
        return "UNBACKED", "no_domain_anchor"
    return "SUPPORTED", "supported"


@pytest.fixture(scope="module")
def independent(request):
    rules = json.loads(
        open(
            request.config.rootpath / "results/frontier/frontier-counter-label-integrity/RULES.json",
            encoding="utf-8").read()
    )
    scored = ("candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting")
    out: dict[str, tuple[str, str]] = {}
    population: dict[str, int] = {}
    for qid, profile in PRIMARY_BUNDLES:
        entry = next(e for e in rules["inputs"] if e["qid"] == qid)
        bundle = json.loads(open(entry["product_mount_path"], encoding="utf-8").read())
        counts = {}
        for row in bundle["decisions"]:
            st = row.get("counter_status") or "none"
            if st == "none":
                continue
            counts[st] = counts.get(st, 0) + 1
            if st in scored:
                out[row["decision_id"]] = _classify(row, rules["lexicons"], rules["question_anchors"][profile])
        population[qid] = counts
    return out, population, rules


def test_independent_population_matches_the_frozen_expectation(independent):
    _, population, rules = independent
    expected = {qid: statuses for qid, statuses in rules["populations"]["primary"]["expected_rows"].items()}
    for qid, counts in population.items():
        exp = expected[qid]
        for status in ("candidate-limiting", "cited"):
            assert counts.get(status, 0) == len(exp.get(status, [])), (qid, status, counts)


def test_independent_classification_matches_the_committed_report(independent, report):
    mine, _, _ = independent
    committed = {r["decision_id"]: r["primary_defect_class"]
                 for r in report["populations"]["primary"]["rows"]}
    assert set(mine) == set(committed) == set(EXPECTED_PRIMARY)
    for did in sorted(mine):
        assert mine[did][0] == committed[did], (did, mine[did], committed[did])


def test_independent_support_rate_is_zero(independent):
    mine, _, _ = independent
    supported = [d for d, (cls, _) in mine.items() if cls == "SUPPORTED"]
    assert supported == []
    assert len(mine) == 7


def test_independent_verdict_is_label_unsound(independent):
    mine, _, rules = independent
    verdict = "LABEL_SOUND" if all(c == "SUPPORTED" for c, _ in mine.values()) else "LABEL_UNSOUND"
    assert verdict == "LABEL_UNSOUND"
    assert rules["verdict_rule"]["threshold_support_rate_sound"] == 1.0


def test_every_primary_row_has_non_empty_quoted_evidence_or_a_recorded_reason(independent):
    """No row may be scored without the frozen fields that make it scorable."""
    mine, _, _ = independent
    for did, (_, reason) in mine.items():
        assert reason and reason != "supported"
        assert did in EXPECTED_PRIMARY


def test_off_domain_rows_really_lack_a_pivot_term(independent, report):
    """Adversarial spot-check of the only authored interpretation in the rubric."""
    for row in report["populations"]["primary"]["rows"]:
        if row["primary_defect_class"] != "OFF-DOMAIN":
            continue
        blob = " ".join(str(row.get(k) or "") for k in ("cited_evidence", "title", "regeste")).lower()
        assert not re.search(
            r"kapitalverletzung|or\s*321|eog|gla(u|ü)biger|schuldner|untergang|sanierung|"
            r"insolvenz|konkurs|liquidit|aktiv|eingriff", blob
        ), row["decision_id"]