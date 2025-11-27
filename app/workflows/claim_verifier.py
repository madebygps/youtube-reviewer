"""Workflow for Phase 3: Verify claims (TODO)."""

from typing import Annotated

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
    ai_function,
)

from chat_client import chat_client
from constants import CLAIM_VERIFIER_INSTRUCTIONS
from models import ClaimVerifierResponse


@ai_function(approval_mode="always_require")
def verify_claim(location: Annotated[str, "The city and state, e.g. San Francisco, CA"]) -> str:
    """Get the current weather for a given location."""
    return f"The weather in {location} is cloudy with a high of 15°C."


class ClaimVerifier(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "claim_verifier")
        self._agent = chat_client.create_agent(
            instructions=CLAIM_VERIFIER_INSTRUCTIONS,
            response_format=ClaimVerifierResponse,
        )

    @handler
    async def handle(
        self, message: str, ctx: WorkflowContext[None, ClaimVerifierResponse]
    ) -> None:
        # TODO: Implement claim verification logic
        pass


def get_claim_verifier_workflow():
    """Workflow for Phase 3: Verify claims."""
    claim_verifier = ClaimVerifier()
    return (
        WorkflowBuilder()
        .set_start_executor(claim_verifier)
        .build()
    )


claim_verifier_workflow = get_claim_verifier_workflow()
