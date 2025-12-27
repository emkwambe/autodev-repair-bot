"""
Metrics Logger for AutoDev.

Stores structured metrics for analysis and ROI demonstration.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

from autodev.state import AutoDevState


@dataclass
class RunMetrics:
    """Metrics for a single AutoDev run."""
    
    timestamp: str
    repo_path: str
    test_command: str
    
    # Outcome
    success: bool
    pr_created: bool
    pr_url: Optional[str]
    
    # Attempts
    attempts_used: int
    max_attempts: int
    
    # Detection
    flaky_detected: bool
    is_dependency_issue: bool
    
    # Policy
    policy_violations: list[str]
    
    # Reason
    stop_reason: Optional[str]
    
    # Timing (can be added later)
    duration_seconds: Optional[float] = None


class MetricsLogger:
    """
    Persistent metrics logger.
    
    Writes JSON lines to a file for later analysis.
    """
    
    def __init__(self, path: str = "autodev_metrics.jsonl"):
        self.path = Path(path)
    
    def log(self, metrics: RunMetrics) -> None:
        """
        Append metrics to the log file.
        
        Args:
            metrics: Run metrics to log
        """
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(metrics)) + "\n")
    
    def read_all(self) -> list[RunMetrics]:
        """
        Read all logged metrics.
        
        Returns:
            List of RunMetrics objects
        """
        if not self.path.exists():
            return []
        
        metrics = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                metrics.append(RunMetrics(**data))
        
        return metrics
    
    def summary(self) -> dict:
        """
        Generate summary statistics.
        
        Returns:
            Dictionary of summary stats
        """
        all_metrics = self.read_all()
        
        if not all_metrics:
            return {"total_runs": 0}
        
        total = len(all_metrics)
        successful = sum(1 for m in all_metrics if m.success)
        prs_created = sum(1 for m in all_metrics if m.pr_created)
        flaky_count = sum(1 for m in all_metrics if m.flaky_detected)
        
        return {
            "total_runs": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0,
            "prs_created": prs_created,
            "flaky_detected": flaky_count,
            "avg_attempts": sum(m.attempts_used for m in all_metrics) / total,
        }


# Default logger instance
_default_logger = MetricsLogger()


def log_run(state: AutoDevState, duration_seconds: Optional[float] = None) -> None:
    """
    Log metrics from a completed run.
    
    Args:
        state: Final agent state
        duration_seconds: Optional run duration
    """
    metrics = RunMetrics(
        timestamp=datetime.utcnow().isoformat(),
        repo_path=state.repo_path,
        test_command=state.test_command,
        success=state.sandbox_passed,
        pr_created=state.pr_url is not None,
        pr_url=state.pr_url,
        attempts_used=state.attempt + 1,
        max_attempts=state.max_attempts,
        flaky_detected=state.flaky_detected,
        is_dependency_issue=state.is_dependency_issue,
        policy_violations=state.policy_violations,
        stop_reason=state.stop_reason,
        duration_seconds=duration_seconds,
    )
    
    _default_logger.log(metrics)
