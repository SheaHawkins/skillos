# skillos-strands API Reference

```python
from skillos_strands import create_skill_tools
```

`skillos-strands` wraps a `SkillRepo` as a list of [Strands Agents](https://pypi.org/project/strands-agents/) tools. Pass the list to `Agent(tools=...)` and the agent can manage skills autonomously.

---

## `create_skill_tools(repo)`

```python
create_skill_tools(repo: SkillRepo) -> list[DecoratedFunctionTool]
```

Return five Strands tools bound to `repo`. The tools share the same repository
instance, so any mutations made by the agent are immediately visible to
subsequent reads within the same session.

```python
from strands import Agent
from skillos_core import SkillRepo
from skillos_strands import create_skill_tools

repo = SkillRepo("./my-skills")
agent = Agent(tools=create_skill_tools(repo))
```

---

## Tools

### `list_skills() -> list[str]`

List all skill names in the repository. Equivalent to `SkillRepo.list_skills()`.

---

### `read_skill(name) -> dict`

Read a skill's metadata and body by name.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | The skill name. |

Returns a dict with keys `name`, `description`, `body`, `metadata`, and `resources`.

---

### `insert_skill(name, description, body, license, allowed_tools, compatibility, metadata) -> dict`

Insert a new skill into the repository. Equivalent to `SkillRepo.insert()`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Lowercase alphanumeric with hyphens, max 64 chars. |
| `description` | `str` | required | 1–1024 chars. |
| `body` | `str` | required | Free-form markdown. |
| `license` | `str` | `"MIT"` | SPDX identifier. |
| `allowed_tools` | `list[str] \| None` | `None` | Tools the skill may use. |
| `compatibility` | `str \| None` | `None` | Compatibility string. |
| `metadata` | `dict \| None` | `None` | Arbitrary nested metadata. |

Returns a dict with keys `name` and `description`.

---

### `update_skill(name, description, body, license, allowed_tools, compatibility, metadata) -> dict`

Update an existing skill's body and/or frontmatter fields. Only supply the
fields you want to change; omitted fields (passed as `None`) are left as-is.
Equivalent to `SkillRepo.update()`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | The skill to update. |
| `description` | `str \| None` | `None` | New description, or `None` to leave unchanged. |
| `body` | `str \| None` | `None` | New body, or `None` to leave unchanged. |
| `license` | `str \| None` | `None` | New license, or `None` to leave unchanged. |
| `allowed_tools` | `list[str] \| None` | `None` | New allowed tools, or `None` to leave unchanged. |
| `compatibility` | `str \| None` | `None` | New compatibility string, or `None` to leave unchanged. |
| `metadata` | `dict \| None` | `None` | New metadata, or `None` to leave unchanged. |

Returns a dict with keys `name` and `description`.

---

### `delete_skill(name) -> dict`

Delete a skill and all its bundled resources. Equivalent to `SkillRepo.delete()`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | The skill to delete. |

Returns `{"deleted": name}`.
