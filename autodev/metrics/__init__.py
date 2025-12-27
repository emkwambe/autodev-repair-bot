"""
Metrics and Observability for AutoDev.

Tracks measurable outcomes for ROI analysis:
- Pass rate
- Attempt distribution
- MTTR reduction
- Failure categories
"""

from autodev.metrics.logger import log_run, MetricsLogger

__all__ = ["log_run", "MetricsLogger"]
