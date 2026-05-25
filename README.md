# skillos

Implementation of Google's [SkillOS](https://arxiv.org/abs/2605.06614) — a framework for self-evolving agents that maintain a live library of reusable skills.

## Packages

| Package | Install | Description |
|---------|---------|-------------|
| [`skillos-core`](packages/skillos-core/) | `pip install skillos-core` | Interfaces and reusable components: `SkillRepo`, `Skill`, `Curator`, `Changelog`, `Trace`. Backend-agnostic via fsspec. |
| [`skillos-strands`](packages/skillos-strands/) | `pip install skillos-strands` | [Strands Agents](https://strandsagents.com) integration — exposes `SkillRepo` as native Strands tools. |
| `skillos-langgraph` | _coming soon_ | [LangGraph](https://github.com/langchain-ai/langgraph) integration — SkillRepo as LangGraph nodes and tools. |
| `skillos-adk` | _coming soon_ | [Google ADK](https://google.github.io/adk-docs/) integration. |

## Getting Started

SkillOS ships three "languages" for working with skill repositories. Pick the one that matches your agent framework:

### skillos-core — direct Python, any framework

The lowest-level entry point. Use it standalone or as the base for your own integration.

```bash
pip install skillos-core
```

```python
from skillos_core import SkillRepo

repo = SkillRepo("./my-skills")

# Read skills
for skill in repo:
    print(f"{skill.name}: {skill.description}")

# Write skills
repo.insert(
    name="summarize",
    description="Summarize a document into bullet points.",
    body="# Summarize\n\nGiven a document, produce a concise summary.",
    license="MIT",
    allowed_tools=["Read", "Write"],
)
```

### skillos-strands — Strands Agents (Amazon Bedrock)

Wraps `SkillRepo` as first-class Strands tools so your agent can read and write skills during a conversation.

```bash
pip install skillos-strands
```

```python
from skillos_core import SkillRepo
from skillos_strands import create_skill_tools
from strands import Agent

repo = SkillRepo("./my-skills")
agent = Agent(tools=create_skill_tools(repo))

agent("What skills do we have? Create a new one called 'greet' that greets the user.")
```

### skillos-langgraph — LangGraph _(coming soon)_

A LangGraph integration providing SkillRepo as graph nodes and tool nodes.

```bash
pip install skillos-langgraph  # not yet released
```

## Curation loop

All three languages share the same curation model from `skillos-core`:

1. An agent produces a `Trace` of spans (OpenTelemetry).
2. A `Curator` analyzes the trace and returns a `Changelog` — a list of `Change` records (insert / update / delete).
3. `AsyncCurator` applies the changes to the `SkillRepo` automatically.

```python
from skillos_core import AsyncCurator, Changelog, ChangeKind, Change, SkillRepo, Trace

repo = SkillRepo("./my-skills")

async def my_analyzer(trace: Trace) -> Changelog:
    # your LLM-backed analysis here
    return Changelog(changes=[
        Change(kind=ChangeKind.INSERT, name="greet",
               description="Greets the user.", body="# Greet\n\n..."),
    ])

curator = AsyncCurator(repo, analyze=my_analyzer)
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for environment and dependency management.

```bash
uv sync           # create .venv and install all workspace packages
uv run pytest     # run the full test suite
```

To work on a single package:

```bash
uv run pytest packages/skillos-core
uv run pytest packages/skillos-strands
```
