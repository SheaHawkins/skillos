from __future__ import annotations

import json
from typing import Any

from .changelog import Change, ChangeKind, Changelog
from .trace import Trace

SYSTEM_PROMPT = """\
You are a skill curator for SkillOS. Given a trace of agent execution \
(OpenTelemetry spans), identify reusable patterns that should be captured \
as skills and output the mutations needed.

Reply with a JSON object matching this schema — nothing else:

{
  "changes": [
    {
      "kind": "insert" | "update" | "delete",
      "name": "skill-name",
      "description": "One-line description (required for insert)",
      "body": "Markdown body with instructions (required for insert)",
      "license": "MIT",
      "allowed_tools": ["Read", "Bash"],
      "compatibility": null,
      "metadata": null
    }
  ]
}

Rules:
- "name" must be lowercase alphanumeric with hyphens, max 64 chars.
- "description" max 1024 chars.
- For "update", include only the fields that changed.
- For "delete", only "kind" and "name" are needed.
- If no skill changes are warranted, return {"changes": []}.
"""


def format_trace_prompt(trace: Trace) -> str:
    lines = [f"Trace {trace.trace_id}", ""]
    for span in trace.spans:
        name = span.name if hasattr(span, "name") else str(span)
        attrs = dict(span.attributes) if hasattr(span, "attributes") and span.attributes else {}
        status = span.status if hasattr(span, "status") else None
        line = f"- [{name}]"
        if attrs:
            attr_str = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
            line += f" {{{attr_str}}}"
        if status and hasattr(status, "status_code"):
            line += f" status={status.status_code.name}"
        lines.append(line)
    if len(lines) == 2:
        lines.append("(empty trace)")
    return "\n".join(lines)


def parse_changelog(text: str) -> Changelog:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    data = json.loads(cleaned)
    changes: list[Change] = []
    for entry in data.get("changes", []):
        kwargs: dict[str, Any] = {
            "kind": ChangeKind(entry["kind"]),
            "name": entry["name"],
        }
        for field in (
            "description",
            "body",
            "license",
            "allowed_tools",
            "compatibility",
            "metadata",
        ):
            if field in entry and entry[field] is not None:
                kwargs[field] = entry[field]
        changes.append(Change(**kwargs))
    return Changelog(changes=changes)
