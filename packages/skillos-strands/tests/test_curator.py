from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from skillos_core import ChangeKind, Changelog, ConversationHistory, SkillRepo
from skillos_strands import StrandsCurator, create_skill_tools
from skillos_strands.curator import _format_history


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


@pytest.fixture
def mock_model() -> MagicMock:
    return MagicMock()


def _sample_history() -> ConversationHistory:
    return [
        {"role": "user", "content": "Summarize this PDF."},
        {
            "role": "assistant",
            "content": [
                {"text": "I'll read the PDF."},
                {"toolUse": {"name": "Read", "input": {"path": "doc.pdf"}}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "t1", "content": [{"text": "PDF text here"}]}},
            ],
        },
        {"role": "assistant", "content": "Here is your summary."},
    ]


def test_format_history_renders_messages() -> None:
    text = _format_history(_sample_history())
    assert "[user] Summarize this PDF." in text
    assert "tool_call: Read" in text
    assert "tool_result: PDF text here" in text
    assert "[assistant] Here is your summary." in text


def test_format_history_openai_style() -> None:
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
    insert = next(t for t in tools if t.tool_name == "insert_skill")

    result = insert(name="hello", description="A greeting.", body="# Hello\n")

    assert result["applied"] is True
    assert result["error"] is None
    assert "hello" in repo
    assert len(changelog.changes) == 1
    assert changelog.changes[0].kind is ChangeKind.INSERT
    assert changelog.changes[0].applied is True


def test_recording_tools_insert_failure(repo: SkillRepo) -> None:
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    insert = next(t for t in tools if t.tool_name == "insert_skill")

    insert(name="hello", description="desc", body="body\n")
    with pytest.raises(FileExistsError):
        insert(name="hello", description="desc", body="body\n")

    assert len(changelog.changes) == 2
    assert changelog.applied == [changelog.changes[0]]
    assert changelog.failed == [changelog.changes[1]]


def test_recording_tools_update(repo: SkillRepo) -> None:
    repo.insert("hello", "v1", "body\n")
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    update = next(t for t in tools if t.tool_name == "update_skill")

    result = update(name="hello", description="v2")

    assert result["applied"] is True
    assert repo.read("hello").description == "v2"
    assert changelog.changes[0].kind is ChangeKind.UPDATE


def test_recording_tools_delete(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    delete = next(t for t in tools if t.tool_name == "delete_skill")

    result = delete(name="hello")

    assert result["applied"] is True
    assert "hello" not in repo
    assert changelog.changes[0].kind is ChangeKind.DELETE


def test_recording_tools_delete_failure(repo: SkillRepo) -> None:
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    delete = next(t for t in tools if t.tool_name == "delete_skill")

    with pytest.raises(FileNotFoundError):
        delete(name="nope")

    assert len(changelog.failed) == 1
    assert changelog.failed[0].error is not None
    assert "nope" in changelog.failed[0].error


def test_recording_tools_list_and_read_do_not_record(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    changelog = Changelog()
    tools = create_skill_tools(repo, changelog=changelog)
    list_fn = next(t for t in tools if t.tool_name == "list_skills")
    read_fn = next(t for t in tools if t.tool_name == "read_skill")

    assert list_fn() == ["hello"]
    result = read_fn(name="hello")
    assert result["name"] == "hello"
    assert len(changelog.changes) == 0


@pytest.mark.asyncio
@patch("skillos_strands.curator.Agent")
async def test_strands_curator_curate(
    mock_agent_cls: MagicMock,
    repo: SkillRepo,
    mock_model: MagicMock,
) -> None:
    def fake_invoke(prompt):
        repo.insert("from-agent", "Agent created this.", "# From Agent\n")

    mock_agent = mock_agent_cls.return_value
    mock_agent.invoke_async = AsyncMock(side_effect=fake_invoke)

    curator = StrandsCurator(repo, model=mock_model)
    await curator.curate(_sample_history())

    mock_agent_cls.assert_called_once()
    assert mock_agent_cls.call_args.kwargs["model"] is mock_model
    mock_agent.invoke_async.assert_awaited_once()
    assert "from-agent" in repo


@pytest.mark.asyncio
@patch("skillos_strands.curator.Agent")
async def test_strands_curator_records_tool_calls(
    mock_agent_cls: MagicMock,
    repo: SkillRepo,
    mock_model: MagicMock,
) -> None:
    def fake_invoke(prompt):
        tools_dict = {t.tool_name: t for t in mock_agent_cls.call_args.kwargs["tools"]}
        tools_dict["insert_skill"](name="new-skill", description="Fresh.", body="# New\n")
        try:
            tools_dict["delete_skill"](name="nonexistent")
        except FileNotFoundError:
            pass

    mock_agent = mock_agent_cls.return_value
    mock_agent.invoke_async = AsyncMock(side_effect=fake_invoke)

    curator = StrandsCurator(repo, model=mock_model)
    cl = await curator.curate(_sample_history())

    assert len(cl.applied) == 1
    assert cl.applied[0].name == "new-skill"
    assert len(cl.failed) == 1
    assert cl.failed[0].name == "nonexistent"
