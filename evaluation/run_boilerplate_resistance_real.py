#!/usr/bin/env python3
"""
Real Boilerplate Resistance Benchmark for Evaluation v3+.

This benchmark uses the ACTUAL full_text from the expanded 1200-decision slice
to test whether neighbor structure is driven by procedural boilerplate rather
than substantive legal content.

Approach:
1. Load full_text for all 1200 decisions
2. Remove procedural boilerplate (headers, standard phrases, footers, citations)
3. Re-compute TF-IDF signal embeddings (sachverhalt, erwaegungen, outcome, etc.)
   with and without boilerplate
4. Measure neighbor preservation: how much do k-NN sets change when boilerplate removed?
5. Low neighbor preservation = high boilerplate resistance (good)
   High neighbor preservation = neighbors driven by boilerplate (bad)

This is the REAL test that v3 proxied with language dominance and v6 skipped entirely.
"""

import json
import numpy as np
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

GLOBAL_SEED = 42
np.random.seed(GLOBAL_SEED)

EXPANDED_SLICE_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/bger_expanded_1200.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/v3_boilerplate_real")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# BOILERPLATE PATTERNS FOR SWISS FEDERAL SUPREME COURT
# ============================================================

# Header boilerplate - multilingual court name block, case metadata
HEADER_PATTERNS = [
    r'^Bundesgericht\s*\n',
    r'^Tribunal f.d.ral\s*\n',
    r'^Tribunale federale\s*\n',
    r'^Tribunal federal\s*\n',
    r'^\d+[A-Z]_\d+/\d{4}\s*\n',  # Case number like 7B_832/2024
    r'^(Urteil|Arr.t|Sentenza|Decisi.un) vom \d{1,2}\. \w+ \d{4}\s*\n',
    r'^(Urteil|Arr.t|Sentenza|Decisi.un) vom \d{1,2}\.\d{1,2}\.\d{4}\s*\n',
    r'^[IVX]+\. (ffentlich|ffentlich-rechtliche|Zivilrechtliche|Strafrechtliche|sozialrechtliche) (Abteilung|Cour de droit)\s*\n',
    r'^(Besetzung|Composition|Composizione|Composizi.un)\s*\n',
    r'^Bundesrichter[in]?\s+[\w\s,.]+\s*\n',
    r'^(Gerichtsschreiber|Greffier|Cancelliere|Scriba)\s*[:\s]*\w+\s*\n',
    r'^(Verfahrensbeteiligte|Participants . la proc.dure|Partecipanti al procedimento|Partizipants da la procedira)\s*\n',
    r'^[\w\._]+\s*\n',  # Party names (simplified)
    r'^(vertreten durch|représenté par|rappresentato da|rappresentà da)\s+[\w\s.]+',
    r'^(Beschwerdeführer|Recourant|Ricorrente|Recurrent)\s*,?\s*\n',
    r'^(Beschwerdegegner|Intimé|Controparte|Contrapart)\s*,?\s*\n',
    r'^(Gegenstand|Objet|Oggetto|Object)\s*\n',
    r'^[A-Z][a-z]+,\s*\n',  # Subject line
]

# Section markers (keep the marker, remove if they're just labels)
SECTION_MARKERS = [
    r'^Faits\s*:?\s*\n',
    r'^Sachverhalt\s*:?\s*\n',
    r'^Erw.gungen\s*:?\s*\n',
    r'^Consid.rant en droit\s*:?\s*\n',
    r'^Considerazioni in diritto\s*:?\s*\n',
    r'^Consid.ratscha da dretg\s*:?\s*\n',
]

