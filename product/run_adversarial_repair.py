#!/usr/bin/env python3
"""Re-run the adversarial RETRIEVAL pass with the audit-repaired classifier.

Why this exists (cycle 38831241913, repair of 38828034436 audit D1-D4)
---------------------------------------------------------------------
The audit required: fix the probe vocabulary (D1), fix the labelling lexicon
(D2), then **re-run live, re-score with the accepted mount, and disclose the
yield drop** without touching any threshold.

A full pipeline re-run would re-generate the answer with a model and re-fetch
the initial 135/150/97-decision pools, which are already frozen claim-bearing
artifacts.  This tool instead:

1. loads the three shipped live bundles of run 38828034436;
2. strips exactly the rows that bundle's own ``adversarial_channel`` field
   marks as products of the *old* adversarial pass, restoring the frozen
   initial population byte-for-byte (the initial pass is the baseline and is
   not re-measured);
3. re-plans the probes from the same query + same answer prose with the FIXED
   planner (now DE+FR+IT interleaved) and re-fetches them live through the
   accepted adapter;
4. re-applies the pass with the FIXED classifier (topic-gated, disposal- and
   boilerplate-guarded, sentence-scoped markers);
5. scores both the new bundles and an offline relabelling of the OLD counter
   rows with the ACCEPTED frontier metric functions (exit 3 if the mount is
   absent — a self-scored metric is the evidence this factory forbids);
6. writes everything under results/product/adversarial_retrieval/<run_id>/.

The superseded artifacts of 38828034436 are never opened for writing.

Usage::

    python product/run_adversarial_repair.py --run-id 38831241913 \
        --source-dir results/product/adversarial_retrieval/38828034436

Exit codes: 0 ok, 3 accepted mount missing, 4 source bundle missing/invalid.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.adversarial_independence_check import score as accepted_score  # noqa: E402
from product.query.adversarial_retrieval import (  # noqa: E402
    apply_adversarial_pass,
    bundle_topic_terms,
    classify_against_intent,
    fetch_adversarial_candidates,
    plan_adversarial_queries,
)
from product.query.bundle import validate_bundle  # noqa: E402

LANGS = ("de", "fr", "it")
#: The four affirmatively inverted rows named by the audit, per language of the
#: bundle they appeared in.  Tracked explicitly so the repair's effect on them
#: is measured, not asserted.
AUDIT_INVERTED_IDS = (
    "bge_136 III 190",   # FR — "nicht entgegen" affirms the landlord may terminate
    "bge_115 II 78",     # FR — recours rejeté, judgment confirmed
    "bge_111 II 384",    # IT — same French disposal sentence
    "bge_123 III 124",   # IT — Berufung abgewiesen
)


def _strip_adversarial_rows(bundle: dict) -> tuple[dict, list[dict]]:
    """Restore the frozen initial population; return (initial_bundle, old_rows)."""
    initial = copy.deepcopy(bundle)
    old_rows = [d for d in initial.get("decisions") or [] if d.get("adversarial_channel")]
    initial["decisions"] = [d for d in initial.get("decisions") or []
                            if not d.get("adversarial_channel")]
    prov = initial.setdefault("provenance", {})
    prov.pop("adversarial_retrieval", None)
    return initial, old_rows


def _offline_relabel(old_rows: list[dict], topic_terms: list[str]) -> list[dict]:
    """Re-classify the OLD counter rows with the FIXED classifier (no network)."""
    out = []
    for row in old_rows:
        text = str(row.get("full_text") or "") or str(row.get("regeste") or "")
        intent = str(row.get("adversarial_intent") or "exception")
        new_status, new_evidence, new_markers = classify_against_intent(
            text, intent, topic_terms=topic_terms)
        out.append({
            "decision_id": row.get("decision_id"),
            "intent": intent,
            "old_status": row.get("counter_status"),
            "new_status": new_status or "none",
            "old_markers": row.get("counter_markers") or [],
            "new_markers": new_markers,
            "changed": (row.get("counter_status") or "none") != (new_status or "none"),
            "text_source": "full_text" if row.get("full_text") else "regeste",
        })
    return out


def run_lang(lang: str, source_dir: Path, out_dir: Path, *, mode: str) -> dict:
    src = source_dir / f"bundle_{lang}.json"
    if not src.is_file():
        print(f"source bundle missing: {src}", file=sys.stderr)
        raise SystemExit(4)
    shipped = json.loads(src.read_text(encoding="utf-8"))
    initial, old_rows = _strip_adversarial_rows(shipped)
    errors = validate_bundle(initial)
    if errors:
        print(f"{lang}: stripped initial bundle invalid: {errors}", file=sys.stderr)
        raise SystemExit(4)

    query = str(shipped.get("query") or "")
    answer_prose = str((shipped.get("answer") or {}).get("prose") or "")
    plan = plan_adversarial_queries(query, answer_prose)
    # D1 guard, checked on the live plan that is about to be issued:
    for probe in plan:
        langs = set(probe.get("intent_term_languages") or ())
        if langs != {"de", "fr", "it"}:
            print(f"{lang}: probe {probe['intent']} lacks full DE+FR+IT coverage: {langs}",
                  file=sys.stderr)
            raise SystemExit(4)

    exclude_ids = {str(d.get("decision_id")) for d in initial["decisions"]}
    exclude_identities = set()
    for d in initial["decisions"]:
        docket = str(d.get("docket_number") or "").strip()
        if docket:
            import re
            exclude_identities.add(
                (str(d.get("court") or "").strip().lower(),
                 re.sub(r"[^a-z0-9]", "", docket.lower())))

    t0 = time.time()
    fetched = fetch_adversarial_candidates(
        query, plan, mode=mode, exclude_ids=exclude_ids,
        exclude_identities=exclude_identities, max_new=40, hydrate_top=12)
    fetch_s = time.time() - t0
    t1 = time.time()
    out_bundle = apply_adversarial_pass(
        initial, list(fetched.get("candidates") or []), fetched.get("provenance"))
    apply_s = time.time() - t1
    out_bundle.setdefault("provenance", {})["adversarial_retrieval"]["pass_seconds"] = round(
        fetched["provenance"].get("seconds") or fetch_s, 3)
    val_errors = validate_bundle(out_bundle)
    if val_errors:
        print(f"{lang}: repaired bundle invalid: {val_errors}", file=sys.stderr)
        raise SystemExit(4)

    scored = accepted_score(out_bundle)   # exits SystemExit(3) if mount missing
    topic_terms = bundle_topic_terms(initial)
    relabel = _offline_relabel(old_rows, topic_terms)

    new_adv_rows = [d for d in out_bundle["decisions"] if d.get("adversarial_channel")]
    new_counter = [d for d in new_adv_rows
                   if str(d.get("counter_status")) not in {"none", "unclassified", ""}]
    old_counter = [r for r in old_rows
                   if str(r.get("counter_status")) not in {"none", "unclassified", ""}]

    inverted_track = []
    for inv in AUDIT_INVERTED_IDS:
        old_hit = next((r for r in relabel if inv in str(r.get("decision_id"))), None)
        new_hit = next((d for d in new_adv_rows if inv in str(d.get("decision_id"))), None)
        inverted_track.append({
            "decision_id": inv,
            "in_old_population": old_hit is not None,
            "old_relabelled_status": (old_hit or {}).get("new_status"),
            "re_retrieved_now": new_hit is not None,
            "new_status_now": (new_hit or {}).get("counter_status") if new_hit else None,
        })

    artifact = {
        "lang": lang,
        "query": query,
        "source_bundle": str(src),
        "initial_decisions": len(initial["decisions"]),
        "old_adversarial_rows": len(old_rows),
        "old_counter_rows": len(old_counter),
        "probes": [{k: p.get(k) for k in ("intent", "query", "intent_term_languages")}
                   for p in plan],
        "new_adversarial_rows": len(new_adv_rows),
        "new_counter_rows": len(new_counter),
        "counter_yield_drop_abs": len(old_counter) - len(new_counter),
        "offline_relabel_old_rows": relabel,
        "inverted_audit_rows_tracked": inverted_track,
        "fetch_s": round(fetch_s, 3),
        "apply_s": round(apply_s, 4),
        "request_summary": fetched["provenance"].get("request_summary"),
        "failures": fetched["provenance"].get("failures"),
        "metrics": scored["metrics"],
        "verdict": scored["verdict"],
        "topic_terms": topic_terms,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"bundle_{lang}_repaired.json").write_text(
        json.dumps(out_bundle, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / f"score_{lang}_repaired.json").write_text(
        json.dumps(scored, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (out_dir / f"relabel_{lang}_old_rows.json").write_text(
        json.dumps(relabel, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return artifact


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--source-dir",
                    default="results/product/adversarial_retrieval/38828034436")
    ap.add_argument("--mode", default="live", choices=("live", "refresh", "offline"))
    args = ap.parse_args(argv)
    source_dir = Path(args.source_dir)
    if not source_dir.is_absolute():
        source_dir = REPO_ROOT / source_dir
    out_dir = REPO_ROOT / "results" / "product" / "adversarial_retrieval" / args.run_id
    started = time.time()
    artifacts = [run_lang(lang, source_dir, out_dir, mode=args.mode) for lang in LANGS]
    consolidated = {
        "cycle_run": str(args.run_id),
        "repair_of": 38828034436,
        "repair_contract": "adversarial_retrieval/2 (D1 DE+FR+IT probes, D2 guarded labelling, D4 vacuous-pass)",
        "mode": args.mode,
        "source_dir": str(source_dir),
        "scored_with": {
            "team": "frontier-adversarial-discoverability",
            "note": "accepted metric functions imported as a library; nothing re-implemented",
        },
        "seconds": round(time.time() - started, 3),
        "bundles": {a["lang"]: a for a in artifacts},
    }
    (out_dir / "MEASUREMENT.json").write_text(
        json.dumps(consolidated, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    for a in artifacts:
        print(json.dumps({
            "lang": a["lang"],
            "initial": a["initial_decisions"],
            "old_rows": a["old_adversarial_rows"],
            "old_counter": a["old_counter_rows"],
            "new_rows": a["new_adversarial_rows"],
            "new_counter": a["new_counter_rows"],
            "verdict": a["verdict"]["retrieval_independence"],
            "metrics": {k: v["verdict"] for k, v in a["metrics"].items()},
        }, ensure_ascii=False))
    print(f"artifacts: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
