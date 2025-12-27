"""
Diff Guard for AutoDev.

Validates proposed patches against policy rules before application.
This is the core trust mechanism - no patch bypasses this check.
"""

from typing import Optional
from unidiff import PatchSet, UnidiffParseError

from autodev.policy.rules import (
    PolicyConfig, 
    DEFAULT_POLICY,
    DANGEROUS_PATTERNS,
)


def validate_patch(
    diff_text: str,
    policy: Optional[PolicyConfig] = None,
) -> list[str]:
    """
    Validate a unified diff against policy rules.
    
    Args:
        diff_text: Unified diff string
        policy: Policy configuration (uses default if not provided)
        
    Returns:
        List of policy violations (empty if valid)
    """
    if policy is None:
        policy = DEFAULT_POLICY
    
    violations = []
    
    # Handle empty or invalid diff
    if not diff_text or not diff_text.strip():
        violations.append("Empty or invalid patch")
        return violations
    
    # Parse the diff
    try:
        patch = PatchSet(diff_text)
    except UnidiffParseError as e:
        violations.append(f"Invalid diff format: {e}")
        return violations
    
    if len(patch) == 0:
        violations.append("Patch contains no file changes")
        return violations
    
    # Track totals for size limits
    total_lines_changed = 0
    files_changed = len(patch)
    
    # Check file count limit
    if files_changed > policy.max_files_changed:
        violations.append(
            f"Too many files changed: {files_changed} > {policy.max_files_changed}"
        )
    
    for patched_file in patch:
        file_path = patched_file.path
        
        # Normalize path separators
        normalized_path = file_path.replace("\\", "/").lstrip("/")
        
        # Check forbidden paths
        for forbidden in policy.forbidden_paths:
            if normalized_path.startswith(forbidden) or f"/{forbidden}" in normalized_path:
                if not policy.allow_test_modifications:
                    violations.append(f"Forbidden path modified: {file_path}")
                    break
        
        # Check for file deletion
        if patched_file.is_removed_file:
            if not policy.allow_file_deletion:
                violations.append(f"File deletion not allowed: {file_path}")
        
        # Check dependency files
        for dep_file in policy.dependency_files:
            if normalized_path.endswith(dep_file):
                if not policy.allow_dependency_changes:
                    violations.append(
                        f"Dependency file modification not allowed: {file_path}"
                    )
                break
        
        # Analyze hunks
        file_lines_changed = 0
        
        for hunk in patched_file:
            hunk_lines = len(list(hunk))
            file_lines_changed += hunk_lines
            
            for line in hunk:
                line_content = line.value
                
                # Check forbidden patterns (in added or modified lines)
                if line.is_added:
                    for pattern in policy.forbidden_patterns:
                        if pattern in line_content:
                            violations.append(
                                f"Forbidden pattern added: '{pattern}' in {file_path}"
                            )
                
                # Check dangerous patterns
                if policy.check_dangerous_patterns and line.is_added:
                    for pattern in DANGEROUS_PATTERNS:
                        if pattern in line_content:
                            violations.append(
                                f"Dangerous pattern detected: '{pattern}' in {file_path}"
                            )
                
                # Check for assertion removal (in test files if allowed)
                if line.is_removed and "assert" in line_content.lower():
                    violations.append(
                        f"Assertion removal detected in {file_path}"
                    )
        
        total_lines_changed += file_lines_changed
        
        # Check hunk count per file
        if len(patched_file) > policy.max_hunks_per_file:
            violations.append(
                f"Too many changes in {file_path}: {len(patched_file)} hunks"
            )
    
    # Check total lines changed
    if total_lines_changed > policy.max_lines_changed:
        violations.append(
            f"Patch too large: {total_lines_changed} lines > {policy.max_lines_changed}"
        )
    
    return violations


def is_patch_safe(
    diff_text: str,
    policy: Optional[PolicyConfig] = None,
) -> bool:
    """
    Quick check if a patch passes all policy rules.
    
    Args:
        diff_text: Unified diff string
        policy: Policy configuration
        
    Returns:
        True if patch is safe to apply
    """
    violations = validate_patch(diff_text, policy)
    return len(violations) == 0


def extract_patch_stats(diff_text: str) -> dict:
    """
    Extract statistics from a patch for reporting.
    
    Args:
        diff_text: Unified diff string
        
    Returns:
        Dictionary with patch statistics
    """
    try:
        patch = PatchSet(diff_text)
    except UnidiffParseError:
        return {"error": "Invalid diff format"}
    
    stats = {
        "files_changed": len(patch),
        "additions": 0,
        "deletions": 0,
        "files": [],
    }
    
    for patched_file in patch:
        file_stats = {
            "path": patched_file.path,
            "additions": patched_file.added,
            "deletions": patched_file.removed,
        }
        stats["files"].append(file_stats)
        stats["additions"] += patched_file.added
        stats["deletions"] += patched_file.removed
    
    return stats
