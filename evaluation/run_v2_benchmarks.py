#!/usr/bin/env python3
"""
Evaluation v2 Complete Benchmark Runner

Runs all v2 benchmarks in sequence:
1. Jurivoc descriptor integration
2. Scale benchmarks (frozen + recomputed PCA)
3. Cross-language transfer stability
4. Jurist usability simulation
"""

import subprocess
import sys
import json
from pathlib import Path


def run_benchmark(script_path: str, args: list, description: str) -> bool:
    """Run a benchmark script and return success status."""
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"Command: python {script_path} {' '.join(args)}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path] + args,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=300
        )
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}", file=sys.stderr)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: {description} exceeded 5 minutes", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: {description} failed with {e}", file=sys.stderr)
        return False


def main():
    print("=" * 70)
    print("EVALUATION v2 COMPLETE BENCHMARK SUITE")
    print("=" * 70)
    print("Running all v2 benchmarks on debiased_citation_blended representation")
    
    results = {}
    
    # 1. Jurivoc Benchmarks
    success = run_benchmark(
        "evaluation/tests/jurivoc_benchmarks.py",
        ["--representation", "debiased_citation_blended", "--output", "results/jurivoc_benchmark_results.json"],
        "Jurivoc Descriptor Integration Benchmarks"
    )
    results["jurivoc"] = success
    
    # 2. Scale Benchmarks (Frozen PCA)
    success = run_benchmark(
        "evaluation/tests/scale_benchmarks_frozen.py",
        ["--output", "results/scale_benchmark_frozen_results.json"],
        "Scale Benchmarks (Frozen PCA - Production Mode)"
    )
    results["scale_frozen"] = success
    
    # 3. Scale Benchmarks (Recomputed PCA)
    success = run_benchmark(
        "evaluation/tests/scale_benchmarks.py",
        ["--output", "results/scale_benchmark_results.json"],
        "Scale Benchmarks (Recomputed PCA - Dev Mode)"
    )
    results["scale_recomputed"] = success
    
    # 4. Cross-Language Benchmarks
    success = run_benchmark(
        "evaluation/tests/cross_language_benchmarks.py",
        ["--output", "results/cross_language_benchmark_results.json"],
        "Cross-Language Transfer Stability Benchmarks"
    )
    results["cross_language"] = success
    
    # 5. Jurist Usability Simulation
    success = run_benchmark(
        "evaluation/tests/jurist_usability.py",
        ["--output", "results/jurist_usability_results.json"],
        "Jurist Usability Simulation Benchmarks"
    )
    results["jurist_usability"] = success
    
    # Summary
    print("\n" + "=" * 70)
    print("V2 BENCHMARK SUITE SUMMARY")
    print("=" * 70)
    for name, success in results.items():
        status = "✅ COMPLETED" if success else "❌ FAILED"
        print(f"  {name}: {status}")
    
    all_success = all(results.values())
    print(f"\nOverall: {'ALL COMPLETED' if all_success else 'SOME FAILED'}")
    
    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)