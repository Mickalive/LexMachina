#!/usr/bin/env python3
"""
Test v17b Label Normalization Generalization at 174k Scale.

The v17b label normalization maps equivalent legal areas across languages 
(e.g., "Vertragsrecht" (DE), "Droit des contrats" (FR), "Diritto contrattuale" (IT))
to a common normalized label. This test evaluates whether the 15-25% purity gain
reported at smaller scale generalizes to 174k fine-grained legal_area labels.
"""

import json
import numpy as np
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter, defaultdict
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import normalized_mutual_info_score
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
METADATA_FILE = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k/embeddings/metadata.json")
EMBEDDINGS_DIR = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k/embeddings")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Test embeddings - focus on production defaults
TEST_EMBEDDINGS = [
    "cited_decisions_tfidf.npy",
    "cited_decisions_tfidf_outcome_hybrid_0.5.npy",
    "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
    "center_projected_64dim",  # Will need to check if available
]

# v17b label normalization mapping (DE/FR/IT equivalents)
# This is a representative mapping based on Swiss legal taxonomy
LABEL_NORMALIZATION_MAP = {
    # Contract law
    "Vertragsrecht": "contract_law",
    "Droit des contrats": "contract_law",
    "Diritto contrattuale": "contract_law",
    "Droit des obligations (en général)": "contract_law",
    "Haftpflichtrecht": "liability_law",
    "Droit de la responsabilité": "liability_law",
    
    # Civil procedure
    "Zivilprozess": "civil_procedure",
    "Procédure civile": "civil_procedure",
    "Procedura civile": "civil_procedure",
    "Schiedsgerichtsbarkeit": "arbitration",
    
    # Family law
    "Familienrecht": "family_law",
    "Droit de la famille": "family_law",
    "Diritto di famiglia": "family_law",
    "Droit des successions": "inheritance_law",
    "Diritto successorio": "inheritance_law",
    "Erbrecht": "inheritance_law",
    
    # Debt enforcement & bankruptcy
    "Schuldbetreibungs- und Konkursrecht": "debt_enforcement_bankruptcy",
    "Droit des poursuites et faillites": "debt_enforcement_bankruptcy",
    "Diritto delle esecuzioni e del fallimento": "debt_enforcement_bankruptcy",
    "Schuldbetreibungs- und Konkurskammer": "debt_enforcement_bankruptcy",
    
    # Criminal law
    "Strafprozess": "criminal_procedure",
    "Procédure pénale": "criminal_procedure",
    "Straftaten": "criminal_offenses",
    "Infractions": "criminal_offenses",
    "Strafrecht (allgemein)": "criminal_law_general",
    
    # Public law - citizenship & foreigners
    "Bürgerrecht und Ausländerrecht": "citizenship_foreigners_law",
    "Droit de cité et droit des étrangers": "citizenship_foreigners_law",
    "Cittadinanza e diritto degli stranieri": "citizenship_foreigners_law",
    
    # Public law - public finance & tax
    "Öffentliche Finanzen & Abgaberecht": "public_finance_tax_law",
    "Finanze pubbliche & diritto tributario": "public_finance_tax_law",
    "Droit des finances publiques": "public_finance_tax_law",
    
    # Public law - spatial planning & construction
    "Raumplanung und öffentliches Baurecht": "spatial_planning_construction_law",
    "Aménagement du territoire et droit public des constructions": "spatial_planning_construction_law",
    "Costruzioni stradali e circolazione stradale": "spatial_planning_construction_law",
    "Pianificazione territoriale e diritto pubblico edilizio": "spatial_planning_construction_law",
    
    # Social insurance
    "Invalidenversicherung": "disability_insurance",
    "Assurance-invalidité": "disability_insurance",
    "Unfallversicherung": "accident_insurance",
    "Assicurazione contro gli infortuni": "accident_insurance",
    "Gesundheitswesen & soziale Sicherheit": "healthcare_social_security",
    "Santé & sécurité sociale": "healthcare_social_security",
    
    # Legal assistance & extradition
    "Entraide et extradition": "legal_assistance_extradition",
    "Rechtshilfe und Auslieferung": "legal_assistance_extradition",
    "Assistenza giudiziaria e estradizione": "legal_assistance_extradition",
    "Diritto fondamentale": "fundamental_rights",
    "Grundrecht": "fundamental_rights",
    
    # Administrative procedure
    "Procédure administrative": "administrative_procedure",
    "Verfahren": "procedure_general",
    
    # Intellectual property & competition
    "Immaterialgüter-, Wettbewerbs- und Kartellrecht": "ip_competition_cartel_law",
    "Droits réels": "property_rights",
    "Diritto reale": "property_rights",
    "Sachenrecht": "property_rights",
    
    # Corporate law
    "Gesellschaftsrecht": "corporate_law",
    "Droit des sociétés": "corporate_law",
    "Diritto societario": "corporate_law",
    
    # Registry
    "Registre": "registry",
    
    # Public service
    "Fonction publique": "civil_service",
    "Öffentliches Dienstverhältnis": "public_service_employment",
    "Pubblico impiego": "civil_service",
    
    # Media law
    "Medien": "media_law",
    
    # Economic law
    "Wirtschaft": "economic_law",
    "Économie": "economic_law",
    
    # Postal & telecommunications
    "Post- und Fernmeldeverkehr": "postal_telecom_law",
    
    # Energy law
    "Energie": "energy_law",
    
    # Environmental law
    "Ökologisches Gleichgewicht": "environmental_law",
    
    # Road construction & traffic
    "Strassenbau und Strassenverkehr": "road_construction_traffic_law",
    
    # Judicial organization
    "Zuständigkeitsfragen, Garantie des Wohnsitzrichters und des v...": "jurisdiction_judge_guarantees",
    
    # Enforcement & bankruptcy (chamber)
    "Camera delle esecuzioni e dei fallimenti": "debt_enforcement_bankruptcy",
    "Schuldbetreibungs- und Konkurskammer": "debt_enforcement_bankruptcy",
    
    # Criminal chamber
    "Cour de droit pénal": "criminal_court",
    "Strafrechtliche Abteilung": "criminal_division",
    
    # Civil courts
    "I. zivilrechtliche Abteilung": "civil_division_1",
    "II. zivilrechtliche Abteilung": "civil_division_2",
    "Ire Cour de droit civil": "civil_court_1",
    "IIe Cour de droit civil": "civil_court_2",
    "I Corte di diritto civile": "civil_court_1",
    "II Corte di diritto civile": "civil_court_2",
    
    # Public law courts
    "I. öffentlich-rechtliche Abteilung": "public_law_division_1",
    "II. Öffentlich-rechtliche Abteilung": "public_law_division_2",
    "Ire Cour de droit public": "public_law_court_1",
    "I. Öffentlich-rechtliche Abteilung": "public_law_division_1",
    
    # Social insurance courts
    "Strafrechtliche Abteilung": "criminal_division",
    "Cour de droit pénal": "criminal_court",
}

