from __future__ import annotations

from abc import ABC, abstractmethod

from .changelog import Changelog
from .trace import Trace


class Curator(ABC):
    @abstractmethod
    async def curate(self, trace: Trace) -> Changelog: ...
