"""Run-time admissibility of a query_result_bundle as human-gate material.

Why this module exists
----------------------
Direction v52 backlog item (3) asks for a *multi-query gate packet*: a small set
of real research tasks whose bundles are "re-verified for admissibility at run
time (never ship a frozen defective bundle)". A frozen bundle is exactly what
bit this lane twice - run 38759730609 committed a synthetic fixture bundle that
the report described as a cache replay, and run 38766812030's audit found 13% of
citation-channel rows carrying another decision's citation. Both defects were
invisible to a human until an independent check looked at the artifact.

So admissibility is a *function of the bundle in hand*, recomputed whenever the
bundle is produced and again whenever the owner ceremony is about to use it. No
verdict is cached, and no packet may ship a bundle this module has not just
passed.

What it checks
--------------
Reused from the existing product code rather than reimplemented:

* :func:`product.query.bundle.validate_bundle` - the bundle contract;
* :func:`product.replay_bundle.inspect_bundle` - synthetic ids/labels, required
  fields, orphan cluster members, dangling relations, citation forensics
  (duplicates / seed refs / pending-shell identity), field coverage and the
  path-independent ``content_sha256``;
* the source-host allowlist already used by the claim path.

Added here (each one is a claim this lane has already been audited for making):

``source_url_null_on_hydrated_row`` (blocking)
    required_fixes[1] of run 38766812030 recorded 30 null ``source_url`` values
    and attributed them to OpenCaseLaw omitting URLs. That causal claim is
    wrong: the nulls are un-hydrated citation-channel shells that have not been
    fetched individually yet. A null on a *hydrated* row would be a different
    (and real) defect, so this check makes the corrected causal claim
    falsifiable instead of merely prose.

``answer_not_grounded`` (blocking)
    the answer must exist and every cited id must be a decision on the map.

``map_too_small`` / ``map_too_large`` (blocking / warning)
    the Master Prompt's 100-300 decision map window; below it there is no
    comparative research task, far above it the map is not the tractable result
    set the gate is about.

``no_counter_authority`` (warning)
    gate question 3 ("did the map increase confidence that contrary authority
    had not been hidden?") cannot be answered on a bundle with zero counter
    rows. That is a warning, not a refusal: the jurist's own answer to a
    unanswerable question is itself evidence, and the packet discloses the yield
    so nobody is misled about what they are being asked.

``map_is_one_mega_cluster`` / ``no_relations_on_map`` (warning)
    the two map-semantics weaknesses the director observed on accepted bundles
    (an 186/227 mega-cluster and zero relation edges). frontier-map-semantics
    owns the accepted measurement of these; until it reports, the packet
    *discloses* the numbers per question instead of claiming anything about map
    quality. They are warnings, never blocking claims.

Severity contract: ``blocking`` findings mean the bundle must not be shown to
the owner as gate material. ``warning`` findings are disclosed on the owner
card so the jurist is never asked a question the artifact cannot support.

Usage
-----
    python -m product.query.gate_admissibility path/to/bundle.json
    from product.query.gate_admissibility import verify_bundle
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # product-owned import shim, matches query/*
    sys.path.insert(0, str(REPO_ROOT))

from product.query.pipeline import CITE_CHANNELS  # noqa: E402
from product.replay_bundle import inspect_bundle  # noqa: E402

SCHEMA = "product-gate-admissibility/1"

#: The public source the product is allowed to cite. Anything else on a decision
#: row is a provenance defect, not a formatting preference.
ACCEPTED_SOURCE_HOSTS = frozenset({"mcp.opencaselaw.ch", "opencaselaw.ch", "www.opencaselaw.ch"})

#: Master Prompt, "query-specific interactive map over roughly 100-300
#: decisions". Below the floor there is no comparative research task; above the
#: ceiling the result set is no longer the tractable one the gate is about.
MIN_MAP_DECISIONS = 100
MAX_MAP_DECISIONS = 400

#: A share of the bundle at or above this in ONE cluster means the "cluster"
#: carries no information for that query: it is the map rendering itself, not
#: structure. Disclosed per question (advisory, never a claim about map quality).
MEGA_CLUSTER_SHARE = 0.5

#: Statuses that mean "this row is not a counter-authority finding". Kept in step
#: with ``isCounter()`` in product/static/query.html, so the packet's disclosed
#: counter yield is exactly the set the researcher sees ringed on the map.
NON_COUNTER_STATUSES = frozenset(
    {"none", "", None, "cited", "unclassified", "supporting-candidate", "context"}
)

#: Languages other than the row's own are still useful context on a map, so this
#: is a signal, not a defect: a question asked in German that returns no German
#: rows is worth disclosing to the jurist before they spend a sitting on it.
MIN_QUESTION_LANGUAGE_SHARE = 0.25


def _is_citation_shell(decision: dict) -> bool:
    """True for an un-hydrated citation-channel row.

    Same predicate the product's own bundle assembly uses
    (``product/query/pipeline.py::_citation_shell``): the row came from a
    citation-expansion channel and has not been fetched individually, so it has
    no detail payload of its own.
    """
    channels = set(decision.get("channels") or ())
    return bool(
        decision.get("record_kind") == "citation_neighbour"
        or decision.get("detail_status") == "pending"
        or (channels and channels <= set(CITE_CHANNELS))
    )


def counter_ids(bundle: dict) -> list[str]:
    """Decision ids the counter-authority pass actually flagged."""
    out = []
    for d in bundle.get("decisions") or []:
        if not isinstance(d, dict):
            continue
        status = d.get("counter_status")
        if status in NON_COUNTER_STATUSES:
            continue
        did = str(d.get("decision_id") or "")
        if did:
            out.append(did)
    return out


def _finding(code: str, severity: str, detail: str, **extra: Any) -> dict:
    row = {"code": code, "severity": severity, "detail": detail}
    row.update(extra)
    return row


def verify_bundle(
    bundle: dict,
    *,
    question: dict | None = None,
    min_decisions: int | None = None,
    max_decisions: int | None = None,
    require_answer: bool = True,
) -> dict:
    """Re-verify one bundle now. Never raises on a bad bundle.

    Returns a machine-readable verdict. ``admissible`` is true only when no
    ``blocking`` finding was raised; warnings are carried separately so the
    owner card can disclose them without refusing the packet.
    """
    decisions = [d for d in (bundle.get("decisions") or []) if isinstance(d, dict)]
    findings: list[dict] = []
    inspection: dict = {}

    try:
        inspection = inspect_bundle(bundle)
    except Exception as exc:  # inspection itself failed: that is a defect, not a crash
        findings.append(
            _finding(
                "inspection_failed",
                "blocking",
                f"the product's own bundle inspection raised {type(exc).__name__}: {exc}",
            )
        )

    n = len(decisions)
    floor = MIN_MAP_DECISIONS if min_decisions is None else int(min_decisions)
    ceiling = MAX_MAP_DECISIONS if max_decisions is None else int(max_decisions)

    if inspection:
        # --- contract, provenance and citation identity (all blocking) ------
        if inspection.get("validate_bundle_errors"):
            findings.append(_finding("validate_bundle", "blocking",
                                    "bundle contract violations: "
                                    + "; ".join(inspection["validate_bundle_errors"][:8]),
                                    count=len(inspection["validate_bundle_errors"])))
        if inspection.get("synthetic_decision_ids"):
            findings.append(_finding("synthetic_decision_ids", "blocking",
                                    "synthetic decision ids in the bundle: "
                                    + ", ".join(map(str, inspection["synthetic_decision_ids"][:5])),
                                    count=len(inspection["synthetic_decision_ids"])))
        if inspection.get("synthetic_cluster_labels"):
            findings.append(_finding("synthetic_cluster_labels", "blocking",
                                    "synthetic cluster labels: "
                                    + ", ".join(map(str, inspection["synthetic_cluster_labels"][:5])),
                                    count=len(inspection["synthetic_cluster_labels"])))
        if inspection.get("missing_required_fields"):
            findings.append(_finding("missing_required_fields", "blocking",
                                    "required per-decision fields absent/empty: "
                                    + ", ".join(inspection["missing_required_fields"][:8]),
                                    count=len(inspection["missing_required_fields"])))
        if inspection.get("orphan_cluster_member_ids"):
            findings.append(_finding("orphan_cluster_member", "blocking",
                                    "cluster members that are not decisions on the map: "
                                    + ", ".join(map(str, inspection["orphan_cluster_member_ids"][:5])),
                                    count=len(inspection["orphan_cluster_member_ids"])))
        if inspection.get("dangling_relations"):
            findings.append(_finding("dangling_relation", "blocking",
                                    "relations naming a decision that is not on the map",
                                    count=len(inspection["dangling_relations"])))
        for code, key in (
            ("citation_duplicates", "citation_duplicates"),
            ("citation_channel_seed_refs", "citation_channel_seed_refs"),
            ("pending_shell_identity", "pending_shell_identity"),
        ):
            rows = inspection.get(key) or []
            if rows:
                # citation_duplicates is {citation: [decision ids]}, the other two
                # are lists of finding rows; both are summarised, never truncated
                # into a shape the reader has to guess.
                detail = (f"{len(rows)} citation string(s) shared by two decisions: "
                          + ", ".join(f"{c} -> {ids}" for c, ids in list(rows.items())[:5])
                          if isinstance(rows, dict) else
                          f"{len(rows)} row(s) carry a citation that is not their own identity: "
                          + "; ".join(f"{r.get('decision_id')}={r.get('citation')}" for r in rows[:5]))
                findings.append(_finding(code, "blocking", detail, count=len(rows)))

        hosts = inspection.get("hosts") or {}
        foreign = {h: c for h, c in hosts.items() if h and h not in ACCEPTED_SOURCE_HOSTS}
        if foreign:
            findings.append(_finding("foreign_source_host", "blocking",
                                    "decisions citing a host outside the accepted OpenCaseLaw source: "
                                    + ", ".join(sorted(foreign)), hosts=foreign))

    # --- map size -------------------------------------------------------
    if n < floor:
        findings.append(_finding("map_too_small", "blocking",
                                f"{n} decisions on the map; the comparative gate needs at least {floor}",
                                n_decisions=n, minimum=floor))
    elif n > ceiling:
        findings.append(_finding("map_too_large", "warning",
                                f"{n} decisions on the map, above the {ceiling} window the gate is about",
                                n_decisions=n, maximum=ceiling))

    # --- the corrected source_url causal claim, machine-checked -----------
    null_rows = [d for d in decisions if not d.get("source_url")]
    unjustified = [str(d.get("decision_id")) for d in null_rows if not _is_citation_shell(d)]
    if unjustified:
        findings.append(_finding(
            "source_url_null_on_hydrated_row", "blocking",
            "source_url is null on a row that is not an un-hydrated citation-channel shell "
            f"({len(unjustified)} row(s)); that would be a provenance defect, not the "
            "known un-hydrated-shell behaviour",
            count=len(unjustified), rows=unjustified[:5],
        ))

    # --- answer grounding -------------------------------------------------
    answer = bundle.get("answer") or {}
    decision_ids = {str(d.get("decision_id")) for d in decisions if d.get("decision_id")}
    cited = [str(x) for x in (answer.get("cited_decision_ids") or [])]
    off_map = sorted({c for c in cited if c not in decision_ids})
    if require_answer:
        if str(answer.get("status") or "") not in ("ready", "degraded"):
            findings.append(_finding("answer_missing", "blocking",
                                    f"answer status is {answer.get('status')!r}; the gate compares an "
                                    "answer against a map and cannot run without one",
                                    status=answer.get("status")))
        if not cited:
            findings.append(_finding("answer_cites_nothing", "blocking",
                                    "the answer cites no decision"))
        if off_map:
            findings.append(_finding("answer_cites_off_map_decision", "blocking",
                                    "the answer cites decisions that are not on the map",
                                    count=len(off_map), rows=off_map[:5]))

    # --- counter-authority pass ------------------------------------------
    counters = counter_ids(bundle)
    if not counters:
        findings.append(_finding("no_counter_authority", "warning",
                                "no row carries a counter-authority status: gate question 3 "
                                "(did the map increase confidence that contrary authority had not "
                                "been hidden?) cannot be answered on this bundle"))

    # --- map-semantics disclosures (warnings, never claims) ---------------
    clusters = [c for c in (bundle.get("clusters") or []) if isinstance(c, dict)]
    sizes = [len(c.get("member_ids") or []) for c in clusters]
    mega = max(sizes) if sizes else 0
    mega_share = (mega / n) if n else 0.0
    if n and mega_share >= MEGA_CLUSTER_SHARE:
        findings.append(_finding(
            "map_is_one_mega_cluster", "warning",
            f"the largest cluster holds {mega}/{n} decisions ({mega_share:.0%}); disclose this to the "
            "jurist before they judge the map's structure (frontier-map-semantics owns the accepted "
            "measurement of map semantics)",
            n_decisions=n, mega_cluster=mega, share=round(mega_share, 4),
        ))
    n_relations = len(bundle.get("relations") or [])
    if n_relations == 0:
        findings.append(_finding(
            "no_relations_on_map", "warning",
            "no relation edge is on the map: 'reveal relations on selection' has nothing to reveal "
            "for this query",
        ))

    # --- language of the question itself ----------------------------------
    lang_counts = Counter(str(d.get("language") or "") for d in decisions)
    if question and question.get("language"):
        want = str(question["language"]).lower()
        have = lang_counts.get(want, 0)
        share = have / n if n else 0.0
        if share < MIN_QUESTION_LANGUAGE_SHARE:
            findings.append(_finding(
                "question_language_underrepresented", "warning",
                f"{have}/{n} decisions are in the question's own language ({want}); the retrieval "
                "may have answered a different question than the one pre-registered",
                language=want, in_language=have, share=round(share, 4),
            ))

    blocking = [f for f in findings if f["severity"] == "blocking"]
    warnings = [f for f in findings if f["severity"] != "blocking"]
    coverage = (inspection.get("decision_field_coverage") or {})
    rows_with_status = sum(
        1 for d in decisions if (d.get("counter_status") or "none") not in ("none", "", None)
    )
    measured = {
        "n_decisions": n,
        "n_clusters": len(clusters),
        "n_relations": n_relations,
        "n_counter_authorities": len(counters),
        "n_rows_with_counter_status": rows_with_status,
        "counter_ranks": sorted(
            int(d.get("rank") or 0) for d in decisions if str(d.get("decision_id") or "") in set(counters)
        )[:25],
        "n_outliers": sum(1 for d in decisions if d.get("is_outlier") is True),
        "languages": dict(sorted((k, v) for k, v in lang_counts.items() if k)),
        "largest_cluster_share": round(mega_share, 4),
        "source_url_null_rows": len(null_rows),
        "source_url_null_rows_explained_by_unhydrated_shells": len(null_rows) - len(unjustified),
        "canonical_url_populated": (coverage.get("canonical_url") or {}).get("populated"),
        "answer_status": answer.get("status"),
        "answer_method": answer.get("method"),
        "answer_cited": len(cited),
        "content_sha256": inspection.get("content_sha256"),
    }
    return {
        "schema": SCHEMA,
        "verified_at": None,  # stamped by the caller: the verdict belongs to the run
        "admissible": not blocking,
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "findings": findings,
        "measured": measured,
        "checks": {
            "min_decisions": floor,
            "max_decisions": ceiling,
            "require_answer": bool(require_answer),
            "accepted_source_hosts": sorted(ACCEPTED_SOURCE_HOSTS),
        },
    }


def verify_file(path: Path, **kwargs: Any) -> dict:
    bundle = json.loads(Path(path).read_text(encoding="utf-8"))
    verdict = verify_bundle(bundle, **kwargs)
    verdict["bundle_path"] = str(path)
    return verdict


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--min-decisions", type=int, default=None)
    ap.add_argument("--max-decisions", type=int, default=None)
    ap.add_argument("--require-answer", action="store_true", default=True)
    ap.add_argument("--no-require-answer", dest="require_answer", action="store_false")
    args = ap.parse_args(argv)
    verdict = verify_file(
        args.bundle, min_decisions=args.min_decisions, max_decisions=args.max_decisions,
        require_answer=args.require_answer,
    )
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    return 0 if verdict["admissible"] else 1


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())