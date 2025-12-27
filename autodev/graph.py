"""
LangGraph Orchestration for AutoDev.

Implements the repair loop as a finite state machine with:
- Bounded retries
- Deterministic exit paths
- Safe feedback loops
"""

from typing import Literal

from langgraph.graph import StateGraph, END
from rich.console import Console

from autodev.state import AutoDevState
from autodev.context.llm import llm
from autodev.context.prompts import PLAN_PROMPT, PATCH_PROMPT
from autodev.context.retriever import (
    extract_files_from_trace,
    load_snippets,
    format_context_for_prompt,
)
from autodev.context.flaky import detect_flakiness, is_failure, looks_like_dependency_issue
from autodev.sandbox.docker_runner import run_in_sandbox
from autodev.policy.diff_guard import validate_patch
from autodev.patching.apply import apply_patch
from autodev.patching.rollback import rollback
from autodev.github.pr import open_pull_request
from autodev.github.pr_body import build_pr_body

console = Console()


# ============================================================================
# Node Functions
# ============================================================================

def collect_failure(state: AutoDevState) -> AutoDevState:
    """
    Initial failure collection node.
    
    Runs tests to capture failure output.
    """
    console.print("[bold blue]📥 Collecting failure information...[/bold blue]")
    
    try:
        logs = run_in_sandbox(state.repo_path, state.test_command, verbose=True)
        state.failure_logs = logs
        
        # Check for dependency issues
        if looks_like_dependency_issue(logs):
            state.is_dependency_issue = True
            console.print("[yellow]⚠ Detected potential dependency issue[/yellow]")
        
    except Exception as e:
        state.failure_logs = f"Error running tests: {e}"
        console.print(f"[red]Error: {e}[/red]")
    
    return state


def check_flaky(state: AutoDevState) -> AutoDevState:
    """
    Flakiness detection node.
    
    Runs tests multiple times to verify failure is deterministic.
    """
    console.print("[bold blue]🔄 Checking for flaky tests...[/bold blue]")
    
    def run_func(repo_path, cmd):
        return run_in_sandbox(repo_path, cmd)
    
    is_flaky, results = detect_flakiness(
        run_func,
        state.repo_path,
        state.test_command,
        runs=3,
    )
    
    state.flaky_detected = is_flaky
    state.flaky_runs = results
    
    if is_flaky:
        state.stop_reason = "Flaky test detected - deterministic fix not possible"
    
    return state


def collect_context(state: AutoDevState) -> AutoDevState:
    """
    Smart context retrieval node.
    
    Extracts relevant files from stack traces.
    """
    console.print("[bold blue]📂 Collecting relevant context...[/bold blue]")
    
    if state.failure_logs:
        files = extract_files_from_trace(state.failure_logs)
        snippets = load_snippets(state.repo_path, files)
        state.context_files = snippets
        
        console.print(f"[dim]Found {len(snippets)} relevant files[/dim]")
    
    return state


def plan_fix(state: AutoDevState) -> AutoDevState:
    """
    LLM reasoning node - root cause analysis.
    
    Produces explanation of the failure and fix strategy.
    """
    console.print("[bold blue]🧠 Analyzing failure and planning fix...[/bold blue]")
    
    context_text = format_context_for_prompt(state.context_files)
    
    prompt = PLAN_PROMPT.format(
        logs=state.failure_logs or "No logs available",
        context=context_text,
    )
    
    response = llm.invoke(prompt)
    state.root_cause_analysis = response.content
    state.fix_strategy = response.content
    
    console.print("[dim]Analysis complete[/dim]")
    
    return state


def generate_patch(state: AutoDevState) -> AutoDevState:
    """
    LLM patch generation node.
    
    Produces a unified diff based on the analysis.
    """
    console.print("[bold blue]🔧 Generating patch...[/bold blue]")
    
    prompt = PATCH_PROMPT.format(
        plan=state.fix_strategy or "",
        logs=state.failure_logs or "",
    )
    
    response = llm.invoke(prompt)
    
    # Extract diff from response (handle markdown code blocks)
    patch_content = response.content
    if "```diff" in patch_content:
        # Extract content between ```diff and ```
        start = patch_content.find("```diff") + 7
        end = patch_content.find("```", start)
        patch_content = patch_content[start:end].strip()
    elif "```" in patch_content:
        # Generic code block
        start = patch_content.find("```") + 3
        end = patch_content.find("```", start)
        patch_content = patch_content[start:end].strip()
    
    state.proposed_patch = patch_content
    
    console.print("[dim]Patch generated[/dim]")
    
    return state


