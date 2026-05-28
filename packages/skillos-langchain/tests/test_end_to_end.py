"""End-to-end test: user agent -> curator callback -> skill created in repo.

The user agent runs with a fake chat model and the curator's callback handler
attached. When the user agent's run finishes, the callback fires, the curator
sees that conversation and (with its own model mocked) calls insert_skill to
create a new skill in the repo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from skillos_core import SkillRepo
from skillos_langchain import LangChainCurator


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


@pytest.mark.asyncio
@patch("skillos_langchain.curator.create_agent")
async def test_user_agent_callback_triggers_curator_which_creates_skill(
    mock_curator_create_agent: MagicMock,
    repo: SkillRepo,
) -> None:
    curator = LangChainCurator(repo, model=MagicMock())

    async def curator_fake_ainvoke(state: Any) -> None:
        tools = {t.name: t for t in mock_curator_create_agent.call_args.args[1]}
        tools["insert_skill"].invoke(
            {
                "name": "pdf-extraction",
                "description": "Extract text from PDFs using pdfplumber.",
                "body": "# PDF Extraction\n\nUse pdfplumber to extract text from PDF files.\n",
            }
        )

    mock_curator_create_agent.return_value.ainvoke = AsyncMock(side_effect=curator_fake_ainvoke)

    # A real user agent, driven by a fake model, with the curator callback attached.
    user_model = GenericFakeChatModel(
        messages=iter([AIMessage(content="The PDF contains Invoice #1234, total $500.00.")])
    )
    user_agent = create_agent(user_model, [])
    await user_agent.ainvoke(
        {"messages": [("user", "Extract the text from invoice.pdf")]},
        config={"callbacks": [curator.callback()]},
    )

    assert "pdf-extraction" in repo
    skill = repo.read("pdf-extraction")
    assert "pdfplumber" in skill.body
    assert skill.description == "Extract text from PDFs using pdfplumber."


@pytest.mark.asyncio
@patch("skillos_langchain.curator.create_agent")
async def test_curator_handles_mixed_success_and_failure(
    mock_curator_create_agent: MagicMock,
    repo: SkillRepo,
) -> None:
    curator = LangChainCurator(repo, model=MagicMock())

    async def curator_fake_ainvoke(state: Any) -> None:
        tools = {t.name: t for t in mock_curator_create_agent.call_args.args[1]}
        tools["insert_skill"].invoke(
            {"name": "good-skill", "description": "A valid skill.", "body": "# Good\n"}
        )
        try:
            tools["insert_skill"].invoke(
                {"name": "INVALID NAME", "description": "bad", "body": "body\n"}
            )
        except ValueError:
            pass

    mock_curator_create_agent.return_value.ainvoke = AsyncMock(side_effect=curator_fake_ainvoke)

    changelog = await curator.curate([{"role": "user", "content": "test"}])

    assert len(changelog.applied) == 1
    assert len(changelog.failed) == 1
    assert changelog.applied[0].name == "good-skill"
    assert "good-skill" in repo
    assert "INVALID NAME" not in repo


@pytest.mark.asyncio
@patch("skillos_langchain.curator.create_agent")
async def test_curator_no_changes_returns_empty_changelog(
    mock_curator_create_agent: MagicMock,
    repo: SkillRepo,
) -> None:
    curator = LangChainCurator(repo, model=MagicMock())

    mock_curator_create_agent.return_value.ainvoke = AsyncMock(return_value=None)

    changelog = await curator.curate([{"role": "user", "content": "nothing interesting"}])

    assert len(changelog.changes) == 0
    assert repo.list_skills() == []
