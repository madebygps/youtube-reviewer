"""Workflow for Phase 3: Find connections between key concepts."""

import json
import logging

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

from chat_client import chat_client
from constants import CONNECTIONS_INSTRUCTIONS
from models import ConnectionsResponse

logger = logging.getLogger(__name__)


class ConnectionsExtractor(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "connections_extractor")
        self._agent = chat_client.create_agent(
            instructions=CONNECTIONS_INSTRUCTIONS,
            response_format=ConnectionsResponse,
        )

    @handler
    async def handle(
        self, message: str, ctx: WorkflowContext[None, ConnectionsResponse]
    ) -> None:
        data = json.loads(message)
        key_concepts = data.get("key_concepts", [])

        if not key_concepts:
            logger.error("No key concepts provided for Phase 3")
            await ctx.yield_output(
                ConnectionsResponse(
                    connections=[],
                    synthesis="Error: No key concepts provided",
                )
            )
            return

        # Format concepts for the prompt
        concepts_text = "\n".join(
            f"- {c['term']}: {c['definition']}" for c in key_concepts
        )

        prompt = (
            "Find meaningful connections between these key concepts from a video:\n\n"
            f"{concepts_text}\n\n"
            "Identify relationships and provide a synthesis of how they work together."
        )

        response = await self._agent.run(prompt)

        if isinstance(response.value, ConnectionsResponse):
            logger.info(f"Found {len(response.value.connections)} connections")
            await ctx.yield_output(response.value)
        else:
            logger.error(f"Unexpected response type for Phase 3: {type(response.value)}")
            await ctx.yield_output(
                ConnectionsResponse(
                    connections=[],
                    synthesis="Error generating connections",
                )
            )


def get_connections_workflow():
    """Workflow for Phase 3: Find connections between concepts."""
    connections_extractor = ConnectionsExtractor()
    return (
        WorkflowBuilder()
        .set_start_executor(connections_extractor)
        .build()
    )


connections_workflow = get_connections_workflow()