def policy_check(state: AutoDevState) -> AutoDevState:
    """
    Policy enforcement node.
    
    Validates patch against safety rules.
    """
    console.print("[bold blue]🛡️ Checking policy compliance...[/bold blue]")
    
    if not state.proposed_patch:
        state.policy_violations = ["No patch was generated"]
        return state
    
    violations = validate_patch(state.proposed_patch)
    state.policy_violations = violations
    
    if violations:
        console.print(f"[yellow]Policy violations: {len(violations)}[/yellow]")
        for v in violations:
            console.print(f"  [dim]- {v}[/dim]")
    else:
        console.print("[green]✓ Policy check passed[/green]")
    
    return state


def apply_and_test(state: AutoDevState) -> AutoDevState:
    """
    Sandbox validation node.
    
    Applies patch and re-runs tests in Docker.
    """
    console.print("[bold blue]🧪 Applying patch and testing...[/bold blue]")
    
    # Skip if policy violations
    if state.policy_violations:
        state.stop_reason = "Policy violations prevented patch application"
        return state
    
    # Rollback to clean state
    rollback(state.repo_path, verbose=True)
    
    # Apply patch
    applied = apply_patch(state.repo_path, state.proposed_patch, verbose=True)
    state.patch_applied = applied
    
    if not applied:
        state.stop_reason = "Patch failed to apply cleanly"
        return state
    
    # Run tests in sandbox
    try:
        logs = run_in_sandbox(state.repo_path, state.test_command, verbose=True)
        state.failure_logs = logs
        state.sandbox_passed = not is_failure(logs)
        
        if state.sandbox_passed:
            console.print("[green]✅ Tests passed![/green]")
        else:
            console.print("[red]❌ Tests still failing[/red]")
            
    except Exception as e:
        console.print(f"[red]Error during sandbox execution: {e}[/red]")
        state.sandbox_passed = False
        state.stop_reason = f"Sandbox execution error: {e}"
    
    return state


def create_pr(state: AutoDevState) -> AutoDevState:
    """
    PR creation node.
    
    Only reached when verification passes.
    """
    console.print("[bold blue]🚀 Creating pull request...[/bold blue]")
    
    branch_name = f"autodev/fix-{state.attempt + 1}"
    title = "AutoDev: Fix failing tests"
    body = build_pr_body(state)
    
    pr_url = open_pull_request(
        repo_path=state.repo_path,
        branch_name=branch_name,
        title=title,
        body=body,
        verbose=True,
    )
    
    state.pr_url = pr_url
    
    if pr_url:
        console.print(f"[green]✅ PR created: {pr_url}[/green]")
    else:
        console.print("[yellow]⚠ Could not create PR (continuing anyway)[/yellow]")
    
    return state


# ============================================================================
# Conditional Edges
# ============================================================================

def should_continue_after_flaky(state: AutoDevState) -> Literal["stop", "continue"]:
    """Decide whether to continue after flaky check."""
    if state.flaky_detected:
        return "stop"
    return "continue"


def should_retry(state: AutoDevState) -> Literal["success", "retry", "stop"]:
    """Decide next step after validation."""
    if state.sandbox_passed:
        return "success"
    
    if state.attempt + 1 >= state.max_attempts:
        state.stop_reason = state.stop_reason or "Max attempts reached"
        return "stop"
    
    # Increment attempt and retry
    state.attempt += 1
    console.print(f"[yellow]Retrying (attempt {state.attempt + 1}/{state.max_attempts})...[/yellow]")
    return "retry"


# ============================================================================
# Graph Builder
# ============================================================================

def build_graph() -> StateGraph:
    """
    Build the AutoDev repair loop graph.
    
    Returns:
        Compiled LangGraph state machine
    """
    # Create graph
    graph = StateGraph(AutoDevState)
    
    # Add nodes
    graph.add_node("collect_failure", collect_failure)
    graph.add_node("check_flaky", check_flaky)
    graph.add_node("collect_context", collect_context)
    graph.add_node("plan_fix", plan_fix)
    graph.add_node("generate_patch", generate_patch)
    graph.add_node("policy_check", policy_check)
    graph.add_node("apply_and_test", apply_and_test)
    graph.add_node("create_pr", create_pr)
    
    # Set entry point
    graph.set_entry_point("collect_failure")
    
    # Add edges
    graph.add_edge("collect_failure", "check_flaky")
    
    # Conditional: stop if flaky
    graph.add_conditional_edges(
        "check_flaky",
        should_continue_after_flaky,
        {
            "stop": END,
            "continue": "collect_context",
        }
    )
    
    graph.add_edge("collect_context", "plan_fix")
    graph.add_edge("plan_fix", "generate_patch")
    graph.add_edge("generate_patch", "policy_check")
    graph.add_edge("policy_check", "apply_and_test")
    
    # Conditional: retry or finish
    graph.add_conditional_edges(
        "apply_and_test",
        should_retry,
        {
            "success": "create_pr",
            "retry": "collect_context",  # Retry with new logs
            "stop": END,
        }
    )
    
    graph.add_edge("create_pr", END)
    
    # Compile
    return graph.compile()
