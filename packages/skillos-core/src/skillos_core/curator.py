from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from .changelog import Change, ChangeKind, Changelog
from .repo import Skill, SkillRepo
from .trace import Trace


class Curator(ABC):
    @abstractmethod
    async def curate(self, trace: Trace) -> Changelog: ...


class AsyncCurator(Curator):
    """In-process async curator that delegates analysis to a user-supplied
    callable and eagerly applies each change to the repo."""

    def __init__(
        self,
        repo: SkillRepo,
        *,
        analyze: Callable[[Trace], Awaitable[Changelog]],
    ) -> None:
        self._repo = repo
        self._analyze = analyze

    async def curate(self, trace: Trace) -> Changelog:
        changelog = await self._analyze(trace)
        for change in changelog.changes:
            try:
                self._apply_change(change)
                change.applied = True
            except Exception as e:
                change.applied = False
                change.error = str(e)
        return changelog

    def _apply_change(self, change: Change) -> Optional[Skill]:
        if change.kind is ChangeKind.INSERT:
            return self._repo.insert(
                change.name,
                change.description or "",
                change.body or "",
                **self._optional_kwargs(change),
            )
        if change.kind is ChangeKind.UPDATE:
            kwargs: dict[str, Any] = {}
            if change.description is not None:
                kwargs["description"] = change.description
            if change.body is not None:
                kwargs["body"] = change.body
            if change.license is not None:
                kwargs["license"] = change.license
            if change.allowed_tools is not None:
                kwargs["allowed_tools"] = change.allowed_tools
            if change.compatibility is not None:
                kwargs["compatibility"] = change.compatibility
            if change.metadata is not None:
                kwargs["metadata"] = change.metadata
            return self._repo.update(change.name, **kwargs)
        if change.kind is ChangeKind.DELETE:
            self._repo.delete(change.name)
            return None
        raise ValueError(f"unknown change kind: {change.kind!r}")

    def _optional_kwargs(self, change: Change) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if change.license is not None:
            kwargs["license"] = change.license
        if change.allowed_tools is not None:
            kwargs["allowed_tools"] = change.allowed_tools
        if change.compatibility is not None:
            kwargs["compatibility"] = change.compatibility
        if change.metadata is not None:
            kwargs["metadata"] = change.metadata
        return kwargs
