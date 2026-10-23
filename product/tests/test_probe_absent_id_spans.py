"""Absent-ID span probe contract (v65 item 4 follow-up).

The probe answers exactly one diagnostic question per named head-excluded row:
does the row's own cached text contain ANY span the frozen confirm-or-abstain
gate would confirm under the shipped precision guard?  These tests pin the
structure and the honesty of that answer; they never move a rank or pool.
"""
from __future__ import annotations

import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import probe_absent_id_spans as probe  # noqa: E402
from product.query.counter_anchor import load_frozen_rules  # noqa: E402

KNOWN = ("gr_gerichte_PZ_2006_125", "zh_mietgericht_MB170006-L",
         "ch_vb_JAAC_68.7__")


def test_known_ids_match_the_published_diagnosis() -> None:
    from product.diagnose_absent_ids import KNOWN_IDS

    flat = [i for ids in KNOWN_IDS.values() for i in ids]
    assert sorted(flat) == sorted(KNOWN)


def test_probe_row_without_profile_records_it_honestly() -> None:
    rules, _digest = load_frozen_rules()
    rec = probe.probe_row(
        {"decision_id": "x", "rank": 104},
        rules=rules,
        query="xyzzy plugh frobnicate the wibble (no frozen profile)",
    )
    assert rec["span_probe"]["applied"] is False
    assert rec["span_probe"]["reason"] == "no_frozen_anchor_profile_for_query"
    assert rec["span_probe"]["evidenced"] is False


def test_probe_row_resolves_the_french_bail_profile_for_rent_default() -> None:
    from product.reality_check import LEGS

    rules, _digest = load_frozen_rules()
    rec = probe.probe_row(
        {
            "decision_id": "gr_gerichte_PZ_2006_125",
            "rank": 104,
            "query_similarity": 0.009,
            "legal_anchor_score": 0.0,
            "regeste": (
                "Der Mieter kann den Vertrag nicht wegen blosser Zahlungsverzögerung "
                "auflösen; Art. 257d OR 257d OR setzt einen wichtigen Grund voraus."
            ),
        },
        rules=rules,
        query=LEGS["rent-default"],
    )
    assert rec["resolved_profile_key"] == "fr-bail-entretien"
    assert rec["span_probe"]["applied"] is True
    assert "evidenced" in rec["span_probe"]
    assert rec["text_fields_present"] == ["regeste"]


def test_full_probe_run_is_network_free_and_keeps_every_named_row() -> None:
    report = probe.run()
    assert report["schema"] == probe.SCHEMA
    assert "network blocked" in report["mode"]
    assert report["summary"]["network_attempts"] == []
    assert report["summary"]["n_probed"] == 3
    ids = [r["decision_id"] for r in report["summary"]["per_row"]]
    assert sorted(ids) == sorted(KNOWN)
    # every row answers the one diagnostic question, evidenced or abstained
    for row in report["summary"]["per_row"]:
        assert row["span_evidenced"] in (True, False)
        assert row["reason_code"]
    # the upstream diagnosis is cited, never silently replaced
    assert "CYCLE_39986094168_absent_ids.json" in report["upstream_diagnosis"]
    assert report["frozen_rules_sha256"]
