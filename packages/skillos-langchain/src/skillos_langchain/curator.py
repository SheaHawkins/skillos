from __future__ import annotations

import json
from typing import Any, Optional
from uuid import UUID

from langchain.agents import create_agent
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from skillos_core import Changelog, ConversationHistory, Curator, SkillRepo

from .tools import create_skill_tools

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

# LangChain message types map to the role labels used in the formatted history.
_ROLE_BY_TYPE = {
    "human": "user",
    "ai": "assistant",
    "system": "system",
    "tool": "tool",
}


def _format_base_message(msg: BaseMessage) -> list[str]:
    role = _ROLE_BY_TYPE.get(msg.type, msg.type)
    lines: list[str] = []

    if msg.type == "tool":
        text = msg.content if isinstance(msg.content, str) else json.dumps(msg.content, default=str)
        lines.append(f"[{role}] tool_result: {text[:500]}")
        return lines

    content = msg.content
    if isinstance(content, str):
        if content:
            lines.append(f"[{role}] {content}")
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and "text" in block:
                lines.append(f"[{role}] {block['text']}")
            else:
                lines.append(f"[{role}] {block}")

    for tc in getattr(msg, "tool_calls", None) or []:
        name = tc.get("name", "?")
        args = tc.get("args", {})
        lines.append(f"[{role}] tool_call: {name}({json.dumps(args, default=str)})")

    return lines


def _format_dict_message(msg: dict[str, Any]) -> list[str]:
    role = msg.get("role", "unknown")
    content = msg.get("content", "")
    lines: list[str] = []

    if isinstance(content, str):
        if content:
            lines.append(f"[{role}] {content}")
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and "text" in block:
                lines.append(f"[{role}] {block['text']}")
            else:
                lines.append(f"[{role}] {block}")

    for tc in msg.get("tool_calls", []) or []:
        fn = tc.get("function", {})
        lines.append(f"[{role}] tool_call: {fn.get('name', '?')}({fn.get('arguments', '')})")

    return lines


def _format_history(history: ConversationHistory) -> str:
    lines: list[str] = []
    for msg in history:
        if isinstance(msg, BaseMessage):
            lines.extend(_format_base_message(msg))
        elif isinstance(msg, dict):
            lines.extend(_format_dict_message(msg))
        else:
            lines.append(f"[unknown] {msg}")

    return "\n".join(lines) if lines else "(empty conversation)"


class _CuratorCallbackHandler(AsyncCallbackHandler):
    """LangChain callback that curates skills after an agent run finishes.

    This is the LangChain analogue of a Strands ``HookProvider``: it hooks
    into the agent lifecycle and fires once, when the root run completes,
    handing the resulting conversation to the curator.
    """

    def __init__(self, curator: LangChainCurator) -> None:
        self._curator = curator

    async def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        # Only act on the root run; nested chains have a parent.
        if parent_run_id is not None:
            return
        messages = outputs.get("messages") if isinstance(outputs, dict) else None
        if messages:
            await self._curator.curate(messages)


class LangChainCurator(Curator):
    """LangChain agent-based Curator that uses tools to mutate a SkillRepo.

    The agent receives formatted conversation history, reasons about what
    skills to create/update/delete, and calls tools to make those changes.
    The Changelog records what actually happened.
    """

    def __init__(
        self,
        repo: SkillRepo,
        *,
        model: BaseChatModel,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self._repo = repo
        self._model = model
        self._system_prompt = system_prompt

    def callback(self) -> AsyncCallbackHandler:
        """Return a callback handler for use in ``config={"callbacks": [curator.callback()]}``.

        This is the LangChain equivalent of a Strands hook provider.
        """
        return _CuratorCallbackHandler(self)

    async def curate(self, history: ConversationHistory) -> Changelog:
        changelog = Changelog()
        tools = create_skill_tools(self._repo, changelog=changelog)
        agent = create_agent(self._model, tools, system_prompt=self._system_prompt)
        prompt = _format_history(history)
        await agent.ainvoke({"messages": [("user", prompt)]})
        return changelog
