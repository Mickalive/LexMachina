"""Conventional ranked-list baseline: the control condition of the human gate.

Acceptance test (1): render the conventional view from a ``query_result_bundle``
alone — rank, decision_id, court, date, language, citation, snippet and source
link, in the bundle's rank order, adding **no** map or semantic information
(no cluster colour, no proximity, no counter grouping), explicitly labelled as
the conventional baseline.

Every coercion rule in this module is mirrored character-for-character in
``static/lex_gate_switch.js`` (``buildListModel`` / ``renderRowsHtml``); the
parity is enforced by the offline test suite.
"""
from __future__ import annotations

import html
from typing import Any

from .bundle_io import bundle_sha256, canonical_json  # noqa: F401  (re-exported for tests)

LIST_FIELDS = ["rank", "decision_id", "court", "decision_date", "language",
               "citation", "snippet", "canonical_url"]
SNIPPET_LIMIT = 300
BASELINE_LABEL_FR = "Liste classée conventionnelle (baseline)"
BASELINE_LABEL_DE = "Konventionelle Rangliste (Baseline)"
BASELINE_NOTE_FR = ("Aucune information de carte dans cette vue : rang, tribunal, date, "
                    "langue, citation, extrait, source.")
BASELINE_NOTE_DE = ("Keine Karteninformation in dieser Ansicht: Rang, Gericht, Datum, "
                    "Sprache, Zitat, Auszug, Quelle.")

ROW_TEMPLATE = (
    '<li class="lex-row" data-rank="{rank}" data-decision-id="{decision_id_esc}">'
    '<span class="lex-rank">#{rank}</span>'
    '<span class="lex-citation">{citation_esc}</span>'
    '<span class="lex-court">{court_esc}</span>'
    '<span class="lex-date">{decision_date_esc}</span>'
    '<span class="lex-lang">{language_esc}</span>'
    '<span class="lex-decision-id">{decision_id_esc}</span>'
    '{source}'
    '<p class="lex-snippet">{snippet_esc}</p>'
    '</li>'
)


def esc(value: Any) -> str:
    """Escape exactly like the product UI (& first, then < > \" ')."""
    text = "" if value is None else str(value)
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;").replace("'", "&#39;"))


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _rank(value: Any) -> int:
    try:
        number = float(value)  # accepts int, float and numeric strings ("3")
    except (TypeError, ValueError):
        return 0
    if number != number or number in (float("inf"), float("-inf")):
        return 0
    return int(number)


def _citation(value: Any) -> str:
    if isinstance(value, list):
        return " · ".join(_text(v) for v in value)
    return _text(value)


def _snippet(value: Any) -> str:
    text = _text(value)
    return text if len(text) <= SNIPPET_LIMIT else text[:SNIPPET_LIMIT] + "…"


def build_model(bundle: dict) -> list[dict]:
    """List model: bundle decisions sorted by rank ascending (STABLE)."""
    raw = bundle.get("decisions")
    decisions = [d for d in raw if isinstance(d, dict)] if isinstance(raw, list) else []
    ordered = sorted(decisions, key=lambda d: _rank(d.get("rank")))  # stable
    return [
        {
            "rank": _rank(d.get("rank")),
            "decision_id": _text(d.get("decision_id")),
            "court": _text(d.get("court")),
            "decision_date": _text(d.get("decision_date")),
            "language": _text(d.get("language")),
            "citation": _citation(d.get("citation")),
            "snippet": _snippet(d.get("snippet")),
            "canonical_url": _text(d.get("canonical_url")),
        }
        for d in ordered
    ]


def _source_html(url: str) -> str:
    lowered = url.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return (f'<a class="lex-source" href="{esc(url)}" '
                f'target="_blank" rel="noopener">source</a>')
    return '<span class="lex-source-missing">\u2014</span>'


