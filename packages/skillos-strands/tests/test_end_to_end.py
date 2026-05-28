"""End-to-end test: user agent → curator hook → skill created in repo.

Both the user agent's model and the curator agent's model are mocked.
The user agent "runs" and produces a conversation about PDF extraction.
The curator hook fires, the curator agent sees that conversation and
calls insert_skill to create a new skill in the repo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from skillos_core import SkillRepo
from skillos_strands import StrandsCurator


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


def _make_model_that_returns(text: str) -> MagicMock:
    """Create a mock Model whose Agent will produce the given text response."""
    model = MagicMock()
    return model


@pytest.mark.asyncio
@patch("skillos_strands.curator.Agent")
async def test_user_agent_triggers_curator_which_creates_skill(
    mock_curator_agent_cls: MagicMock,
    repo: SkillRepo,
) -> None:
    curator_model = MagicMock()
    curator = StrandsCurator(repo, model=curator_model)

    def curator_fake_invoke(prompt: Any) -> None:
        tools = {t.tool_name: t for t in mock_curator_agent_cls.call_args.kwargs["tools"]}
        tools["insert_skill"](
            name="pdf-extraction",
            description="Extract text from PDFs using pdfplumber.",
            body="# PDF Extraction\n\nUse pdfplumber to extract text from PDF files.\n",
        )

    mock_curator_agent = mock_curator_agent_cls.return_value
    mock_curator_agent.invoke_async = _async_side_effect(curator_fake_invoke)

    user_messages: list[dict[str, Any]] = [
        {"role": "user", "content": "Extract the text from invoice.pdf"},
        {
            "role": "assistant",
            "content": [
                {"text": "I'll extract the text from the PDF."},
                {
                    "toolUse": {
                        "name": "Bash",
                        "input": {
                            "command": 'python -c "import pdfplumber; '
                            "pdf = pdfplumber.open('invoice.pdf'); "
                            'print(pdf.pages[0].extract_text())"'
                        },
                    }
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "t1",
                        "content": [{"text": "Invoice #1234\nTotal: $500.00"}],
                    }
                }
            ],
        },
        {
            "role": "assistant",
            "content": "The PDF contains Invoice #1234 with a total of $500.00.",
        },
    ]

    changelog = await curator.curate(user_messages)

    assert len(changelog.applied) == 1
    assert changelog.applied[0].name == "pdf-extraction"
    assert "pdf-extraction" in repo

    skill = repo.read("pdf-extraction")
    assert "pdfplumber" in skill.body
    assert skill.description == "Extract text from PDFs using pdfplumber."


@pytest.mark.asyncio
@patch("skillos_strands.curator.Agent")
async def test_curator_handles_mixed_success_and_failure(
    mock_curator_agent_cls: MagicMock,
    repo: SkillRepo,
) -> None:
    curator_model = MagicMock()
    curator = StrandsCurator(repo, model=curator_model)

    def curator_fake_invoke(prompt: Any) -> None:
        tools = {t.tool_name: t for t in mock_curator_agent_cls.call_args.kwargs["tools"]}
        tools["insert_skill"](
            name="good-skill",
            description="A valid skill.",
            body="# Good\n",
        )
        try:
            tools["insert_skill"](
                name="INVALID NAME",
                description="bad",
                body="body\n",
            )
        except ValueError:
            pass

    mock_curator_agent = mock_curator_agent_cls.return_value
    mock_curator_agent.invoke_async = _async_side_effect(curator_fake_invoke)

    changelog = await curator.curate([{"role": "user", "content": "test"}])

    assert len(changelog.applied) == 1
    assert len(changelog.failed) == 1
    assert changelog.applied[0].name == "good-skill"
    assert "good-skill" in repo
    assert "INVALID NAME" not in repo


@pytest.mark.asyncio
@patch("skillos_strands.curator.Agent")
async def test_curator_no_changes_returns_empty_changelog(
    mock_curator_agent_cls: MagicMock,
    repo: SkillRepo,
) -> None:
    curator_model = MagicMock()
    curator = StrandsCurator(repo, model=curator_model)

    mock_curator_agent = mock_curator_agent_cls.return_value
    mock_curator_agent.invoke_async = _async_side_effect(lambda prompt: None)

    changelog = await curator.curate([{"role": "user", "content": "nothing interesting"}])

    assert len(changelog.changes) == 0
    assert repo.list_skills() == []


def _async_side_effect(fn):
    """Wrap a sync function as an async mock side_effect."""

    async def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper
