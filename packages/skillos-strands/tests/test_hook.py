from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from skillos_core import SkillRepo
from skillos_strands import StrandsCurator
from skillos_strands.curator import _CuratorHookProvider
from strands.hooks import AfterInvocationEvent
from strands.hooks.registry import HookRegistry


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


@pytest.fixture
def mock_model() -> MagicMock:
    return MagicMock()


def test_hook_returns_hook_provider(repo: SkillRepo, mock_model: MagicMock) -> None:
    curator = StrandsCurator(repo, model=mock_model)
    provider = curator.hook()
    assert isinstance(provider, _CuratorHookProvider)


def test_hook_provider_registers_after_invocation(repo: SkillRepo, mock_model: MagicMock) -> None:
    curator = StrandsCurator(repo, model=mock_model)
    provider = curator.hook()
    registry = HookRegistry()
    provider.register_hooks(registry)
    assert AfterInvocationEvent in registry._registered_callbacks
    assert len(registry._registered_callbacks[AfterInvocationEvent]) == 1


@pytest.mark.asyncio
async def test_hook_fires_after_agent_invocation(repo: SkillRepo, mock_model: MagicMock) -> None:
    curator = StrandsCurator(repo, model=mock_model)

    with patch.object(curator, "curate", new_callable=AsyncMock) as mock_curate:
        provider = curator.hook()
        event = MagicMock(spec=AfterInvocationEvent)
        event.agent = MagicMock()
        event.agent.messages = [
            {"role": "user", "content": "Create a greeting skill."},
            {"role": "assistant", "content": "Done."},
        ]

        registry = HookRegistry()
        provider.register_hooks(registry)
        callback = registry._registered_callbacks[AfterInvocationEvent][0]
        result = callback(event)
        if result is not None:
            await result

        mock_curate.assert_awaited_once_with(event.agent.messages)


@pytest.mark.asyncio
async def test_hook_skips_empty_messages(repo: SkillRepo, mock_model: MagicMock) -> None:
    curator = StrandsCurator(repo, model=mock_model)

    with patch.object(curator, "curate", new_callable=AsyncMock) as mock_curate:
        provider = curator.hook()
        event = MagicMock(spec=AfterInvocationEvent)
        event.agent = MagicMock()
        event.agent.messages = []

        registry = HookRegistry()
        provider.register_hooks(registry)
        callback = registry._registered_callbacks[AfterInvocationEvent][0]
        result = callback(event)
        if result is not None:
            await result

        mock_curate.assert_not_awaited()
