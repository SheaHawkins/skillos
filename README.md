# SkillOS

Reference implementation of Google's SkillOS skill format. This is a [uv
workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
containing the SkillOS packages.

## Architecture

SkillOS separates skill storage from the agent framework you use. A shared
core handles the repository format and curation interface; SDK-specific
packages expose that repository in the native idiom of each framework.

| Package | SDK | Description |
|---------|-----|-------------|
| [`packages/skillos-core/`](packages/skillos-core/) | — | Core abstractions: `SkillRepo`, `Skill`, `Curator`, `Changelog`. Backend-agnostic via fsspec. |
| [`packages/skillos-strands/`](packages/skillos-strands/) | Strands Agents | Wraps `SkillRepo` as Strands tools, ready for `Agent(tools=...)`. |

SDK integrations for Google ADK and LangGraph are planned.

## Development

This project uses [uv](https://docs.astral.sh/uv/) for environment and
dependency management. The Python version is pinned in `.python-version`
and resolved deps are locked in `uv.lock`.

```
uv sync           # create .venv and install all workspace packages
uv run pytest     # run the full test suite
```

To work on a single package, run pytest scoped to it:

```
uv run pytest packages/skillos-core
uv run pytest packages/skillos-strands
```
