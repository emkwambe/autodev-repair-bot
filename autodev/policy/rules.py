"""
Policy Rules Configuration for AutoDev.

These rules prevent "cheating" fixes that:
- Disable or skip tests
- Modify CI configuration
- Make destructive changes
"""

from dataclasses import dataclass, field


# Paths that cannot be modified by AutoDev
FORBIDDEN_PATHS = (
    "tests/",
    "test/",
    "__tests__/",
    ".github/",
    ".gitlab-ci",
    "Jenkinsfile",
    ".circleci/",
    "azure-pipelines",
)

# Patterns that indicate test bypass attempts
FORBIDDEN_PATTERNS = (
    "pytest.skip",
    "@pytest.mark.skip",
    "@pytest.mark.xfail",
    "xfail",
    "skipIf",
    "skipUnless",
    "unittest.skip",
    "@skip",
    "# noqa",  # Suspicious if added to bypass linting
    "pass  # TODO",  # Placeholder that bypasses logic
)

# Patterns that indicate dangerous code
DANGEROUS_PATTERNS = (
    "os.system",
    "subprocess.call",
    "eval(",
    "exec(",
    "__import__",
    "os.remove",
    "shutil.rmtree",
)


@dataclass
class PolicyConfig:
    """
    Configurable policy settings.
    
    These can be adjusted per-repository if needed.
    """
    
    # Path restrictions
    forbidden_paths: tuple[str, ...] = FORBIDDEN_PATHS
    allow_test_modifications: bool = False
    
    # Pattern restrictions  
    forbidden_patterns: tuple[str, ...] = FORBIDDEN_PATTERNS
    check_dangerous_patterns: bool = True
    
    # Size limits
    max_files_changed: int = 5
    max_lines_changed: int = 150
    max_hunks_per_file: int = 10
    
    # Behavior
    allow_file_deletion: bool = False
    allow_new_files: bool = True
    require_minimal_diff: bool = True
    
    # Dependency handling
    allow_dependency_changes: bool = False
    dependency_files: tuple[str, ...] = field(default_factory=lambda: (
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Pipfile",
        "poetry.lock",
        "Pipfile.lock",
    ))


# Default policy instance
DEFAULT_POLICY = PolicyConfig()
