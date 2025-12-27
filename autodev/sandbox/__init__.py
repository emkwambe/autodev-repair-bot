"""
Sandbox execution for AutoDev.

All AI-generated code runs inside Docker containers:
- Non-root user
- No network access
- Clean environment per attempt
- Isolated from host
"""

from autodev.sandbox.docker_runner import run_in_sandbox, is_docker_available

__all__ = ["run_in_sandbox", "is_docker_available"]
