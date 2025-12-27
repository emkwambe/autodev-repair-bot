"""
GitHub API Client for AutoDev.

Provides authenticated access to GitHub for PR operations.
"""

import os
import re
from typing import Optional

from github import Github, GithubException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_github_client() -> Github:
    """
    Get authenticated GitHub client.
    
    Returns:
        Authenticated Github instance
        
    Raises:
        RuntimeError: If GITHUB_TOKEN is not set
    """
    token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable is not set. "
            "Please set it to a GitHub Personal Access Token with 'repo' permissions."
        )
    
    return Github(token)


def get_repo_from_remote(repo_path: str) -> Optional[str]:
    """
    Extract GitHub repository identifier from git remote.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Repository identifier (e.g., "owner/repo") or None
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        
        remote_url = result.stdout.strip()
        
        # Handle different URL formats
        # SSH: git@github.com:owner/repo.git
        # HTTPS: https://github.com/owner/repo.git
        
        ssh_match = re.match(r"git@github\.com:(.+?)(?:\.git)?$", remote_url)
        if ssh_match:
            return ssh_match.group(1)
        
        https_match = re.match(r"https://github\.com/(.+?)(?:\.git)?$", remote_url)
        if https_match:
            return https_match.group(1)
        
        return None
        
    except subprocess.CalledProcessError:
        return None


def validate_github_access(repo_identifier: str) -> bool:
    """
    Validate that we have access to the specified repository.
    
    Args:
        repo_identifier: Repository in "owner/repo" format
        
    Returns:
        True if we have push access
    """
    try:
        client = get_github_client()
        repo = client.get_repo(repo_identifier)
        
        # Check if we have push permissions
        return repo.permissions.push
        
    except GithubException:
        return False
