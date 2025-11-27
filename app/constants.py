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
KEY_CONCEPTS_INSTRUCTIONS = """Extract key concepts from the transcript. Be extremely concise.

For each concept provide:
- term: The name
- definition: One sentence max
- relevance: One sentence max, why it matters HERE
- timestamp: When first mentioned

CRITICAL: Return concepts in CHRONOLOGICAL ORDER by timestamp (earliest first).

Keep definitions SHORT. No historical context. No "how it works". Just the essentials."""

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

# Knowledge level prompts
KNOWLEDGE_LEVEL_PROMPTS = {
    "beginner": "Include basic terms. 8-12 concepts max.",
    "intermediate": "Skip basics. 5-8 concepts.",
    "advanced": "Only specialized terms. 3-5 concepts max.",
}
