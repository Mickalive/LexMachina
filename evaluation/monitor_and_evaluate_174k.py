#!/usr/bin/env python3
"""
Monitor and Auto-Evaluate 174k Representations

Watches the legal-distance accepted state for 174k production representations
and automatically runs the full evaluation suite when they appear.

Factory Direction v25: Evaluation lane runs 174k formal suite autonomously 
as representations land.
"""

import json
import time
import logging
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('evaluation/logs/monitor_174k.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
LEX_ACCEPTED_ROOT = Path("/tmp/lex_accepted")
LEGAL_DISTANCE_RESULTS_ROOT = LEX_ACCEPTED_ROOT / "legal-distance/legal_distance/results"
FRACTAL_MAP_RESULTS_ROOT = LEX_ACCEPTED_ROOT / "fractal-map/results/fractal_map"

# Production representations expected at 174k (from factory direction v27)
# TF-IDF family COMPLETED at 174k (8 representations evaluated) - names match actual filenames in fractal-map mount
EXPECTED_REPRESENTATIONS = {
    "completed_tfidf_174k": [
        "cited_decisions_tfidf",
        "outcome_tfidf", 
        "cited_decisions_tfidf_outcome_hybrid_0.5",
        "cited_decisions_tfidf_outcome_hybrid_0.7",
        "regeste_tfidf",
        "full_text_tfidf_light",
        "regeste_full_text_hybrid_0.5",
        "regeste_full_text_hybrid_0.7",
    ],
    "awaited_dense_174k": [
        "center_projected_768dim",
        "center_projected_64dim",
        "center_projected_128dim",
        "linear_metric_epoch4",
        "mahalanobis_metric_epoch4",
        "hybrid_stabilized_epoch1",
        "hybrid_v2_epoch3",
    ],
    "awaited_citation_roles_174k": [
        "citation_role_citing_alpha0.3",
        "citation_role_following_alpha0.3",
        "citation_role_criticizing_alpha0.3",
    ],
    "awaited_linear_hybrids_174k": [
        "linear_citation_concat",
        "linear_hybrid05_concat",
    ]
}

# Flatten all expected
ALL_EXPECTED = []
for cat, reps in EXPECTED_REPRESENTATIONS.items():
    ALL_EXPECTED.extend(reps)

# Completed TF-IDF representations (already evaluated)
COMPLETED_TFIDF = EXPECTED_REPRESENTATIONS["completed_tfidf_174k"]

# Awaited representations
AWAITED_REPRESENTATIONS = []
for cat, reps in EXPECTED_REPRESENTATIONS.items():
    if cat != "completed_tfidf_174k":
        AWAITED_REPRESENTATIONS.extend(reps)

# Evaluation scripts
EVALUATION_SCRIPTS = {
    "full_corpus_adversarial": "evaluation/run_full_corpus_evaluation.py",
    "formal_benchmark_suite": "evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py",
    "citation_heritage": "evaluation/validate_citation_heritage_174k.py",
    "v17b_label_normalization": "evaluation/experiments/run_v17b_label_normalization_all_reps.py",
}

# Metadata and data paths
METADATA_174K = Path("evaluation/data/174k/metadata_174k.json")
CORPUS_174K = Path("evaluation/data/174k/corpus_174k.jsonl")
CITATION_PAIRS = Path("evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json")

# State tracking
STATE_FILE = Path("evaluation/state/monitor_174k_state.json")
LOG_DIR = Path("evaluation/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_state() -> Dict:
    """Load monitoring state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "started_at": datetime.now().isoformat(),
        "last_check": None,
        "completed_evaluations": {},
        "detected_representations": {},
        "check_count": 0
    }


def save_state(state: Dict):
    """Save monitoring state."""
    state["last_check"] = datetime.now().isoformat()
    state["check_count"] += 1
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def scan_for_representations() -> Dict[str, List[Path]]:
    """Scan accepted state mounts for 174k representation directories."""
    found = {}
    
    # 1. Scan legal-distance results for 174k dense embeddings (final concatenated)
    dense_embeddings_root = LEGAL_DISTANCE_RESULTS_ROOT / "174k_dense_embeddings"
    if dense_embeddings_root.exists():
        # Check for final embeddings in the root (not in checkpoints subdirectory)
        npy_files = list(dense_embeddings_root.glob("*.npy"))
        if npy_files:
            found["174k_dense_embeddings"] = npy_files
            logger.info(f"Found 174k representation dir: 174k_dense_embeddings with {len(npy_files)} embeddings")
        # Also check any subdirectories that are not 'checkpoints'
        for item in dense_embeddings_root.iterdir():
            if item.is_dir() and item.name != "checkpoints" and "174k" in item.name.lower():
                npy_files = list(item.glob("*.npy"))
                if npy_files:
                    found[f"174k_dense_embeddings/{item.name}"] = npy_files
                    logger.info(f"Found 174k representation dir: 174k_dense_embeddings/{item.name} with {len(npy_files)} embeddings")
    
    # 2. Scan fractal-map accepted mount for TF-IDF 174k embeddings (already evaluated but good to verify)
    tfidf_emb_dir = FRACTAL_MAP_RESULTS_ROOT / "hierarchical_map_174k" / "legal_tfidf_embeddings"
    if tfidf_emb_dir.exists():
        npy_files = list(tfidf_emb_dir.glob("*.npy"))
        if npy_files:
            found["fractal_map/hierarchical_map_174k/legal_tfidf_embeddings"] = npy_files
            logger.info(f"Found 174k TF-IDF embeddings: {len(npy_files)} files")
    
    tfidf_emb_dir2 = FRACTAL_MAP_RESULTS_ROOT / "hierarchical_map_174k" / "tfidf_embeddings"
    if tfidf_emb_dir2.exists():
        npy_files = list(tfidf_emb_dir2.glob("*.npy"))
        if npy_files:
            found["fractal_map/hierarchical_map_174k/tfidf_embeddings"] = npy_files
            logger.info(f"Found 174k TF-IDF embeddings (alt): {len(npy_files)} files")
    
    # 3. Scan legal-distance version directories for any other 174k representations
    if LEGAL_DISTANCE_RESULTS_ROOT.exists():
        for version_dir in LEGAL_DISTANCE_RESULTS_ROOT.iterdir():
            if not version_dir.is_dir():
                continue
            if not version_dir.name.startswith('v'):
                continue
                
            for item in version_dir.iterdir():
                if item.is_dir() and "174k" in item.name.lower():
                    # Check for embedding files
                    npy_files = list(item.glob("*.npy"))
                    if npy_files:
                        found[f"{version_dir.name}/{item.name}"] = npy_files
                        logger.info(f"Found 174k representation dir: {version_dir.name}/{item.name} with {len(npy_files)} embeddings")
    
    # 4. Scan for citation role 174k embeddings (when they land)
    # These would be in legal-distance results under a 174k citation roles directory
    for version_dir in LEGAL_DISTANCE_RESULTS_ROOT.iterdir():
        if not version_dir.is_dir():
            continue
        if not version_dir.name.startswith('v'):
            continue
        for item in version_dir.iterdir():
            if item.is_dir() and "citation_role" in item.name.lower() and "174k" in item.name.lower():
                npy_files = list(item.glob("*.npy"))
                if npy_files:
                    found[f"{version_dir.name}/{item.name}"] = npy_files
                    logger.info(f"Found 174k citation role dir: {version_dir.name}/{item.name} with {len(npy_files)} embeddings")
    
    # 5. Scan for linear hybrid 174k embeddings
    for version_dir in LEGAL_DISTANCE_RESULTS_ROOT.iterdir():
        if not version_dir.is_dir():
            continue
        if not version_dir.name.startswith('v'):
            continue
        for item in version_dir.iterdir():
            if item.is_dir() and "linear" in item.name.lower() and "174k" in item.name.lower():
                npy_files = list(item.glob("*.npy"))
                if npy_files:
                    found[f"{version_dir.name}/{item.name}"] = npy_files
                    logger.info(f"Found 174k linear hybrid dir: {version_dir.name}/{item.name} with {len(npy_files)} embeddings")
    
    return found


def get_expected_representation_dirs() -> List[str]:
    """Get list of expected representation directory names."""
    # These would be created by legal-distance with standard naming
    dirs = []
    # TF-IDF signals might be in a combined dir or separate
    dirs.append("174k_tfidf_signals")
    dirs.append("174k_cited_outcome_hybrid")
    dirs.append("174k_linear_combinations")
    # Dense embeddings
    dirs.append("center_projected_174k")
    dirs.append("center_projected_64dim_174k")
    dirs.append("metric_learning_174k")
    dirs.append("hybrid_stabilized_174k")
    # Citation roles
    dirs.append("citation_roles_174k")
    return dirs


def check_representations_ready(found_dirs: Dict) -> Dict[str, bool]:
    """Check which expected representations are ready."""
    ready = {}
    
    # Map found directories to expected representations
    for dir_name, npy_files in found_dirs.items():
        for npy in npy_files:
            rep_name = npy.stem.replace("embeddings_", "").replace("embeddings-", "")
            ready[rep_name] = True
    
    # Check all expected (including completed)
    status = {}
    for exp in ALL_EXPECTED:
        status[exp] = ready.get(exp, False)
    
    return status


def run_evaluation_command(cmd: List[str], output_dir: Path, representation: str) -> bool:
    """Run an evaluation command and return success status."""
    logger.info(f"Running evaluation for {representation}: {' '.join(cmd)}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / f"{representation}_eval.log"
    
    try:
        with open(log_file, 'w') as f:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=7200,  # 2 hour timeout
                cwd="/home/runner/work/LexMachina/LexMachina"
            )
            f.write(result.stdout)
            f.write(result.stderr)
        
        if result.returncode == 0:
            logger.info(f"Evaluation SUCCESS for {representation}")
            return True
        else:
            logger.error(f"Evaluation FAILED for {representation} (exit code {result.returncode})")
            logger.error(f"Stderr: {result.stderr[:1000]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Evaluation TIMEOUT for {representation}")
        return False
    except Exception as e:
        logger.error(f"Evaluation ERROR for {representation}: {e}")
        return False


def run_full_corpus_evaluation(embeddings_dir: Path, representation: str, output_base: Path) -> bool:
    """Run full corpus adversarial evaluation on a representation directory."""
    output_dir = output_base / f"full_corpus_174k_{representation}"
    
    cmd = [
        "python", "evaluation/run_full_corpus_evaluation.py",
        "--embeddings-dir", str(embeddings_dir),
        "--metadata", str(METADATA_174K),
        "--output-dir", str(output_dir)
    ]
    
    return run_evaluation_command(cmd, output_dir, representation)


def run_citation_heritage(embeddings_dir: Path, representation: str, output_base: Path) -> bool:
    """Run citation heritage benchmark on a representation."""
    output_dir = output_base / f"citation_heritage_174k_{representation}"
    
    # Find the embedding file
    npy_files = list(embeddings_dir.glob("*.npy"))
    if not npy_files:
        logger.warning(f"No embedding files found in {embeddings_dir}")
        return False
    
    # For citation heritage, we need to run validate_citation_heritage_174k.py
    # This script needs to be adapted to load specific embeddings
    logger.info(f"Citation heritage evaluation for {representation} - script adaptation needed")
    return True  # Placeholder


def run_v17b_normalization(embeddings_dir: Path, representation: str, output_base: Path) -> bool:
    """Run v17b label normalization clustering test."""
    output_dir = output_base / f"v17b_174k_{representation}"
    
    logger.info(f"v17b label normalization test for {representation} - script adaptation needed")
    return True  # Placeholder


def run_formal_suite_v25(embeddings_dir: Path, representation: str, output_base: Path) -> bool:
    """Run the full v25 174k formal suite for a representation.
    
    This copies the embedding to the v25 suite embeddings directory and runs
    the frozen protocol runner (12-benchmark suite + citation_heritage + v17b).
    """
    # Target directory for v25 suite embeddings
    v25_emb_dir = Path("results/evaluation/v25_174k_formal_suite/embeddings")
    v25_emb_dir.mkdir(parents=True, exist_ok=True)
    
    # Find embedding file in source directory
    npy_files = list(embeddings_dir.glob("*.npy"))
    if not npy_files:
        logger.warning(f"No embedding files found in {embeddings_dir} for {representation}")
        return False
    
    # Use the first .npy file (should be the main embedding)
    src_npy = npy_files[0]
    dst_npy = v25_emb_dir / f"{representation}.npy"
    
    # Copy or symlink the embedding
    try:
        if dst_npy.exists() or dst_npy.is_symlink():
            dst_npy.unlink()
        import shutil
        shutil.copy2(src_npy, dst_npy)
        logger.info(f"Copied {src_npy} -> {dst_npy}")
    except Exception as e:
        logger.error(f"Failed to copy embedding: {e}")
        return False
    
    # Run the v25 formal suite for this representation
    cmd = [
        "python", "evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py",
        "--rep", representation,
        "--parallel", "1"
    ]
    
    output_dir = output_base / f"v25_formal_suite_{representation}"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / f"{representation}_v25_suite.log"
    
    logger.info(f"Running v25 formal suite for {representation}: {' '.join(cmd)}")
    
    try:
        with open(log_file, 'w') as f:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10800,  # 3 hour timeout for full suite
                cwd="/home/runner/work/LexMachina/LexMachina"
            )
            f.write(result.stdout)
            f.write(result.stderr)
        
        if result.returncode == 0:
            logger.info(f"v25 formal suite SUCCESS for {representation}")
            return True
        else:
            logger.error(f"v25 formal suite FAILED for {representation} (exit code {result.returncode})")
            logger.error(f"Stderr: {result.stderr[:2000]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"v25 formal suite TIMEOUT for {representation}")
        return False
    except Exception as e:
        logger.error(f"v25 formal suite ERROR for {representation}: {e}")
        return False


def execute_evaluation_suite(found_dirs: Dict, state: Dict):
    """Execute the full evaluation suite for newly detected AWAITED representations."""
    output_base = Path("evaluation/results/174k_formal_suite")
    output_base.mkdir(parents=True, exist_ok=True)
    
    # Only evaluate awaited representations, not already-completed TF-IDF
    awaited_reps = set(AWAITED_REPRESENTATIONS)
    
    newly_ready = {}
    for dir_name, npy_files in found_dirs.items():
        # Determine representation names from files in this directory
        rep_names_in_dir = set()
        for npy in npy_files:
            rep_name = npy.stem.replace("embeddings_", "").replace("embeddings-", "")
            rep_names_in_dir.add(rep_name)
        
        # Check if any awaited representations are in this directory
        awaited_in_dir = rep_names_in_dir & awaited_reps
        if not awaited_in_dir:
            # No awaited representations here - skip (e.g., TF-IDF already done)
            continue
            
        if dir_name not in state["detected_representations"]:
            newly_ready[dir_name] = npy_files
            state["detected_representations"][dir_name] = {
                "first_seen": datetime.now().isoformat(),
                "files": [str(f) for f in npy_files],
                "awaited_representations": list(awaited_in_dir)
            }
    
    if not newly_ready:
        logger.info("No new awaited representations detected")
        return
    
    logger.info(f"NEW AWAITED REPRESENTATIONS DETECTED: {list(newly_ready.keys())}")
    
    for dir_name, npy_files in newly_ready.items():
        # Map found directory to actual filesystem path
        if dir_name.startswith("fractal_map/"):
            embeddings_dir = FRACTAL_MAP_RESULTS_ROOT / dir_name.split("/", 1)[1]
        elif dir_name.startswith("174k_dense_embeddings"):
            embeddings_dir = LEGAL_DISTANCE_RESULTS_ROOT / dir_name
        else:
            embeddings_dir = LEGAL_DISTANCE_RESULTS_ROOT / dir_name
        
        if not embeddings_dir.exists():
            logger.error(f"Embeddings directory not found: {embeddings_dir}")
            continue
        
        # Determine awaited representation names from files
        awaited_in_dir = state["detected_representations"][dir_name].get("awaited_representations", [])
        
        for rep_name in awaited_in_dir:
            # Verify the embedding file exists
            rep_file = embeddings_dir / f"{rep_name}.npy"
            if not rep_file.exists():
                # Try alternative naming
                alt_names = [
                    f"embeddings_{rep_name}.npy",
                    f"embeddings-{rep_name}.npy",
                    f"{rep_name}_embeddings.npy",
                ]
                for alt in alt_names:
                    if (embeddings_dir / alt).exists():
                        rep_file = embeddings_dir / alt
                        break
                else:
                    logger.warning(f"Embedding file not found for {rep_name} in {embeddings_dir}")
                    continue
            
            logger.info(f"Processing awaited representation: {rep_name} from {dir_name}")
            
            # 1. Run full corpus adversarial evaluation (v3 harness at 174k scale)
            logger.info(f"Starting full corpus adversarial evaluation for {rep_name}")
            adv_success = run_full_corpus_evaluation(embeddings_dir, rep_name, output_base)
            
            # 2. Run the full v25 formal suite (12-benchmark + citation_heritage + v17b)
            logger.info(f"Starting v25 formal suite for {rep_name}")
            suite_success = run_formal_suite_v25(embeddings_dir, rep_name, output_base)
            
            eval_key = f"{dir_name}/{rep_name}"
            state["completed_evaluations"][eval_key] = {
                "representation_name": rep_name,
                "source_dir": dir_name,
                "full_corpus_adversarial": adv_success,
                "v25_formal_suite": suite_success,
                "completed_at": datetime.now().isoformat(),
                "adv_output_dir": str(output_base / f"full_corpus_174k_{rep_name}"),
                "suite_output_dir": str(output_base / f"v25_formal_suite_{rep_name}")
            }
        
        save_state(state)


def main():
    """Main monitoring loop."""
    logger.info("=" * 60)
    logger.info("174k Evaluation Monitor Started")
    logger.info(f"Watching: {LEGAL_DISTANCE_RESULTS_ROOT}")
    logger.info(f"Expected representations: {len(ALL_EXPECTED)} ({len(COMPLETED_TFIDF)} TF-IDF completed, {len(AWAITED_REPRESENTATIONS)} awaited)")
    logger.info("=" * 60)
    
    state = load_state()
    
    # Initial scan
    found = scan_for_representations()
    if found:
        logger.info(f"Initial scan found: {list(found.keys())}")
        execute_evaluation_suite(found, state)
    else:
        logger.info("No 174k representations found yet")
    
    save_state(state)
    
    # Print summary
    ready_status = check_representations_ready(found)
    logger.info("\nREPRESENTATION READINESS:")
    logger.info("  COMPLETED (TF-IDF family at 174k):")
    for rep in COMPLETED_TFIDF:
        status = "✓" if ready_status.get(rep, False) else "✗"
        logger.info(f"    {status} {rep}")
    logger.info("  AWAITED (dense embeddings, citation roles, linear hybrids):")
    for cat in ["awaited_dense_174k", "awaited_citation_roles_174k", "awaited_linear_hybrids_174k"]:
        if cat in EXPECTED_REPRESENTATIONS:
            logger.info(f"    {cat}:")
            for rep in EXPECTED_REPRESENTATIONS[cat]:
                status = "✓" if ready_status.get(rep, False) else "✗"
                logger.info(f"      {status} {rep}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())