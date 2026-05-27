# Getting Started

SkillOS speaks three languages — **Strands**, **ADK**, and **LangGraph** — one for each major agent framework. All three share the same `SkillRepo` from `skillos-core`; the SDK package is just the bridge between your framework and the skill repository.

## 1. Install

=== "Strands"

    ```bash
    pip install skillos-strands
    ```

    Requires Python ≥ 3.10 and an AWS account with Amazon Bedrock access.

=== "ADK"

    ```bash
    pip install skillos-adk   # coming soon
    ```

=== "LangGraph"

    ```bash
    pip install skillos-langgraph   # coming soon
    ```

If you prefer [uv](https://docs.astral.sh/uv/):

```bash
uv add skillos-strands
```

---

## 2. Create a skill repository

A skill repository is a directory (or any remote path) where each subdirectory contains a `SKILL.md` file:

```
my-skills/
├── code-review/
│   └── SKILL.md
└── summarize/
    ├── SKILL.md
    └── prompt.txt
```

Open it with `SkillRepo`:

```python
from skillos_core import SkillRepo

repo = SkillRepo("./my-skills")           # local
repo = SkillRepo("s3://bucket/skills")    # S3
repo = SkillRepo("gs://bucket/skills")    # GCS
repo = SkillRepo("memory://test-repo")    # in-memory (tests)
```

---

## 3. Attach a curator

The curator analyses conversation history from your agent runs and updates the skill repository accordingly.

=== "Strands"

    ```python
    from skillos_core import ConversationHistory, SkillRepo
    from skillos_strands import StrandsCurator
    from strands.models import BedrockModel

    repo = SkillRepo("./my-skills")
    curator = StrandsCurator(
        repo,
        model=BedrockModel("us.amazon.nova-pro-v1:0"),
    )

    # After each agent run, pass the conversation history:
    history: ConversationHistory = agent.messages   # list of role/content dicts
    changelog = await curator.curate(history)
    print(f"{len(changelog.applied)} skill(s) changed")
    ```

=== "ADK"

    ```python
    # Coming soon
    from skillos_core import ConversationHistory, SkillRepo
    from skillos_adk import ADKCurator

    repo = SkillRepo("./my-skills")
    curator = ADKCurator(repo, model=...)
    changelog = await curator.curate(history)
    ```

=== "LangGraph"

    ```python
    # Coming soon
    from skillos_core import ConversationHistory, SkillRepo
    from skillos_langgraph import LangGraphCurator

    repo = SkillRepo("./my-skills")
    curator = LangGraphCurator(repo, model=...)
    changelog = await curator.curate(history)
    ```

---

## 4. Read and write skills directly

You can also interact with the repository without a curator — useful for seeding initial skills or inspecting the repo.

```python
from skillos_core import SkillRepo

repo = SkillRepo("./my-skills")

# List all skill names
print(repo.list_skills())   # ['code-review', 'summarize']

# Read a skill
skill = repo.read("code-review")
print(skill.description)
print(skill.body)

# Iterate
for skill in repo:
    print(f"{skill.name}: {skill.description}")

# Insert
repo.insert(
    name="hello-world",
    description="Greet the user. Use when the user asks for a greeting.",
    body="# Hello World\n\nSay hello to the user.",
    license="MIT",
    allowed_tools=["Read", "Bash"],
)

# Update
repo.update("hello-world", description="Greet the user warmly.")

# Delete
repo.delete("hello-world")
```

---

## 5. Remote backends

Because `SkillRepo` uses [fsspec](https://filesystem-spec.readthedocs.io/), any supported protocol works out of the box:

```python
# S3 (pip install skillos-core[s3])
repo = SkillRepo("s3://my-bucket/skills", anon=False)

# GCS (pip install skillos-core[gcs])
repo = SkillRepo("gs://my-bucket/skills")

# Azure Blob
repo = SkillRepo("az://my-container/skills")

# In-memory — great for tests
repo = SkillRepo("memory://test-repo")
```
