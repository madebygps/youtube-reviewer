import asyncio
import logging
import os
import re
from typing import List

from youtube_transcript_api import YouTubeTranscriptApi
from pydantic import BaseModel, Field
from agent_framework import (
    ChatAgent,
    ChatMessage,
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowEvent,
    handler,
)
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.observability import setup_observability


DEFAULT_AZURE_API_VERSION = "2024-02-15-preview"

chat_client = AzureOpenAIChatClient(
    api_key=os.environ.get("AZURE_OPENAI_API_KEY_GPT5"),
    endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_GPT5"),
    deployment_name=os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"),
    api_version=os.environ.get(
        "AZURE_OPENAI_ENDPOINT_VERSION_GPT5", DEFAULT_AZURE_API_VERSION
    ),
)

# Custom Workflow Events


class GenerateInsightsEvent(WorkflowEvent):
    """Event emitted when insights generation is complete."""

    def __init__(self, insights_data: "ActionableInsightsAgentResponse"):
        super().__init__(
            f"Insights generation complete "
            f"with {len(insights_data.insights)} insights"
        )
        self.insights_data = insights_data


class ActionableInsight(BaseModel):
    description: str = Field(
        ...,
        description="The actionable insight derived from the video captions.",
    )
    timestamp: str = Field(
        ...,
        description="The timestamp from when the actionable insight "
        "is based off of.",
    )


class ActionableInsightsAgentResponse(BaseModel):
    insights: List[ActionableInsight] = Field(
        ...,
        description="A list of actionable insights derived " \
        "from the video captions.",
    )


class CaptionExtractor(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "caption_extractor")

    @handler
    async def handle(
        self, message: ChatMessage, ctx: WorkflowContext[str]
    ) -> None:
        # Parse message: format is "video_url|||PROMPT_SEPARATOR|||custom_prompt" or just "video_url"
        message_text = message.text.strip()
        if "|||PROMPT_SEPARATOR|||" in message_text:
            message_parts = message_text.split("|||PROMPT_SEPARATOR|||", 1)
            video_url = message_parts[0]
            custom_prompt = message_parts[1]
        else:
            video_url = message_text
            custom_prompt = None

        # Extract video ID from URL
        video_id = self._extract_video_id(video_url)

        # Fetch transcript
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, ["en"])
        transcript = fetched.snippets

        # Convert to SRT format
        srt_captions = self._convert_to_srt(transcript)

        # Pass both captions and custom prompt to next executor
        if custom_prompt:
            await ctx.send_message(
                f"{srt_captions}|||CUSTOM_PROMPT|||{custom_prompt}"
            )
        else:
            await ctx.send_message(srt_captions)

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        patterns = [
            r"(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)",
            r"youtube\.com\/embed\/([^&\n?#]+)",
            r"youtube\.com\/v\/([^&\n?#]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ValueError(f"Could not extract video ID from URL: {url}")

    def _convert_to_srt(self, transcript: list) -> str:
        """Convert transcript to SRT format"""
        srt_lines = []
        for i, entry in enumerate(transcript, 1):
            start = self._format_timestamp(entry.start)
            end = self._format_timestamp(entry.start + entry.duration)
            text = entry.text

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")

        return "\n".join(srt_lines)

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class ActionableSummaryGenerator(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "actionable_summary_generator")
        self._actionable_insights_agent = chat_client.create_agent(
            instructions=(
                "You are an expert at summarizing YouTube video captions into "
                "actionable insights."
            ),
            response_format=ActionableInsightsAgentResponse,
        )

    @handler
    async def handle(
        self, message: str, ctx: WorkflowContext[List[ActionableInsight]]
    ) -> None:
        # Parse message: format is "captions|||CUSTOM_PROMPT|||prompt" or just "captions"
        message_parts = message.split("|||CUSTOM_PROMPT|||", 1)
        captions = message_parts[0]
        custom_prompt = message_parts[1] if len(message_parts) > 1 else None

        logging.info(f"Received captions length: {len(captions)} characters")
        logging.info(f"First 500 chars: {captions[:500]}")
        logging.info(f"Custom prompt provided: {custom_prompt is not None}")

        # Build the prompt based on whether custom prompt is provided
        if custom_prompt:
            prompt = f"{custom_prompt}\n\nYouTube video captions:\n{captions}"
        else:
            prompt = (
                "Based on the following YouTube video captions, "
                "generate a concise "
                "summary highlighting key points and actionable "
                "insights for the content creator:\n\n"
                f"{captions}"
            )

        agent_response = await self._actionable_insights_agent.run(prompt)

        insights_payload = agent_response.value
        logging.info(f"Agent response type: {type(insights_payload)}")
        logging.info(f"Insights payload: {insights_payload}")

        # Extract the insights list from the response
        if insights_payload and hasattr(insights_payload, "insights"):
            insights = insights_payload.insights
            logging.info(f"Extracted {len(insights)} insights")
            await ctx.add_event(GenerateInsightsEvent(insights_payload))
            await ctx.yield_output(insights)
        else:
            logging.warning("No insights generated")
            await ctx.yield_output([])


def get_workflow():
    caption_extractor = CaptionExtractor()
    actionable_summary_generator = ActionableSummaryGenerator()
    workflow = (
        WorkflowBuilder()
        .set_start_executor(caption_extractor)
        .add_edge(caption_extractor, actionable_summary_generator)
        .build()
    )
    return workflow


workflow = get_workflow()

setup_observability()
