"""
LexMachina Evaluation Runner

Runs the full evaluation suite on a legal distance representation.
Can run on synthetic data for development or real corpus data.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add evaluation to path
sys.path.insert(0, str(Path(__file__).parent))

from evaluation.benchmarks.core import BenchmarkHarness
from evaluation.tests.neighbor_relevance import NeighborRelevanceTest, NeighborRelevanceConfig
from evaluation.tests.boilerplate_resistance import BoilerplateResistanceTest, BoilerplateConfig
from evaluation.tests.multilingual_invariance import MultilingualInvarianceTest, MultilingualConfig
from evaluation.tests.stability import CorpusStabilityTest, StabilityConfig
from evaluation.tests.hierarchy_coherence import HierarchyCoherenceTest, HierarchyConfig
from evaluation.data.synthetic import create_synthetic_corpus, SyntheticCorpusConfig


def run_synthetic_evaluation(
    output_dir: str = "evaluation/results",
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run evaluation on synthetic data."""
    print("=" * 60)
    print("LexMachina Evaluation - Synthetic Data Run")
    print("=" * 60)

    # Create synthetic corpus
    print("\n1. Generating synthetic corpus...")
    synth_config = SyntheticCorpusConfig(**(config_overrides.get("corpus", {}) if config_overrides else {}))
    decisions, representation_fn, corpus, ground_truth = create_synthetic_corpus(synth_config)
    print(f"   Generated {len(decisions)} synthetic decisions")
    print(f"   Embedding dimension: {synth_config.embedding_dim}")
    print(f"   Legal areas: {synth_config.num_legal_areas}")
    print(f"   Jurivoc concepts: {synth_config.num_jurivoc_concepts}")

    # Set up benchmark harness
    print("\n2. Setting up benchmark harness...")
    harness = BenchmarkHarness(output_dir=output_dir)

    # Configure tests
    neighbor_config = NeighborRelevanceConfig(**(config_overrides.get("neighbor_relevance", {}) if config_overrides else {}))
    boilerplate_config = BoilerplateConfig(**(config_overrides.get("boilerplate", {}) if config_overrides else {}))
    multilingual_config = MultilingualConfig(**(config_overrides.get("multilingual", {}) if config_overrides else {}))
    stability_config = StabilityConfig(**(config_overrides.get("stability", {}) if config_overrides else {}))
    hierarchy_config = HierarchyConfig(**(config_overrides.get("hierarchy", {}) if config_overrides else {}))

    # Register tests
    harness.register(NeighborRelevanceTest(neighbor_config))
    harness.register(BoilerplateResistanceTest(boilerplate_config))
    harness.register(MultilingualInvarianceTest(multilingual_config))
    harness.register(CorpusStabilityTest(stability_config))
    harness.register(HierarchyCoherenceTest(hierarchy_config))

    print(f"   Registered {len(harness.benchmarks)} benchmarks")

    # Run all benchmarks
    print("\n3. Running benchmarks...")
    results = harness.run_all(representation_fn, corpus, ground_truth=ground_truth)

    # Print summary
    print("\n4. Results Summary:")
    print("-" * 60)
    summary = harness.summary()
    print(f"   Total benchmarks: {summary['total']}")
    print(f"   Passed: {summary['passed']}")
    print(f"   Failed: {summary['failed']}")
    print(f"   Errors: {summary['errors']}")
    print()

    for bm in summary['benchmarks']:
        status_icon = "✓" if bm['status'] == 'PASSED' else "✗" if bm['status'] == 'FAILED' else "⚠"
        print(f"   {status_icon} {bm['name']}: {bm['status']}")
        for metric, value in bm['metrics'].items():
            if isinstance(value, float):
                print(f"      {metric}: {value:.4f}")
            else:
                print(f"      {metric}: {value}")

    # Save detailed results
    results_file = harness.save_results("synthetic_evaluation_results.json")
    print(f"\n   Detailed results saved to: {results_file}")

    # Save ground truth for reference
    gt_file = Path(output_dir) / "synthetic_ground_truth.json"
    with open(gt_file, "w") as f:
        json.dump(ground_truth, f, indent=2, default=str)
    print(f"   Ground truth saved to: {gt_file}")

    return {
        "summary": summary,
        "results_file": str(results_file),
        "ground_truth_file": str(gt_file),
    }


