#!/usr/bin/env python3
"""Assemble the accepted-config disclosure layer for a LIVE gate packet.

Factory direction v58, product lane ordered work (2): assemble the next gate
packet -- the packet of record v3 -- on the promoted tip with every accepted fix
present in-tree, freeze the packet bytes, publish ``packet.json``'s raw sha256
and run the shipped ledger against the exact committed bytes.

This module is the DISCLOSURE ASSEMBLER, not a new packet builder.  It does not
retrieve, does not regenerate and does not mutate a single bundle byte; the
packet's bundles are produced by the shipped server (``product/gate_packet.py
preflight --live``) and this module only *reads* those exact committed bytes and
publishes, beside them, the accepted-config disclosures the lane is obliged to
carry:

* **relevance_ordered geometry, re-scored** on the shipped post-rerank bundles
  (frozen rule ``a7452748...``, re-hashed before use) with the incumbent
  grouping scored side by side so a "does not fire" is visibly a smaller real
  number and never a suppressed disclosure;
* the **size-based** mega-cluster disclosure (``len(idx)/n``, threshold 0.5
  unchanged) with the ``member_ids`` share published beside it;
* the **query-concept under-coverage** disclosure state per bundle;
* the **abstain-and-disclose** counter-anchor three numbers together
  (support-among-issued, abstention count, yield) from the accepted component
  (accept ``d236f599``);
* the **RF1 counter split** (counter_authorities beside status_bearing, under
  the one accepted predicate in ``product/query/counter_status.py``), so a
  ``cited`` row can never be narrated as a counter authority (audit
  ``CYCLE_39310811831`` R3);
* the **retrieval provenance** measured off the bundle's own request_summary
  bytes -- ``live_network`` vs ``cache_replayed_read_through`` vs
  ``fixture_provider`` -- so a warm-cache replay can never be narrated as a
  live-network search (audit ``CYCLE_39310811831`` R2);
* the measured **evidence-hydration** facts (requested / hydrated / ids), so a
  hydration claim can never exceed the bytes (audit ``CYCLE_39310811831`` R4);
* the shipped ledger's re-verification of the exact committed bytes.

Everything here is fail-closed.  The module never writes ``human_gate_ready``,
never asserts a frozen bar passed, never edits a threshold, rubric, success rule
or bundle, and it refuses to publish an owner-ready claim: admission is decided
by the accepted ``packet_admission`` module reading the accepted bar verdicts.

Commands
--------
    # assemble disclosures + handoff over a live packet's committed bytes
    python product/packet_of_record.py assemble \
        --packet results/product/gate_packet/<run> --run-id <run> --tip <sha>

    # machine-check a committed packet-of-record (recompute and compare)
    python product/packet_of_record.py check --packet results/product/gate_packet/<run>

Exit codes: 0 ok, 2 bad arguments / not a live packet, 6 I/O, 7 reproduction
mismatch.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gate_packet import CLAIM_CEILING, content_sha256, recheck_packet  # noqa: E402
from product.query.gate_admissibility import verify_bundle  # noqa: E402
from product.query import packet_admission  # noqa: E402
from product.query.counter_status import (  # noqa: E402
    counter_authority_count,
    counter_authority_ids,
    counter_status_bearing_count,
    counter_status_histogram,
    evidenced_counter_ids,
    unevidenced_counter_ids,
)
from product.query.counter_anchor import (  # noqa: E402
    ABSTAINED_STATUS,
    adoption_record,
    counter_anchor_summary,
)
from product.query.qmap_variants import (  # noqa: E402
    ADOPTABLE_VARIANT,
    V2_AXIS_X_LABEL,
    V2_AXIS_Y_LABEL,
    apply_geometry_variant,
)

SCHEMA = "product-gate-packet-of-record/1"
DISCLOSURES_SCHEMA = "product-gate-packet-disclosures/1"
HANDOFF_SCHEMA = "product-gate-packet-handoff/1"

#: Accepted geometry rule identity.  Re-hashed before every use; never edited.
FROZEN_GEOMETRY_RULES_SHA256 = (
    "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
)
FROZEN_GEOMETRY_RULES_PATH = REPO_ROOT / "product" / "frozen" / "RULES_GEOMETRY.json"

#: The accepted FAIL this work must always be reported beside (requirement 15,
#: decision of record: frontier-map-semantics team run 38846038296, accept
#: 15362f6).  Preserved verbatim as evidence; never softened or relabelled.
ACCEPTED_GEOMETRY_FAIL = {
    "team_run_id": 38846038296,
    "accept_commit": "15362f6",
    "decision": (
        "FAIL with NO working in-budget alternative: keep the shipped geometry "
        "and CLOSE geometry work until after the human gate"
    ),
    "accepted_pass_counts_shipped_geometry": {
        "de-kapitalverletzung": 6,
        "fr-bail-entretien": 5,
        "it-responsabilita-medica": 5,
    },
    "accepted_baselines": {"de": 5, "fr": 5, "it": 4},
    "note": (
        "Preserved verbatim.  The in-budget INPUT change (hydrate-before-cluster "
        "/ relevance-ordered layout) was accepted later (be5eba7f / dc3ffc6c) and "
        "is the only geometry work permitted before the human gate."
    ),
}

#: Mega-cluster threshold, frozen.  Published, never edited.
MEGA_CLUSTER_SHARE = 0.5
MEGA_CLUSTER_FINDING_CODE = "map_is_one_mega_cluster"

#: Language per anchor qid (the packet's three questions).
_QID_LANGUAGE = {
    "de-kapitalverletzung": "de",
    "fr-bail-entretien": "fr",
    "it-responsabilita-medica": "it",
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _language_of(qid: str) -> str:
    return _QID_LANGUAGE.get(qid, (qid or "").split("-")[0] or "de")


def load_frozen_geometry_rules() -> dict[str, Any]:
    """Re-hash and load the frozen geometry rubric (never re-derived).

    Identical contract to ``product/rebuild_packet.py::load_frozen_geometry_rules``:
    the accepted rubric is fetched from its committed path, its sha256 is
    recomputed and compared, and only then is it parsed.  A mismatch refuses.
    """
    raw = FROZEN_GEOMETRY_RULES_PATH.read_bytes()
    digest = _sha256_file(FROZEN_GEOMETRY_RULES_PATH)
    if digest != FROZEN_GEOMETRY_RULES_SHA256:
        raise ValueError(
            f"frozen RULES_GEOMETRY.json sha256 {digest} != accepted "
            f"{FROZEN_GEOMETRY_RULES_SHA256}"
        )
    vendored = REPO_ROOT / "product" / "vendored"
    if str(vendored) not in sys.path:
        sys.path.insert(0, str(vendored))
    from qmap_geometry.scoring import load_rules  # noqa: E402

    return load_rules(str(FROZEN_GEOMETRY_RULES_PATH))


def score_geometry(bundle: dict, qid: str) -> dict[str, Any]:
    """Score one bundle under the frozen 11-criteria rule AS THAT BUNDLE SHIPS.

    Nothing is applied here: the caller passes either the shipped bundle or a
    variant-rendered copy, so the counts published for each state are counts of
    a state that exists in the packet, not of a hypothetical.
    """
    rules = load_frozen_geometry_rules()
    from qmap_geometry.scoring import rule_block_for, score_bundle  # noqa: E402

    scored = score_bundle(bundle, rule_block_for(rules, qid))
    return {
        "n_pass": scored["n_pass"],
        "n_criteria": scored["n_criteria"],
        "overall": scored["overall"],
        "criteria": scored["criteria"],
        "frozen_rules_sha256": FROZEN_GEOMETRY_RULES_SHA256,
    }


def render_variant(bundle: dict, qid: str) -> tuple[dict, dict[str, Any]]:
    """Return (variant_bundle_copy, meta) for ADOPTABLE_VARIANT.  No mutation."""
    variant_meta_name = ADOPTABLE_VARIANT
    decisions, clusters, meta = apply_geometry_variant(
        [dict(d) for d in (bundle.get("decisions") or [])],
        [dict(c) for c in (bundle.get("clusters") or [])],
        str(bundle.get("query") or ""),
        variant_meta_name,
        query_language=_language_of(qid),
    )
    out = dict(bundle)
    out["decisions"] = decisions
    out["clusters"] = clusters
    prov = dict(out.get("provenance") or {})
    prov["geometry_variant"] = variant_meta_name
    out["provenance"] = prov
    meta = dict(meta)
    meta["axis_x_label"] = V2_AXIS_X_LABEL
    meta["axis_y_label"] = V2_AXIS_Y_LABEL
    return out, meta


def _mega_finding(verdict: dict) -> dict | None:
    for f in verdict.get("findings") or []:
        if f.get("code") == MEGA_CLUSTER_FINDING_CODE:
            return f
    return None


def mega_cluster_disclosure(shipped_verdict: dict, variant_verdict: dict,
                            *, variant_basis: str = "variant_applied_once") -> dict[str, Any]:
    """Size-based mega-cluster disclosure with the member_ids share beside it.

    ``variant_basis`` states how the variant verdict was obtained, so no reader
    can mistake a double-applied phantom for a packet state: when the shipped
    bundle already carries the adopted variant, the caller passes the shipped
    verdict as the variant verdict with basis
    ``shipped_bundle_is_already_the_adopted_variant`` (apply_geometry_variant is
    not idempotent; a second application would publish a share that exists
    nowhere in the packet).
    """
    return {
        "definition": "largest_cluster_size / n_decisions (size-based, len(idx))",
        "bar": MEGA_CLUSTER_SHARE,
        "threshold_edited": False,
        "size_based_not_member_ids": True,
        "variant_basis": variant_basis,
        "shipped_geometry": {
            "largest_cluster_share": (shipped_verdict.get("measured") or {}).get(
                "largest_cluster_share"),
            "largest_cluster_member_ids_share": (shipped_verdict.get("measured") or {}).get(
                "largest_cluster_member_ids_share"),
            "member_ids_truncated": (shipped_verdict.get("measured") or {}).get(
                "largest_cluster_member_ids_truncated"),
            "fired": bool(_mega_finding(shipped_verdict)),
            "warning": _mega_finding(shipped_verdict),
        },
        "variant_geometry": {
            "variant": ADOPTABLE_VARIANT,
            "largest_cluster_share": (variant_verdict.get("measured") or {}).get(
                "largest_cluster_share"),
            "largest_cluster_member_ids_share": (variant_verdict.get("measured") or {}).get(
                "largest_cluster_member_ids_share"),
            "fired": bool(_mega_finding(variant_verdict)),
            "warning": _mega_finding(variant_verdict),
        },
        "fired_on_any_state": bool(_mega_finding(shipped_verdict) or _mega_finding(variant_verdict)),
        "note": (
            "The disclosure fires whenever the SIZE-based largest-cluster share "
            ">= 0.5; the threshold is unchanged and the share is len(idx)-based, "
            "never member_ids-based.  A state whose share is below the bar is a "
            "smaller real number, not a suppressed disclosure."
        ),
    }


def under_coverage_disclosure(shipped_verdict: dict) -> dict[str, Any]:
    """The accepted Evaluation handoff disclosure, read off the shipped verdict."""
    measured = shipped_verdict.get("measured") or {}
    under = measured.get("query_concepts_under_covered") or []
    fired = any(
        f.get("code") == "query_concepts_under_covered"
        for f in (shipped_verdict.get("findings") or [])
    )
    return {
        "disclosure_code": "query_concepts_under_covered",
        "under_covered_concepts": list(under),
        "rows_per_concept": measured.get("query_concept_rows"),
        "fired_on_admission_path": bool(fired),
        "warning": next((f for f in (shipped_verdict.get("findings") or [])
                         if f.get("code") == "query_concepts_under_covered"), None),
        "note": (
            "Disclosure only: an under-covered concept is a recall warning, never "
            "a verdict that a decision is irrelevant."
        ),
    }


def counter_anchor_three_numbers(bundle: dict) -> dict[str, Any]:
    """The abstain-and-disclose three numbers, published together, never alone."""
    summary = counter_anchor_summary(bundle)
    return {
        "component": summary.get("component"),
        "mode": "abstain-and-disclose",
        "n_scored": summary.get("n_scored"),
        "n_emitted": summary.get("n_emitted"),
        "n_abstained": summary.get("n_abstained"),
        "support_rate_among_emitted": summary.get("support_rate_among_emitted"),
        "yield": summary.get("yield"),
        "n_unevidenced_rows": summary.get("n_unevidenced_rows"),
        "abstained_status_marker": ABSTAINED_STATUS,
        "published_together": [
            "support_rate_among_emitted", "n_abstained", "yield",
        ],
        "claim_ceiling": (
            "The component CONFIRMS or ABSTAINS on a row's own proposed label; it "
            "never asserts that any specific decision IS supporting/contrary/"
            "limiting, and an abstained row is unevidenced AS A COUNTER LABEL and "
            "stays visible on the map."
        ),
    }


def retrieval_provenance(bundle: dict) -> dict[str, Any]:
    """How this bundle's retrieval actually ran, measured off the bundle itself.

    Audit ``CYCLE_39310811831`` R2 (BLOCKED) showed why this block must exist:
    a warm-cache read-through replay labelled ``mode: live`` was narrated in a
    report as a live-network search ("0 cache hits, 9 network calls" -- numbers
    that belonged to a different, map-only artifact).  The bytes never lied;
    the conflation happened between the bytes and the prose.  This block reads
    the bundle's OWN ``provenance.request_summary`` / ``cache_stats`` and
    publishes a machine classification beside the packet, so the report of
    record has no room to conflate the two:

    * ``live_network``                   -- the live provider path issued >= 1
      real network call in this build;
    * ``cache_replayed_read_through``    -- the live provider path served every
      request from the on-disk claim cache (network_calls == 0, cache_hits > 0).
      This is deterministic replay of a previously retrieved envelope -- honest
      gate-material behaviour, but NOT fresh network evidence;
    * ``fixture_provider``               -- the fixture/mock provider, rehearsal
      only, never gate material.
    """
    prov = bundle.get("provenance") or {}
    req = dict(prov.get("request_summary") or {})
    cache = prov.get("cache_stats") or {}
    fixture = bool(prov.get("fixture_mode"))
    network_calls = req.get("network_calls")
    cache_hits = req.get("cache_hits")
    if fixture:
        classification = "fixture_provider"
    elif isinstance(network_calls, int) and network_calls > 0:
        classification = "live_network"
    elif (isinstance(network_calls, int) and network_calls == 0
          and isinstance(cache_hits, int) and cache_hits > 0):
        classification = "cache_replayed_read_through"
    else:
        classification = "undetermined"
    return {
        "mode": prov.get("mode"),
        "fixture_mode": fixture,
        "classification": classification,
        "network_calls": network_calls,
        "cache_hits": cache_hits,
        "request_summary": req,
        "cache_stats": {
            "hits": cache.get("hits"),
            "misses": cache.get("misses"),
            "writes": cache.get("writes"),
            "n_keys": cache.get("n_keys"),
            "available": cache.get("available"),
        },
        "latency_seconds": prov.get("latency_seconds"),
        "note": (
            "Measured from this bundle's own provenance bytes by "
            "packet_of_record.retrieval_provenance; never asserted from prose. "
            "'mode: live' names the live provider PATH, not fresh network I/O: "
            "a cache_replayed_read_through build is deterministic replay of a "
            "previously retrieved envelope and is disclosed as such."
        ),
        "claim_ceiling": (
            "A cache_replayed_read_through classification is NOT live-network "
            "retrieval evidence for this packet build; freshness claims must "
            "cite the source envelope's own capture, not this build."
        ),
    }


def counter_status_rf1(bundle: dict) -> dict[str, Any]:
    """The RF1 counter split, under the ONE accepted predicate.

    Audit ``CYCLE_39310811831`` R3 (BLOCKED, recurrence of RF1): a report
    labelled status-bearing rows (mostly ``cited``) as "counter authorities".
    ``product/query/counter_status.py`` is the single source of truth; both
    definitions are always published side by side, never one alone.
    """
    rows = bundle.get("decisions") or []
    return {
        "single_source_of_truth": "product/query/counter_status.py",
        "n_counter_authorities": counter_authority_count(rows),
        "n_status_bearing": counter_status_bearing_count(rows),
        "histogram": counter_status_histogram(rows),
        "counter_authority_ids": counter_authority_ids(rows),
        "evidenced_counter_ids": evidenced_counter_ids(rows),
        "unevidenced_counter_ids": unevidenced_counter_ids(rows),
        "note": (
            "counter_authorities excludes cited/supporting-candidate/context/"
            "unclassified rows: a decision the sourced answer CITED is "
            "status-bearing provenance, the opposite of a counter authority. "
            "Both counts are always published together."
        ),
    }


def hydration_summary(bundle: dict) -> dict[str, Any]:
    """Measured evidence-hydration facts (audit CYCLE_39310811831 R4 class).

    The packet publishes what the bundle's own provenance recorded -- requested,
    hydrated and their ids -- so a report can never claim a hydration count the
    bytes do not carry.
    """
    eh = (bundle.get("provenance") or {}).get("evidence_hydration") or {}
    hydrated_ids = list(eh.get("hydrated_ids") or [])
    return {
        "requested": eh.get("requested"),
        "n_hydrated": eh.get("n_hydrated"),
        "n_hydrated_ids": len(hydrated_ids),
        "hydrated_ids": hydrated_ids,
        "degraded": eh.get("degraded"),
        "note": (
            "Measured from the bundle's provenance.evidence_hydration; a report "
            "claim must equal n_hydrated or re-measure."
        ),
    }


def geometry_rescore(bundle: dict, qid: str) -> dict[str, Any]:
    """relevance_ordered re-scored on the shipped post-rerank bundle.

    Reports deliberately together, so no single number can be read as a verdict:

    1. ``shipped`` -- the frozen rule's per-criterion counts on the packet's
       bundle exactly as committed (the state the map ships);
    2. ``variant_rescore`` -- the accepted ``relevance_ordered`` variant scored
       on the same rows.  The packet is assembled WITH the accepted variant
       enabled, so the shipped bundle already carries it and the re-score IS the
       shipped state; the basis field says so explicitly.  The variant is never
       applied twice: ``apply_geometry_variant`` is not idempotent and a second
       application would publish a state that does not exist in the packet.
       When a future packet ships the incumbent grouping, the variant is applied
       once to the shipped rows and the basis records that instead.
    3. the accepted FAIL and its per-bundle counts, preserved verbatim;
    4. the absolute bar coincidence: every criterion on every bundle.
    """
    shipped_variant = ((bundle.get("provenance") or {}).get("geometry_variant")
                       or "incumbent")
    shipped_score = score_geometry(bundle, qid)
    shipped_verdict = verify_bundle(bundle)
    if shipped_variant == ADOPTABLE_VARIANT:
        variant_meta = {
            "axis_x_label": ((bundle.get("provenance") or {}).get("axis_metadata") or {}).get(
                "axis_x_label"),
            "axis_y_label": ((bundle.get("provenance") or {}).get("axis_metadata") or {}).get(
                "axis_y_label"),
            "projection": ((bundle.get("provenance") or {}).get("axis_metadata") or {}).get(
                "projection"),
        }
        variant_score = shipped_score
        variant_verdict = shipped_verdict
        variant_basis = (
            "shipped_bundle_is_already_the_adopted_variant: the re-score of "
            "relevance_ordered IS the shipped state, not a second application"
        )
    else:
        variant_bundle, variant_meta = render_variant(bundle, qid)
        variant_score = score_geometry(variant_bundle, qid)
        variant_verdict = verify_bundle(variant_bundle)
        variant_basis = (
            "adopted_variant_applied_once_to_the_shipped_rows (the shipped state "
            "is the incumbent grouping)"
        )
    return {
        "qid": qid,
        "frozen_rules_sha256": FROZEN_GEOMETRY_RULES_SHA256,
        "shipped": {
            "geometry_variant": shipped_variant,
            "n_pass": shipped_score["n_pass"],
            "n_criteria": shipped_score["n_criteria"],
            "criteria": shipped_score["criteria"],
        },
        "variant_rescore": {
            "geometry_variant": ADOPTABLE_VARIANT,
            "basis": variant_basis,
            "n_pass": variant_score["n_pass"],
            "n_criteria": variant_score["n_criteria"],
            "criteria": variant_score["criteria"],
            "axis_x_label": variant_meta.get("axis_x_label"),
            "axis_y_label": variant_meta.get("axis_y_label"),
            "projection": variant_meta.get("projection"),
        },
        "accepted_fail_preserved": ACCEPTED_GEOMETRY_FAIL,
        "absolute_bar": "11 of 11 criteria on every bundle",
        "absolute_bar_met_shipped": shipped_score["n_pass"] == shipped_score["n_criteria"],
        "absolute_bar_met_variant_rescore": (
            variant_score["n_pass"] == variant_score["n_criteria"]),
        "disclosure": (
            "Counts for both states are published.  The geometry absolute bar is "
            "reported, not enforced here: enforcement is the accepted bar gate's "
            "and Core Evaluation's.  No threshold, rubric or success rule is "
            "edited by this module."
        ),
        "_variant_mega_fired": bool(_mega_finding(variant_verdict)),
    }


def _question_specs(packet_dir: Path, packet: dict) -> dict[str, dict]:
    """qid -> question spec from the packet's own frozen manifest copy."""
    qfile = packet_dir / "manifest.json"
    specs: dict[str, dict] = {}
    if qfile.is_file():
        try:
            manifest = json.loads(qfile.read_text(encoding="utf-8"))
            for q in manifest.get("questions") or []:
                if q.get("qid"):
                    specs[q["qid"]] = q
        except (OSError, ValueError):
            pass
    for entry in packet.get("questions") or []:
        qid = entry.get("qid")
        if qid and qid not in specs:
            specs[qid] = {"qid": qid, "language": entry.get("language"),
                          "question": entry.get("question")}
    return specs


