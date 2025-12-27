# AutoDev Policy Documentation

This document details the policy rules that govern AutoDev's behavior. These rules are the foundation of trust in the system.

---

## Core Philosophy

> "The agent is allowed to try, but it only ships when tests pass, and it cannot bypass safety checks."

Policy enforcement is:
- **Deterministic** - No AI involved in policy decisions
- **Non-negotiable** - Rules cannot be overridden by the LLM
- **Auditable** - All violations are logged

---

## Forbidden Paths

The following paths cannot be modified by AutoDev:

| Path | Reason |
|------|--------|
| `tests/` | Prevent test manipulation |
| `test/` | Alternative test directory |
| `__tests__/` | JavaScript-style test directory |
| `.github/` | Prevent CI/CD manipulation |
| `.gitlab-ci` | GitLab CI configuration |
| `Jenkinsfile` | Jenkins pipeline |
| `.circleci/` | CircleCI configuration |
| `azure-pipelines` | Azure DevOps pipelines |

**Rationale:** If the agent could modify tests, it could "fix" failures by removing or weakening assertions.

---

## Forbidden Patterns

The following patterns are blocked when added to code:

| Pattern | Reason |
|---------|--------|
| `pytest.skip` | Bypasses test execution |
| `@pytest.mark.skip` | Marks test to be skipped |
| `@pytest.mark.xfail` | Marks test as expected to fail |
| `xfail` | Expected failure marker |
| `skipIf` / `skipUnless` | Conditional skip |
| `unittest.skip` | Standard library skip |
| `@skip` | Generic skip decorator |

**Rationale:** These patterns would allow the agent to "pass" tests by simply not running them.

---

## Dangerous Patterns

The following patterns trigger warnings:

| Pattern | Risk |
|---------|------|
| `os.system` | Arbitrary command execution |
| `subprocess.call` | Arbitrary command execution |
| `eval(` | Code injection |
| `exec(` | Code injection |
| `__import__` | Dynamic import manipulation |
| `os.remove` | File deletion |
| `shutil.rmtree` | Directory deletion |

**Rationale:** Even in sandboxed execution, these patterns indicate potentially malicious intent.

---

## Size Limits

| Metric | Default Limit | Rationale |
|--------|---------------|-----------|
| Files changed | 5 | Limit blast radius |
| Lines changed | 150 | Keep patches reviewable |
| Hunks per file | 10 | Prevent scattered changes |

**Philosophy:** Minimal patches are safer and easier to review.

---

## Behavior Rules

### File Deletion
- **Default:** Disabled
- **Override:** `allow_file_deletion: true`

### New File Creation
- **Default:** Allowed
- **Override:** `allow_new_files: false`

### Dependency Changes
- **Default:** Disabled
- **Override:** `allow_dependency_changes: true`

Protected dependency files:
- `requirements.txt`
- `pyproject.toml`
- `setup.py`
- `setup.cfg`
- `Pipfile` / `Pipfile.lock`
- `poetry.lock`

---

## Attempt Budget

| Setting | Default | Description |
|---------|---------|-------------|
| `max_attempts` | 2 | Maximum repair attempts |

**Rationale:** Unbounded retries waste resources and delay human intervention.

---

## Custom Policy Configuration

You can customize policy for specific repositories:

```python
from autodev.policy.rules import PolicyConfig

custom_policy = PolicyConfig(
    # Allow test modifications (use with caution)
    allow_test_modifications=False,
    
    # Allow dependency updates
    allow_dependency_changes=True,
    
    # Larger patches allowed
    max_lines_changed=300,
    max_files_changed=10,
    
    # Allow file deletion
    allow_file_deletion=True,
)
```

**Warning:** Relaxing policies reduces safety guarantees.

---

## Violation Handling

When a policy violation is detected:

1. **Patch is rejected** - Not applied to the repository
2. **Violation is logged** - Added to `policy_violations` list
3. **Retry may occur** - If attempts remain
4. **Diagnostic produced** - If max attempts reached

---

## Assertion Protection

AutoDev specifically protects against assertion removal:

```python
# This would be flagged:
-    assert result > 0
+    # assert result > 0  # Commented out
```

**Rationale:** Removing assertions is a common way to make tests pass without fixing the underlying bug.

---

## Policy Testing

The policy engine has its own test suite:

```bash
pytest tests/test_policy_guards.py -v
```

Tests verify:
- Forbidden paths are blocked
- Forbidden patterns are detected
- Size limits are enforced
- Edge cases are handled

---

## Escape Hatches

In exceptional cases, you may need to bypass policies. This is **not recommended** but possible:

```python
# Override specific rules
policy = PolicyConfig(
    forbidden_paths=(),  # Allow all paths (dangerous!)
    forbidden_patterns=(),  # Allow all patterns (dangerous!)
)
```

**Use only for testing or in controlled environments.**

---

## Future Enhancements

| Feature | Status |
|---------|--------|
| Semantic pattern detection | Planned |
| Repository-specific profiles | Planned |
| Policy learning from history | Research |
| Multi-language support | Planned |

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [README.md](../README.md) - Getting started
