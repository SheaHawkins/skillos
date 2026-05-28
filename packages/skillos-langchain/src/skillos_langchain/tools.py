from __future__ import annotations

from typing import Any, Optional

from langchain_core.tools import BaseTool, tool
from skillos_core import Change, ChangeKind, Changelog, SkillRepo


def create_skill_tools(repo: SkillRepo, *, changelog: Optional[Changelog] = None) -> list[BaseTool]:
    """Create LangChain tools for interacting with a SkillRepo.

    Returns a list of tools suitable for passing to ``create_agent(model, tools)``.
    When ``changelog`` is provided, insert/update/delete operations also
    record each mutation as a :class:`Change` with ``applied`` status.
    """

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
            "resources": skill.list_resources(),
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
        kwargs: dict[str, Any] = {"license": license}
        if allowed_tools is not None:
            kwargs["allowed_tools"] = allowed_tools
        if compatibility is not None:
            kwargs["compatibility"] = compatibility
        if metadata is not None:
            kwargs["metadata"] = metadata

        change = (
            Change(
                kind=ChangeKind.INSERT,
                name=name,
                description=description,
                body=body,
                license=license,
                allowed_tools=allowed_tools,
                compatibility=compatibility,
                metadata=metadata,
            )
            if changelog is not None
            else None
        )
        try:
            repo.insert(name, description, body, **kwargs)
            if change:
                change.applied = True
        except Exception as e:
            if change:
                change.applied = False
                change.error = str(e)
            raise
        finally:
            if change and changelog is not None:
                changelog.changes.append(change)

        return {"name": name, "applied": True, "error": None}

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

        change = (
            Change(
                kind=ChangeKind.UPDATE,
                name=name,
                description=description,
                body=body,
                license=license,
                allowed_tools=allowed_tools,
                compatibility=compatibility,
                metadata=metadata,
            )
            if changelog is not None
            else None
        )
        try:
            repo.update(name, **kwargs)
            if change:
                change.applied = True
        except Exception as e:
            if change:
                change.applied = False
                change.error = str(e)
            raise
        finally:
            if change and changelog is not None:
                changelog.changes.append(change)

        return {"name": name, "applied": True, "error": None}

    @tool
    def delete_skill(name: str) -> dict[str, Any]:
        """Delete a skill and all its bundled resources."""
        change = Change(kind=ChangeKind.DELETE, name=name) if changelog is not None else None
        try:
            repo.delete(name)
            if change:
                change.applied = True
        except Exception as e:
            if change:
                change.applied = False
                change.error = str(e)
            raise
        finally:
            if change and changelog is not None:
                changelog.changes.append(change)

        return {"name": name, "applied": True, "error": None}

    return [list_skills, read_skill, insert_skill, update_skill, delete_skill]
