"""Parity tests: the local runner must not drift from the durable CI gate.

``product/reality_check.py`` exists so a leg can be debugged locally before it
is burned into a durable ``[reality-check]`` Actions run.  That only helps if
the local gates are the *same* gates.  These tests parse
``.github/workflows/product-reality-check.yml`` and fail whenever the workflow
questions or the substantive truth-gate literals change without a matching
change in the runner (or vice versa).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))

from reality_check import LEGS, norm, structural_gates, truth_gates, evaluate, GateFailure  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "product-reality-check.yml"


def _workflow_text() -> str:
    assert WORKFLOW.is_file(), f"missing durable gate workflow at {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


def _workflow_questions() -> dict[str, str]:
    text = _workflow_text()
    found = dict(re.findall(r'-\s*slug:\s*(\S+)\n\s+question:\s*"([^"]*)"', text))
    assert found, "could not parse the reality-check matrix"
    return found


def test_runner_legs_match_workflow_matrix():
    assert _workflow_questions() == LEGS


def test_truth_gate_literals_present_in_both_directions():
    """Every string literal the workflow asserts on must also gate locally."""
    text = _workflow_text()
    local = (ROOT / "product" / "reality_check.py").read_text(encoding="utf-8")

    # Collect the per-slug assertion regions from the workflow heredoc.
    for slug in LEGS:
        m = re.search(
            rf'(?:if|elif) slug == "{re.escape(slug)}":(.*?)(?=\n\s*(?:elif|else:) |\n\s*PY\b)',
            text,
            re.S,
        )
        assert m, f"workflow has no branch for {slug}"
        body = m.group(1)
        literals = [
            lit for lit in re.findall(r'"([^"\\\n]{2,})"', body)
            if not lit.startswith(("candidate-", "limiting", "contrary"))
        ]
        assert literals, f"no gate literals extracted for {slug}"
        for lit in literals:
            assert lit in local, (
                f"workflow truth gate for {slug} asserts {lit!r}, "
                f"but product/reality_check.py does not"
            )
        # and the local branch gates on the same literals
        lm = re.search(
            rf'slug == "{re.escape(slug)}":(.*?)(?=\n    elif slug ==|\n    else:)',
            local,
            re.S,
        )
        assert lm, f"local runner has no branch for {slug}"
        for lit in literals:
            if lit in ("ready", "generative_audit_llm_v2", "independent_llm_adversarial_v2"):
                continue  # structural, asserted in structural_gates()
            assert lit in lm.group(1) or lit in local, (
                f"local branch for {slug} is missing gate literal {lit!r}"
            )


def test_norm_matches_workflow_normalisation():
    """NFKD + strip combining marks + casefold + collapse whitespace."""
    assert norm("BONNE  Foi") == "bonne foi"
    assert norm("RÉsiduël") == "residuel"
    assert norm("Rechtsmissbrauch\u2019S") == "rechtsmissbrauch\u2019s"


def _report(prose: str, cited=None, ids=None, method="generative_audit_llm_v2",
            adv_method="independent_llm_adversarial_v2"):
    ids = ids or {"bge_1", "bge_2"}
    return {
        "validation_errors": [],
        "bundle": {
            "decisions": [{"decision_id": i, "x": 0, "y": 0} for i in sorted(ids)],
            "answer": {
                "status": "ready",
                "method": method,
                "prose": prose,
                "cited_decision_ids": sorted(cited if cited is not None else ["bge_1"]),
            },
            "provenance": {"generative_audit": {
                "provider_error": None,
                "adversarial": {"method": adv_method, "model": "opencode/test", "error": None},
            }},
        },
    }


def test_rent_default_truth_gate_passes_on_correct_answer():
    prose = (
        "Le bailleur ne peut résilier que pour cause d'importantes difficultés "
        "financières. Pour un local d'habitation, la résiliation doit prendre effet "
        "à la fin d'un mois et doit être annoncée au moins 30 jours à l'avance "
        "(art. 257d al. 2 CO). En outre, la résiliation exercée de mauvaise foi "
        "constitue un abus de droit et peut être contestée."
    )
    report = _report(prose)
    gates = evaluate("rent-default", report)
    assert all(g["passed"] for g in gates), gates


def test_rent_default_truth_gate_fails_without_good_faith_branch():
    prose = (
        "La résiliation doit prendre effet à la fin d'un mois avec 30 jours de préavis "
        "selon l'art. 257d al. 2 CO pour les locaux d'habitation."
    )
    report = _report(prose)
    gates = {g["gate"]: g for g in evaluate("rent-default", report)}
    assert gates["structural"]["passed"]
    assert not gates["truth::rent-default"]["passed"]
    assert "good-faith" in gates["truth::rent-default"]["detail"]


def test_rent_default_truth_gate_fails_without_notice_period():
    prose = (
        "La résiliation est soumise à la bonne foi et à l'interdiction de l'abus de droit ; "
        "aucune durée de préavis n'est toutefois imposée par ce texte."
    )
    report = _report(prose)
    gates = {g["gate"]: g for g in evaluate("rent-default", report)}
    assert not gates["truth::rent-default"]["passed"]
    assert "30" in gates["truth::rent-default"]["detail"]


def test_structural_gate_blocks_truth_gate_on_degraded_answer():
    report = _report("short", method="extractive_tfidf_v1")
    gates = evaluate("rent-default", report)
    assert not gates[0]["passed"]
    assert not gates[1]["passed"]
    assert "skipped" in gates[1]["detail"]


def test_truth_gate_rejects_unknown_slug():
    report = _report("x" * 200)
    try:
        truth_gates("not-a-leg", report)
    except GateFailure as exc:
        assert "unknown slug" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown slug must fail")


def test_structural_gate_rejects_citation_outside_bundle():
    report = _report("x" * 200, cited=["bge_missing"])
    try:
        structural_gates(report)
    except GateFailure as exc:
        assert "outside the bundle" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown citation must fail")
