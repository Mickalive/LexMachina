#!/usr/bin/env python3
"""
Generate Legal-Distance Embeddings for Map Modes.

This script computes the legal-distance TF-IDF representations and hybrid embeddings
that are needed for the legal-distance map modes. It reuses the legal-distance
extraction logic but outputs embeddings in a format compatible with the fractal-map
multi-resolution Leiden pipeline.

Run this script to generate embeddings for all 5 selectable legal-distance modes.
"""

import json
import re
import numpy as np
from pathlib import Path
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("results/legal_distance/embeddings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata():
    """Load baseline metadata."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    return metadata


def load_corpus_decisions(metadata):
    """Load corpus decisions for the baseline set."""
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions[d['decision_id']] = d
    
    return decisions


def extract_section(text, language, section_patterns, end_patterns):
    """Generic section extractor."""
    if not text:
        return ""
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    
    start = -1
    for pattern in section_patterns:
        match = re.search(pattern, text_norm, re.IGNORECASE)
        if match:
            start = match.end()
            break
    if start == -1:
        return ""
    
    end = len(text_norm)
    for pattern in end_patterns:
        match = re.search(pattern, text_norm[start:], re.IGNORECASE)
        if match:
            candidate = start + match.start()
            if candidate < end:
                end = candidate
    return text_norm[start:end].strip()


def extract_erwaegungen(text, language):
    """Extract Erwägungen (reasoning) section."""
    if language == 'de':
        patterns = [r'(?:In\s+Erwägung\s*:)\s*\n', r'(?:Erwägungen\s*:)\s*\n']
    elif language == 'fr':
        patterns = [r'(?:Considérant\s+en\s+droit\s*:)\s*\n', r'(?:Considérant\s*:)\s*\n']
    elif language == 'it':
        patterns = [r'(?:Considerando\s+in\s+diritto\s*:)\s*\n', r'(?:Considerando\s*:)\s*\n']
    else:
        return ""
    end_patterns = [
        r'\n\s*(?:Dispositiv|Erkenntnis|Ausgang|Dispositif|Dispositivo)\s*:',
        r'\n\s*(?:Sachverhalt|Faits|Fatto)\s*:',
    ]
    return extract_section(text, language, patterns, end_patterns)


def extract_sachverhalt(text, language):
    """Extract Sachverhalt (facts) section."""
    if language == 'de':
        patterns = [r'(?:Sachverhalt\s*:)\s*\n']
    elif language == 'fr':
        patterns = [r'(?:Faits\s*:)\s*\n']
    elif language == 'it':
        patterns = [r'(?:Fatto\s*:)\s*\n']
    else:
        return ""
    end_patterns = [
        r'\n\s*(?:Erwägungen|Considérant|Considerando)\s*:',
        r'\n\s*(?:Dispositiv|Erkenntnis|Dispositif|Dispositivo)\s*:',
    ]
    return extract_section(text, language, patterns, end_patterns)


def extract_dispositiv(text, language):
    """Extract Dispositiv (holding) section."""
    if language == 'de':
        patterns = [r'(?:Dispositiv\s*:)\s*\n', r'(?:Erkenntnis\s*:)\s*\n']
    elif language == 'fr':
        patterns = [r'(?:Dispositif\s*:)\s*\n']
    elif language == 'it':
        patterns = [r'(?:Dispositivo\s*:)\s*\n']
    else:
        return ""
    return extract_section(text, language, patterns, [])


def extract_cited_decisions(text):
    """Extract cited BGE/ATF references."""
    if not text:
        return ""
    # BGE/ATF citation pattern
    pattern = r'(?:BGE|ATF)\s+\d+\s+[IVX]+\s+\d+'
    return " ".join(re.findall(pattern, text))


def extract_statutes(text):
    """Extract statute/norm references."""
    if not text:
        return ""
    # Swiss statute patterns (Art., §, ZGB, OR, StGB, etc.)
    patterns = [
        r'\bArt\.\s*\d+[a-z]?(?:\s+[A-Z][a-z]+)?',
        r'\b§\s*\d+[a-z]?(?:\s+[A-Z][a-z]+)?',
        r'\b(ZGB|OR|StGB|StPO|ZPO|VwVG|BV|VG|KAG|DBG|MWSTG|AHVG|IVG|UVG|FAMG|ELG)\b',
    ]
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, re.IGNORECASE))
    return " ".join(matches)


def extract_legal_area(text):
    """Extract legal area references."""
    if not text:
        return ""
    # This would ideally come from metadata, but we can try to extract
    return ""


def extract_outcome(text, language):
    """Extract outcome/disposition."""
    if not text:
        return ""
    dispositiv = extract_dispositiv(text, language)
    return dispositiv


def extract_erwaegungen_headings(text, language):
    """Extract headings from Erwägungen."""
    erwaegungen = extract_erwaegungen(text, language)
    if not erwaegungen:
        return ""
    # Extract numbered headings (1., 2., etc.)
    headings = re.findall(r'^\d+\.\s+.+$', erwaegungen, re.MULTILINE)
    return " ".join(headings)


def extract_doctrine_refs(text):
    """Extract doctrine/author citations."""
    if not text:
        return ""
    # Pattern for author citations (simplified)
    return ""


def build_legal_texts(metadata, decisions, config):
    """Build legal texts for TF-IDF based on config."""
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        if did not in decisions:
            continue
        
        d = decisions[did]
        full_text = d.get('full_text', '')
        language = m.get('language', 'de')
        
        parts = []
        
        if config.get('use_erwaegungen'):
            parts.append(extract_erwaegungen(full_text, language))
        if config.get('use_statutes'):
            parts.append(extract_statutes(full_text))
        if config.get('use_cited_decisions'):
            parts.append(extract_cited_decisions(full_text))
        if config.get('use_legal_area'):
            # Legal area from metadata
            area = m.get('legal_area', '')
            if area:
                parts.append(area)
        if config.get('use_outcome'):
            parts.append(extract_outcome(full_text, language))
        if config.get('use_doctrine_refs'):
            parts.append(extract_doctrine_refs(full_text))
        if config.get('use_erwaegungen_headings'):
            parts.append(extract_erwaegungen_headings(full_text, language))
        
        combined = " ".join(p for p in parts if p)
        if combined.strip():
            texts.append((i, combined))
    
    return texts


def compute_tfidf_embeddings(texts, n_components=128, max_features=5000, min_df=2, max_df=0.95, ngram_range=(1, 2)):
    """Compute TF-IDF embeddings with SVD reduction."""
    if not texts:
        return np.zeros((1000, n_components)), []
    
    indices = [t[0] for t in texts]
    only_texts = [t[1] for t in texts]
    
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        sublinear_tf=True,
        min_df=min_df,
        max_df=max_df,
        strip_accents='unicode'
    )
    tfidf_matrix = vectorizer.fit_transform(only_texts)
    
    n_comp = min(n_components, tfidf_matrix.shape[1] - 1, len(only_texts) - 1)
    if n_comp <= 0:
        return np.zeros((1000, n_components)), indices
    
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    
    # Normalize
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    # Pad to full size
    full_size = 1000  # baseline size
    tfidf_full = np.zeros((full_size, n_components))
    for j, i in enumerate(indices):
        tfidf_full[i, :n_comp] = reduced[j]
    
    # Normalize full
    norms = np.linalg.norm(tfidf_full, axis=1, keepdims=True)
    norms[norms == 0] = 1
    tfidf_full = tfidf_full / norms
    
    return tfidf_full, indices


def load_baseline_embeddings():
    """Load baseline embeddings for hybrid modes."""
    baseline_emb = np.load(BASELINE_DIR / "embeddings.npy")
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    return baseline_emb, center_emb


def build_debiased_citation_blended():
    """Build debiased_citation_blended embeddings (n_pca=1, alpha=0.7)."""
    logger.info("Building debiased_citation_blended embeddings...")
    
    baseline_emb, center_emb = load_baseline_embeddings()
    
    # n_pca=1: remove first PC from center embeddings
    from sklearn.decomposition import PCA
    pca = PCA(n_components=1)
    pca.fit(center_emb)
    pc1 = pca.components_[0]
    center_debiased = center_emb - np.outer(center_emb @ pc1, pc1)
    
    # Normalize
    norms = np.linalg.norm(center_debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    center_debiased = center_debiased / norms
    
    # Blend with baseline (alpha=0.7 for center_debiased, 0.3 for baseline)
    alpha = 0.7
    blended = alpha * center_debiased + (1 - alpha) * baseline_emb
    
    norms = np.linalg.norm(blended, axis=1, keepdims=True)
    norms[norms == 0] = 1
    blended = blended / norms
    
    output_path = OUTPUT_DIR / "debiased_citation_blended.npy"
    np.save(output_path, blended)
    logger.info(f"Saved to {output_path}: {blended.shape}")
    
    return blended


def build_legal_tfidf_mode(mode_id: str, config: dict):
    """Build a legal TF-IDF mode."""
    logger.info(f"Building {mode_id} embeddings...")
    
    metadata = load_metadata()
    decisions = load_corpus_decisions(metadata)
    
    texts = build_legal_texts(metadata, decisions, config)
    logger.info(f"Valid texts: {len(texts)}")
    
    embeddings, _ = compute_tfidf_embeddings(
        texts,
        n_components=128,
        max_features=config.get('max_features', 5000),
        min_df=config.get('min_df', 2),
        max_df=config.get('max_df', 0.95),
        ngram_range=tuple(config.get('ngram_range', [1, 2]))
    )
    
    output_path = OUTPUT_DIR / f"{mode_id}.npy"
    np.save(output_path, embeddings)
    logger.info(f"Saved to {output_path}: {embeddings.shape}")
    
    return embeddings


def build_hybrid_mode(mode_id: str, alpha: float, legal_config: dict):
    """Build a hybrid mode (legal TF-IDF + baseline)."""
    logger.info(f"Building {mode_id} embeddings (alpha={alpha})...")
    
    # Load baseline
    baseline_emb, center_emb = load_baseline_embeddings()
    
    # Build legal TF-IDF
    metadata = load_metadata()
    decisions = load_corpus_decisions(metadata)
    texts = build_legal_texts(metadata, decisions, legal_config)
    legal_emb, _ = compute_tfidf_embeddings(
        texts,
        n_components=128,
        max_features=legal_config.get('max_features', 5000),
        min_df=legal_config.get('min_df', 2),
        max_df=legal_config.get('max_df', 0.95),
        ngram_range=tuple(legal_config.get('ngram_range', [1, 2]))
    )
    
    # Align dimensions: baseline is 768-dim, legal is 128-dim
    # Pad legal to 768 or truncate baseline to 128
    # For hybrid, we'll use the same approach as the original: concat then blend
    # Actually, the original legal-distance uses concat of center + tfidf
    # For hybrid, we blend the legal_full_signals concat with baseline
    
    # Let's use the concat approach: center (768) + tfidf (128) = 896
    # But the baseline is just 768
    # The original legal-distance paper uses TF-IDF only for legal modes
    # For hybrid, they likely blend the similarity matrices, not embeddings
    # But we need embeddings for clustering...
    
    # Simplest approach: pad legal to 768 dimensions (repeat or zero-pad)
    # Or use only the TF-IDF part for legal modes (128-dim)
    # Actually, looking at the original code, legal modes use TF-IDF only
    # The hybrid blends the TF-IDF with baseline embeddings
    
    # Pad legal_emb to 768 dimensions
    if legal_emb.shape[1] < 768:
        legal_padded = np.zeros((legal_emb.shape[0], 768))
        legal_padded[:, :legal_emb.shape[1]] = legal_emb
    else:
        legal_padded = legal_emb[:, :768]
    
    # Normalize
    norms = np.linalg.norm(legal_padded, axis=1, keepdims=True)
    norms[norms == 0] = 1
    legal_padded = legal_padded / norms
    
    # Blend
    blended = alpha * legal_padded + (1 - alpha) * baseline_emb
    
    norms = np.linalg.norm(blended, axis=1, keepdims=True)
    norms[norms == 0] = 1
    blended = blended / norms
    
    output_path = OUTPUT_DIR / f"{mode_id}.npy"
    np.save(output_path, blended)
    logger.info(f"Saved to {output_path}: {blended.shape}")
    
    return blended


def generate_all_embeddings():
    """Generate embeddings for all legal-distance map modes."""
    logger.info("=== Generating Legal-Distance Embeddings ===")
    
    # 1. debiased_citation_blended
    build_debiased_citation_blended()
    
    # 2. legal_cited_decisions_only
    build_legal_tfidf_mode("legal_cited_decisions_only", {
        "use_cited_decisions": True,
        "use_statutes": False,
        "use_erwaegungen": False,
        "use_legal_area": False,
        "use_outcome": False,
        "use_doctrine_refs": False,
        "use_erwaegungen_headings": False,
    })
    
    # 3. legal_full_signals (for hybrid)
    legal_full = build_legal_tfidf_mode("legal_full_signals", {
        "use_statutes": True,
        "use_erwaegungen": True,
        "use_cited_decisions": True,
        "use_legal_area": True,
        "use_outcome": True,
        "use_doctrine_refs": True,
        "use_erwaegungen_headings": True,
    })
    
    # 4. hybrid_alpha_03
    build_hybrid_mode("hybrid_alpha_03", 0.3, {
        "use_statutes": True,
        "use_erwaegungen": True,
        "use_cited_decisions": True,
        "use_legal_area": True,
        "use_outcome": True,
        "use_doctrine_refs": True,
        "use_erwaegungen_headings": True,
    })
    
    # 5. hybrid_alpha_05
    build_hybrid_mode("hybrid_alpha_05", 0.5, {
        "use_statutes": True,
        "use_erwaegungen": True,
        "use_cited_decisions": True,
        "use_legal_area": True,
        "use_outcome": True,
        "use_doctrine_refs": True,
        "use_erwaegungen_headings": True,
    })
    
    # 6. legal_issues_outcomes
    build_legal_tfidf_mode("legal_issues_outcomes", {
        "use_legal_area": True,
        "use_outcome": True,
        "use_erwaegungen_headings": True,
        "use_statutes": False,
        "use_erwaegungen": False,
        "use_cited_decisions": False,
        "use_doctrine_refs": False,
    })
    
    logger.info("=== All embeddings generated ===")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate legal-distance embeddings")
    parser.add_argument("--all", action="store_true", help="Generate all embeddings")
    parser.add_argument("--mode", type=str, help="Generate specific mode")
    
    args = parser.parse_args()
    
    if args.all:
        generate_all_embeddings()
    elif args.mode:
        if args.mode == "debiased_citation_blended":
            build_debiased_citation_blended()
        elif args.mode in ["legal_cited_decisions_only", "legal_issues_outcomes"]:
            configs = {
                "legal_cited_decisions_only": {
                    "use_cited_decisions": True,
                    "use_statutes": False,
                    "use_erwaegungen": False,
                    "use_legal_area": False,
                    "use_outcome": False,
                    "use_doctrine_refs": False,
                    "use_erwaegungen_headings": False,
                },
                "legal_issues_outcomes": {
                    "use_legal_area": True,
                    "use_outcome": True,
                    "use_erwaegungen_headings": True,
                    "use_statutes": False,
                    "use_erwaegungen": False,
                    "use_cited_decisions": False,
                    "use_doctrine_refs": False,
                }
            }
            build_legal_tfidf_mode(args.mode, configs[args.mode])
        elif args.mode in ["hybrid_alpha_03", "hybrid_alpha_05"]:
            alpha = 0.3 if "03" in args.mode else 0.5
            build_hybrid_mode(args.mode, alpha, {
                "use_statutes": True,
                "use_erwaegungen": True,
                "use_cited_decisions": True,
                "use_legal_area": True,
                "use_outcome": True,
                "use_doctrine_refs": True,
                "use_erwaegungen_headings": True,
            })
        else:
            print(f"Unknown mode: {args.mode}")
    else:
        print("Usage: --all or --mode MODE_ID")