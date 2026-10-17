"""CROSS-CHECK table vs Core Evaluation's published re-score (if any).

If Core Evaluation has published a re-score of the rebuilt packet
(content_sha256 2942c3c2...), place its reported numbers beside this team's
recomputation for every quantity; any divergence is the headline finding.
If it has not published by hard stop, record Evaluation's numbers as ABSENT
(never invented, never blocking) and publish this team's recomputation alone.
Product's in-packet claimed numbers (packet.json counter_anchor /
geometry_scoring) are recorded as a SECONDARY reference clearly labelled as
product-claimed, not Evaluation-published.
"""
from __future__ import annotations

import json
from pathlib import Path

# Locations where a Core Evaluation re-score of the rebuilt packet might land.
EVAL_RESCORE_CANDIDATES = (
    Path("/tmp/lex_accepted/core/evaluation/results/evaluation/rebuilt_packet_rescore"),
    Path("/tmp/lex_accepted/core/evaluation/results/evaluation/bar_gates"),
    Path("/tmp/lex_accepted/core/evaluation/results/evaluation/label_lineage_gate/adjudications"),
    Path("/tmp/lex_accepted/core/evaluation/results/evaluation/rebuild_preflight"),
)

# Evidence of the search performed for a published Evaluation re-score. Recorded
# verbatim in the record so that an ABSENT reading is defensible rather than
# merely asserted (charter acceptance test 2).
EVAL_RESCORE_SEARCH_BASIS = {
    "accepted_mounts_grepped": [
        "/tmp/lex_accepted/core/evaluation (recursive grep for 2942c3c2, rebuilt-39027045675, 39034350468)",
        "/tmp/lex_accepted/core/product (recursive grep for 2942c3c2, rebuilt-39027045675)",
    ],
    "git_refs_swept": "all origin/cycle/core/evaluation/*, origin/lab/evaluation, origin/main",
    "git_commands": [
        "git log --all --oneline -S2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170",
        "git grep -l 'rebuilt-39027045675|2942c3c2|39034350468|6c56332c' <every ref> -- results/ reports/",
        "git ls-tree -r --name-only <ref> | grep -iE 'rescore|rebuilt' on the four newest evaluation cycle refs",
    ],
    "result": (
        "Zero evaluation-lane hits on every ref. The only lane artefacts naming these bytes are "
        "product/director/frontier ones. Core Evaluation's newest cycle reports state verbatim that "
        "'no real rebuilt packet was adjudicated' and that 'item (2) needs a rebuilt packet from "
        "Product; none exists'. The evaluation lane's rebuild_preflight legs are SYNTHETIC /tmp "
        "packets built from the accepted served packet 38839347028, not from 2942c3c2."
    ),
    "detected_at_run": 39048947212,
}


def _load_rescore(explicit_paths) -> dict | None:
    """Use an explicitly supplied Evaluation re-score if the lane published one."""
    for raw in explicit_paths or ():
        p = Path(raw)
        if not p.is_file():
            raise FileNotFoundError(f"evaluation re-score not found: {p}")
        return {"path": str(p), "record": json.loads(p.read_text(encoding="utf-8")), "source": "explicit_path"}
    return None


def _dig(record, *names):
    """First present key among ``names`` in a nested mapping (no invention)."""
    if not isinstance(record, dict):
        return None
    if "bars" in record and isinstance(record["bars"], dict):
        for name in names:
            for bar in record["bars"].values():
                if isinstance(bar, dict) and name in bar:
                    return bar[name]
    for name in names:
        if name in record:
            return record[name]
    for value in record.values():
        if isinstance(value, dict):
            hit = _dig(value, *names)
            if hit is not None:
                return hit
    return None


def _find_evaluation_rescore(packet_content_sha256: str) -> dict | None:
    """Best-effort discovery of an Evaluation re-score naming this packet.

    Returns None when nothing is published: the charter requires recording
    absence rather than inventing numbers or blocking.
    """
    needles = ("39027045675", "rebuilt-39027045675", packet_content_sha256[:16])
    for root in EVAL_RESCORE_CANDIDATES:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*.json")):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(n in text for n in needles) and "rescore" in (p.name + text[:2000]).lower():
                try:
                    return {"path": str(p), "record": json.loads(text)}
                except json.JSONDecodeError:
                    return {"path": str(p), "record": None, "parse_error": True}
    return None


