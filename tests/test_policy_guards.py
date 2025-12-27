"""
Tests for AutoDev Policy Guard.

These tests verify that the policy engine correctly:
- Blocks forbidden path modifications
- Detects test bypass patterns
- Enforces diff size limits
- Prevents dangerous patterns
"""

import pytest

from autodev.policy.diff_guard import validate_patch, is_patch_safe
from autodev.policy.rules import PolicyConfig


class TestPolicyGuard:
    """Test suite for policy guard validation."""
    
    def test_valid_patch_passes(self):
        """A clean, minimal patch should pass all checks."""
        diff = """--- a/src/calculator.py
+++ b/src/calculator.py
@@ -10,7 +10,9 @@ def divide(a, b):
-    return a / b
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
+    return a / b
"""
        violations = validate_patch(diff)
        assert len(violations) == 0
        assert is_patch_safe(diff)
    
    def test_blocks_test_modifications(self):
        """Modifications to test files should be blocked."""
        diff = """--- a/tests/test_calculator.py
+++ b/tests/test_calculator.py
@@ -5,7 +5,7 @@ def test_divide():
-    assert divide(10, 2) == 5
+    assert divide(10, 2) == 6
"""
        violations = validate_patch(diff)
        assert len(violations) > 0
        assert any("test" in v.lower() for v in violations)
    
    def test_blocks_github_workflow_changes(self):
        """Changes to CI configuration should be blocked."""
        diff = """--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -10,7 +10,7 @@ jobs:
-    runs-on: ubuntu-latest
+    runs-on: self-hosted
"""
        violations = validate_patch(diff)
        assert len(violations) > 0
    
    def test_blocks_pytest_skip(self):
        """Adding pytest.skip should be blocked."""
        diff = """--- a/src/utils.py
+++ b/src/utils.py
@@ -1,5 +1,6 @@
+import pytest; pytest.skip("skip this")
 def helper():
     pass
"""
        violations = validate_patch(diff)
        assert len(violations) > 0
        assert any("skip" in v.lower() for v in violations)
    
    def test_blocks_xfail(self):
        """Adding xfail markers should be blocked."""
        diff = """--- a/src/module.py
+++ b/src/module.py
@@ -1,4 +1,5 @@
+@pytest.mark.xfail
 def function():
     pass
"""
        violations = validate_patch(diff)
        assert len(violations) > 0
    
    def test_blocks_assertion_removal(self):
        """Removing assertions should be flagged."""
        diff = """--- a/src/validator.py
+++ b/src/validator.py
@@ -5,7 +5,6 @@ def validate(data):
-    assert data is not None
     return True
"""
        violations = validate_patch(diff)
        assert len(violations) > 0
        assert any("assert" in v.lower() for v in violations)
    
    def test_blocks_oversized_patch(self):
        """Patches that are too large should be blocked."""
        # Generate a large patch
        lines = []
        for i in range(200):
            lines.append(f"+# line {i}")
        
        diff = f"""--- a/src/big_file.py
+++ b/src/big_file.py
@@ -1,0 +1,200 @@
{'chr(10).join(lines)}
"""
        violations = validate_patch(diff)
        assert len(violations) > 0
        assert any("large" in v.lower() or "size" in v.lower() for v in violations)
    
    def test_blocks_dangerous_patterns(self):
        """Dangerous code patterns should be flagged."""
        diff = """--- a/src/module.py
+++ b/src/module.py
@@ -1,4 +1,5 @@
+os.system("rm -rf /")
 def function():
     pass
"""
        violations = validate_patch(diff)
        assert len(violations) > 0
        assert any("dangerous" in v.lower() for v in violations)
    
    def test_empty_patch_rejected(self):
        """Empty patches should be rejected."""
        violations = validate_patch("")
        assert len(violations) > 0
    
    def test_invalid_diff_format_rejected(self):
        """Invalid diff format should be rejected."""
        violations = validate_patch("this is not a valid diff")
        assert len(violations) > 0
    
    def test_custom_policy_allows_deps(self):
        """Custom policy can allow dependency changes."""
        diff = """--- a/requirements.txt
+++ b/requirements.txt
@@ -1,3 +1,4 @@
 requests==2.28.0
+new-package==1.0.0
 pytest==7.0.0
"""
        # Default policy blocks it
        default_violations = validate_patch(diff)
        assert len(default_violations) > 0
        
        # Custom policy allows it
        custom_policy = PolicyConfig(allow_dependency_changes=True)
        custom_violations = validate_patch(diff, policy=custom_policy)
        assert len(custom_violations) == 0
    
    def test_blocks_file_deletion(self):
        """File deletions should be blocked by default."""
        diff = """--- a/src/old_module.py
+++ /dev/null
@@ -1,10 +0,0 @@
-def old_function():
-    pass
"""
        violations = validate_patch(diff)
        assert len(violations) > 0
        assert any("delet" in v.lower() for v in violations)


class TestPolicySafety:
    """Verify the policy guard is robust against bypass attempts."""
    
    def test_path_normalization(self):
        """Paths should be normalized to catch variants."""
        # Windows-style path
        diff = """--- a\\tests\\test_file.py
+++ b\\tests\\test_file.py
@@ -1,1 +1,1 @@
-pass
+pass  # modified
"""
        violations = validate_patch(diff)
        assert len(violations) > 0
    
    def test_nested_test_path(self):
        """Deeply nested test paths should be caught."""
        diff = """--- a/src/submodule/tests/test_deep.py
+++ b/src/submodule/tests/test_deep.py
@@ -1,1 +1,1 @@
-pass
+pass  # modified
"""
        violations = validate_patch(diff)
        assert len(violations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