def render_row(row: dict) -> str:
    return ROW_TEMPLATE.format(
        rank=row["rank"],
        decision_id_esc=esc(row["decision_id"]),
        citation_esc=esc(row["citation"]),
        court_esc=esc(row["court"]),
        decision_date_esc=esc(row["decision_date"]),
        language_esc=esc(row["language"]),
        snippet_esc=esc(row["snippet"]),
        source=_source_html(row["canonical_url"]),
    )


def render_rows_html(bundle: dict) -> str:
    """Rows only — byte-identical to the JavaScript renderer over the same bundle."""
    return "\n".join(render_row(row) for row in build_model(bundle))


def render_document(bundle: dict) -> str:
    """Self-contained offline baseline page (no external asset, no network)."""
    model = build_model(bundle)
    sha = bundle_sha256(bundle)
    query = bundle.get("query", "")
    rows = "\n".join(render_row(row) for row in model)
    languages: dict[str, int] = {}
    for row in model:
        languages[row["language"]] = languages.get(row["language"], 0) + 1
    lang_meta = " · ".join(f"{k} {v}" for k, v in sorted(languages.items()))
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LexMachina — {BASELINE_LABEL_FR}</title>
<style>
:root{{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#17191f;background:#f5f6f8}}
*{{box-sizing:border-box}}
body{{margin:0;padding:24px;max-width:900px}}
h1{{font-size:19px;margin:0 0 4px}}
h2{{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#737b88;margin:18px 0 6px}}
.meta{{color:#68707d;font-size:12px;margin:2px 0}}
.note{{color:#6b5b1e;background:#fffbe6;border:1px solid #f0d7a8;padding:8px 10px;border-radius:8px;font-size:12px;margin:12px 0}}
.lex-ranked-list{{list-style:none;margin:0;padding:0}}
.lex-row{{display:grid;grid-template-columns:52px 1fr;gap:4px 10px;padding:11px 8px;border-bottom:1px solid #e7e9ee;font-size:13px}}
.lex-rank{{color:#737b88;font-variant-numeric:tabular-nums}}
.lex-citation{{font-weight:700}}
.lex-court,.lex-date,.lex-lang,.lex-decision-id{{color:#737b88;font-size:12px;margin-right:8px}}
.lex-snippet{{grid-column:2;margin:4px 0 0;color:#33383f;line-height:1.45}}
.lex-source{{grid-column:2;font-size:12px;color:#2459a8;text-decoration:none}}
.lex-source-missing{{grid-column:2;font-size:12px;color:#98a0ab}}
footer{{margin-top:22px;color:#737b88;font-size:11px}}
</style>
</head>
<body data-lex-view="baseline-list" data-bundle-sha256="{sha}">
<h1>{BASELINE_LABEL_FR} / {BASELINE_LABEL_DE}</h1>
<p class="meta">{BASELINE_NOTE_FR}</p>
<p class="meta">{BASELINE_NOTE_DE}</p>
<p class="meta">requête / Abfrage : <b>{esc(query)}</b> · {len(model)} décisions · {esc(lang_meta)}</p>
<div class="note">Cette vue est le <b>contrôle</b> du comparatif du Main Prompt :
réponse + liste classée conventionnelle, rendue depuis le <i>même</i>
<code>query_result_bundle</code> que la carte (sha256 {sha[:16]}…). Aucune donnée n'est
rajoutée ni retirée par rapport à la carte.</div>
<ol class="lex-ranked-list" start="1">
{rows}
</ol>
<footer>frontier-human-gate-harness v1 · rendu déterministe hors-ligne · aucune requête réseau</footer>
</body>
</html>
"""


def render_summary(bundle: dict) -> dict:
    model = build_model(bundle)
    return {
        "view": "baseline-list",
        "label": f"{BASELINE_LABEL_FR} / {BASELINE_LABEL_DE}",
        "n_rows": len(model),
        "ranks_strictly_ascending": [r["rank"] for r in model] == sorted(r["rank"] for r in model),
        "fields": list(LIST_FIELDS),
        "no_map_semantics": True,
        "bundle_sha256": bundle_sha256(bundle),
        "query": bundle.get("query"),
    }
