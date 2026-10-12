"""LexMachina Frontier — generative audit v2.2 — frozen deterministic suite.

Covers the charter acceptance tests (v2, charter_version=2):

  (1) provider interface with a real no-owner-cost development path
      (OpenCode CLI / local OpenAI-compatible server; exercised live in
      ``test_real_model_smoke`` when LEX_REAL_MODEL=1) plus fixture mode;
  (2) generated answers cite only bundle decision IDs; hallucinated IDs are
      programmatically rejected AND redacted from surfaced prose;
  (3) logically independent adversarial pass (challenge-only, unknown IDs
      rejected, never a restatement);
  (4) merged statuses supporting / limiting / contrary_or_exception /
      unclassified with uncertainty + evidence references;
  (5) post-generation citation/source validation (OpenCaseLaw attestation
      where feasible, strict local otherwise) — including live
      ``mcp.opencaselaw.ch`` probes when LEX_LIVE_OCL=1;
  (6) end-to-end cached example with answer + adversarial findings;
  (7) tests for invented-citation rejection, unsupported-status downgrade,
      provider failure fallback and deterministic parsing;
  (8) narrow integration contract for the product lane.

Repair cycle 38181577763 (rejected cycle 38180132239, round 1) added the
auditor's required regressions: sound attestation verdicts for the live
``200 {"error": ...}`` body, empty/non-object bodies and non-2xx responses;
verbatim source-checking of adversarial ``evidence_refs`` (fabricated quotes
must never reach ``decisions[*].counter_evidence``); and reconciliation of
the product-compatibility check with the accepted core validator.

Run:  python3 tests/frontier/frontier-generative-audit/test_generative_audit_v2.py
Or:   python3 -m pytest tests/frontier/frontier-generative-audit/ -q
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List

HERE = Path(__file__).resolve().parent
CANONICAL = HERE.parents[2] / "frontier" / "frontier-generative-audit"
sys.path.insert(0, str(CANONICAL))

import generative_audit  # noqa: E402
from generative_audit import paths  # noqa: E402

assert Path(generative_audit.__file__).resolve().is_relative_to(CANONICAL.resolve()), (
    f"imported wrong package tree: {generative_audit.__file__}"
)

from generative_audit.adversarial import (  # noqa: E402
    AdversarialFinding,
    AdversarialPass,
    MAX_PROMPT_SOURCES,
)
from generative_audit.evidence import (  # noqa: E402
    DOWNGRADED_MIN_UNCERTAINTY,
    normalize_quote,
    quote_in_source,
    source_check_findings,
)
from generative_audit.integration_contract import (  # noqa: E402
    CONTRACT_VERSION,
    package_answer,
    apply_to_product_bundle,
    run_generative_audit,
)
from generative_audit.models import StatusLabel  # noqa: E402
from generative_audit.opencaselaw import (  # noqa: E402
    DEFAULT_OCL_API_BASE,
    RETIRED_WRONG_API_BASE,
    OpenCaseLawAttestor,
    PostGenerationValidator,
)
from generative_audit.product_compat import validate_product_bundle  # noqa: E402
from generative_audit.provider import Provider, ProviderError, ProviderResult  # noqa: E402
from generative_audit.source_packing import (  # noqa: E402
    CitationValidator,
    Decision,
    DecisionBundle,
    from_product_bundle,
    redact_unknown_citations,
)

FIXTURE_BUNDLE = HERE / "fixtures" / "sample_bundle.json"
RESULTS_DIR = HERE.parents[2] / "results" / "frontier" / "frontier-generative-audit"

#: The exact HTTP-200 error body observed from the live OpenCaseLaw
#: ``POST /api/attest`` route when ``draft_text`` is missing (cycle
#: 38180132239 audit, defect 2).  Must never count as verification.
OBSERVED_ATTEST_ERROR_BODY = {"error": "Provide draft_text to audit."}

#: Product-required keys, mirroring product/query/bundle.py (accepted core mount).
PRODUCT_REQUIRED_TOP = ["bundle_version", "query", "query_variants", "answer",
                        "decisions", "clusters", "relations", "provenance"]
PRODUCT_REQUIRED_DECISION = ["decision_id", "court", "language", "rank", "score",
                             "provenance", "snippet", "cluster_id", "x", "y",
                             "counter_status", "canonical_url", "citation"]


def _small_bundle() -> DecisionBundle:
    return DecisionBundle(
        query="Requirements for a valid Swiss non-compete clause?",
        decision_ids=["CH-001", "CH-002", "CH-003"],
        decisions=[
            Decision(decision_id="CH-001", title="BGE 4A 1",
                     text="A non-compete clause is valid only if limited in time, space and content."),
            Decision(decision_id="CH-002", title="BGE 4A 2",
                     text="A clause exceeding two years is presumptively disproportionate."),
            Decision(decision_id="CH-003", title="BGE 4A 3",
                     text="Blanket clauses covering all employees are unenforceable."),
        ],
    )


def _load_fixture_bundle() -> DecisionBundle:
    with open(FIXTURE_BUNDLE, encoding="utf-8") as fh:
        return from_product_bundle(json.load(fh))


def _check_product_compatible(bundle: dict) -> List[str]:
    """Validate with the accepted product contract (real validator if mounted)."""
    errors, _source = validate_product_bundle(bundle)
    return errors


# ---------------------------------------------------------------- tests ----


def test_real_path_fixture_and_contract_surface():
    """Acceptance (1)+(8): provider modes exist; contract surface is exported."""
    print(">>> test_real_path_fixture_and_contract_surface")
    assert callable(run_generative_audit)
    assert callable(package_answer)
    assert callable(apply_to_product_bundle)
    assert CONTRACT_VERSION.startswith("generative-audit-contract/")
    p = Provider(fixture_mode=True)
    assert p.model == "fixture://generative-audit"
    real = Provider()  # non-fixture: resolves a free model from state/model_health.json
    assert real.model.startswith("opencode/") or "/" in real.model
    assert callable(real.runner), "real provider must resolve a runner backend"
    print(f"  PASS: fixture + real provider paths present (real model slot: {real.model})")
    return True


def test_fixture_mode_deterministic():
    """Acceptance (1)+(7): deterministic fixture/mock path."""
    print(">>> test_fixture_mode_deterministic")
    bundle = _small_bundle()
    p = Provider(fixture_mode=True, fixture_answer="Deterministic fixture answer.",
                 fixture_cited_ids=["CH-001"])
    r1, r2 = p.generate(bundle), p.generate(bundle)
    assert r1.answer == r2.answer == "Deterministic fixture answer."
    assert r1.cited_decision_ids == r2.cited_decision_ids == ["CH-001"]
    assert r1.model_used == r2.model_used == "fixture://generative-audit"
    print("  PASS: fixture mode is deterministic")
    return True


def test_prompt_surfaces_relevant_passage_beyond_judgment_prefix():
    """Hydrated holdings later in a judgment must reach the answer model."""
    print(">>> test_prompt_surfaces_relevant_passage_beyond_judgment_prefix")
    late = (
        "Procedural history and party submissions. " * 80
        + " Art. 102 Abs. 2 StGB: Bei der originären Haftung "
          "(responsabilité primaire) tritt die Strafbarkeit des Unternehmens "
          "neben diejenige des Individualtäters und gilt unabhängig von der "
          "Strafbarkeit natürlicher Personen."
    )
    bundle = DecisionBundle(
        query="La responsabilité selon l'art. 102 CP est-elle subsidiaire ou primaire ?",
        decision_ids=["BGE-142-IV-333"],
        decisions=[
            Decision(
                decision_id="BGE-142-IV-333",
                title="BGE 142 IV 333",
                text=late,
                metadata={
                    "court": "bge",
                    "rank": 1,
                    "score": 0.9,
                    "snippet": "Art. 102 Abs. 1 und 2 StGB; Strafbarkeit des Unternehmens.",
                },
            )
        ],
    )
    prompt = Provider(fixture_mode=True).build_prompt(bundle)
    assert "originären Haftung" in prompt
    assert "responsabilité primaire" in prompt
    assert "unabhängig von der Strafbarkeit" in prompt
    print("  PASS: late decisive holding packed into prompt")
    return True


def test_provider_preserves_multi_paragraph_answer():
    """Regression: structured legal answers must not be truncated at first blank line."""
    print(">>> test_provider_preserves_multi_paragraph_answer")
    bundle = _small_bundle()
    raw = (
        "**Rule**\n\n"
        "First proposition [CH-001].\n\n"
        "**Exception**\n\n"
        "Second proposition [CH-002]."
    )
    p = Provider(model="fixture-model", runner=lambda *_args, **_kwargs: raw, use_attestation=False)
    result = p._parse_output(raw, bundle, "fixture-model")
    assert "**Rule**" in result.answer
    assert "First proposition" in result.answer
    assert "**Exception**" in result.answer
    assert "Second proposition" in result.answer
    assert result.cited_decision_ids == ["CH-001", "CH-002"]
    print("  PASS: multi-paragraph answer preserved")
    return True


def test_fixture_rejects_invented_cited_ids():
    """Acceptance (2)+(7): fixture cannot smuggle unknown IDs through."""
    print(">>> test_fixture_rejects_invented_cited_ids")
    bundle = _small_bundle()
    p = Provider(fixture_mode=True, fixture_answer="A", fixture_cited_ids=["CH-001", "FAKE-999"])
    r = p.generate(bundle)
    assert r.cited_decision_ids == ["CH-001"]
    assert "FAKE-999" not in r.cited_decision_ids
    print("  PASS: invented fixture citation filtered")
    return True


def test_hallucinated_citation_rejection_and_redaction():
    """Acceptance (2)+(7): invented IDs rejected AND removed from prose."""
    print(">>> test_hallucinated_citation_rejection_and_redaction")
    bundle = _small_bundle()

    def fake_runner(prompt: str, model: str, timeout: float) -> str:
        return (
            "The clause must be limited in time and scope [CH-001]. "
            "Two years is presumptively excessive [CH-002]. "
            "See also the immortal holding [BGE-9999-FAKE]."
        )

    p = Provider(model="fake/model", runner=fake_runner, use_attestation=False)
    r = p.generate(bundle)
    assert r.ok, r.error
    assert r.cited_decision_ids == ["CH-001", "CH-002"]
    assert "BGE-9999-FAKE" in r.validation_report["hallucinated_ids"]
    assert "BGE-9999-FAKE" not in r.answer
    assert "citation removed" in r.answer
    assert all(cid in bundle.decision_ids for cid in r.cited_decision_ids)
    print(f"  PASS: rejected {r.validation_report['hallucinated_ids']}, redacted from prose")
    return True


def test_redaction_helper_unit():
    print(">>> test_redaction_helper_unit")
    clean, removed = redact_unknown_citations(
        "a [CH-001] b [NOPE-9] c (2019) d [1]", ["CH-001"]
    )
    assert "[CH-001]" in clean and "NOPE-9" not in clean
    assert removed == ["NOPE-9"]
    assert "(2019)" in clean and "[1]" in clean, "non-ID tokens must survive"
    print("  PASS: redaction helper (ID-like only)")
    return True


def test_provider_fallback_across_models():
    """Acceptance (1)+(7): provider failure fallback to the next free model."""
    print(">>> test_provider_fallback_across_models")
    bundle = _small_bundle()
    calls: List[str] = []

    def flaky_runner(prompt: str, model: str, timeout: float) -> str:
        calls.append(model)
        if model == "free/broken":
            raise ProviderError("simulated backend outage")
        return "Upheld with limitations [CH-002]."

    p = Provider(model="free/broken", runner=flaky_runner, use_attestation=False)
    p._fallback_models = lambda exclude=None: ["free/healthy"]  # deterministic fallback list
    r = p.generate(bundle)
    assert r.ok, r.error
    assert calls == ["free/broken", "free/healthy"]
    assert r.model_used == "free/healthy", "successful fallback model must be recorded"
    assert r.cited_decision_ids == ["CH-002"]
    assert r.attempts and r.attempts[0]["model"] == "free/broken"
    print("  PASS: fallback engaged, success attributed to healthy model")
    return True


def test_provider_total_failure_is_recorded():
    """Acceptance (7): all-models-fail returns a recorded failure, not silence."""
    print(">>> test_provider_total_failure_is_recorded")

    def dead_runner(prompt: str, model: str, timeout: float) -> str:
        raise ProviderError("no backend reachable")

    bundle = _small_bundle()
    p = Provider(model="free/a", runner=dead_runner, use_attestation=False)
    p._fallback_models = lambda exclude=None: ["free/b"]
    r = p.generate(bundle)
    assert not r.ok and r.error
    assert r.answer == "" and r.cited_decision_ids == []
    assert "ALL_MODELS_FAILED" in (r.raw_output or "")
    assert len(r.attempts) == 2
    print("  PASS: total provider failure recorded with per-model attempts")
    return True


def test_prompt_constrains_citations():
    print(">>> test_prompt_constrains_citations")
    bundle = _small_bundle()
    prompt = Provider(fixture_mode=True).build_prompt(bundle)
    for did in bundle.decision_ids:
        assert did in prompt
    assert "Never invent" in prompt
    assert bundle.query in prompt
    print("  PASS: prompt carries bundle IDs + no-invention constraint")
    return True


def test_adversarial_prefers_live_proven_fast_reviewer():
    """Observed live latency: start with the reviewer that actually completed."""
    print(">>> test_adversarial_prefers_live_proven_fast_reviewer")
    original = paths.healthy_models
    try:
        paths.healthy_models = lambda: [
            "opencode/nemotron-3-ultra-free",
            "opencode/nemotron-3.5-lightning-free",
            "opencode/space-bunny-free",
            "opencode/mimo-v2.6-flash-free",
        ]
        adv = AdversarialPass(
            bundle=_small_bundle(),
            answer="Provisional answer [CH-001].",
            runner=lambda prompt, model, timeout: "[]",
        )
        assert adv.model == "opencode/space-bunny-free"
        assert adv._fallback_models(exclude=adv.model) == [
            "opencode/nemotron-3.5-lightning-free",
            "opencode/mimo-v2.6-flash-free",
            "opencode/nemotron-3-ultra-free",
        ]
    finally:
        paths.healthy_models = original
    print("  PASS: live-proven reviewer is first, healthy pool remains fallback")
    return True


def test_adversarial_fallback_across_models():
    """Integration repair: a timeout/error must rotate to another healthy model."""
    print(">>> test_adversarial_fallback_across_models")
    bundle = _small_bundle()
    calls: List[str] = []

    def runner(prompt: str, model: str, timeout: float) -> str:
        calls.append(model)
        if model == "free/slow":
            raise TimeoutError("simulated adversarial timeout")
        return json.dumps([
            {
                "decision_id": "CH-002",
                "title": "BGE 4A 2",
                "reason": "limiting",
                "evidence_refs": ["exceeding two years is presumptively disproportionate"],
                "uncertainty": 0.2,
                "confidence": 0.9,
            }
        ])

    adv = AdversarialPass(
        bundle=bundle,
        answer="The clause is valid [CH-001].",
        model="free/slow",
        runner=runner,
    )
    adv._fallback_models = lambda exclude=None: ["free/fast"]
    findings, info = adv.run_with_info()

    assert calls == ["free/slow", "free/fast"]
    assert [f.decision_id for f in findings] == ["CH-002"]
    assert info["model"] == "free/fast"
    assert not info.get("error")
    assert info["attempts"] and info["attempts"][0]["model"] == "free/slow"
    print("  PASS: adversarial timeout rotates to healthy fallback")
    return True


def test_adversarial_prompt_shortlist_is_bounded_multilingual_and_counter_aware():
    """Large bundles must not be dumped wholesale into the adversarial model."""
    print(">>> test_adversarial_prompt_shortlist_is_bounded_multilingual_and_counter_aware")
    decisions = []
    ids = []
    langs = ("de", "fr", "it")
    for i in range(90):
        did = f"CH-LARGE-{i:03d}"
        ids.append(did)
        lang = langs[i % len(langs)]
        text = f"ordinary retrieved authority number {i}"
        if i % 7 == 0:
            text += " toutefois exception ausnahme eccezione limiting"
        decisions.append(
            Decision(
                decision_id=did,
                title=f"Decision {i}",
                text=text,
                metadata={"rank": i + 1, "language": lang},
            )
        )

    bundle = DecisionBundle(
        query="large-bundle challenge test",
        decision_ids=ids,
        decisions=decisions,
    )
    adv = AdversarialPass(
        bundle=bundle,
        answer="Provisional answer [CH-LARGE-001].",
        model="m",
        fixture_mode=True,
    )
    shortlist = adv._prompt_decisions()
    assert len(shortlist) == MAX_PROMPT_SOURCES
    assert "CH-LARGE-084" in {d.decision_id for d in shortlist}, (
        "late-ranked explicit exception authority should survive the shortlist"
    )
    langs_kept = {d.metadata.get("language") for d in shortlist}
    assert {"de", "fr", "it"} <= langs_kept
    prompt = adv.build_prompt()
    assert f"{MAX_PROMPT_SOURCES} of 90 retrieved decisions" in prompt
    print("  PASS: large prompt bounded with counter signals + language branches preserved")
    return True


def test_adversarial_parse_rejects_unknown_ids():
    """Acceptance (3)+(7): findings citing non-bundle IDs are rejected."""
    print(">>> test_adversarial_parse_rejects_unknown_ids")
    bundle = _small_bundle()
    adv = AdversarialPass(bundle=bundle, answer="The clause is valid.", model="fake/model")
    raw = json.dumps([
        {"decision_id": "CH-002", "title": "BGE 4A 2", "reason": "limiting",
         "evidence_refs": ["exceeding two years is presumptively disproportionate"],
         "uncertainty": 0.2, "confidence": 0.9},
        {"decision_id": "GHOST-42", "reason": "contradictory", "evidence_refs": ["x"],
         "uncertainty": 0.1},
    ])
    findings = adv.parse_findings(raw)
    assert [f.decision_id for f in findings] == ["CH-002"]
    assert findings[0].reason == "limiting"
    assert adv.rejected_ids == ["GHOST-42"]
    print("  PASS: unknown finding ID rejected and recorded")
    return True


def test_adversarial_parse_deterministic():
    """Acceptance (7): deterministic parsing of the same raw model output."""
    print(">>> test_adversarial_parse_deterministic")
    bundle = _small_bundle()
    raw = (
        'Reasoning... [{"decision_id": "CH-003", "reason": "contradictory", '
        '"evidence_refs": ["blanket clauses are unenforceable"], '
        '"uncertainty": "medium", "confidence": "high"}] done'
    )
    a1 = AdversarialPass(bundle=bundle, answer="ans", model="m").parse_findings(raw)
    a2 = AdversarialPass(bundle=bundle, answer="ans", model="m").parse_findings(raw)
    assert [f.to_dict() for f in a1] == [f.to_dict() for f in a2]
    assert a1[0].uncertainty == 0.5 and a1[0].confidence == 0.9
    print("  PASS: adversarial parsing deterministic (incl. worded uncertainty)")
    return True


def test_adversarial_prompt_is_independent():
    """Acceptance (3): separate call/objective — not a restatement of the answer."""
    print(">>> test_adversarial_prompt_is_independent")
    bundle = _small_bundle()
    answer = "The clause is valid if limited in time and scope [CH-001]."
    adv = AdversarialPass(bundle=bundle, answer=answer, model="m")
    adv_prompt = adv.build_prompt()
    ans_prompt = Provider(fixture_mode=True).build_prompt(bundle)
    assert adv_prompt != ans_prompt
    assert "CHALLENGE" in adv_prompt or "challenge" in adv_prompt
    assert "contradictory" in adv_prompt and "exception" in adv_prompt
    assert answer in adv_prompt  # reviewed object, not reused as conclusion
    assert "JSON array" in adv_prompt
    print("  PASS: adversarial prompt structurally independent")
    return True


def test_adversarial_fixture_mode_challenge_only():
    print(">>> test_adversarial_fixture_mode_challenge_only")
    bundle = _small_bundle()
    good = AdversarialFinding(decision_id="CH-003", title="BGE 4A 3", reason="contradictory",
                              evidence_refs=["blanket clauses unenforceable"], uncertainty=0.2,
                              confidence=0.8)
    ghost = AdversarialFinding(decision_id="GHOST", reason="limiting")
    adv = AdversarialPass(bundle=bundle, answer="ans", fixture_mode=True,
                          fixture_findings=[good, ghost])
    findings, info = adv.run_with_info()
    assert [f.decision_id for f in findings] == ["CH-003"]
    assert info["n_rejected_ids"] == 1
    assert info["method"] == "fixture_adversarial_v2"
    print("  PASS: fixture adversarial pass challenges only, rejects unknown")
    return True


def test_structured_statuses_merging():
    """Acceptance (4): statuses with uncertainty + evidence references."""
    print(">>> test_structured_statuses_merging")
    bundle = _small_bundle()
    result = ProviderResult(answer="Rule X [CH-001].", cited_decision_ids=["CH-001"], model_used="t")
    findings = [
        AdversarialFinding(decision_id="CH-001", reason="limiting",
                           evidence_refs=["limited in time, space and content"], uncertainty=0.3),
        AdversarialFinding(decision_id="CH-002", reason="contradictory",
                           evidence_refs=["exceeding two years is presumptively disproportionate"],
                           uncertainty=0.2),
    ]
    package = package_answer(result, findings, bundle)
    s1 = package.decision_statuses["CH-001"]
    assert s1.label == StatusLabel.LIMITING, "limiting must override cited-supporting"
    assert s1.uncertainty == 0.3 and s1.evidence_refs
    s2 = package.decision_statuses["CH-002"]
    assert s2.label == StatusLabel.CONTRARY_OR_EXCEPTION
    s3 = package.decision_statuses["CH-003"]
    assert s3.label == StatusLabel.UNCLASSIFIED and s3.uncertainty == 1.0
    assert package.summary() == {"supporting": 0, "limiting": 1,
                                 "contrary_or_exception": 1, "unclassified": 1}
    print(f"  PASS: merged statuses {package.summary()}")
    return True


def test_unsupported_status_downgrade():
    """Acceptance (4)+(7): decisions without evidence stay unclassified."""
    print(">>> test_unsupported_status_downgrade")
    bundle = _small_bundle()
    result = ProviderResult(answer="X [CH-001]", cited_decision_ids=["CH-001"], model_used="t")
    package = package_answer(result, [], bundle)
    assert package.decision_statuses["CH-001"].label == StatusLabel.SUPPORTING
    assert package.decision_statuses["CH-002"].label == StatusLabel.UNCLASSIFIED
    assert package.decision_statuses["CH-003"].label == StatusLabel.UNCLASSIFIED
    print("  PASS: unsupported decisions downgraded to unclassified")
    return True


def test_post_generation_validation_strict_local_and_attestation():
    """Acceptance (5): strict local fallback + attestation when feasible."""
    print(">>> test_post_generation_validation_strict_local_and_attestation")
    bundle = _small_bundle()

    # strict local mode (default in CI: deterministic, network-free)
    report = PostGenerationValidator(bundle, use_attestation=False).validate_citations(
        ["CH-001", "GHOST"]
    )
    assert report["mode"] == "strict_local"
    assert report["valid_citations"] == ["CH-001"]
    assert report["hallucinated_ids"] == ["GHOST"]

    # attestation reachable -> verified (realistic decision-record payload)
    ok_attestor = OpenCaseLawAttestor(
        fetch=lambda url, timeout: {"decision": "ok", "decision_id": "CH-001", "url": url}
    )
    report_ok = PostGenerationValidator(bundle, use_attestation=True, attestor=ok_attestor)
    rep_ok = report_ok.validate_citations(["CH-001"])
    assert rep_ok["mode"] == "attestation+local"
    assert rep_ok["verified_ids"] == ["CH-001"]
    assert rep_ok["attestation_results"]["CH-001"]["verdict"].startswith("ok_")

    # attestation unreachable -> local-valid retained, flagged unverified
    def _raise(url: str, timeout: float):
        raise TimeoutError("simulated: OpenCaseLaw /api/attest unreachable from CI sandbox")

    down_attestor = OpenCaseLawAttestor(fetch=_raise)
    rep_down = PostGenerationValidator(bundle, use_attestation=True, attestor=down_attestor)
    rep = rep_down.validate_citations(["CH-001", "GHOST"])
    assert rep["valid_citations"] == ["CH-001"]
    assert rep["unverified_ids"] == ["CH-001"]
    assert "unreachable" in rep["attestation_results"]["CH-001"]["error"]
    assert rep["hallucinated_ids"] == ["GHOST"]
    print("  PASS: strict-local + attestation-up + attestation-down paths")
    return True


def test_attestation_error_body_is_not_verified():
    """Audit repair 2: HTTP-200 ``{"error": ...}`` must never verify a decision.

    Reproduces the observed live body of ``POST /api/attest`` when
    ``draft_text`` is missing, plus the 404 ``{"detail": ...}`` bodies the
    decisions/integrity routes return for unknown ids.
    """
    print(">>> test_attestation_error_body_is_not_verified")
    bundle = _small_bundle()

    attestor = OpenCaseLawAttestor(fetch=lambda url, timeout: dict(OBSERVED_ATTEST_ERROR_BODY))
    res = attestor.attest_decision("CH-001")
    assert res.verified is False, "an HTTP-200 error body must not verify"
    assert res.verdict in ("error_payload", "unresolved_in_both_routes")
    assert "error" not in (res.attestation_data or {})

    rep = PostGenerationValidator(bundle, use_attestation=True, attestor=attestor).validate_citations(
        ["CH-001"]
    )
    assert rep["verified_ids"] == []
    assert rep["unverified_ids"] == ["CH-001"]

    # the FastAPI 404 shape ({"detail": ...}) must be equally unverified
    detail_attestor = OpenCaseLawAttestor(
        fetch=lambda url, timeout: {"detail": "Decision not found: CH-001"}
    )
    assert detail_attestor.attest_decision("CH-001").verified is False

    # an error payload served against the draft-audit route is inconclusive
    draft = OpenCaseLawAttestor(post=lambda url, payload, timeout: dict(OBSERVED_ATTEST_ERROR_BODY))
    assert draft.attest_draft("").verified is False
    print("  PASS: 200 error bodies, 404 detail bodies and empty drafts stay unverified")
    return True


def test_attestation_empty_and_mismatched_payloads_unverified():
    """Audit repair 2: empty payloads, id mismatches and inconclusive audits."""
    print(">>> test_attestation_empty_and_mismatched_payloads_unverified")
    assert OpenCaseLawAttestor(fetch=lambda u, t: {}).attest_decision("CH-001").verified is False
    assert OpenCaseLawAttestor(fetch=lambda u, t: None).attest_decision("CH-001").verified is False
    assert OpenCaseLawAttestor(fetch=lambda u, t: []).attest_decision("CH-001").verified is False

    mismatch = OpenCaseLawAttestor(
        fetch=lambda u, t: {"decision_id": "SOME-OTHER-CASE", "court": "bger"}
    )
    assert mismatch.attest_decision("CH-001").verified is False

    # attest ok=true but zero case citations audited => inconclusive, not verified
    inconclusive = OpenCaseLawAttestor(
        post=lambda u, p, t: {"ok": True, "citations_found": 0, "citations_ok": 0, "issues": []}
    )
    assert inconclusive.attest_draft("Der Fall betrifft X.").verified is False

    # non-2xx surfaces as an exception from the default transport -> unverified
    def _http_error(url: str, timeout: float):
        raise OSError("HTTP Error 500: Internal Server Error")

    assert OpenCaseLawAttestor(fetch=_http_error).attest_decision("CH-001").verified is False
    print("  PASS: empty / mismatched / inconclusive / non-2xx all unverified")
    return True


def test_evidence_source_check_rejects_fabricated_quote():
    """Audit repair 3: the auditor's injection attack must not surface.

    A finding whose evidence quote is absent from the cited decision's text
    must lose that quote (never ``counter_evidence``) and be downgraded to
    high uncertainty — while staying visible as a candidate counter-authority.
    """
    print(">>> test_evidence_source_check_rejects_fabricated_quote")
    bundle = _small_bundle()
    forged = AdversarialFinding(
        decision_id="CH-003", reason="limiting",
        evidence_refs=["Dieses Zitat existiert nicht im Entscheidtext 12345."],
        uncertainty=0.1, confidence=0.95,
    )
    checked, report = source_check_findings([forged], bundle)
    assert checked[0].evidence_refs == [], "fabricated quote must be rejected"
    assert checked[0].uncertainty >= DOWNGRADED_MIN_UNCERTAINTY
    assert report["refs_rejected"] == 1 and report["refs_verified"] == 0
    assert report["n_downgraded"] == 1

    # product-shaped bundle containing the small fixture decisions
    mini = {
        "bundle_version": "1.0", "query": bundle.query, "query_variants": [],
        "answer": {"prose": "", "statements": [], "cited_decision_ids": ["CH-001"]},
        "decisions": [
            {"decision_id": dec.decision_id, "court": "bger", "language": "de", "rank": i,
             "score": 1.0, "provenance": {}, "snippet": dec.text, "cluster_id": "c1",
             "x": 0.0, "y": 0.0, "counter_status": "none", "canonical_url": "", "citation": dec.title}
            for i, dec in enumerate(bundle.decisions)
        ],
        "clusters": [{"cluster_id": "c1", "label": "c",
                      "decision_ids": list(bundle.decision_ids)}],
        "relations": [],
        "provenance": {},
    }

    result = ProviderResult(answer="Rule [CH-001]", cited_decision_ids=["CH-001"], model_used="t")
    package = package_answer(result, [forged], bundle)
    audited = apply_to_product_bundle(mini, package, [forged])
    by_id = {d["decision_id"]: d for d in audited["decisions"]}

    assert by_id["CH-003"]["counter_status"] == "candidate-limiting", (
        "a downgraded finding must stay visible (never hidden)"
    )
    assert by_id["CH-003"]["counter_evidence"] == "", (
        "fabricated quote must not reach counter_evidence"
    )
    assert by_id["CH-003"]["counter_uncertainty"] >= DOWNGRADED_MIN_UNCERTAINTY
    assert by_id["CH-003"]["counter_reason"] == "limiting"

    prov = audited["provenance"]["generative_audit"]
    check = prov["evidence_source_check"]
    assert check["refs_rejected"] == 1
    assert check["findings"][0]["rejected_refs"] == forged.evidence_refs, (
        "rejected quotes are kept in provenance for audit, never as evidence"
    )
    assert prov["evidence_boundary_rejected_refs"] == 0  # already stripped upstream
    for dec in audited["decisions"]:
        assert "Dieses Zitat" not in str(dec.get("counter_evidence", ""))
    assert "Dieses Zitat" not in str(audited["answer"])

    # defence in depth: even an UNCHECKED status cannot push a quote through
    package.decision_statuses["CH-003"].evidence_refs.append(
        "Dieses Zitat existiert nicht im Entscheidtext 12345."
    )
    audited2 = apply_to_product_bundle(mini, package, [forged])
    by_id2 = {d["decision_id"]: d for d in audited2["decisions"]}
    assert by_id2["CH-003"]["counter_evidence"] == ""
    assert by_id2["CH-003"]["counter_evidence_verified"] is False
    assert audited2["provenance"]["generative_audit"]["evidence_boundary_rejected_refs"] == 1
    print("  PASS: fabricated quote rejected, finding downgraded but still visible")
    return True


def test_evidence_source_check_accepts_verbatim_quote():
    """Audit repair 3 (positive path): verbatim quotes survive and are surfaced."""
    print(">>> test_evidence_source_check_accepts_verbatim_quote")
    bundle = _small_bundle()
    good = AdversarialFinding(
        decision_id="CH-002", reason="limiting",
        evidence_refs=["exceeding two years is presumptively disproportionate"],
        uncertainty=0.2, confidence=0.9,
    )
    checked, report = source_check_findings([good], bundle)
    assert checked[0].evidence_refs == good.evidence_refs
    assert checked[0].uncertainty == 0.2
    assert report["refs_verified"] == 1 and report["n_downgraded"] == 0

    # normalisation: case + whitespace collapse, and unicode-hyphen folding
    assert quote_in_source("EXCEEDING   TWO YEARS is presumptively disproportionate",
                           bundle.by_id()["CH-002"].text)
    assert quote_in_source(
        "Karenz\u2011entschädigung fuehrt zur Unverbindlichkeit",
        "Der Verzicht auf die Karenz-entschädigung fuehrt zur Unverbindlichkeit.",
    )
    assert normalize_quote("  A\u00a0Quote\u2014Here. ") == "a quote-here."
    assert not quote_in_source("two", "A clause exceeding two years is disproportionate."), (
        "quotes shorter than the minimum evidential length must not verify"
    )
    assert not quote_in_source("this sentence is not in the decision at all 999",
                               bundle.by_id()["CH-002"].text)

    # the boundary filter keeps non-quote internal markers
    from generative_audit.evidence import verified_evidence_refs
    kept, rejected = verified_evidence_refs(
        ["cited in generated answer", "exceeding two years is presumptively disproportionate",
         "not in the text at all 12345"],
        bundle.by_id()["CH-002"].text,
    )
    assert kept[0] == "cited in generated answer"
    assert kept[1].startswith("exceeding two years")
    assert rejected == 1
    print("  PASS: verbatim quotes survive normalisation; boundary filter counts rejects")
    return True


def test_product_bundle_adapter():
    """Acceptance (8): consumes the accepted product query_result_bundle shape."""
    print(">>> test_product_bundle_adapter")
    with open(FIXTURE_BUNDLE, encoding="utf-8") as fh:
        product_bundle = json.load(fh)
    bundle = from_product_bundle(product_bundle)
    assert bundle.query == product_bundle["query"]
    assert bundle.decision_ids[0] == "CH-2020-FR-001"  # rank-ordered
    assert "CH-2021-DE-042" in bundle.decision_ids
    assert bundle.by_id()["CH-2019-DE-014"].text  # full_text/snippet mapped
    print(f"  PASS: product bundle adapted ({len(bundle.decision_ids)} decisions)")
    return True


def test_run_generative_audit_end_to_end_contract():
    """Acceptance (3)+(4)+(8): one-call seam produces a product-compatible bundle."""
    print(">>> test_run_generative_audit_end_to_end_contract")
    with open(FIXTURE_BUNDLE, encoding="utf-8") as fh:
        product_bundle = json.load(fh)

    fixture_findings = [
        AdversarialFinding(
            decision_id="CH-2021-DE-042", title="BGer 4A_42/2021", reason="limiting",
            # verbatim substring of the fixture decision text (source-checked)
            evidence_refs=["Der Verzicht des Arbeitgebers auf die Karenzentschaedigung "
                           "waehrend der"],
            uncertainty=0.25, confidence=0.85,
        ),
        AdversarialFinding(
            decision_id="CH-2022-IT-007", title="BGer 4A_7/2022", reason="exception",
            evidence_refs=["non e opponibile al dipendente che non aveva alcun accesso"],
            uncertainty=0.3, confidence=0.8,
        ),
        AdversarialFinding(
            decision_id="CH-2016-FR-088", title="TF 4A_88/2016", reason="minority_line",
            evidence_refs=["Ligne minoritaire ancienne"],
            uncertainty=0.4, confidence=0.7,
        ),
    ]

    audited = run_generative_audit(
        product_bundle,
        fixture_mode=True,
        fixture_answer="A valid non-compete must be limited in time, space and content "
                       "and protect a legitimate employer interest [CH-2020-FR-001].",
        fixture_cited_ids=["CH-2020-FR-001"],
        fixture_findings=fixture_findings,
    )

    assert _check_product_compatible(audited) == [], _check_product_compatible(audited)
    json.dumps(audited)  # must stay JSON-serializable for the product server

    by_id = {d["decision_id"]: d for d in audited["decisions"]}
    assert by_id["CH-2020-FR-001"]["counter_status"] == "cited"
    assert by_id["CH-2021-DE-042"]["counter_status"] == "candidate-limiting"
    assert by_id["CH-2022-IT-007"]["counter_status"] == "candidate-contrary"
    assert by_id["CH-2016-FR-088"]["counter_status"] == "candidate-contrary"
    assert by_id["CH-2019-DE-014"]["counter_status"] == "none"
    assert by_id["CH-2021-DE-042"]["counter_evidence"]
    assert by_id["CH-2021-DE-042"]["counter_uncertainty"] < 1.0

    assert audited["answer"]["cited_decision_ids"] == ["CH-2020-FR-001"]
    assert audited["answer"]["method"] == "generative_audit_llm_v2"
    assert audited["answer"]["prose"]
    prov = audited["provenance"]["generative_audit"]
    assert prov["status_summary"]["limiting"] == 1
    assert prov["status_summary"]["contrary_or_exception"] == 2
    assert prov["adversarial"]["method"] == "fixture_adversarial_v2"
    print("  PASS: audited bundle is product-compatible with counter-authorities visible")
    return True


def test_end_to_end_cached_example():
    """Acceptance (6): cached deterministic example with answer + findings."""
    print(">>> test_end_to_end_cached_example")
    with open(FIXTURE_BUNDLE, encoding="utf-8") as fh:
        product_bundle = json.load(fh)
    audited = run_generative_audit(
        product_bundle,
        fixture_mode=True,
        fixture_answer="Grounded fixture answer citing the lead decision [CH-2020-FR-001].",
        fixture_cited_ids=["CH-2020-FR-001"],
        fixture_findings=[
            AdversarialFinding(decision_id="CH-2021-DE-042", reason="limiting",
                               evidence_refs=["Karenzentschaedigung"], uncertainty=0.25,
                               confidence=0.85),
        ],
    )
    cached = {
        "query": product_bundle["query"],
        "mode": "fixture",
        "answer": audited["answer"]["prose"],
        "cited_decision_ids": audited["answer"]["cited_decision_ids"],
        "adversarial_findings": [
            {"decision_id": "CH-2021-DE-042", "reason": "limiting", "uncertainty": 0.25}
        ],
        "status_summary": audited["provenance"]["generative_audit"]["status_summary"],
        "counter_statuses": {
            d["decision_id"]: d["counter_status"] for d in audited["decisions"]
        },
        "evidence_source_check": audited["provenance"]["generative_audit"]["evidence_source_check"],
        "audited_product_bundle": audited,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lex-genaudit-cache-") as tmp:
        out = Path(tmp) / "cached_example_fixture.json"
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(cached, fh, indent=2, ensure_ascii=False)
        with open(out, encoding="utf-8") as fh:
            back = json.load(fh)
        assert back["answer"] == cached["answer"]
        assert back["cited_decision_ids"] == ["CH-2020-FR-001"]
        assert back["adversarial_findings"][0]["reason"] == "limiting"
        assert back["counter_statuses"]["CH-2021-DE-042"] == "candidate-limiting"
    # the suite never mutates claim-bearing result files (audit observation);
    # publication belongs to run_e2e.py
    assert cached["evidence_source_check"]["refs_verified"] == 1
    assert cached["evidence_source_check"]["refs_rejected"] == 0
    print("  PASS: cached example round-trips through a temp path (results/ untouched)")
    return True


def test_real_model_smoke():
    """Acceptance (1): live no-owner-cost model path (opt-in).

    Set LEX_REAL_MODEL=1 to run.  Uses the OpenCode CLI with a free model
    from state/model_health.json (or LEX_MODEL).  Asserts the hard
    invariant: every cited ID is in the bundle.
    """
    if os.environ.get("LEX_REAL_MODEL", "0") != "1":
        print(">>> test_real_model_smoke: SKIPPED (set LEX_REAL_MODEL=1 to enable)")
        return True
    print(">>> test_real_model_smoke")
    bundle = _small_bundle()
    model = os.environ.get("LEX_MODEL") or None
    p = Provider(model=model, use_attestation=False, timeout=180.0)
    r = p.generate(bundle)
    assert r.ok, f"real provider failed: {r.error} attempts={r.attempts}"
    assert r.answer, "real provider produced no answer text"
    for cid in r.cited_decision_ids:
        assert cid in bundle.decision_ids
    assert not r.redacted_citation_ids, (
        f"model hallucinated IDs that had to be redacted: {r.redacted_citation_ids}"
    )
    print(f"  PASS: real model {r.model_used} produced {len(r.cited_decision_ids)} "
          f"bundle-constrained citations")
    return True


def test_live_model_citation_styles_parentheses_and_unicode_hyphens():
    """Regression (run 38176699303): live models cite as (CH‑2020‑FR‑001).

    Parenthetical markers and unicode (non-breaking) hyphens must still be
    recognized as decision-ID citations, while ordinary parentheses and
    numbered citations stay untouched.
    """
    print(">>> test_live_model_citation_styles_parentheses_and_unicode_hyphens")
    bundle = _small_bundle()
    raw = (
        "A valid clause must be limited in time, space and content "
        "(CH\u2011001). Blanket clauses fail the proportionality test [CH\u2011002]. "
        "Nested style ([CH\u2011003]) also occurs. "
        "See the 2019 amendment (2019) and the annex [1]. "
        "An immortal holding is reported in (BGE-9999-FAKE)."
    )

    def fake_runner(prompt: str, model: str, timeout: float) -> str:
        return raw

    p = Provider(model="fake/model", runner=fake_runner, use_attestation=False)
    r = p.generate(bundle)
    assert r.ok, r.error
    assert r.cited_decision_ids == ["CH-001", "CH-002", "CH-003"], r.cited_decision_ids
    assert "BGE-9999-FAKE" in r.validation_report["hallucinated_ids"]
    assert "BGE-9999-FAKE" not in r.answer
    assert "(2019)" in r.answer and "[1]" in r.answer, (
        f"non-ID parentheses/numbers must survive redaction: {r.answer}"
    )
    print("  PASS: parenthetical + unicode-hyphen citations parsed; prose protected")
    return True


def test_adversarial_parse_normalizes_unicode_hyphens():
    print(">>> test_adversarial_parse_normalizes_unicode_hyphens")
    bundle = _small_bundle()
    raw = '[{"decision_id": "CH\u2011002", "reason": "limiting", "evidence_refs": ["two years"], "uncertainty": 0.2}]'
    findings = AdversarialPass(bundle=bundle, answer="a", model="m").parse_findings(raw)
    assert [f.decision_id for f in findings] == ["CH-002"]
    print("  PASS: adversarial decision_id normalization")
    return True


def test_adversarial_format_retry_recovers_prose_response():
    """Live-model behavior: prose reply first, strict JSON on the single retry."""
    print(">>> test_adversarial_format_retry_recovers_prose_response")
    bundle = _small_bundle()
    calls = {"n": 0}

    def prose_then_json(prompt: str, model: str, timeout: float) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            return "I think decision two limits the answer because of its two-year rule."
        return json.dumps([
            {"decision_id": "CH-002", "reason": "limiting",
             "evidence_refs": ["two-year rule"], "uncertainty": 0.3}
        ])

    adv = AdversarialPass(bundle=bundle, answer="ans", model="m", runner=prose_then_json)
    findings, info = adv.run_with_info()
    assert calls["n"] == 2, "exactly one format retry expected"
    assert [f.decision_id for f in findings] == ["CH-002"]
    assert info["retries"] == 1
    print("  PASS: single format retry recovers structured findings")
    return True


def test_cited_but_contrary_stays_visible_as_counter():
    """Product doctrine: a cited decision that also limits/contradicts must not
    be hidden behind counter_status='cited' (UI hides only none/cited)."""
    print(">>> test_cited_but_contrary_stays_visible_as_counter")
    with open(FIXTURE_BUNDLE, encoding="utf-8") as fh:
        product_bundle = json.load(fh)
    # Lead decision is cited AND flagged as an exception-laden authority.
    audited = run_generative_audit(
        product_bundle,
        fixture_mode=True,
        fixture_answer="Valid when limited [CH-2020-FR-001].",
        fixture_cited_ids=["CH-2020-FR-001"],
        fixture_findings=[
            AdversarialFinding(decision_id="CH-2020-FR-001", reason="limiting",
                               evidence_refs=["but only for two years"], uncertainty=0.2),
        ],
    )
    by_id = {d["decision_id"]: d for d in audited["decisions"]}
    assert by_id["CH-2020-FR-001"]["counter_status"] == "candidate-limiting", (
        "cited+limiting decision must remain a visible counter-authority"
    )
    assert "CH-2020-FR-001" in audited["answer"]["cited_decision_ids"]
    print("  PASS: cited+limiting stays discoverable as counter-authority")
    return True


def test_live_ocl_endpoints_and_sound_verification():
    """Audit repair 1+2 (opt-in): the documented host is reachable and sound.

    Set ``LEX_LIVE_OCL=1``.  Probes ``https://mcp.opencaselaw.ch/api`` with
    the correct methods, asserts the retired ``opencaselaw.org`` host is the
    wrong one, and re-checks that a live ``200 {"error": ...}`` body from
    ``POST /attest`` cannot be mistaken for verification.
    """
    if os.environ.get("LEX_LIVE_OCL", "0") != "1":
        print(">>> test_live_ocl_endpoints_and_sound_verification: SKIPPED "
              "(set LEX_LIVE_OCL=1 to enable)")
        return True
    print(">>> test_live_ocl_endpoints_and_sound_verification")
    from generative_audit.opencaselaw import default_fetch, default_post

    base = DEFAULT_OCL_API_BASE
    spec = default_fetch(f"{base}/openapi.json", 30.0)
    assert spec["info"]["title"] == "OpenCaseLaw API", spec["info"]
    assert any(s.get("url", "").startswith(base) for s in spec.get("servers", []))

    # routes required by acceptance (5) exist with the documented methods
    assert "post" in spec["paths"]["/attest"]
    assert "post" in spec["paths"]["/verify-claim"]
    assert "get" in spec["paths"]["/decisions/{decision_id}"]
    assert "get" in spec["paths"]["/integrity/{decision_id}"]

    real_id = "bge_BGE_89_II_126"
    attestor = OpenCaseLawAttestor(enabled=True, timeout=45.0)
    res = attestor.attest_decision(real_id)
    assert res.verified is True, f"real decision must verify: {res.error}"
    assert res.evidence.get("decision_id") == real_id or res.evidence.get("leaf_hash")

    unknown = attestor.attest_decision("CH-2020-FR-001")
    assert unknown.verified is False, "synthetic id must stay unverified against the corpus"

    # live POST /attest: a malformed draft yields HTTP-200 {"error": ...}
    bad = default_post(f"{base}/attest", {}, 30.0)
    assert "error" in bad, bad
    res_bad = attestor.attest_draft("")
    assert res_bad.verified is False

    # live POST /attest with a real draft + audit_quotes
    good = attestor.attest_draft(
        f"Laut {real_id} ist ein Konkurrenzverbot auslegungsbedürftig.", audit_quotes=True
    )
    assert good.attestation_data is not None or good.verified or good.verdict

    # verify-claim returns a judge verdict, never a bare truthy body
    claim = attestor.verify_claim(
        "Ein Konkurrenzverbot in einem Werklieferungsvertrag ist auslegungsbedürftig.", real_id
    )
    assert claim.verified is True and claim.evidence.get("supports") in {
        "yes", "partial", "no", "contradicts", "unrelated"}

    # the retired host must NOT be used as the default
    assert "opencaselaw.org" not in base
    assert RETIRED_WRONG_API_BASE.startswith("https://opencaselaw.org")
    print(f"  PASS: live host {base} verified decision {real_id} "
          f"({res.endpoint.split(' | ')[0]}), synthetic id unverified")
    return True


def test_product_compat_uses_accepted_validator():
    """Audit observation: reconcile the product-compatibility check with core.

    The suite must call the *accepted* ``product/query/bundle.py`` validator
    when the core mount is available, and fall back to a faithful offline
    mirror otherwise — never a divergent re-implementation.
    """
    print(">>> test_product_compat_uses_accepted_validator")
    errors, source = validate_product_bundle({"query": "x"})
    assert any("missing top-level key" in e for e in errors), errors
    print(f"  validator source: {source}")

    with open(FIXTURE_BUNDLE, encoding="utf-8") as fh:
        fixture = json.load(fh)
    ok, source2 = validate_product_bundle(fixture)
    assert ok == [], (ok, source2)

    if source.startswith("accepted-core"):
        from generative_audit.product_compat import load_accepted_validator
        fn, _ = load_accepted_validator()
        assert fn(fixture) == [], "mirror and accepted validator must agree"
        print(f"  PASS: accepted validator used ({source}); mirror agrees")
    else:
        print("  PASS: offline mirror used (accepted core mount not present)")
    return True


ALL_TESTS = [
    test_real_path_fixture_and_contract_surface,
    test_fixture_mode_deterministic,
    test_provider_preserves_multi_paragraph_answer,
    test_prompt_surfaces_relevant_passage_beyond_judgment_prefix,
    test_fixture_rejects_invented_cited_ids,
    test_hallucinated_citation_rejection_and_redaction,
    test_redaction_helper_unit,
    test_provider_fallback_across_models,
    test_provider_total_failure_is_recorded,
    test_prompt_constrains_citations,
    test_adversarial_prefers_live_proven_fast_reviewer,
    test_adversarial_fallback_across_models,
    test_adversarial_prompt_shortlist_is_bounded_multilingual_and_counter_aware,
    test_adversarial_parse_rejects_unknown_ids,
    test_adversarial_parse_deterministic,
    test_adversarial_prompt_is_independent,
    test_adversarial_fixture_mode_challenge_only,
    test_structured_statuses_merging,
    test_unsupported_status_downgrade,
    test_post_generation_validation_strict_local_and_attestation,
    test_attestation_error_body_is_not_verified,
    test_attestation_empty_and_mismatched_payloads_unverified,
    test_evidence_source_check_rejects_fabricated_quote,
    test_evidence_source_check_accepts_verbatim_quote,
    test_product_bundle_adapter,
    test_run_generative_audit_end_to_end_contract,
    test_end_to_end_cached_example,
    test_cited_but_contrary_stays_visible_as_counter,
    test_live_model_citation_styles_parentheses_and_unicode_hyphens,
    test_adversarial_parse_normalizes_unicode_hyphens,
    test_adversarial_format_retry_recovers_prose_response,
    test_product_compat_uses_accepted_validator,
    test_live_ocl_endpoints_and_sound_verification,
    test_real_model_smoke,
]


if __name__ == "__main__":
    passed = failed = 0
    for test in ALL_TESTS:
        try:
            test()
            passed += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  FAIL: {test.__name__}: {exc}")
            import traceback
            traceback.print_exc()
    print(f"\n{'=' * 64}\nResults: {passed} passed, {failed} failed out of {len(ALL_TESTS)}")
    sys.exit(1 if failed else 0)
