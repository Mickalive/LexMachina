"""
Benchmark Harness - Core evaluation infrastructure.

Provides a standardized interface for running evaluation benchmarks
against legal distance representations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import json
import uuid
from pathlib import Path
from dataclasses import is_dataclass, asdict


class EvidenceTier(Enum):
    UNTESTED = "UNTESTED"
    EXPLORATORY = "EXPLORATORY"
    REPRODUCED = "REPRODUCED"
    ACCEPTED = "ACCEPTED"


class BenchmarkStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    benchmark_id: str
    benchmark_name: str
    status: BenchmarkStatus
    timestamp: str
    duration_seconds: float
    metrics: Dict[str, float]
    details: Dict[str, Any]
    evidence_tier: EvidenceTier = EvidenceTier.UNTESTED
    baseline_comparison: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        def serialize(obj):
            if is_dataclass(obj):
                return asdict(obj)
            elif isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [serialize(v) for v in obj]
            elif isinstance(obj, (set, frozenset)):
                return list(obj)
            elif isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, (str, int, float, bool)) or obj is None:
                return obj
            elif hasattr(obj, '__dict__'):
                return vars(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        def serialize_dict(d):
            return {k: serialize(v) for k, v in d.items()}

        def serialize_list(l):
            return [serialize(v) for v in l]

        def serialize_val(v):
            if isinstance(v, dict):
                return serialize_dict(v)
            elif isinstance(v, list):
                return serialize_list(v)
            else:
                return serialize(v)

        return {
            "benchmark_id": self.benchmark_id,
            "benchmark_name": self.benchmark_name,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "metrics": self.metrics,
            "details": serialize_val(self.details),
            "evidence_tier": self.evidence_tier.value,
            "baseline_comparison": self.baseline_comparison,
            "error_message": self.error_message,
            "provenance": serialize_val(self.provenance),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkResult":
        data = data.copy()
        data["status"] = BenchmarkStatus(data["status"])
        data["evidence_tier"] = EvidenceTier(data["evidence_tier"])
        return cls(**data)


class BaseBenchmark(ABC):
    """Abstract base class for all evaluation benchmarks."""

    def __init__(self, name: str, config: Optional[Any] = None):
        self.name = name
        # Convert config to dict if it's a dataclass or has __dict__
        if config is None:
            self.config = {}
        elif hasattr(config, '__dataclass_fields__'):
            # It's a dataclass
            import dataclasses
            self.config = dataclasses.asdict(config)
        elif hasattr(config, '__dict__'):
            self.config = vars(config)
        else:
            self.config = config
        self.benchmark_id = str(uuid.uuid4())[:8]

    @abstractmethod
    def run(self, representation_fn: Callable, corpus: Any, **kwargs) -> BenchmarkResult:
        """Run the benchmark against a representation function and corpus."""
        pass

    @abstractmethod
    def get_baseline_metrics(self) -> Dict[str, float]:
        """Return expected baseline metrics for comparison."""
        pass

    def _create_result(
        self,
        status: BenchmarkStatus,
        metrics: Dict[str, float],
        details: Dict[str, Any],
        duration: float,
        evidence_tier: EvidenceTier = EvidenceTier.EXPLORATORY,
        baseline_comparison: Optional[Dict[str, float]] = None,
        error_message: Optional[str] = None,
    ) -> BenchmarkResult:
        return BenchmarkResult(
            benchmark_id=self.benchmark_id,
            benchmark_name=self.name,
            status=status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            duration_seconds=duration,
            metrics=metrics,
            details=details,
            evidence_tier=evidence_tier,
            baseline_comparison=baseline_comparison,
            error_message=error_message,
            provenance={
                "config": self.config,
                "benchmark_class": self.__class__.__name__,
            },
        )


class BenchmarkHarness:
    """Orchestrates multiple benchmarks and manages results."""

    def __init__(self, output_dir: str = "evaluation/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.benchmarks: List[BaseBenchmark] = []
        self.results: List[BenchmarkResult] = []

    def register(self, benchmark: BaseBenchmark) -> "BenchmarkHarness":
        """Register a benchmark to run."""
        self.benchmarks.append(benchmark)
        return self

    def run_all(
        self,
        representation_fn: Callable,
        corpus: Any,
        save_results: bool = True,
        **kwargs,
    ) -> List[BenchmarkResult]:
        """Run all registered benchmarks."""
        self.results = []
        for benchmark in self.benchmarks:
            print(f"Running benchmark: {benchmark.name}...")
            try:
                result = benchmark.run(representation_fn, corpus, **kwargs)
                self.results.append(result)
                print(f"  {benchmark.name}: {result.status.value}")
                if result.error_message:
                    print(f"  Error: {result.error_message}")
            except Exception as e:
                error_result = BenchmarkResult(
                    benchmark_id=str(uuid.uuid4())[:8],
                    benchmark_name=benchmark.name,
                    status=BenchmarkStatus.ERROR,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    duration_seconds=0.0,
                    metrics={},
                    details={"exception": str(e)},
                    error_message=str(e),
                )
                self.results.append(error_result)
                print(f"  {benchmark.name}: ERROR - {e}")

        if save_results:
            self.save_results()

        return self.results

    def save_results(self, filename: Optional[str] = None) -> Path:
        """Save results to JSON file."""
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"

        filepath = self.output_dir / filename
        data = {
            "run_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "results": [r.to_dict() for r in self.results],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return filepath

    def load_results(self, filepath: Path) -> List[BenchmarkResult]:
        """Load results from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        self.results = [BenchmarkResult.from_dict(r) for r in data["results"]]
        return self.results

    def summary(self) -> Dict[str, Any]:
        """Generate a summary of all results."""
        if not self.results:
            return {"message": "No results available"}

        passed = sum(1 for r in self.results if r.status == BenchmarkStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == BenchmarkStatus.FAILED)
        errors = sum(1 for r in self.results if r.status == BenchmarkStatus.ERROR)

        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "benchmarks": [
                {
                    "name": r.benchmark_name,
                    "status": r.status.value,
                    "metrics": r.metrics,
                    "evidence_tier": r.evidence_tier.value,
                }
                for r in self.results
            ],
        }