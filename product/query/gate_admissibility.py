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

``dominant_cluster_composition`` (warning / info)
    the pre-registered ``language_coverage_expectation`` is about the bundle, but
    the jurist reads the *dominant cluster* - the circle the map renders at the
    centre.  A bundle can clear the bundle-level language check while its
    dominant cluster is mostly other-language, mostly un-hydrated rows.  Without
    a finding for that composition the packet can ship the same failure and still
    verify ``admissible=true`` (factory direction v54, item 3(a)), so it is
    measured and disclosed per question against the pre-registered expectation.

``unverifiable_source_url_host`` (blocking) + host distribution (info)
    ``source_url`` is the *court's own* host as OpenCaseLaw returns it, so a
    spread of cantonal hosts is normal and disclosed, not a defect.  A bare IP
    literal is different: nothing about that row can be verified by a human, and
    the direction requires it to be flagged explicitly rather than averaged into
    a host histogram (v54 item 3(b)).

Measurement-definition discipline (v54 R2)
    the largest-cluster share is computed from each cluster's ``size`` field, NOT
    from ``len(member_ids)``: ``product/query/qmap.py`` truncates ``member_ids``
    at :data:`CLUSTER_MEMBER_IDS_CAP`, so the two definitions diverge by up to
    17.5 points on real bundles and the divergence silently suppressed the
    mega-cluster disclosure.  Both numbers are now published side by side and the
    truncation is recorded, so a reader never has to guess which definition an
    artifact used.  :data:`MEGA_CLUSTER_SHARE` is unchanged.

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
import re
import sys
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # product-owned import shim, matches query/*
    sys.path.insert(0, str(REPO_ROOT))

from product.query.adversarial_retrieval import ADVERSARIAL_CHANNELS  # noqa: E402
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

#: Retrieval channels the PRODUCT owns, i.e. the routes the conventional ranked
#: list did not walk.  ``citation.*`` is the frontier adapter's own citation
#: expansion; the four ``adversarial.*`` channels are the independent
#: adversarial retrieval route ``product/query/adversarial_retrieval.py`` (D1 of
#: repair 38831241913, which replaced the classification-only pass the accepted
#: frontier measurement named as the single bounded candidate cause).
#:
#: This constant exists because the disclosure below once read
#: ``if counters and not n_counter_from_citations`` — i.e. it treated CITATION
#: channels as the only product-owned route.  After the adversarial route
#: shipped that predicate fired on bundles that demonstrably DO have their own
#: channel (10 of 15 counter rows on the live FR question of run 38838116453
#: arrived via ``adversarial.*``), and told the jurist on the owner card that
#: "the map cannot surface contrary authority that the ranked list did not
#: already contain".  A disclosure that contradicts the artifact it describes is
#: worse than no disclosure, so the predicate is now the full set and the row
#: provenance is recomputed and published next to it.
PRODUCT_OWNED_CHANNELS = frozenset(CITE_CHANNELS) | frozenset(ADVERSARIAL_CHANNELS)

#: Ranks beyond this are "not already visible in the ranked list" — the literal
#: reading of what the adversarial route is for.  Disclosed, never a claim.
COUNTER_LOW_RANK = 20

#: A share of the bundle at or above this in ONE cluster means the "cluster"
#: carries no information for that query: it is the map rendering itself, not
#: structure. Disclosed per question (advisory, never a claim about map quality).
#: FROZEN. Never changed to make a disclosure fire (v54 R2).
MEGA_CLUSTER_SHARE = 0.5

#: ``product/query/qmap.py`` emits ``member_ids`` truncated to the first 50 rows
#: (``member_ids: [...][:50]``) while ``size`` keeps the true cluster population.
#: Any share computed from ``len(member_ids)`` therefore understates the cluster
#: by exactly the truncation on every cluster larger than the cap (v54 R2). The
#: cap is recorded in every verdict so the two definitions can be reconciled
#: without re-deriving either.
CLUSTER_MEMBER_IDS_CAP = 50

