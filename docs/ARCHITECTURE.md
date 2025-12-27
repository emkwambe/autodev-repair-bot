# AutoDev Architecture

This document describes the internal architecture of AutoDev and the reasoning behind key design decisions.

---

## System Overview

AutoDev is a **stateful, event-driven repair agent** built around a verification-first loop.

```
┌─────────────────────────────────────────────────────────┐
│                    System Flow                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│    CI Failure                                           │
│        ↓                                                │
│    Flaky Detection ──────────────→ STOP (if flaky)     │
│        ↓                                                │
│    Context Collection                                   │
│        ↓                                                │
│    LLM Reasoning (Proposal)                             │
│        ↓                                                │
│    Policy Gate ──────────────────→ STOP (if violated)  │
│        ↓                                                │
│    Sandbox Execution (Docker)                           │
│        ↓                                                │
│    Verification Gate                                    │
│        ↓                        ↓                       │
│    PASS → PR              FAIL → Retry (bounded)       │
│                                  ↓                      │
│                            STOP + Diagnostic            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Orchestrator (LangGraph)

AutoDev uses LangGraph to model the repair loop as a finite state machine.

**Responsibilities:**
- Manage retries
- Persist state between attempts
- Enforce stop conditions
- Guarantee deterministic exit paths

**Why LangGraph?**
- Explicit state transitions (no hidden behavior)
- Built-in retry/loop support
- Easy to debug and trace
- Prevents uncontrolled agent behavior

---

### 2. Context Provider

Rather than sending entire repositories to the LLM, AutoDev retrieves:

- Failing test files
- Source files referenced in stack traces
- Nearby definitions (bounded)

**Benefits:**
- Improves LLM accuracy
- Reduces hallucinations
- Keeps costs down
- Faster processing

---

### 3. Reasoning Engine (GPT-4o)

The LLM is used in **two strictly separated steps**:

1. **Pre-flight reasoning**
   - Explain root cause
   - Justify fix strategy
   - No code generation yet

2. **Patch generation**
   - Output a unified diff only
   - No prose, no commands

**Critical constraint:** The LLM never executes code.

---

### 4. Policy Engine

Before any patch is applied, it is inspected for violations:

| Rule | Purpose |
|------|---------|
| Forbidden paths (`tests/`, `.github/`) | Prevent test/CI manipulation |
| Test bypass patterns | Block `skip`, `xfail`, etc. |
| Excessive diff size | Limit blast radius |
| Destructive edits | Prevent file deletion |
| Dangerous patterns | Block `os.system`, `eval`, etc. |

Policy enforcement is **deterministic and non-AI**.

---

### 5. Sandbox Executor (Docker)

All code execution occurs inside Docker:

| Security Feature | Implementation |
|-----------------|----------------|
| Non-root user | Container runs as `autodev` user |
| No network access | `network_disabled: true` |
| Clean environment | Fresh container per attempt |
| Resource limits | CPU/memory constraints |

**Key guarantee:** Host system is never at risk.

---

### 6. Verification Gate

A fix is considered valid only if:

- ✅ Failing tests pass
- ✅ No new failures are introduced
- ✅ Execution completes successfully

**No exceptions.**

---

### 7. Git Integration

When verification passes:
1. A new branch is created
2. Changes are committed
3. A pull request is opened with:
   - Failure summary
   - Fix explanation
   - Verification evidence
   - Risk notes

**AutoDev never merges code.**

---

## State Model

The `AutoDevState` class tracks everything:

```python
class AutoDevState:
    # Configuration
    repo_path: str
    test_command: str
    
    # Attempt tracking
    attempt: int
    max_attempts: int
    
    # Context
    failure_logs: str
    context_files: dict[str, str]
    
    # LLM outputs
    root_cause_analysis: str
    proposed_patch: str
    
    # Validation
    policy_violations: list[str]
    sandbox_passed: bool
    
    # Outcome
    stop_reason: str
    pr_url: str
```

---

## Failure Modes & Handling

| Scenario | AutoDev Behavior |
|----------|------------------|
| Flaky test | Stop + diagnostic report |
| Policy violation | Stop immediately |
| Patch fails to apply | Roll back + retry |
| New failures introduced | Roll back + retry |
| Max attempts reached | Stop + report |
| Docker unavailable | Stop with error |

---

## Threat Model

### Prevented Risks
- ❌ Destructive shell commands
- ❌ Test disabling
- ❌ CI manipulation
- ❌ Infinite loops
- ❌ Silent failures
- ❌ Host system damage

### Accepted Risks
- ⚠️ Incorrect but test-passing fixes (mitigated by human review)

**Mitigation:** All PRs require human approval before merge.

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                         Data Flow                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [Repository]                                                │
│       ↓                                                      │
│  [Test Execution] → [Failure Logs]                          │
│       ↓                                                      │
│  [Stack Trace Parser] → [Relevant Files]                    │
│       ↓                                                      │
│  [LLM: GPT-4o] → [Root Cause + Patch]                       │
│       ↓                                                      │
│  [Policy Guard] → [Violations?] → STOP                      │
│       ↓                                                      │
│  [Git Apply] → [Modified Repository]                        │
│       ↓                                                      │
│  [Docker Sandbox] → [Test Results]                          │
│       ↓                                                      │
│  [Verification] → PASS → [GitHub PR]                        │
│                 → FAIL → [Retry or Stop]                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Design Philosophy

AutoDev is designed to be:

| Quality | Meaning |
|---------|---------|
| **Conservative** | Prefer stopping over making risky changes |
| **Explainable** | Every decision is logged and traceable |
| **Reversible** | All changes can be rolled back |
| **Boring** | No clever tricks, just solid engineering |

**Trust is earned through verification, not confidence.**

---

## Extension Points

To add new capabilities:

1. **New LLM**: Implement adapter in `context/llm.py`
2. **New policy rules**: Add to `policy/rules.py`
3. **New language support**: Add test runner in `sandbox/`
4. **New CI platform**: Add client in `github/`

---

## Related Documentation

- [POLICY.md](POLICY.md) - Detailed policy rules
- [README.md](../README.md) - Getting started
