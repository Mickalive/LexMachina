"""
Real Corpus Adapter for Evaluation

Loads Swiss Federal Supreme Court (BGer) decisions from canonical JSONL files
produced by the corpus lane and exposes them in the interface expected by
evaluation benchmarks.

Provenance:
- Source: /tmp/lex_accepted/corpus/corpus/normalization/canonical/
- Schema: /tmp/lex_accepted/corpus/corpus/schema/decision_schema.json
- Corpus lane state: /tmp/lex_accepted/corpus/state/corpus.json
"""

import json
import hashlib
import random
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class RealDecision:
    """Wrapper for a real BGer decision compatible with evaluation benchmarks."""
    decision_id: str
    docket_number: str
    date: str
    language: str
    court: str = "bger"
    chamber: Optional[str] = None
    legal_area: Optional[str] = None
    branch: Optional[str] = None
    jurivoc_descriptors: List[str] = field(default_factory=list)
    cited_decisions: List[str] = field(default_factory=list)
    citing_decisions: List[str] = field(default_factory=list)
    outcome: Optional[str] = None
    full_text: str = ""
    text_length: int = 0
    # Section-level text
    sachverhalt: Optional[str] = None
    erwaegungen_text: Optional[str] = None
    dispositiv: Optional[str] = None


class RealCorpusLoader:
    """
    Loads real BGer canonical JSONL data and provides the corpus interface
    needed by evaluation benchmarks.
    """

    def __init__(
        self,
        canonical_dir: str = "/tmp/lex_accepted/corpus/corpus/normalization/canonical",
        citation_graph_path: Optional[str] = None,
        max_decisions: Optional[int] = None,
        random_seed: int = 42,
    ):
        self.canonical_dir = Path(canonical_dir)
        self.citation_graph_path = citation_graph_path
        self.max_decisions = max_decisions
        self.random_seed = random_seed
        self.decisions: Dict[str, RealDecision] = {}
        self.citation_graph: Dict[str, List[str]] = {}  # decision_id -> [cited docket_numbers]
        self._loaded = False

    def load(self) -> bool:
        """Load canonical JSONL files and citation graph.
        
        Priority order:
        1. eval_structure.jsonl (highest quality, has Sachverhalt/Erwägungen)
        2. eval_balanced.jsonl (balanced sample with structural sections)
        3. eval_sample.jsonl (largest eval sample)
        4. yearly bger_20*.jsonl (bulk corpus, full_text only)
        """
        if self._loaded:
            return True

        # Load eval files first (they have structured sections)
        eval_files = [
            "bger_eval_structure.jsonl",
            "bger_eval_balanced.jsonl",
            "bger_eval_sample.jsonl",
        ]
        loaded_ids = set()
        for fname in eval_files:
            fp = self.canonical_dir / fname
            if fp.exists():
                count = self._load_jsonl(fp, loaded_ids)
                loaded_ids.update(self.decisions.keys())
                logger.info(f"Loaded {count} decisions from {fname}")

        # Load yearly files (bulk corpus, full_text only)
        yearly_files = sorted(self.canonical_dir.glob("bger_20*.jsonl"))
        for jf in yearly_files:
            count = self._load_jsonl(jf, loaded_ids)
            loaded_ids.update(self.decisions.keys())
            logger.info(f"Loaded {count} new decisions from {jf.name}")

        # Load citation graph
        if self.citation_graph_path:
            self._load_citation_graph(Path(self.citation_graph_path))
        else:
            cg_path = self.canonical_dir / "citation_graph.json"
            if cg_path.exists():
                self._load_citation_graph(cg_path)

        # Build reverse citation mapping
        self._build_reverse_citations()

        # Apply max_decisions limit
        if self.max_decisions and len(self.decisions) > self.max_decisions:
            random.seed(self.random_seed)
            ids = list(self.decisions.keys())
            selected = set(random.sample(ids, self.max_decisions))
            self.decisions = {k: v for k, v in self.decisions.items() if k in selected}

        self._loaded = True
        logger.info(f"Total decisions loaded: {len(self.decisions)}")
        return len(self.decisions) > 0

    def _load_jsonl(self, filepath: Path, skip_ids: Optional[set] = None) -> int:
        """Load a single JSONL file into decisions dict, skipping already-loaded IDs."""
        if skip_ids is None:
            skip_ids = set()
        count = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        decision = self._parse_decision(data)
                        if decision and decision.full_text and decision.decision_id not in skip_ids:
                            self.decisions[decision.decision_id] = decision
                            count += 1
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
        return count

    def _parse_decision(self, data: Dict[str, Any]) -> Optional[RealDecision]:
        """Parse a canonical JSONL record into a RealDecision."""
        decision_id = data.get("decision_id", "")
        if not decision_id:
            return None

        # Extract reasoning text from structured erwaegungen
        erwaegungen_text = None
        erwaegungen = data.get("erwaegungen")
        if erwaegungen and isinstance(erwaegungen, list):
            parts = []
            for e in erwaegungen:
                if isinstance(e, dict) and e.get("text"):
                    parts.append(e["text"])
            erwaegungen_text = " ".join(parts) if parts else None

        # Extract cited decisions (normalize to decision_ids where possible)
        raw_cited = data.get("cited_decisions", [])
        cited_ids = []
        for ref in raw_cited:
            if isinstance(ref, str) and ref:
                cited_ids.append(ref)

        return RealDecision(
            decision_id=decision_id,
            docket_number=data.get("docket_number", ""),
            date=data.get("decision_date", ""),
            language=data.get("language", "de"),
            court=data.get("court", "bger"),
            chamber=data.get("chamber"),
            legal_area=data.get("legal_area"),
            branch=data.get("branch"),
            cited_decisions=cited_ids,
            outcome=data.get("outcome"),
            full_text=data.get("full_text", ""),
            text_length=data.get("text_length", len(data.get("full_text", ""))),
            sachverhalt=data.get("sachverhalt"),
            erwaegungen_text=erwaegungen_text,
            dispositiv=data.get("dispositiv"),
        )

    def _load_citation_graph(self, filepath: Path):
        """Load the citation graph JSON."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            outgoing = data.get("outgoing", {})
            self.citation_graph = outgoing
            logger.info(f"Loaded citation graph: {len(outgoing)} outgoing edges")
        except Exception as e:
            logger.error(f"Error loading citation graph: {e}")

    def _build_reverse_citations(self):
        """Build reverse citation mapping (who cites this decision)."""
        reverse = defaultdict(list)
        for citing_id, cited_refs in self.citation_graph.items():
            for ref in cited_refs:
                reverse[ref].append(citing_id)
        for did in self.decisions:
            self.decisions[did].citing_decisions = reverse.get(did, [])
            # Also try matching by docket_number
            docket = self.decisions[did].docket_number
            if docket in reverse:
                self.decisions[did].citing_decisions.extend(reverse[docket])

    def get_decisions(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get decisions as list of dicts (corpus interface)."""
        decisions = list(self.decisions.values())
        if limit:
            decisions = decisions[:limit]
        return [asdict(d) for d in decisions]

    def get_decision_by_id(self, decision_id: str) -> Optional[RealDecision]:
        """Get a single decision by ID."""
        return self.decisions.get(decision_id)

    def get_language_distribution(self) -> Dict[str, int]:
        """Get language distribution."""
        dist = defaultdict(int)
        for d in self.decisions.values():
            dist[d.language] += 1
        return dict(dist)

    def get_legal_area_distribution(self) -> Dict[str, int]:
        """Get legal area distribution."""
        dist = defaultdict(int)
        for d in self.decisions.values():
            area = d.legal_area or d.branch or "unknown"
            dist[area] += 1
        return dict(dist)

    def get_year_distribution(self) -> Dict[str, int]:
        """Get year distribution."""
        dist = defaultdict(int)
        for d in self.decisions.values():
            year = d.date[:4] if d.date else "unknown"
            dist[year] += 1
        return dict(dist)


