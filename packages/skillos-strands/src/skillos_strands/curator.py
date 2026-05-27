from __future__ import annotations

import json
from typing import Any

from skillos_core import Changelog, ConversationHistory, Curator, SkillRepo
from strands import Agent
from strands.models import Model

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


def _format_history(history: ConversationHistory) -> str:
    lines: list[str] = []
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if isinstance(content, str):
            lines.append(f"[{role}] {content}")

        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if "text" in block:
                        lines.append(f"[{role}] {block['text']}")
                    elif "toolUse" in block:
                        tu = block["toolUse"]
                        lines.append(
                            f"[{role}] tool_call: {tu.get('name', '?')}"
                            f"({json.dumps(tu.get('input', {}), default=str)})"
                        )
                    elif "toolResult" in block:
                        tr = block["toolResult"]
                        result_parts = tr.get("content", [])
                        text = " ".join(
                            p.get("text", "") for p in result_parts if isinstance(p, dict)
                        )
                        lines.append(f"[{role}] tool_result: {text[:500]}")
                    elif "tool_calls" in block:
                        for tc in block.get("tool_calls", []):
                            fn = tc.get("function", {})
                            lines.append(
                                f"[{role}] tool_call: {fn.get('name', '?')}"
                                f"({fn.get('arguments', '')})"
                            )
                else:
                    lines.append(f"[{role}] {block}")

        if "tool_calls" in msg:
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                lines.append(
                    f"[{role}] tool_call: {fn.get('name', '?')}({fn.get('arguments', '')})"
                )

    return "\n".join(lines) if lines else "(empty conversation)"


class StrandsCurator(Curator):
    """Strands Agent-based Curator that uses tools to mutate a SkillRepo.

    The Agent receives formatted conversation history, reasons about what
    skills to create/update/delete, and calls tools to make those changes.
    The Changelog records what actually happened.
    """

    def __init__(
        self,
        repo: SkillRepo,
        *,
        model: Model,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self._repo = repo
        self._model = model
        self._system_prompt = system_prompt

    async def curate(self, history: ConversationHistory) -> Changelog:
        changelog = Changelog()
        tools: list[Any] = create_skill_tools(self._repo, changelog=changelog)
        agent = Agent(model=self._model, tools=tools, system_prompt=self._system_prompt)
        prompt = _format_history(history)
        await agent.invoke_async(prompt)
        return changelog
