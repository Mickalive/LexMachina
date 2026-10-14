"""Acceptance (1) + (6): the conventional ranked-list baseline renderer."""
from __future__ import annotations

import json

from _bootstrap import (FIXTURE_PATH, SWITCH_JS, VERIFY_JS, load_fixture,
                        require_node, run_node)

from frontier_human_gate_harness import baseline_view as bv
from frontier_human_gate_harness.bundle_io import bundle_sha256

MAP_TOKENS = ["cluster", "counter_status", "is_outlier", "proximity"]


def test_render_order_equals_bundle_rank():
    bundle = load_fixture()
    model = bv.build_model(bundle)
    assert [row["rank"] for row in model] == list(range(1, len(bundle["decisions"]) + 1))
    bundle_ranks = [d["rank"] for d in bundle["decisions"]]
    assert [row["rank"] for row in model] == sorted(bundle_ranks)
    # every rendered rank exists in the bundle, in the same relative order
    by_id = {d["decision_id"]: d["rank"] for d in bundle["decisions"]}
    assert [by_id[row["decision_id"]] for row in model] == [row["rank"] for row in model]


def test_model_has_exactly_the_list_fields():
    bundle = load_fixture()
    model = bv.build_model(bundle)
    assert model, "fixture rendered no rows"
    for row in model:
        assert list(row.keys()) == bv.LIST_FIELDS
        for forbidden in ("cluster_id", "x", "y", "counter_status", "score"):
            assert forbidden not in row


def test_no_map_semantics_in_rendered_html():
    bundle = load_fixture()
    rows = bv.render_rows_html(bundle)
    lowered = rows.lower()
    for token in MAP_TOKENS:
        assert token not in lowered, f"map/semantic token {token!r} leaked into the baseline"
    assert "#" not in rows or all(ch not in "abcdefABCDEF0123456789" for ch in rows.split("#")[0][-2:])
    # no inline colour attribute and no coordinate attribute
    assert 'style="' not in rows
    assert ' data-x="' not in rows and ' data-y="' not in rows
    assert 'counter' not in lowered


def test_explicit_baseline_label_in_document():
    bundle = load_fixture()
    doc = bv.render_document(bundle)
    assert bv.BASELINE_LABEL_FR in doc and bv.BASELINE_LABEL_DE in doc
    assert "baseline" in doc.lower()
    assert doc.startswith("<!DOCTYPE html>")
    assert f'data-bundle-sha256="{bundle_sha256(bundle)}"' in doc


def test_same_fixture_byte_identical_render():
    bundle = load_fixture()
    first = bv.render_document(bundle).encode("utf-8")
    second = bv.render_document(load_fixture()).encode("utf-8")
    assert first == second
    # the hash the page carries is the canonical bundle hash, recomputed here
    import hashlib

    canonical = json.dumps(bundle, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == bundle_sha256(bundle)


def test_escaping_truncation_and_link_scheme():
    bundle = {
        "query": "q", "decisions": [
            {"rank": 1, "decision_id": "a&b", "court": "<bger>", "decision_date": "2020'",
             "language": "de", "citation": ["C1", "C2"], "snippet": "x" * 400,
             "canonical_url": "javascript:alert(1)"},
            {"rank": 2, "decision_id": "ok", "court": "bger", "decision_date": "",
             "language": "fr", "citation": None, "snippet": None,
             "canonical_url": "https://bger.ch/x?a=1&b=2"},
        ],
    }
    rows = bv.render_rows_html(bundle)
    assert rows.split("\n")[0].count("x" * 300) == 1
    assert "\u2026" in rows.split("\n")[0]
    assert "x" * 301 not in rows
    assert "<bger>" not in rows and "&lt;bger&gt;" in rows
    assert "a&amp;b" in rows
    assert "C1 \u00b7 C2" in rows
    assert "lex-source-missing" in rows.split("\n")[0]
    assert 'href="https://bger.ch/x?a=1&amp;b=2"' in rows.split("\n")[1]
    model = bv.build_model(bundle)
    assert model[1]["citation"] == "" and model[1]["snippet"] == ""


def test_python_and_javascript_renderers_are_byte_identical():
    """Cross-language parity: the product drop-in JS must equal the Python baseline."""
    require_node()
    assert SWITCH_JS.is_file()
    bundle = load_fixture()
    proc = run_node([str(VERIFY_JS), "--emit-fixture", str(FIXTURE_PATH)])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["model"] == bv.build_model(bundle)
    assert payload["rows"] == bv.render_rows_html(bundle)
    assert payload["list_fields"] == bv.LIST_FIELDS
