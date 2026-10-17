#!/usr/bin/env python3
"""Rebuild the served-packet per-leg summary from a product bundle, offline.

Why this module exists
----------------------
Run 38984833779 rebuilt the served packet live and committed the per-leg summary

    results/product/CYCLE_38984833779/leg_business-judgment-rule_live.json

with ``schema: "product/rebuild-served-packet/1"``.  That artifact carries the
lane question's headline obligation-(5) claim:

    "recall_gate_recall_controlling_authority": {"passes": true, "n": 3, "of": 5}

i.e. that a live run generated an answer citing **3 of the 5** frozen direct-TF
BJR authorities, against an accepted-base baseline of 0/5.  The producer of that
schema, however, was **never committed**: no file in the tree emits
``rebuild-served-packet`` / ``recall_gate_recall_controlling_authority``.  An
independent auditor handed the snapshot therefore cannot recompute the claim the
report rests on, and the audit burns its whole work quantum reverse-engineering
an absent tool (run 38988477028's audit job died rc 78
``LEX_WORK_QUANTUM_EXPIRED``; the producer itself had succeeded).

This module closes that gap.  It is the committed, product-owned producer for
``product/rebuild-served-packet/1``.  Given a committed bundle it recomputes the
summary with:

* no network, no provider, no LLM, no paid dependency;
* the product's OWN admissibility and admission code reused verbatim --
  ``product/query/gate_admissibility.py`` (``verify_bundle`` / ``cluster_shares``)
  and ``product/packet_admission.py`` (``packet_admission``) -- so this tool can
  never disagree with the code that decides a packet;
* the frozen authority table reused from ``product/evidence_pack_recall.py``, so
  the recall target is defined in exactly one place.

It never asserts a gate result it did not compute: ``recall_gate`` reports the
measured ``n``/``of`` and a single documented bar (``>= 1``), and the baseline is
carried as a literal from the accepted direction.

Usage
-----
    # rebuild from a committed bundle
    python product/rebuild_served_packet.py \
        --bundle results/product/CYCLE_38984833779/bundle_business-judgment-rule_live.json \
        --slug business-judgment-rule --run-id 38984833779 --out /tmp/leg.json

    # prove the rebuild reproduces a reference artifact field-for-field
    python product/rebuild_served_packet.py ... --reference <leg.json> --check

Exit codes: 0 ok; 1 a ``--check`` comparison failed; 2 bad arguments.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from reality_check import LEGS  # noqa: E402  (frozen question strings)
from evidence_pack_recall import FROZEN_AUTHORITIES  # noqa: E402

SCHEMA = "product/rebuild-served-packet/1"

#: One cluster holding at least this share of the served map means the "cluster"
#: is the map rendering itself, not structure.  FROZEN (matches
#: ``gate_admissibility.MEGA_CLUSTER_SHARE``); never changed to fire a disclosure.
MEGA_CLUSTER_SHARE = 0.5

#: The recall bar the lane question states: the answer must cite at least one of
#: the frozen direct authorities.  The accepted-base baseline is a literal from
#: direction v50 (accepted executions cited 0 frozen BJR authorities).
RECALL_BAR = 1
ACCEPTED_BASE_BASELINE = {"business-judgment-rule": "0/5"}

#: Fields that are deterministic functions of the bundle and are therefore
#: asserted field-for-field by a ``--check`` / test comparison.  Timing and
#: ``built_at`` are excluded: they are wall-clock measurements of the run that
#: produced the bundle, not properties of the bundle's content.  ``bundle_summary``
#: is compared key-by-key because one of its keys (``n_counter``) is a known,
#: disclosed divergence -- see :data:`COUNTER_COUNT_NOTE`.
CHECK_FIELDS = (
    "schema",
    "run_id",
    "question_slug",
    "retrieval_mode",
    "fixture_mode",
    "validation_errors",
    "bundle_summary",
    "answer_status",
    "answer_model",
    "cited_decision_ids",
    "frozen_bjr_authorities_cited",
    "n_frozen_cited",
    "recall_gate_recall_controlling_authority",
    "head_recall_moved",
    "cluster_shares_size_based",
    "largest_cluster_size_share",
    "mega_cluster_disclosure",
    "admissibility",
    "packet_admission",
)

#: The one key of ``bundle_summary`` that the reference artifact got wrong and
#: this tool therefore does not reproduce verbatim.  See ``counter_count`` in the
#: emitted summary for the reconciled values.
KNOWN_BUNDLE_SUMMARY_DIVERGENCE = "n_counter"

#: The one *environment-scoped* subfield of ``packet_admission``.  ``packet_admission()``
#: emits ``verdict_source`` as ``str(REPO_ROOT / "results/product/frontier_verdicts/...")``,
#: an absolute path, so two checkouts that rebuild the same committed bundle emit
#: two different strings for the same file (``/home/runner/work/LexMachina/...`` vs
#: ``/tmp/lex_team/...``).  Independent audit of cycle 38993348615 (gate=REVISE,
#: REQUIRED-1) established that this made the "19 deterministic fields" reproduction
#: claim checkout-scoped: ``--check`` exited 1 and 3 of 12 tests failed in the
#: producer workspace.
#:
#: Accepted repository standard (required fix D1 of cycle 38785927063): an
#: artifact-identity claim must be path-independent and verified at two checkout
#: paths, or state the dependence explicitly.  :func:`compare` therefore
#: canonicalises BOTH sides of a ``packet_admission`` comparison to the
#: repo-relative path below ``results/``.  The normalisation strips ONLY the
#: checkout prefix -- the verdict file name, team, run, bars and every other
#: subfield stay strictly compared, so a genuine verdict swap or content change
#: still fails.  Nothing outside ``compare`` is rewritten; ``build_summary`` keeps
#: reusing ``packet_admission()`` verbatim.
VERDICT_SOURCE_MARKER = "results/product/frontier_verdicts/"
_VERDICT_SOURCE_REL_RE = re.compile(
    r"^results/product/frontier_verdicts/[^/\\]+$"
)


def canonical_verdict_source(value: object) -> str:
    """Checkout-independent form of a ``packet_admission.verdict_source``.

    ``/home/runner/work/LexMachina/LexMachina/results/product/frontier_verdicts/X.json``
    and ``/tmp/lex_team/results/product/frontier_verdicts/X.json`` both canonicalise
    to ``results/product/frontier_verdicts/X.json``.  A value that does not end in a
    single ``results/product/frontier_verdicts/<file>`` tail is returned unchanged, so
    this can never launder a different file, a nested path or an arbitrary string.
    Idempotent.
    """
    text = str(value or "")
    idx = text.rfind(VERDICT_SOURCE_MARKER)
    if idx > 0:
        tail = text[idx:]
        if _VERDICT_SOURCE_REL_RE.match(tail):
            return tail
    return text


def _normalise_packet_admission_for_compare(value: object) -> object:
    """Copy ``packet_admission`` with only ``verdict_source`` canonicalised."""
    if isinstance(value, dict):
        out = dict(value)
        if "verdict_source" in out:
            out["verdict_source"] = canonical_verdict_source(out["verdict_source"])
        return out
    return value

COUNTER_COUNT_NOTE = (
    "This tool counts counter rows with the product's own definition, "
    "gate_admissibility.counter_ids() / NON_COUNTER_STATUSES (a row whose "
    "counter_status is in {'none','','cited','unclassified','supporting-candidate',"
    "'context'} is NOT a counter finding). The per-leg artifact "
    "results/product/CYCLE_38984833779/leg_business-judgment-rule_live.json "
    "recorded the WIDER counter_status != 'none' count, which counts the answer's "
    "own cited rows; that artifact therefore reported n_counter=4 while its own "
    "admissibility block correctly warned no_counter_authority (zero rows carry a "
    "counter-authority status). The reconciliation is published below rather than "
    "silently matched or silently changed."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _slug_from_query(bundle: dict) -> str | None:
    query = str(bundle.get("query") or "")
    for slug, question in LEGS.items():
        if query.strip() == question.strip():
            return slug
    return None


def _languages(decisions: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for d in decisions:
        lang = d.get("language")
        key = str(lang) if lang else "null"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _counter_count(bundle: dict) -> int:
    # Reuse the product's own definition of "counts as a counter row".
    from query.gate_admissibility import counter_ids

    return len(counter_ids(bundle))


def _counter_status_not_none(bundle: dict) -> int:
    """The wider, naive count the legacy artifact used (counter_status != 'none')."""
    n = 0
    for d in bundle.get("decisions") or []:
        if isinstance(d, dict) and str(d.get("counter_status") or "none") != "none":
            n += 1
    return n


def _recall_gate(slug: str, cited: list[str]) -> tuple[list[str], dict]:
    spec = FROZEN_AUTHORITIES.get(slug) or {}
    direct = [str(x) for x in spec.get("direct", [])]  # type: ignore[arg-type]
    cited_set = set(cited)
    frozen_cited = sorted(i for i in direct if i in cited_set)
    gate = {
        "passes": len(frozen_cited) >= RECALL_BAR,
        "n": len(frozen_cited),
        "of": len(direct),
    }
    if slug in ACCEPTED_BASE_BASELINE:
        gate["baseline_accepted_base"] = ACCEPTED_BASE_BASELINE[slug]
    return frozen_cited, gate


def _head_recall_moved(bundle: dict, slug: str) -> list[dict]:
    spec = FROZEN_AUTHORITIES.get(slug) or {}
    frozen = {str(x) for x in spec.get("direct", [])}  # type: ignore[arg-type]
    moved = (((bundle.get("provenance") or {})
              .get("product_rerank") or {})
             .get("remote_head_recall") or {})
    out = []
    for m in moved.get("moved") or []:
        did = m.get("decision_id")
        out.append({
            "decision_id": did,
            "rank": m.get("to_rank"),
            "frozen": did in frozen,
        })
    return out


def build_summary(bundle: dict, *, slug: str, run_id: str,
                  built_at: str | None = None) -> dict:
    """Recompute the served-packet per-leg summary from one bundle (offline)."""
    from query.bundle import validate_bundle
    from query.gate_admissibility import verify_bundle, cluster_shares
    from product.packet_admission import packet_admission

    if slug not in FROZEN_AUTHORITIES:
        raise SystemExit(f"unknown slug {slug!r}; expected one of "
                         f"{sorted(FROZEN_AUTHORITIES)}")

    provenance = bundle.get("provenance") or {}
    decisions = [d for d in (bundle.get("decisions") or []) if isinstance(d, dict)]
    clusters = [c for c in (bundle.get("clusters") or []) if isinstance(c, dict)]
    relations = [r for r in (bundle.get("relations") or []) if isinstance(r, dict)]
    answer = bundle.get("answer") or {}

    cited = sorted(str(x) for x in (answer.get("cited_decision_ids") or []))
    frozen_cited, recall_gate = _recall_gate(slug, cited)

    shares = cluster_shares(bundle)
    largest = max((float(c["size_share"]) for c in shares), default=0.0)

    verdict = verify_bundle(bundle)
    admissibility = {
        "admissible": bool(verdict.get("admissible")),
        "warning_count": int(verdict.get("warning_count") or 0),
        "findings": [
            {"code": f.get("code"), "severity": f.get("severity"),
             "detail": f.get("detail")}
            for f in (verdict.get("findings") or [])
        ],
    }

    timing = provenance.get("timing")
    latency_total = provenance.get("latency_seconds_total")
    latency_map = provenance.get("latency_seconds")

    summary = {
        "schema": SCHEMA,
        "run_id": str(run_id),
        "built_at": built_at or _utc_now(),
        "question_slug": slug,
        "retrieval_mode": provenance.get("mode"),
        "fixture_mode": bool(provenance.get("fixture_mode")),
        "geometry": provenance.get("geometry"),
        "map_seconds": round(float(latency_map), 3) if latency_map is not None else None,
        "total_seconds": (round(float(latency_total), 3)
                          if latency_total is not None else None),
        "timing": timing,
        "validation_errors": validate_bundle(bundle),
        "bundle_summary": {
            "n_decisions": len(decisions),
            "n_clusters": len(clusters),
            "n_relations": len(relations),
            "n_counter": _counter_count(bundle),
            "languages": _languages(decisions),
            "answer_citations": len(cited),
        },
        "counter_count": {
            "product_definition_n_counter": _counter_count(bundle),
            "legacy_artifact_definition_counter_status_not_none":
                _counter_status_not_none(bundle),
            "note": COUNTER_COUNT_NOTE,
        },
        "answer_status": answer.get("status"),
        "answer_model": answer.get("model"),
        "cited_decision_ids": cited,
        "frozen_bjr_authorities_cited": frozen_cited,
        "n_frozen_cited": len(frozen_cited),
        "recall_gate_recall_controlling_authority": recall_gate,
        "head_recall_moved": _head_recall_moved(bundle, slug),
        "cluster_shares_size_based": shares,
        "largest_cluster_size_share": largest,
        "mega_cluster_disclosure": {
            "fired": largest >= MEGA_CLUSTER_SHARE,
            "bar": MEGA_CLUSTER_SHARE,
            "largest_share": largest,
            "note": ("Size-based share computed from clusters[].size per the "
                     "accepted R2 reconciliation; MEGA_CLUSTER_SHARE unchanged "
                     "at 0.5."),
        },
        "admissibility": admissibility,
        "packet_admission": packet_admission(),
    }
    return summary


def compare(rebuilt: dict, reference: dict,
            fields: tuple[str, ...] = CHECK_FIELDS) -> list[str]:
    """Return human-readable differences on the deterministic fields.

    ``bundle_summary`` is compared key-by-key, excluding the single key
    :data:`KNOWN_BUNDLE_SUMMARY_DIVERGENCE` (``n_counter``), whose reconciled
    values and explanation travel in the rebuilt ``counter_count`` block.  A
    caller that wants to assert that divergence checks ``counter_count``
    directly, so it can never be an accident.

    ``packet_admission`` is compared with its single environment-scoped subfield
    ``verdict_source`` canonicalised on BOTH sides by
    :func:`canonical_verdict_source`, so reproduction does not depend on the
    directory that wrote the reference artifact.  Every other subfield (verdict
    team, run, accept commit, bars, blocked_by, serve recommendation) is compared
    strictly, and a changed verdict *file* still fails.
    """
    diffs: list[str] = []
    for field in fields:
        a, b = rebuilt.get(field), reference.get(field)
        if field == "bundle_summary":
            if isinstance(a, dict) and isinstance(b, dict):
                a = {k: v for k, v in a.items()
                     if k != KNOWN_BUNDLE_SUMMARY_DIVERGENCE}
                b = {k: v for k, v in b.items()
                     if k != KNOWN_BUNDLE_SUMMARY_DIVERGENCE}
        elif field == "packet_admission":
            a = _normalise_packet_admission_for_compare(a)
            b = _normalise_packet_admission_for_compare(b)
        if a != b:
            diffs.append(f"{field}:\n  rebuilt   = "
                         f"{json.dumps(a, ensure_ascii=False, sort_keys=True)}\n"
                         f"  reference = "
                         f"{json.dumps(b, ensure_ascii=False, sort_keys=True)}")
    return diffs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", type=Path, required=True,
                        help="product bundle json to rebuild from")
    parser.add_argument("--slug", default=None,
                        help="frozen leg slug (inferred from the bundle query if omitted)")
    parser.add_argument("--run-id", default="unknown")
    parser.add_argument("--built-at", default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--reference", type=Path, default=None,
                        help="committed leg summary to compare against")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if --reference differs on any deterministic field")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    slug = args.slug or _slug_from_query(bundle)
    if not slug:
        parser.error("could not infer --slug from the bundle query; pass it explicitly")

    summary = build_summary(bundle, slug=slug, run_id=args.run_id,
                            built_at=args.built_at)
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    if args.json:
        print(text)

    rc = 0
    if args.reference:
        reference = json.loads(args.reference.read_text(encoding="utf-8"))
        diffs = compare(summary, reference)
        if diffs:
            rc = 1
            print("DIFFERENCES against reference:", file=sys.stderr)
            for d in diffs:
                print(d, file=sys.stderr)
        else:
            print(f"OK: rebuild reproduces {args.reference} on "
                  f"{len(CHECK_FIELDS)} deterministic fields "
                  f"(path-independent: packet_admission.verdict_source "
                  f"canonicalised to its repo-relative form on both sides; "
                  f"every other subfield compared strictly)")
        ref_nc = (reference.get("bundle_summary") or {}).get("n_counter")
        new_nc = summary["bundle_summary"]["n_counter"]
        if ref_nc != new_nc:
            print(f"counter_count reconciliation: rebuilt n_counter={new_nc} "
                  f"(product counter_ids) vs reference n_counter={ref_nc} "
                  f"(counter_status != 'none'; counted the answer's cited rows). "
                  f"See the counter_count block.")
    elif not args.json:
        gate = summary["recall_gate_recall_controlling_authority"]
        print(f"{slug}: frozen cited {gate['n']}/{gate['of']} "
              f"(passes={gate['passes']}); admissible="
              f"{summary['admissibility']['admissible']}; "
              f"owner-session-ready="
              f"{summary['packet_admission'].get('ready_for_owner_session')}")
    return rc


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())
