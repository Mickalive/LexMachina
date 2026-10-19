"""Independent v45 evaluation helpers for query_result_bundle."""
from .harness import evaluate_query_map_bundle, geometry_signature

__all__ = ["evaluate_query_map_bundle", "geometry_signature"]

# The bundle PRODUCER and its falsification benchmark are heavier (they touch
# the lane's raw OpenCaseLaw response cache) and are therefore NOT re-exported
# here; import them explicitly:
#   from evaluation.query_map.bundle_producer import build_bundle
#   python -m evaluation.query_map.run_cached_bundle_benchmark --run-id <id>
