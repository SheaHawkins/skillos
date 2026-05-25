# SkillOS

SkillOS is Google's format for packaging, discovering, and managing agent skills. This project is the reference implementation — a backend-agnostic skill repository plus SDK integrations that expose it in the native idiom of each agent framework.

## Architecture

```
skillos-core          ← shared interfaces and repo logic (fsspec-backed)
  ├── SkillRepo       ← read/write skills on local disk, S3, GCS, Azure, …
  ├── Skill           ← a parsed SKILL.md with metadata + body
  ├── Curator         ← interface for trace-driven skill curation
  └── Changelog       ← structured log of insert/update/delete changes

skillos-strands       ← Strands Agents integration
skillos-adk           ← Google ADK integration          (planned)
skillos-langgraph     ← LangGraph integration           (planned)
```

| Package | SDK | Status |
|---------|-----|--------|
| `skillos-core` | — | Available |
| `skillos-strands` | Strands Agents | Available |
| `skillos-adk` | Google ADK | Planned |
| `skillos-langgraph` | LangGraph | Planned |

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

Pick your SDK in [Getting Started](getting-started.md) to connect the repository to your agent framework.