# Also normalize chamber names that appear as legal_area
CHAMBER_TO_NORMALIZED = {
    "I. zivilrechtliche Abteilung": "civil_division_1",
    "II. zivilrechtliche Abteilung": "civil_division_2",
    "Ire Cour de droit civil": "civil_court_1",
    "IIe Cour de droit civil": "civil_court_2",
    "I Corte di diritto civile": "civil_court_1",
    "II Corte di diritto civile": "civil_court_2",
    "I. öffentlich-rechtliche Abteilung": "public_law_division_1",
    "II. Öffentlich-rechtliche Abteilung": "public_law_division_2",
    "Ire Cour de droit public": "public_law_court_1",
    "I. Öffentlich-rechtliche Abteilung": "public_law_division_1",
    "Strafrechtliche Abteilung": "criminal_division",
    "Cour de droit pénal": "criminal_court",
    "Camera delle esecuzioni e dei fallimenti": "debt_enforcement_bankruptcy",
    "Schuldbetreibungs- und Konkurskammer": "debt_enforcement_bankruptcy",
}

GLOBAL_SEED = 42
SAMPLE_SIZE = 5000  # Sample for efficiency at 174k scale

def normalize_legal_area(legal_area: str, chamber: str = "") -> str:
    """Normalize a legal_area label using v17b mapping."""
    if legal_area and legal_area != "unknown" and legal_area in LABEL_NORMALIZATION_MAP:
        return LABEL_NORMALIZATION_MAP[legal_area]
    
    # Fallback: try chamber
    if chamber and chamber in CHAMBER_TO_NORMALIZED:
        return CHAMBER_TO_NORMALIZED[chamber]
    
    # Fallback: use original (lowercase, underscores)
    if legal_area and legal_area != "unknown":
        return legal_area.lower().replace(" ", "_").replace("-", "_").replace("&", "and").replace("(", "").replace(")", "").replace(",", "").replace(".", "").replace("'", "")
    
    return "unknown"

def load_metadata() -> List[Dict[str, Any]]:
    """Load metadata."""
    with open(METADATA_FILE) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    return metadata

