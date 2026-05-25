from __future__ import annotations

from collections.abc import Awaitable, Callable

from skillos_core import SYSTEM_PROMPT, Changelog, Trace
from skillos_core.analysis import format_trace_prompt, parse_changelog
from strands import Agent
from strands.models import BedrockModel

AnalyzeFn = Callable[[Trace], Awaitable[Changelog]]

DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-6-20250514-v1:0"


def create_strands_analyzer(
    *,
    model_id: str = DEFAULT_MODEL_ID,
    system_prompt: str = SYSTEM_PROMPT,
) -> AnalyzeFn:
    """Create an analyze callable backed by Strands Agents + Amazon Bedrock.

    Returns a function suitable for passing to ``AsyncCurator(analyze=...)``.
    """
    model = BedrockModel(model_id=model_id)
    agent = Agent(model=model, system_prompt=system_prompt)

    async def analyze(trace: Trace) -> Changelog:
        prompt = format_trace_prompt(trace)
        result = await agent.invoke_async(prompt)
        return parse_changelog(str(result))

    return analyze
