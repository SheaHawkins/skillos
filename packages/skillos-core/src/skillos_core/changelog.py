from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

from .repo import License


class ChangeKind(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class Change:
    kind: ChangeKind
    name: str
    applied: bool = False
    error: Optional[str] = None
    description: Optional[str] = None
    body: Optional[str] = None
    license: Optional[Union[License, str]] = None
    allowed_tools: Optional[list[str]] = None
    compatibility: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass
class Changelog:
    changes: list[Change] = field(default_factory=list)

    @property
    def applied(self) -> list[Change]:
        return [c for c in self.changes if c.applied]

    @property
    def failed(self) -> list[Change]:
        return [c for c in self.changes if not c.applied]