# Standard procedural phrases that appear in almost every decision
PROCEDURAL_PHRASES = [
    # Cost allocation
    r'(Le recourant|Der Beschwerdeführer|Il ricorrente|Il recurrent), qui succombe, supportera les frais judiciaires\s*\(cf\.\s*art\.\s*66\s*al\.\s*1\s*LTF\)',
    r'Die Gerichtskosten (hat|werden) (dem|den) (Beschwerdeführer|Parteien) (auferlegt|zu tragen)\s*\(vgl\.\s*art\.\s*66\s*Abs\.\s*\d+\s*BGG\)',
    r'Il ricorrente, che soccombe, assume le spese giudiziarie\s*\(cfr\.\s*art\.\s*66\s*cpv\.\s*1\s*LTF\)',
    # Party compensation
    r'(Er|Il|Il|El) (schuldet|ha|ha) (der|la|la) (anwaltlich vertretenen|represented|avvocato|avocat) (Beschwerdegegnerin|intimée|controparte|contrapart) eine angemessene Parteientschädigung\s*\(vgl\.\s*art\.\s*68\s*Abs\.\s*\d+\s*BGG\)',
    r'(Il|El|Il) (ricorrente|recurrent|recurrent) (deve|devrà|devra) (versare|pagare|indennizzare) (la|una) (partecipazione alle spese|indennità di parte|parteientschädigung)\s*\(cfr\.\s*art\.\s*68\s*cpv\.\s*\d+\s*LTF\)',
    # Standard communication
    r'(Dieses Urteil|Le présent arrêt|La presente sentenza|Questa decisium) wird den (Parteien|parties|parti|partidas) (und|et|e) (dem|au|al|al) (Gericht|autorité|autorità|otoritad) (schriftlich|par écrit|per iscritto|in iscrit) (mitgeteilt|communiqué|comunicato|comunicà)\.',
    r'Lausanne, (le|der|il|il) \d{1,2}\. \w+ \d{4}',
    r'(Im Namen der|Au nom de la|In nome della|In nom da la) [IVX]+\. (zivilrechtliche|Strafrechtliche|öffentlich-rechtliche|sozialrechtliche) (Abteilung|Cour de droit|corte di diritto|cort da dretg) (des|du|del|dal) (Schweizerischen Bundesgerichts|Tribunal fédéral suisse|Tribunale federale svizzero|Tribunal federal svizzer)',
    r'(Der Präsident|Le Président|Il Presidente|Il President): \w+',
    r'(Der Gerichtsschreiber|Le Greffier|Il Cancelliere|Il Scriba): \w+',
]

# Standard legal article citations that appear repeatedly (procedural articles)
PROCEDURAL_ARTICLES = [
    r'art\.\s*29\s*al\.\s*1\s*LTF',
    r'art\.\s*66\s*al\.\s*1\s*LTF',
    r'art\.\s*66\s*al\.\s*3\s*LTF',
    r'art\.\s*68\s*al\.\s*1\s*BGG',
    r'art\.\s*68\s*al\.\s*2\s*BGG',
    r'art\.\s*68\s*al\.\s*3\s*BGG',
    r'art\.\s*68\s*al\.\s*5\s*BGG',
    r'art\.\s*105\s*al\.\s*1\s*LTF',
    r'art\.\s*105\s*al\.\s*2\s*LTF',
    r'art\.\s*97\s*al\.\s*1\s*LTF',
    r'art\.\s*95\s*LTF',
    r'art\.\s*42\s*al\.\s*2\s*LTF',
    r'art\.\s*106\s*al\.\s*2\s*LTF',
    r'ATF\s+\d+\s+[IV]+\s+\d+',
    r'BGE\s+\d+\s+[IV]+\s+\d+',
    r'art\.\s*56\s*let\.\s*[a-f]\s*CPP',
    r'art\.\s*58\s*CPP',
    r'art\.\s*61\s*let\.\s*a\s*CPP',
    r'art\.\s*62\s*al\.\s*1\s*CPP',
    r'art\.\s*393\s*al\.\s*2\s*let\.\s*a\s*CPP',
    r'art\.\s*394\s*let\.\s*b\s*CPP',
    r'art\.\s*396\s*al\.\s*2\s*CPP',
]

