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
    BJR_DIRECT_TF_FROZEN,
    norm,
    structural_gates,
    truth_gates,
    evaluate,
    strip_bundle,
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


# --------------------------------------------------------------------------- #
# frozen-benchmark parity: recall::citation_controlling_authority (BJR)
# --------------------------------------------------------------------------- #
BJR_PROSE = (
    "Le juge suisse s'abstient de revoir la decision commerciale du conseil "
    "d'administration lorsque celui-ci disposait d'une information adequate, "
    "a suivi un processus decisionnel complet, n'etait pas en conflit "
    "d'interets, et que la decision reste defendable au regard du standard "
    "de retenue judiciaire."
)


def _bjr_report(cited, mode="live"):
    report = _report(BJR_PROSE, cited=cited,
                     ids=set(cited) | {"bge_other"})
    report["mode"] = mode
    return report


def test_bjr_frozen_recall_gate_fails_when_only_non_frozen_authorities_cited():
    """The exact accepted RED shape (live leg 20261016T165604Z): the durable
    workflow's wider truth gate PASSES on bge_BGE_139_III_24 while the frozen
    benchmark's controlling-authority recall leg FAILS because none of the five
    direct-TF authorities is cited.  The local parity gate must surface that
    blind spot instead of hiding it behind a green truth gate."""
    report = _bjr_report(["bge_BGE_110_II_391", "bge_BGE_139_III_24",
                          "zh_handelsgericht_HG120149"])
    gates = {g["gate"]: g for g in evaluate("business-judgment-rule", report)}
    assert gates["structural"]["passed"]
    assert gates["truth::business-judgment-rule"]["passed"], (
        "the durable workflow's wider truth gate must still pass — the parity "
        "gate is STRICTER, not a replacement")
    assert not gates["recall::citation_controlling_authority"]["passed"]
    assert "4A_219_2015" in gates["recall::citation_controlling_authority"]["detail"]


def test_bjr_frozen_recall_gate_passes_when_a_frozen_tf_authority_cited():
    report = _bjr_report(["bge_BGE_139_III_24", "bger_4A_219_2015"])
    gates = {g["gate"]: g for g in evaluate("business-judgment-rule", report)}
    assert all(g["passed"] for g in gates.values()), gates


def test_bjr_frozen_recall_gate_fixture_mode_is_instrumented_skip():
    """Fixture runs are a wiring check; they record the non-evaluation as an
    explicit wiring::* marker instead of a false recall pass.

    Repair of audit D1 (cycle 39014141628): this test used to pin the
    fabricated green (frozen gate name + passed=true + 'not applicable'
    detail).  The frozen gate name must now be absent from fixture output
    entirely; the wiring marker carries the explicit not-evaluation.
    """
    report = _bjr_report(["bge_BGE_139_III_24"], mode="fixture")
    gates = {g["gate"]: g for g in evaluate("business-judgment-rule", report)}
    assert "recall::citation_controlling_authority" not in gates, (
        "fixture mode must never emit the frozen gate name")
    gate = gates["wiring::frozen_recall_gate_not_evaluated"]
    assert gate["passed"] is True
    assert "not evaluated" in gate["detail"]
    assert "fixture" in gate["detail"]


def test_non_bjr_legs_gain_no_extra_gate():
    report = _report(
        "Pour un local d'habitation, le bailleur doit notifier la resiliation "
        "avec un preavis de 30 jours pour la fin du mois selon l'art. 257d al. 2 CO ; "
        "une resiliation exercee de mauvaise foi constitue un abus de droit "
        "et peut etre annulee par le tribunal."
    )
    report["mode"] = "live"
    gates = evaluate("rent-default", report)
    assert [g["gate"] for g in gates] == ["structural", "truth::rent-default"]


# --------------------------------------------------------------------------- #
# repair of audit R1 (cycle 39023182745): the cited_decisions projection must
# carry the abstention CAUSE, not only the status, or a reader cannot tell a
# frozen-rubric abstention from the fail-closed 'no_anchor_profile' branch.
# --------------------------------------------------------------------------- #

def _report_with_abstained_cited_decision():
    report = _report(BJR_PROSE, cited=["bge_BGE_110_II_391"])
    report["cited_decision_ids"] = ["bge_BGE_110_II_391"]
    report["bundle"]["decisions"] = [
        {
            "decision_id": "bge_BGE_110_II_391",
            "rank": 3,
            "citation": "BGE 110 II 391",
            "language": "de",
            "counter_status": "abstained_unevidenced",
            "counter_reason_code": "no_anchor_profile",
            "counter_uncertainty": 1.0,
            "counter_evidence_verified": False,
            "canonical_url": "https://mcp.opencaselaw.ch/entscheid/bge_BGE_110_II_391",
            "snippet": "Regeste Aktienrecht.",
        }
    ]
    return report


def test_strip_bundle_carries_counter_reason_code_for_abstained_cited_row():
    report = _report_with_abstained_cited_decision()
    slim = strip_bundle(report)
    rows = {r["decision_id"]: r for r in slim["cited_decisions"]}
    row = rows["bge_BGE_110_II_391"]
    assert row["counter_status"] == "abstained_unevidenced"
    assert row["counter_reason_code"] == "no_anchor_profile"
    assert row["counter_uncertainty"] == 1.0
    assert row["counter_evidence_verified"] is False


def test_strip_bundle_omits_reason_code_when_absent_not_fabricates_it():
    """A row without a reason code must surface as null, never a guessed value."""
    report = _report(BJR_PROSE, cited=["bge_BGE_110_II_391"])
    report["cited_decision_ids"] = ["bge_BGE_110_II_391"]
    report["bundle"]["decisions"] = [
        {"decision_id": "bge_BGE_110_II_391", "rank": 3,
         "counter_status": "cited", "snippet": ""}
    ]
    slim = strip_bundle(report)
    row = slim["cited_decisions"][0]
    assert row["counter_status"] == "cited"
    assert row["counter_reason_code"] is None
    assert row["counter_uncertainty"] is None
    assert row["counter_evidence_verified"] is None


def test_frozen_set_is_exactly_the_five_direct_tf_authorities():
    """Pin the set against silent drift: these are the five frozen direct-TF
    BJR authorities of the accepted benchmark, nothing more."""
    assert BJR_DIRECT_TF_FROZEN == {
        "bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013",
        "bger_4A_603_2014", "bger_4A_62_2024",
    }
