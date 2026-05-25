from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from skillos_core import ChangeKind, Changelog, SkillRepo, Trace
from skillos_strands import StrandsCurator
from skillos_strands.curator import _format_trace, _make_recording_tools


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


def _make_trace() -> Trace:
    return Trace(trace_id="test-trace", spans=[])


def test_format_trace_empty() -> None:
    t = Trace(trace_id="abc", spans=[])
    text = _format_trace(t)
    assert "abc" in text
    assert "(empty trace)" in text


def test_recording_tools_insert(repo: SkillRepo) -> None:
    changelog = Changelog()
    tools = _make_recording_tools(repo, changelog)
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
    tools = _make_recording_tools(repo, changelog)
    insert = next(t for t in tools if t.tool_name == "insert_skill")

    insert(name="hello", description="desc", body="body\n")
    result = insert(name="hello", description="desc", body="body\n")

    assert result["applied"] is False
    assert "already exists" in result["error"]
    assert len(changelog.changes) == 2
    assert changelog.applied == [changelog.changes[0]]
    assert changelog.failed == [changelog.changes[1]]


def test_recording_tools_update(repo: SkillRepo) -> None:
    repo.insert("hello", "v1", "body\n")
    changelog = Changelog()
    tools = _make_recording_tools(repo, changelog)
    update = next(t for t in tools if t.tool_name == "update_skill")

    result = update(name="hello", description="v2")

    assert result["applied"] is True
    assert repo.read("hello").description == "v2"
    assert changelog.changes[0].kind is ChangeKind.UPDATE


def test_recording_tools_delete(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    changelog = Changelog()
    tools = _make_recording_tools(repo, changelog)
    delete = next(t for t in tools if t.tool_name == "delete_skill")

    result = delete(name="hello")

    assert result["applied"] is True
    assert "hello" not in repo
    assert changelog.changes[0].kind is ChangeKind.DELETE


def test_recording_tools_delete_failure(repo: SkillRepo) -> None:
    changelog = Changelog()
    tools = _make_recording_tools(repo, changelog)
    delete = next(t for t in tools if t.tool_name == "delete_skill")

    result = delete(name="nope")

    assert result["applied"] is False
    assert "nope" in result["error"]


def test_recording_tools_list_and_read_do_not_record(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    changelog = Changelog()
    tools = _make_recording_tools(repo, changelog)
    list_fn = next(t for t in tools if t.tool_name == "list_skills")
    read_fn = next(t for t in tools if t.tool_name == "read_skill")

    assert list_fn() == ["hello"]
    result = read_fn(name="hello")
    assert result["name"] == "hello"
    assert len(changelog.changes) == 0


@pytest.mark.asyncio
@patch("skillos_strands.curator.Agent")
@patch("skillos_strands.curator.BedrockModel")
async def test_strands_curator_curate(
    mock_bedrock_cls: MagicMock,
    mock_agent_cls: MagicMock,
    repo: SkillRepo,
) -> None:
    def fake_invoke(prompt):
        repo.insert("from-agent", "Agent created this.", "# From Agent\n")

    mock_agent = mock_agent_cls.return_value
    mock_agent.invoke_async = AsyncMock(side_effect=fake_invoke)

    curator = StrandsCurator(repo, model_id="us.amazon.nova-pro-v1:0")
    await curator.curate(_make_trace())

    mock_bedrock_cls.assert_called_once_with(model_id="us.amazon.nova-pro-v1:0")
    mock_agent.invoke_async.assert_awaited_once()
    assert "from-agent" in repo


@pytest.mark.asyncio
@patch("skillos_strands.curator.Agent")
@patch("skillos_strands.curator.BedrockModel")
async def test_strands_curator_records_tool_calls(
    mock_bedrock_cls: MagicMock,
    mock_agent_cls: MagicMock,
    repo: SkillRepo,
) -> None:
    def fake_invoke(prompt):
        tools_dict = {t.tool_name: t for t in mock_agent_cls.call_args.kwargs["tools"]}
        tools_dict["insert_skill"](name="new-skill", description="Fresh.", body="# New\n")
        tools_dict["delete_skill"](name="nonexistent")

    mock_agent = mock_agent_cls.return_value
    mock_agent.invoke_async = AsyncMock(side_effect=fake_invoke)

    curator = StrandsCurator(repo)
    cl = await curator.curate(_make_trace())

    assert len(cl.applied) == 1
    assert cl.applied[0].name == "new-skill"
    assert len(cl.failed) == 1
    assert cl.failed[0].name == "nonexistent"
