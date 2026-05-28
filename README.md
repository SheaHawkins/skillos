# skillos

Implementation of Google's [SkillOS](https://arxiv.org/abs/2605.06614).

Basically, it is a framework for self-evolving agents.

## Packages

- [`packages/skillos-core/`](packages/skillos-core/) — core abstractions
  (`SkillRepo`, `Skill`, `Curator`, `AsyncCurator`). Backend-agnostic via fsspec.
- [`packages/skillos-strands/`](packages/skillos-strands/) — Strands Agents
  analyzer for the Curator (Amazon Bedrock via `strands-agents`).
- [`packages/skillos-langchain/`](packages/skillos-langchain/) — LangChain
  analyzer for the Curator (`LangChainCurator` plus a callback handler that
  curates skills after an agent run, via `langchain`).

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
```
