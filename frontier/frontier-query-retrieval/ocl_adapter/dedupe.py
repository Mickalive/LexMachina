"""Deterministic de-duplication by canonical decision identity.

Identity is resolved with several independent schemes and a union-find so two
records are merged if they agree on **any** of:

* ``cid:`` canonical decision id (falls back to ``decision_id``)
* ``src:`` publisher ``source_url`` (same underlying document)
* ``dkt:`` ``court|docket_number|decision_date`` (same ruling, different id)

The merge is order-independent: input order never changes the output, which
is what the determinism test asserts.
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .normalize import CHANNEL_PRIORITY


def _norm(value: Optional[str]) -> str:
    if not value:
        return ""
    return unicodedata.normalize("NFC", str(value)).strip()


def identity_schemes(rec: dict) -> List[Tuple[str, str]]:
    """All identity keys a record claims. Empty list = not identifiable."""
    keys: List[Tuple[str, str]] = []
    cid = _norm(rec.get("canonical_decision_id")) or _norm(rec.get("decision_id"))
    if cid:
        keys.append(("cid", cid))
    src = _norm(rec.get("source_url"))
    if src:
        keys.append(("src", src))
    court, docket, date = _norm(rec.get("court")), _norm(rec.get("docket_number")), _norm(rec.get("decision_date"))
    if docket:
        keys.append(("dkt", f"{court}|{docket}|{date}"))
    return keys


def identity_key(rec: dict) -> str:
    """Primary identity string used in reports and tests."""
    keys = identity_schemes(rec)
    if not keys:
        did = _norm(rec.get("decision_id"))
        return f"raw:{did}"
    scheme, value = keys[0]
    return f"{scheme}:{value}"


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _channel_rank(rec: dict) -> int:
    return CHANNEL_PRIORITY.get(rec.get("channel"), 99)


def _primary_key(rec: dict) -> tuple:
    """Lower is better. Fully deterministic (no dict iteration involved)."""
    rank = rec.get("rank")
    rank = 10**9 if rank is None else int(rank)
    score = rec.get("score")
    score = float("-inf") if score is None else float(score)
    return (_channel_rank(rec), rank, -score, _norm(rec.get("decision_id")))


def _merge(group: Sequence[dict]) -> dict:
    members = sorted(group, key=_primary_key)
    primary = dict(members[0])
    scores: Dict[str, Optional[float]] = {}
    channels: List[str] = []
    events: List[dict] = []
    seen_event = set()
    for m in members:
        ch = m.get("channel")
        if ch and ch not in channels:
            channels.append(ch)
        scores[ch or "?"] = m.get("score")
        for ev in m.get("provenance_events") or []:
            sig = json.dumps(ev, sort_keys=True, default=str)
            if sig not in seen_event:
                seen_event.add(sig)
                events.append(ev)
        # Fill missing descriptive fields from lower-priority members.
        for k, v in m.items():
            if primary.get(k) in (None, "", [], {}) and v not in (None, "", [], {}):
                primary[k] = v
        primary.setdefault("provenance_events", [])

    # Keep the strongest score of the primary's own kind; expose the rest.
    kind = primary.get("score_kind")
    same_kind = [m.get("score") for m in members
                 if m.get("score_kind") == kind and m.get("score") is not None]
    if same_kind:
        primary["score"] = max(same_kind)
    primary["channels"] = channels
    primary["provenance_events"] = events
    primary["merged"] = {
        "n_members": len(members),
        "member_ids": sorted({_norm(m.get("decision_id")) for m in members}),
        "channels": list(channels),
        "scores_by_channel": scores,
        "primary_key": list(_primary_key(primary)),
    }
    if len(members) > 1:
        primary["provenance"] = (primary.get("provenance") or "") + " merged×%d" % len(members)
    return primary


@dataclass
class DedupeResult:
    candidates: List[dict]
    stats: dict

    def __iter__(self):
        return iter(self.candidates)

    def __len__(self) -> int:
        return len(self.candidates)


def dedupe(records: Iterable[dict], *, order: str = "identity") -> DedupeResult:
    """Collapse records that refer to the same decision.

    Output order is independent of input order: groups are emitted sorted by
    ``(primary sort key, identity key)``.
    """
    recs = [r for r in records if isinstance(r, dict) and _norm(r.get("decision_id"))]
    n_input = len(recs)

    uf = _UnionFind(n_input)
    key_to_indices: Dict[Tuple[str, str], List[int]] = {}
    for i, rec in enumerate(recs):
        for key in identity_schemes(rec):
            key_to_indices.setdefault(key, []).append(i)
    for indices in key_to_indices.values():
        head = indices[0]
        for other in indices[1:]:
            uf.union(head, other)

    groups: Dict[int, List[dict]] = {}
    for i, rec in enumerate(recs):
        groups.setdefault(uf.find(i), []).append(rec)

    merged = [_merge(g) for g in groups.values()]
    merged.sort(key=lambda r: (_primary_key(r), identity_key(r)))

    n_by_channel: Dict[str, int] = {}
    for r in merged:
        for ch in r.get("channels") or [r.get("channel")]:
            n_by_channel[ch] = n_by_channel.get(ch, 0) + 1

    stats = {
        "input_records": n_input,
        "unique_candidates": len(merged),
        "merged_away": n_input - len(merged),
        "identity_keys": len(key_to_indices),
        "candidates_by_channel": dict(sorted(n_by_channel.items())),
        "strategy": "canonical_identity_v1",
        "schemes": ["canonical_decision_id", "source_url", "court|docket|date"],
    }
    return DedupeResult(candidates=merged, stats=stats)
