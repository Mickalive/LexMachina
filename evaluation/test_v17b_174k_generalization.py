#!/usr/bin/env python3
"""
Test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds)
generalizes to 174k fine-grained legal_area labels (214 labels).

Uses stratified subsample for efficiency.
"""
import json
import numpy as np
import logging
from pathlib import Path
from collections import Counter, defaultdict
from sklearn.cluster import KMeans
from sklearn.metrics import normalized_mutual_info_score
import sys

sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
METADATA_174K = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings/metadata.json")
V17B_RESULTS = Path("/home/runner/work/LexMachina/LexMachina/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_results.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/v17b_174k_generalization")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUBSAMPLE_SIZE = 15000  # Same as hierarchy_family_subsample in formal suite
SEED = 42

# Label normalization function (from v17b)
def normalize_legal_area(label: str) -> str:
    """Normalize legal area label to coarse category (v17b method)."""
    if not label or label == 'unknown':
        return 'unknown'
    
    label_lower = label.lower()
    
    # Tax law
    if any(kw in label_lower for kw in ['steuer', 'tax', 'impôt', 'tassa', 'steuerrecht']):
        return 'steuerrecht'
    
    # Social security
    if any(kw in label_lower for kw in ['sozialversicherung', 'social security', 'assurance sociale', 'assicurazione sociale', 'ahv', 'iv', 'faq', 'eog', 'el', 'bvg']):
        return 'sozialversicherungsrecht'
    
    # Administrative law
    if any(kw in label_lower for kw in ['verwaltung', 'administrative', 'amministrativo', 'verwaltungsrecht']):
        return 'verwaltungsrecht'
    
    # Constitutional / public law
    if any(kw in label_lower for kw in ['verfassungs', 'constitution', 'costituz', 'öffentliches recht', 'droit public', 'diritto pubblico', 'grundrecht', 'fundamental right', 'diritti fundamental']):
        return 'verfassungsrecht'
    
    # Civil law / contract / obligations
    if any(kw in label_lower for kw in ['obligationen', 'obligation', 'obbligaz', 'zivilrecht', 'droit civil', 'diritto civile', 'contract', 'vertrag', 'contratto', 'schadenersatz', 'dommage', 'danno']):
        return 'zivilrecht'
    
    # Criminal law
    if any(kw in label_lower for kw in ['straf', 'pénal', 'penale', 'strafrecht', 'droit pénal', 'diritto penale']):
        return 'strafrecht'
    
    # Labor / employment
    if any(kw in label_lower for kw in ['arbeits', 'labor', 'lavoro', 'employment', 'arbeitsrecht', 'droit du travail', 'diritto del lavoro']):
        return 'arbeitsrecht'
    
    # Family law
    if any(kw in label_lower for kw in ['familien', 'famille', 'famiglia', 'family', 'ehe', 'mariage', 'matrimonio']):
        return 'familienrecht'
    
    # Inheritance
    if any(kw in label_lower for kw in ['erb', 'succession', 'successione', 'inheritance']):
        return 'erbrecht'
    
    # Corporate / commercial
    if any(kw in label_lower for kw in ['gesellschaft', 'societ', 'company', 'corporate', 'commercial', 'handelsrecht', 'droit commercial', 'diritto commerciale']):
        return 'gesellschaftsrecht'
    
    # Insurance
    if any(kw in label_lower for kw in ['versicherung', 'assurance', 'assicurazione', 'insurance']):
        return 'versicherungsrecht'
    
    # Procedure
    if any(kw in label_lower for kw in ['prozess', 'procédure', 'procedimento', 'procedure', 'zpo', 'cpc', 'verfahrensrecht']):
        return 'prozessrecht'
    
    # Construction / real estate
    if any(kw in label_lower for kw in ['bau', 'construction', 'immobilien', 'real estate', 'bauwesen', 'immobilier']):
        return 'baurecht'
    
    # Competition / antitrust
    if any(kw in label_lower for kw in ['kartell', 'cartel', 'concorrenza', 'wettbewerb', 'competition']):
        return 'kartellrecht'
    
    # Intellectual property
    if any(kw in label_lower for kw in ['patent', 'marque', 'trademark', 'copyright', 'urheber', 'geistiges eigentum', 'propriété intellectuelle', 'proprietà intellettuale']):
        return 'immaterialguterrecht'
    
    # Foreigners / asylum
    if any(kw in label_lower for kw in ['ausländer', 'asylum', 'asile', 'asilo', 'foreigner', 'migration']):
        return 'ausländerrecht'
    
    # Default fallback: use first word
    return label_lower.split()[0] if label_lower.split() else 'other'