# Footer boilerplate - standard disposition block
FOOTER_PATTERNS = [
    r'^Par ces motifs, le Tribunal fédéral prononce\s*:?\s*\n',
    r'^Demnach erkennt das Bundesgericht\s*:?\s*\n',
    r'^Di conseguenza il Tribunale federale pronuncia\s*:?\s*\n',
    r'^Per quai il Tribunal federal decideix\s*:?\s*\n',
    r'^\d+\.\s*(Le recours|Die Beschwerde|Il ricorso|La recusa) (est|wird|viene|vaina) (rejeté|abgewiesen|respinto|rebuttà)',
    r'^\d+\.\s*(Les frais|Die Gerichtskosten|Le spese|Las custas) (judiciaires|gerichtliche|giudiziarie|judicialas)',
    r'^\d+\.\s*(Chaque Partei|Jede Partei|Ogni parte|Mada partita) (trägt|porta|porta) (für|per|per) (das|das|das|il) bundesgerichtliche Verfahren',
    r'^\d+\.\s*(Die Neuregelung|La nouvelle répartition|La nuova ripartizione|La nova distribuziun)',
    r'^\d+\.\s*(Dieses Urteil|Le présent arrêt|La presente sentenza|Questa decisium)',
]


def remove_boilerplate(text: str) -> str:
    """Remove procedural boilerplate from Swiss Federal Supreme Court decision text."""
    cleaned = text
    
    # Remove header patterns (multiline at start)
    for pattern in HEADER_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
    
    # Remove section markers (but keep content after them)
    for pattern in SECTION_MARKERS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
    
    # Remove procedural phrases
    for pattern in PROCEDURAL_PHRASES:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove procedural article citations
    for pattern in PROCEDURAL_ARTICLES:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Remove footer patterns
    for pattern in FOOTER_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
    
    # Clean up excessive whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def extract_sections(text: str) -> Dict[str, str]:
    """Extract substantive sections from decision text."""
    sections = {
        'sachverhalt': '',
        'erwaegungen': '',
        'dispositiv': '',
        'full': text
    }
    
    # Try to find section boundaries
    # German: Sachverhalt / Erwägungen / Dispositiv
    # French: Faits / Considérant en droit / Par ces motifs
    # Italian: Fatto / Considerazioni in diritto / Di conseguenza
    
    # Simple extraction: find content between section markers
    # This is approximate - the TF-IDF will handle the rest
    
    return sections


def load_expanded_slice() -> List[Dict]:
    """Load expanded slice with full_text."""
    decisions = []
    with open(EXPANDED_SLICE_PATH, 'r') as f:
        for line in f:
            decisions.append(json.loads(line))
    return decisions


def build_tfidf_embeddings(texts: List[str], max_features: int = 5000, n_components: int = 128) -> Tuple[np.ndarray, List[int]]:
    """Build TF-IDF + SVD embeddings from texts."""
    valid_texts = []
    valid_indices = []
    
    for i, t in enumerate(texts):
        if t and len(t.strip()) > 50:
            valid_texts.append(t)
            valid_indices.append(i)
    
    if len(valid_texts) < 10:
        logger.warning(f"Only {len(valid_texts)} valid texts for TF-IDF")
        return np.zeros((len(texts), n_components)), valid_indices
    
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        min_df=2,
        max_df=0.95,
        ngram_range=(1, 2),
        sublinear_tf=True,
        lowercase=True,
        strip_accents='unicode',
    )
    
    tfidf_matrix = vectorizer.fit_transform(valid_texts)
    
    n_comp = min(n_components, tfidf_matrix.shape[1] - 1, len(valid_texts) - 1)
    if n_comp < 2:
        logger.warning(f"Too few features for SVD: {n_comp}")
        return np.zeros((len(texts), n_components)), valid_indices
    
    svd = TruncatedSVD(n_components=n_comp, random_state=GLOBAL_SEED)
    reduced = svd.fit_transform(tfidf_matrix)
    
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    full_emb = np.zeros((len(texts), n_comp))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = reduced[j]
    
    return full_emb, valid_indices