#: The Federal Courts' own publication domain. Disclosed as a *share* of the
#: hydrated rows whose ``source_url`` points there: the product never promised a
#: federal-only corpus, so a low share is context for the jurist, not a defect.
FEDERAL_COURT_HOST_SUFFIX = "bger.ch"

#: A host that is an IPv4 literal, or an IPv6 literal (two or more colons and only
#: hex/colon/dot characters). Nothing about such a row can be opened, checked or
#: re-verified by the researcher who follows the source link, so it is a blocking
#: provenance finding instead of one more bar in a histogram.
_IPV4_LITERAL = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
_IPV6_LITERAL = re.compile(r"^(?=.*:.*:)[0-9a-f:.]+$", re.I)


def _is_ip_literal(host: str) -> bool:
    return bool(_IPV4_LITERAL.match(host) or _IPV6_LITERAL.match(host))

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


# --------------------------------------------------------------------------- #
# measurement helpers (publication-ready, reused by the packet and by tests)
# --------------------------------------------------------------------------- #

def cluster_shares(bundle: dict) -> list[dict]:
    """Per-cluster size, in BOTH published definitions, plus the truncation flag.

    ``size`` is the definition the finding thresholds use (v54 R2); ``member_ids``
    is what a reader counting ids by hand would get. Publishing both makes the
    divergence explicit instead of letting one of them be silently chosen.
    """
    decisions = [d for d in (bundle.get("decisions") or []) if isinstance(d, dict)]
    n = len(decisions)
    out: list[dict] = []
    for c in sorted((x for x in (bundle.get("clusters") or []) if isinstance(x, dict)),
                    key=lambda x: x.get("cluster_id") or 0):
        members = [str(m) for m in (c.get("member_ids") or [])]
        try:
            size = int(c.get("size"))
        except (TypeError, ValueError):
            size = len(members)
        out.append({
            "cluster_id": c.get("cluster_id"),
            "label": str(c.get("label") or "")[:120],
            "size": size,
            "size_share": round(size / n, 4) if n else 0.0,
            "member_ids_count": len(members),
            "member_ids_share": round(len(members) / n, 4) if n else 0.0,
            "member_ids_truncated": len(members) < size,
            "member_ids_omitted": max(0, size - len(members)),
        })
    return sorted(out, key=lambda r: (-int(r["size"]), r["cluster_id"]))


def dominant_cluster_composition(bundle: dict, question_language: str | None = None) -> dict:
    """Language and hydration composition of the cluster the map renders at centre.

    Computed from the *decisions* (``cluster_id``), not from ``member_ids``, so the
    truncation at :data:`CLUSTER_MEMBER_IDS_CAP` cannot hide rows from the
    measurement. ``unhydrated`` is the pre-registered definition
    ``detail_status != "search_hit"`` (v54 item 3(a)).
    """
    decisions = [d for d in (bundle.get("decisions") or []) if isinstance(d, dict)]
    clusters = cluster_shares(bundle)
    if not clusters or not decisions:
        return {}
    top = clusters[0]
    cid = top["cluster_id"]
    members = [d for d in decisions if d.get("cluster_id") == cid]
    langs = Counter(str(d.get("language") or "") for d in members)
    # Rows whose language the upstream payload did not state are counted, never
    # dropped: a composition that quietly omits 42 of 99 rows is not a composition.
    unlabelled = langs.get("", 0)
    statuses = Counter(str(d.get("detail_status") or "unrecorded") for d in members)
    unhydrated = [d for d in members if str(d.get("detail_status") or "") != "search_hit"]
    want = (question_language or "").lower() or None
    share = (langs.get(want, 0) / len(members)) if (want and members) else 0.0
    return {
        "cluster_id": cid,
        "label": top["label"],
        "size": top["size"],
        "bundle_size_share": top["size_share"],
        "members": len(members),
        "languages": dict(sorted((k, v) for k, v in langs.items() if k)),
        "rows_without_language": unlabelled,
        "question_language": want,
        "question_language_rows": langs.get(want, 0) if want else None,
        "question_language_share": round(share, 4) if want else None,
        "detail_status": dict(sorted(statuses.items())),
        "unhydrated_rows": len(unhydrated),
        "unhydrated_share": round(len(unhydrated) / len(members), 4) if members else 0.0,
    }