def run_real_corpus_evaluation(
    representation_fn,
    corpus,
    output_dir: str = "evaluation/results",
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run evaluation on real corpus data."""
    print("=" * 60)
    print("LexMachina Evaluation - Real Corpus Run")
    print("=" * 60)

    # Set up benchmark harness
    print("\n1. Setting up benchmark harness...")
    harness = BenchmarkHarness(output_dir=output_dir)

    # Configure tests
    neighbor_config = NeighborRelevanceConfig(**(config_overrides.get("neighbor_relevance", {}) if config_overrides else {}))
    boilerplate_config = BoilerplateConfig(**(config_overrides.get("boilerplate", {}) if config_overrides else {}))
    multilingual_config = MultilingualConfig(**(config_overrides.get("multilingual", {}) if config_overrides else {}))
    stability_config = StabilityConfig(**(config_overrides.get("stability", {}) if config_overrides else {}))
    hierarchy_config = HierarchyConfig(**(config_overrides.get("hierarchy", {}) if config_overrides else {}))

    # Register tests
    harness.register(NeighborRelevanceTest(neighbor_config))
    harness.register(BoilerplateResistanceTest(boilerplate_config))
    harness.register(MultilingualInvarianceTest(multilingual_config))
    harness.register(CorpusStabilityTest(stability_config))
    harness.register(HierarchyCoherenceTest(hierarchy_config))

    print(f"   Registered {len(harness.benchmarks)} benchmarks")

    # Run all benchmarks
    print("\n2. Running benchmarks...")
    results = harness.run_all(representation_fn, corpus)

    # Print summary
    print("\n3. Results Summary:")
    print("-" * 60)
    summary = harness.summary()
    print(f"   Total benchmarks: {summary['total']}")
    print(f"   Passed: {summary['passed']}")
    print(f"   Failed: {summary['failed']}")
    print(f"   Errors: {summary['errors']}")
    print()

    for bm in summary['benchmarks']:
        status_icon = "✓" if bm['status'] == 'PASSED' else "✗" if bm['status'] == 'FAILED' else "⚠"
        print(f"   {status_icon} {bm['name']}: {bm['status']}")
        for metric, value in bm['metrics'].items():
            if isinstance(value, float):
                print(f"      {metric}: {value:.4f}")
            else:
                print(f"      {metric}: {value}")

    # Save detailed results
    results_file = harness.save_results("real_corpus_evaluation_results.json")
    print(f"\n   Detailed results saved to: {results_file}")

    return {
        "summary": summary,
        "results_file": str(results_file),
    }


def main():
    parser = argparse.ArgumentParser(description="Run LexMachina evaluation suite")
    parser.add_argument(
        "--mode",
        choices=["synthetic", "real"],
        default="synthetic",
        help="Run mode: synthetic (default) or real corpus",
    )
    parser.add_argument(
        "--output-dir",
        default="evaluation/results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="JSON config file for test parameters",
    )
    parser.add_argument(
        "--representation-module",
        type=str,
        help="Python module containing representation_fn for real corpus mode",
    )
    parser.add_argument(
        "--corpus-module",
        type=str,
        help="Python module containing corpus object for real corpus mode",
    )

    args = parser.parse_args()

    # Load config overrides
    config_overrides = {}
    if args.config:
        with open(args.config, "r") as f:
            config_overrides = json.load(f)

    if args.mode == "synthetic":
        result = run_synthetic_evaluation(args.output_dir, config_overrides)
    else:
        if not args.representation_module or not args.corpus_module:
            print("Error: --representation-module and --corpus-module required for real mode")
            sys.exit(1)

        # Import representation and corpus
        import importlib
        rep_module = importlib.import_module(args.representation_module)
        corpus_module = importlib.import_module(args.corpus_module)

        representation_fn = rep_module.representation_fn
        corpus = corpus_module.corpus

        result = run_real_corpus_evaluation(
            representation_fn, corpus, args.output_dir, config_overrides
        )

    # Exit with appropriate code
    if result["summary"]["failed"] > 0 or result["summary"]["errors"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()