def assemble(packet_dir: Path, *, run_id: str, operator: str, tip: str) -> dict[str, Any]:
    """Read a live packet's committed bytes and write the disclosure layer."""
    packet_dir = Path(packet_dir)
    packet_path = packet_dir / "packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if packet.get("mode") != "live":
        raise ValueError(
            f"packet mode is {packet.get('mode')!r}; the packet of record must be "
            "a LIVE packet (a fixture packet is rehearsal, not gate material)"
        )
    manifest_path = packet_dir / "manifest.json"
    packet_raw_sha256 = _sha256_file(packet_path)
    manifest_sha256 = _sha256_file(manifest_path) if manifest_path.is_file() else None
    specs = _question_specs(packet_dir, packet)

    per_bundle: dict[str, Any] = {}
    handoff_bundles: list[dict[str, Any]] = []
    for entry in packet.get("questions") or []:
        qid = entry.get("qid")
        spec = specs.get(qid, {"qid": qid, "language": entry.get("language"),
                               "question": entry.get("question")})
        bundle_path = _resolve(packet_dir, entry.get("bundle_path"),
                               f"questions/{qid}.bundle.json")
        if not bundle_path.is_file():
            raise FileNotFoundError(f"bundle for {qid} missing: {bundle_path}")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        shipped_verdict = verify_bundle(bundle, question=spec)
        # apply_geometry_variant is NOT idempotent (see geometry_rescore).  When
        # the shipped bundle already carries the adopted variant, the variant
        # verdict IS the shipped verdict; re-rendering would publish a
        # double-applied phantom state that exists nowhere in the packet.
        shipped_variant_now = ((bundle.get("provenance") or {}).get("geometry_variant")
                               or "incumbent")
        if shipped_variant_now == ADOPTABLE_VARIANT:
            variant_verdict = shipped_verdict
        else:
            variant_bundle, _meta = render_variant(bundle, qid)
            variant_verdict = verify_bundle(variant_bundle, question=spec)
        rescore = geometry_rescore(bundle, qid)
        mega = mega_cluster_disclosure(
            shipped_verdict, variant_verdict,
            variant_basis=(
                "shipped_bundle_is_already_the_adopted_variant: the variant "
                "verdict IS the shipped verdict, never a second application"
                if shipped_variant_now == ADOPTABLE_VARIANT else
                "adopted_variant_applied_once_to_the_shipped_rows"),
        )
        coverage = under_coverage_disclosure(shipped_verdict)
        anchor = counter_anchor_three_numbers(bundle)
        retrieval = retrieval_provenance(bundle)
        rf1 = counter_status_rf1(bundle)
        hydration = hydration_summary(bundle)
        net = {
            "qid": qid,
            "language": entry.get("language"),
            "geometry_rescore": rescore,
            "mega_cluster_disclosure": mega,
            "under_coverage_disclosure": coverage,
            "counter_anchor": anchor,
            "counter_status_rf1": rf1,
            "retrieval_provenance": retrieval,
            "evidence_hydration": hydration,
            "warnings": [
                {"code": f.get("code"), "severity": f.get("severity"),
                 "detail": f.get("detail")}
                for f in (shipped_verdict.get("findings") or [])
                if f.get("severity") != "blocking"
            ],
            "blocking": [
                {"code": f.get("code"), "detail": f.get("detail")}
                for f in (shipped_verdict.get("findings") or [])
                if f.get("severity") == "blocking"
            ],
        }
        per_bundle[qid] = net
        handoff_bundles.append({
            "qid": qid,
            "bundle_path": str(bundle_path),
            "content_sha256": content_sha256(bundle),
            "n_decisions": len(bundle.get("decisions") or []),
            "n_clusters": len(bundle.get("clusters") or []),
            "n_relations": len(bundle.get("relations") or []),
            "admissible": bool(shipped_verdict.get("admissible")),
            "geometry_variant_shipped": (bundle.get("provenance") or {}).get(
                "geometry_variant") or "incumbent",
            "counter_anchor": anchor,
            "counter_status_rf1": rf1,
            "retrieval_provenance": retrieval,
            "evidence_hydration": hydration,
            "mega_cluster_disclosure": mega,
            "under_coverage_disclosure": coverage,
        })

    # The shipped ledger: re-verify the exact committed bytes NOW.
    ledger = recheck_packet(packet_dir)

    disclosures = {
        "schema": DISCLOSURES_SCHEMA,
        "packet_id": packet.get("packet_id"),
        "run_id": run_id,
        "generated_at": _now(),
        "operator": operator,
        "mode": "live",
        "adopted_config": {
            "counter_labels": adoption_record(),
            "geometry_variant": ADOPTABLE_VARIANT,
            "axis_x_label": V2_AXIS_X_LABEL,
            "axis_y_label": V2_AXIS_Y_LABEL,
        },
        "accepted_geometry_fail_preserved": ACCEPTED_GEOMETRY_FAIL,
        "per_bundle": per_bundle,
        "claim_ceiling": CLAIM_CEILING,
    }
    (packet_dir / "disclosures.json").write_text(
        json.dumps(disclosures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    handoff = {
        "schema": HANDOFF_SCHEMA,
        "packet_id": packet.get("packet_id"),
        "run_id": run_id,
        "generated_at": _now(),
        "operator": operator,
        "tip_commit": tip,
        "packet_path": str(packet_path),
        "packet_raw_sha256": packet_raw_sha256,
        "manifest_sha256": manifest_sha256,
        "mode": "live",
        "bundles": handoff_bundles,
        "admission": packet.get("packet_admission"),
        "packet_admission_blocked": bool(packet.get("packet_admission_blocked")),
        "ready_for_owner_session": bool(packet.get("ready_for_owner_session")),
        "ledger": {
            "schema": ledger.get("schema"),
            "checked_at": ledger.get("checked_at"),
            "admissible_questions": ledger.get("admissible_questions"),
            "blocked_questions": ledger.get("blocked_questions"),
            "ready_for_owner_session": ledger.get("ready_for_owner_session"),
        },
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": bool((packet.get("packet_admission") or {}).get("packet_admitted")),
        "claim_ceiling": (
            "This handoff names the exact committed bytes of the packet of record "
            "and the accepted-config disclosures over them.  It is NOT a serve "
            "recommendation, NOT a self-certification and NOT an owner card: "
            "human_gate_ready, machine_gate_ready and ready_for_owner_session stay "
            "false while the accepted frozen bars are unmet or an independently "
            "accepted serve audit has not superseded the standing DO-NOT-SERVE "
            "orders."
        ),
    }
    (packet_dir / "handoff.json").write_text(
        json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    record = {
        "schema": SCHEMA,
        "packet_id": packet.get("packet_id"),
        "run_id": run_id,
        "generated_at": _now(),
        "operator": operator,
        "tip_commit": tip,
        "mode": "live",
        "packet_path": str(packet_path),
        "packet_raw_sha256": packet_raw_sha256,
        "manifest_sha256": manifest_sha256,
        "frozen_geometry_rules_sha256": FROZEN_GEOMETRY_RULES_SHA256,
        "frozen_label_rules_sha256": packet_admission.FROZEN_LABEL_RULES_SHA256,
        "admission": packet.get("packet_admission"),
        "packet_admission_blocked": bool(packet.get("packet_admission_blocked")),
        "packet_admission_reason": packet.get("packet_admission_reason"),
        "ready_for_owner_session": bool(packet.get("ready_for_owner_session")),
        "ready_for_owner_session_base": packet.get("ready_for_owner_session_base"),
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": bool((packet.get("packet_admission") or {}).get("packet_admitted")),
        "ledger": ledger,
        "disclosures_sha256": _sha256_file(packet_dir / "disclosures.json"),
        "handoff_sha256": _sha256_file(packet_dir / "handoff.json"),
        "claim_ceiling": CLAIM_CEILING,
    }
    (packet_dir / "PACKET_OF_RECORD.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def _resolve(packet_dir: Path, recorded: Any, relative: str) -> Path:
    """Re-root a recorded (possibly absolute, producer-machine) path."""
    if recorded:
        cand = Path(str(recorded))
        if cand.is_file():
            return cand
        # re-root from the 'results' component onward
        parts = list(cand.parts)
        for i, part in enumerate(parts):
            if part == "results":
                rerooted = REPO_ROOT.joinpath(*parts[i:])
                if rerooted.is_file():
                    return rerooted
    return packet_dir / relative


def check(packet_dir: Path) -> dict[str, Any]:
    """Recompute the disclosure layer from committed bytes and compare.

    A committed ``disclosures.json`` that does not reproduce from the committed
    bundles is a claim that cannot be re-derived -- the defect class the factory
    treated as blocking across both lanes (factory-wide requirement 29).
    """
    packet_dir = Path(packet_dir)
    committed = json.loads((packet_dir / "disclosures.json").read_text(encoding="utf-8"))
    packet = json.loads((packet_dir / "packet.json").read_text(encoding="utf-8"))
    specs = _question_specs(packet_dir, packet)
    mismatches: list[str] = []
    for entry in packet.get("questions") or []:
        qid = entry.get("qid")
        spec = specs.get(qid, {"qid": qid, "language": entry.get("language"),
                               "question": entry.get("question")})
        bundle_path = _resolve(packet_dir, entry.get("bundle_path"),
                               f"questions/{qid}.bundle.json")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        shipped_verdict_c = verify_bundle(bundle, question=spec)
        shipped_variant_c = ((bundle.get("provenance") or {}).get("geometry_variant")
                             or "incumbent")
        if shipped_variant_c == ADOPTABLE_VARIANT:
            variant_verdict_c = shipped_verdict_c
        else:
            variant_bundle_c, _meta_c = render_variant(bundle, qid)
            variant_verdict_c = verify_bundle(variant_bundle_c, question=spec)
        fresh = {
            "geometry_rescore": geometry_rescore(bundle, qid),
            "counter_anchor": counter_anchor_three_numbers(bundle),
            "counter_status_rf1": counter_status_rf1(bundle),
            "retrieval_provenance": retrieval_provenance(bundle),
            "evidence_hydration": hydration_summary(bundle),
            "mega_cluster_disclosure": mega_cluster_disclosure(
                shipped_verdict_c, variant_verdict_c,
                variant_basis=(
                    "shipped_bundle_is_already_the_adopted_variant: the variant "
                    "verdict IS the shipped verdict, never a second application"
                    if shipped_variant_c == ADOPTABLE_VARIANT else
                    "adopted_variant_applied_once_to_the_shipped_rows"),
            ),
            "under_coverage_disclosure": under_coverage_disclosure(shipped_verdict_c),
        }
        recorded = (committed.get("per_bundle") or {}).get(qid) or {}
        for key in ("counter_anchor", "geometry_rescore", "counter_status_rf1",
                    "retrieval_provenance", "evidence_hydration",
                    "mega_cluster_disclosure", "under_coverage_disclosure"):
            rec = recorded.get(key) or {}
            a = json.dumps(rec, sort_keys=True)
            b = json.dumps(fresh[key], sort_keys=True)
            if a != b:
                mismatches.append(f"{qid}:{key}")
    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "checked_at": _now(),
        "packet_id": packet.get("packet_id"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ap = sub.add_parser("assemble")
    ap.add_argument("--packet", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--operator", default="lex-product-team")
    ap.add_argument("--tip", default="")
    cp = sub.add_parser("check")
    cp.add_argument("--packet", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "assemble":
            record = assemble(Path(args.packet), run_id=args.run_id,
                              operator=args.operator, tip=args.tip)
            print(json.dumps({
                "ok": True,
                "packet_raw_sha256": record["packet_raw_sha256"],
                "packet_admission_blocked": record["packet_admission_blocked"],
                "ready_for_owner_session": record["ready_for_owner_session"],
                "packet_admitted": record["packet_admitted"],
            }, indent=2))
            return 0
        result = check(Path(args.packet))
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 7
    except (OSError, ValueError, FileNotFoundError) as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 6


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
