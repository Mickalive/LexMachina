#!/usr/bin/env python3
"""
Sync 174k artifacts from accepted evidence to product results directory.

This script copies the full 174k TF-IDF embeddings and clustering artifacts
from /tmp/lex_accepted/fractal-map/results/fractal_map/ to
/home/runner/work/LexMachina/LexMachina/product/results/fractal_map/
"""

import shutil
from pathlib import Path

ACCEPTED_BASE = Path("/tmp/lex_accepted/fractal-map/results/fractal_map")
PRODUCT_BASE = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map")

def sync_hierarchical_map_174k():
    """Sync hierarchical_map_174k directory with full 174k embeddings and metadata."""
    src = ACCEPTED_BASE / "hierarchical_map_174k"
    dst = PRODUCT_BASE / "hierarchical_map_174k"
    
    print(f"Syncing {src} -> {dst}")
    dst.mkdir(parents=True, exist_ok=True)
    
    # Copy embeddings and metadata
    for file in ["metadata_174k_full.json", "metadata_174k_eval.json", "metadata_174k_bge.json", 
                 "metadata_174k.json", "metadata_174k_full_summary.json", "metadata_174k_summary.json",
                 "tfidf_embeddings_metadata.json", "embeddings_metadata.json"]:
        src_file = src / file
        if src_file.exists():
            shutil.copy2(src_file, dst / file)
            print(f"  Copied {file}")
    
    # Copy legal_tfidf_embeddings
    src_legal = src / "legal_tfidf_embeddings"
    dst_legal = dst / "legal_tfidf_embeddings"
    if src_legal.exists():
        dst_legal.mkdir(parents=True, exist_ok=True)
        for file in src_legal.iterdir():
            shutil.copy2(file, dst_legal / file.name)
            print(f"  Copied legal_tfidf_embeddings/{file.name}")
    
    # Copy tfidf_embeddings
    src_tfidf = src / "tfidf_embeddings"
    dst_tfidf = dst / "tfidf_embeddings"
    if src_tfidf.exists():
        dst_tfidf.mkdir(parents=True, exist_ok=True)
        for file in src_tfidf.iterdir():
            shutil.copy2(file, dst_tfidf / file.name)
            print(f"  Copied tfidf_embeddings/{file.name}")

def sync_product_integration_174k():
    """Sync product_integration_174k with full 174k clustering artifacts."""
    src = ACCEPTED_BASE / "product_integration_174k"
    dst = PRODUCT_BASE / "product_integration_174k"
    
    print(f"Syncing {src} -> {dst}")
    if not src.exists():
        print(f"  Source not found: {src}")
        return
    
    dst.mkdir(parents=True, exist_ok=True)
    
    for rep_dir in src.iterdir():
        if not rep_dir.is_dir():
            continue
        dst_rep = dst / rep_dir.name
        dst_rep.mkdir(parents=True, exist_ok=True)
        print(f"  Syncing {rep_dir.name}...")
        for file in rep_dir.iterdir():
            shutil.copy2(file, dst_rep / file.name)
            print(f"    Copied {file.name}")

def sync_174k_representation_dirs():
    """Sync individual 174k representation directories (cluster artifacts)."""
    # The product integration directories already have the cluster artifacts
    # But the individual representation directories (e.g., cited_outcome_hybrid_0.5_174k)
    # may need to be updated with the full 174k artifacts
    
    # Mapping from accepted evidence directory names to product directory names
    rep_mapping = [
        ("cited_decisions_tfidf", "cited_decisions_tfidf_174k"),
        ("cited_decisions_tfidf_outcome_hybrid_0.5_174k", "cited_outcome_hybrid_0.5_174k"),
        ("cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25", "cited_outcome_hybrid_0.7_174k"),
        ("regeste_tfidf_174k", "regeste_tfidf_174k"),
    ]
    
    for src_name, dst_name in rep_mapping:
        src = ACCEPTED_BASE / "product_integration_174k" / src_name
        dst = PRODUCT_BASE / dst_name
        if src.exists():
            print(f"Syncing {src_name} -> {dst_name}...")
            dst.mkdir(parents=True, exist_ok=True)
            for file in src.iterdir():
                shutil.copy2(file, dst / file.name)
                print(f"  Copied {file.name}")
        else:
            print(f"  Source not found: {src}")

def main():
    print("=== Syncing 174k artifacts from accepted evidence ===")
    sync_hierarchical_map_174k()
    sync_product_integration_174k()
    sync_174k_representation_dirs()
    print("=== Sync complete ===")

if __name__ == "__main__":
    main()
