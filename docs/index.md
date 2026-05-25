# SkillOS

SkillOS is an implementation of Google's [SkillOS paper](https://arxiv.org/abs/2605.06614) — a framework for self-evolving agents that grow and refine a shared library of reusable skills over time.

The repository is split into a **framework-agnostic core** and **SDK-specific integrations**. Pick the integration that matches your agent framework; all of them share the same `SkillRepo` storage format and curation model.

## Packages

| Package | Description |
|---------|-------------|
| [skillos-core](api/skillos-core.md) | Core interfaces and components: `SkillRepo`, `Skill`, `Curator`, `AsyncCurator`, `Changelog`, `Trace`. Backend-agnostic via fsspec. |
| [skillos-strands](api/skillos-strands.md) | [Strands Agents](https://strandsagents.com) integration — wraps `SkillRepo` as native Strands tools. |
| skillos-langgraph | _coming soon_ — [LangGraph](https://github.com/langchain-ai/langgraph) integration. |
| skillos-adk | _coming soon_ — [Google ADK](https://google.github.io/adk-docs/) integration. |

## Quick example

```python
from skillos_core import SkillRepo

repo = SkillRepo("./my-skills")

# list all skills
for skill in repo:
    print(f"{skill.name}: {skill.description}")

# create a new skill
repo.insert(
    name="hello-world",
    description="A minimal example skill.",
    body="# Hello World\n\nThis skill does nothing yet.",
)
```

## How it works

SkillOS models agent self-improvement as a curation loop:

1. The agent runs and produces an OpenTelemetry **Trace**.
2. A **Curator** (backed by an LLM) analyzes the trace and produces a **Changelog** — a list of insert / update / delete operations.
3. An **AsyncCurator** applies each change to the **SkillRepo** automatically.

The `SkillRepo` is the durable store. It is backed by [fsspec](https://filesystem-spec.readthedocs.io/), so the same code works against local disk, S3, GCS, Azure, or an in-memory test fixture.
