# Getting Started

SkillOS separates skill storage from the agent framework you use. Think of the
SDK packages as different languages for the same skill repository: they all
read and write the same `SKILL.md` format, but each speaks in the native idiom
of its framework.

| Language | Package | Status |
|----------|---------|--------|
| [Strands Agents](#strands-agents) | `skillos-strands` | Available |
| [Google ADK](#google-adk) | `skillos-adk` | Planned |
| [LangGraph](#langgraph) | `skillos-langgraph` | Planned |

If you only need the repository itself — or you're building your own
integration — start with [Core only](#core-only).

---

## Core only

Install `skillos-core` for the skill repository and curation interface,
without any framework dependency.

```bash
pip install skillos-core
# optional backend extras:
pip install skillos-core[s3]    # S3 via s3fs
pip install skillos-core[gcs]   # GCS via gcsfs
pip install skillos-core[azure] # Azure via adlfs
```

### Create a skill repository

A skill repository is any directory (or remote path) where each subdirectory
contains a `SKILL.md` file:

```
my-skills/
├── hello-world/
│   └── SKILL.md
└── code-review/
    ├── SKILL.md
    └── prompt.txt
```

### Read and write skills

```python
from skillos_core import SkillRepo

repo = SkillRepo("./my-skills")          # local
repo = SkillRepo("s3://bucket/skills")  # S3
repo = SkillRepo("memory://test-repo")  # in-memory (great for tests)

# list
print(repo.list_skills())   # ['code-review', 'hello-world']

# read
skill = repo.read("hello-world")
print(skill.description)
print(skill.body)

# write
repo.insert(
    name="summarize",
    description="Summarize a document into bullet points.",
    body="# Summarize\n\nGiven a document, produce a concise summary.",
    license="MIT",
    allowed_tools=["Read", "Write"],
)

repo.update("summarize", description="Summarize any document concisely.")
repo.delete("summarize")
```

---

## Strands Agents

`skillos-strands` wraps `SkillRepo` as a set of Strands tools. Pass them to
`Agent(tools=...)` and the agent can list, read, insert, update, and delete
skills autonomously.

```bash
pip install skillos-strands
```

```python
from strands import Agent
from skillos_core import SkillRepo
from skillos_strands import create_skill_tools

repo = SkillRepo("./my-skills")
tools = create_skill_tools(repo)

agent = Agent(tools=tools)
agent("List all skills in the repository, then write a new one called 'greet'.")
```

`create_skill_tools` returns five tools — `list_skills`, `read_skill`,
`insert_skill`, `update_skill`, `delete_skill` — that the agent calls as
needed. See the [Strands API reference](api/skillos-strands.md) for full
parameter details.

---

## Google ADK

!!! note "Planned"
    `skillos-adk` is not yet available. The section below shows the intended API.

`skillos-adk` will expose `SkillRepo` as Google ADK tools, following the same
pattern as the Strands integration.

```bash
# pip install skillos-adk   (coming soon)
```

```python
# from adk import Agent
# from skillos_core import SkillRepo
# from skillos_adk import create_skill_tools
#
# repo = SkillRepo("./my-skills")
# tools = create_skill_tools(repo)
# agent = Agent(tools=tools)
```

---

## LangGraph

!!! note "Planned"
    `skillos-langgraph` is not yet available. The section below shows the intended API.

`skillos-langgraph` will expose `SkillRepo` as LangGraph-compatible tools and
nodes, following the same pattern as the Strands integration.

```bash
# pip install skillos-langgraph   (coming soon)
```

```python
# from langgraph.prebuilt import create_react_agent
# from skillos_core import SkillRepo
# from skillos_langgraph import create_skill_tools
#
# repo = SkillRepo("./my-skills")
# tools = create_skill_tools(repo)
# agent = create_react_agent(model, tools)
```
