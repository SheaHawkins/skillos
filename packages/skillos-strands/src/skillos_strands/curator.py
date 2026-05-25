from __future__ import annotations

from typing import Any

from skillos_core import Changelog, Curator, SkillRepo, Trace
from strands import Agent
from strands.models import Model

from .tools import create_skill_tools

SYSTEM_PROMPT = """\
You are a skill curator for SkillOS. You receive traces of agent execution \
and use your tools to manage a skill repository.

Analyze the trace and determine what skills should be created, updated, or \
deleted. Use list_skills and read_skill to understand the current state, then \
insert_skill, update_skill, or delete_skill to make changes.

Rules for skills:
- name: lowercase alphanumeric with hyphens, max 64 chars.
- description: concise, max 1024 chars. Include what and when to use.
- body: markdown instructions for the agent.
- If no changes are warranted, do nothing.
"""


def _format_trace(trace: Trace) -> str:
    lines = [f"Trace {trace.trace_id}", ""]
    for span in trace.spans:
        name = span.name if hasattr(span, "name") else str(span)
        attrs = dict(span.attributes) if hasattr(span, "attributes") and span.attributes else {}
        line = f"- [{name}]"
        if attrs:
            attr_str = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
            line += f" {{{attr_str}}}"
        lines.append(line)
    if len(lines) == 2:
        lines.append("(empty trace)")
    return "\n".join(lines)


class StrandsCurator(Curator):
    """Strands Agent-based Curator that uses tools to mutate a SkillRepo.

    The Agent receives a formatted trace, reasons about what skills to
    create/update/delete, and calls tools to make those changes. The
    Changelog records what actually happened.
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

    async def curate(self, trace: Trace) -> Changelog:
        changelog = Changelog()
        tools: list[Any] = create_skill_tools(self._repo, changelog=changelog)
        agent = Agent(model=self._model, tools=tools, system_prompt=self._system_prompt)
        prompt = _format_trace(trace)
        await agent.invoke_async(prompt)
        return changelog
