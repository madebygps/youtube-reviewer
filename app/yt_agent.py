import asyncio
import json
import logging
import os
from typing import List, Never

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.observability import setup_observability

from models import (
    ActionableInsightsAgentResponse,
    ActionableInsight,
    GenerateInsightsEvent,
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


class CaptionExtractor(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "caption_extractor")

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[str]) -> None:
        try:
            data = json.loads(message)
            if isinstance(data, str):
                video_url = data
                custom_prompt = None
            else:
                video_url = data.get("video_url")
                custom_prompt = data.get("custom_prompt")
        except json.JSONDecodeError:
            video_url = message.strip()
            custom_prompt = None

        # Extract video ID from URL
        video_id = extract_video_id(video_url)

        if not video_id:
            error_payload = {"error": "Invalid URL."}
            await ctx.send_message(json.dumps(error_payload))
            return

        try:
            
            
            transcript = await asyncio.to_thread(fetch_transcript, video_id, ["end"])
            formatted_captions = convert_to_text_with_timestamps(transcript)

            payload = {
                "captions": formatted_captions, 
                "custom_prompt": custom_prompt
                }

            await ctx.send_message(json.dumps(payload))
        except Exception as e:
            logging.error(f"Error fetching transcript: {e}")
            error_payload = {"error": f"Failed to fetch transcript: {str(e)}"}
            await ctx.send_message(json.dumps(error_payload))


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
        self, message: str, ctx: WorkflowContext[Never, List[ActionableInsight]]
    ) -> None:
        try:
            data = json.loads(message)
            if isinstance(data, str):
                captions = data
                custom_prompt = None
            else:
                captions = data.get("captions")
                custom_prompt = data.get("custom_prompt")
        except json.JSONDecodeError:
            captions = message.strip()
            custom_prompt = None

        # Build the prompt based on whether custom prompt is provided
        if custom_prompt:
            prompt = f"{custom_prompt}\n\nYouTube video captions:\n{captions}"
        else:
            prompt = (
                "Analyze the following YouTube video transcript and extract the most significant actionable insights.\n"
                "Guidelines:\n"
                "- Focus on high-impact advice and key takeaways.\n"
                "- Avoid minor details, obscure examples, or redundant points.\n"
                "- Consolidate related ideas into a single strong insight.\n"
                "- Ensure each insight is clear, concise, and directly actionable for the viewer.\n"
                "- Maintain the chronological order of the insights as they appear in the video.\n\n"
                f"Transcript:\n{captions}"
            )

        agent_response = await self._actionable_insights_agent.run(prompt)

        if isinstance(agent_response.value, ActionableInsightsAgentResponse):
            insights_payload = agent_response.value
        else:
            logging.error(
                f"Unexpected agent response type: {type(agent_response.value)}"
            )
            empty_insights: List[ActionableInsight] = []
            await ctx.yield_output(empty_insights)
            return

        insights = insights_payload.insights
        logging.info(f"Extracted {len(insights)} insights")
        await ctx.add_event(GenerateInsightsEvent(insights_payload))
        await ctx.yield_output(insights)

       


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
