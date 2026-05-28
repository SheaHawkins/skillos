from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from google.adk.agents.invocation_context import InvocationContext
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types
from skillos_adk import ADKCurator
from skillos_adk.curator import _CuratorPlugin
from skillos_core import SkillRepo


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


@pytest.fixture
def mock_model() -> str:
    return "gemini-2.0-flash"


def _event(role: str, parts: list[types.Part]) -> SimpleNamespace:
    return SimpleNamespace(content=types.Content(role=role, parts=parts), author=role)


def _context(events: list) -> InvocationContext:
    # A SimpleNamespace stands in for the InvocationContext: the plugin only
    # touches ``.session.events``.
    return cast(InvocationContext, SimpleNamespace(session=SimpleNamespace(events=events)))


def test_plugin_returns_base_plugin(repo: SkillRepo, mock_model: str) -> None:
    curator = ADKCurator(repo, model=mock_model)
    plugin = curator.plugin()
    assert isinstance(plugin, _CuratorPlugin)
    assert isinstance(plugin, BasePlugin)


@pytest.mark.asyncio
async def test_plugin_fires_after_run(repo: SkillRepo, mock_model: str) -> None:
    curator = ADKCurator(repo, model=mock_model)

    with patch.object(curator, "curate", new_callable=AsyncMock) as mock_curate:
        plugin = curator.plugin()
        ctx = _context(
            [
                _event("user", [types.Part(text="Create a greeting skill.")]),
                _event("model", [types.Part(text="Done.")]),
            ]
        )

        await plugin.after_run_callback(invocation_context=ctx)

        mock_curate.assert_awaited_once()
        assert mock_curate.await_args is not None
        history = mock_curate.await_args.args[0]
        assert history[0] == {"role": "user", "content": [{"text": "Create a greeting skill."}]}
        assert history[1] == {"role": "model", "content": [{"text": "Done."}]}


@pytest.mark.asyncio
async def test_plugin_skips_empty_session(repo: SkillRepo, mock_model: str) -> None:
    curator = ADKCurator(repo, model=mock_model)

    with patch.object(curator, "curate", new_callable=AsyncMock) as mock_curate:
        plugin = curator.plugin()
        await plugin.after_run_callback(invocation_context=_context([]))
        mock_curate.assert_not_awaited()


@pytest.mark.asyncio
async def test_plugin_skips_session_with_no_usable_content(
    repo: SkillRepo, mock_model: str
) -> None:
    curator = ADKCurator(repo, model=mock_model)

    with patch.object(curator, "curate", new_callable=AsyncMock) as mock_curate:
        plugin = curator.plugin()
        ctx = _context([SimpleNamespace(content=None, author="model")])
        await plugin.after_run_callback(invocation_context=ctx)
        mock_curate.assert_not_awaited()
