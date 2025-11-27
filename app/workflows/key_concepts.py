"""Workflow for Phase 1: Extract captions and key concepts from YouTube videos."""

import asyncio
import json
import logging

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

from chat_client import chat_client
from constants import KEY_CONCEPTS_INSTRUCTIONS, KNOWLEDGE_LEVEL_PROMPTS
from models import KeyConceptsResponse
from utilities import (
    cache_captions,
    convert_to_text_with_timestamps,
    extract_video_id,
    fetch_transcript,
    get_cached_captions,
)

logger = logging.getLogger(__name__)


class CaptionExtractor(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "caption_extractor")

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[str]) -> None:
        video_id = None
        try:
            data = json.loads(message)
            video_url = data.get("video_url") if isinstance(data, dict) else data
            knowledge_level = (
                data.get("knowledge_level", "beginner")
                if isinstance(data, dict)
                else "beginner"
            )
        except json.JSONDecodeError:
            video_url = message.strip()
            knowledge_level = "beginner"

        video_id = extract_video_id(video_url)

        if not video_id:
            await ctx.send_message(json.dumps({"error": "Invalid URL."}))
            return

        try:
            # Check cache first
            formatted_captions = get_cached_captions(video_id)
            
            if formatted_captions:
                logger.info(f"📦 Using cached captions for video {video_id}")
            else:
                logger.info(f"🌐 Fetching fresh captions for video {video_id}")
                transcript = await asyncio.to_thread(fetch_transcript, video_id, ["en"])
                formatted_captions = convert_to_text_with_timestamps(transcript)
                
                # Cache captions for subsequent phases
                cache_captions(video_id, formatted_captions)

            # Pass captions, video_id, and knowledge_level to next executor
            await ctx.send_message(
                json.dumps(
                    {"captions": formatted_captions, "video_id": video_id, "knowledge_level": knowledge_level}
                )
            )
        except Exception as e:
            logger.error(f"Error fetching transcript: {e}")
            await ctx.send_message(
                json.dumps({"error": f"Failed to fetch transcript: {e}"})
            )


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
        video_id = None
        try:
            data = json.loads(message)
            captions = data.get("captions") if isinstance(data, dict) else data
            video_id = data.get("video_id") if isinstance(data, dict) else None
            knowledge_level = (
                data.get("knowledge_level", "beginner")
                if isinstance(data, dict)
                else "beginner"
            )
        except json.JSONDecodeError:
            captions = message.strip()
            knowledge_level = "beginner"

        # Get the appropriate knowledge level guidance
        level_guidance = KNOWLEDGE_LEVEL_PROMPTS.get(
            knowledge_level, KNOWLEDGE_LEVEL_PROMPTS["beginner"]
        )

        prompt = (
            f"VIEWER KNOWLEDGE LEVEL: {level_guidance}\n\n"
            "Extract key concepts from the following YouTube video transcript.\n\n"
            f"Transcript:\n{captions}"
        )

        response = await self._agent.run(prompt)

        if isinstance(response.value, KeyConceptsResponse):
            logger.info(f"Extracted {len(response.value.key_concepts)} key concepts")
            # Attach video_id so subsequent phases can fetch captions from cache
            response.value.video_id = video_id
            await ctx.yield_output(response.value)
        else:
            logger.error(f"Unexpected response type: {type(response.value)}")
            await ctx.yield_output(KeyConceptsResponse(key_concepts=[]))


def get_key_concepts_workflow():
    """Workflow for Phase 1: Extract captions and key concepts."""
    caption_extractor = CaptionExtractor()
    key_concepts_extractor = KeyConceptsExtractor()
    return (
        WorkflowBuilder()
        .set_start_executor(caption_extractor)
        .add_edge(caption_extractor, key_concepts_extractor)
        .build()
    )


key_concepts_workflow = get_key_concepts_workflow()
