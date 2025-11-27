"""Constants and instruction prompts for the YouTube reviewer agents."""

import os

DEFAULT_AZURE_API_VERSION = "2024-02-15-preview"

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY_GPT5")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT_GPT5")
AZURE_OPENAI_DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5")
AZURE_OPENAI_API_VERSION = os.environ.get(
    "AZURE_OPENAI_ENDPOINT_VERSION_GPT5", DEFAULT_AZURE_API_VERSION
)

# Agent Instructions
KEY_CONCEPTS_INSTRUCTIONS = """You are an expert educator and researcher who creates comprehensive study notes.
Your goal is to help someone deeply understand complex content.

When analyzing content, extract KEY CONCEPTS:
- For each term, acronym, institution, historical event, or specialized concept:
  - Provide a clear definition
  - Explain the historical context (when/why it was created, what problem it solved)
  - Explain how it works mechanically
  - Explain why it matters in this specific context
  - Note the timestamp where it's discussed
  - MUST MAINTAIN chronological order

IMPORTANT: Adjust depth based on the viewer's prior knowledge level provided in the prompt.
Do NOT explain concepts that someone at that knowledge level would already know."""

THESIS_ARGUMENT_INSTRUCTIONS = """You are an expert educator and researcher who deeply understands arguments.
Summarize the main thesis and break down all argument chains in the content.

When analyzing content, you must:

1. IDENTIFY THE MAIN THESIS
    - What is the central argument or point being made?
    - Summarize in 1-2 clear sentences.

2. MAP ARGUMENT CHAINS
    Break down the logical reasoning step by step:
    - What are the premises (starting facts/assumptions)?
    - What are the reasoning steps?
    - What conclusions are drawn?
    - What are the implications?

Respond in the schema provided. Be concise but complete."""

CLAIM_VERIFIER_INSTRUCTIONS = """"""

# Knowledge level prompts that modify concept extraction behavior
KNOWLEDGE_LEVEL_PROMPTS = {
    "beginner": (
        "The viewer is a BEGINNER with no prior knowledge of this topic. "
        "Extract and explain ALL concepts, including basic terminology. "
        "Assume they need everything explained from scratch."
    ),
    "intermediate": (
        "The viewer has INTERMEDIATE knowledge. "
        "Skip commonly known concepts "
        "Focus on domain-specific terminology, historical context, and specialized concepts "
        "that require deeper understanding. Aim for 10-20 key concepts."
    ),
    "advanced": (
        "The viewer is ADVANCED and familiar with this domain. "
        "Only extract highly specialized concepts, nuanced distinctions, "
        "and novel ideas that even an expert might want clarified. "
        "Be very selective - aim for 5-10 truly essential concepts."
    ),
}
