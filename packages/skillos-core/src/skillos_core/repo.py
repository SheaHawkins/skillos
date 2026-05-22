from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import fsspec
import yaml

SKILL_FILE = "SKILL.md"

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


@dataclass
class Skill:
    name: str
    metadata: dict[str, Any]
    body: str
    fs: fsspec.AbstractFileSystem = field(repr=False)
    root: str = field(repr=False)

    @property
    def description(self) -> str:
        return self.metadata.get("description", "")

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
    """A read-only repository of skills backed by any fsspec filesystem.

    The repo URL selects the backend by protocol — local paths, ``s3://``,
    ``gs://``, ``az://``, ``memory://``, etc. A skill is any immediate
    subdirectory containing a ``SKILL.md`` file.
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
