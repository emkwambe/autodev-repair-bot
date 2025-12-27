"""
GitHub Integration for AutoDev.

Handles:
- Branch creation
- Commit management
- Pull request creation with evidence
- Diagnostic comments
"""

from autodev.github.client import get_github_client, get_repo_from_remote
from autodev.github.pr import open_pull_request, create_branch_and_commit
from autodev.github.pr_body import build_pr_body, build_diagnostic_report

__all__ = [
    "get_github_client",
    "get_repo_from_remote",
    "open_pull_request",
    "create_branch_and_commit",
    "build_pr_body",
    "build_diagnostic_report",
]