def load_embeddings(embedding_file: str) -> np.ndarray:
    """Load embeddings."""
    filepath = EMBEDDINGS_DIR / embedding_file
    logger.info(f"Loading embeddings from {filepath}")
    embeddings = np.load(filepath)
    logger.info(f"Embeddings shape: {embeddings.shape}")
    return embeddings

def run_clustering_evaluation(
    embeddings: np.ndarray,
    labels: List[str],
    n_clusters: int,
    name: str,
) -> Dict[str, float]:
    """Run clustering and compute NMI and purity."""
    np.random.seed(GLOBAL_SEED)
    
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    
    # Clustering
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        metric="cosine",
        linkage="average",
    )
    pred_labels = clustering.fit_predict(normalized)
    
    # NMI
    nmi = float(normalized_mutual_info_score(labels, pred_labels))
    
    # Purity
    purity_scores = []
    unique_clusters = set(pred_labels)
    for cluster_id in unique_clusters:
        mask = pred_labels == cluster_id
        cluster_true = [labels[i] for i in range(len(labels)) if mask[i]]
        if cluster_true:
            most_common = Counter(cluster_true).most_common(1)[0][1]
            purity_scores.append(most_common / len(cluster_true))
    
    purity = float(np.mean(purity_scores)) if purity_scores else 0.0
    
    return {
        "nmi": nmi,
        "purity": purity,
        "n_clusters": n_clusters,
        "n_samples": len(labels),
    }

