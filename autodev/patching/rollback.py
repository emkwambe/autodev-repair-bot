"""
Git Rollback Utilities for AutoDev.

Ensures clean state between repair attempts:
- No dirty files
- No compounding hallucinations
- Each attempt starts fresh
"""

import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def rollback(
    repo_path: str,
    verbose: bool = False,
) -> bool:
    """
    Reset repository to clean state (discard all uncommitted changes).
    
    Args:
        repo_path: Path to the repository
        verbose: Whether to print progress
        
    Returns:
        True if rollback succeeded
    """
    try:
        # Hard reset to discard changes
        subprocess.run(
            ["git", "reset", "--hard"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        
        # Clean untracked files
        subprocess.run(
            ["git", "clean", "-fd"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        
        if verbose:
            console.print("[blue]Repository reset to clean state[/blue]")
        
        return True
        
    except subprocess.CalledProcessError as e:
        if verbose:
            console.print(f"[red]Rollback failed: {e.stderr}[/red]")
        return False


def ensure_clean_state(
    repo_path: str,
    verbose: bool = False,
) -> tuple[bool, Optional[str]]:
    """
    Ensure repository is in a clean state before starting.
    
    If dirty, offers to stash or abort.
    
    Args:
        repo_path: Path to the repository
        verbose: Whether to print progress
        
    Returns:
        Tuple of (is_clean, stash_ref if stashed)
    """
    try:
        # Check for uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        
        if result.stdout.strip():
            # Repository is dirty - stash changes
            if verbose:
                console.print("[yellow]Stashing uncommitted changes...[/yellow]")
            
            stash_result = subprocess.run(
                ["git", "stash", "push", "-m", "autodev-pre-repair"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            
            # Get stash reference
            stash_ref = "stash@{0}"
            return True, stash_ref
        
        return True, None
        
    except subprocess.CalledProcessError as e:
        if verbose:
            console.print(f"[red]Failed to check/clean state: {e}[/red]")
        return False, None


def restore_stash(
    repo_path: str,
    stash_ref: str = "stash@{0}",
    verbose: bool = False,
) -> bool:
    """
    Restore previously stashed changes.
    
    Args:
        repo_path: Path to the repository
        stash_ref: Stash reference to restore
        verbose: Whether to print progress
        
    Returns:
        True if restore succeeded
    """
    try:
        subprocess.run(
            ["git", "stash", "pop", stash_ref],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        
        if verbose:
            console.print("[blue]Restored stashed changes[/blue]")
        
        return True
        
    except subprocess.CalledProcessError:
        return False


def get_current_branch(repo_path: str) -> Optional[str]:
    """
    Get the current git branch name.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Branch name or None if not on a branch
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except subprocess.CalledProcessError:
        return None
