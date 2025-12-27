"""
LLM Prompts for AutoDev.

Two-step prompting strategy:
1. Pre-flight reasoning (diagnosis)
2. Patch generation (structured diff output)

This separation improves accuracy and makes PR summaries informative.
"""

PLAN_PROMPT = """You are a senior Python engineer diagnosing a test failure.

Given the following pytest failure logs and relevant source code, provide:

1. **Root Cause Analysis**: What is causing the test to fail?
2. **Fix Strategy**: What is the minimal change needed to fix this?

## Rules
- DO NOT propose modifying test files
- DO NOT write any code yet
- Focus on the SOURCE code, not the test assertions
- Prefer the smallest possible change

## Failure Logs
```
{logs}
```

## Relevant Source Files
{context}

Provide a clear, concise analysis."""

PATCH_PROMPT = """You are a senior Python engineer generating a fix.

Based on the analysis below, generate a **unified diff** that fixes the issue.

## Analysis
{plan}

## Original Failure
```
{logs}
```

## Rules (CRITICAL)
- Output ONLY a valid unified diff (no prose, no explanation)
- Modify SOURCE code only, NEVER test files
- Make the MINIMAL change possible
- Use correct diff format: `--- a/path` and `+++ b/path`
- Include proper @@ line markers

## Example Format
```diff
--- a/src/calculator.py
+++ b/src/calculator.py
@@ -10,7 +10,7 @@ def divide(a, b):
-    return a / b
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
+    return a / b
```

Generate the diff now:"""

DIAGNOSTIC_PROMPT = """You are a senior Python engineer reviewing a test failure that could not be automatically fixed.

## Failure Logs
```
{logs}
```

## Attempts Made
{attempts}

## Policy Violations (if any)
{violations}

## Flaky Detection
{flaky_info}

Provide a brief diagnostic report explaining:
1. Why automatic repair was not possible
2. Recommended manual actions
3. Whether this appears to be a code bug, infrastructure issue, or flaky test

Keep it concise and actionable."""
