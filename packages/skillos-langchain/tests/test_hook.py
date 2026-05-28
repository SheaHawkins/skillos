from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.callbacks import AsyncCallbackHandler
from skillos_core import SkillRepo
from skillos_langchain import LangChainCurator
from skillos_langchain.curator import _CuratorCallbackHandler


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


@pytest.fixture
def mock_model() -> MagicMock:
    return MagicMock()


def test_callback_returns_callback_handler(repo: SkillRepo, mock_model: MagicMock) -> None:
    curator = LangChainCurator(repo, model=mock_model)
    handler = curator.callback()
    assert isinstance(handler, _CuratorCallbackHandler)
    assert isinstance(handler, AsyncCallbackHandler)


@pytest.mark.asyncio
async def test_callback_fires_on_root_chain_end(repo: SkillRepo, mock_model: MagicMock) -> None:
    curator = LangChainCurator(repo, model=mock_model)

    with patch.object(curator, "curate", new_callable=AsyncMock) as mock_curate:
        handler = curator.callback()
        messages = [
            {"role": "user", "content": "Create a greeting skill."},
            {"role": "assistant", "content": "Done."},
        ]
        await handler.on_chain_end({"messages": messages}, run_id=uuid4(), parent_run_id=None)

        mock_curate.assert_awaited_once_with(messages)


@pytest.mark.asyncio
async def test_callback_skips_nested_chains(repo: SkillRepo, mock_model: MagicMock) -> None:
    curator = LangChainCurator(repo, model=mock_model)

    with patch.object(curator, "curate", new_callable=AsyncMock) as mock_curate:
        handler = curator.callback()
        await handler.on_chain_end(
            {"messages": [{"role": "user", "content": "hi"}]},
            run_id=uuid4(),
            parent_run_id=uuid4(),
        )

        mock_curate.assert_not_awaited()


@pytest.mark.asyncio
async def test_callback_skips_empty_messages(repo: SkillRepo, mock_model: MagicMock) -> None:
    curator = LangChainCurator(repo, model=mock_model)

    with patch.object(curator, "curate", new_callable=AsyncMock) as mock_curate:
        handler = curator.callback()
        await handler.on_chain_end({"messages": []}, run_id=uuid4(), parent_run_id=None)
        await handler.on_chain_end({}, run_id=uuid4(), parent_run_id=None)

        mock_curate.assert_not_awaited()
