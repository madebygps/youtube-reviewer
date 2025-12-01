"""Workflow for Phase 4: Verify claims made in the video."""

import json
import logging
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

logger = logging.getLogger(__name__)


@ai_function(approval_mode="always_require")
def search_web(query: Annotated[str, "The search query to verify the claim"]) -> str:
    """Search the web to find evidence supporting or refuting a claim."""
    # This is a placeholder - in production, integrate with a real search API
    return f"Search results for: {query} - [Simulated search results would appear here]"


class ClaimVerifier(Executor):
    def __init__(self, id: str | None = None):
        super().__init__(id=id or "claim_verifier")
        self._agent = chat_client.create_agent(
            instructions=CLAIM_VERIFIER_INSTRUCTIONS,
            response_format=ClaimVerifierResponse,
            functions=[search_web],
        )

    @handler
    async def handle(
        self, message: str, ctx: WorkflowContext[None, ClaimVerifierResponse]
    ) -> None:
        data = json.loads(message)
        claims = data.get("claims", [])
        thesis = data.get("thesis", "")
        argument_chains = data.get("argument_chains", [])

        if not claims and not thesis and not argument_chains:
            logger.error("No claims, thesis, or argument chains provided for Phase 4")
            await ctx.yield_output(
                ClaimVerifierResponse(
                    verified_claims=[],
                    overall_credibility="Unable to assess",
                    summary="Error: No content provided for verification",
                    cautions=[],
                )
            )
            return

        # Build context for verification
        content_parts = []
        
        if thesis:
            content_parts.append(f"MAIN THESIS:\n{thesis}")
        
        if argument_chains:
            chains_text = "\n".join(
                f"- {chain.get('title', 'Unnamed')}: {chain.get('conclusion', '')}"
                for chain in argument_chains
            )
            content_parts.append(f"ARGUMENT CONCLUSIONS:\n{chains_text}")
        
        if claims:
            claims_text = "\n".join(f"- {claim}" for claim in claims)
            content_parts.append(f"SPECIFIC CLAIMS:\n{claims_text}")

        prompt = (
            "Analyze and verify the following claims from a video. "
            "Assess the credibility of each claim and provide an overall assessment.\n\n"
            f"{chr(10).join(content_parts)}\n\n"
            "For each verifiable claim, determine if it's supported, refuted, or unverifiable. "
            "Use the search tool if needed to find supporting or contradicting evidence."
        )

        response = await self._agent.run(prompt)

        if isinstance(response.value, ClaimVerifierResponse):
            logger.info(f"Verified {len(response.value.verified_claims)} claims")
            await ctx.yield_output(response.value)
        else:
            logger.error(f"Unexpected response type for Phase 4: {type(response.value)}")
            await ctx.yield_output(
                ClaimVerifierResponse(
                    verified_claims=[],
                    overall_credibility="Error",
                    summary="Error generating claim verification",
                    cautions=[],
                )
            )



def get_claim_verifier_workflow():
    """Workflow for Phase 4: Verify claims."""
    claim_verifier = ClaimVerifier()
    return (
        WorkflowBuilder()
        .set_start_executor(claim_verifier)
        .build()
    )


claim_verifier_workflow = get_claim_verifier_workflow()
