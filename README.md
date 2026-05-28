# skillos

Implementation of Google's [SkillOS](https://arxiv.org/abs/2605.06614) — a framework for self-evolving agents.

SkillOS lets agents record what they learn as structured skills and reuse them in future sessions. This repository is organized into a backend-agnostic core and SDK-specific integrations.

## Packages

### Core

- [`skillos-core`](packages/skillos-core/) — interfaces and shared components: `SkillRepo`, `Skill`, `Curator`, `ConversationHistory`, `Changelog`. Backend-agnostic via [fsspec](https://filesystem-spec.readthedocs.io/).

### SDK Integrations

Pick the package that matches your agent framework:

| Package | Framework | Status |
|---------|-----------|--------|
| [`skillos-strands`](packages/skillos-strands/) | [Strands Agents](https://strandsagents.com) | Available |
| `skillos-adk` | [Google ADK](https://google.github.io/adk-docs/) | Coming soon |
| `skillos-langgraph` | [LangGraph](https://langchain-ai.github.io/langgraph/) | Coming soon |

## Getting Started

Choose the package for your agent framework and install it:

```bash
# Strands Agents (Amazon Bedrock)
pip install skillos-strands

# Google ADK  (coming soon)
pip install skillos-adk

# LangGraph  (coming soon)
pip install skillos-langgraph
```

All three share the same `SkillRepo` from `skillos-core` — the SDK package is just the bridge between your framework and the skill repository.

**Strands example — hook-based (automatic):**

```python
from skillos_core import SkillRepo
from skillos_strands import StrandsCurator
from strands import Agent
from strands.models import BedrockModel

repo = SkillRepo("./my-skills")
curator = StrandsCurator(repo, model=BedrockModel("us.amazon.nova-pro-v1:0"))

# Wire the curator as a hook — skills are updated automatically after every run
agent = Agent(
    model=BedrockModel("us.amazon.nova-pro-v1:0"),
    hooks=[curator.hook()],
)
await agent.invoke_async("What tools did you use for that task?")
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for environment and dependency management. The Python version is pinned in `.python-version` and resolved deps are locked in `uv.lock`.

```bash
uv sync           # create .venv and install all workspace packages
uv run pytest     # run the full test suite
```

To work on a single package:

```bash
uv run pytest packages/skillos-core
uv run pytest packages/skillos-strands
```
