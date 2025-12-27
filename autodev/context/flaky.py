"""
Flaky Test Detection for AutoDev.

Before attempting any code repair, we verify the failure is deterministic.
Flaky tests are the #1 reason AI repair bots lose credibility.

Strategy:
1. Re-run the failing test N times
2. If results are inconsistent → classify as flaky
3. Do NOT attempt code repair for flaky tests
4. Produce a diagnostic report instead
"""

from rich.console import Console

console = Console()


def detect_flakiness(
    run_func,
    repo_path: str, 
    test_command: str, 
    runs: int = 3,
    verbose: bool = True,
) -> tuple[bool, list[bool]]:
    """
    Detect if a test failure is flaky by running multiple times.
    
    Args:
        run_func: Function that runs tests and returns logs
        repo_path: Path to repository
        test_command: Test command to execute
        runs: Number of times to run the test
        verbose: Whether to print progress
        
    Returns:
        Tuple of (is_flaky, list of pass/fail results)
    """
    results = []
    
    if verbose:
        console.print(f"[yellow]Checking for flakiness ({runs} runs)...[/yellow]")
    
    for i in range(runs):
        if verbose:
            console.print(f"  Run {i + 1}/{runs}...", end=" ")
        
        try:
            logs = run_func(repo_path, test_command)
            passed = not is_failure(logs)
            results.append(passed)
            
            if verbose:
                status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
                console.print(status)
                
        except Exception as e:
            results.append(False)
            if verbose:
                console.print(f"[red]ERROR: {e}[/red]")
    
    # Flaky if results are inconsistent
    is_flaky = len(set(results)) > 1
    
    if verbose:
        if is_flaky:
            console.print("[yellow]⚠ Flaky test detected - results inconsistent[/yellow]")
        else:
            console.print("[blue]✓ Test failure is deterministic[/blue]")
    
    return is_flaky, results


def is_failure(logs: str) -> bool:
    """
    Determine if test output indicates failure.
    
    Args:
        logs: Test execution output
        
    Returns:
        True if tests failed
    """
    failure_indicators = [
        "FAILED",
        "FAIL",
        "ERROR",
        "error:",
        "Error:",
        "AssertionError",
        "Exception",
        "Traceback",
    ]
    
    # Also check pytest-specific patterns
    pytest_fail_patterns = [
        "failed",
        "error",
        "= FAILURES =",
        "= ERRORS =",
    ]
    
    logs_lower = logs.lower()
    
    for indicator in failure_indicators:
        if indicator in logs:
            return True
    
    for pattern in pytest_fail_patterns:
        if pattern in logs_lower:
            return True
    
    return False


def looks_like_dependency_issue(logs: str) -> bool:
    """
    Check if failure appears to be a dependency/import issue.
    
    These require special handling (lockfile updates, etc.)
    
    Args:
        logs: Test execution output
        
    Returns:
        True if this looks like a dependency problem
    """
    dependency_keywords = [
        "ModuleNotFoundError",
        "ImportError",
        "No module named",
        "VersionConflict",
        "PackageNotFoundError",
        "Could not find a version",
        "pip install",
        "requirements",
    ]
    
    return any(keyword in logs for keyword in dependency_keywords)
