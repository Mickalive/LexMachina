#!/usr/bin/env python3
"""POST-HOC semantic audit of the emitted spans (NOT part of the frozen verdict).

The frozen protocol decides OUTCOME_A/B from mechanical conditions only.  This
script asks a narrower, exploratory question after that verdict is fixed:

    When a frozen anchor "hit" licenses an emitted span, is the anchor matched
    as a full stemmed token, or only through the frozen >=5-character PREFIX
    tolerance?  A prefix hit on a short generic token (e.g. "unter" matching
    "untergang", "kapital" matching "kapitalverletzung") is a mechanical match
    but not a semantic anchor to the question.

This diagnostic changes no frozen number and is never used to re-label a row.
It is written to ``SEMANTIC_AUDIT.json`` with ``role`` explicitly marked
post-hoc so the provenance of the primary verdict is preserved.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import scorer_bridge  # noqa: E402
import span_select  # noqa: E402

QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")
DEFAULT_MOUNT = Path("/tmp/lex_accepted/core/product")
DEFAULT_PROTOCOL = (
    HERE.parents[1]
    / "results"
    / "frontier"
    / "frontier-counter-evidence-span-selection"
    / "PROTOCOL.json"
)
DEFAULT_OUT = (
    HERE.parents[1]
    / "results"
    / "frontier"
    / "frontier-counter-evidence-span-selection"
    / "SEMANTIC_AUDIT.json"
)


def match_detail(nz: Any, tokens: list[str], anchor: str) -> dict[str, Any] | None:
    """Return how ``anchor`` matched: exact stem token / multi-token phrase / prefix."""
    want = nz.stems(anchor)
    if not want:
        return None
    if len(want) > 1:
        n, m = len(tokens), len(want)
        for i in range(n - m + 1):
            if tokens[i : i + m] == want:
                return {
                    "match_type": "exact_phrase",
                    "matched_token": " ".join(tokens[i : i + m]),
                }
        return None
    target = want[0]
    for tok in tokens:
        if tok == target:
            return {"match_type": "exact", "matched_token": tok}
    for tok in tokens:
        limit = min(len(tok), len(target))
        if limit >= 5 and tok[:limit] == target[:limit]:
            return {"match_type": "prefix", "matched_token": tok}
    return None


def main() -> int:
    protocol = json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    limits = protocol["span_rule"]["limits"]
    mount = DEFAULT_MOUNT
    modules = scorer_bridge.load_product_modules(mount)
    _decide, load_rules = scorer_bridge.load_classifier(mount)
    rules = load_rules(str(mount / "product" / "frozen" / "RULES_LABEL.json"))
    nz = rules.normalizer

    packet_dir = Path(protocol["inputs"]["packet_of_record"]["path_prefix"])
    rows_out: list[dict[str, Any]] = []
    for qid in QIDS:
        bundle = scorer_bridge.load_bundle(packet_dir, qid)
        repaired = modules["counter_emission_repair"].apply_counter_emission_repair(bundle)
        profile = rules.anchor_profile(qid)
        selected, decisions = span_select.apply_span_selection(
            repaired,
            rules,
            profile,
            qid=qid,
            min_chars=int(limits["min_span_chars"]),
            max_chars=int(limits["max_span_chars"]),
            max_units=int(limits["max_window_units"]),
        )
        final = modules["counter_anchor"].apply_anchor_labels(selected, qid=qid)
        emitted_ids = set(
            ((final.get("provenance") or {}).get("counter_anchor") or {}).get("emitted_ids")
            or []
        )
        for dec in decisions:
            if not dec.evidenced or dec.decision_id not in emitted_ids:
                continue
            tokens = nz.stems(dec.quote)
            domain = match_detail(nz, tokens, dec.domain_anchor) if dec.domain_anchor else None
            pivot = match_detail(nz, tokens, dec.pivot_anchor) if dec.pivot_anchor else None
            prefix_only = bool(
                (domain and domain["match_type"] == "prefix")
                or (pivot and pivot["match_type"] == "prefix")
            )
            short_prefix = bool(
                (domain and domain["match_type"] == "prefix" and len(domain["matched_token"]) <= 8)
                or (pivot and pivot["match_type"] == "prefix" and len(pivot["matched_token"]) <= 8)
            )
            # Manual post-hoc category.  ``resili`` is a legitimate stem of
            # ``résilier`` (morphological prefix); ``unter``/``kapital`` are
            # unrelated short words that only share a prefix with the anchor.
            quality = "exact"
            if prefix_only:
                short_tokens = {
                    m["matched_token"]
                    for m in (domain, pivot)
                    if m and m["match_type"] == "prefix" and len(m["matched_token"]) <= 8
                }
                if short_tokens & {"unter", "kapital"}:
                    quality = "string_coincidence"
                else:
                    quality = "morphological_prefix"
            rows_out.append({
                "qid": qid,
                "decision_id": dec.decision_id,
                "quote_chars": len(dec.quote),
                "quote_head": dec.quote[:180],
                "intent_marker": dec.intent_marker,
                "domain_anchor": dec.domain_anchor,
                "domain_match": domain,
                "pivot_anchor": dec.pivot_anchor,
                "pivot_match": pivot,
                "prefix_only_anchor": prefix_only,
                "short_generic_prefix": short_prefix,
                "anchor_quality": quality,
            })

    n = len(rows_out)
    n_prefix = sum(1 for r in rows_out if r["prefix_only_anchor"])
    n_short = sum(1 for r in rows_out if r["short_generic_prefix"])
    n_exact = sum(1 for r in rows_out if r["anchor_quality"] == "exact")
    n_string = sum(1 for r in rows_out if r["anchor_quality"] == "string_coincidence")
    n_morph = sum(1 for r in rows_out if r["anchor_quality"] == "morphological_prefix")
    audit = {
        "schema": "frontier-counter-evidence-span-selection/semantic-audit/1",
        "role": (
            "POST-HOC DIAGNOSTIC ONLY. This file does not change the frozen "
            "OUTCOME_A/B verdict, any n_scored/n_emitted count, or any claim. "
            "It records whether an emitted span's anchor hit was exact or only "
            "the frozen >=5-character prefix tolerance."
        ),
        "protocol_sha256": hashlib.sha256(DEFAULT_PROTOCOL.read_bytes()).hexdigest(),
        "n_emitted_rows": n,
        "n_exact_anchor": n_exact,
        "n_morphological_prefix": n_morph,
        "n_string_coincidence_prefix": n_string,
        "n_prefix_only_anchor": n_prefix,
        "n_short_generic_prefix": n_short,
        "prefix_only_share": (n_prefix / n if n else 0.0),
        "short_generic_prefix_share": (n_short / n if n else 0.0),
        "string_coincidence_share": (n_string / n if n else 0.0),
        "interpretation": (
            "Four of seven emitted spans are licensed by a string coincidence on "
            "a short generic token: 'unter' for 'untergang' (three rows) and "
            "'kapital' for 'kapitalverletzung' (one row). One is a legitimate "
            "morphological prefix ('resili' for 'resiliation'); two match exactly "
            "('defaut'). Only the exact rows, and arguably the morphological row, "
            "are candidates for semantic review. The string-coincidence rows are "
            "mechanically supported by the frozen rubric but must not be reported "
            "as legal counter-authority. This diagnostic does not move the "
            "frozen OUTCOME_A/B verdict."
        ),
        "rows": rows_out,
    }
    DEFAULT_OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "n_emitted_rows": n,
        "n_prefix_only_anchor": n_prefix,
        "n_short_generic_prefix": n_short,
        "out": str(DEFAULT_OUT),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
