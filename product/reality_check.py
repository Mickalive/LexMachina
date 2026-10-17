#!/usr/bin/env python3
"""Local pre-validation of the frozen Product Reality Check legs.

Why this exists
---------------
``.github/workflows/product-reality-check.yml`` is the durable gate: it only
runs on a push to ``lab/product`` whose commit message contains
``[reality-check]``, and a failed leg therefore costs a full GitHub round trip
plus an audit cycle.  This runner executes the *same* questions and the *same*
assertions locally so that

  1. a leg can be debugged before it is burned into a durable Actions run;
  2. the independent auditor can recompute the gate instead of trusting prose;
  3. failures are recorded as evidence instead of being rediscovered.

Scope honesty: results produced here are LOCAL evidence.  They are written to
``results/product/reality_check/`` and are never a substitute for the durable
Actions run; ``state/product.json`` keeps ``durable_green_run_id: null`` until
one exists.

Gate parity
-----------
The question strings and the assertion semantics are copied from
``product-reality-check.yml`` at the moment this file was written (run
38554018429, workflow head ``097f00d``).  ``test_reality_check_parity`` in
``product/tests/test_reality_check.py`` fails if the workflow and this file
drift apart, so the two cannot silently diverge.

Usage
-----
    python product/reality_check.py --slug rent-default            # one leg, live
    python product/reality_check.py --slug all --mode fixture      # offline wiring pass
    python product/reality_check.py --list

``--mode fixture`` is an OFFLINE WIRING check (network-free replay of cached
envelopes → bundle → map coordinates → citations → adversarial recording).
It emits ``wiring::*`` gates only; the frozen structural/truth/recall gates are
live-only and are never evaluated — or reported as passed — in fixture mode.
The business-judgment-rule leg additionally carries an explicit
``wiring::frozen_recall_gate_not_evaluated`` marker recording that the frozen
recall leg was not evaluated there (repair of audit D1, cycle 39014141628:
the branch used to emit the frozen gate name with ``passed=true``).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Frozen questions — byte-identical to the workflow matrix.
LEGS: dict[str, str] = {
    "rent-default": (
        "Sous quelles conditions un bailleur peut-il résilier un bail d'habitation "
        "pour retard dans le paiement du loyer selon le droit suisse, et quelles "
        "exceptions ou limites jurisprudentielles existent ?"
    ),
    "petty-theft-dismissal": (
        "Un vol de faible valeur commis par un employé justifie-t-il un licenciement "
        "immédiat selon l'art. 337 CO ? Quelles circonstances font varier la réponse ?"
    ),
    "corporate-criminal-liability": (
        "La responsabilité pénale de l'entreprise selon l'art. 102 CP est-elle "
        "subsidiaire ou primaire, et pour quelles infractions ? Quelles exigences "
        "d'organisation doivent être prouvées ?"
    ),
    "business-judgment-rule": (
        "Dans quelles conditions le juge suisse s'abstient-il de revoir une décision "
        "commerciale d'un conseil d'administration au titre de la business judgment "
        "rule, et quelles exceptions ou limites ressortent de la jurisprudence ?"
    ),
}


def norm(value: Any) -> str:
    """NFKD + strip diacritics + casefold + collapse whitespace (workflow parity)."""
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.casefold().split())


class GateFailure(Exception):
    """Raised by the workflow-style assertions; carries the report payload."""


def _require(condition: bool, report: dict, message: str) -> None:
    if not condition:
        raise GateFailure(message or "assertion failed")


def structural_gates(report: dict) -> None:
    """Assertions that run for every leg before the substantive truth gates.

    Workflow parity: this mirrors ``.github/workflows/product-reality-check.yml``
    (structural block + language/latency block).  The local copy exists so a
    leg can be debugged before it is burned into a durable Actions run; the
    parity test fails if the two drift apart.
    """
    final = report["bundle"]
    answer = final.get("answer", {})
    ga = final.get("provenance", {}).get("generative_audit", {}) or {}
    adv = ga.get("adversarial") or {}
    errors = report["validation_errors"]
    _require(errors == [], report, f"bundle validation errors: {errors}")
    _require(answer.get("status") == "ready", report, "answer status not ready")
    _require(answer.get("method") == "generative_audit_llm_v2", report,
             f"unexpected answer method: {answer.get('method')}")
    _require(len(str(answer.get("prose") or "")) >= 120, report, "answer prose too short")
    _require(bool(answer.get("cited_decision_ids")), report, "answer cites nothing")
    ids = {d["decision_id"] for d in final["decisions"]}
    _require(set(answer.get("cited_decision_ids") or []) <= ids, report,
             "answer cites ids outside the bundle")
    _require(ga.get("provider_error") in (None, ""), report,
             f"provider error: {ga.get('provider_error')}")
    _require(adv.get("method") == "independent_llm_adversarial_v2", report,
             f"adversarial method: {adv.get('method')}")
    _require(adv.get("error") in (None, ""), report, f"adversarial error: {adv.get('error')}")
    _require(len(final.get("decisions") or []) <= 100, report,
             f"top_n=100 must not serve {len(final.get('decisions') or [])} decisions")
    counter_rows = [
        d for d in final.get("decisions") or []
        if d.get("counter_status") in {"candidate-limiting", "candidate-contrary",
                                       "limiting", "contrary_or_exception"}
    ]
    for counter in counter_rows:
        _require(counter.get("counter_evidence_verified") is True, report,
                 f"surfaced counter lacks verified evidence: {counter.get('decision_id')}")
        _require(str(counter.get("counter_evidence") or "").strip(), report,
                 f"surfaced counter has empty evidence: {counter.get('decision_id')}")
        _require((counter.get("rank") or 10**9) <= 40 or bool(counter.get("adversarial_channel")),
                 report,
                 f"surfaced counter escaped precision policy: {counter.get('decision_id')}")

    prose_raw = str(answer.get("prose") or "")
    prose = norm(prose_raw)
    # All four frozen questions are in French. A Swiss-law answer may quote
    # German/Italian sources, but the synthesis itself must remain French
    # and must not contain corrupted CJK/token garbage.
    _require(not re.search(r"[\u3400-\u9fff]", prose_raw), report,
             "corrupted/non-French token leakage")
    french_markers = sum(
        marker in f" {prose} "
        for marker in (" le ", " la ", " les ", " selon ", " doit ", " lorsque ",
                       " tribunal ", " responsabilite ", " resiliation ")
    )
    _require(french_markers >= 3, report, "answer is not synthesized in the user's language")

    # Product latency gate: the map can be progressive, but a full answer
    # taking five-to-eight minutes is not acceptable even if legally sound.
    total_seconds = report.get("total_seconds")
    _require(total_seconds is not None and total_seconds < 300, report,
             f"full product answer too slow: {total_seconds}s")


def truth_gates(slug: str, report: dict) -> None:
    """Substantive Swiss-law truth gates — workflow parity, one branch per slug.

    This mirrors ``.github/workflows/product-reality-check.yml`` verbatim
    (same patterns, same literals, same messages): structural green is not
    enough, and a fluent but materially wrong answer must fail.  The parity
    test fails if the two drift apart.  Gates are only ever strengthened
    here, never weakened to make a run green.
    """
    final = report["bundle"]
    answer = final.get("answer", {})
    prose = norm(answer.get("prose"))
    cited_ids = set(answer.get("cited_decision_ids") or [])
    ids = {d["decision_id"] for d in final["decisions"]}

    if slug == "rent-default":
        # Do not allow the 30-day cure period + a separate month-end phrase
        # to masquerade as the distinct Art. 257d(2) termination notice.
        notice_patterns = (
            r"(?:preavis|delai de conge|kundigungsfrist)[^.!?\n]{0,100}30\s+jours[^.!?\n]{0,120}(?:fin (?:d'un|du|de) mois|ende eines monats|monatsende)",
            r"30\s+jours[^.!?\n]{0,100}(?:pour|jusqu.a|sur)[^.!?\n]{0,50}(?:fin (?:d'un|du|de) mois|ende eines monats|monatsende)",
            r"30\s+tage[^.!?\n]{0,100}(?:ende eines monats|monatsende)",
        )
        _require(any(re.search(p, prose) for p in notice_patterns), report,
                 "missing distinct Art. 257d(2) 30-day notice to month-end")
        _require(
            "abus" in prose or "bonne foi" in prose or "rechtsmissbrauch" in prose,
            report,
            "missing jurisprudential limitation / good-faith branch",
        )

    elif slug == "corporate-criminal-liability":
        _require("subsidi" in prose, report, "missing Art. 102(1) subsidiary branch")
        _require(
            "responsabilite primaire" in prose or "responsabilite originaire" in prose
            or "originar" in prose,
            report,
            "missing Art. 102(2) primary/original liability",
        )
        _require("ne cree pas une responsabilite primaire" not in prose, report,
                 "answer reverses the Federal Supreme Court's Art. 102(2) classification")
        _require(("organisation" in prose or "organis" in prose), report,
                 "missing organizational-fault requirement")
        _require(
            (("necessair" in prose and "raisonnabl" in prose)
             or ("erforderlich" in prose and "zumutbar" in prose)),
            report,
            "missing concrete Art. 102(2) necessary/reasonable organizational-measures standard",
        )
        _require(bool(cited_ids & {"bge_BGE_142_IV_333", "bger_6B_124_2016"}), report,
                 "answer must use direct Federal Supreme Court Art. 102(2) authority")

    elif slug == "business-judgment-rule":
        _require("information" in prose, report, "missing adequate-information criterion")
        _require(
            "conflit" in prose or "interessenkonflikt" in prose,
            report,
            "missing conflict-of-interest criterion",
        )
        _require(
            "processus" in prose or "verfahren" in prose,
            report,
            "missing decision-process criterion",
        )
        _require(
            "retenue" in prose or "zuruckhaltung" in prose or "deference" in prose
            or "abstient" in prose or "abstenir" in prose,
            report,
            "missing judicial-restraint proposition",
        )
        _require(
            "defendable" in prose or "vertretbar" in prose or "justifiable" in prose
            or "plausible" in prose or "plausibilite" in prose,
            report,
            "missing residual merits threshold",
        )
        _require(bool(cited_ids & {
            "bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013",
            "bger_4A_603_2014", "bger_4A_62_2024", "bge_BGE_139_III_24",
        }), report, "answer must cite direct Federal Supreme Court BJR authority")

    elif slug == "petty-theft-dismissal":
        direct = {"bger_4A_228_2015", "bger_4A_177_2017"}
        _require(bool(ids & direct), report,
                 "retrieval missed direct Federal Supreme Court petty-theft authority")
        _require(bool(cited_ids & direct), report,
                 "answer ignored direct Federal Supreme Court petty-theft authority")
        _require(
            "confiance" in prose or "vertrauen" in prose or "treuepflicht" in prose,
            report,
            "missing trust relationship / duty-of-loyalty analysis",
        )
        low_value_rule = (
            r"(?:meme|y compris)[^.!?\n]{0,60}(?:faible valeur|peu de valeur)[^.!?\n]{0,100}(?:peut|justif)",
            r"(?:faible valeur|peu de valeur)[^.!?\n]{0,120}(?:n.est pas decisive|n.est pas determinante|n.exclut pas|ne fait pas obstacle|peut justifier)",
            r"(?:geringfug|bagatell)[^.!?\n]{0,120}(?:nicht ausschlaggebend|kann[^.!?\n]{0,50}fristlos)",
        )
        _require(any(re.search(p, prose) for p in low_value_rule), report,
                 "answer must state that low value is not itself decisive/exclusive")
        _require(not re.search(
            r"(?:faible valeur|peu de valeur)[^.!?\n]{0,100}ne justifie (?:generalement )?pas",
            prose,
        ), report, "answer improperly turns low value into a presumptive bar")
    else:
        raise GateFailure(f"unknown slug {slug}")


#: The five frozen direct-TF business-judgment-rule authorities the ACCEPTED
#: Core Evaluation frozen benchmark (frozen_sha256 ff57f556...) scores in its
#: ``recall::citation_controlling_authority`` leg.  The durable workflow's own
#: truth gate is deliberately wider (it also accepts ``bge_BGE_139_III_24``);
#: this local parity gate is STRICTER, so a green local live run is predictive
#: of the frozen leg instead of masking it.  Local-only: the durable workflow
#: (control-plane scope) is untouched, and no frozen threshold is weakened.
BJR_DIRECT_TF_FROZEN = frozenset({
    "bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013",
    "bger_4A_603_2014", "bger_4A_62_2024",
})


def frozen_recall_gate(slug: str, report: dict) -> None:
    """Local parity with the frozen benchmark's controlling-authority recall leg.

    Runs ONLY for the business-judgment-rule leg and ONLY in live mode: fixture
    runs are a wiring check and cannot prove retrieval recall, so they record an
    instrumented skip instead of a false pass.  A failure here means the durable
    Product Reality Check would pass its wider truth gate while the accepted
    frozen benchmark still fails — exactly the blind spot that kept the BJR leg
    RED at executions 38920872324 / 38934722443 / 38945976309.
    """
    if slug != "business-judgment-rule":
        return
    if str(report.get("mode") or "live") != "live":
        return  # fixture runs: instrumented skip, recorded by evaluate()
    cited = set((report.get("bundle") or {}).get("answer", {}).get("cited_decision_ids") or [])
    hit = cited & BJR_DIRECT_TF_FROZEN
    if not hit:
        raise GateFailure(
            "answer cites none of the five frozen direct-TF BJR authorities "
            f"{sorted(BJR_DIRECT_TF_FROZEN)} (cited={sorted(cited)}); the frozen "
            "benchmark leg recall::citation_controlling_authority would FAIL"
        )


def fixture_wiring_gates(report: dict) -> list[dict]:
    """Offline wiring checks for ``--mode fixture`` runs.

    Why this exists
    ---------------
    ``--mode fixture`` replays content-addressed OpenCaseLaw envelopes with
    ``mode="offline"`` (network-free) and stamps its synthetic answer and
    adversarial pass with ``fixture_*`` methods by design.  Those inputs can
    therefore **never** satisfy the durable workflow's live-only assertions
    (``generative_audit_llm_v2`` / ``independent_llm_adversarial_v2`` method
    names, ≥120-char French synthesis) nor its substantive truth gates: before
    this wiring pass, every fixture leg died at retrieval ("OpenCaseLaw
    retrieval returned no decisions", preserved in
    ``summary_fixture_20261016T165553Z.json`` / ``..._20261017T055734Z.json``)
    and, once retrieval was repaired, failed forever on a method assertion no
    offline run can meet.

    Contract (frozen by tests)
    --------------------------
    * ``structural_gates`` / ``truth_gates`` / ``frozen_recall_gate`` are
      byte-untouched and are **never evaluated and never reported as passed**
      in fixture mode — fixture runs emit only ``wiring::*`` gates;
    * a fixture summary always carries ``live_gates_evaluated: false`` and an
      explicit claim ceiling, so offline wiring evidence can never be read as
      a green frozen leg;
    * live mode is unchanged: ``evaluate()`` runs the exact live gate set.
    """
    final = report.get("bundle") or {}
    answer = final.get("answer") or {}
    decisions = final.get("decisions") or []
    ga = ((final.get("provenance") or {}).get("generative_audit") or {})
    adv = ga.get("adversarial") or {}
    out: list[dict] = []

    def step(name: str, fn) -> None:
        try:
            fn()
            out.append({"gate": f"wiring::{name}", "passed": True, "detail": ""})
        except GateFailure as exc:
            out.append({"gate": f"wiring::{name}", "passed": False, "detail": str(exc)})

    def _bundle_present() -> None:
        _require("fatal_error" not in report, report,
                 report.get("fatal_error") or "no bundle")
        _require(bool(final), report, "empty bundle")

    step("bundle_present", _bundle_present)
    if not out[-1]["passed"]:
        # Nothing else can be wired without a bundle; report the single
        # located failure instead of nine derived ones.
        return out
    step("bundle_valid",
         lambda: _require(report.get("validation_errors") == [], report,
                          f"bundle validation errors: {report.get('validation_errors')}"))
    step("retrieval_replayed",
         lambda: _require(len(decisions) >= 40, report,
                          f"fixture replay returned {len(decisions)} decisions (<40)"))
    step("map_coordinates",
         lambda: [
             _require(isinstance(d.get("x"), (int, float))
                      and isinstance(d.get("y"), (int, float))
                      and d.get("cluster_id") is not None, report,
                      f"decision without map coordinates/cluster: {d.get('decision_id')}")
             for d in decisions
         ])
    step("answer_ready",
         lambda: (_require(answer.get("status") == "ready", report,
                           "answer status not ready"),
                  _require(bool(str(answer.get("prose") or "").strip()), report,
                           "answer prose empty"),
                  _require(bool(answer.get("method")), report, "answer method empty")))
    def _citations() -> None:
        cited = set(answer.get("cited_decision_ids") or [])
        ids = {d.get("decision_id") for d in decisions}
        _require(bool(cited), report, "answer cites nothing")
        _require(cited <= ids, report,
                 f"cited ids outside the bundle: {sorted(cited - ids)}")
    step("citations_in_bundle", _citations)
    step("adversarial_recorded",
         lambda: (_require(bool(adv.get("method")), report, "adversarial method empty"),
                  _require(adv.get("error") in (None, ""), report,
                           f"adversarial error: {adv.get('error')}")))
    step("counter_rows_keep_evidence_rule", _counter_evidence_invariant(final))
    return out


def _counter_evidence_invariant(final: dict):
    """The one live counter policy that is mode-independent: a surfaced
    counter row must carry verified evidence. Fixture runs must uphold it too,
    because the render/evidence contract is bundle-level, not model-level."""
    def check() -> None:
        for d in final.get("decisions") or []:
            if d.get("counter_status") in {"candidate-limiting", "candidate-contrary",
                                           "candidate-distinguishing", "candidate-exception"}:
                _require(d.get("counter_evidence_verified") is True, report_proxy(d),
                         f"surfaced counter lacks verified evidence: {d.get('decision_id')}")
    return check


def _repo_relative(path: Path) -> str:
    """Repo-relative path when inside the checkout, absolute otherwise
    (``--out`` may legitimately point at a temp/scratch directory)."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def report_proxy(decision: dict) -> dict:
    """Minimal report-shaped payload for a single-row GateFailure message."""
    return {"decision_id": decision.get("decision_id")}


