"""
Pull Request Creation for AutoDev.

Creates verified PRs only when all gates pass.
"""

import subprocess
from datetime import datetime
from typing import Optional

from git import Repo
from github import GithubException
from rich.console import Console

from autodev.github.client import get_github_client, get_repo_from_remote

console = Console()


def create_branch_and_commit(
    repo_path: str,
    branch_name: str,
    commit_message: str,
    verbose: bool = False,
) -> bool:
    """
    Create a new branch and commit all changes.
    
    Args:
        repo_path: Path to the repository
        branch_name: Name for the new branch
        commit_message: Commit message
        verbose: Whether to print progress
        
    Returns:
        True if successful
    """
    try:
        repo = Repo(repo_path)
        
        # Create and checkout new branch
        if branch_name in repo.heads:
            # Branch exists, use a unique suffix
            branch_name = f"{branch_name}-{datetime.now().strftime('%H%M%S')}"
        
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        
        if verbose:
            console.print(f"[blue]Created branch: {branch_name}[/blue]")
        
        # Stage all changes
        repo.git.add(all=True)
        
        # Commit
        repo.index.commit(commit_message)
        
        if verbose:
            console.print(f"[blue]Committed: {commit_message}[/blue]")
        
        return True
        
    except Exception as e:
        if verbose:
            console.print(f"[red]Failed to create branch/commit: {e}[/red]")
        return False


def push_branch(
    repo_path: str,
    branch_name: str,
    verbose: bool = False,
) -> bool:
    """
    Push branch to origin.
    
    Args:
        repo_path: Path to the repository
        branch_name: Branch to push
        verbose: Whether to print progress
        
    Returns:
        True if successful
    """
    try:
        result = subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        
        if verbose:
            console.print(f"[blue]Pushed branch: {branch_name}[/blue]")
        
        return True
        
    except subprocess.CalledProcessError as e:
        if verbose:
            console.print(f"[red]Failed to push: {e.stderr}[/red]")
        return False


def open_pull_request(
    repo_path: str,
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "main",
    verbose: bool = False,
) -> Optional[str]:
    """
    Create a pull request on GitHub.
    
    Args:
        repo_path: Path to the repository
        branch_name: Source branch for the PR
        title: PR title
        body: PR description body
        base_branch: Target branch (default: main)
        verbose: Whether to print progress
        
    Returns:
        PR URL if successful, None otherwise
    """
    # Get repository identifier
    repo_id = get_repo_from_remote(repo_path)
    if not repo_id:
        if verbose:
            console.print("[red]Could not determine GitHub repository from remote[/red]")
        return None
    
    # Create branch and commit
    commit_message = f"AutoDev: {title}"
    if not create_branch_and_commit(repo_path, branch_name, commit_message, verbose):
        return None
    
    # Push branch
    if not push_branch(repo_path, branch_name, verbose):
        return None
    
    # Create PR
    try:
        gh = get_github_client()
        gh_repo = gh.get_repo(repo_id)
        
        # Check if base branch exists
        try:
            gh_repo.get_branch(base_branch)
        except GithubException:
            # Try "master" as fallback
            base_branch = "master"
        
        pr = gh_repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base_branch,
        )
        
        if verbose:
            console.print(f"[green]Created PR: {pr.html_url}[/green]")
        
        return pr.html_url
        
    except GithubException as e:
        if verbose:
            console.print(f"[red]Failed to create PR: {e}[/red]")
        return None
