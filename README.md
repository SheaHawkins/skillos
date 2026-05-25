# skillos-strands

Reference implementation for SkillOS. This is a [uv
workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
containing the SkillOS packages.

## Packages

- [`packages/skillos-core/`](packages/skillos-core/) — core abstractions
  (`SkillRepo`, `Skill`, `Curator`, `AsyncCurator`). Backend-agnostic via fsspec.
- [`packages/skillos-strands/`](packages/skillos-strands/) — Strands Agents
  analyzer for the Curator (Amazon Bedrock via `strands-agents`).

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
