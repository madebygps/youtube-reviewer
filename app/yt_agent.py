import asyncio
import json
import logging
import os

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.observability import setup_observability

from models import (
    DeepComprehensionAgentResponse,
    DeepComprehensionNotes,
    GenerateInsightsEvent,
    KeyConceptsResponse
)
from utilities import extract_video_id, convert_to_text_with_timestamps, fetch_transcript

DEFAULT_AZURE_API_VERSION = "2024-02-15-preview"

chat_client = AzureOpenAIChatClient(
    api_key=os.environ.get("AZURE_OPENAI_API_KEY_GPT5"),
    endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_GPT5"),
    deployment_name=os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"),
    api_version=os.environ.get(
        "AZURE_OPENAI_ENDPOINT_VERSION_GPT5", DEFAULT_AZURE_API_VERSION
    ),
)

DEEP_COMPREHENSION_INSTRUCTIONS = """You are an expert educator and researcher who creates comprehensive study notes.
Your goal is to help someone deeply understand complex content as if they had researched every topic themselves.

When analyzing content, you must:

1. IDENTIFY THE MAIN THESIS
   - What is the central argument or point being made?
   - Summarize in 1-2 clear sentences.

2. EXTRACT KEY CONCEPTS
   For every term, acronym, institution, historical event, or specialized concept mentioned:
   - Provide a clear definition
   - Explain the historical context (when/why it was created, what problem it solved)
   - Explain how it works mechanically
   - Explain why it matters in this specific context
   - Note the timestamp where it's discussed
   - Keep to chronological order

3. MAP ARGUMENT CHAINS
   Break down the logical reasoning step by step:
   - What are the premises (starting facts/assumptions)?
   - What are the reasoning steps?
   - What conclusions are drawn?
   - What are the implications?

4. IDENTIFY CONNECTIONS
   How do different concepts relate to each other?
   - What are the cause-and-effect relationships?
   - What dependencies exist between concepts?

5. SYNTHESIZE
   Tie everything together:
   - What does this all mean when combined?
   - What is the complete picture?

6. NOTE OPEN QUESTIONS
   - What is left unanswered?
   - What would require further research?

Be thorough and assume no prior knowledge. Your notes should enable complete understanding of the original content."""

KEY_CONCEPTS_INSTRUCTIONS = """You are an expert educator and researcher who creates comprehensive study notes.
Your goal is to help someone deeply understand complex content as if they had researched every topic themselves.

When analyzing content, you must:


1. EXTRACT KEY CONCEPTS
   For every term, acronym, institution, historical event, or specialized concept mentioned:
   - Provide a clear definition
   - Explain the historical context (when/why it was created, what problem it solved)
   - Explain how it works mechanically
   - Explain why it matters in this specific context
   - Note the timestamp where it's discussed
   - Keep to chronological order

Be thorough and assume no prior knowledge."""


class CaptionExtractor(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "caption_extractor")

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[str]) -> None:
        try:
            data = json.loads(message)
            video_url = data.get("video_url") if isinstance(data, dict) else data
        except json.JSONDecodeError:
            video_url = message.strip()

        video_id = extract_video_id(video_url)

        if not video_id:
            await ctx.send_message(json.dumps({"error": "Invalid URL."}))
            return

        try:
            transcript = await asyncio.to_thread(fetch_transcript, video_id, ["en"])
            formatted_captions = convert_to_text_with_timestamps(transcript)

            await ctx.send_message(json.dumps({"captions": formatted_captions}))
        except Exception as e:
            logging.error(f"Error fetching transcript: {e}")
            await ctx.send_message(json.dumps({"error": f"Failed to fetch transcript: {e}"}))


class DeepComprehensionGenerator(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "deep_comprehension_generator")
        self._agent = chat_client.create_agent(
            instructions=DEEP_COMPREHENSION_INSTRUCTIONS,
            response_format=DeepComprehensionAgentResponse,
        )

    @handler
    async def handle(
        self, message: str, ctx: WorkflowContext[None, DeepComprehensionNotes]
    ) -> None:
        try:
            data = json.loads(message)
            captions = data.get("captions") if isinstance(data, dict) else data
            custom_prompt = data.get("custom_prompt") if isinstance(data, dict) else None
        except json.JSONDecodeError:
            captions = message.strip()
            custom_prompt = None

        if custom_prompt:
            prompt = f"{custom_prompt}\n\nYouTube video transcript:\n{captions}"
        else:
            prompt = (
                "Create comprehensive study notes for the following YouTube video transcript.\n"
                "I want to deeply understand this content as if I had researched every topic myself.\n\n"
                "For any specialized terms, concepts, institutions, or historical events:\n"
                "- Explain what they are and why they were created\n"
                "- Explain how they work\n"
                "- Explain why they matter in this context\n\n"
                "Then break down the logical arguments step by step, identify connections between concepts, "
                "and synthesize everything into a cohesive understanding.\n\n"
                f"Transcript:\n{captions}"
            )

        response = await self._agent.run(prompt)

        if isinstance(response.value, DeepComprehensionAgentResponse):
            notes = response.value.notes
            logging.info(
                f"Generated notes with {len(notes.key_concepts)} concepts, "
                f"{len(notes.argument_chains)} argument chains"
            )
            await ctx.add_event(GenerateInsightsEvent(notes))
            await ctx.yield_output(notes)
        else:
            logging.error(f"Unexpected response type: {type(response.value)}")
            empty_notes = DeepComprehensionNotes(
                main_thesis="Error generating notes",
                key_concepts=[],
                argument_chains=[],
                connections=[],
                synthesis="",
                open_questions=[],
            )
            await ctx.yield_output(empty_notes)
            #https://learn.microsoft.com/en-us/agent-framework/tutorials/agents/function-tools-approvals?pivots=programming-language-python


class KeyConceptsExtractor(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "key_concepts_extractor")
        self._agent = chat_client.create_agent(
            instructions=KEY_CONCEPTS_INSTRUCTIONS,
            response_format=KeyConceptsResponse,
        )

    @handler
    async def handle(
        self, message: str, ctx: WorkflowContext[None, KeyConceptsResponse]
    ) -> None:
        try:
            data = json.loads(message)
            captions = data.get("captions") if isinstance(data, dict) else data
        except json.JSONDecodeError:
            captions = message.strip()

        prompt = (
            "Extract and explain all key concepts from the following YouTube video transcript.\n\n"
            "For every term, acronym, institution, historical event, or specialized concept:\n"
            "- Provide a clear definition\n"
            "- Explain the historical context (when/why it was created)\n"
            "- Explain how it works\n"
            "- Explain why it matters in this context\n"
            "- Note the timestamp where it's discussed\n\n"
            f"Transcript:\n{captions}"
        )

        response = await self._agent.run(prompt)

        if isinstance(response.value, KeyConceptsResponse):
            logging.info(f"Extracted {len(response.value.key_concepts)} key concepts")
            await ctx.yield_output(response.value)
        else:
            logging.error(f"Unexpected response type: {type(response.value)}")
            await ctx.yield_output(KeyConceptsResponse(key_concepts=[]))
    

def get_workflow():
    caption_extractor = CaptionExtractor()
    key_concepts_extractor = KeyConceptsExtractor()
    return (
        WorkflowBuilder()
        .set_start_executor(caption_extractor)
        .add_edge(caption_extractor, key_concepts_extractor)
        .build()
    )


workflow = get_workflow()

setup_observability()
