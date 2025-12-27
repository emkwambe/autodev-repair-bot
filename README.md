# AutoDev — Agentic CI/CD Repair Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

AutoDev is an **agentic CI/CD remediation system** that detects failing tests, proposes minimal code fixes using an LLM, validates them in a sandboxed environment, and opens a pull request **only if all verification gates pass**.

This project is intentionally engineered to treat AI as a *proposal engine*, not an authority. Every change is constrained, verified, and auditable.

---

## Why AutoDev Exists

Modern CI pipelines surface failures quickly, but resolving them still requires:

- Reproducing the failure locally
- Diagnosing root cause
- Making a safe change
- Re-running tests
- Preparing a pull request

AutoDev compresses this loop by automating **reproduction → diagnosis → patch proposal → sandbox verification**, while keeping humans in control of merging.

---

## Core Principles

| Principle | Description |
|-----------|-------------|
| **Verification over generation** | AI suggestions are accepted only if they pass deterministic checks |
| **Sandboxed execution** | All AI-generated code runs inside Docker, never on the host |
| **Bounded autonomy** | Attempts, diff size, and allowed actions are strictly limited |
| **Policy-enforced safety** | The agent is prevented from "cheating" (e.g., disabling tests) |
| **Auditability** | Every decision is logged, explainable, and reversible |

---

## What AutoDev Does

```
┌─────────────────────────────────────────────────────────────┐
│                    AutoDev Repair Loop                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Detect failing test run (locally or via CI trigger)    │
│                          ↓                                  │
│  2. Check for flaky tests (abort if non-deterministic)     │
│                          ↓                                  │
│  3. Retrieve relevant code context (smart, not entire repo)│
│                          ↓                                  │
│  4. Use GPT-4o to:                                         │
│     • Explain the root cause                               │
│     • Propose a minimal fix                                │
│                          ↓                                  │
│  5. Validate against policy rules                          │
│                          ↓                                  │
│  6. Apply patch on a clean git branch                      │
│                          ↓                                  │
│  7. Re-run tests in Docker sandbox                         │
│                          ↓                                  │
│  8. ONLY if tests pass → Open pull request                 │
│     Otherwise → Retry (bounded) or produce diagnostic      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## What AutoDev Does *Not* Do

- ❌ Auto-merge code
- ❌ Run on the host machine
- ❌ Modify or delete tests (by default)
- ❌ Disable CI workflows
- ❌ Loop indefinitely
- ❌ Hide failures

These constraints are deliberate.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (running)
- OpenAI API key
- GitHub Personal Access Token (for PR creation)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/autodev-repair-bot.git
cd autodev-repair-bot

# Install
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env with your API keys
```

### Usage

```bash
# Basic usage
autodev --repo /path/to/failing/repo --cmd "pytest -q"

# With options
autodev --repo . --cmd "pytest tests/" --max-attempts 3

# Verify fix without creating PR
autodev --repo /path/to/repo --cmd "pytest -q" --no-pr
```

AutoDev will:
1. Detect the failure
2. Check for flakiness
3. Propose a fix
4. Validate in sandbox
5. Open a verified PR (or stop with diagnostics)

---

## Supported Stack

| Component | Technology |
|-----------|------------|
| Language | Python |
| Test Runner | pytest |
| Agent Orchestration | LangGraph |
| Sandbox | Docker |
| LLM | GPT-4o |
| CI Integration | GitHub Actions |

---

## Safety & Trust Model

AutoDev enforces multiple independent gates:

### Policy Gate
- Forbids modifying tests and CI config
- Limits patch size
- Blocks test bypass patterns (`skip`, `xfail`, etc.)

### Sandbox Gate
- Docker execution with no network access
- Clean environment per attempt
- Non-root user isolation

### Verification Gate
- Failing tests must pass
- No new failures allowed
- Execution must complete successfully

**If any gate fails, AutoDev stops.**

---

## CI Integration

### GitHub Actions (Manual Trigger)

```yaml
name: AutoDev Repair

on:
  workflow_dispatch:
    inputs:
      test_command:
        default: 'pytest -q'

jobs:
  autodev:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: autodev --repo . --cmd "${{ inputs.test_command }}"
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Metrics & Observability

AutoDev records structured metrics per run:

- Attempts used
- Pass/fail outcome
- Flaky detection
- Policy violations
- Stop reason

Metrics are stored in `autodev_metrics.jsonl` for analysis.

---

## Roadmap

| Feature | Status |
|---------|--------|
| Multi-Language Support (Node + Python) | Planned |
| PR Risk Scoring | Planned |
| Test Impact Analysis | Planned |
| Llama 3 Offline Fallback | Planned |
| Policy Learning (Adaptive Thresholds) | Research |

---

## Project Structure

```
autodev-repair-bot/
├── autodev/
│   ├── context/         # LLM, prompts, retrieval
│   ├── github/          # PR creation
│   ├── metrics/         # Observability
│   ├── patching/        # Patch application
│   ├── policy/          # Safety guardrails
│   ├── sandbox/         # Docker execution
│   ├── graph.py         # LangGraph state machine
│   ├── main.py          # CLI entry point
│   └── state.py         # Agent state model
├── docker/
│   └── runner.Dockerfile
├── docs/
│   ├── ARCHITECTURE.md
│   └── POLICY.md
├── tests/
└── .github/workflows/
```

---

## Contributing

Contributions are welcome! Please read the [Architecture](docs/ARCHITECTURE.md) and [Policy](docs/POLICY.md) documentation first.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [LangChain](https://github.com/langchain-ai/langchain) - LLM integration
- [Docker](https://www.docker.com/) - Sandbox isolation
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal output
