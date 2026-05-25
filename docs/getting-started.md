# Getting Started

SkillOS ships three "languages" for working with skill repositories. All three share the same storage format and curation model — choose based on your agent framework.

| Language | Package | Use when |
|----------|---------|----------|
| [skillos-core](#skillos-core) | `pip install skillos-core` | Direct Python, framework-agnostic, or building your own integration. |
| [skillos-strands](#skillos-strands) | `pip install skillos-strands` | Using [Strands Agents](https://strandsagents.com) (Amazon Bedrock). |
| [skillos-langgraph](#skillos-langgraph) | _coming soon_ | Using [LangGraph](https://github.com/langchain-ai/langgraph). |

---

## skillos-core

The lowest-level entry point. It provides all the core interfaces and is what the SDK-specific packages build on.

### Install

```bash
pip install skillos-core
# with cloud storage extras:
pip install "skillos-core[s3]"    # Amazon S3
pip install "skillos-core[gcs]"   # Google Cloud Storage
pip install "skillos-core[azure]" # Azure Blob Storage
```

### Create a skill repository

A skill repository is a directory where each subdirectory contains a `SKILL.md` file.

```
my-skills/
├── hello-world/
│   └── SKILL.md
└── code-review/
    ├── SKILL.md
    └── prompt.txt
```

### Read skills

```python
from skillos_core import SkillRepo

repo = SkillRepo("./my-skills")

# list all skill names
print(repo.list_skills())  # ['code-review', 'hello-world']

# iterate
for skill in repo:
    print(f"{skill.name}: {skill.description}")

# read one skill
skill = repo.read("hello-world")
print(skill.body)
```

### Write skills

```python
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

### Remote backends

Because SkillOS uses fsspec, any supported protocol works without changing your application code:

```python
repo = SkillRepo("s3://my-bucket/skills", anon=False)
repo = SkillRepo("gs://my-bucket/skills")
repo = SkillRepo("memory://test-repo")  # in-memory, useful for tests
```

### Curation loop

The curation loop lets an agent self-improve by analyzing its own traces and updating the skill library.

```python
import asyncio
from skillos_core import AsyncCurator, Change, ChangeKind, Changelog, SkillRepo, Trace

repo = SkillRepo("./my-skills")

async def analyze(trace: Trace) -> Changelog:
    # your LLM call here — return a Changelog describing what to change
    return Changelog(changes=[
        Change(
            kind=ChangeKind.INSERT,
            name="greet",
            description="Greets the user by name.",
            body="# Greet\n\nCall the user by name and say hello.",
        ),
    ])

curator = AsyncCurator(repo, analyze=analyze)

# run one curation cycle
trace = Trace(trace_id="abc123", spans=[])
changelog = asyncio.run(curator.curate(trace))
print(f"Applied {len(changelog.applied)} changes")
```

---

## skillos-strands

`skillos-strands` wraps `SkillRepo` as native [Strands Agents](https://strandsagents.com) tools so your Bedrock-backed agent can read and write skills mid-conversation without any extra wiring.

### Install

```bash
pip install skillos-strands
```

### Use with a Strands agent

```python
from skillos_core import SkillRepo
from skillos_strands import create_skill_tools
from strands import Agent

repo = SkillRepo("./my-skills")

agent = Agent(tools=create_skill_tools(repo))

# the agent can now call list_skills, read_skill, insert_skill,
# update_skill, and delete_skill as part of its normal tool loop
agent("What skills do we have? Add a new one called 'format-json' that formats JSON.")
```

### Available tools

`create_skill_tools(repo)` returns five Strands tools:

| Tool | Description |
|------|-------------|
| `list_skills` | List all skill names in the repository. |
| `read_skill(name)` | Read a skill's metadata and body. |
| `insert_skill(name, description, body, ...)` | Create a new skill. |
| `update_skill(name, ...)` | Partially update an existing skill. |
| `delete_skill(name)` | Delete a skill and all its bundled resources. |

### Remote repository

Any fsspec-backed repo works:

```python
repo = SkillRepo("s3://my-bucket/skills")
agent = Agent(tools=create_skill_tools(repo))
```

---

## skillos-langgraph

!!! note "Coming soon"
    `skillos-langgraph` is not yet released. This section describes the planned API.

`skillos-langgraph` will expose `SkillRepo` operations as LangGraph tool nodes, making it easy to add self-evolving skill management to any LangGraph graph.

```python
# planned API (not yet available)
from skillos_core import SkillRepo
from skillos_langgraph import create_skill_tool_node

repo = SkillRepo("./my-skills")
tool_node = create_skill_tool_node(repo)
```

To be notified when `skillos-langgraph` ships, watch the [GitHub repository](https://github.com/sheahawkins/skillos).
