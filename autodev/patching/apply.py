"""
Patch Application for AutoDev.

Applies unified diffs to repositories safely and reversibly.
"""

import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

# Patch file name (gitignored)
PATCH_FILENAME = ".autodev.patch"


def apply_patch(
    repo_path: str,
    diff: str,
    verbose: bool = False,
) -> bool:
    """
    Apply a unified diff to a repository.
    
    Args:
        repo_path: Path to the repository
        diff: Unified diff content
        verbose: Whether to print progress
        
    Returns:
        True if patch applied successfully
    """
    repo = Path(repo_path)
    patch_file = repo / PATCH_FILENAME
    
    # Write patch to file
    try:
        patch_file.write_text(diff, encoding="utf-8")
    except IOError as e:
        if verbose:
            console.print(f"[red]Failed to write patch file: {e}[/red]")
        return False
    
    try:
        # Try to apply with git apply
        result = subprocess.run(
            [
                "git", "apply",
                "--whitespace=fix",
                "--verbose" if verbose else "--quiet",
                str(patch_file)
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        
        if verbose:
            console.print("[green]Patch applied successfully[/green]")
            if result.stdout:
                console.print(f"[dim]{result.stdout}[/dim]")
        
        return True
        
    except subprocess.CalledProcessError as e:
        if verbose:
            console.print(f"[red]Failed to apply patch:[/red]")
            console.print(f"[dim]{e.stderr}[/dim]")
        
        # Try with more lenient options
        try:
            result = subprocess.run(
                [
                    "git", "apply",
                    "--whitespace=fix",
                    "--reject",  # Create .rej files for conflicts
                    str(patch_file)
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            
            # Check if we have reject files
            reject_files = list(repo.glob("**/*.rej"))
            if reject_files:
                if verbose:
                    console.print(f"[yellow]Partial apply with {len(reject_files)} conflicts[/yellow]")
                # Clean up reject files
                for rej in reject_files:
                    rej.unlink()
                return False
            
            return result.returncode == 0
            
        except subprocess.CalledProcessError:
            return False
    
    finally:
        # Clean up patch file
        if patch_file.exists():
            patch_file.unlink()


def apply_patch_safe(
    repo_path: str,
    diff: str,
    verbose: bool = False,
) -> tuple[bool, Optional[str]]:
    """
    Safe wrapper that returns error message on failure.
    
    Args:
        repo_path: Path to the repository
        diff: Unified diff content
        verbose: Whether to print progress
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        success = apply_patch(repo_path, diff, verbose)
        if success:
            return True, None
        else:
            return False, "Patch failed to apply cleanly"
    except Exception as e:
        return False, str(e)


def check_git_available(repo_path: str) -> bool:
    """
    Check if git is available and the path is a git repository.
    
    Args:
        repo_path: Path to check
        
    Returns:
        True if git is available and path is a repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
