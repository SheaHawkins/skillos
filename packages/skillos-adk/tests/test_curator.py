from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types
from skillos_adk import ADKCurator, create_skill_tools
from skillos_adk.curator import _events_to_history, _format_history
from skillos_core import ChangeKind, Changelog, ConversationHistory, SkillRepo


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


@pytest.fixture
def mock_model() -> str:
    # ADK accepts a model id string or a BaseLlm instance; a string keeps the
    # curator from touching the network when the runner is mocked.
    return "gemini-2.0-flash"


def _sample_history() -> ConversationHistory:
    return [
        {"role": "user", "content": [{"text": "Summarize this PDF."}]},
        {
            "role": "model",
            "content": [
                {"text": "I'll read the PDF."},
                {"function_call": {"name": "read_file", "args": {"path": "doc.pdf"}}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"function_response": {"name": "read_file", "response": {"text": "PDF text here"}}},
            ],
        },
        {"role": "model", "content": [{"text": "Here is your summary."}]},
    ]


def _make_event(role: str, parts: list[types.Part], author: str = "") -> SimpleNamespace:
    """Build a minimal stand-in for an ADK Event with a ``content`` attribute."""
    return SimpleNamespace(content=types.Content(role=role, parts=parts), author=author or role)


# --- _format_history ---------------------------------------------------------


def test_format_history_renders_messages() -> None:
    text = _format_history(_sample_history())
    assert "[user] Summarize this PDF." in text
    assert "tool_call: read_file" in text
    assert "tool_result:" in text
    assert "PDF text here" in text
    assert "[model] Here is your summary." in text


def test_format_history_string_content() -> None:
    history: ConversationHistory = [
        {"role": "user", "content": "hello"},
        {"role": "model", "content": "hi there"},
    ]
    text = _format_history(history)
    assert "[user] hello" in text
    assert "[model] hi there" in text


def test_format_history_empty() -> None:
    assert _format_history([]) == "(empty conversation)"


# --- _events_to_history ------------------------------------------------------


def test_events_to_history_extracts_text_and_calls() -> None:
    events = [
        _make_event("user", [types.Part(text="Extract text from invoice.pdf")]),
        _make_event(
            "model",
            [
                types.Part(text="Reading the PDF."),
                types.Part(
                    function_call=types.FunctionCall(name="read_pdf", args={"path": "invoice.pdf"})
                ),
            ],
        ),
        _make_event(
            "user",
            [
                types.Part(
                    function_response=types.FunctionResponse(
                        name="read_pdf", response={"text": "Invoice #1234"}
                    )
                )
            ],
        ),
    ]
    history = _events_to_history(events)
    assert history[0] == {"role": "user", "content": [{"text": "Extract text from invoice.pdf"}]}
    assert {"text": "Reading the PDF."} in history[1]["content"]
    assert {"function_call": {"name": "read_pdf", "args": {"path": "invoice.pdf"}}} in history[1][
        "content"
    ]
    assert history[2]["content"][0]["function_response"]["name"] == "read_pdf"


def test_events_to_history_skips_empty_content() -> None:
    events = [
        SimpleNamespace(content=None, author="model"),
        _make_event("user", [types.Part(text="hi")]),
    ]
    history = _events_to_history(events)
    assert len(history) == 1
    assert history[0]["content"] == [{"text": "hi"}]


def test_format_after_events_to_history_roundtrip() -> None:
    events = [
        _make_event("user", [types.Part(text="Do a thing")]),
        _make_event(
            "model",
            [types.Part(function_call=types.FunctionCall(name="act", args={"k": "v"}))],
        ),
    ]
    text = _format_history(_events_to_history(events))
    assert "[user] Do a thing" in text
    assert "tool_call: act" in text


# --- recording tools ---------------------------------------------------------


def test_recording_tools_insert(repo: SkillRepo) -> None:
    changelog = Changelog()
    tools = {t.name: t.func for t in create_skill_tools(repo, changelog=changelog)}

    result = tools["insert_skill"](name="hello", description="A greeting.", body="# Hello\n")

    assert result["applied"] is True
    assert result["error"] is None
    assert "hello" in repo
    assert len(changelog.changes) == 1
    assert changelog.changes[0].kind is ChangeKind.INSERT
    assert changelog.changes[0].applied is True


