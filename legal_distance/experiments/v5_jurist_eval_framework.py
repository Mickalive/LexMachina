#!/usr/bin/env python3
"""
Legal Distance Lane v5 - Jurist Pairwise Evaluation Framework

Sets up a framework for jurist pairwise evaluation of map modes vs baseline.
This creates the evaluation infrastructure (question generation, UI specification,
sampling strategy) for future human studies.
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
SCALE_RESULTS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/scale_test/scale_test_all_results.json")
FULL_CORPUS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/jurist_eval")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class EvaluationQuestion:
    question_id: str
    anchor_decision_id: str
    anchor_title: str
    candidate_a_id: str
    candidate_a_title: str
    candidate_b_id: str
    candidate_b_title: str
    mode_a: str  # map mode for candidate A
    mode_b: str  # map mode for candidate B
    expected_preference: str  # 'A', 'B', or 'unknown'
    rationale: str
    category: str  # 'fact_similarity', 'legal_issue', 'statute_tracking', 'precedent_reasoning', 'general'

@dataclass
class JuristSession:
    session_id: str
    jurist_id: str
    questions: List[str]  # question_ids
    responses: Dict[str, str]  # question_id -> 'A' or 'B' or 'equal'
    timestamps: Dict[str, float]

def load_scale_results() -> Dict[str, Any]:
    with open(SCALE_RESULTS, 'r') as f:
        return json.load(f)

def load_corpus() -> List[Dict]:
    corpus = []
    with open(FULL_CORPUS, 'r') as f:
        for line in f:
            corpus.append(json.loads(line))
    return corpus

def get_decision_summary(decision: Dict) -> str:
    """Create a human-readable summary of a decision."""
    parts = []
    if decision.get('legal_area'):
        parts.append(f"Area: {decision['legal_area']}")
    if decision.get('outcome'):
        parts.append(f"Outcome: {decision['outcome']}")
    if decision.get('branch'):
        parts.append(f"Branch: {decision['branch']}")
    if decision.get('year'):
        parts.append(f"Year: {decision['year']}")
    if decision.get('language'):
        parts.append(f"Lang: {decision['language']}")
    return " | ".join(parts)

def select_anchor_decisions(corpus: List[Dict], n: int = 50) -> List[Dict]:
    """Select diverse anchor decisions for evaluation."""
    # Stratify by branch and language
    by_branch_lang = defaultdict(list)
    for d in corpus:
        branch = d.get('branch', 'unknown')
        lang = d.get('language', 'unknown')
        by_branch_lang[(branch, lang)].append(d)
    
    anchors = []
    for (branch, lang), decisions in by_branch_lang.items():
        # Take up to 3 per stratum
        sample = random.sample(decisions, min(3, len(decisions)))
        anchors.extend(sample)
        if len(anchors) >= n:
            break
    
    return anchors[:n]

def get_top_neighbors(
    embeddings: np.ndarray, 
    anchor_idx: int, 
    k: int = 10,
    exclude_self: bool = True
) -> List[Tuple[int, float]]:
    """Get top-k nearest neighbors for a decision."""
    from sklearn.metrics.pairwise import cosine_similarity
    sim = cosine_similarity(embeddings[anchor_idx:anchor_idx+1], embeddings)[0]
    if exclude_self:
        sim[anchor_idx] = -1
    top_k = np.argsort(sim)[::-1][:k]
    return [(idx, float(sim[idx])) for idx in top_k]

def generate_evaluation_questions(
    corpus: List[Dict],
    scale_results: Dict[str, Any],
    n_anchors: int = 30,
    n_neighbors: int = 5
) -> List[EvaluationQuestion]:
    """Generate pairwise evaluation questions."""
    
    # Load embeddings for each mode
    mode_embeddings = {}
    for mode_name, results in scale_results.items():
        if 'error' in results:
            continue
        emb_path = Path(f"/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/scale_test") / f"embeddings_{mode_name}.npy"
        if not emb_path.exists():
            # Try alternative naming
            emb_path = Path(f"/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/scale_test/scale_{mode_name}_embeddings.npy")
        # We don't have saved embeddings, so we'll use a placeholder approach
        # For the framework, we'll define the structure without actual embeddings
    
    # Define the map modes to compare
    map_modes = [
        ("baseline_debiased_citation_blended", "Baseline (debiased_citation_blended)"),
        ("sachverhalt_tfidf", "Sachverhalt/Facts Mode"),
        ("norm_embeddings", "Norm/Statute Embeddings Mode"),
        ("erwaegungen_tfidf", "Erwägungen/Reasoning Mode"),
        ("hybrid_erwaegungen_07", "Hybrid: 70% Reasoning + 30% Baseline"),
        ("legal_issues_outcomes", "Legal Issues + Outcomes Mode"),
        ("cited_decisions_tfidf", "Cited Decisions Mode"),
    ]
    
    anchors = select_anchor_decisions(corpus, n_anchors)
    questions = []
    
    question_id = 0
    for anchor in anchors:
        anchor_id = anchor['decision_id']
        anchor_title = get_decision_summary(anchor)
        
        # For each pair of modes, create a question
        for i, (mode_a_key, mode_a_name) in enumerate(map_modes):
            for mode_b_key, mode_b_name in map_modes[i+1:]:
                # Create a question: "Which neighbor is more legally relevant to the anchor?"
                # In practice, this would use actual neighbor retrieval from each mode
                # For the framework, we create the structure
                
                q = EvaluationQuestion(
                    question_id=f"q_{question_id:04d}",
                    anchor_decision_id=anchor_id,
                    anchor_title=anchor_title,
                    candidate_a_id=f"NEIGHBOR_FROM_{mode_a_key}",  # Placeholder
                    candidate_a_title=f"[Retrieved via {mode_a_name}]",
                    candidate_b_id=f"NEIGHBOR_FROM_{mode_b_key}",  # Placeholder
                    candidate_b_title=f"[Retrieved via {mode_b_name}]",
                    mode_a=mode_a_key,
                    mode_b=mode_b_key,
                    expected_preference="unknown",
                    rationale=f"Compare {mode_a_name} vs {mode_b_name} for legal relevance to anchor",
                    category="general",
                )
                questions.append(q)
                question_id += 1
                
                if question_id >= 200:  # Limit total questions
                    break
            if question_id >= 200:
                break
        if question_id >= 200:
            break
    
    return questions

def create_evaluation_ui_spec() -> Dict[str, Any]:
    """Create UI specification for jurist evaluation interface."""
    return {
        "title": "LexMachina Map Mode Comparison - Jurist Evaluation",
        "description": "Compare legal relevance of neighbor decisions retrieved by different map modes",
        "instructions": """
        You will be shown an anchor decision and two candidate neighbor decisions.
        Each candidate comes from a different map mode (similarity representation).
        Your task: Select which candidate is MORE legally relevant to the anchor decision.
        
        Consider:
        - Legal issue similarity (same legal question/doctrine)
        - Factual similarity (comparable fact patterns)
        - Statutory basis (same articles/norms at issue)
        - Precedent reasoning (similar legal reasoning)
        - Outcome alignment (similar holdings)
        
        Ignore: Language, procedural boilerplate, citation formatting differences.
        """,
        "question_format": {
            "anchor_display": {
                "fields": ["decision_id", "legal_area", "outcome", "branch", "year", "language", "key_facts_summary", "key_holding_summary"],
                "layout": "card"
            },
            "candidate_display": {
                "fields": ["decision_id", "legal_area", "outcome", "branch", "year", "language", "similarity_score", "shared_citations", "shared_statutes"],
                "layout": "side_by_side"
            },
            "response_options": ["A is more relevant", "B is more relevant", "Equally relevant", "Cannot determine"],
            "confidence_scale": [1, 2, 3, 4, 5],
            "optional_rationale": True,
        },
        "session_config": {
            "questions_per_session": 20,
            "estimated_time_per_question_sec": 60,
            "break_after": 10,
            "randomize_order": True,
            "randomize_left_right": True,
        },
        "jurist_requirements": {
            "min_experience_years": 3,
            "swiss_law_expertise": True,
            "languages": ["de", "fr", "it"],
        },
    }

def create_sampling_strategy() -> Dict[str, Any]:
    """Define sampling strategy for evaluation questions."""
    return {
        "anchor_selection": {
            "method": "stratified",
            "strata": ["branch", "language", "year_bucket"],
            "per_stratum": 3,
            "total_anchors": 50,
        },
        "mode_pairs": {
            "primary_comparisons": [
                ["baseline_debiased_citation_blended", "sachverhalt_tfidf"],
                ["baseline_debiased_citation_blended", "norm_embeddings"],
                ["baseline_debiased_citation_blended", "hybrid_erwaegungen_07"],
                ["sachverhalt_tfidf", "erwaegungen_tfidf"],
                ["norm_embeddings", "legal_area_tfidf"],
                ["legal_issues_outcomes", "hybrid_erwaegungen_07"],
            ],
            "exploratory_comparisons": [
                ["cited_decisions_tfidf", "erwaegungen_tfidf"],
                ["norm_embeddings", "cited_decisions_tfidf"],
            ],
        },
        "question_balancing": {
            "per_anchor_per_pair": 1,
            "max_questions_per_jurist": 30,
            "min_jurists_per_question": 3,
            "target_total_responses": 600,
        },
        "quality_control": {
            "attention_check_rate": 0.1,
            "gold_standard_questions": 5,
            "agreement_threshold": 0.67,
        },
    }

def create_analysis_plan() -> Dict[str, Any]:
    """Define statistical analysis plan for jurist evaluation results."""
    return {
        "primary_metric": "pairwise_preference_rate",
        "definition": "Proportion of times mode A preferred over mode B when both retrieved as neighbors",
        "comparisons": [
            "Each legal-signal mode vs baseline",
            "Best single signals vs each other",
            "Hybrid modes vs their component signals",
        ],
        "statistical_tests": {
            "binomial_test": "Test if preference rate != 0.5 (no preference)",
            "mcnemar_test": "Compare paired preferences across modes",
            "bootstrap_ci": "95% CI for preference rates (10000 resamples)",
        },
        "secondary_metrics": [
            "Confidence-weighted preference",
            "Agreement rate among jurists (Fleiss' kappa)",
            "Per-category preference (fact/legal/statute/precedent/outcome)",
            "Cross-language preference consistency",
        ],
        "subgroup_analyses": [
            "By jurist expertise level",
            "By anchor decision branch",
            "By anchor decision language",
            "By question category",
        ],
        "success_criteria": {
            "min_preference_rate": 0.55,  # Mode must be preferred >55% of time
            "min_statistical_significance": 0.05,
            "min_jurist_agreement": 0.6,  # Fleiss' kappa
            "min_sample_per_comparison": 30,
        },
    }

def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v5 - Jurist Pairwise Evaluation Framework")
    logger.info("=" * 70)
    
    # Load data
    logger.info("\n1. Loading corpus...")
    corpus = load_corpus()
    logger.info(f"Loaded {len(corpus)} decisions")
    
    logger.info("\n2. Loading scale test results...")
    scale_results = load_scale_results()
    logger.info(f"Loaded results for {len(scale_results)} modes")
    
    # Generate evaluation questions
    logger.info("\n3. Generating evaluation questions...")
    questions = generate_evaluation_questions(corpus, scale_results, n_anchors=30)
    logger.info(f"Generated {len(questions)} evaluation questions")
    
    # Save questions
    questions_data = [asdict(q) for q in questions]
    with open(OUTPUT_DIR / "evaluation_questions.json", 'w') as f:
        json.dump(questions_data, f, indent=2, default=str)
    
    # Create UI spec
    logger.info("\n4. Creating UI specification...")
    ui_spec = create_evaluation_ui_spec()
    with open(OUTPUT_DIR / "ui_specification.json", 'w') as f:
        json.dump(ui_spec, f, indent=2, default=str)
    
    # Create sampling strategy
    logger.info("\n5. Creating sampling strategy...")
    sampling = create_sampling_strategy()
    with open(OUTPUT_DIR / "sampling_strategy.json", 'w') as f:
        json.dump(sampling, f, indent=2, default=str)
    
    # Create analysis plan
    logger.info("\n6. Creating analysis plan...")
    analysis = create_analysis_plan()
    with open(OUTPUT_DIR / "analysis_plan.json", 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    # Create master protocol document
    protocol = {
        "protocol_version": "1.0",
        "date": "2026-08-28",
        "lane": "legal-distance",
        "factory_direction_version": 5,
        "components": {
            "evaluation_questions": f"{len(questions)} questions generated",
            "ui_specification": "Complete",
            "sampling_strategy": "Complete",
            "analysis_plan": "Complete",
        },
        "files": {
            "questions": "evaluation_questions.json",
            "ui_spec": "ui_specification.json",
            "sampling": "sampling_strategy.json",
            "analysis": "analysis_plan.json",
        },
        "next_steps": [
            "Recruit 5-10 Swiss law jurists (3+ years experience)",
            "Pilot test with 2 jurists on 10 questions each",
            "Refine UI based on pilot feedback",
            "Run full evaluation (target 600 responses)",
            "Analyze per analysis_plan.json",
            "Report results with statistical tests",
        ],
        "success_criteria": analysis["success_criteria"],
    }
    
    with open(OUTPUT_DIR / "evaluation_protocol.json", 'w') as f:
        json.dump(protocol, f, indent=2, default=str)
    
    logger.info("\n" + "=" * 70)
    logger.info("JURIST EVALUATION FRAMEWORK COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Questions generated: {len(questions)}")
    logger.info(f"Files created:")
    for name, fname in protocol["files"].items():
        logger.info(f"  - {fname}")
    
    return protocol

if __name__ == "__main__":
    main()