def evaluate(slug: str, report: dict) -> list[dict]:
    """Run all gates, returning an ordered list of per-gate outcomes."""
    results: list[dict] = []

    def step(name: str, fn) -> None:
        try:
            fn()
            results.append({"gate": name, "passed": True, "detail": ""})
        except GateFailure as exc:
            results.append({"gate": name, "passed": False, "detail": str(exc)})

    if str(report.get("mode") or "live") != "live":
        # Fixture mode = offline wiring check (see fixture_wiring_gates).
        # Live-only structural/truth gates are never evaluated here; the live
        # path below is byte-for-byte what the durable workflow gets.
        results.extend(fixture_wiring_gates(report))
        if slug == "business-judgment-rule":
            # Audit D1 (cycle 39014141628): this branch used to emit the
            # FROZEN gate name `recall::citation_controlling_authority` with
            # passed=true and a 'not applicable' detail — a fabricated green
            # on a gate that was never evaluated, pinned by two tests.  The
            # contract now records the non-evaluation as a wiring::* marker:
            # the frozen gate name is absent from fixture output entirely
            # and the summary carries frozen_gates_evaluated: [] (main()).
            # No frozen gate is weakened: the live path below is unchanged.
            results.append({"gate": "wiring::frozen_recall_gate_not_evaluated",
                            "passed": True,
                            "detail": "not evaluated: fixture mode "
                                      "(frozen recall leg is live-only; "
                                      "wiring check only, never a "
                                      "frozen-gate pass)"})
        return results

    step("structural", lambda: structural_gates(report))
    if results[-1]["passed"]:
        step(f"truth::{slug}", lambda: truth_gates(slug, report))
    else:
        results.append({"gate": f"truth::{slug}", "passed": False,
                        "detail": "skipped: structural gates failed"})
    if slug == "business-judgment-rule":
        truth_ok = results[-1]["passed"] and results[-1]["gate"] == f"truth::{slug}"
        if not truth_ok:
            results.append({"gate": "recall::citation_controlling_authority",
                            "passed": False,
                            "detail": "skipped: truth gate failed"})
        else:
            step("recall::citation_controlling_authority",
                 lambda: frozen_recall_gate(slug, report))
    return results


