"""Broad multilingual retrieval + free TF-IDF reranking over the query corpus."""
from __future__ import annotations

import re

# Small built-in legal synonym expansion (DE/FR/IT). Query terms not present
# here still work via plain TF-IDF; this only boosts cross-language recall.
EXPANSION = {
    "miete": ["mietrecht", "loyer", "bail", "locazione", "affitto", "mietvertrag", "mietzins", "rent"],
    "mietrecht": ["miete", "loyer", "bail", "locazione", "mietvertrag", "mietzins"],
    "loyer": ["miete", "mietrecht", "bail", "locazione", "mietvertrag"],
    "bail": ["miete", "mietrecht", "loyer", "locazione"],
    "arbeit": ["arbeitsrecht", "travail", "emploi", "lavoro", "kündigung", "licenciement", "dismissal"],
    "kündigung": ["arbeit", "licenciement", "dismissal", "congé", "disdetta"],
    "licenciement": ["kündigung", "arbeit", "dismissal", "congé"],
    "strafe": ["strafrecht", "peine", "pénal", "pena", "penale", "sanction"],
    "pénal": ["strafe", "strafrecht", "pena", "penale"],
    "asyl": ["asile", "asilo", "migration", "flüchtling", "réfugié", "rifugiato"],
    "asile": ["asyl", "asilo", "migration"],
    "sozialversicherung": ["assurance", "sociale", "assicurazione", "invalidität", "invalidité", "invalidità", "ahv", "avs"],
    "invalidität": ["invalidité", "invalidità", "sozialversicherung", "assurance"],
    "steuer": ["impôt", "fiscal", "imposta", "tax", "steuerrecht", "droit fiscal"],
    "familie": ["famille", "famiglia", "scheidung", "divorce", "divorzio", "ehe"],
    "scheidung": ["divorce", "divorzio", "familie", "ehe"],
    "vertrag": ["contrat", "contratto", "obligation", "obbligazione", "schuld"],
    "haftung": ["responsabilité", "responsabilità", "liability", "schadenersatz", "dommages"],
    "eigentum": ["propriété", "proprietà", "property"],
    "umwelt": ["environnement", "ambiente", "environment"],
    "datenschutz": ["protection des données", "protezione dei dati", "data protection"],
}

TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "") if len(t) > 1]


def expand_query(query: str) -> list[str]:
    """Return [original, expanded_variant, ...] — provenance-preserving variants."""
    toks = tokenize(query)
    extra: list[str] = []
    for t in toks:
        for syn in EXPANSION.get(t, []):
            if syn not in toks and syn not in extra:
                extra.append(syn)
    variants = [query]
    if extra:
        variants.append(query + " " + " ".join(extra[:12]))
    # Per-language light variants: original + top expansion terms only
    return variants


def tfidf_scores(query: str, docs: list[str]):
    """Rank docs against query with sklearn TF-IDF cosine. Returns (order, scores)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b[^\W\d_]{2,}\b", lowercase=True,
                                 sublinear_tf=True, max_features=20000)
    mat = vectorizer.fit_transform([query] + docs)
    sims = cosine_similarity(mat[0:1], mat[1:]).ravel()
    order = sorted(range(len(docs)), key=lambda i: -float(sims[i]))
    return order, [float(s) for s in sims]


def retrieve(query: str, corpus: list[dict], top_n: int = 150) -> tuple[list[dict], list[str]]:
    """Broad retrieval: score full_text, keep high recall (top_n of corpus)."""
    variants = expand_query(query)
    broad_q = variants[-1]
    docs = [(d.get("full_text", "") or "")[:8000] for d in corpus]
    order, scores = tfidf_scores(broad_q, docs)
    ranked = []
    for rank, idx in enumerate(order[:top_n]):
        d = corpus[idx]
        ranked.append({**d, "rank": rank + 1, "score": round(scores[idx], 6)})
    return ranked, variants
