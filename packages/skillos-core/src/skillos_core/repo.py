from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

import fsspec
import yaml

SKILL_FILE = "SKILL.md"

# Frontmatter spec (per the SKILL.md / Agent Skills format):
#   name:        ≤64 chars, lowercase letters, digits, hyphens; reserved
#                words "anthropic" and "claude" are not allowed.
#   description: 1–1024 chars, non-empty.
# Recognized optional fields: license, allowed-tools, compatibility, metadata.
# https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
NAME_MAX_LEN = 64
DESCRIPTION_MAX_LEN = 1024
RESERVED_NAMES = frozenset({"anthropic", "claude"})
_NAME_RE = re.compile(r"^[a-z0-9-]+$")


class License(str, Enum):
    """SPDX identifiers for the ten most common open-source licenses.

    Used as the default vocabulary for the SKILL.md ``license`` frontmatter
    field. Accepts string coercion (``License("MIT")``) so callers can pass
    plain SPDX strings interchangeably.
    """

    MIT = "MIT"
    APACHE_2_0 = "Apache-2.0"
    GPL_3_0 = "GPL-3.0"
    BSD_3_CLAUSE = "BSD-3-Clause"
    GPL_2_0 = "GPL-2.0"
    BSD_2_CLAUSE = "BSD-2-Clause"
    LGPL_3_0 = "LGPL-3.0"
    MPL_2_0 = "MPL-2.0"
    AGPL_3_0 = "AGPL-3.0"
    UNLICENSE = "Unlicense"


LicenseLike = Union[License, str]

_FRONTMATTER_SPLIT = re.compile(r"^---\s*$", re.MULTILINE)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.lstrip().startswith("---"):
        return {}, text
    parts = _FRONTMATTER_SPLIT.split(text, maxsplit=2)
    if len(parts) < 3:
        return {}, text
    _, front_text, body = parts
    metadata = yaml.safe_load(front_text) or {}
    if not isinstance(metadata, dict):
        return {}, text
    return metadata, body.lstrip("\n")


def _validate_name(name: str) -> None:
    if not name:
        raise ValueError("skill name must be non-empty")
    if len(name) > NAME_MAX_LEN:
        raise ValueError(f"skill name must be at most {NAME_MAX_LEN} characters")
    if not _NAME_RE.fullmatch(name):
        raise ValueError("skill name must contain only lowercase letters, digits, and hyphens")
    if name in RESERVED_NAMES:
        raise ValueError(f"skill name {name!r} is reserved")


def _validate_description(description: Any) -> None:
    if not isinstance(description, str) or not description.strip():
        raise ValueError("description is required and must be a non-empty string")
    if len(description) > DESCRIPTION_MAX_LEN:
        raise ValueError(f"description must be at most {DESCRIPTION_MAX_LEN} characters")


def _serialize_skill(metadata: dict[str, Any], body: str) -> str:
    front = yaml.safe_dump(metadata, sort_keys=False).strip()
    body_text = body if body.endswith("\n") else body + "\n"
    return f"---\n{front}\n---\n\n{body_text}"


@dataclass
class Skill:
    name: str
    metadata: dict[str, Any]
    body: str
    fs: fsspec.AbstractFileSystem = field(repr=False)
    root: str = field(repr=False)

    @property
    def description(self) -> Optional[str]:
        return self.metadata.get("description")

    def list_resources(self) -> list[str]:
        prefix = self.root.rstrip("/") + "/"
        paths = self.fs.find(self.root, withdirs=False)
        out = []
        for p in paths:
            rel = p[len(prefix) :] if p.startswith(prefix) else p
            if rel == SKILL_FILE or not rel:
                continue
            out.append(rel)
        return sorted(out)

    def read_resource(self, path: str) -> bytes:
        with self.fs.open(f"{self.root.rstrip('/')}/{path}", "rb") as f:
            return f.read()


