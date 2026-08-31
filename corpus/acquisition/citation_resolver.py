#!/usr/bin/env python3
"""Citation ID resolution pipeline for LexMachina corpus lane.

Resolves text citation references (e.g., "BGE 133 II 249", "1C_704/2020")
to canonical decision_ids from the JSONL corpus.

Usage:
    python -m corpus.acquisition.citation_resolver
"""

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CitationResolver:
    """Resolve citation text references to canonical decision_ids.

    Maintains three indexes built from the canonical JSONL corpus:
    - docket_number -> decision_id (exact)
    - normalized_ref -> decision_id (for fuzzy matching)
    - decision_id -> metadata (reverse lookup)
    """

    def __init__(self, canonical_corpus_dir: str = "corpus/normalization/canonical"):
        self.corpus_dir = Path(canonical_corpus_dir)
        self._docket_index: Dict[str, str] = {}
        self._norm_index: Dict[str, str] = {}
        self._decision_meta: Dict[str, Dict[str, Any]] = {}
        self._bge_index: Dict[str, str] = {}
        self._built = False

    @staticmethod
    def _normalize_ref(text: str) -> str:
        """Normalize a reference string for matching.

        Strips prefixes (only when followed by a space, i.e. standard BGE
        format like 'BGE 133 II 249'), lowercases, replaces separators
        with underscores, and collapses multiple underscores.

        BUG-001 FIX: Previously stripped 'bge_' prefix unconditionally,
        which caused '_normalize_ref("BGE_133_II_249")' to return
        "133_ii_249" instead of "bge_133_ii_249". Now only strips when
        prefix is followed by a space (the standard BGE text format).
        """
        s = text.strip()
        for prefix in ("BGER ", "BGE "):
            if s.upper().startswith(prefix) and len(s) > len(prefix):
                s = s[len(prefix):]
                break
        s = s.lower()
        s = re.sub(r"[\s/\-]+", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s

    @staticmethod
    def _normalize_bge(text: str) -> str:
        """Normalize a BGE reference to canonical form 'BGE <vol> <sec> <page>'.

        Returns the normalized string or None if it doesn't parse.
        """
        s = text.strip()
        m = re.match(
            r"^BGE\s+(\d{1,3})\s+([IVXLC]+)\s+(\d{1,4})$",
            s,
            re.IGNORECASE,
        )
        if not m:
            return None
        vol, sec, page = m.group(1), m.group(2).upper(), m.group(3)
        return f"BGE {vol} {sec} {page}"

    @staticmethod
    def _normalize_docket(text: str) -> str:
        """Normalize a docket reference for index lookup.

        Produces lowercase, underscores only, no prefix.
        """
        s = text.strip()
        for prefix in ("bger_", "bge_"):
            if s.lower().startswith(prefix):
                s = s[len(prefix):]
                break
        s = re.sub(r"[\s/\-]+", "_", s)
        s = re.sub(r"_+", "_", s).strip("_").lower()
        return s

    def build_index(self) -> Dict[str, int]:
        """Scan all JSONL files in the corpus directory and build lookup indexes.

        Returns:
            Dict with stats: decisions_indexed, bge_indexed, docket_indexed.
        """
        self._docket_index.clear()
        self._norm_index.clear()
        self._decision_meta.clear()
        self._bge_index.clear()

        decisions_indexed = 0
        jsonl_files = sorted(self.corpus_dir.glob("*.jsonl"))

        for fpath in jsonl_files:
            with open(fpath, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    decision_id = record.get("decision_id")
                    if not decision_id:
                        continue

                    docket = record.get("docket_number", "")
                    bge_ref = record.get("bge_reference")
                    decision_date = record.get("decision_date", "")
                    language = record.get("language", "")

                    # Store metadata
                    self._decision_meta[decision_id] = {
                        "docket_number": docket,
                        "bge_reference": bge_ref,
                        "decision_date": decision_date,
                        "language": language,
                    }

                    # Index docket_number -> decision_id (exact)
                    if docket:
                        self._docket_index[docket] = decision_id
                        norm_key = self._normalize_docket(docket)
                        self._norm_index[norm_key] = decision_id

                    # Index decision_id itself (some refs are decision_ids)
                    self._norm_index[self._normalize_ref(decision_id)] = decision_id

                    # Index bge_reference -> decision_id
                    if bge_ref:
                        norm_bge = self._normalize_bge(bge_ref)
                        if norm_bge:
                            self._bge_index[norm_bge] = decision_id
                            self._norm_index[self._normalize_ref(norm_bge)] = (
                                decision_id
                            )

                    decisions_indexed += 1

        self._built = True
        return {
            "decisions_indexed": decisions_indexed,
            "bge_indexed": len(self._bge_index),
            "docket_indexed": len(self._docket_index),
        }

    def _require_index(self):
        if not self._built:
            raise RuntimeError("Index not built. Call build_index() first.")

    def resolve_ref(self, ref_text: str) -> Dict[str, Any]:
        """Resolve a single citation reference text to a decision_id.

        Resolution strategies (in priority order):
        1. Exact match on docket_number or bge_reference.
        2. Normalized match (case-insensitive, separator-agnostic).
        3. Match against decision_id directly.
        4. Return unresolved.

        Returns:
            Dict with target_decision_id, target_ref, confidence_score,
            resolution_method.
        """
        self._require_index()

        result: Dict[str, Any] = {
            "target_decision_id": None,
            "target_ref": ref_text,
            "confidence_score": 0.0,
            "resolution_method": "unresolved",
        }

        text = ref_text.strip()
        if not text:
            return result

        # --- Strategy 1: Exact docket match ---
        if text in self._docket_index:
            result["target_decision_id"] = self._docket_index[text]
            result["confidence_score"] = 1.0
            result["resolution_method"] = "exact_docket"
            return result

        # --- Strategy 2: Exact BGE match ---
        norm_bge = self._normalize_bge(text)
        if norm_bge and norm_bge in self._bge_index:
            result["target_decision_id"] = self._bge_index[norm_bge]
            result["confidence_score"] = 1.0
            result["resolution_method"] = "exact_bge"
            return result

        # --- Strategy 3: Normalized docket match ---
        norm_docket = self._normalize_docket(text)
        if norm_docket in self._norm_index:
            result["target_decision_id"] = self._norm_index[norm_docket]
            result["confidence_score"] = 0.8
            result["resolution_method"] = "normalized_docket"
            return result

        # --- Strategy 4: Normalized BGE match ---
        if norm_bge:
            norm_bge_key = self._normalize_ref(norm_bge)
            if norm_bge_key in self._norm_index:
                result["target_decision_id"] = self._norm_index[norm_bge_key]
                result["confidence_score"] = 0.8
                result["resolution_method"] = "normalized_bge"
                return result

        # --- Strategy 5: Decision ID direct match ---
        norm_ref = self._normalize_ref(text)
        if norm_ref in self._norm_index:
            result["target_decision_id"] = self._norm_index[norm_ref]
            result["confidence_score"] = 0.8
            result["resolution_method"] = "normalized_docket"
            return result

        return result

    def resolve_batch(self, refs: List[str]) -> List[Dict[str, Any]]:
        """Resolve a list of citation references.

        Returns:
            List of resolution results, one per input ref.
        """
        return [self.resolve_ref(r) for r in refs]

    def classify_ref(self, ref_text: str) -> str:
        """Classify a reference as 'bge', 'docket', or 'other'.

        Classification rules:
        - Starts with 'BGE ' (case-insensitive) -> 'bge'
        - Contains a '/' and digits -> 'docket'
        - Matches pattern like 'XX.NNNN.NNNN' (e.g., VB.2020.00892) -> 'other'
        - Anything else -> 'other'
        """
        text = ref_text.strip()
        if re.match(r"^BGE\s", text, re.IGNORECASE):
            return "bge"
        if "/" in text and any(c.isdigit() for c in text):
            return "docket"
        if re.match(r"^[A-Z]{2,3}\.\d{4}\.\d+", text, re.IGNORECASE):
            return "other"
        # Heuristic: if it looks like a docket number (has digits and separators)
        if re.search(r"\d", text) and re.search(r"[_/\-]", text):
            return "docket"
        return "other"

    def resolve_citation_graph(
        self, graph_path: str, output_path: str
    ) -> Dict[str, Any]:
        """Resolve the full citation graph and produce statistics.

        Reads the citation_graph.json, resolves every outgoing reference,
        and writes the resolved graph + report.

        Args:
            graph_path: Path to citation_graph.json.
            output_path: Directory where outputs will be written.

        Returns:
            Statistics dict with total_references, resolved, unresolved,
            by_type, resolution_rate, etc.
        """
        self._require_index()

        with open(graph_path, "r", encoding="utf-8") as fh:
            graph = json.load(fh)

        outgoing = graph.get("outgoing", {})
        incoming = graph.get("incoming", {})

        resolved_outgoing: Dict[str, List[Dict[str, Any]]] = {}
        all_resolutions: List[Dict[str, Any]] = []
        type_stats: Counter = Counter()
        method_stats: Counter = Counter()

        for source_id, refs in outgoing.items():
            resolved_list = []
            for ref in refs:
                ref_type = self.classify_ref(ref)
                resolution = self.resolve_ref(ref)
                resolution["target_type"] = ref_type
                resolved_list.append(resolution)
                all_resolutions.append(resolution)
                type_stats[ref_type] += 1
                method_stats[resolution["resolution_method"]] += 1
            resolved_outgoing[source_id] = resolved_list

        total = len(all_resolutions)
        resolved_count = sum(
            1 for r in all_resolutions if r["target_decision_id"] is not None
        )
        unresolved_count = total - resolved_count

        stats = {
            "total_references": total,
            "resolved": resolved_count,
            "unresolved": unresolved_count,
            "resolution_rate": round(resolved_count / total, 4) if total else 0.0,
            "by_type": {
                "bge": type_stats.get("bge", 0),
                "docket": type_stats.get("docket", 0),
                "other": type_stats.get("other", 0),
            },
            "by_method": dict(method_stats),
            "source_decisions": len(outgoing),
            "incoming_refs": len(incoming),
        }

        # Build output
        resolved_graph = {
            "outgoing": resolved_outgoing,
            "incoming": incoming,
            "resolution_stats": stats,
            "original_stats": graph.get("stats", {}),
        }

        os.makedirs(output_path, exist_ok=True)

        resolved_graph_path = os.path.join(output_path, "citation_graph_resolved.json")
        with open(resolved_graph_path, "w", encoding="utf-8") as fh:
            json.dump(resolved_graph, fh, indent=2, ensure_ascii=False)

        report_path = os.path.join(output_path, "citation_resolution_report.md")
        self._write_report(stats, report_path)

        return stats

    @staticmethod
    def _write_report(stats: Dict[str, Any], path: str) -> None:
        """Write a markdown resolution report."""
        lines = [
            "# Citation Resolution Report\n",
            "## Summary\n",
            f"- **Total references**: {stats['total_references']}",
            f"- **Resolved**: {stats['resolved']}",
            f"- **Unresolved**: {stats['unresolved']}",
            f"- **Resolution rate**: {stats['resolution_rate']:.1%}",
            "",
            "## By Reference Type\n",
            f"| Type | Count |",
            f"|------|-------|",
        ]
        for ref_type, count in stats.get("by_type", {}).items():
            lines.append(f"| {ref_type} | {count} |")

        lines += [
            "",
            "## By Resolution Method\n",
            f"| Method | Count |",
            f"|--------|-------|",
        ]
        for method, count in stats.get("by_method", {}).items():
            lines.append(f"| {method} | {count} |")

        lines += [
            "",
            "## Source Decisions\n",
            f"- Decisions with outgoing citations: {stats.get('source_decisions', 'N/A')}",
            f"- Incoming citation entries: {stats.get('incoming_refs', 'N/A')}",
            "",
        ]

        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))


def run_resolution(
    canonical_corpus_dir: str = "corpus/normalization/canonical",
    citation_graph_path: str = "corpus/normalization/canonical/citation_graph.json",
    output_dir: str = "corpus/normalization/canonical/resolved",
) -> Dict[str, Any]:
    """Top-level entry point for citation resolution.

    Builds the index from the canonical corpus, resolves the citation graph,
    and writes outputs.

    Returns:
        Resolution statistics dict.
    """
    resolver = CitationResolver(canonical_corpus_dir)

    print(f"Building index from {canonical_corpus_dir}...")
    index_stats = resolver.build_index()
    print(f"  Index built: {index_stats}")

    print(f"Resolving citation graph: {citation_graph_path}")
    stats = resolver.resolve_citation_graph(citation_graph_path, output_dir)
    print(f"  Resolution complete: {stats}")

    return stats


if __name__ == "__main__":
    corpus_dir = sys.argv[1] if len(sys.argv) > 1 else "corpus/normalization/canonical"
    graph_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "corpus/normalization/canonical/citation_graph.json"
    )
    out_dir = (
        sys.argv[3] if len(sys.argv) > 3 else "corpus/normalization/canonical/resolved"
    )

    run_resolution(corpus_dir, graph_path, out_dir)
