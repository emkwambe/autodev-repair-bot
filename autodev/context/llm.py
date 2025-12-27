"""
LLM Integration for AutoDev.

Uses GPT-4o as the reasoning engine with clean adapter interface
for future swapping to Llama 3 or other models.
"""

import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_llm(
    model: str = "gpt-4o",
    temperature: float = 0.1,
) -> ChatOpenAI:
    """
    Get configured LLM instance.
    
    Args:
        model: Model identifier (default: gpt-4o)
        temperature: Sampling temperature (lower = more deterministic)
        
    Returns:
        Configured ChatOpenAI instance
    """
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


# Default LLM instance
llm = get_llm()
