from __future__ import annotations

from typing import Any, Optional

from skillos_core import SkillRepo
from strands import tool
from strands.tools.decorator import DecoratedFunctionTool


def create_skill_tools(repo: SkillRepo) -> list[DecoratedFunctionTool]:
    """Create Strands tools for interacting with a SkillRepo.

    Returns a list of tools suitable for passing to ``Agent(tools=...)``.
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
        description max 1024 chars. license must be a valid SPDX identifier.
        """
        kwargs: dict[str, Any] = {"license": license}
        if allowed_tools is not None:
            kwargs["allowed_tools"] = allowed_tools
        if compatibility is not None:
            kwargs["compatibility"] = compatibility
        if metadata is not None:
            kwargs["metadata"] = metadata
        skill = repo.insert(name, description, body, **kwargs)
        return {"name": skill.name, "description": skill.description}

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
        skill = repo.update(name, **kwargs)
        return {"name": skill.name, "description": skill.description}

    @tool
    def delete_skill(name: str) -> dict[str, str]:
        """Delete a skill and all its bundled resources."""
        repo.delete(name)
        return {"deleted": name}

    return [list_skills, read_skill, insert_skill, update_skill, delete_skill]