#: Exact list the durable reality-check workflow writes into
#: ``paths.DEFAULT_FREE_MODELS`` after the seam runs (workflow lines 63-67).
#: Used by ``--workflow-override`` to reproduce the durable gate's model-list
#: condition locally, so a green local run is evidence the durable gate is green.
WORKFLOW_MODEL_OVERRIDE = [
    "opencode/nemotron-3-ultra-free",
    "opencode/nemotron-3.5-lightning-free",
    "opencode/space-bunny-free",
    "opencode/mimo-v2.6-flash-free",
]


def run_leg(slug: str, mode: str, top_n: int, evidence_count: int, max_cites: int,
            workflow_override: bool = False) -> dict:
    from query import enrich_query_bundle, run_query_initial
    from query.bundle import validate_bundle

    question = LEGS[slug]
    fixture_generation = mode == "fixture"
    retrieval_mode = "fixture" if fixture_generation else "live"

    if workflow_override:
        # Reproduce the durable workflow's post-seam model-list override.
        # The seam's call-time dead-model filter must make this harmless.
        from generative_audit import paths
        paths.DEFAULT_FREE_MODELS[:] = list(WORKFLOW_MODEL_OVERRIDE)

    t0 = time.time()
    initial = run_query_initial(question, top_n=top_n, retrieval_mode=retrieval_mode)
    map_seconds = round(time.time() - t0, 3)
    final = enrich_query_bundle(
        initial,
        retrieval_mode=retrieval_mode,
        evidence_count=evidence_count,
        max_cites=max_cites,
        fixture_generation=fixture_generation,
    )
    total_seconds = round(time.time() - t0, 3)

    answer = final.get("answer", {})
    ga = final.get("provenance", {}).get("generative_audit", {}) or {}
    adv = ga.get("adversarial") or {}
    cited = set(answer.get("cited_decision_ids") or [])
    counters = [
        d for d in final["decisions"]
        if d.get("counter_status") in {"candidate-limiting", "candidate-contrary",
                                       "candidate-distinguishing", "candidate-exception"}
    ]

    report: dict[str, Any] = {
        "slug": slug,
        "mode": mode,
        "question": question,
        "workflow_override": workflow_override,
        "map_seconds": map_seconds,
        "total_seconds": total_seconds,
        "validation_errors": validate_bundle(final),
        "decision_count": len(final["decisions"]),
        "cluster_count": len(final["clusters"]),
        "answer_status": answer.get("status"),
        "answer_method": answer.get("method"),
        "answer_model": answer.get("model"),
        "answer_prose": answer.get("prose"),
        "cited_decision_ids": sorted(cited),
        "counter_count": len(counters),
        "provider_error": ga.get("provider_error"),
        "adversarial_method": adv.get("method"),
        "adversarial_model": adv.get("model"),
        "adversarial_error": adv.get("error"),
        "adversarial_attempts": adv.get("attempts"),
        "adversarial_prompt_decisions": adv.get("prompt_decisions"),
        "adversarial_bundle_decisions": adv.get("bundle_decisions"),
        "product_audit_seam": (final.get("provenance") or {}).get("product_audit_seam"),
        "answer_coverage": (final.get("provenance") or {}).get("answer_coverage"),
        "bundle": final,
    }
    if slug == "business-judgment-rule":
        # Durability diagnostic for the frozen leg: the failure chain is
        # retrieved -> spliced into the evidence head -> cited by the model.
        # Recording each stage separately turns a red run into a located repair
        # instead of a coin flip.
        by_id = {d.get("decision_id"): d for d in final.get("decisions", [])}
        moved = (((final.get("provenance") or {}).get("product_rerank") or {})
                 .get("remote_head_recall") or {}).get("moved")
        report["frozen_bjr_recall"] = {
            "frozen_authorities": sorted(BJR_DIRECT_TF_FROZEN),
            "retrieved": sorted(a for a in BJR_DIRECT_TF_FROZEN if a in by_id),
            "in_evidence_head": sorted(
                a for a in BJR_DIRECT_TF_FROZEN
                if a in by_id and (by_id[a].get("rank") or 10 ** 9) <= 10
            ),
            "cited": sorted(cited & BJR_DIRECT_TF_FROZEN),
            "remote_head_recall_moved": moved,
        }
    return report