class RealCorpusRepresentation:
    """
    Provides representation functions for real corpus data.
    
    Supports:
    - TF-IDF baseline (whole-document)
    - TF-IDF on reasoning sections only (Sachverhalt + Erwaegungen)
    - TF-IDF on legal content only (excluding boilerplate headers)
    """

    def __init__(self, decisions: Dict[str, RealDecision], random_seed: int = 42):
        self.decisions = decisions
        self.random_seed = random_seed
        self._tfidf_vectorizer = None
        self._tfidf_reasoning_vectorizer = None
        self._embedding_cache: Dict[str, np.ndarray] = {}

    def _get_texts(self, mode: str = "full") -> Tuple[List[str], List[str]]:
        """Get texts and IDs for vectorizer fitting.
        
        When mode is 'reasoning' or 'legal_only' and a decision has no
        structured sections, falls back to full_text so the vectorizer
        can still be fitted on the entire corpus.
        """
        ids = []
        texts = []
        for did, d in self.decisions.items():
            if mode == "full":
                text = d.full_text
            elif mode == "reasoning":
                # Combine Sachverhalt and Erwaegungen (exclude headers/boilerplate)
                parts = []
                if d.sachverhalt:
                    parts.append(d.sachverhalt)
                if d.erwaegungen_text:
                    parts.append(d.erwaegungen_text)
                text = " ".join(parts) if parts else d.full_text  # fallback to full_text
            elif mode == "legal_only":
                # Use reasoning sections, which are the substantive legal content
                parts = []
                if d.sachverhalt:
                    parts.append(d.sachverhalt)
                if d.erwaegungen_text:
                    parts.append(d.erwaegungen_text)
                if d.dispositiv:
                    parts.append(d.dispositiv)
                text = " ".join(parts) if parts else d.full_text  # fallback to full_text
            else:
                text = d.full_text

            if text and len(text) > 50:
                ids.append(did)
                texts.append(text)
        return ids, texts

    def fit_tfidf(self, mode: str = "full", max_features: int = 10000):
        """Fit a TF-IDF vectorizer on the corpus."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        ids, texts = self._get_texts(mode)
        if not texts:
            raise ValueError("No valid texts for fitting")

        vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=True,
        )
        matrix = vectorizer.fit_transform(texts)

        # Normalize
        from sklearn.preprocessing import normalize
        matrix = normalize(matrix, norm="l2")

        # Build ID mapping
        id_to_idx = {did: i for i, did in enumerate(ids)}

        if mode == "full":
            self._tfidf_full_matrix = matrix
            self._tfidf_full_vectorizer = vectorizer
            self._tfidf_full_ids = ids
            self._tfidf_full_id_to_idx = id_to_idx
        elif mode == "reasoning":
            self._tfidf_reasoning_matrix = matrix
            self._tfidf_reasoning_vectorizer = vectorizer
            self._tfidf_reasoning_ids = ids
            self._tfidf_reasoning_id_to_idx = id_to_idx
        else:
            self._tfidf_legal_matrix = matrix
            self._tfidf_legal_vectorizer = vectorizer
            self._tfidf_legal_ids = ids
            self._tfidf_legal_id_to_idx = id_to_idx

        logger.info(f"TF-IDF fitted on {len(texts)} documents, {matrix.shape[1]} features (mode={mode})")
        return vectorizer, ids

    def get_tfidf_representation(self, mode: str = "full") -> Callable[[str], Optional[np.ndarray]]:
        """Get a representation function using TF-IDF embeddings."""
        if mode == "full":
            if not hasattr(self, "_tfidf_full_matrix"):
                self.fit_tfidf("full")
            matrix = self._tfidf_full_matrix
            id_to_idx = self._tfidf_full_id_to_idx
        elif mode == "reasoning":
            if not hasattr(self, "_tfidf_reasoning_matrix"):
                self.fit_tfidf("reasoning")
            matrix = self._tfidf_reasoning_matrix
            id_to_idx = self._tfidf_reasoning_id_to_idx
        else:
            if not hasattr(self, "_tfidf_legal_matrix"):
                self.fit_tfidf("legal_only")
            matrix = self._tfidf_legal_matrix
            id_to_idx = self._tfidf_legal_id_to_idx

        def representation_fn(decision_id: str, **kwargs) -> Optional[np.ndarray]:
            if decision_id in id_to_idx:
                idx = id_to_idx[decision_id]
                return np.asarray(matrix[idx].todense()).flatten().astype(np.float32)
            return None

        return representation_fn

    def get_text_embedding_fn(self, mode: str = "full") -> Callable[[str], np.ndarray]:
        """Get a function that embeds raw text (for boilerplate resistance test)."""
        if mode == "full":
            if not hasattr(self, "_tfidf_full_vectorizer"):
                self.fit_tfidf("full")
            vectorizer = self._tfidf_full_vectorizer
        elif mode == "reasoning":
            if not hasattr(self, "_tfidf_reasoning_vectorizer"):
                self.fit_tfidf("reasoning")
            vectorizer = self._tfidf_reasoning_vectorizer
        else:
            if not hasattr(self, "_tfidf_legal_vectorizer"):
                self.fit_tfidf("legal_only")
            vectorizer = self._tfidf_legal_vectorizer

        def text_embedding_fn(text: str) -> np.ndarray:
            vec = vectorizer.transform([text])
            norm = np.linalg.norm(vec.toarray()[0])
            if norm > 0:
                return (vec.toarray()[0] / norm).astype(np.float32)
            return np.zeros(vec.shape[1], dtype=np.float32)

        return text_embedding_fn


def load_real_corpus(
    canonical_dir: str = "/tmp/lex_accepted/corpus/corpus/normalization/canonical",
    max_decisions: Optional[int] = None,
) -> Tuple[Dict[str, RealDecision], Callable, Any]:
    """
    Convenience function to load real corpus and get components needed by evaluation.
    
    Returns:
        decisions: dict of decision_id -> RealDecision
        representation_fn: TF-IDF full-document representation
        corpus: corpus-like object for benchmark tests
    """
    loader = RealCorpusLoader(canonical_dir=canonical_dir, max_decisions=max_decisions)
    loader.load()

    rep = RealCorpusRepresentation(loader.decisions)
    rep.fit_tfidf("full")
    rep.fit_tfidf("reasoning")
    rep.fit_tfidf("legal_only")

    # Choose the representation to use (reasoning-only is better for legal distance)
    representation_fn = rep.get_tfidf_representation("reasoning")
    text_embedding_fn = rep.get_text_embedding_fn("reasoning")

    # Corpus wrapper
    corpus = loader

    # Return text_embedding_fn attached to representation_fn for boilerplate test
    representation_fn.text_embedding_fn = text_embedding_fn

    return loader.decisions, representation_fn, corpus
