"""
AutoDev CLI Entry Point.

Usage:
    autodev --repo /path/to/repo --cmd "pytest -q"
    autodev --repo . --max-attempts 3
    autodev --help
"""

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from autodev import __version__
from autodev.state import AutoDevState
from autodev.graph import build_graph
from autodev.metrics import log_run
from autodev.sandbox.docker_runner import is_docker_available
from autodev.github.pr_body import build_diagnostic_report

# Load environment
load_dotenv()

console = Console()


def print_banner():
    """Print the AutoDev banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║     _         _        ____                           ║
    ║    / \\  _   _| |_ ___ |  _ \\  _____   __              ║
    ║   / _ \\| | | | __/ _ \\| | | |/ _ \\ \\ / /              ║
    ║  / ___ \\ |_| | || (_) | |_| |  __/\\ V /               ║
    ║ /_/   \\_\\__,_|\\__\\___/|____/ \\___| \\_/                ║
    ║                                                       ║
    ║         Agentic CI/CD Repair Bot v{version}             ║
    ╚═══════════════════════════════════════════════════════╝
    """.format(version=__version__)
    console.print(banner, style="bold blue")


def check_prerequisites() -> bool:
    """Check that all prerequisites are met."""
    issues = []
    
    # Check Docker
    if not is_docker_available():
        issues.append("Docker is not running or not installed")
    
    # Check OpenAI API key
    import os
    if not os.getenv("OPENAI_API_KEY"):
        issues.append("OPENAI_API_KEY environment variable not set")
    
    if issues:
        console.print("[red]Prerequisites not met:[/red]")
        for issue in issues:
            console.print(f"  [red]✗[/red] {issue}")
        return False
    
    console.print("[green]✓ All prerequisites met[/green]")
    return True


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AutoDev - Agentic CI/CD Repair Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  autodev --repo /path/to/project --cmd "pytest -q"
  autodev --repo . --max-attempts 3
  autodev --repo ~/myproject --cmd "python -m pytest tests/"

For more information, visit:
  https://github.com/yourusername/autodev-repair-bot
        """,
    )
    
    parser.add_argument(
        "--repo",
        required=True,
        help="Path to the repository to repair",
    )
    parser.add_argument(
        "--cmd",
        default="pytest -q",
        help="Test command to run (default: pytest -q)",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=2,
        help="Maximum repair attempts (default: 2)",
    )
    parser.add_argument(
        "--skip-flaky-check",
        action="store_true",
        help="Skip flaky test detection (not recommended)",
    )
    parser.add_argument(
        "--no-pr",
        action="store_true",
        help="Skip PR creation (just verify the fix)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"AutoDev {__version__}",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity",
    )
    
    args = parser.parse_args()
    
    # Print banner
    if not args.quiet:
        print_banner()
    
    # Validate repo path
    repo_path = Path(args.repo).resolve()
    if not repo_path.exists():
        console.print(f"[red]Error: Repository path does not exist: {repo_path}[/red]")
        sys.exit(1)
    
    if not (repo_path / ".git").exists():
        console.print(f"[red]Error: Not a git repository: {repo_path}[/red]")
        sys.exit(1)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Initialize state
    state = AutoDevState(
        repo_path=str(repo_path),
        test_command=args.cmd,
        max_attempts=args.max_attempts,
    )
    
    console.print(Panel.fit(
        f"[bold]Repository:[/bold] {repo_path}\n"
        f"[bold]Test Command:[/bold] {args.cmd}\n"
        f"[bold]Max Attempts:[/bold] {args.max_attempts}",
        title="Configuration",
    ))
    
    # Build and run the graph
    graph = build_graph()
    
    start_time = time.time()
    
    try:
        console.print("\n[bold]Starting repair loop...[/bold]\n")
        result = graph.invoke(state)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
        
    except Exception as e:
        console.print(f"\n[red]Error during execution: {e}[/red]")
        sys.exit(1)
    
    duration = time.time() - start_time
    
    # Log metrics
    log_run(result, duration_seconds=duration)
    
    # Print results
    console.print("\n" + "=" * 60)
    
    if result.pr_url:
        console.print(Panel.fit(
            f"[bold green]✅ Fix verified and PR created![/bold green]\n\n"
            f"[bold]PR URL:[/bold] {result.pr_url}\n"
            f"[bold]Attempts:[/bold] {result.attempt + 1}/{result.max_attempts}\n"
            f"[bold]Duration:[/bold] {duration:.1f}s",
            title="Success",
            border_style="green",
        ))
        sys.exit(0)
        
    elif result.sandbox_passed and args.no_pr:
        console.print(Panel.fit(
            f"[bold green]✅ Fix verified![/bold green]\n\n"
            f"PR creation skipped (--no-pr flag)\n"
            f"[bold]Attempts:[/bold] {result.attempt + 1}/{result.max_attempts}\n"
            f"[bold]Duration:[/bold] {duration:.1f}s",
            title="Success",
            border_style="green",
        ))
        sys.exit(0)
        
    else:
        # Generate diagnostic report
        diagnostic = build_diagnostic_report(result)
        
        console.print(Panel.fit(
            f"[bold red]❌ Repair unsuccessful[/bold red]\n\n"
            f"[bold]Reason:[/bold] {result.stop_reason or 'Unknown'}\n"
            f"[bold]Attempts:[/bold] {result.attempt + 1}/{result.max_attempts}\n"
            f"[bold]Flaky:[/bold] {'Yes' if result.flaky_detected else 'No'}\n"
            f"[bold]Policy Violations:[/bold] {len(result.policy_violations)}\n"
            f"[bold]Duration:[/bold] {duration:.1f}s",
            title="Stopped",
            border_style="red",
        ))
        
        if not args.quiet:
            console.print("\n[bold]Diagnostic Report:[/bold]")
            console.print(diagnostic)
        
        sys.exit(1)


if __name__ == "__main__":
    main()
