"""Workflow for Phase 2: Extract thesis and argument chains from captions."""

import json
import logging

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

from chat_client import chat_client
from constants import THESIS_ARGUMENT_INSTRUCTIONS
from models import ThesisArgumentResponse
from utilities import get_cached_captions


class ThesisArgumentExtractor(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "thesis_argument_extractor")
        self._agent = chat_client.create_agent(
            instructions=THESIS_ARGUMENT_INSTRUCTIONS,
            response_format=ThesisArgumentResponse,
        )

    @handler
    async def handle(
        self, message: str, ctx: WorkflowContext[None, ThesisArgumentResponse]
    ) -> None:
        data = json.loads(message)
        video_id = data["video_id"]

        captions = get_cached_captions(video_id)
        if captions is None:
            logging.error(f"No cached captions found for video {video_id}")
            await ctx.yield_output(
                ThesisArgumentResponse(
                    main_thesis="Error: captions not found in cache",
                    argument_chains=[],
                )
            )
            return

        prompt = (
            "Extract the main thesis and all argument chains from the following YouTube video transcript.\n\n"
            "Provide:\n"
            "- main_thesis (1-2 sentences)\n"
            "- argument_chains: for each chain include title, premise, reasoning_steps, conclusion, implications\n\n"
            f"Transcript:\n{captions}"
        )
        response = await self._agent.run(prompt)

        if isinstance(response.value, ThesisArgumentResponse):
            await ctx.yield_output(response.value)
        else:
            logging.error(f"Unexpected response type for Phase 2: {type(response.value)}")
            await ctx.yield_output(ThesisArgumentResponse(main_thesis="Error generating thesis", argument_chains=[]))


def get_thesis_argument_workflow():
    """Workflow for Phase 2: Extract thesis and argument chains from captions."""
    thesis_argument_extractor = ThesisArgumentExtractor()
    return (
        WorkflowBuilder()
        .set_start_executor(thesis_argument_extractor)
        .build()
    )


thesis_argument_workflow = get_thesis_argument_workflow()