def load_174k_metadata():
    """Load 174k metadata with legal_area labels."""
    logger.info(f"Loading 174k metadata from {METADATA_174K}")
    with open(METADATA_174K) as f:
        metadata = json.load(f)
    
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    unique_raw = set(la for la in legal_areas if la != 'unknown')
    logger.info(f"Total decisions: {len(metadata)}")
    logger.info(f"Unique raw legal_area labels: {len(unique_raw)}")
    
    return metadata, legal_areas

def normalize_labels(legal_areas):
    """Apply v17b normalization to legal_area labels."""
    normalized = [normalize_legal_area(la) for la in legal_areas]
    unique_norm = set(n for n in normalized if n != 'unknown')
    logger.info(f"Unique normalized labels: {len(unique_norm)}")
    return normalized

def stratified_subsample(labels, embeddings, n_samples=SUBSAMPLE_SIZE, seed=SEED):
    """Stratified subsample by label."""
    np.random.seed(seed)
    unique_labels = list(set(l for l in labels if l != 'unknown'))
    n_labels = len(unique_labels)
    
    if n_labels == 0:
        return np.arange(len(labels))[:n_samples]
    
    per_label = n_samples // n_labels
    all_indices = []
    
    for label in unique_labels:
        label_indices = [i for i, l in enumerate(labels) if l == label]
        if len(label_indices) <= per_label:
            all_indices.extend(label_indices)
        else:
            all_indices.extend(np.random.choice(label_indices, per_label, replace=False))
    
    # If still need more, add from 'unknown' or randomly
    if len(all_indices) < n_samples:
        remaining = n_samples - len(all_indices)
        unknown_indices = [i for i, l in enumerate(labels) if l == 'unknown']
        if len(unknown_indices) >= remaining:
            all_indices.extend(np.random.choice(unknown_indices, remaining, replace=False))
        else:
            all_indices.extend(unknown_indices)
    
    # Trim if oversampled
    all_indices = all_indices[:n_samples]
    np.random.shuffle(all_indices)
    
    return np.array(all_indices)

def evaluate_hierarchy_coherence(embeddings, labels, name="", n_clusters_range=None):
    """Evaluate hierarchy coherence with KMeans."""
    if n_clusters_range is None:
        n_clusters_range = [3, 5, 10, 20, 30, 40, 50, 60]
    
    best_purity = 0.0
    best_nmi = 0.0
    best_k = 0
    
    for k in n_clusters_range:
        if k >= len(embeddings):
            continue
        try:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            pred = kmeans.fit_predict(embeddings)
            
            # Purity
            total_purity = 0
            total_size = 0
            for cid in set(pred):
                mask = pred == cid
                cluster_labels = [labels[i] for i in np.where(mask)[0] if labels[i] != 'unknown']
                if cluster_labels:
                    most_common = Counter(cluster_labels).most_common(1)[0][1]
                    total_purity += most_common
                    total_size += len(cluster_labels)
            
            purity = total_purity / total_size if total_size > 0 else 0
            nmi = normalized_mutual_info_score(labels, pred)
            
            if purity > best_purity:
                best_purity = purity
                best_nmi = nmi
                best_k = k
        except Exception as e:
            logger.warning(f"KMeans failed for k={k}: {e}")
    
    return {
        'best_purity': best_purity,
        'best_nmi': best_nmi,
        'best_k': best_k
    }

def evaluate_zoom_coherence(embeddings, labels, name=""):
    """Evaluate zoom coherence (coarse vs fine clustering)."""
    # Coarse: 4 clusters (branch level)
    kmeans_coarse = KMeans(n_clusters=4, random_state=42, n_init=10)
    coarse_pred = kmeans_coarse.fit_predict(embeddings)
    
    coarse_purity = 0
    coarse_size = 0
    for cid in set(coarse_pred):
        mask = coarse_pred == cid
        cluster_labels = [labels[i] for i in np.where(mask)[0] if labels[i] != 'unknown']
        if cluster_labels:
            most_common = Counter(cluster_labels).most_common(1)[0][1]
            coarse_purity += most_common
            coarse_size += len(cluster_labels)
    coarse_purity = coarse_purity / coarse_size if coarse_size > 0 else 0
    
    # Fine: 30 clusters
    kmeans_fine = KMeans(n_clusters=30, random_state=42, n_init=10)
    fine_pred = kmeans_fine.fit_predict(embeddings)
    
    fine_purity = 0
    fine_size = 0
    for cid in set(fine_pred):
        mask = fine_pred == cid
        cluster_labels = [labels[i] for i in np.where(mask)[0] if labels[i] != 'unknown']
        if cluster_labels:
            most_common = Counter(cluster_labels).most_common(1)[0][1]
            fine_purity += most_common
            fine_size += len(cluster_labels)
    fine_purity = fine_purity / fine_size if fine_size > 0 else 0
    
    improvement_pct = (fine_purity - coarse_purity) / coarse_purity * 100 if coarse_purity > 0 else 0
    
    return {
        'coarse_purity': coarse_purity,
        'fine_purity': fine_purity,
        'improvement_pct': improvement_pct
    }

