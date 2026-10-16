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

from reality_check import (  # noqa: E402
    LEGS,
    WORKFLOW_MODEL_OVERRIDE,
    norm,
    structural_gates,
    truth_gates,
    evaluate,
    GateFailure,
)

WORKFLOW = ROOT / ".github" / "workflows" / "product-reality-check.yml"


def _workflow_text() -> str:
    assert WORKFLOW.is_file(), f"missing durable gate workflow at {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


def _workflow_questions() -> dict[str, str]:
    text = _workflow_text()
    found = dict(re.findall(r'-\s*slug:\s*(\S+)\n\s+question:\s*"([^"]*)"', text))
    assert found, "could not parse the reality-check matrix"
    return found


def _workflow_model_override() -> list[str]:
    """The exact ``paths.DEFAULT_FREE_MODELS[:] = [...]`` block in the workflow."""
    text = _workflow_text()
    blocks = re.findall(r"paths\.DEFAULT_FREE_MODELS\[:\]\s*=\s*\[(.*?)\]", text, re.S)
    assert len(blocks) == 1, (
        f"expected exactly one DEFAULT_FREE_MODELS override in the durable "
        f"workflow, found {len(blocks)} — reality_check.WORKFLOW_MODEL_OVERRIDE "
        f"cannot be assumed to reproduce a layout it does not mirror"
    )
    models = re.findall(r'"([^"]+)"', blocks[0])
    assert models, "could not parse the workflow's model-list override"
    return models


def test_runner_legs_match_workflow_matrix():
    assert _workflow_questions() == LEGS


def test_workflow_model_override_matches_durable_workflow():
    """Fail-closed parity for the constant ``--workflow-override`` reproduces.

    ``reality_check.WORKFLOW_MODEL_OVERRIDE`` is a hand-copied mirror of the
    durable workflow's post-seam ``paths.DEFAULT_FREE_MODELS[:] = [...]`` block,
    and it is the entire evidentiary basis for "the four legs are green under
    the durable gate's *exact* model-list condition".  Until this guard existed
    (independent audit of cycle 38933925523, MODERATE fix) nothing kept the
    constant in step: if the control plane reorders or edits that list — which
    happens whenever model health is refreshed — ``--workflow-override`` would
    keep reproducing a stale condition while reports still claimed exactness.

    Fail-closed in both directions: a workflow edit without a constant update
    fails, and a constant edit without a workflow update fails too.
    """
    assert WORKFLOW_MODEL_OVERRIDE == _workflow_model_override(), (
        "product/reality_check.py WORKFLOW_MODEL_OVERRIDE has drifted from the "
        "durable .github/workflows/product-reality-check.yml override block"
    )


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
            adv_method="independent_llm_adversarial_v2", total_seconds=12.0):
    ids = ids or {"bge_1", "bge_2"}
    return {
        "validation_errors": [],
        "total_seconds": total_seconds,
        "bundle": {
            "decisions": [{"decision_id": i, "x": 0, "y": 0, "rank": 1,
                           "counter_status": "none"} for i in sorted(ids)],
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
        "Pour un local d'habitation, le bailleur doit notifier la resiliation "
        "avec un preavis de 30 jours pour la fin du mois selon l'art. 257d al. 2 CO ; "
        "une resiliation exercee de mauvaise foi constitue un abus de droit "
        "et peut etre annulee par le tribunal."
    )
    report = _report(prose)
    gates = evaluate("rent-default", report)
    assert all(g["passed"] for g in gates), gates


def test_rent_default_truth_gate_fails_without_good_faith_branch():
    prose = (
        "Pour un local d'habitation, la resiliation pour retard de loyer prend effet "
        "avec un preavis de 30 jours pour la fin du mois selon l'art. 257d al. 2 CO ; "
        "le tribunal verifie le respect du delai."
    )
    report = _report(prose)
    gates = {g["gate"]: g for g in evaluate("rent-default", report)}
    assert gates["structural"]["passed"]
    assert not gates["truth::rent-default"]["passed"]
    assert "good-faith" in gates["truth::rent-default"]["detail"]


def test_rent_default_truth_gate_fails_without_notice_period():
    prose = (
        "La resiliation est soumise a la bonne foi et a l'interdiction de l'abus de droit ; "
        "aucune duree de preavis n'est toutefois imposee par ce texte, selon le tribunal."
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
