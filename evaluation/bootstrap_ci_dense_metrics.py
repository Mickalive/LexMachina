#!/usr/bin/env python3
"""
Bootstrap Confidence Intervals for Dense Embedding Metrics
Computes 95% CIs for citation heritage AUC and cross-lingual section metrics.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import sys

# Set seed for reproducibility
np.random.seed(42)


def bootstrap_auc_ci(y_true: np.ndarray, y_score: np.ndarray, n_bootstrap: int = 10000, alpha: float = 0.05) -> Tuple[float, float, float]:
    """
    Bootstrap confidence interval for AUC-ROC.
    Returns (point_estimate, ci_lower, ci_upper)
    """
    from sklearn.metrics import roc_auc_score
    
    point = roc_auc_score(y_true, y_score)
    
    n = len(y_true)
    bootstrap_aucs = []
    
    for _ in range(n_bootstrap):
        indices = np.random.choice(n, n, replace=True)
        y_true_boot = y_true[indices]
        y_score_boot = y_score[indices]
        
        # Need both classes for AUC
        if len(np.unique(y_true_boot)) < 2:
            continue
        
        try:
            auc = roc_auc_score(y_true_boot, y_score_boot)
            bootstrap_aucs.append(auc)
        except ValueError:
            continue
    
    bootstrap_aucs = np.array(bootstrap_aucs)
    ci_lower = np.percentile(bootstrap_aucs, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_aucs, 100 * (1 - alpha / 2))
    
    return point, ci_lower, ci_upper


def bootstrap_mean_ci(values: np.ndarray, n_bootstrap: int = 10000, alpha: float = 0.05) -> Tuple[float, float, float]:
    """
    Bootstrap confidence interval for mean.
    Returns (point_estimate, ci_lower, ci_upper)
    """
    point = np.mean(values)
    n = len(values)
    bootstrap_means = []
    
    for _ in range(n_bootstrap):
        indices = np.random.choice(n, n, replace=True)
        bootstrap_means.append(np.mean(values[indices]))
    
    bootstrap_means = np.array(bootstrap_means)
    ci_lower = np.percentile(bootstrap_means, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_means, 100 * (1 - alpha / 2))
    
    return point, ci_lower, ci_upper


def compute_citation_heritage_ci():
    """Compute CIs for dense embedding citation heritage AUC at 22-year scale."""
    
    # Load the 22-year dense citation heritage results
    results_path = Path("results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json")
    with open(results_path) as f:
        data = json.load(f)
    
    print("=" * 80)
    print("CITATION HERITAGE AUC - BOOTSTRAP 95% CIs (22-year / 144k)")
    print("=" * 80)
    
    # We need to reconstruct y_true and y_score from the saved data
    # The saved data has num_positive_pairs=344, num_negative_pairs=500
    # But not the individual scores. We'll simulate from the reported statistics.
    
    # For a proper bootstrap, we'd need the raw similarity scores.
    # Since we only have aggregate metrics, we'll use a parametric bootstrap
    # based on the reported means and the assumption of normal distributions.
    
    results = {}
    
    for rep_name, rep_data in data.items():
        metrics = rep_data["metrics"]
        n_pos = metrics["num_positive_pairs"]
        n_neg = metrics["num_negative_pairs"]
        pos_mean = metrics["positive_mean_sim"]
        neg_mean = metrics["negative_mean_sim"]
        auc_point = metrics["auc_roc"]
        
        # Simulate score distributions for bootstrap
        # Using the fact that AUC = P(score_pos > score_neg)
        # We can approximate by assuming normal distributions
        # with means = pos_mean, neg_mean and std derived from AUC
        
        # For normal distributions, AUC = Phi((mu_pos - mu_neg) / sqrt(sigma_pos^2 + sigma_neg^2))
        # Assume equal variance for simplicity
        from scipy.stats import norm
        
        # Invert to find implied standardized difference
        z = norm.ppf(auc_point)
        # z = (mu_pos - mu_neg) / (sqrt(2) * sigma) for equal variance
        sigma = (pos_mean - neg_mean) / (z * np.sqrt(2)) if z > 0 else 0.1
        
        # Generate bootstrap samples
        np.random.seed(42)
        bootstrap_aucs = []
        
        for _ in range(10000):
            pos_scores = np.random.normal(pos_mean, sigma, n_pos)
            neg_scores = np.random.normal(neg_mean, sigma, n_neg)
            
            y_true = np.concatenate([np.ones(n_pos), np.zeros(n_neg)])
            y_score = np.concatenate([pos_scores, neg_scores])
            
            try:
                from sklearn.metrics import roc_auc_score
                auc = roc_auc_score(y_true, y_score)
                bootstrap_aucs.append(auc)
            except ValueError:
                continue
        
        bootstrap_aucs = np.array(bootstrap_aucs)
        ci_lower = np.percentile(bootstrap_aucs, 2.5)
        ci_upper = np.percentile(bootstrap_aucs, 97.5)
        
        results[rep_name] = {
            "point": auc_point,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "n_pos": n_pos,
            "n_neg": n_neg
        }
        
        print(f"\n{rep_name}:")
        print(f"  AUC = {auc_point:.4f} [{ci_lower:.4f}, {ci_upper:.4f}]")
        print(f"  n_pos={n_pos}, n_neg={n_neg}")
        print(f"  PASS (>0.75): {ci_lower > 0.75}")
    
    return results


def compute_cross_lingual_ci():
    """Compute CIs for cross-lingual section metrics."""
    
    results_path = Path("results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json")
    with open(results_path) as f:
        data = json.load(f)
    
    print("\n" + "=" * 80)
    print("CROSS-LINGUAL SECTION METRICS - BOOTSTRAP 95% CIs")
    print("=" * 80)
    
    # For cross-lingual metrics, we need per-decision scores
    # The saved data only has aggregate means. We'll use a parametric bootstrap
    # assuming the per-decision cross_lang_same_branch follows a beta distribution.
    
    sections = ["sachverhalt", "dispositiv", "erwaegungen"]
    representations = ["center_projected_768", "center_projected_64", "raw_768"]
    
    thresholds = {
        "sachverhalt": 0.20,
        "dispositiv": 0.10,
        "erwaegungen": 0.10
    }
    
    results = {}
    
    for section in sections:
        sec_data = data[section]
        n_decisions = sec_data.get("n_decisions", 0)
        coverage = sec_data.get("coverage", 0)
        
        print(f"\n--- {section.upper()} (n={n_decisions}, coverage={coverage:.1%}) ---")
        
        for rep in representations:
            if rep not in sec_data:
                continue
            
            rep_data = sec_data[rep]
            clq = rep_data["cross_language_neighbor_quality"]
            point = clq["cross_lang_same_branch_mean"]
            
            # Parametric bootstrap: assume per-decision indicator ~ Bernoulli(p)
            # where p = point. For k=10 neighbors, the mean is average of 10 Bernoullis.
            # Variance of mean of k Bernoullis = p*(1-p)/k
            k = clq.get("k", 10)
            
            # Simulate per-decision means
            np.random.seed(42)
            bootstrap_means = []
            
            for _ in range(10000):
                # Each decision: k Bernoulli trials
                decision_means = np.random.binomial(k, point, n_decisions) / k
                bootstrap_means.append(np.mean(decision_means))
            
            bootstrap_means = np.array(bootstrap_means)
            ci_lower = np.percentile(bootstrap_means, 2.5)
            ci_upper = np.percentile(bootstrap_means, 97.5)
            
            threshold = thresholds[section]
            status = "PASS" if ci_lower > threshold else ("MARGINAL" if point > threshold else "FAIL")
            
            key = f"{section}_{rep}"
            results[key] = {
                "point": point,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "threshold": threshold,
                "status": status,
                "n_decisions": n_decisions,
                "coverage": coverage
            }
            
            print(f"  {rep}: {point:.4f} [{ci_lower:.4f}, {ci_upper:.4f}] threshold={threshold} → {status}")
    
    return results


def main():
    print("Bootstrap Confidence Intervals for Dense Embedding Metrics")
    print("Factory Direction v34 | Evaluation Lane | 2026-10-06")
    print()
    
    # Citation heritage AUC CIs
    ch_results = compute_citation_heritage_ci()
    
    # Cross-lingual section CIs
    cl_results = compute_cross_lingual_ci()
    
    # Save combined results
    output = {
        "citation_heritage_auc": ch_results,
        "cross_lingual_sections": cl_results,
        "method": "Parametric bootstrap (10,000 iterations) with normal/Bernoulli assumptions",
        "seed": 42,
        "note": "CIs computed from aggregate statistics; raw per-pair/per-decision scores would yield tighter CIs"
    }
    
    output_path = Path("results/evaluation/bootstrap_ci_dense_metrics_20261006.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\nResults saved to: {output_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()