"""Workflow for Phase 5: Generate quiz to test user understanding."""

import json
import logging

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

from chat_client import chat_client
from constants import QUIZ_GENERATOR_INSTRUCTIONS
from models import QuizResponse

logger = logging.getLogger(__name__)


class QuizGenerator(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "quiz_generator")
        self._agent = chat_client.create_agent(
            instructions=QUIZ_GENERATOR_INSTRUCTIONS,
            response_format=QuizResponse,
        )

    @handler
    async def handle(
        self, message: str, ctx: WorkflowContext[None, QuizResponse]
    ) -> None:
        data = json.loads(message)
        key_concepts = data.get("key_concepts", [])
        thesis = data.get("thesis", "")
        argument_chains = data.get("argument_chains", [])
        connections = data.get("connections", [])

        if not key_concepts and not thesis:
            logger.error("No content provided for Phase 5")
            await ctx.yield_output(
                QuizResponse(
                    questions=[],
                    quiz_focus="Error: No content provided",
                )
            )
            return

        # Build comprehensive context for quiz generation
        content_parts = []

        if key_concepts:
            concepts_text = "\n".join(
                f"- {c.get('term', 'Unknown')}: {c.get('definition', '')}"
                for c in key_concepts
            )
            content_parts.append(f"KEY CONCEPTS:\n{concepts_text}")

        if thesis:
            content_parts.append(f"MAIN THESIS:\n{thesis}")

        if argument_chains:
            chains_text = "\n".join(
                f"- {chain.get('title', 'Unnamed')}: {chain.get('conclusion', '')}"
                for chain in argument_chains
            )
            content_parts.append(f"ARGUMENT CONCLUSIONS:\n{chains_text}")

        if connections:
            connections_text = "\n".join(
                f"- {conn.get('concept_a', '')} ↔ {conn.get('concept_b', '')}: {conn.get('relationship', '')}"
                for conn in connections
            )
            content_parts.append(f"CONCEPT CONNECTIONS:\n{connections_text}")

        prompt = (
            "Generate a comprehensive quiz to test understanding of this video content:\n\n"
            f"{chr(10).join(content_parts)}\n\n"
            "Create questions that test recall, understanding, and application of these concepts."
        )

        response = await self._agent.run(prompt)

        if isinstance(response.value, QuizResponse):
            logger.info(f"Generated {len(response.value.questions)} quiz questions")
            await ctx.yield_output(response.value)
        else:
            logger.error(f"Unexpected response type for Phase 5: {type(response.value)}")
            await ctx.yield_output(
                QuizResponse(
                    questions=[],
                    quiz_focus="Error generating quiz",
                )
            )


def get_quiz_generator_workflow():
    """Workflow for Phase 5: Generate comprehension quiz."""
    quiz_generator = QuizGenerator()
    return (
        WorkflowBuilder()
        .set_start_executor(quiz_generator)
        .build()
    )


quiz_generator_workflow = get_quiz_generator_workflow()