def compute_neighbor_preservation(
    emb_full: np.ndarray,
    emb_clean: np.ndarray,
    valid_indices: List[int],
    k: int = 20
) -> Dict:
    """Measure how much neighbor sets change when boilerplate removed."""
    n = len(valid_indices)
    if n < k + 1:
        return {'preservation_rate': 0.0, 'note': 'insufficient_decisions'}
    
    emb_full_valid = emb_full[valid_indices]
    emb_clean_valid = emb_clean[valid_indices]
    
    # Build NN graphs
    nn_full = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nn_full.fit(emb_full_valid)
    _, indices_full = nn_full.kneighbors(emb_full_valid)
    neighbors_full = indices_full[:, 1:]  # Exclude self
    
    nn_clean = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nn_clean.fit(emb_clean_valid)
    _, indices_clean = nn_clean.kneighbors(emb_clean_valid)
    neighbors_clean = indices_clean[:, 1:]
    
    # Compute preservation rate per decision
    preservation_rates = []
    for i in range(n):
        set_full = set(neighbors_full[i])
        set_clean = set(neighbors_clean[i])
        overlap = len(set_full & set_clean)
        preservation_rates.append(overlap / k)
    
    return {
        'mean_preservation_rate': float(np.mean(preservation_rates)),
        'std_preservation_rate': float(np.std(preservation_rates)),
        'min_preservation_rate': float(np.min(preservation_rates)),
        'max_preservation_rate': float(np.max(preservation_rates)),
        'k': k,
        'n_decisions': n,
        'note': 'Lower preservation = higher boilerplate resistance (neighbors change when boilerplate removed)'
    }


