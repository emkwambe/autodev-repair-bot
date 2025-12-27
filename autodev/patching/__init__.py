"""
Patch Application for AutoDev.

Handles:
- Applying unified diffs to repositories
- Rolling back failed patches
- Clean git state management
"""

from autodev.patching.apply import apply_patch, apply_patch_safe
from autodev.patching.rollback import rollback, ensure_clean_state

__all__ = [
    "apply_patch",
    "apply_patch_safe",
    "rollback",
    "ensure_clean_state",
]
