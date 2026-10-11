"""
TF-IDF Proximity Calculator
Computes text-based similarity between decisions using TF-IDF.
Enhances proximity explanations with deep text similarity.
"""
import math
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple, Any


class TFIDFProximity:
    """Computes TF-IDF-based proximity between decisions."""

    def __init__(self):
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._tfidf_vectors: Dict[str, Dict[int, float]] = {}
        self._built = False

    def build_from_corpus(self, decisions: List[Dict]) -> None:
        """Build TF-IDF model from corpus decisions.

        Args:
            decisions: List of decision dicts with 'id' and 'text' fields
        """
        if not decisions:
            return

        # Tokenize and compute TF for each document
        doc_tfs = {}
        doc_freq = defaultdict(int)

        for doc in decisions:
            doc_id = doc.get("decision_id", "") or doc.get("id", "")
            # Handle different text field formats
            text = doc.get("text", "") or ""
            if not text:
                # Try to extract text from erwaegungen (list of dicts)
                erwaegungen = doc.get("erwaegungen", [])
                if isinstance(erwaegungen, list):
                    text_parts = []
                    for item in erwaegungen:
                        if isinstance(item, dict):
                            text_parts.append(item.get("text", ""))
                        elif isinstance(item, str):
                            text_parts.append(item)
                    text = " ".join(text_parts)
            if not text:
                # Try sachverhalt
                text = doc.get("sachverhalt", "") or ""
            if not text:
                # Try full_text (truncated in to_full)
                text = doc.get("full_text", "") or ""

            if not text or not isinstance(text, str):
                continue

            # Simple tokenization
            tokens = self._tokenize(text)
            if not tokens:
                continue

            # Compute term frequency
            tf = Counter(tokens)
            doc_tfs[doc_id] = tf

            # Update document frequency
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_freq[token] += 1

        if not doc_tfs:
            return

        # Build vocabulary
        vocab = {}
        for tf in doc_tfs.values():
            for token in tf.keys():
                if token not in vocab:
                    vocab[token] = len(vocab)
        self._vocab = vocab

        # Compute IDF
        n_docs = len(doc_tfs)
        self._idf = {}
        for token, idx in vocab.items():
            df = doc_freq.get(token, 0)
            self._idf[token] = math.log((n_docs + 1) / (df + 1)) + 1

        # Compute TF-IDF vectors
        self._tfidf_vectors = {}
        for doc_id, tf in doc_tfs.items():
            vector = {}
            for token, count in tf.items():
                if token in vocab:
                    tf_val = 1 + math.log(count) if count > 0 else 0
                    idf_val = self._idf.get(token, 1.0)
                    vector[vocab[token]] = tf_val * idf_val
            self._tfidf_vectors[doc_id] = vector

        self._built = True

    def cosine_similarity(self, doc_id_a: str, doc_id_b: str) -> float:
        """Compute cosine similarity between two documents.

        Args:
            doc_id_a: First document ID
            doc_id_b: Second document ID

        Returns:
            Cosine similarity score (0-1)
        """
        if not self._built:
            return 0.0

        vec_a = self._tfidf_vectors.get(doc_id_a, {})
        vec_b = self._tfidf_vectors.get(doc_id_b, {})

        if not vec_a or not vec_b:
            return 0.0

        # Compute dot product
        dot_product = 0.0
        for idx, val_a in vec_a.items():
            if idx in vec_b:
                dot_product += val_a * vec_b[idx]

        # Compute magnitudes
        mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot_product / (mag_a * mag_b)

    def get_similarity_explanation(
        self,
        doc_id_a: str,
        doc_id_b: str,
        corpus_summaries: Dict[str, Dict],
    ) -> Dict[str, Any]:
        """Get explanation of text similarity between two decisions.

        Args:
            doc_id_a: First document ID
            doc_id_b: Second document ID
            corpus_summaries: Dict mapping decision_id -> summary dict

        Returns:
            Dict with similarity score and top shared terms
        """
        if not self._built:
            return {
                "text_similarity": 0.0,
                "error": "TF-IDF model not built",
            }

        similarity = self.cosine_similarity(doc_id_a, doc_id_b)

        # Find top shared terms
        vec_a = self._tfidf_vectors.get(doc_id_a, {})
        vec_b = self._tfidf_vectors.get(doc_id_b, {})

        shared_terms = []
        for idx in vec_a:
            if idx in vec_b:
                # Find the token for this index
                token = None
                for t, i in self._vocab.items():
                    if i == idx:
                        token = t
                        break
                if token:
                    shared_terms.append({
                        "term": token,
                        "tfidf_a": round(vec_a[idx], 4),
                        "tfidf_b": round(vec_b[idx], 4),
                        "importance": round((vec_a[idx] + vec_b[idx]) / 2, 4),
                    })

        # Sort by importance
        shared_terms.sort(key=lambda x: x["importance"], reverse=True)

        return {
            "text_similarity": round(similarity, 4),
            "top_shared_terms": shared_terms[:10],
            "n_shared_terms": len(shared_terms),
            "doc_a_summary": corpus_summaries.get(doc_id_a, {}),
            "doc_b_summary": corpus_summaries.get(doc_id_b, {}),
        }

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization: lowercase, split on non-alphanumeric, remove stopwords."""
        # Basic stopwords (German, French, English)
        stopwords = {
            "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem", "einer",
            "und", "oder", "aber", "nicht", "ist", "sind", "war", "hat", "haben", "wird", "werden",
            "le", "la", "les", "des", "un", "une", "et", "ou", "mais", "ne", "pas", "est", "sont",
            "the", "a", "an", "and", "or", "but", "not", "is", "are", "was", "were", "be", "been",
            "art", "ist", "sind", "war", "hat", "haben", "wird", "werden", "kann", "soll", "muss",
        }

        # Lowercase and split
        text = text.lower()
        tokens = re.findall(r'[a-zäöüßéèêëàâçùûüîïô]+', text)

        # Remove stopwords and short tokens
        tokens = [t for t in tokens if t not in stopwords and len(t) > 2]

        return tokens