def source_url_host_distribution(bundle: dict) -> dict:
    """Where the source links the jurist will actually follow point.

    ``source_url`` is the *court's own* host as OpenCaseLaw records it, so a wide
    spread across cantonal and municipal hosts is the expected shape and is
    published rather than flagged. What is flagged is a row a human cannot
    verify at all: a bare IP literal (v54 item 3(b)).
    """
    decisions = [d for d in (bundle.get("decisions") or []) if isinstance(d, dict)]
    hosts: Counter = Counter()
    schemes: Counter = Counter()
    ip_rows: list[dict] = []
    linked = 0
    for d in decisions:
        raw = str(d.get("source_url") or "")
        if not raw:
            continue
        linked += 1
        parsed = urllib.parse.urlparse(raw)
        host = parsed.hostname or parsed.netloc or ""
        hosts[host] += 1
        schemes[parsed.scheme or "none"] += 1
        if _is_ip_literal(host):
            ip_rows.append({"decision_id": d.get("decision_id"), "source_url": raw})
    federal = sum(c for h, c in hosts.items() if h.endswith(FEDERAL_COURT_HOST_SUFFIX))
    return {
        "rows_with_source_url": linked,
        "rows_without_source_url": len(decisions) - linked,
        "hosts": dict(sorted(hosts.items())),
        "n_hosts": len(hosts),
        "schemes": dict(sorted(schemes.items())),
        "federal_court_host": FEDERAL_COURT_HOST_SUFFIX,
        "federal_court_hosted_rows": federal,
        "federal_court_hosted_share_of_linked": round(federal / linked, 4) if linked else 0.0,
        "ip_literal_rows": ip_rows,
    }


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
    # Query-concept coverage of the retrieved set. Measured for every verdict so
    # a *blocked* bundle says WHY: an uncited answer on a question whose second
    # concept has zero supporting rows upstream is a corpus fact, not a defect
    # of the generator, and the jurist must be able to see the difference.
    coverage: dict = {}
    try:
        from product.query.concept_coverage import coverage_report

        coverage = coverage_report(str(bundle.get("query") or ""), decisions)
    except Exception as exc:  # coverage is a disclosure, never a refusal reason
        coverage = {"error": f"{type(exc).__name__}: {exc}"}
    if require_answer:
        if str(answer.get("status") or "") not in ("ready", "degraded"):
            findings.append(_finding("answer_missing", "blocking",
                                    f"answer status is {answer.get('status')!r}; the gate compares an "
                                    "answer against a map and cannot run without one",
                                    status=answer.get("status")))
        if not cited:
            gap = (bundle.get("provenance") or {}).get("answer_gap_contract") or {}
            findings.append(_finding(
                "answer_cites_nothing", "blocking",
                "the answer cites no decision"
                + ("" if gap.get("fired") else
                   "; the product's zero-citation contract did not fire either, so neither the "
                   "generative answer nor the product fallback could ground this answer"
                   + (f" (query concepts without any supporting row: "
                      f"{', '.join(coverage.get('under_covered') or []) or 'unknown'})"
                      if coverage.get("under_covered") else "")),
                coverage_under_covered=coverage.get("under_covered"),
                coverage_rows_per_concept=coverage.get("rows_per_concept"),
                gap_contract_fired=bool(gap.get("fired")),
            ))
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
    # Where the counter rows came from.  The accepted frontier-adversarial-
    # discoverability measurement (cycle 38794235870, gate=PASS) found on the
    # accepted bundles that counter yield was 1.3% against a 2% threshold, that
    # every counter row came from the INITIAL retrieval channels, and that the
    # counter pass had no retrieval client at all (verdict CLASSIFICATION_ONLY).
    # The product then shipped the independent adversarial retrieval route
    # (repair 38831241913, adversarial_retrieval/2).  This disclosure is
    # therefore recomputed per question against the bundle in hand and reports
    # WHICH product-owned route brought each counter row, instead of asserting a
    # fixed verdict about the product: without it, gate question 3 asks the
    # jurist to judge something the artifact cannot show, and with a stale
    # predicate it says the opposite of what the artifact does show.
    counter_channels: Counter = Counter()
    counter_ids_ordered = set(counters)
    n_counter_from_citations = 0
    n_counter_from_adversarial = 0
    n_counter_from_product_owned = 0
    counter_ranks: list[int] = []
    counter_ranks_product_owned: list[int] = []
    counter_ranks_low: list[int] = []
    for d in decisions:
        if str(d.get("decision_id") or "") not in counter_ids_ordered:
            continue
        channels = {str(c) for c in (d.get("channels") or ())}
        counter_channels.update(channels)
        rank = int(d.get("rank") or 0)
        counter_ranks.append(rank)
        from_cites = bool(channels & CITE_CHANNELS)
        from_adv = bool(channels & set(ADVERSARIAL_CHANNELS))
        n_counter_from_citations += from_cites
        n_counter_from_adversarial += from_adv
        if from_cites or from_adv:
            n_counter_from_product_owned += 1
            counter_ranks_product_owned.append(rank)
            if rank > COUNTER_LOW_RANK:
                counter_ranks_low.append(rank)
    if counters and not n_counter_from_product_owned:
        findings.append(_finding(
            "counter_authority_has_no_own_channel", "warning",
            f"none of the {len(counters)} counter rows came through a product-owned retrieval "
            f"channel ({dict(counter_channels) or 'no channel recorded on any counter row'}); "
            "every contrary authority on this map was already in the initial ranked list, so "
            "the map cannot surface contrary authority the list did not already contain — judge "
            "gate question 3 with that in mind",
            n_counter_rows=len(counters), counter_channels=dict(counter_channels),
        ))
    elif counters:
        # The positive case must be visible too: the product-owned route is the
        # reason the map can be judged at all, and a silent positive reads as
        # "nothing to disclose".
        findings.append(_finding(
            "counter_authority_has_product_owned_channel", "info",
            f"{n_counter_from_product_owned}/{len(counters)} counter rows came through a "
            f"product-owned retrieval channel (adversarial {n_counter_from_adversarial}, "
            f"citation {n_counter_from_citations}); {len(counter_ranks_low)} of them sit beyond "
            f"rank {COUNTER_LOW_RANK} (max rank {max(counter_ranks_product_owned) if counter_ranks_product_owned else 0} "
            f"of {n}) - that is the set the conventional ranked list shows last",
            n_counter_rows=len(counters),
            n_counter_from_adversarial=n_counter_from_adversarial,
            n_counter_from_citation=n_counter_from_citations,
            counter_ranks_beyond_low=sorted(counter_ranks_low)[:25],
        ))

    # --- map-semantics disclosures (warnings, never claims) ---------------
    # R2: the share comes from cluster["size"], NOT len(member_ids). qmap.py
    # truncates member_ids at CLUSTER_MEMBER_IDS_CAP, so the old definition
    # understated every large cluster and suppressed this disclosure entirely on
    # a bundle whose true share was 55.7% (shipped as warning_count=0).
    clusters = [c for c in (bundle.get("clusters") or []) if isinstance(c, dict)]
    shares = cluster_shares(bundle)
    largest = shares[0] if shares else None
    mega = int(largest["size"]) if largest else 0
    mega_share = float(largest["size_share"]) if largest else 0.0
    if n and mega_share >= MEGA_CLUSTER_SHARE:
        findings.append(_finding(
            "map_is_one_mega_cluster", "warning",
            f"the largest cluster holds {mega}/{n} decisions ({mega_share:.0%}, measured from the "
            f"cluster's own 'size' field; its member_ids list is capped at {CLUSTER_MEMBER_IDS_CAP} "
            f"and covers {largest['member_ids_count']}); disclose this to the jurist before they "
            "judge the map's structure (frontier-map-semantics owns the accepted measurement of "
            "map semantics)",
            n_decisions=n, mega_cluster=mega, share=round(mega_share, 4),
            mega_cluster_share_from_member_ids=round(float(largest["member_ids_share"]), 4),
            member_ids_truncated=bool(largest["member_ids_truncated"]),
        ))
    n_relations = len(bundle.get("relations") or [])
    if n_relations == 0:
        findings.append(_finding(
            "no_relations_on_map", "warning",
            "no relation edge is on the map: 'reveal relations on selection' has nothing to reveal "
            "for this query",
        ))

    # --- composition of the dominant cluster (v54 item 3(a)) --------------
    # The bundle-level language check below can pass while the cluster the map
    # renders at the centre is mostly another language and mostly un-hydrated
    # rows, which is exactly the composition failure the pre-registered
    # language_coverage_expectation is about. Same frozen 0.25 constant: no new
    # threshold is introduced.
    composition = dominant_cluster_composition(bundle, question.get("language") if question else None)
    if composition:
        share = composition.get("question_language_share")
        expectation = str((question or {}).get("language_coverage_expectation") or "").strip()
        detail = (
            f"the dominant cluster holds {composition['size']}/{n} decisions "
            f"({composition['bundle_size_share']:.0%} of the map"
            + (f", languages {composition['languages']}" if composition.get("languages") else "")
            + (f"; {composition['rows_without_language']} of its {composition['members']} rows "
               "carry no language in the upstream payload"
               if composition.get("rows_without_language") else "")
            + (f"); {composition['unhydrated_rows']} of its {composition['members']} rows are "
               f"un-hydrated (detail_status != search_hit, {composition['unhydrated_share']:.0%})."
               if composition.get("members") else "")
        )
        if share is not None and share < MIN_QUESTION_LANGUAGE_SHARE:
            findings.append(_finding(
                "dominant_cluster_language_composition", "warning",
                f"{composition['question_language_rows']}/{composition['members']} of the "
                f"dominant cluster's rows are in the question's language ({share:.0%}, against the "
                f"same {MIN_QUESTION_LANGUAGE_SHARE:.0%} floor the bundle-level check uses); "
                + detail
                + (f" Pre-registered expectation: {expectation}" if expectation else ""),
                cluster_id=composition["cluster_id"], share=share, **{
                    k: composition[k] for k in ("languages", "rows_without_language",
                                                "unhydrated_rows", "unhydrated_share")
                },
            ))
        elif share is not None:
            findings.append(_finding(
                "dominant_cluster_composition", "info",
                f"{composition['question_language_rows']}/{composition['members']} of the dominant "
                f"cluster's rows are in the question's language ({share:.0%}); " + detail,
                cluster_id=composition["cluster_id"], share=share, **{
                    k: composition[k] for k in ("languages", "rows_without_language",
                                                "unhydrated_rows", "unhydrated_share")
                },
            ))

    # --- where the source links point (v54 item 3(b)) --------------------
    source_hosts = source_url_host_distribution(bundle)
    if source_hosts["ip_literal_rows"]:
        findings.append(_finding(
            "unverifiable_source_url_host", "blocking",
            f"{len(source_hosts['ip_literal_rows'])} row(s) carry a source_url whose host is a bare "
            "IP literal: the researcher cannot open, check or re-verify that link, so it is a "
            "provenance defect rather than a host-distribution fact",
            count=len(source_hosts["ip_literal_rows"]),
            rows=[r["decision_id"] for r in source_hosts["ip_literal_rows"]][:5],
        ))
    findings.append(_finding(
        "source_url_host_distribution", "info",
        f"{source_hosts['rows_with_source_url']} of {n} rows carry a source_url across "
        f"{source_hosts['n_hosts']} court/aggregator hosts; "
        f"{source_hosts['federal_court_hosted_rows']} of them "
        f"({source_hosts['federal_court_hosted_share_of_linked']:.0%}) are hosted by the federal "
        f"courts themselves, the rest on cantonal/municipal or aggregator sites "
        f"({source_hosts['rows_without_source_url']} rows have no source_url at all)",
        hosts=source_hosts["hosts"], schemes=source_hosts["schemes"],
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
    warnings = [f for f in findings if f["severity"] == "warning"]
    # "info" is a positive disclosure, not a defect: it must never inflate
    # warning_count, or a healthy packet starts looking like a sick one.
    notices = [f for f in findings if f["severity"] == "info"]
    coverage_field_coverage = (inspection.get("decision_field_coverage") or {})
    rows_with_status = sum(
        1 for d in decisions if (d.get("counter_status") or "none") not in ("none", "", None)
    )
    measured = {
        "n_decisions": n,
        "n_clusters": len(clusters),
        "n_relations": n_relations,
        "n_counter_authorities": len(counters),
        "n_rows_with_counter_status": rows_with_status,
        "counter_ranks": sorted(counter_ranks)[:25],
        "counter_channels": dict(counter_channels),
        "counter_rows_from_citation_channels": n_counter_from_citations,
        "counter_rows_from_adversarial_channels": n_counter_from_adversarial,
        "counter_rows_from_product_owned_channels": n_counter_from_product_owned,
        "counter_ranks_from_product_owned_channels": sorted(counter_ranks_product_owned)[:25],
        "counter_ranks_beyond_top20_from_product_owned_channels": sorted(counter_ranks_low)[:25],
        "counter_rows_beyond_top20": sum(1 for r in counter_ranks if r > COUNTER_LOW_RANK),
        "product_owned_channels": sorted(PRODUCT_OWNED_CHANNELS),
        "counter_yield": round(len(counters) / n, 4) if n else 0.0,
        "n_outliers": sum(1 for d in decisions if d.get("is_outlier") is True),
        "languages": dict(sorted((k, v) for k, v in lang_counts.items() if k)),
        "largest_cluster_share": round(mega_share, 4),
        "largest_cluster_share_definition": "cluster['size'] / n_decisions",
        "largest_cluster_member_ids_share": (
            round(float(largest["member_ids_share"]), 4) if largest else 0.0),
        "largest_cluster_member_ids_truncated": bool(largest["member_ids_truncated"]) if largest else False,
        "cluster_member_ids_cap": CLUSTER_MEMBER_IDS_CAP,
        "cluster_shares": shares[:8],
        "dominant_cluster": composition,
        "source_url_hosts": source_hosts["hosts"],
        "source_url_n_hosts": source_hosts["n_hosts"],
        "source_url_schemes": source_hosts["schemes"],
        "source_url_rows_without_url": source_hosts["rows_without_source_url"],
        "source_url_federal_court_hosted_rows": source_hosts["federal_court_hosted_rows"],
        "source_url_federal_court_hosted_share_of_linked": source_hosts[
            "federal_court_hosted_share_of_linked"],
        "source_url_ip_literal_rows": len(source_hosts["ip_literal_rows"]),
        "source_url_null_rows": len(null_rows),
        "source_url_null_rows_explained_by_unhydrated_shells": len(null_rows) - len(unjustified),
        "canonical_url_populated": (coverage_field_coverage or {}).get("canonical_url", {}).get("populated"),
        "answer_status": answer.get("status"),
        "answer_method": answer.get("method"),
        "answer_cited": len(cited),
        "answer_gap_contract_fired": bool(
            ((bundle.get("provenance") or {}).get("answer_gap_contract") or {}).get("fired")
        ),
        "query_concepts": coverage.get("concepts"),
        "query_concept_rows": coverage.get("rows_per_concept"),
        "query_concepts_under_covered": coverage.get("under_covered"),
        "content_sha256": inspection.get("content_sha256"),
    }
    return {
        "schema": SCHEMA,
        "verified_at": None,  # stamped by the caller: the verdict belongs to the run
        "admissible": not blocking,
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "notice_count": len(notices),
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