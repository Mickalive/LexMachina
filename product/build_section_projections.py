"""
LexMachina Section Projection Builder
Generates 2D UMAP projections for section-specific text (sachverhalt, erwaegungen, dispositiv)
using TF-IDF embeddings. Enables section-mode coverage for all decisions with extracted sections.
"""
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from app.corpus_loader import CorpusLoader
from app.section_extractor import extract_sections, SECTION_MARKERS


SECTION_MODES = [
    "sachverhalt",
    "erwaegungen",
    "dispositiv",
    "full_text",
    "erwaegungen_dispositiv",
    "sachverhalt_erwaegungen_dispositiv",
]

SECTION_LABELS = {
    "sachverhalt": "Facts (Sachverhalt)",
    "erwaegungen": "Reasoning (Erwägungen)",
    "dispositiv": "Holding (Dispositiv)",
    "full_text": "Full Text",
    "erwaegungen_dispositiv": "Reasoning + Holding",
    "sachverhalt_erwaegungen_dispositiv": "Facts + Reasoning + Holding",
}

OUTPUT_DIR = Path(__file__).resolve().parent / "results" / "fractal_map" / "section_scaled_v2"


def build_tfidf_embeddings(texts: List[str], max_features: int = 5000) -> np.ndarray:
    """Build TF-IDF embeddings for a list of texts."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        stop_words=None,  # We handle stopwords in tokenization
        lowercase=True,
        token_pattern=r'(?u)\b\w\w+\b',
    )
    
    tfidf_matrix = vectorizer.fit_transform(texts)
    return tfidf_matrix.toarray(), vectorizer


def build_svd_embeddings(tfidf_matrix: np.ndarray, n_components: int = 128) -> np.ndarray:
    """Apply Truncated SVD to reduce TF-IDF dimensionality."""
    from sklearn.decomposition import TruncatedSVD
    
    n_components = min(n_components, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
    if n_components < 2:
        return tfidf_matrix
    
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    return svd.fit_transform(tfidf_matrix)


def build_umap_projection(embeddings: np.ndarray, n_neighbors: int = 15, min_dist: float = 0.1) -> np.ndarray:
    """Build 2D UMAP projection from embeddings."""
    import umap
    
    # UMAP parameters tuned for legal document similarity
    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        n_components=2,
        metric='cosine',
        random_state=42,
        n_jobs=1,
    )
    
    projection = reducer.fit_transform(embeddings)
    return projection


def get_section_text(decision: Dict, section_name: str) -> str:
    """Get text for a specific section mode from a decision."""
    if section_name == "sachverhalt":
        return decision.get("sachverhalt", "") or ""
    elif section_name == "erwaegungen":
        return decision.get("erwaegungen", "") or ""
    elif section_name == "dispositiv":
        return decision.get("dispositiv", "") or ""
    elif section_name == "full_text":
        return decision.get("full_text", "") or ""
    elif section_name == "erwaegungen_dispositiv":
        parts = []
        if decision.get("erwaegungen"):
            parts.append(decision["erwaegungen"])
        if decision.get("dispositiv"):
            parts.append(decision["dispositiv"])
        return " ".join(parts)
    elif section_name == "sachverhalt_erwaegungen_dispositiv":
        parts = []
        if decision.get("sachverhalt"):
            parts.append(decision["sachverhalt"])
        if decision.get("erwaegungen"):
            parts.append(decision["erwaegungen"])
        if decision.get("dispositiv"):
            parts.append(decision["dispositiv"])
        return " ".join(parts)
    return ""


def run() -> None:
    """Generate section projections for all decisions with extracted sections."""
    print("Loading corpus...")
    corpus_dir = str(Path(__file__).parent / "results" / "corpus" / "normalization" / "canonical")
    cl = CorpusLoader(corpus_dir)
    cl.load()
    
    print(f"Loaded {cl.size} decisions")
    
    # Collect decisions with section data
    decisions_with_sections = []
    decisions_without_sections = []
    
    for did, decision in cl.decisions.items():
        d = decision.to_full_raw()
        # Check if any section has content
        has_section = any(d.get(s) for s in ["sachverhalt", "erwaegungen", "dispositiv"])
        if has_section:
            decisions_with_sections.append(d)
        else:
            decisions_without_sections.append(d)
    
    print(f"Decisions with at least one section: {len(decisions_with_sections)}")
    print(f"Decisions without sections: {len(decisions_without_sections)}")
    
    # For each section mode, build projections
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Track provenance for blending with baseline
    all_decision_ids = [d["decision_id"] for d in decisions_with_sections + decisions_without_sections]
    section_decision_ids = [d["decision_id"] for d in decisions_with_sections]
    
    decision_provenance = []
    for did in all_decision_ids:
        if did in section_decision_ids:
            decision_provenance.append({"decision_id": did, "source": "section_projection"})
        else:
            decision_provenance.append({"decision_id": did, "source": "baseline"})
    
    mode_stats = {}
    
    for mode_name in SECTION_MODES:
        print(f"\nProcessing {mode_name}...")
        
        # Collect texts for decisions with sections
        texts = []
        valid_ids = []
        
        for d in decisions_with_sections:
            text = get_section_text(d, mode_name)
            if text and len(text.strip()) > 50:  # Minimum content
                texts.append(text)
                valid_ids.append(d["decision_id"])
        
        if len(texts) < 10:
            print(f"  SKIP {mode_name}: only {len(texts)} decisions with sufficient content")
            continue
        
        print(f"  Building TF-IDF for {len(texts)} decisions...")
        tfidf_matrix, vectorizer = build_tfidf_embeddings(texts)
        print(f"  TF-IDF shape: {tfidf_matrix.shape}")
        
        print(f"  Building SVD embeddings...")
        svd_embeddings = build_svd_embeddings(tfidf_matrix, n_components=min(128, tfidf_matrix.shape[1] - 1))
        print(f"  SVD shape: {svd_embeddings.shape}")
        
        print(f"  Building UMAP projection...")
        projection = build_umap_projection(svd_embeddings)
        print(f"  Projection shape: {projection.shape}")
        
        # Create full projection array (all decisions, section where available, baseline elsewhere)
        # For now, save section-only projection
        section_projection = np.zeros((len(all_decision_ids), 2))
        id_to_idx = {did: i for i, did in enumerate(all_decision_ids)}
        
        for i, did in enumerate(valid_ids):
            if did in id_to_idx:
                section_projection[id_to_idx[did]] = projection[i]
        
        # Save section-only projection
        out_path = OUTPUT_DIR / f"projection_{mode_name}.npy"
        np.save(out_path, section_projection)
        print(f"  Saved to {out_path}")
        
        # Save valid decision IDs for this mode
        with open(OUTPUT_DIR / f"valid_ids_{mode_name}.json", "w") as f:
            json.dump(valid_ids, f)
        
        n_section = len(valid_ids)
        n_baseline = len(all_decision_ids) - n_section
        mode_stats[mode_name] = {
            "label": SECTION_LABELS.get(mode_name, mode_name),
            "total_decisions": len(all_decision_ids),
            "section_decisions": n_section,
            "baseline_fallback": n_baseline,
            "coverage_pct": round(100.0 * n_section / len(all_decision_ids), 1),
        }
        print(f"  Coverage: {n_section}/{len(all_decision_ids)} ({mode_stats[mode_name]['coverage_pct']}%)")
    
    # Load baseline projection for reference
    baseline_dir = Path(__file__).parent / "results" / "fractal_map" / "baseline"
    baseline_proj = np.load(baseline_dir / "projection_2d.npy")
    shutil.copy2(baseline_dir / "projection_2d.npy", OUTPUT_DIR / "projection_baseline.npy")
    
    # Build blended projections (section where available, baseline elsewhere)
    for mode_name in SECTION_MODES:
        section_proj_path = OUTPUT_DIR / f"projection_{mode_name}.npy"
        if not section_proj_path.exists():
            continue
        
        section_proj = np.load(section_proj_path)
        # Blend: use section projection where non-zero (has section data), baseline elsewhere
        blended = baseline_proj.copy()
        # Find rows where section projection is non-zero
        mask = np.any(section_proj != 0, axis=1)
        blended[mask] = section_proj[mask]
        
        blended_path = OUTPUT_DIR / f"projection_{mode_name}_blended.npy"
        np.save(blended_path, blended)
        print(f"  Blended projection saved to {blended_path}")
    
    # Write metadata
    metadata = {
        "description": "Section-specific projections generated from extracted sections (TF-IDF + SVD + UMAP)",
        "total_decisions": len(all_decision_ids),
        "section_covered_decisions": len(section_decision_ids),
        "section_modes": mode_stats,
        "decision_provenance": decision_provenance,
        "generation_method": "TF-IDF (max_features=5000) -> SVD (128D) -> UMAP (2D, cosine)",
    }
    
    with open(OUTPUT_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nDone. Output: {OUTPUT_DIR}")
    print(f"Total decisions: {len(all_decision_ids)}")
    print(f"Section-covered: {len(section_decision_ids)}")


if __name__ == "__main__":
    import shutil
    run()