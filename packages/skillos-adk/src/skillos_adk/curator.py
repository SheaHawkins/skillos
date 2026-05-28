from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Union

from google.adk.agents import LlmAgent
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import InMemoryRunner
from google.genai import types
from skillos_core import Changelog, ConversationHistory, Curator, SkillRepo

from .tools import create_skill_tools

if TYPE_CHECKING:
    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.models.base_llm import BaseLlm

SYSTEM_PROMPT = """\
You are a skill curator for SkillOS. You receive conversation history from \
an agent's run and use your tools to manage a skill repository.

Analyze the conversation and determine what skills should be created, updated, \
or deleted. Use list_skills and read_skill to understand the current state, then \
insert_skill, update_skill, or delete_skill to make changes.

Rules for skills:
- name: lowercase alphanumeric with hyphens, max 64 chars.
- description: concise, max 1024 chars. Include what and when to use.
- body: markdown instructions for the agent.
- If no changes are warranted, do nothing.
"""

_APP_NAME = "skillos-adk-curator"
_USER_ID = "skillos-curator"


def _format_history(history: ConversationHistory) -> str:
    lines: list[str] = []
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if isinstance(content, str):
            if content:
                lines.append(f"[{role}] {content}")

        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if "text" in block:
                        lines.append(f"[{role}] {block['text']}")
                    elif "function_call" in block:
                        fc = block["function_call"]
                        lines.append(
                            f"[{role}] tool_call: {fc.get('name', '?')}"
                            f"({json.dumps(fc.get('args', {}), default=str)})"
                        )
                    elif "function_response" in block:
                        fr = block["function_response"]
                        lines.append(
                            f"[{role}] tool_result: "
                            f"{json.dumps(fr.get('response', ''), default=str)[:500]}"
                        )
                else:
                    lines.append(f"[{role}] {block}")

    return "\n".join(lines) if lines else "(empty conversation)"


def _events_to_history(events: list[Any]) -> ConversationHistory:
    """Convert ADK session events into a backend-agnostic ConversationHistory.

    Each ADK ``Event`` carries a ``types.Content`` with a role and a list of
    parts (text, function_call, function_response). This flattens those into
    the dict-of-blocks shape that :func:`_format_history` understands.
    """
    history: ConversationHistory = []
    for event in events:
        content = getattr(event, "content", None)
        if content is None:
            continue
        role = content.role or getattr(event, "author", None) or "unknown"
        blocks: list[dict[str, Any]] = []
        for part in content.parts or []:
            if getattr(part, "text", None):
                blocks.append({"text": part.text})
            elif getattr(part, "function_call", None):
                fc = part.function_call
                blocks.append({"function_call": {"name": fc.name, "args": dict(fc.args or {})}})
            elif getattr(part, "function_response", None):
                fr = part.function_response
                blocks.append({"function_response": {"name": fr.name, "response": fr.response}})
        if blocks:
            history.append({"role": role, "content": blocks})
    return history


class _CuratorPlugin(BasePlugin):
    """ADK plugin that runs the curator after each agent invocation.

    This is the ADK analogue of a Strands ``HookProvider``: a class that
    subscribes to runner lifecycle callbacks. ``after_run_callback`` fires
    once the runner finishes a full invocation, at which point the session's
    events are handed to the curator.
    """

    def __init__(self, curator: ADKCurator, *, name: str = "skillos_curator") -> None:
        super().__init__(name=name)
        self._curator = curator

    async def after_run_callback(self, *, invocation_context: InvocationContext) -> None:
        events = list(getattr(invocation_context.session, "events", []) or [])
        history = _events_to_history(events)
        if history:
            await self._curator.curate(history)


class ADKCurator(Curator):
    """Google ADK agent-based Curator that uses tools to mutate a SkillRepo.

    The curator builds an :class:`~google.adk.agents.LlmAgent` armed with skill
    tools, feeds it the formatted conversation history, and runs it via an
    in-memory runner. The agent reasons about what skills to create/update/delete
    and calls tools to make those changes; the :class:`Changelog` records what
    actually happened.
    """

    def __init__(
        self,
        repo: SkillRepo,
        *,
        model: Union[str, BaseLlm],
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self._repo = repo
        self._model = model
        self._system_prompt = system_prompt

    def plugin(self) -> BasePlugin:
        """Return a plugin for use in ``Runner(plugins=[curator.plugin()])``."""
        return _CuratorPlugin(self)

    async def curate(self, history: ConversationHistory) -> Changelog:
        changelog = Changelog()
        tools = create_skill_tools(self._repo, changelog=changelog)
        agent = LlmAgent(
            name="skill_curator",
            model=self._model,
            instruction=self._system_prompt,
            tools=list(tools),
        )
        runner = InMemoryRunner(agent=agent, app_name=_APP_NAME)
        session = await runner.session_service.create_session(app_name=_APP_NAME, user_id=_USER_ID)
        message = types.Content(role="user", parts=[types.Part(text=_format_history(history))])
        async for _ in runner.run_async(
            user_id=_USER_ID, session_id=session.id, new_message=message
        ):
            pass
        return changelog
