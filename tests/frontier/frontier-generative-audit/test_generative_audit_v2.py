"""LexMachina Frontier — generative audit v2.1 — frozen deterministic suite.

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
      where feasible, strict local otherwise);
  (6) end-to-end cached example with answer + adversarial findings;
  (7) tests for invented-citation rejection, unsupported-status downgrade,
      provider failure fallback and deterministic parsing;
  (8) narrow integration contract for the product lane.

Run:  python3 tests/frontier/frontier-generative-audit/test_generative_audit_v2.py
Or:   python3 -m pytest tests/frontier/frontier-generative-audit/ -q
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List

HERE = Path(__file__).resolve().parent
CANONICAL = HERE.parents[2] / "frontier" / "frontier-generative-audit"
sys.path.insert(0, str(CANONICAL))

import generative_audit  # noqa: E402

assert Path(generative_audit.__file__).resolve().is_relative_to(CANONICAL.resolve()), (
    f"imported wrong package tree: {generative_audit.__file__}"
)

from generative_audit.adversarial import (  # noqa: E402
    AdversarialFinding,
    AdversarialPass,
)
from generative_audit.integration_contract import (  # noqa: E402
    CONTRACT_VERSION,
    package_answer,
    apply_to_product_bundle,
    run_generative_audit,
)
from generative_audit.models import StatusLabel  # noqa: E402
from generative_audit.opencaselaw import (  # noqa: E402
    OpenCaseLawAttestor,
    PostGenerationValidator,
)
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

# Product-required keys, mirroring product/query/bundle.py (accepted core mount).
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
    """Replicate product validate_bundle() rules (accepted core contract)."""
    errors = []
    for key in PRODUCT_REQUIRED_TOP:
        if key not in bundle:
            errors.append(f"missing top-level key: {key}")
    if errors:
        return errors
    ids = set()
    for i, d in enumerate(bundle["decisions"]):
        for key in PRODUCT_REQUIRED_DECISION:
            if key not in d:
                errors.append(f"decision[{i}] missing key: {key}")
        did = d.get("decision_id")
        if did in ids:
            errors.append(f"duplicate decision_id: {did}")
        ids.add(did)
    cited = set(bundle.get("answer", {}).get("cited_decision_ids", []))
    unknown = cited - ids
    if unknown:
        errors.append(f"answer cites unknown decision_ids: {sorted(unknown)}")
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
                           evidence_refs=["but not for apprentices"], uncertainty=0.3),
        AdversarialFinding(decision_id="CH-002", reason="contradictory",
                           evidence_refs=["two years presumptively excessive"], uncertainty=0.2),
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

    # strict local mode (default in CI: no egress)
    report = PostGenerationValidator(bundle, use_attestation=False).validate_citations(
        ["CH-001", "GHOST"]
    )
    assert report["mode"] == "strict_local"
    assert report["valid_citations"] == ["CH-001"]
    assert report["hallucinated_ids"] == ["GHOST"]

    # attestation reachable -> verified
    ok_attestor = OpenCaseLawAttestor(fetch=lambda url, timeout: {"decision": "ok", "url": url})
    report_ok = PostGenerationValidator(bundle, use_attestation=True, attestor=ok_attestor)
    rep_ok = report_ok.validate_citations(["CH-001"])
    assert rep_ok["mode"] == "attestation+local"
    assert rep_ok["verified_ids"] == ["CH-001"]

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
            evidence_refs=["Der Verzicht auf die Karenzentschaedigung fuehrt zur Unverbindlichkeit"],
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
        "audited_product_bundle": audited,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "cached_example_fixture.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(cached, fh, indent=2, ensure_ascii=False)
    with open(out, encoding="utf-8") as fh:
        back = json.load(fh)
    assert back["answer"] == cached["answer"]
    assert back["cited_decision_ids"] == ["CH-2020-FR-001"]
    assert back["adversarial_findings"][0]["reason"] == "limiting"
    assert back["counter_statuses"]["CH-2021-DE-042"] == "candidate-limiting"
    print(f"  PASS: cached example written to {out}")
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


ALL_TESTS = [
    test_real_path_fixture_and_contract_surface,
    test_fixture_mode_deterministic,
    test_fixture_rejects_invented_cited_ids,
    test_hallucinated_citation_rejection_and_redaction,
    test_redaction_helper_unit,
    test_provider_fallback_across_models,
    test_provider_total_failure_is_recorded,
    test_prompt_constrains_citations,
    test_adversarial_parse_rejects_unknown_ids,
    test_adversarial_parse_deterministic,
    test_adversarial_prompt_is_independent,
    test_adversarial_fixture_mode_challenge_only,
    test_structured_statuses_merging,
    test_unsupported_status_downgrade,
    test_post_generation_validation_strict_local_and_attestation,
    test_product_bundle_adapter,
    test_run_generative_audit_end_to_end_contract,
    test_end_to_end_cached_example,
    test_cited_but_contrary_stays_visible_as_counter,
    test_live_model_citation_styles_parentheses_and_unicode_hyphens,
    test_adversarial_parse_normalizes_unicode_hyphens,
    test_adversarial_format_retry_recovers_prose_response,
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
