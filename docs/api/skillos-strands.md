# skillos-strands API Reference

```bash
pip install skillos-strands
```

`skillos-strands` exposes a `SkillRepo` as native [Strands Agents](https://strandsagents.com) tools, so a Bedrock-backed agent can read and write skills as part of its normal tool loop — no extra wiring required.

---

## create_skill_tools

```python
from skillos_strands import create_skill_tools
```

### `create_skill_tools(repo) -> list[DecoratedFunctionTool]`

Create a set of Strands tools bound to the given `SkillRepo`. Pass the returned list directly to `Agent(tools=...)`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `repo` | `SkillRepo` | The skill repository to expose. |

**Returns** a list of five `DecoratedFunctionTool` instances (see below).

### Example

```python
from skillos_core import SkillRepo
from skillos_strands import create_skill_tools
from strands import Agent

repo = SkillRepo("./my-skills")
agent = Agent(tools=create_skill_tools(repo))

agent("List the available skills and add a new one called 'format-json'.")
```

---

## Tools

The following tools are created by `create_skill_tools` and become available to the agent.

### `list_skills() -> list[str]`

Return the names of all skills in the repository.

### `read_skill(name) -> dict`

Read a skill by name. Returns a dict with keys `name`, `description`, `body`, `metadata`, and `resources`.

| Key | Type | Description |
|-----|------|-------------|
| `name` | `str` | Skill name. |
| `description` | `str \| None` | Short description from frontmatter. |
| `body` | `str` | Markdown body. |
| `metadata` | `dict` | Full YAML frontmatter. |
| `resources` | `list[str]` | Relative paths of bundled resource files. |

### `insert_skill(name, description, body, license?, allowed_tools?, compatibility?, metadata?) -> dict`

Create a new skill. Returns `{"name": ..., "description": ...}`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | — | Lowercase alphanumeric with hyphens, max 64 chars. |
| `description` | `str` | — | 1–1024 chars. |
| `body` | `str` | — | Free-form markdown body. |
| `license` | `str` | `"MIT"` | SPDX identifier. |
| `allowed_tools` | `list[str] \| None` | `None` | Tools the skill may use. |
| `compatibility` | `str \| None` | `None` | Compatibility string. |
| `metadata` | `dict \| None` | `None` | Arbitrary nested metadata. |

### `update_skill(name, description?, body?, license?, allowed_tools?, compatibility?, metadata?) -> dict`

Partially update an existing skill. Only the supplied fields are changed. Returns `{"name": ..., "description": ...}`.

### `delete_skill(name) -> dict`

Delete a skill and all its bundled resources. Returns `{"deleted": name}`.
