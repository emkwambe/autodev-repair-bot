"""
Policy Engine for AutoDev.

Enforces hard constraints that make the agent trustworthy:
- Forbidden path modifications
- Forbidden patterns (test bypasses)
- Diff size limits
- Destructive edit prevention

The policy engine is deterministic and non-AI.
"""

from autodev.policy.diff_guard import validate_patch
from autodev.policy.rules import FORBIDDEN_PATHS, FORBIDDEN_PATTERNS, PolicyConfig

__all__ = [
    "validate_patch",
    "FORBIDDEN_PATHS",
    "FORBIDDEN_PATTERNS", 
    "PolicyConfig",
]