class SkillRepo:
    """A repository of skills backed by any fsspec filesystem.

    The repo URL selects the backend by protocol — local paths, ``s3://``,
    ``gs://``, ``az://``, ``memory://``, etc. A skill is any immediate
    subdirectory containing a ``SKILL.md`` file.

    Skills can be enumerated and read via :meth:`list_skills`, :meth:`read`,
    and iteration, and mutated via :meth:`insert`, :meth:`update`, and
    :meth:`delete`. Write operations validate ``name`` and ``description``
    against the SKILL.md frontmatter spec.
    """

    def __init__(self, url: str, **storage_options: Any) -> None:
        self.url = url
        self.fs, self.root = fsspec.url_to_fs(url, **storage_options)
        self.root = self.root.rstrip("/")

    def list_skills(self) -> list[str]:
        pattern = f"{self.root}/*/{SKILL_FILE}"
        names = []
        for match in self.fs.glob(pattern):
            parts = match.rstrip("/").split("/")
            if len(parts) >= 2:
                names.append(parts[-2])
        return sorted(set(names))

    def read(self, name: str) -> Skill:
        skill_root = f"{self.root}/{name}"
        skill_md = f"{skill_root}/{SKILL_FILE}"
        if not self.fs.exists(skill_md):
            raise FileNotFoundError(f"No skill named {name!r} at {skill_md}")
        with self.fs.open(skill_md, "r") as f:
            content = f.read()
        metadata, body = _parse_frontmatter(content)
        return Skill(
            name=name,
            metadata=metadata,
            body=body,
            fs=self.fs,
            root=skill_root,
        )

    def __iter__(self) -> Iterator[Skill]:
        for name in self.list_skills():
            yield self.read(name)

    def __contains__(self, name: str) -> bool:
        return self.fs.exists(f"{self.root}/{name}/{SKILL_FILE}")

    def insert(
        self,
        name: str,
        description: str,
        body: str,
        *,
        license: LicenseLike = License.MIT,
        allowed_tools: Optional[list[str]] = None,
        compatibility: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Skill:
        """Create a new skill named ``name``.

        Each keyword argument maps to a SKILL.md frontmatter field:
        ``license`` (SPDX, default MIT, validated against :class:`License`),
        ``allowed_tools`` (serialized as ``allowed-tools``),
        ``compatibility``, and ``metadata`` (the spec's nested metadata
        dict for things like version). ``body`` is the free-form markdown
        body and is not validated. Raises :class:`FileExistsError` if a
        skill with this name already exists.
        """
        _validate_name(name)
        _validate_description(description)
        if name in self:
            raise FileExistsError(f"Skill {name!r} already exists")
        front: dict[str, Any] = {
            "name": name,
            "description": description,
            "license": License(license).value,
        }
        if allowed_tools is not None:
            front["allowed-tools"] = list(allowed_tools)
        if compatibility is not None:
            front["compatibility"] = compatibility
        if metadata is not None:
            front["metadata"] = dict(metadata)
        return self._write(name, body, front)

    def update(
        self,
        name: str,
        *,
        body: Optional[str] = None,
        description: Optional[str] = None,
        license: Optional[LicenseLike] = None,
        allowed_tools: Optional[list[str]] = None,
        compatibility: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Skill:
        """Partial update of an existing skill. Each keyword argument
        corresponds to a frontmatter field; ``None`` means leave the
        existing value unchanged. The skill's ``name`` always tracks the
        directory and cannot be changed here. Raises
        :class:`FileNotFoundError` if the skill does not exist.
        """
        existing = self.read(name)
        new_body = existing.body if body is None else body
        front: dict[str, Any] = dict(existing.metadata)
        front["name"] = name
        if description is not None:
            front["description"] = description
        if license is not None:
            front["license"] = License(license).value
        if allowed_tools is not None:
            front["allowed-tools"] = list(allowed_tools)
        if compatibility is not None:
            front["compatibility"] = compatibility
        if metadata is not None:
            front["metadata"] = dict(metadata)
        _validate_description(front.get("description"))
        return self._write(name, new_body, front)

    def delete(self, name: str) -> None:
        """Remove a skill and all its bundled resources."""
        skill_root = f"{self.root}/{name}"
        if not self.fs.exists(f"{skill_root}/{SKILL_FILE}"):
            raise FileNotFoundError(f"No skill named {name!r}")
        self.fs.rm(skill_root, recursive=True)

    def _write(self, name: str, body: str, metadata: dict[str, Any]) -> Skill:
        skill_root = f"{self.root}/{name}"
        self.fs.makedirs(skill_root, exist_ok=True)
        with self.fs.open(f"{skill_root}/{SKILL_FILE}", "w") as f:
            f.write(_serialize_skill(metadata, body))
        return self.read(name)
