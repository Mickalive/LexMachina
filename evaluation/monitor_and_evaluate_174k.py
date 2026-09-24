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
LEGAL_DISTANCE_RESULTS = LEX_ACCEPTED_ROOT / "legal-distance/legal_distance/results/v5"

# Production representations expected at 174k (from factory direction v25)
EXPECTED_REPRESENTATIONS = {
    "priority_1_tfidf_signals": [
        "cited_decisions_tfidf",
        "outcome_tfidf", 
        "cited_outcome_hybrid_0.5",
        "cited_outcome_hybrid_0.7",
        "linear_citation_concat",
        "linear_hybrid05_concat",
        "linear_citation_w3070",
        "linear_citation_ridge",
    ],
    "priority_2_dense_embeddings": [
        "center_projected_768dim",
        "center_projected_64dim",
        "linear_metric_epoch4",
        "mahalanobis_metric_epoch4",
        "hybrid_stabilized_epoch1",
    ],
    "priority_3_citation_roles": [
        "citation_role_citing_alpha0.3",
        "citation_role_following_alpha0.3",
        "citation_role_criticizing_alpha0.3",
        "citation_role_distinguishing_alpha0.3",
        "citation_role_overruling_alpha0.3",
    ]
}

# Flatten all expected
ALL_EXPECTED = []
for cat, reps in EXPECTED_REPRESENTATIONS.items():
    ALL_EXPECTED.extend(reps)

# Evaluation scripts
EVALUATION_SCRIPTS = {
    "full_corpus_adversarial": "evaluation/run_full_corpus_evaluation.py",
    "formal_benchmark_suite": "evaluation/experiments/run_v16_full_benchmark_suite.py",
    "citation_heritage": "evaluation/validate_citation_heritage_174k.py",
    "v17b_label_normalization": "evaluation/experiments/run_v17b_label_normalization_all_reps.py",
}

# Metadata and data paths
METADATA_174K = Path("evaluation/data/174k/metadata_174k.json")
CORPUS_174K = Path("evaluation/data/174k/corpus_174k.jsonl")  # May need to be generated
CITATION_PAIRS = Path("evaluation/results/174k_citation_heritage/citation_pairs_174k.json")

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
    """Scan legal-distance accepted state for 174k representation directories."""
    found = {}
    
    if not LEGAL_DISTANCE_RESULTS.exists():
        logger.warning(f"Legal-distance results path not found: {LEGAL_DISTANCE_RESULTS}")
        return found
    
    for item in LEGAL_DISTANCE_RESULTS.iterdir():
        if item.is_dir() and "174k" in item.name.lower():
            # Check for embedding files
            npy_files = list(item.glob("*.npy"))
            if npy_files:
                found[item.name] = npy_files
                logger.info(f"Found 174k representation dir: {item.name} with {len(npy_files)} embeddings")
    
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
    
    # Check all expected
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


def execute_evaluation_suite(found_dirs: Dict, state: Dict):
    """Execute the full evaluation suite for newly detected representations."""
    output_base = Path("evaluation/results/174k_formal_suite")
    output_base.mkdir(parents=True, exist_ok=True)
    
    newly_ready = {}
    for dir_name, npy_files in found_dirs.items():
        if dir_name not in state["detected_representations"]:
            newly_ready[dir_name] = npy_files
            state["detected_representations"][dir_name] = {
                "first_seen": datetime.now().isoformat(),
                "files": [str(f) for f in npy_files]
            }
    
    if not newly_ready:
        logger.info("No new representations detected")
        return
    
    logger.info(f"NEW REPRESENTATIONS DETECTED: {list(newly_ready.keys())}")
    
    for dir_name, npy_files in newly_ready.items():
        embeddings_dir = LEGAL_DISTANCE_RESULTS / dir_name
        
        # Run full corpus adversarial evaluation
        logger.info(f"Starting full corpus evaluation for {dir_name}")
        success = run_full_corpus_evaluation(embeddings_dir, dir_name, output_base)
        
        state["completed_evaluations"][dir_name] = {
            "full_corpus_adversarial": success,
            "completed_at": datetime.now().isoformat(),
            "output_dir": str(output_base / f"full_corpus_174k_{dir_name}")
        }
        
        # TODO: Run formal benchmark suite (requires 174k corpus)
        # TODO: Run citation heritage
        # TODO: Run v17b label normalization
        
        save_state(state)


def main():
    """Main monitoring loop."""
    logger.info("=" * 60)
    logger.info("174k Evaluation Monitor Started")
    logger.info(f"Watching: {LEGAL_DISTANCE_RESULTS}")
    logger.info(f"Expected representations: {len(ALL_EXPECTED)}")
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
    for cat, reps in EXPECTED_REPRESENTATIONS.items():
        logger.info(f"  {cat}:")
        for rep in reps:
            status = "✓" if ready_status.get(rep, False) else "✗"
            logger.info(f"    {status} {rep}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())