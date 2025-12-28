# AutoDev Usage Guide

## Prerequisites

Before using AutoDev, ensure you have:

1. **Python 3.10+** installed
2. **Docker Desktop** installed and running
3. **OpenAI API Key** (for GPT-4o reasoning)
4. **GitHub Token** (optional, only for PR creation)

---

## Installation

### From Source
`ash
git clone https://github.com/emkwambe/autodev-repair-bot.git
cd autodev-repair-bot
pip install -e ".[dev]"
`

### Verify Installation
`ash
autodev --version
# or
python -m autodev.main --version
`

---

## Configuration

### 1. Create Environment File
`ash
cp .env.example .env
`

### 2. Add Your API Keys

Edit `.env`:
`
OPENAI_API_KEY=sk-your-actual-openai-key
GITHUB_TOKEN=ghp-your-github-token  # Optional
`

---

## Basic Usage

### Command Syntax
`ash
autodev --repo <path-to-repo> --cmd <test-command> [options]
`

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--repo` | Path to repository (required) | - |
| `--cmd` | Test command to run | `pytest -q` |
| `--max-attempts` | Max repair attempts | 2 |
| `--no-pr` | Skip PR creation | False |
| `--quiet` | Reduce output | False |

---

## Examples

### Example 1: Fix a Local Repo (No PR)
`ash
autodev --repo ~/my-project --cmd "pytest" --no-pr
`

### Example 2: Fix and Create PR
`ash
autodev --repo ~/my-project --cmd "pytest tests/" --max-attempts 3
`

### Example 3: Custom Test Command
`ash
autodev --repo ~/my-project --cmd "python -m pytest tests/unit/"
`

---

## Quick Test (Create a Failing Repo)

### Step 1: Create Test Repository
`ash
mkdir ~/test-repo && cd ~/test-repo
git init
`

### Step 2: Create a Buggy File
`python
# calculator.py
def add(a, b):
    return a - b  # Bug: should be a + b

def multiply(a, b):
    return a * b
`

### Step 3: Create a Failing Test
`python
# test_calculator.py
from calculator import add, multiply

def test_add():
    assert add(2, 3) == 5  # This will fail!

def test_multiply():
    assert multiply(2, 3) == 6  # This passes
`

### Step 4: Run AutoDev
`ash
autodev --repo ~/test-repo --cmd "pytest" --no-pr
`

### What Happens:

1. AutoDev detects `test_add` is failing
2. Checks if it's a flaky test (runs 3x)
3. Analyzes the code with GPT-4o
4. Proposes fix: change `a - b` to `a + b`
5. Applies fix in Docker sandbox
6. Re-runs tests to verify
7. Reports success!

---

## How AutoDev Works
`
┌─────────────────────────────────────────────┐
│            AutoDev Repair Loop              │
├─────────────────────────────────────────────┤
│                                             │
│  1. Detect failing tests                    │
│              ↓                              │
│  2. Check for flaky tests (run 3x)          │
│              ↓                              │
│  3. Collect relevant code context           │
│              ↓                              │
│  4. GPT-4o analyzes root cause              │
│              ↓                              │
│  5. GPT-4o generates minimal patch          │
│              ↓                              │
│  6. Policy check (no test modifications)    │
│              ↓                              │
│  7. Apply patch in Docker sandbox           │
│              ↓                              │
│  8. Re-run tests in sandbox                 │
│              ↓                              │
│  PASS → Create PR    FAIL → Retry (max 2)   │
│                                             │
└─────────────────────────────────────────────┘
`

---

## Safety Guardrails

AutoDev will **NOT**:

- ❌ Modify test files
- ❌ Delete files
- ❌ Change CI/CD configuration
- ❌ Skip or disable tests
- ❌ Make large changes (>150 lines)
- ❌ Auto-merge PRs

---

## Troubleshooting

### Docker Not Running
`
Error: Docker is not available
`

**Fix:** Start Docker Desktop and try again.

### OpenAI API Key Missing
`
Error: OPENAI_API_KEY environment variable not set
`

**Fix:** Add your key to `.env` file.

### Permission Denied (Windows)
`ash
# Run PowerShell as Administrator, or use:
python -m autodev.main --repo <path> --cmd "pytest"
`

---

## GitHub Actions Integration

Add to your repo's `.github/workflows/autodev.yml`:
`yaml
name: AutoDev Repair

on:
  workflow_dispatch:
    inputs:
      test_command:
        default: 'pytest -q'

jobs:
  repair:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install autodev-repair-bot
      - run: autodev --repo . --cmd "${{ inputs.test_command }}"
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
`

---

## Getting Help

- **Issues:** https://github.com/emkwambe/autodev-repair-bot/issues
- **Docs:** https://github.com/emkwambe/autodev-repair-bot#readme
