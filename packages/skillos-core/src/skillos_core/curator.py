from __future__ import annotations

from abc import ABC, abstractmethod

from .changelog import Changelog
from .conversation import ConversationHistory


class Curator(ABC):
    @abstractmethod
    async def curate(self, history: ConversationHistory) -> Changelog: ...
