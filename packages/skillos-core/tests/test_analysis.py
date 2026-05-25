from __future__ import annotations

import json

from opentelemetry.sdk.trace import TracerProvider
from skillos_core import ChangeKind, Trace
from skillos_core.analysis import format_trace_prompt, parse_changelog


def _make_span(name: str, attrs: dict | None = None):
    provider = TracerProvider()
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span(name, attributes=attrs or {}) as span:
        pass
    return span


def test_format_trace_prompt_with_spans() -> None:
    s1 = _make_span("llm.call", {"gen_ai.request.model": "claude-sonnet"})
    s2 = _make_span("tool.invoke", {"tool.name": "Read"})
    t = Trace(trace_id="abc", spans=[s1, s2])
    prompt = format_trace_prompt(t)
    assert "abc" in prompt
    assert "llm.call" in prompt
    assert "tool.invoke" in prompt
    assert "gen_ai.request.model" in prompt
    assert "Read" in prompt


def test_format_trace_prompt_empty() -> None:
    t = Trace(trace_id="empty", spans=[])
    prompt = format_trace_prompt(t)
    assert "(empty trace)" in prompt


def test_parse_changelog_insert() -> None:
    raw = json.dumps(
        {
            "changes": [
                {
                    "kind": "insert",
                    "name": "pdf-extract",
                    "description": "Extract text from PDFs",
                    "body": "# PDF Extract\n\nUse pdfplumber.\n",
                    "license": "MIT",
                    "allowed_tools": ["Read", "Bash"],
                }
            ]
        }
    )
    cl = parse_changelog(raw)
    assert len(cl.changes) == 1
    c = cl.changes[0]
    assert c.kind is ChangeKind.INSERT
    assert c.name == "pdf-extract"
    assert c.description == "Extract text from PDFs"
    assert c.body == "# PDF Extract\n\nUse pdfplumber.\n"
    assert c.license == "MIT"
    assert c.allowed_tools == ["Read", "Bash"]


def test_parse_changelog_update_and_delete() -> None:
    raw = json.dumps(
        {
            "changes": [
                {"kind": "update", "name": "hello", "description": "updated desc"},
                {"kind": "delete", "name": "old-skill"},
            ]
        }
    )
    cl = parse_changelog(raw)
    assert len(cl.changes) == 2
    assert cl.changes[0].kind is ChangeKind.UPDATE
    assert cl.changes[0].description == "updated desc"
    assert cl.changes[0].body is None
    assert cl.changes[1].kind is ChangeKind.DELETE
    assert cl.changes[1].name == "old-skill"


def test_parse_changelog_empty() -> None:
    cl = parse_changelog('{"changes": []}')
    assert cl.changes == []


def test_parse_changelog_strips_markdown_fence() -> None:
    raw = '```json\n{"changes": [{"kind": "delete", "name": "x"}]}\n```'
    cl = parse_changelog(raw)
    assert len(cl.changes) == 1
    assert cl.changes[0].name == "x"


def test_parse_changelog_null_fields_ignored() -> None:
    raw = json.dumps(
        {
            "changes": [
                {
                    "kind": "insert",
                    "name": "test",
                    "description": "d",
                    "body": "b",
                    "license": None,
                    "compatibility": None,
                    "metadata": None,
                }
            ]
        }
    )
    cl = parse_changelog(raw)
    c = cl.changes[0]
    assert c.license is None
    assert c.compatibility is None
    assert c.metadata is None
