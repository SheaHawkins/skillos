"""End-to-end test: user run -> curator plugin -> skill created in repo.

The curator's internal ADK runner is mocked so no real LLM is called. The
mocked runner stands in for the curator agent: when "invoked" it calls the
skill tools, mirroring what a real model would do after reasoning about the
conversation. The user-side run is represented by ADK session events fed
through the curator plugin's ``after_run_callback``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents.invocation_context import InvocationContext
from google.genai import types
from skillos_adk import ADKCurator
from skillos_core import SkillRepo


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


def _mock_runner(mock_runner_cls: MagicMock, invoke_fn) -> None:
    """Wire a patched InMemoryRunner so curate() drives ``invoke_fn`` offline."""
    runner = mock_runner_cls.return_value
    runner.session_service.create_session = AsyncMock(return_value=SimpleNamespace(id="session-1"))

    async def run_async(*args, **kwargs):
        invoke_fn()
        return
        yield  # pragma: no cover - makes this an async generator

    runner.run_async = run_async


def _event(role: str, parts: list[types.Part]) -> SimpleNamespace:
    return SimpleNamespace(content=types.Content(role=role, parts=parts), author=role)


def _pdf_session_events() -> list[SimpleNamespace]:
    return [
        _event("user", [types.Part(text="Extract the text from invoice.pdf")]),
        _event(
            "model",
            [
                types.Part(text="I'll extract the text from the PDF."),
                types.Part(
                    function_call=types.FunctionCall(
                        name="run_shell",
                        args={"command": 'python -c "import pdfplumber; ..."'},
                    )
                ),
            ],
        ),
        _event(
            "user",
            [
                types.Part(
                    function_response=types.FunctionResponse(
                        name="run_shell",
                        response={"output": "Invoice #1234\nTotal: $500.00"},
                    )
                )
            ],
        ),
        _event(
            "model",
            [types.Part(text="The PDF contains Invoice #1234 with a total of $500.00.")],
        ),
    ]


@pytest.mark.asyncio
@patch("skillos_adk.curator.InMemoryRunner")
async def test_user_run_triggers_curator_plugin_which_creates_skill(
    mock_runner_cls: MagicMock,
    repo: SkillRepo,
) -> None:
    curator = ADKCurator(repo, model="gemini-2.0-flash")

    def fake_invoke() -> None:
        agent = mock_runner_cls.call_args.kwargs["agent"]
        tools = {t.name: t.func for t in agent.tools}
        tools["insert_skill"](
            name="pdf-extraction",
            description="Extract text from PDFs using pdfplumber.",
            body="# PDF Extraction\n\nUse pdfplumber to extract text from PDF files.\n",
        )

    _mock_runner(mock_runner_cls, fake_invoke)

    # Drive the full path: user session events -> plugin -> curator -> repo.
    plugin = curator.plugin()
    ctx = cast(
        InvocationContext,
        SimpleNamespace(session=SimpleNamespace(events=_pdf_session_events())),
    )
    await plugin.after_run_callback(invocation_context=ctx)

    # The curator agent saw the conversation and received it as a prompt.
    assert mock_runner_cls.call_args.kwargs["agent"].name == "skill_curator"
    assert "pdf-extraction" in repo
    skill = repo.read("pdf-extraction")
    assert "pdfplumber" in skill.body
    assert skill.description == "Extract text from PDFs using pdfplumber."


@pytest.mark.asyncio
@patch("skillos_adk.curator.InMemoryRunner")
async def test_curator_handles_mixed_success_and_failure(
    mock_runner_cls: MagicMock,
    repo: SkillRepo,
) -> None:
    curator = ADKCurator(repo, model="gemini-2.0-flash")

    def fake_invoke() -> None:
        agent = mock_runner_cls.call_args.kwargs["agent"]
        tools = {t.name: t.func for t in agent.tools}
        tools["insert_skill"](name="good-skill", description="A valid skill.", body="# Good\n")
        try:
            tools["insert_skill"](name="INVALID NAME", description="bad", body="body\n")
        except ValueError:
            pass

    _mock_runner(mock_runner_cls, fake_invoke)

    changelog = await curator.curate([{"role": "user", "content": "test"}])

    assert len(changelog.applied) == 1
    assert len(changelog.failed) == 1
    assert changelog.applied[0].name == "good-skill"
    assert "good-skill" in repo
    assert "INVALID NAME" not in repo


@pytest.mark.asyncio
@patch("skillos_adk.curator.InMemoryRunner")
async def test_curator_no_changes_returns_empty_changelog(
    mock_runner_cls: MagicMock,
    repo: SkillRepo,
) -> None:
    curator = ADKCurator(repo, model="gemini-2.0-flash")

    _mock_runner(mock_runner_cls, lambda: None)

    changelog = await curator.curate([{"role": "user", "content": "nothing interesting"}])

    assert len(changelog.changes) == 0
    assert repo.list_skills() == []
