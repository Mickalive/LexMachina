"""Before/after pair vs the OLD packet 38839347028, labelled by content_sha256.

Historical artifacts are never overwritten: the old packet is read-only and
both sides are labelled by their raw packet.json sha256 / bundle shas.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

from . import geometry_half
from .paths import QIDS

ISSUED_STATUSES = ("candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting")


def _bundle_stats(path: Path, qid: str) -> dict:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    c = collections.Counter((d.get("counter_status") or "none") for d in bundle.get("decisions") or [])
    issued = sum(c.get(s, 0) for s in ISSUED_STATUSES)
    mega = geometry_half.size_based_mega_cluster(bundle)
    return {
        "qid": qid,
        "n_decisions": len(bundle.get("decisions") or []),
        "counter_status_counts": dict(sorted(c.items())),
        "n_issued_counter_rows": issued,
        "n_abstained": c.get("abstained_unevidenced", 0),
        "largest_cluster_share_size_based": mega["largest_cluster_share"],
        "mega_cluster_fired": mega["fired"],
    }


def measure(old_questions: Path, rebuilt_questions: Path) -> dict:
    per_qid = {}
    for qid in QIDS:
        old_p = old_questions / f"{qid}.bundle.json"
        new_p = rebuilt_questions / f"{qid}.bundle.json"
        per_qid[qid] = {
            "before": _bundle_stats(old_p, qid),
            "after": _bundle_stats(new_p, qid),
        }
    old_packet = old_questions.parent / "packet.json"
    new_packet = rebuilt_questions.parent / "packet.json"
    return {
        "before_after": {
            "before_packet_label": {
                "packet_id": "38839347028",
                "packet_json_sha256": _sha(old_packet),
                "role": "OLD served packet under the accepted DO-NOT-SERVE order; read-only",
            },
            "after_packet_label": {
                "packet_id": "rebuilt-39027045675",
                "packet_json_sha256": _sha(new_packet),
                "role": "REBUILT packet measured by this charter",
            },
            "per_qid": per_qid,
            "no_historical_artifact_overwritten": True,
        }
    }


def _sha(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
