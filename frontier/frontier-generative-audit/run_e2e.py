#!/usr/bin/env python3
"""End-to-end orchestrator for the generative-audit capability.

Examples
--------
Deterministic, offline (frozen test path)::

    python3 frontier/frontier-generative-audit/run_e2e.py --fixture \\
        --out results/frontier/frontier-generative-audit/cached_example_fixture.json

Real free model via OpenCode CLI (no owner-provisioned API cost)::

    python3 frontier/frontier-generative-audit/run_e2e.py --real --model opencode/mimo-v2.6-flash-free \\
        --out results/frontier/frontier-generative-audit/cached_example_real_model.json

Local OpenAI-compatible server (Ollama etc.)::

    LEX_GENAUDIT_BACKEND=openai LEX_OPENAI_BASE_URL=http://127.0.0.1:11434/v1 \\
        python3 frontier/frontier-generative-audit/run_e2e.py --real --model llama3.1
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # canonical in-scope package wins over legacy root copy

from generative_audit.adversarial import AdversarialPass  # noqa: E402
from generative_audit.integration_contract import (  # noqa: E402
    package_answer,
    apply_to_product_bundle,
)
from generative_audit.provider import Provider  # noqa: E402
from generative_audit.source_packing import from_product_bundle  # noqa: E402

DEFAULT_BUNDLE = (
    HERE.parent.parent
    / "tests" / "frontier" / "frontier-generative-audit" / "fixtures" / "sample_bundle.json"
)


def _load_bundle(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "query" not in data:
        raise SystemExit(f"bundle must be a JSON object with a 'query' key: {path}")
    # Accept both the product v1.0 bundle and the minimal {query, decisions} shape.
    data.setdefault("decisions", [])
    if not data["decisions"] and data.get("decision_ids"):
        data["decisions"] = [
            {"decision_id": did, "snippet": ""} for did in data["decision_ids"]
        ]
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE, help="query_result_bundle JSON")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--fixture", action="store_true", help="deterministic offline mode")
    mode.add_argument("--real", action="store_true", help="use a real free model backend")
    ap.add_argument("--model", default=None, help="model id override (free OpenCode or local)")
    ap.add_argument("--answer", default=None, help="fixture answer text (fixture mode)")
    ap.add_argument("--out", type=Path, default=None, help="write cached example JSON here")
    ap.add_argument("--attestation", action="store_true", help="attempt OpenCaseLaw attestation")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args(argv)

    product_bundle = _load_bundle(args.bundle)
    bundle = from_product_bundle(product_bundle)
    fixture = not args.real

    provider = Provider(
        model=args.model,
        fixture_mode=fixture,
        fixture_answer=args.answer,
        fixture_cited_ids=bundle.decision_ids[:2],
        use_attestation=True if args.attestation else False,
        timeout=args.timeout,
    )

    t0 = time.time()
    result = provider.generate(bundle)
    adv = AdversarialPass(
        bundle=bundle,
        answer=result.answer,
        model=args.model,
        fixture_mode=fixture,
        fixture_findings=[] if fixture else None,
        timeout=args.timeout,
    )
    findings, adv_info = adv.run_with_info()
    package = package_answer(result, findings, bundle)
    audited = apply_to_product_bundle(
        product_bundle, package, findings,
        provenance={
            "model": result.model_used,
            "provider_error": result.error,
            "citation_validation": {
                k: result.validation_report.get(k)
                for k in ("mode", "hallucinated_ids", "verified_ids", "unverified_ids")
            },
            "adversarial": adv_info,
            "latency_seconds": round(time.time() - t0, 3),
            "mode": "fixture" if fixture else "real-model",
        },
    )

    cached = {
        "query": bundle.query,
        "mode": "fixture" if fixture else "real-model",
        "model_used": result.model_used,
        "provider_error": result.error,
        "answer": package.answer,
        "cited_decision_ids": package.cited_decision_ids,
        "redacted_citation_ids": result.redacted_citation_ids,
        "citation_validation": result.validation_report,
        "adversarial_findings": [f.to_dict() for f in findings],
        "adversarial_info": adv_info,
        **package.to_dict(),
        "status_summary": package.summary(),
        "audited_product_bundle": audited,
        "provenance": audited.get("provenance", {}),
    }
    # package.to_dict() already carries answer/cited/status_summary; keep one copy
    cached.pop("answer", None)
    cached["answer"] = package.answer
    cached["cited_decision_ids"] = list(package.cited_decision_ids)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(cached, fh, indent=2, ensure_ascii=False)
        print(f"wrote {args.out}")

    summary = {
        "mode": cached["mode"],
        "model_used": cached["model_used"],
        "provider_error": cached["provider_error"],
        "cited": cached["cited_decision_ids"],
        "redacted": cached["redacted_citation_ids"],
        "findings": [(f.decision_id, f.reason) for f in findings],
        "status_summary": package.summary(),
        "validation_mode": result.validation_report.get("mode"),
    }
    print(json.dumps(summary, indent=2))
    return 0 if result.error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
