# SkillOS

SkillOS is a framework for self-evolving agents, based on [Google's SkillOS paper](https://arxiv.org/abs/2605.06614). Agents accumulate experience as structured **skills** stored in a repository, and a **curator** analyses conversation history to keep that repository up to date.

This implementation is split into a backend-agnostic core and SDK-specific integrations.

---

## skillos-core

The core package defines the shared interfaces and the skill repository. It has no dependency on any agent framework.

| Component | Description |
|-----------|-------------|
| [`SkillRepo`](api/skillos-core.md#skillrepo) | Read/write skill repository backed by any [fsspec](https://filesystem-spec.readthedocs.io/) filesystem — local, S3, GCS, Azure, in-memory, and more. |
| [`Skill`](api/skillos-core.md#skill) | A parsed skill: name, frontmatter metadata, markdown body, and bundled resources. |
| [`Curator`](api/skillos-core.md#curator) | Abstract base class. Receives a `ConversationHistory` and returns a `Changelog` of mutations. |
| [`ConversationHistory`](api/skillos-core.md#conversationhistory) | Type alias for a list of conversation messages passed to a curator. |
| [`Changelog`](api/skillos-core.md#changelog) | Record of `Change` objects (insert / update / delete) produced by a curator run. |

```bash
pip install skillos-core
```

---

## SDK integrations

Each integration implements the `Curator` interface for a specific agent framework. Pick the one that matches your stack.

### skillos-strands

Curator backed by [Strands Agents](https://strandsagents.com) (Amazon Bedrock).

| Component | Description |
|-----------|-------------|
| [`StrandsCurator`](api/skillos-strands.md#strandscurator) | Runs a Strands `Agent` that calls skill tools to mutate the repo. |
| [`create_skill_tools`](api/skillos-strands.md#create_skill_tools) | Returns the list of Strands tools (`list_skills`, `read_skill`, `insert_skill`, `update_skill`, `delete_skill`). |

```bash
pip install skillos-strands
```

### skillos-adk *(coming soon)*

Curator backed by [Google ADK](https://google.github.io/adk-docs/).

### skillos-langgraph *(coming soon)*

Curator backed by [LangGraph](https://langchain-ai.github.io/langgraph/).

---

## Quick example

```python
from skillos_core import SkillRepo
from skillos_strands import StrandsCurator
from strands.models import BedrockModel

repo = SkillRepo("./my-skills")
curator = StrandsCurator(repo, model=BedrockModel("us.amazon.nova-pro-v1:0"))

changelog = await curator.curate(history)
for change in changelog.applied:
    print(change.kind, change.name)
```