def main():
    logger.info("Starting v17b Label Normalization Test at 174k Scale")
    start_time = time.time()
    
    # Load metadata
    metadata = load_metadata()
    
    # Create normalized labels
    logger.info("Creating normalized labels...")
    raw_labels = []
    normalized_labels = []
    decision_ids = []
    
    for m in metadata:
        legal_area = m.get("legal_area", "unknown")
        chamber = m.get("chamber", "")
        decision_id = m.get("decision_id", "")
        
        raw = legal_area if legal_area != "unknown" else "unknown"
        norm = normalize_legal_area(legal_area, chamber)
        
        raw_labels.append(raw)
        normalized_labels.append(norm)
        decision_ids.append(decision_id)
    
    # Statistics
    raw_unique = len(set(raw_labels))
    norm_unique = len(set(normalized_labels))
    unknown_count = raw_labels.count("unknown")
    
    logger.info(f"Raw unique labels: {raw_unique}")
    logger.info(f"Normalized unique labels: {norm_unique}")
    logger.info(f"Unknown count: {unknown_count} ({unknown_count/len(raw_labels)*100:.1f}%)")
    
    # Filter out unknown for clustering evaluation
    valid_indices = [i for i, (r, n) in enumerate(zip(raw_labels, normalized_labels)) 
                     if r != "unknown" and n != "unknown"]
    
    logger.info(f"Valid indices for clustering: {len(valid_indices)}")
    
    # Sample for efficiency
    if len(valid_indices) > SAMPLE_SIZE:
        np.random.seed(GLOBAL_SEED)
        valid_indices = np.random.choice(valid_indices, SAMPLE_SIZE, replace=False).tolist()
    
    # Load embeddings and test
    results = {}
    
    for emb_file in TEST_EMBEDDINGS:
        if not (EMBEDDINGS_DIR / emb_file).exists():
            logger.warning(f"Embedding file not found: {emb_file}")
            continue
            
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {emb_file}")
        logger.info(f"{'='*60}")
        
        try:
            embeddings = load_embeddings(emb_file)
            
            # Get embeddings for valid indices
            sample_embeddings = embeddings[valid_indices]
            sample_raw = [raw_labels[i] for i in valid_indices]
            sample_norm = [normalized_labels[i] for i in valid_indices]
            
            # Filter out zero vectors
            norms = np.linalg.norm(sample_embeddings, axis=1)
            non_zero_mask = norms > 1e-10
            if not np.all(non_zero_mask):
                logger.info(f"  Filtering out {np.sum(~non_zero_mask)} zero vectors")
                sample_embeddings = sample_embeddings[non_zero_mask]
                sample_raw = [sample_raw[i] for i in range(len(sample_raw)) if non_zero_mask[i]]
                sample_norm = [sample_norm[i] for i in range(len(sample_norm)) if non_zero_mask[i]]
            
            # Determine n_clusters (use normalized unique count, capped)
            n_clusters = min(len(set(sample_norm)), 50)
            n_clusters = max(n_clusters, 4)  # At least 4 (branches)
            
            logger.info(f"Sample size: {len(sample_embeddings)}")
            logger.info(f"Raw unique in sample: {len(set(sample_raw))}")
            logger.info(f"Normalized unique in sample: {len(set(sample_norm))}")
            logger.info(f"Using n_clusters: {n_clusters}")
            
            # Evaluate with raw labels
            raw_metrics = run_clustering_evaluation(
                sample_embeddings, sample_raw, n_clusters, f"{emb_file}_raw"
            )
            
            # Evaluate with normalized labels
            norm_metrics = run_clustering_evaluation(
                sample_embeddings, sample_norm, n_clusters, f"{emb_file}_norm"
            )
            
            # Compute purity gain
            purity_gain_pct = 0
            if raw_metrics["purity"] > 0:
                purity_gain_pct = (norm_metrics["purity"] - raw_metrics["purity"]) / raw_metrics["purity"] * 100
            
            results[emb_file.replace('.npy', '')] = {
                "raw_labels": raw_metrics,
                "normalized_labels": norm_metrics,
                "purity_gain_pct": purity_gain_pct,
                "nmi_gain": norm_metrics["nmi"] - raw_metrics["nmi"],
                "normalized_unique_labels": len(set(sample_norm)),
                "raw_unique_labels": len(set(sample_raw)),
            }
            
            logger.info(f"  Raw:     NMI={raw_metrics['nmi']:.4f}, Purity={raw_metrics['purity']:.4f}")
            logger.info(f"  Norm:    NMI={norm_metrics['nmi']:.4f}, Purity={norm_metrics['purity']:.4f}")
            logger.info(f"  Gain:    NMI={norm_metrics['nmi'] - raw_metrics['nmi']:.4f}, Purity={purity_gain_pct:.1f}%")
            
        except Exception as e:
            logger.error(f"Error processing {emb_file}: {e}")
            results[emb_file.replace('.npy', '')] = {"error": str(e)}
    
    # Save results
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    output_file = OUTPUT_DIR / f"v17b_label_normalization_174k_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "run_info": {
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "direction_version": 29,
                "total_decisions": len(metadata),
                "valid_decisions": len(valid_indices),
                "sample_size": SAMPLE_SIZE,
                "global_seed": GLOBAL_SEED,
                "raw_unique_labels": raw_unique,
                "normalized_unique_labels": norm_unique,
                "unknown_count": unknown_count,
            },
            "results": results
        }, f, indent=2)
    
    # Also save as latest
    latest_file = OUTPUT_DIR / "v17b_label_normalization_174k_latest.json"
    with open(latest_file, 'w') as f:
        json.dump({
            "run_info": {
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "direction_version": 29,
                "total_decisions": len(metadata),
                "valid_decisions": len(valid_indices),
                "sample_size": SAMPLE_SIZE,
                "global_seed": GLOBAL_SEED,
                "raw_unique_labels": raw_unique,
                "normalized_unique_labels": norm_unique,
                "unknown_count": unknown_count,
            },
            "results": results
        }, f, indent=2)
    
    logger.info(f"\nResults saved to {output_file}")
    logger.info(f"Total duration: {time.time() - start_time:.2f}s")
    
    # Print summary
    print("\n" + "="*100)
    print("v17b LABEL NORMALIZATION 174k GENERALIZATION TEST")
    print("="*100)
    print(f"Total decisions: {len(metadata)}")
    print(f"Valid decisions (non-unknown): {len([r for r in raw_labels if r != 'unknown'])}")
    print(f"Raw unique labels: {raw_unique} -> Normalized unique labels: {norm_unique}")
    print(f"Reduction: {(1 - norm_unique/raw_unique)*100:.1f}%")
    print()
    
    for name, result in results.items():
        if "error" in result:
            print(f"  {name}: ERROR - {result['error']}")
        else:
            raw = result["raw_labels"]
            norm = result["normalized_labels"]
            gain = result["purity_gain_pct"]
            nmi_gain = result["nmi_gain"]
            status = "✓ GAIN" if gain > 0 else "✗ LOSS/NO GAIN"
            print(f"  {name}:")
            print(f"    Raw:     NMI={raw['nmi']:.4f}, Purity={raw['purity']:.4f} ({result['raw_unique_labels']} labels)")
            print(f"    Norm:    NMI={norm['nmi']:.4f}, Purity={norm['purity']:.4f} ({result['normalized_unique_labels']} labels)")
            print(f"    Gain:    NMI={nmi_gain:+.4f}, Purity={gain:+.1f}% {status}")

if __name__ == "__main__":
    main()