def product_claimed_numbers(packet_json: Path) -> dict:
    """Product's OWN in-packet claimed numbers (secondary reference only)."""
    packet = json.loads(Path(packet_json).read_text(encoding="utf-8"))
    out = {"per_bundle": {}}
    for q in packet.get("questions") or []:
        qid = q.get("qid")
        ca = q.get("counter_anchor") or {}
        gs = q.get("geometry_scoring") or {}
        mega = q.get("mega_cluster_disclosure") or {}
        out["per_bundle"][qid] = {
            "product_claimed_counter_anchor": ca,
            "product_claimed_geometry_n_pass": gs.get("n_pass"),
            "product_claimed_geometry_overall": gs.get("overall"),
            "product_claimed_mega_cluster_fired_on_rebuilt": (mega.get("rebuilt_packet") or {}).get("fired"),
        }
    admission = packet.get("packet_admission") or {}
    out["product_claimed_packet_admission"] = {
        "packet_admitted": admission.get("packet_admitted"),
        "blocking_reason": admission.get("blocking_reason"),
        "bars": admission.get("bars"),
    }
    out["label"] = "product-claimed in-packet numbers, NOT Core Evaluation's independent re-score"
    return out


def build(team_half_a: dict, team_half_b: dict, packet_json: Path,
          packet_content_sha256: str = "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170",
          evaluation_rescore_paths=None) -> dict:
    evaluation = _load_rescore(evaluation_rescore_paths) or _find_evaluation_rescore(packet_content_sha256)
    record = (evaluation or {}).get("record") or {}
    rows = []
    # Label quantities
    pooled = team_half_a["pooled"]
    label_quantities = [
        ("label.n_scored_on_issued_population", pooled["n_issued"], "n_scored", "scored_counter_rows"),
        ("label.n_supported_among_issued", pooled["n_supported"], "n_supported", "n_supported"),
        ("label.support_rate_among_issued", pooled["support_rate_among_issued"], "support_rate", "support_rate"),
        ("label.n_abstained", pooled["n_abstained"], "n_abstained", "n_abstained"),
        ("label.yield_over_classifier_population", pooled["yield_over_classifier_population"],
         "yield", "yield_over_classifier_population"),
    ]
    for quantity, mine, *keys in label_quantities:
        theirs = _dig(record, *keys) if record else None
        rows.append({
            "quantity": quantity,
            "this_team_recomputed": mine,
            "core_evaluation_published": theirs,
            "divergence": None if theirs is None else (theirs != mine),
        })
    for qid, n_pass in sorted(team_half_b["criterion_counts"].items()):
        theirs = _dig(record, f"n_pass_{qid}", qid) if record else None
        rows.append({
            "quantity": f"geometry.{qid}.n_pass_of_11",
            "this_team_recomputed": n_pass,
            "core_evaluation_published": theirs if isinstance(theirs, int) else None,
            "divergence": None if not isinstance(theirs, int) else (theirs != n_pass),
        })
    mega_mine = team_half_b.get("mega_cluster_fires_on_any_rebuilt_bundle")
    mega_theirs = _dig(record, "mega_cluster_fires", "mega_cluster_disclosure_fires") if record else None
    rows.append({
        "quantity": "geometry.mega_cluster_disclosure_fires_on_any_rebuilt_bundle",
        "this_team_recomputed": mega_mine,
        "core_evaluation_published": mega_theirs,
        "divergence": None if mega_theirs is None else (mega_theirs != mega_mine),
    })
    if evaluation is None:
        status = "CORE_EVALUATION_RESCORE_ABSENT"
        headline = (
            "Core Evaluation's re-score of the rebuilt packet had not published at "
            "this team's hard stop; this team's recomputation is published alone and "
            "Evaluation's numbers are recorded as ABSENT (never invented, never blocking)."
        )
    else:
        status = "CORE_EVALUATION_RESCORE_PRESENT"
        divergences = [r["quantity"] for r in rows if r["divergence"]]
        headline = (
            f"Divergence on: {', '.join(divergences)}" if divergences
            else "No divergence detected between this team's recomputation and Evaluation's published numbers."
        )
    return {
        "status": status,
        "packet_content_sha256": packet_content_sha256,
        "core_evaluation_record_path": None if not evaluation else evaluation.get("path"),
        "cross_check_rows": rows,
        "headline_finding": headline,
        "evaluation_search_basis": EVAL_RESCORE_SEARCH_BASIS,
        "threshold_re_derived": False,
        "product_claimed_secondary_reference": product_claimed_numbers(packet_json),
    }
