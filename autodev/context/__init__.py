"""
Context retrieval and parsing for AutoDev.

Handles:
- LLM integration (GPT-4o)
- Log parsing
- Smart file retrieval
- Flaky test detection
"""

from autodev.context.llm import llm
from autodev.context.prompts import PLAN_PROMPT, PATCH_PROMPT
from autodev.context.retriever import extract_files_from_trace, load_snippets
from autodev.context.flaky import detect_flakiness

__all__ = [
    "llm",
    "PLAN_PROMPT",
    "PATCH_PROMPT",
    "extract_files_from_trace",
    "load_snippets",
    "detect_flakiness",
]
