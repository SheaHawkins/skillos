from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from skillos_core import AsyncCurator, ChangeKind, SkillRepo, Trace
from skillos_strands import create_strands_analyzer

FAKE_LLM_RESPONSE = json.dumps(
    {
        "changes": [
            {
                "kind": "insert",
                "name": "pdf-extract",
                "description": "Extract text from PDFs using pdfplumber",
                "body": "# PDF Extract\n\nUse pdfplumber to extract text.\n",
            }
        ]
    }
)


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


def _make_trace() -> Trace:
    return Trace(trace_id="test-trace", spans=[])


@patch("skillos_strands.analyzer.Agent")
@patch("skillos_strands.analyzer.BedrockModel")
def test_create_strands_analyzer_configures_agent(
    mock_bedrock_cls: MagicMock,
    mock_agent_cls: MagicMock,
) -> None:
    create_strands_analyzer(model_id="us.amazon.nova-pro-v1:0")
    mock_bedrock_cls.assert_called_once_with(model_id="us.amazon.nova-pro-v1:0")
    mock_agent_cls.assert_called_once()
    call_kwargs = mock_agent_cls.call_args
    assert call_kwargs.kwargs["model"] is mock_bedrock_cls.return_value


@pytest.mark.asyncio
@patch("skillos_strands.analyzer.Agent")
@patch("skillos_strands.analyzer.BedrockModel")
async def test_analyzer_calls_agent_and_parses_response(
    mock_bedrock_cls: MagicMock,
    mock_agent_cls: MagicMock,
) -> None:
    mock_agent = mock_agent_cls.return_value
    mock_agent.invoke_async = AsyncMock(return_value=MagicMock(__str__=lambda _: FAKE_LLM_RESPONSE))

    analyze = create_strands_analyzer()
    changelog = await analyze(_make_trace())

    mock_agent.invoke_async.assert_awaited_once()
    assert len(changelog.changes) == 1
    assert changelog.changes[0].kind is ChangeKind.INSERT
    assert changelog.changes[0].name == "pdf-extract"


@pytest.mark.asyncio
@patch("skillos_strands.analyzer.Agent")
@patch("skillos_strands.analyzer.BedrockModel")
async def test_end_to_end_with_async_curator(
    mock_bedrock_cls: MagicMock,
    mock_agent_cls: MagicMock,
    repo: SkillRepo,
) -> None:
    mock_agent = mock_agent_cls.return_value
    mock_agent.invoke_async = AsyncMock(return_value=MagicMock(__str__=lambda _: FAKE_LLM_RESPONSE))

    analyze = create_strands_analyzer()
    curator = AsyncCurator(repo, analyze=analyze)
    cl = await curator.curate(_make_trace())

    assert len(cl.applied) == 1
    assert cl.applied[0].name == "pdf-extract"
    assert "pdf-extract" in repo
    assert repo.read("pdf-extract").description == "Extract text from PDFs using pdfplumber"
