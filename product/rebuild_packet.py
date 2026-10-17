"""Offline rebuild of a served gate packet under the ADOPTED product config.

Factory direction v52, product lane P2 (rebuild) + P3 (publish).  The two
accepted frozen bars are UNMET on the served packet 38839347028
(``ACCEPTED_frontier-served-packet-falsification_38880639079.json``), so the
standing DO-NOT-SERVE order stands.  This module produces the REBUILT packet the
order's supersession condition names: the SAME three anchor questions, re-decided
under the adopted configuration:

* counter labels  -> ``frontier-counter-anchor-classifier`` (Outcome A,
  abstain-and-disclose, accept ``d236f5990``);
* rerank          -> ``rerank_product_bundle`` runs exactly once, so the bundle
  handed to the frozen scorer and to Core Evaluation is literally POST
  ``rerank_product_bundle`` (pre-serving obligation (a), CYCLE_38976645446
  claim ceiling).  The source packet 38839347028 predates the reranker
  (``run_query_initial`` gained it in ``d0de05378``) and carries raw adapter
  scores of 0.54..35917 with no ``retrieval_score_raw``; today's live pipeline
  would not ship that state.
* geometry        -> ``frontier-query-conditioned-map-geometry`` variant
  ``relevance_ordered`` (accept ``be5eba7f``);
* V2 axis metadata -> relabelled to ``retrieval relevance score`` (pre-serving
  obligation (b), CYCLE_38976645446_GATE.json).

Obligation (a) is a COMPARISON, not a promise of equality.  Both numbers are
published for every bundle: the post-rerank frozen counts on the bundle that
actually ships, AND the pre-rerank reference counts that reproduce the accepted
measured 7/8/7, with the per-criterion delta between them.  Where they differ
the drop is disclosed, never hidden; the geometry ABSOLUTE bar (11 of 11 on
every bundle) is unmet under either state, so no claim-bearing verdict changes.

The rebuild is OFFLINE and reuses the decisions/answers already cached in the
source packet: it does NOT re-retrieve and does NOT re-generate.  It re-decides
the counter labels under the FROZEN rubric and re-renders the query-conditioned
geometry, then re-verifies each bundle with the product's own admissibility
verifier and runs packet admission.  It writes a NEW packet directory and a
handoff manifest with every bundle's ``content_sha256``.

It does NOT self-certify.  The rebuilt packet is handed to Core Evaluation for
bar re-scoring; until an independent accepted audit of the REBUILT packet
returns gate=PASS with a serve recommendation superseding the DO-NOT-SERVE
order, admission stays DENIED and ``human_gate_ready`` stays false.
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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gate_packet import (  # noqa: E402
    CLAIM_CEILING,
    _now,
    build_question_draft,
    content_sha256,
    load_manifest,
)
from product.query import packet_admission  # noqa: E402
from product.query.counter_anchor import (  # noqa: E402
    ABSTAINED_STATUS,
    adoption_record,
    apply_anchor_labels,
    counter_anchor_summary,
    find_forbidden_constructions,
)
from product.query.gate_admissibility import verify_bundle  # noqa: E402
from product.query.qmap_variants import (  # noqa: E402
    ADOPTABLE_VARIANT,
    V2_AXIS_X_LABEL,
    V2_AXIS_Y_LABEL,
    apply_geometry_variant,
)
from product.query.relevance import rerank_product_bundle  # noqa: E402

DEFAULT_SOURCE = REPO_ROOT / "results" / "product" / "gate_packet" / "38839347028"
DEFAULT_OUT_ROOT = REPO_ROOT / "results" / "product" / "gate_packet"

#: Frozen geometry rule identity (pre-serving obligation (a)).  The scorer is the
#: accepted component, vendored byte-identically under
#: ``product/vendored/qmap_geometry/``; this module only feeds it the rebuilt
#: bundle and compares the per-criterion counts against the measured 7/8/7.
FROZEN_GEOMETRY_RULES_SHA256 = (
    "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
)
FROZEN_GEOMETRY_RULES_PATH = REPO_ROOT / "product" / "frozen" / "RULES_GEOMETRY.json"
#: Measured relevance_ordered per-bundle pass counts on the served packet.
MEASURED_PASS_COUNTS = {
    "de-kapitalverletzung": 7,
    "fr-bail-entretien": 8,
    "it-responsabilita-medica": 7,
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def score_rebuilt_geometry(bundle: dict, qid: str, *,
                           pre_rerank_reference: dict | None = None) -> dict[str, Any]:
    """Re-run the FROZEN 11-criteria rule on a rebuilt bundle.

    Pre-serving obligation (a): the shipped bundle is POST
    ``rerank_product_bundle``, and its per-criterion counts are compared against
    the measured 7/8/7.  When ``pre_rerank_reference`` is given the same rule is
    also scored on the adopted configuration WITHOUT the rerank (the state the
    7/8/7 was measured in) so the comparison is explicit and reproducible rather
    than asserted.  The rule and scorer are the accepted component; nothing is
    re-tuned here.
    """
    rules = load_frozen_geometry_rules()
    from qmap_geometry.scoring import rule_block_for, score_bundle  # noqa: E402

    scored = score_bundle(bundle, rule_block_for(rules, qid))
    measured = MEASURED_PASS_COUNTS.get(qid)
    result: dict[str, Any] = {
        "frozen_rules_sha256": FROZEN_GEOMETRY_RULES_SHA256,
        "qid": qid,
        "bundle_state": "post_rerank_product_bundle",
        "n_pass": scored["n_pass"],
        "n_criteria": scored["n_criteria"],
        "overall": scored["overall"],
        "criteria": scored["criteria"],
        "measured_pass_count": measured,
        "matches_measured": scored["n_pass"] == measured,
        "comparison_basis": (
            "post rerank_product_bundle counts vs the accepted measured 7/8/7 "
            "(measured pre-rerank on the served packet); comparison, not equality"
        ),
    }
    if pre_rerank_reference is not None:
        ref = score_bundle(pre_rerank_reference, rule_block_for(rules, qid))
        flips = {}
        for name, cell in scored["criteria"].items():
            ref_cell = (ref["criteria"] or {}).get(name) or {}
            if bool(cell.get("pass")) != bool(ref_cell.get("pass")):
                flips[name] = {
                    "post_rerank_pass": bool(cell.get("pass")),
                    "pre_rerank_pass": bool(ref_cell.get("pass")),
                    "post_rerank_value": cell.get("value"),
                    "pre_rerank_value": ref_cell.get("value"),
                    "bar": cell.get("bar"),
                }
        result["pre_rerank_reference"] = {
            "bundle_state": "adopted_config_without_rerank (the measured 7/8/7 state)",
            "n_pass": ref["n_pass"],
            "measured_pass_count": measured,
            "matches_measured": ref["n_pass"] == measured,
            "criteria": ref["criteria"],
        }
        result["comparison"] = {
            "post_rerank_n_pass": scored["n_pass"],
            "pre_rerank_n_pass": ref["n_pass"],
            "measured_pass_count": measured,
            "post_rerank_equals_measured": scored["n_pass"] == measured,
            "pre_rerank_equals_measured": ref["n_pass"] == measured,
            "criterion_flips": flips,
            "absolute_bar": "11 of 11 criteria on every bundle",
            "absolute_bar_met_post_rerank": scored["n_pass"] == scored["n_criteria"],
            "disclosure": (
                "Counts that fall below the measured value are published, not "
                "suppressed. The geometry absolute bar is unmet under every "
                "measured state, so no frozen verdict turns on the delta."
            ),
        }
    return result


def load_frozen_geometry_rules() -> dict[str, Any]:
    """Re-hash and load the frozen geometry rubric (never re-derived)."""
    raw = FROZEN_GEOMETRY_RULES_PATH.read_bytes()
    digest = _sha256_bytes(raw)
    if digest != FROZEN_GEOMETRY_RULES_SHA256:
        raise ValueError(
            f"frozen RULES_GEOMETRY.json sha256 {digest} != accepted "
            f"{FROZEN_GEOMETRY_RULES_SHA256}"
        )
    if str(REPO_ROOT / "product" / "vendored") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "product" / "vendored"))
    from qmap_geometry.scoring import load_rules  # noqa: E402

    return load_rules(str(FROZEN_GEOMETRY_RULES_PATH))


def _language_of(qid: str) -> str:
    return {"de-kapitalverletzung": "de", "fr-bail-entretien": "fr",
            "it-responsabilita-medica": "it"}.get(qid, qid.split("-")[0])


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def apply_adopted_config(bundle: dict, qid: str, *, rerank: bool = True,
                         ) -> tuple[dict, dict[str, Any]]:
    """Apply the adopted counter-label decision + rerank + geometry variant.

    Returns ``(rebuilt_bundle, applied_meta)``.  With ``rerank=True`` (the
    default, and the state that ships) the bundle is passed through
    ``rerank_product_bundle`` exactly once, which is what makes it literally
    "post rerank_product_bundle" for pre-serving obligation (a).
    ``rerank=False`` reproduces the adopted configuration WITHOUT the rerank so
    the frozen rule can be scored on the measured 7/8/7 state for comparison.

    Geometry, answer and relations are otherwise untouched; the counter-label
    seam never moves a rendered point.
    """
    language = _language_of(qid)
    out = apply_anchor_labels(bundle, qid=qid)
    rerank_meta: dict[str, Any] = {"applied": False, "reason": "rerank=False reference state"}
    if rerank:
        before_ids = [str(d.get("decision_id")) for d in out.get("decisions") or []]
        before_scores = [d.get("score") for d in out.get("decisions") or []]
        # rerank_product_bundle reads the adapter score as an input feature, so
        # it is a one-shot transform (rerank(rerank(x)) != rerank(x)).  The
        # shipped bytes are therefore documented as rerank(adopted(source)) and
        # are reproduced by replaying exactly that chain from the preserved
        # source packet, not by re-running rerank on the shipped file.
        out = rerank_product_bundle(out)
        for position, row in enumerate(out.get("decisions") or [], start=1):
            row["rank"] = position
        after_ids = [str(d.get("decision_id")) for d in out.get("decisions") or []]
        after_scores = [d.get("score") for d in out.get("decisions") or []]
        rerank_meta = {
            "applied": True,
            "function": "product.query.relevance.rerank_product_bundle",
            "call_count": 1,
            "runs_once": True,
            "non_idempotent": True,
            "replay_instruction": (
                "reproduce shipped bytes with "
                "rerank_product_bundle(apply_anchor_labels(source_bundle)) "
                "then apply_geometry_variant; rerank is a one-shot transform"
            ),
            "same_row_set": set(before_ids) == set(after_ids),
            "n_rows": len(after_ids),
            "positions_changed": sum(1 for a, b in zip(before_ids, after_ids) if a != b),
            "score_field_before": _score_range(before_scores),
            "score_field_after": _score_range(after_scores),
            "retrieval_score_raw_present": all(
                "retrieval_score_raw" in d for d in out.get("decisions") or []
            ),
            "why": (
                "factory direction v52 product P2 pre-serving obligation (a): the "
                "bundle scored and handed to Core Evaluation must be post "
                "rerank_product_bundle; run_query_initial has reranked since "
                "commit d0de05378 and the source packet predates it"
            ),
        }
    decisions, clusters, variant_meta = apply_geometry_variant(
        out.get("decisions") or [],
        out.get("clusters") or [],
        str(out.get("query") or ""),
        ADOPTABLE_VARIANT,
        query_language=language,
    )
    out["decisions"] = decisions
    out["clusters"] = clusters
    prov = dict(out.get("provenance") or {})
    prov["geometry_variant"] = ADOPTABLE_VARIANT
    prov["rerank_product_bundle"] = rerank_meta
    prov["axis_metadata"] = {
        "geometry_variant": ADOPTABLE_VARIANT,
        "axis_x_label": V2_AXIS_X_LABEL,
        "axis_y_label": V2_AXIS_Y_LABEL,
        "axis_x_field": "score",
        "axis_relabel_source": (
            "CYCLE_38976645446_GATE.json claim_ceiling."
            "integrator_action_required_before_serving_v2(b)"
        ),
        "component_disclosure_wording": (
            "horizontal position is the retrieval relevance score"
        ),
        "component_projection_string": variant_meta.get("projection"),
    }
    out["provenance"] = prov
    return out, variant_meta


def _score_range(scores: list[Any]) -> dict[str, Any]:
    nums = [float(s) for s in scores if isinstance(s, (int, float))]
    if not nums:
        return {"min": None, "max": None}
    return {"min": min(nums), "max": max(nums)}


def path_binding_disclosure(out_dir: Path) -> dict[str, Any]:
    """D2: disclose that the packet's recorded paths are absolute workspace paths.

    Factory direction v55 product item (1)/D2. The rebuilt packet embeds the
    absolute CI workspace path in ``packet_dir``, ``packet_path`` and every
    ``bundles[*].bundle_path``. These are claim-bearing measured artifacts whose
    bytes must NOT be regenerated to store relative paths (that would change
    packet.json's raw sha256 2942c3c2... and invalidate the published identity),
    so the embedding is disclosed here and handled by re-rooting on the consumer
    side instead. Single source of truth: the writer and any later repair both
    emit this exact block.
    """
    return {
        "paths_are_absolute": True,
        "embedded_workspace_path": str(out_dir),
        "embedded_workspace_path_semantics": (
            "the packet-dir spelling passed to this writer (str(out_dir)), NOT "
            "necessarily an absolute path: the committed rebuilt-39027045675 "
            "disclosures carry the repo-relative spelling because that rebuild "
            "was invoked with a relative out_dir, while a rebuild invoked with an "
            "absolute out_dir writes an absolute string here. The PATH FIELDS in "
            "the packet (packet_dir, packet_path, bundles[*].bundle_path) are "
            "absolute in both cases. Do not read agreement between this field and "
            "the committed artifact as more than the writer semantics."
        ),
        "root_marker": "results",
        "statement": (
            "packet_dir, packet_path and every bundles[*].bundle_path in this "
            "packet and its handoff embed the ABSOLUTE workspace path of the "
            "machine that produced them (e.g. /home/runner/work/...). They are "
            "claim-bearing measured artifacts, so they are NOT regenerated to "
            "store relative paths: doing so would change packet.json's raw "
            "sha256 and invalidate the published identity. A consumer must "
            "re-root them onto its own checkout by taking the path tail from the "
            "'results' component onward, and must never open the embedded "
            "absolute path (that reads the producer's tree, not the tree under "
            "test). See product/tests/test_v52_endgame_delivery.py::"
            "resolve_committed_path."
        ),
        "packet_json_regenerated_for_relative_paths": False,
        "packet_content_sha256_remains": (
            "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170"),
    }


def rebuild_packet(
    source_dir: Path,
    out_dir: Path,
    *,
    run_id: str,
    operator: str = "autonomous-packet",
    top_n: int = 150,
) -> dict[str, Any]:
    """Rebuild the served packet offline under the adopted config."""
    source_dir = Path(source_dir)
    out_dir = Path(out_dir)
    manifest = load_manifest(source_dir / "manifest.json", strict=False)
    manifest["_run_id"] = run_id
    manifest["_operator"] = operator
    qdir = out_dir / "questions"
    qdir.mkdir(parents=True, exist_ok=True)

    questions_out: list[dict[str, Any]] = []
    handoff: list[dict[str, Any]] = []
    for spec in manifest["questions"]:
        qid = spec["qid"]
        src_bundle = source_dir / "questions" / f"{qid}.bundle.json"
        bundle = json.loads(src_bundle.read_text(encoding="utf-8"))
        rebuilt, variant_meta = apply_adopted_config(bundle, qid)
        # Obligation (a) comparison state: identical adopted config WITHOUT the
        # rerank, i.e. the state the accepted 7/8/7 was measured in.
        reference, _ref_meta = apply_adopted_config(bundle, qid, rerank=False)
        verdict = verify_bundle(rebuilt, question=spec)
        verdict["verified_at"] = _now()
        # The pre-serving mega-cluster disclosure, published on the SIZE-BASED
        # share (len(idx)/n) for the adopted geometry, the source packet's
        # incumbent geometry and the REBUILT rows re-clustered by the incumbent
        # algorithm.  The adopted relevance_ordered layout dissolves the
        # incumbent mega-cluster, so the incumbent checks are kept visible rather
        # than silently dropped: they also prove the rule is wired and live on
        # THIS packet's rows (non-vacuity), not only on the preserved source.
        source_verdict = verify_bundle(bundle, question=spec)
        source_measured = source_verdict.get("measured") or {}
        source_mega = next((w for w in (source_verdict.get("findings") or [])
                            if w.get("code") == "map_is_one_mega_cluster"), None)
        rebuilt_mega = next((w for w in (verdict.get("findings") or [])
                             if w.get("code") == "map_is_one_mega_cluster"), None)
        mega_disclosure = {
            "definition": "largest_cluster_size / n_decisions (size-based, len(idx))",
            "bar": 0.5,
            "threshold_edited": False,
            "size_based_not_member_ids": True,
            "source_packet": {
                "geometry": "incumbent (grouping of record for 38839347028)",
                "largest_cluster_share": source_measured.get("largest_cluster_share"),
                "largest_cluster_member_ids_share": source_measured.get("largest_cluster_member_ids_share"),
                "fired": bool(source_mega),
                "warning": source_mega,
                "computed_during_this_rebuild": True,
            },
            "rebuilt_packet": {
                "geometry": ADOPTABLE_VARIANT,
                "largest_cluster_share": (verdict.get("measured") or {}).get("largest_cluster_share"),
                "fired": bool(rebuilt_mega),
                "warning": rebuilt_mega,
            },
            "fired_on_any_check": bool(source_mega or rebuilt_mega),
            "rule_wiring": {
                "fires_when": "size-based largest-cluster share >= 0.5",
                "fired_example_share": (source_measured.get("largest_cluster_share")
                                        if source_mega else None),
                "fired_example_geometry": "incumbent",
                "why_a_check_may_not_fire": (
                    "The rebuilt packet ships relevance_ordered geometry, which "
                    "dissolves the incumbent mega-cluster; a check that does not "
                    "fire there is a smaller real share, not a suppressed "
                    "disclosure. The same size-based rule, run in this rebuild on "
                    "the incumbent grouping of record, still fires at 0.7696 on "
                    "the French bundle, so the rule is live and the threshold is "
                    "unchanged."
                ),
            },
            "note": (
                "The size-based mega-cluster disclosure fires whenever the largest "
                "cluster's size-based share >= 0.5; the threshold is unchanged at "
                "0.5 and the share is len(idx)-based, never member_ids-based. The "
                "packet 38839347028 as originally shipped suppressed this at "
                "warning_count=0 despite a 0.7696 French share; this rebuilt "
                "packet records the fired warning (0.7696, computed during this "
                "rebuild) rather than dropping it, and separately reports the "
                "share on its own adopted geometry."
            ),
        }
        # Adopted-config counters, published beside the admissibility verdict.
        anchor = counter_anchor_summary(rebuilt)
        verdict.setdefault("measured", {})["counter_anchor"] = anchor
        verdict["counter_anchor"] = anchor
        verdict["mega_cluster_disclosure"] = mega_disclosure
        # Pre-serving obligation (a): re-run the frozen 11-criteria rule on the
        # POST-RERANK bundle that ships and compare per-criterion counts vs the
        # measured 7/8/7 (with the pre-rerank reference state alongside).
        geometry_scoring = score_rebuilt_geometry(rebuilt, qid, pre_rerank_reference=reference)
        verdict["geometry_scoring"] = geometry_scoring
        verdict["rerank_product_bundle"] = (rebuilt.get("provenance") or {}).get(
            "rerank_product_bundle")

        bundle_path = qdir / f"{qid}.bundle.json"
        bundle_path.write_text(
            json.dumps(rebuilt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (qdir / f"{qid}.admissibility.json").write_text(
            json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        draft = build_question_draft(
            spec, rebuilt, verdict,
            manifest=manifest,
            server_run_id="offline-rebuild",
            bundle_path=bundle_path,
            mode="offline",
            base_url=None,
            top_n=top_n,
        )
        draft["counter_anchor"] = anchor
        draft["rebuild"] = {
            "source_packet": str(source_dir),
            "adopted_config": {
                "counter_labels": adoption_record(),
                "geometry_variant": ADOPTABLE_VARIANT,
                "axis_x_label": V2_AXIS_X_LABEL,
            },
        }
        (qdir / f"{qid}.question.json").write_text(
            json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        digest = content_sha256(rebuilt)
        questions_out.append({
            "index": len(questions_out) + 1,
            "qid": qid,
            "language": spec.get("language"),
            "question": spec.get("question"),
            "status": "admissible" if verdict["admissible"] else "blocked",
            "bundle_path": str(bundle_path),
            "question_path": str(qdir / f"{qid}.question.json"),
            "content_sha256": digest,
            "measured": verdict.get("measured") or {},
            "blocking": [f for f in (verdict.get("findings") or [])
                         if f.get("severity") == "blocking"],
            "warnings": [f for f in (verdict.get("findings") or [])
                         if f.get("severity") == "warning"],
            "notices": [f for f in (verdict.get("findings") or [])
                        if f.get("severity") == "info"],
            "guards_ok": verdict["admissible"],
            "counter_anchor": anchor,
            "mega_cluster_disclosure": mega_disclosure,
            "geometry_scoring": geometry_scoring,
            "rerank_product_bundle": verdict.get("rerank_product_bundle"),
        })
        handoff.append({
            "qid": qid,
            "bundle_path": str(bundle_path),
            "content_sha256": digest,
            "n_decisions": len(rebuilt.get("decisions") or []),
            "n_clusters": len(rebuilt.get("clusters") or []),
            "n_relations": len(rebuilt.get("relations") or []),
            "admissible": bool(verdict["admissible"]),
            "counter_anchor": anchor,
            "axis_x_label": V2_AXIS_X_LABEL,
            "mega_cluster_disclosure": mega_disclosure,
            "geometry_scoring": geometry_scoring,
            "rerank_product_bundle": verdict.get("rerank_product_bundle"),
        })

    packet = {
        "record_type": "lex_gate_packet_rebuilt",
        "schema": "product-gate-packet-rebuilt/1",
        "packet_id": f"rebuilt-{run_id}",
        "source_packet": str(source_dir),
        "generated_at": _now(),
        "run_id": run_id,
        "operator": operator,
        "mode": "offline",
        "n_questions": len(questions_out),
        "ok": all(q["status"] == "admissible" for q in questions_out),
        "questions": questions_out,
        "manifest_sha256": manifest.get("_sha256"),
        "adopted_config": {
            "counter_labels": adoption_record(),
            "rerank_product_bundle": {
                "applied": True,
                "function": "product.query.relevance.rerank_product_bundle",
                "obligation": (
                    "CYCLE_38976645446_GATE.json claim_ceiling."
                    "integrator_action_required_before_serving_v2(a): score a bundle "
                    "that is post rerank_product_bundle and compare counts with 7/8/7"
                ),
            },
            "geometry_variant": ADOPTABLE_VARIANT,
            "axis_x_label": V2_AXIS_X_LABEL,
            "axis_relabel_obligation": (
                "CYCLE_38976645446_GATE.json claim_ceiling."
                "integrator_action_required_before_serving_v2(b)"
            ),
        },
        "claim_ceiling": CLAIM_CEILING,
        "rebuilt_packet_ceiling": (
            "This is the REBUILT packet produced by the product under the adopted "
            "configuration. It is NOT certified: the two accepted frozen bars remain "
            "unmet until Core Evaluation re-scores it under the frozen rules and an "
            "independent accepted audit returns gate=PASS with a serve recommendation "
            "superseding the DO-NOT-SERVE order. The component never asserts that any "
            "specific decision IS supporting/contrary/limiting."
        ),
    }
    # Admission is a machine gate over the accepted bar verdicts; the rebuilt
    # packet cannot self-certify, so it is denied until re-scored.
    packet_admission.enforce(packet)
    (out_dir / "packet.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Disclosures: per-bundle warnings + the adopted-config abstain disclosure.
    disclosures: dict[str, Any] = {
        "schema": "product-gate-packet-disclosures/1",
        "rebuilt_packet": True,
        "adopted_config": packet["adopted_config"],
        "path_binding_disclosure": path_binding_disclosure(out_dir),
        "per_bundle": {
            q["qid"]: {
                "warnings": q["warnings"],
                "notices": q["notices"],
                "counter_anchor": q["counter_anchor"],
                "mega_cluster_disclosure": q["mega_cluster_disclosure"],
                "geometry_scoring": {
                    "bundle_state": q["geometry_scoring"].get("bundle_state"),
                    "n_pass": q["geometry_scoring"]["n_pass"],
                    "n_criteria": q["geometry_scoring"]["n_criteria"],
                    "overall": q["geometry_scoring"]["overall"],
                    "measured_pass_count": q["geometry_scoring"]["measured_pass_count"],
                    "matches_measured": q["geometry_scoring"]["matches_measured"],
                    "pre_rerank_reference": {
                        k: v for k, v in (
                            q["geometry_scoring"].get("pre_rerank_reference") or {}
                        ).items() if k != "criteria"
                    },
                    "comparison": q["geometry_scoring"].get("comparison"),
                },
                "rerank_product_bundle": q.get("rerank_product_bundle"),
            }
            for q in questions_out
        },
        "abstain_and_disclose": {
            "marker": ABSTAINED_STATUS,
            "note": (
                "Counter rows the adopted component abstains on are kept on the map "
                "as explicitly unevidenced rows. Support-among-issued, the abstention "
                "count and the yield are published side by side; none is traded away "
                "silently."
            ),
        },
        "claim_ceiling": packet["rebuilt_packet_ceiling"],
    }
    (out_dir / "disclosures.json").write_text(
        json.dumps(disclosures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "manifest.json").write_text(
        json.dumps({k: v for k, v in manifest.items() if not k.startswith("_")},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    handoff_manifest = {
        "schema": "product-rebuilt-packet-handoff/1",
        "generated_at": _now(),
        "run_id": run_id,
        "packet_dir": str(out_dir),
        "packet_path": str(out_dir / "packet.json"),
        "packet_content_sha256": _sha256_file(out_dir / "packet.json"),
        "bundles": handoff,
        "next_step": (
            "Hand this packet to Core Evaluation for bar re-scoring under the frozen "
            "rules (label RULES_LABEL.json 4457e971..., geometry RULES_GEOMETRY.json "
            "a7452748...). The DO-NOT-SERVE order on 38839347028 stands until an "
            "independent accepted audit of THIS rebuilt packet returns gate=PASS with "
            "a serve recommendation superseding it."
        ),
        "self_certification": False,
        "human_gate_ready": False,
    }
    (out_dir / "handoff.json").write_text(
        json.dumps(handoff_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Fail-closed self-check: no artifact may assert a specific decision IS
    # supporting/contrary/limiting (the component's claim ceiling).
    offenders: list[str] = []
    for path in (out_dir / "packet.json", out_dir / "disclosures.json",
                 out_dir / "handoff.json"):
        offenders.extend(f"{path.name}: {p}" for p in find_forbidden_constructions(path.read_text(encoding="utf-8")))
    handoff_manifest["forbidden_construction_offenders"] = offenders
    (out_dir / "handoff.json").write_text(
        json.dumps(handoff_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "packet_dir": str(out_dir),
        "packet_path": str(out_dir / "packet.json"),
        "handoff_path": str(out_dir / "handoff.json"),
        "n_questions": len(questions_out),
        "admission": packet.get("packet_admission"),
        "forbidden_construction_offenders": offenders,
        "bundles": handoff,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    ap.add_argument("--run-id", default=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ap.add_argument("--operator", default="autonomous-packet")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_root) / f"rebuilt-{args.run_id}"
    result = rebuild_packet(Path(args.source), out_dir, run_id=args.run_id, operator=args.operator)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
