from __future__ import annotations

from typing import Any, Optional

from skillos_core import Change, ChangeKind, Changelog, Curator, SkillRepo, Trace
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.decorator import DecoratedFunctionTool

DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-6-20250514-v1:0"

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


def _make_recording_tools(repo: SkillRepo, changelog: Changelog) -> list[DecoratedFunctionTool]:
    @tool
    def list_skills() -> list[str]:
        """List all skill names in the repository."""
        return repo.list_skills()

    @tool
    def read_skill(name: str) -> dict[str, Any]:
        """Read a skill's metadata and body by name."""
        skill = repo.read(name)
        return {
            "name": skill.name,
            "description": skill.description,
            "body": skill.body,
            "metadata": skill.metadata,
        }

    @tool
    def insert_skill(
        name: str,
        description: str,
        body: str,
        license: str = "MIT",
        allowed_tools: Optional[list[str]] = None,
        compatibility: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Insert a new skill into the repository.

        name must be lowercase alphanumeric with hyphens, max 64 chars.
        description max 1024 chars. body is markdown. license must be a valid SPDX identifier.
        """
        change = Change(
            kind=ChangeKind.INSERT,
            name=name,
            description=description,
            body=body,
            license=license,
            allowed_tools=allowed_tools,
            compatibility=compatibility,
            metadata=metadata,
        )
        try:
            kwargs: dict[str, Any] = {"license": license}
            if allowed_tools is not None:
                kwargs["allowed_tools"] = allowed_tools
            if compatibility is not None:
                kwargs["compatibility"] = compatibility
            if metadata is not None:
                kwargs["metadata"] = metadata
            repo.insert(name, description, body, **kwargs)
            change.applied = True
        except Exception as e:
            change.applied = False
            change.error = str(e)
        changelog.changes.append(change)
        return {"name": name, "applied": change.applied, "error": change.error}

    @tool
    def update_skill(
        name: str,
        description: Optional[str] = None,
        body: Optional[str] = None,
        license: Optional[str] = None,
        allowed_tools: Optional[list[str]] = None,
        compatibility: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Update an existing skill's body and/or frontmatter fields.

        Only supply the fields you want to change; omitted fields are left as-is.
        """
        change = Change(
            kind=ChangeKind.UPDATE,
            name=name,
            description=description,
            body=body,
            license=license,
            allowed_tools=allowed_tools,
            compatibility=compatibility,
            metadata=metadata,
        )
        try:
            kwargs: dict[str, Any] = {}
            if description is not None:
                kwargs["description"] = description
            if body is not None:
                kwargs["body"] = body
            if license is not None:
                kwargs["license"] = license
            if allowed_tools is not None:
                kwargs["allowed_tools"] = allowed_tools
            if compatibility is not None:
                kwargs["compatibility"] = compatibility
            if metadata is not None:
                kwargs["metadata"] = metadata
            repo.update(name, **kwargs)
            change.applied = True
        except Exception as e:
            change.applied = False
            change.error = str(e)
        changelog.changes.append(change)
        return {"name": name, "applied": change.applied, "error": change.error}

    @tool
    def delete_skill(name: str) -> dict[str, Any]:
        """Delete a skill and all its bundled resources."""
        change = Change(kind=ChangeKind.DELETE, name=name)
        try:
            repo.delete(name)
            change.applied = True
        except Exception as e:
            change.applied = False
            change.error = str(e)
        changelog.changes.append(change)
        return {"name": name, "applied": change.applied, "error": change.error}

    return [list_skills, read_skill, insert_skill, update_skill, delete_skill]


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
        model_id: str = DEFAULT_MODEL_ID,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self._repo = repo
        self._model_id = model_id
        self._system_prompt = system_prompt

    async def curate(self, trace: Trace) -> Changelog:
        changelog = Changelog()
        tools: list[Any] = _make_recording_tools(self._repo, changelog)
        model = BedrockModel(model_id=self._model_id)
        agent = Agent(model=model, tools=tools, system_prompt=self._system_prompt)
        prompt = _format_trace(trace)
        await agent.invoke_async(prompt)
        return changelog
