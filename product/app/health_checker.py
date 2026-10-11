"""
LexMachina Representation Health Checker
Graceful degradation and health monitoring for map representations.
"""
import time
from typing import Dict, List, Optional, Any

from .map_loader import MapLoader, MapState


class RepresentationHealthChecker:
    """Health checker for map representations.

    Reports per-representation status including zoom-level integrity,
    cluster coverage, and position coverage so the server can degrade
    gracefully instead of crashing when a representation fails.
    """

    # Minimum thresholds for a representation to be considered healthy
    MIN_ZOOM_LEVELS = 2
    MIN_CLUSTER_COVERAGE = 0.9
    MIN_POSITION_COVERAGE = 0.9

    def check_representation_health(
        self, representation: str, map_loader: MapLoader
    ) -> Dict[str, Any]:
        """Check the health of a single representation.

        Returns a dict with:
            status: "healthy" | "degraded" | "failed"
            zoom_levels_ok: bool
            cluster_coverage: float (0-1)
            position_coverage: float (0-1)
            issues: list of strings describing problems
        """
        issues: List[str] = []
        map_state: Optional[MapState] = map_loader.get_map(representation)

        if map_state is None:
            return {
                "status": "failed",
                "zoom_levels_ok": False,
                "cluster_coverage": 0.0,
                "position_coverage": 0.0,
                "issues": [f"Representation '{representation}' not loaded"],
            }

        zoom_levels = sorted(map_state.zoom_levels.keys())
        zoom_levels_ok = len(zoom_levels) >= self.MIN_ZOOM_LEVELS
        if not zoom_levels_ok:
            issues.append(
                f"Only {len(zoom_levels)} zoom level(s) found (need >= {self.MIN_ZOOM_LEVELS})"
            )

        total_decisions = 0
        decisions_with_clusters = 0
        decisions_with_positions = 0

        for level, zl in map_state.zoom_levels.items():
            level_count = len(zl.positions)
            total_decisions = max(total_decisions, level_count)
            decisions_with_positions += level_count

            # Count decisions that have a valid (non-negative) cluster assignment
            for did, cid in zl.cluster_assignments.items():
                if cid >= 0:
                    decisions_with_clusters += 1

        # For the base coverage metrics, use the first zoom level's counts
        if zoom_levels:
            base_zl = map_state.zoom_levels[zoom_levels[0]]
            base_n = len(base_zl.positions) if base_zl else 0
            if base_n > 0:
                clustered = sum(
                    1
                    for cid in base_zl.cluster_assignments.values()
                    if cid >= 0
                )
                cluster_coverage = clustered / base_n
                position_coverage = base_n / max(1, map_state.n_decisions)
            else:
                cluster_coverage = 0.0
                position_coverage = 0.0
        else:
            cluster_coverage = 0.0
            position_coverage = 0.0

        if cluster_coverage < self.MIN_CLUSTER_COVERAGE:
            issues.append(
                f"Cluster coverage {cluster_coverage:.1%} below threshold {self.MIN_CLUSTER_COVERAGE:.0%}"
            )
        if position_coverage < self.MIN_POSITION_COVERAGE:
            issues.append(
                f"Position coverage {position_coverage:.1%} below threshold {self.MIN_POSITION_COVERAGE:.0%}"
            )

        if not zoom_levels:
            status = "failed"
        elif issues:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "zoom_levels_ok": zoom_levels_ok,
            "cluster_coverage": round(cluster_coverage, 4),
            "position_coverage": round(position_coverage, 4),
            "issues": issues,
        }

    def check_all_representations(
        self, map_loader: MapLoader
    ) -> Dict[str, Dict[str, Any]]:
        """Check health of every loaded representation.

        Returns dict mapping representation name -> health dict.
        """
        results: Dict[str, Dict[str, Any]] = {}
        for rep in map_loader.get_available_representations():
            results[rep] = self.check_representation_health(rep, map_loader)
        return results

    def get_degraded_representations(
        self, map_loader: MapLoader
    ) -> List[str]:
        """Return list of representation names that are degraded or failed."""
        all_health = self.check_all_representations(map_loader)
        return [
            rep
            for rep, info in all_health.items()
            if info["status"] in ("degraded", "failed")
        ]

    def get_health_summary(
        self, map_loader: MapLoader
    ) -> Dict[str, Any]:
        """Return overall health summary across all representations."""
        all_health = self.check_all_representations(map_loader)
        total = len(all_health)
        healthy = sum(1 for h in all_health.values() if h["status"] == "healthy")
        degraded = sum(1 for h in all_health.values() if h["status"] == "degraded")
        failed = sum(1 for h in all_health.values() if h["status"] == "failed")

        return {
            "total": total,
            "healthy": healthy,
            "degraded": degraded,
            "failed": failed,
            "healthy_pct": round(healthy / max(1, total) * 100, 1),
            "degraded_representations": [
                rep for rep, h in all_health.items() if h["status"] == "degraded"
            ],
            "failed_representations": [
                rep for rep, h in all_health.items() if h["status"] == "failed"
            ],
            "per_representation": all_health,
        }
