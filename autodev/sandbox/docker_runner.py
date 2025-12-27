"""
Docker Sandbox Runner for AutoDev.

Executes commands in isolated Docker containers to:
- Prevent host damage
- Ensure reproducibility
- Isolate potentially harmful AI-generated code
"""

import os
from pathlib import Path
from typing import Optional

import docker
from docker.errors import DockerException, ImageNotFound
from rich.console import Console

console = Console()

# Default Docker image for Python projects
DEFAULT_IMAGE = "python:3.11-slim"

# Maximum execution time (seconds)
MAX_TIMEOUT = 300


def is_docker_available() -> bool:
    """Check if Docker daemon is accessible."""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except DockerException:
        return False


def run_in_sandbox(
    repo_path: str,
    command: str,
    image: str = DEFAULT_IMAGE,
    timeout: int = MAX_TIMEOUT,
    network_disabled: bool = True,
    install_deps: bool = True,
    verbose: bool = False,
) -> str:
    """
    Execute a command in a Docker sandbox.
    
    Args:
        repo_path: Path to repository to mount
        command: Command to execute (e.g., "pytest -q")
        image: Docker image to use
        timeout: Maximum execution time in seconds
        network_disabled: Whether to disable network access
        install_deps: Whether to install dependencies first
        verbose: Whether to print progress
        
    Returns:
        Command output (stdout + stderr combined)
        
    Raises:
        RuntimeError: If Docker is unavailable or execution fails
    """
    if not is_docker_available():
        raise RuntimeError(
            "Docker is not available. Please ensure Docker is running."
        )
    
    abs_repo = os.path.abspath(repo_path)
    
    if not Path(abs_repo).exists():
        raise RuntimeError(f"Repository path does not exist: {abs_repo}")
    
    client = docker.from_env()
    
    # Build the full command
    if install_deps:
        # Check for common dependency files and install
        full_command = """
            cd /workspace && \
            if [ -f requirements.txt ]; then pip install -q -r requirements.txt 2>/dev/null; fi && \
            if [ -f pyproject.toml ]; then pip install -q -e . 2>/dev/null; fi && \
            """ + command
    else:
        full_command = f"cd /workspace && {command}"
    
    try:
        if verbose:
            console.print(f"[dim]Running in sandbox: {command}[/dim]")
        
        # Ensure image exists
        try:
            client.images.get(image)
        except ImageNotFound:
            if verbose:
                console.print(f"[yellow]Pulling image: {image}[/yellow]")
            client.images.pull(image)
        
        # Run container
        output = client.containers.run(
            image=image,
            command=["bash", "-c", full_command],
            volumes={abs_repo: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            network_disabled=network_disabled,
            remove=True,
            stderr=True,
            stdout=True,
            user="root",  # Need root for pip install; code is still isolated
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000,  # 50% CPU limit
        )
        
        return output.decode("utf-8")
        
    except docker.errors.ContainerError as e:
        # Container exited with non-zero code (expected for test failures)
        if e.stderr:
            return e.stderr.decode("utf-8")
        return str(e)
        
    except docker.errors.APIError as e:
        raise RuntimeError(f"Docker API error: {e}")


def run_in_sandbox_safe(
    repo_path: str,
    command: str,
    **kwargs
) -> tuple[str, bool]:
    """
    Safe wrapper that catches all exceptions.
    
    Returns:
        Tuple of (output, success)
    """
    try:
        output = run_in_sandbox(repo_path, command, **kwargs)
        return output, True
    except Exception as e:
        return str(e), False
