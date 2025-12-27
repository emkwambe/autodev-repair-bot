"""
Smart Context Retrieval for AutoDev.

Instead of sending entire repositories to the LLM, we:
1. Parse stack traces to find relevant files
2. Load only those files (truncated)
3. Provide focused context for better reasoning
"""

import re
from pathlib import Path
from typing import Optional


def extract_files_from_trace(logs: str) -> list[str]:
    """
    Extract Python file paths from stack trace logs.
    
    Args:
        logs: Raw pytest failure output
        
    Returns:
        List of unique file paths mentioned in traces
    """
    # Match patterns like: File "/path/to/file.py", line 42
    pattern = r'File ["\'](.+?\.py)["\']'
    matches = re.findall(pattern, logs)
    
    # Deduplicate while preserving order
    seen = set()
    unique_files = []
    for f in matches:
        # Normalize path
        normalized = f.replace("\\", "/")
        if normalized not in seen:
            seen.add(normalized)
            unique_files.append(normalized)
    
    return unique_files


def extract_failing_test_info(logs: str) -> dict:
    """
    Extract structured information about failing tests.
    
    Args:
        logs: Raw pytest failure output
        
    Returns:
        Dictionary with test names, assertions, and locations
    """
    info = {
        "test_names": [],
        "assertions": [],
        "error_types": [],
    }
    
    # Find test function names
    test_pattern = r"(test_\w+)"
    info["test_names"] = list(set(re.findall(test_pattern, logs)))
    
    # Find assertion errors
    assert_pattern = r"(AssertionError|assert .+)"
    info["assertions"] = re.findall(assert_pattern, logs)[:5]  # Limit
    
    # Find exception types
    error_pattern = r"(\w+Error|\w+Exception):"
    info["error_types"] = list(set(re.findall(error_pattern, logs)))
    
    return info


def load_snippets(
    repo_path: str, 
    files: list[str], 
    max_lines: int = 200
) -> dict[str, str]:
    """
    Load relevant file contents with truncation.
    
    Args:
        repo_path: Base repository path
        files: List of file paths to load
        max_lines: Maximum lines per file
        
    Returns:
        Dictionary mapping file paths to their contents
    """
    snippets = {}
    repo = Path(repo_path)
    
    for file_path in files:
        # Handle both absolute and relative paths
        if Path(file_path).is_absolute():
            full_path = Path(file_path)
        else:
            full_path = repo / file_path
        
        # Also try stripping repo path prefix
        if not full_path.exists():
            # Extract just the relative portion
            parts = file_path.split("/")
            for i in range(len(parts)):
                candidate = repo / "/".join(parts[i:])
                if candidate.exists():
                    full_path = candidate
                    break
        
        if full_path.exists() and full_path.is_file():
            try:
                content = full_path.read_text(encoding="utf-8")
                lines = content.splitlines()
                
                if len(lines) > max_lines:
                    # Keep first and last portions
                    half = max_lines // 2
                    truncated = (
                        lines[:half] + 
                        [f"\n... [{len(lines) - max_lines} lines truncated] ...\n"] + 
                        lines[-half:]
                    )
                    content = "\n".join(truncated)
                
                # Use relative path as key
                rel_path = str(full_path.relative_to(repo)) if repo in full_path.parents else str(full_path)
                snippets[rel_path] = content
                
            except (UnicodeDecodeError, PermissionError):
                continue
    
    return snippets


def format_context_for_prompt(snippets: dict[str, str]) -> str:
    """
    Format file snippets for inclusion in LLM prompts.
    
    Args:
        snippets: Dictionary of file paths to contents
        
    Returns:
        Formatted string for prompt inclusion
    """
    if not snippets:
        return "(No relevant source files found)"
    
    parts = []
    for path, content in snippets.items():
        parts.append(f"### {path}\n```python\n{content}\n```")
    
    return "\n\n".join(parts)