def test_recording_tools_insert_failure(repo: SkillRepo) -> None:
    changelog = Changelog()
    tools = {t.name: t.func for t in create_skill_tools(repo, changelog=changelog)}

    tools["insert_skill"](name="hello", description="desc", body="body\n")
    with pytest.raises(FileExistsError):
        tools["insert_skill"](name="hello", description="desc", body="body\n")

    assert len(changelog.changes) == 2
    assert changelog.applied == [changelog.changes[0]]
    assert changelog.failed == [changelog.changes[1]]


def test_recording_tools_update(repo: SkillRepo) -> None:
    repo.insert("hello", "v1", "body\n")
    changelog = Changelog()
    tools = {t.name: t.func for t in create_skill_tools(repo, changelog=changelog)}

    result = tools["update_skill"](name="hello", description="v2")

    assert result["applied"] is True
    assert repo.read("hello").description == "v2"
    assert changelog.changes[0].kind is ChangeKind.UPDATE


def test_recording_tools_delete(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    changelog = Changelog()
    tools = {t.name: t.func for t in create_skill_tools(repo, changelog=changelog)}

    result = tools["delete_skill"](name="hello")

    assert result["applied"] is True
    assert "hello" not in repo
    assert changelog.changes[0].kind is ChangeKind.DELETE


def test_recording_tools_delete_failure(repo: SkillRepo) -> None:
    changelog = Changelog()
    tools = {t.name: t.func for t in create_skill_tools(repo, changelog=changelog)}

    with pytest.raises(FileNotFoundError):
        tools["delete_skill"](name="nope")

    assert len(changelog.failed) == 1
    assert changelog.failed[0].error is not None
    assert "nope" in changelog.failed[0].error


def test_recording_tools_list_and_read_do_not_record(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    changelog = Changelog()
    tools = {t.name: t.func for t in create_skill_tools(repo, changelog=changelog)}

    assert tools["list_skills"]() == ["hello"]
    result = tools["read_skill"](name="hello")
    assert result["name"] == "hello"
    assert len(changelog.changes) == 0


# --- ADKCurator.curate (runner mocked) ---------------------------------------


def _mock_runner(mock_runner_cls: MagicMock, invoke_fn) -> MagicMock:
    """Wire a patched InMemoryRunner so curate() drives ``invoke_fn`` offline."""
    runner = mock_runner_cls.return_value
    runner.session_service.create_session = AsyncMock(return_value=SimpleNamespace(id="session-1"))

    async def run_async(*args, **kwargs):
        invoke_fn()
        return
        yield  # pragma: no cover - makes this an async generator

    runner.run_async = run_async
    return runner


@pytest.mark.asyncio
@patch("skillos_adk.curator.InMemoryRunner")
async def test_adk_curator_curate(
    mock_runner_cls: MagicMock,
    repo: SkillRepo,
    mock_model: str,
) -> None:
    def fake_invoke() -> None:
        repo.insert("from-agent", "Agent created this.", "# From Agent\n")

    _mock_runner(mock_runner_cls, fake_invoke)

    curator = ADKCurator(repo, model=mock_model)
    await curator.curate(_sample_history())

    mock_runner_cls.assert_called_once()
    agent = mock_runner_cls.call_args.kwargs["agent"]
    assert agent.model == mock_model
    assert "from-agent" in repo


@pytest.mark.asyncio
@patch("skillos_adk.curator.InMemoryRunner")
async def test_adk_curator_records_tool_calls(
    mock_runner_cls: MagicMock,
    repo: SkillRepo,
    mock_model: str,
) -> None:
    def fake_invoke() -> None:
        agent = mock_runner_cls.call_args.kwargs["agent"]
        tools = {t.name: t.func for t in agent.tools}
        tools["insert_skill"](name="new-skill", description="Fresh.", body="# New\n")
        try:
            tools["delete_skill"](name="nonexistent")
        except FileNotFoundError:
            pass

    _mock_runner(mock_runner_cls, fake_invoke)

    curator = ADKCurator(repo, model=mock_model)
    cl = await curator.curate(_sample_history())

    assert len(cl.applied) == 1
    assert cl.applied[0].name == "new-skill"
    assert len(cl.failed) == 1
    assert cl.failed[0].name == "nonexistent"
