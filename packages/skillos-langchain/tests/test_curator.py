from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from skillos_core import ChangeKind, Changelog, ConversationHistory, SkillRepo
from skillos_langchain import LangChainCurator, create_skill_tools
from skillos_langchain.curator import _format_history


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


@pytest.fixture
def mock_model() -> MagicMock:
    return MagicMock()


def _sample_history() -> list:
    return [
        HumanMessage(content="Summarize this PDF."),
        AIMessage(
            content="I'll read the PDF.",
            tool_calls=[{"name": "Read", "args": {"path": "doc.pdf"}, "id": "t1"}],
        ),
        ToolMessage(content="PDF text here", tool_call_id="t1"),
        AIMessage(content="Here is your summary."),
    ]


def test_format_history_renders_langchain_messages() -> None:
    text = _format_history(_sample_history())
    assert "[user] Summarize this PDF." in text
    assert "tool_call: Read" in text
    assert "tool_result: PDF text here" in text
    assert "[assistant] Here is your summary." in text


def test_format_history_dict_openai_style() -> None:
    history: ConversationHistory = [
        {"role": "user", "content": "hello"},
        {
            "role": "assistant",
            "content": "thinking...",
            "tool_calls": [
                {"function": {"name": "search", "arguments": '{"q": "test"}'}},
            ],
        },
        {"role": "tool", "content": "search result"},
    ]
    text = _format_history(history)
    assert "[user] hello" in text
    assert "tool_call: search" in text
    assert "[tool] search result" in text


def test_format_history_empty() -> None:
    assert _format_history([]) == "(empty conversation)"


def test_recording_tools_insert(repo: SkillRepo) -> None:
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    insert = next(t for t in tools if t.name == "insert_skill")

    result = insert.invoke({"name": "hello", "description": "A greeting.", "body": "# Hello\n"})

    assert result["applied"] is True
    assert result["error"] is None
    assert "hello" in repo
    assert len(changelog.changes) == 1
    assert changelog.changes[0].kind is ChangeKind.INSERT
    assert changelog.changes[0].applied is True


def test_recording_tools_insert_failure(repo: SkillRepo) -> None:
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    insert = next(t for t in tools if t.name == "insert_skill")

    insert.invoke({"name": "hello", "description": "desc", "body": "body\n"})
    with pytest.raises(FileExistsError):
        insert.invoke({"name": "hello", "description": "desc", "body": "body\n"})

    assert len(changelog.changes) == 2
    assert changelog.applied == [changelog.changes[0]]
    assert changelog.failed == [changelog.changes[1]]


def test_recording_tools_update(repo: SkillRepo) -> None:
    repo.insert("hello", "v1", "body\n")
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    update = next(t for t in tools if t.name == "update_skill")

    result = update.invoke({"name": "hello", "description": "v2"})

    assert result["applied"] is True
    assert repo.read("hello").description == "v2"
    assert changelog.changes[0].kind is ChangeKind.UPDATE


def test_recording_tools_delete(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    delete = next(t for t in tools if t.name == "delete_skill")

    result = delete.invoke({"name": "hello"})

    assert result["applied"] is True
    assert "hello" not in repo
    assert changelog.changes[0].kind is ChangeKind.DELETE


def test_recording_tools_delete_failure(repo: SkillRepo) -> None:
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    delete = next(t for t in tools if t.name == "delete_skill")

    with pytest.raises(FileNotFoundError):
        delete.invoke({"name": "nope"})

    assert len(changelog.failed) == 1
    assert changelog.failed[0].error is not None
    assert "nope" in changelog.failed[0].error


def test_recording_tools_list_and_read_do_not_record(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    list_fn = next(t for t in tools if t.name == "list_skills")
    read_fn = next(t for t in tools if t.name == "read_skill")

    assert list_fn.invoke({}) == ["hello"]
    result = read_fn.invoke({"name": "hello"})
    assert result["name"] == "hello"
    assert len(changelog.changes) == 0


@pytest.mark.asyncio
@patch("skillos_langchain.curator.create_agent")
async def test_langchain_curator_curate(
    mock_create_agent: MagicMock,
    repo: SkillRepo,
    mock_model: MagicMock,
) -> None:
    async def fake_ainvoke(state):
        repo.insert("from-agent", "Agent created this.", "# From Agent\n")

    mock_agent = mock_create_agent.return_value
    mock_agent.ainvoke = AsyncMock(side_effect=fake_ainvoke)

    curator = LangChainCurator(repo, model=mock_model)
    await curator.curate(_sample_history())

    mock_create_agent.assert_called_once()
    assert mock_create_agent.call_args.args[0] is mock_model
    mock_agent.ainvoke.assert_awaited_once()
    assert "from-agent" in repo


@pytest.mark.asyncio
@patch("skillos_langchain.curator.create_agent")
async def test_langchain_curator_records_tool_calls(
    mock_create_agent: MagicMock,
    repo: SkillRepo,
    mock_model: MagicMock,
) -> None:
    async def fake_ainvoke(state):
        tools_dict = {t.name: t for t in mock_create_agent.call_args.args[1]}
        tools_dict["insert_skill"].invoke(
            {"name": "new-skill", "description": "Fresh.", "body": "# New\n"}
        )
        try:
            tools_dict["delete_skill"].invoke({"name": "nonexistent"})
        except FileNotFoundError:
            pass

    mock_agent = mock_create_agent.return_value
    mock_agent.ainvoke = AsyncMock(side_effect=fake_ainvoke)

    curator = LangChainCurator(repo, model=mock_model)
    cl = await curator.curate(_sample_history())

    assert len(cl.applied) == 1
    assert cl.applied[0].name == "new-skill"
    assert len(cl.failed) == 1
    assert cl.failed[0].name == "nonexistent"
