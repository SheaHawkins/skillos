# skillos-strands API Reference

`skillos-strands` implements the `Curator` interface for [Strands Agents](https://strandsagents.com) (Amazon Bedrock).

```bash
pip install skillos-strands
```

---

## StrandsCurator

```python
from skillos_strands import StrandsCurator
```

A `Curator` that runs a Strands `Agent` to analyse traces and mutate the skill repository. The agent receives a formatted trace and calls skill tools (`list_skills`, `read_skill`, `insert_skill`, `update_skill`, `delete_skill`) to decide what to create, update, or delete.

### `StrandsCurator(repo, *, model, system_prompt=...)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `repo` | `SkillRepo` | The skill repository to manage. |
| `model` | `strands.models.Model` | Any Strands-compatible model (e.g. `BedrockModel`). |
| `system_prompt` | `str` | Override the default curator system prompt. |

### `async curate(trace: Trace) -> Changelog`

Format the trace, invoke the Strands agent, and return the resulting `Changelog`.

**Example:**

```python
from skillos_core import SkillRepo
from skillos_strands import StrandsCurator
from strands.models import BedrockModel

repo = SkillRepo("./my-skills")
curator = StrandsCurator(
    repo,
    model=BedrockModel("us.amazon.nova-pro-v1:0"),
)

changelog = await curator.curate(trace)

for change in changelog.applied:
    print(f"[{change.kind}] {change.name}")

for change in changelog.failed:
    print(f"FAILED [{change.kind}] {change.name}: {change.error}")
```

---

## create_skill_tools

```python
from skillos_strands import create_skill_tools
```

Build the list of Strands tools for interacting with a `SkillRepo`. Use this directly when you want to embed skill-management tools into your own Strands agent rather than delegating to `StrandsCurator`.

### `create_skill_tools(repo, *, changelog=None) -> list[DecoratedFunctionTool]`

| Parameter | Type | Description |
|-----------|------|-------------|
| `repo` | `SkillRepo` | The skill repository to manage. |
| `changelog` | `Changelog \| None` | If provided, every mutation is recorded here. |

Returns five tools:

| Tool | Description |
|------|-------------|
| `list_skills` | List all skill names in the repository. |
| `read_skill` | Read a skill's metadata and body by name. |
| `insert_skill` | Create a new skill. |
| `update_skill` | Partially update an existing skill. |
| `delete_skill` | Delete a skill and all its bundled resources. |

**Example — embedding tools in your own agent:**

```python
from skillos_core import Changelog, SkillRepo
from skillos_strands import create_skill_tools
from strands import Agent
from strands.models import BedrockModel

repo = SkillRepo("./my-skills")
changelog = Changelog()
skill_tools = create_skill_tools(repo, changelog=changelog)

agent = Agent(
    model=BedrockModel("us.amazon.nova-pro-v1:0"),
    tools=[*your_other_tools, *skill_tools],
)
```