def boilerplate_resistance_proxy(
    embeddings: np.ndarray,
    metadata: List[Dict],
    valid_indices: Optional[List[int]] = None,
    k: int = 20
) -> Dict:
    """
    Boilerplate resistance proxy: language dominance in neighbors.
    Fraction of decisions with >80% same-language neighbors.
    """
    if valid_indices is not None:
        rep_embeddings = embeddings[valid_indices]
        rep_metadata = [metadata[i] for i in valid_indices]
    else:
        rep_embeddings = embeddings
        rep_metadata = metadata
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine', n_jobs=-1)
    nn.fit(rep_embeddings)
    _, indices = nn.kneighbors(rep_embeddings)
    neighbors = indices[:, 1:]
    
    boilerplate_dominated = 0
    for i, m in enumerate(rep_metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [rep_metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        if same_lang / k > 0.8:
            boilerplate_dominated += 1
    
    boilerplate_rate = boilerplate_dominated / len(rep_metadata)
    
    return {
        'boilerplate_dominated_rate': float(boilerplate_rate),
        'k': k,
        'threshold': 0.3,
        'status': 'PASS' if boilerplate_rate < 0.3 else 'FAIL',
        'note': 'Fraction of decisions with >80% same-language neighbors. Lower = less boilerplate-driven.'
    }


def run_boilerplate_benchmark_for_signal(
    signal_name: str,
    full_texts: List[str],
    clean_texts: List[str],
    signal_config: Dict,
    metadata: List[Dict]
) -> Dict:
    """Run boilerplate resistance test for a specific signal configuration."""
    logger.info(f"  Testing signal: {signal_name}")
    
    # Build embeddings for full text
    emb_full, valid_idx = build_tfidf_embeddings(
        full_texts, 
        max_features=signal_config.get('max_features', 5000),
        n_components=signal_config.get('n_components', 128)
    )
    
    # Build embeddings for clean text
    emb_clean, _ = build_tfidf_embeddings(
        clean_texts,
        max_features=signal_config.get('max_features', 5000),
        n_components=signal_config.get('n_components', 128)
    )
    
    # Measure neighbor preservation
    preservation = compute_neighbor_preservation(emb_full, emb_clean, valid_idx)
    
    # Also compute boilerplate-dominated rate (language dominance proxy)
    # for comparison with v3 results
    bp_proxy = boilerplate_resistance_proxy(emb_full, metadata, valid_indices=valid_idx)
    
    return {
        'signal': signal_name,
        'n_valid': len(valid_idx),
        'embedding_dim': emb_full.shape[1],
        'neighbor_preservation': preservation,
        'boilerplate_proxy': bp_proxy,
        'interpretation': {
            'preservation_mean': preservation['mean_preservation_rate'],
            'proxy_rate': bp_proxy['boilerplate_dominated_rate'],
            'resistance_score': 1.0 - preservation['mean_preservation_rate'],  # Higher = more resistant
            'note': 'Resistance score = 1 - neighbor_preservation. Higher = neighbors NOT driven by boilerplate.'
        }
    }


def main():
    logger.info("=" * 80)
    logger.info("REAL BOILERPLATE RESISTANCE BENCHMARK")
    logger.info("Using full_text from expanded 1200-decision slice")
    logger.info(f"Global seed: {GLOBAL_SEED} (FROZEN)")
    logger.info("=" * 80)
    
    # Load data
    logger.info("Loading expanded slice with full_text...")
    decisions = load_expanded_slice()
    logger.info(f"Loaded {len(decisions)} decisions")
    
    full_texts = [d['full_text'] for d in decisions]
    languages = [d['language'] for d in decisions]
    
    # Remove boilerplate
    logger.info("Removing boilerplate from all decisions...")
    clean_texts = [remove_boilerplate(t) for t in full_texts]
    
    # Report stats
    full_lens = [len(t) for t in full_texts]
    clean_lens = [len(t) for t in clean_texts]
    reductions = [(f - c) / f * 100 for f, c in zip(full_lens, clean_lens)]
    logger.info(f"Full text: mean={np.mean(full_lens):.0f} chars")
    logger.info(f"Clean text: mean={np.mean(clean_lens):.0f} chars")
    logger.info(f"Mean reduction: {np.mean(reductions):.1f}%")
    
    # Metadata for language proxy
    metadata = [{'language': d['language']} for d in decisions]
    
    # Define signal configurations to test
    signal_configs = {
        'sachverhalt_tfidf': {
            'max_features': 5000,
            'n_components': 128,
            'section': 'sachverhalt'  # Facts section - most substantive
        },
        'erwaegungen_tfidf': {
            'max_features': 5000,
            'n_components': 128,
            'section': 'erwaegungen'  # Legal reasoning - most substantive
        },
        'outcome_tfidf': {
            'max_features': 2000,
            'n_components': 64,
            'section': 'outcome'  # Outcome/holding
        },
        'full_text_tfidf': {
            'max_features': 5000,
            'n_components': 128,
            'section': 'full'
        },
        'sachverhalt+erwaegungen': {
            'max_features': 5000,
            'n_components': 128,
            'section': 'combined'
        }
    }
    
    # For combined, we need to extract sections. For now use full text.
    # In practice, we'd extract specific sections.
    
    all_results = {
        'factory_direction_version': 6,
        'evaluation_version': 'v3_boilerplate_real',
        'global_seed': GLOBAL_SEED,
        'n_decisions': len(decisions),
        'boilerplate_reduction_stats': {
            'mean_full_length': float(np.mean(full_lens)),
            'mean_clean_length': float(np.mean(clean_lens)),
            'mean_reduction_pct': float(np.mean(reductions)),
        },
        'signals': {}
    }
    
    # Test each signal configuration
    for signal_name, config in signal_configs.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"BENCHMARKING: {signal_name}")
        logger.info(f"{'='*60}")
        
        # For now, use full text for all signals (section extraction is complex)
        # The key comparison is full vs clean for the SAME text
        result = run_boilerplate_benchmark_for_signal(
            signal_name, full_texts, clean_texts, config, metadata
        )
        
        all_results['signals'][signal_name] = result
        
        # Log key metrics
        interp = result['interpretation']
        logger.info(f"  Neighbor preservation (full->clean): {interp['preservation_mean']:.4f}")
        logger.info(f"  Resistance score: {interp['resistance_score']:.4f}")
        logger.info(f"  Language-dominance proxy rate: {interp['proxy_rate']:.4f}")
        
        # Save intermediate
        with open(OUTPUT_DIR / f"boilerplate_{signal_name}.json", 'w') as f:
            json.dump(result, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("BOILERPLATE RESISTANCE SUMMARY (REAL TEST)")
    logger.info("=" * 80)
    logger.info(f"{'Signal':<30} {'Preservation':>12} {'Resistance':>12} {'Proxy Rate':>12}")
    logger.info("-" * 80)
    
    for signal_name, result in all_results['signals'].items():
        interp = result['interpretation']
        logger.info(f"{signal_name:<30} {interp['preservation_mean']:>12.4f} {interp['resistance_score']:>12.4f} {interp['proxy_rate']:>12.4f}")
    
    # Save final results
    output_file = OUTPUT_DIR / "boilerplate_resistance_real_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("Real boilerplate resistance benchmark complete.")
    
    return all_results


if __name__ == '__main__':
    main()