def strip_bundle(report: dict) -> dict:
    """Drop the heavy decision payload; keep everything a reviewer needs."""
    out = {k: v for k, v in report.items() if k != "bundle"}
    final = report.get("bundle") or {}
    out["cited_decisions"] = [
        {
            "decision_id": d.get("decision_id"),
            "rank": d.get("rank"),
            "citation": d.get("citation"),
            "language": d.get("language"),
            "counter_status": d.get("counter_status"),
            "canonical_url": d.get("canonical_url"),
            "snippet": str(d.get("snippet") or "")[:400],
        }
        for d in final.get("decisions", [])
        if d.get("decision_id") in set(report.get("cited_decision_ids") or [])
    ]
    out["clusters"] = [
        {"cluster_id": c.get("cluster_id"), "label": c.get("label"), "size": c.get("size")}
        for c in final.get("clusters", [])
    ]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", default="rent-default",
                        help="leg name or 'all' (default: rent-default)")
    parser.add_argument("--mode", choices=("live", "fixture"), default="live")
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--evidence-count", type=int, default=10)
    parser.add_argument("--max-cites", type=int, default=8)
    parser.add_argument("--workflow-override", action="store_true",
                        help="reproduce the durable workflow's post-seam model-list "
                             "override (dead models first) before running the leg")
    parser.add_argument("--out", default=str(REPO_ROOT / "results" / "product" / "reality_check"))
    parser.add_argument("--list", action="store_true", help="print frozen legs and exit")
    args = parser.parse_args(argv)

    if args.list:
        for slug, question in LEGS.items():
            print(f"{slug}\t{question}")
        return 0

    slugs = list(LEGS) if args.slug == "all" else [args.slug]
    unknown = [s for s in slugs if s not in LEGS]
    if unknown:
        print(f"unknown slug(s): {unknown}; known: {list(LEGS)}", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": args.mode,
        "local_evidence_only": True,
        "live_gates_evaluated": args.mode == "live",
        "durable_run_required": "product-reality-check.yml on lab/product with [reality-check]",
        "legs": [],
    }
    if args.mode != "live":
        summary["claim_ceiling"] = (
            "OFFLINE WIRING EVIDENCE ONLY: fixture runs replay cached "
            "OpenCaseLaw envelopes with no network and emit wiring::* gates "
            "(retrieval replay, bundle validity, map coordinates, citations, "
            "adversarial recording, counter-evidence invariant). The frozen "
            "structural/truth/recall gates are NOT evaluated in fixture mode "
            "and no fixture result may be cited as a green frozen leg."
        )
        # Audit D1 (cycle 39014141628): make the non-evaluation machine-
        # readable — the frozen gate names that fixture mode did NOT run.
        summary["frozen_gates_evaluated"] = []
    exit_code = 0
    for slug in slugs:
        print(f"== reality leg: {slug} (mode={args.mode}) ==", flush=True)
        try:
            report = run_leg(slug, args.mode, args.top_n, args.evidence_count, args.max_cites,
                             workflow_override=args.workflow_override)
            gates = evaluate(slug, report)
        except Exception as exc:  # keep negative results as evidence
            report = {"slug": slug, "mode": args.mode, "question": LEGS[slug],
                      "fatal_error": f"{type(exc).__name__}: {exc}"}
            gates = [{"gate": "run", "passed": False, "detail": report["fatal_error"]}]
        passed = all(g["passed"] for g in gates)
        exit_code = exit_code or (0 if passed else 1)
        slim = strip_bundle(report) if "bundle" in report else dict(report)
        slim["gates"] = gates
        slim["leg_passed"] = passed
        slim["evidence_tier"] = "LOCAL_NOT_DURABLE"
        path = out_dir / f"{slug}_{args.mode}_{stamp}.json"
        path.write_text(json.dumps(slim, ensure_ascii=False, indent=2, sort_keys=True),
                        encoding="utf-8")
        summary["legs"].append({"slug": slug, "passed": passed, "gates": gates,
                                "report": _repo_relative(path)})
        for g in gates:
            mark = "PASS" if g["passed"] else "FAIL"
            print(f"   [{mark}] {g['gate']}" + (f" — {g['detail']}" if g["detail"] else ""),
                  flush=True)

    summary_path = out_dir / f"summary_{args.mode}_{stamp}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
                            encoding="utf-8")
    print(f"\nwrote {_repo_relative(summary_path)}")
    print(f"overall: {'PASS' if exit_code == 0 else 'FAIL'} (local evidence; "
          f"a durable Actions run is still required)")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