def evaluate_legal_area_clustering(embeddings, labels, name=""):
    """Evaluate legal area clustering."""
    unique_labels = len(set(l for l in labels if l != 'unknown'))
    if unique_labels < 2:
        return {'overall_purity': 0, 'nmi': 0, 'num_areas': unique_labels}
    
    k = min(30, unique_labels)
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    pred = kmeans.fit_predict(embeddings)
    
    # Purity
    total_purity = 0
    total_size = 0
    for cid in set(pred):
        mask = pred == cid
        cluster_labels = [labels[i] for i in np.where(mask)[0] if labels[i] != 'unknown']
        if cluster_labels:
            most_common = Counter(cluster_labels).most_common(1)[0][1]
            total_purity += most_common
            total_size += len(cluster_labels)
    
    purity = total_purity / total_size if total_size > 0 else 0
    nmi = normalized_mutual_info_score(labels, pred)
    
    return {
        'overall_purity': purity,
        'nmi': nmi,
        'num_areas': unique_labels
    }

def main():
    logger.info("=" * 70)
    logger.info("TEST: v17b LABEL NORMALIZATION GENERALIZATION TO 174k LEGAL_AREA LABELS")
    logger.info("=" * 70)
    
    # Load 174k metadata
    metadata, raw_labels = load_174k_metadata()
    
    # Normalize labels using v17b method
    norm_labels = normalize_labels(raw_labels)
    
    # Load v17b reference results (from 1148-decision sample)
    with open(V17B_RESULTS) as f:
        v17b_ref = json.load(f)
    
    # Representations to test
    representations = {
        'cited_decisions_tfidf': 'cited_decisions_tfidf.npy',
        'outcome_tfidf': 'outcome_tfidf.npy',
        'regeste_tfidf': 'regeste_tfidf.npy',
        'full_text_tfidf_light': 'full_text_tfidf_light.npy',
        'cited_decisions_tfidf_outcome_hybrid_0.5': 'cited_decisions_tfidf_outcome_hybrid_0.5.npy',
        'cited_decisions_tfidf_outcome_hybrid_0.7': 'cited_decisions_tfidf_outcome_hybrid_0.7.npy',
        'regeste_full_text_hybrid_0.5': 'regeste_full_text_hybrid_0.5.npy',
        'regeste_full_text_hybrid_0.7': 'regeste_full_text_hybrid_0.7.npy',
    }
    
    results = {}
    
    for rep_name, fname in representations.items():
        logger.info(f"\n--- Testing {rep_name} ---")
        
        path = EMBEDDINGS_DIR / fname
        if not path.exists():
            logger.warning(f"Embedding file not found: {path}")
            continue
        
        embeddings = np.load(path, mmap_mode='r')
        # Trim to match metadata (175440 -> 173963)
        if embeddings.shape[0] > len(metadata):
            embeddings = embeddings[:len(metadata)]
            logger.info(f"Trimmed embeddings to {embeddings.shape[0]}")
        
        # Stratified subsample
        sub_indices = stratified_subsample(raw_labels, embeddings, SUBSAMPLE_SIZE, SEED)
        logger.info(f"  Subsample size: {len(sub_indices)}")
        
        sub_embeddings = embeddings[sub_indices]
        sub_raw_labels = [raw_labels[i] for i in sub_indices]
        sub_norm_labels = [norm_labels[i] for i in sub_indices]
        
        # Evaluate with RAW labels (214 unique)
        logger.info("  Evaluating with RAW legal_area labels (214 labels)...")
        raw_hierarchy = evaluate_hierarchy_coherence(sub_embeddings, sub_raw_labels, rep_name)
        raw_zoom = evaluate_zoom_coherence(sub_embeddings, sub_raw_labels, rep_name)
        raw_legal_area = evaluate_legal_area_clustering(sub_embeddings, sub_raw_labels, rep_name)
        
        # Evaluate with NORMALIZED labels (v17b: ~54 labels)
        logger.info("  Evaluating with NORMALIZED legal_area labels (v17b method)...")
        norm_hierarchy = evaluate_hierarchy_coherence(sub_embeddings, sub_norm_labels, rep_name)
        norm_zoom = evaluate_zoom_coherence(sub_embeddings, sub_norm_labels, rep_name)
        norm_legal_area = evaluate_legal_area_clustering(sub_embeddings, sub_norm_labels, rep_name)
        
        # Compute ratios (normalized / raw)
        hierarchy_ratio = norm_hierarchy['best_purity'] / raw_hierarchy['best_purity'] if raw_hierarchy['best_purity'] > 0 else 0
        zoom_fine_ratio = norm_zoom['fine_purity'] / raw_zoom['fine_purity'] if raw_zoom['fine_purity'] > 0 else 0
        legal_area_ratio = norm_legal_area['overall_purity'] / raw_legal_area['overall_purity'] if raw_legal_area['overall_purity'] > 0 else 0
        
        # Compare with v17b reference (1148 decisions)
        v17b_ref_rep = v17b_ref['per_representation'].get(rep_name, {})
        v17b_hierarchy_ratio = v17b_ref_rep.get('purity_ratios_norm_over_raw', {}).get('hierarchy', 0)
        v17b_zoom_ratio = v17b_ref_rep.get('purity_ratios_norm_over_raw', {}).get('zoom_fine', 0)
        v17b_legal_area_ratio = v17b_ref_rep.get('purity_ratios_norm_over_raw', {}).get('legal_area', 0)
        
        results[rep_name] = {
            'raw': {
                'hierarchy_coherence': raw_hierarchy,
                'zoom_coherence': raw_zoom,
                'legal_area_clustering': raw_legal_area,
            },
            'normalized': {
                'hierarchy_coherence': norm_hierarchy,
                'zoom_coherence': norm_zoom,
                'legal_area_clustering': norm_legal_area,
            },
            'purity_ratios_norm_over_raw': {
                'hierarchy': hierarchy_ratio,
                'zoom_fine': zoom_fine_ratio,
                'legal_area': legal_area_ratio,
            },
            'v17b_reference_ratios': {
                'hierarchy': v17b_hierarchy_ratio,
                'zoom_fine': v17b_zoom_ratio,
                'legal_area': v17b_legal_area_ratio,
            },
            'generalization': {
                'hierarchy_ratio_close': abs(hierarchy_ratio - v17b_hierarchy_ratio) < 0.1,
                'zoom_fine_ratio_close': abs(zoom_fine_ratio - v17b_zoom_ratio) < 0.1,
                'legal_area_ratio_close': abs(legal_area_ratio - v17b_legal_area_ratio) < 0.1,
                'all_close': (abs(hierarchy_ratio - v17b_hierarchy_ratio) < 0.1 and
                             abs(zoom_fine_ratio - v17b_zoom_ratio) < 0.1 and
                             abs(legal_area_ratio - v17b_legal_area_ratio) < 0.1),
            },
            'norm_num_areas': len(set(n for n in norm_labels if n != 'unknown')),
            'raw_num_areas': len(set(l for l in raw_labels if l != 'unknown')),
        }
        
        logger.info(f"  RAW: hierarchy_purity={raw_hierarchy['best_purity']:.4f}, zoom_fine={raw_zoom['fine_purity']:.4f}, legal_area={raw_legal_area['overall_purity']:.4f}")
        logger.info(f"  NORM: hierarchy_purity={norm_hierarchy['best_purity']:.4f}, zoom_fine={norm_zoom['fine_purity']:.4f}, legal_area={norm_legal_area['overall_purity']:.4f}")
        logger.info(f"  Ratios: hierarchy={hierarchy_ratio:.4f}, zoom_fine={zoom_fine_ratio:.4f}, legal_area={legal_area_ratio:.4f}")
        logger.info(f"  v17b ref: hierarchy={v17b_hierarchy_ratio:.4f}, zoom_fine={v17b_zoom_ratio:.4f}, legal_area={v17b_legal_area_ratio:.4f}")
        logger.info(f"  Generalization: {'PASS' if results[rep_name]['generalization']['all_close'] else 'FAIL'}")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("V17B 174K GENERALIZATION TEST SUMMARY")
    logger.info("=" * 70)
    
    all_pass = True
    for rep_name, res in results.items():
        gen = res['generalization']
        status = "PASS" if gen['all_close'] else "FAIL"
        if not gen['all_close']:
            all_pass = False
        logger.info(f"{rep_name}: {status} (hierarchy={gen['hierarchy_ratio_close']}, zoom_fine={gen['zoom_fine_ratio_close']}, legal_area={gen['legal_area_ratio_close']})")
    
    logger.info(f"\nOverall: {'GENERALIZES' if all_pass else 'DOES NOT GENERALIZE'}")
    
    # Save results
    from datetime import datetime
    output = {
        'run_id': f'v17b_174k_generalization_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'timestamp': datetime.now().isoformat(),
        'v17b_reference_run_id': v17b_ref.get('run_id'),
        'corpus_size': len(metadata),
        'subsample_size': SUBSAMPLE_SIZE,
        'raw_num_areas': len(set(l for l in raw_labels if l != 'unknown')),
        'normalized_num_areas': len(set(n for n in norm_labels if n != 'unknown')),
        'results': results,
        'overall_generalization': all_pass,
    }
    
    output_path = OUTPUT_DIR / f"v17b_174k_generalization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to {output_path}")
    
    return results, all_pass

if __name__ == "__main__":
    main()
