# skillos-core API Reference

## SkillRepo

```python
from skillos_core import SkillRepo
```

A repository of skills backed by any fsspec filesystem.

### `SkillRepo(url, **storage_options)`

Open a skill repository at the given URL. The protocol selects the backend — local paths, `s3://`, `gs://`, `az://`, `memory://`, etc. Extra keyword arguments are passed to fsspec.

### `list_skills() -> list[str]`

Return sorted names of all skills (subdirectories containing a `SKILL.md`).

### `read(name) -> Skill`

Read and parse a single skill by name. Raises `FileNotFoundError` if it doesn't exist.

### `insert(name, description, body, *, license="MIT", allowed_tools=None, compatibility=None, metadata=None) -> Skill`

Create a new skill. Validates `name` and `description` against the SKILL.md spec. Raises `FileExistsError` if the skill already exists.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Lowercase letters, digits, hyphens. Max 64 chars. |
| `description` | `str` | 1–1024 chars, non-empty. |
| `body` | `str` | Free-form markdown body. |
| `license` | `License \| str` | SPDX identifier. Default `MIT`. |
| `allowed_tools` | `list[str] \| None` | Tools the skill may use. |
| `compatibility` | `str \| None` | Compatibility string. |
| `metadata` | `dict \| None` | Arbitrary nested metadata. |

### `update(name, *, body=None, description=None, license=None, allowed_tools=None, compatibility=None, metadata=None) -> Skill`

Partial update of an existing skill. `None` means leave unchanged. Raises `FileNotFoundError` if the skill doesn't exist.

### `delete(name) -> None`

Remove a skill and all its bundled resources. Raises `FileNotFoundError` if the skill doesn't exist.

### Iteration

`SkillRepo` supports iteration and containment checks:

```python
for skill in repo:
    print(skill.name)

if "my-skill" in repo:
    print("found it")
```

---

## Skill

```python
from skillos_core import Skill
```

A parsed skill. Returned by `SkillRepo.read()` and `SkillRepo.insert()`.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | The skill's directory name. |
| `metadata` | `dict` | Parsed YAML frontmatter. |
| `body` | `str` | Markdown body after frontmatter. |

### `description -> str | None`

The `description` field from frontmatter, if present.

### `list_resources() -> list[str]`

Return sorted relative paths of all files in the skill directory, excluding `SKILL.md` itself.

### `read_resource(path) -> bytes`

Read a bundled resource file by relative path.

---

## License

```python
from skillos_core import License
```

Enum of common SPDX license identifiers. Accepts string coercion (`License("MIT")`).

| Member | Value |
|--------|-------|
| `MIT` | `MIT` |
| `APACHE_2_0` | `Apache-2.0` |
| `GPL_3_0` | `GPL-3.0` |
| `BSD_3_CLAUSE` | `BSD-3-Clause` |
| `GPL_2_0` | `GPL-2.0` |
| `BSD_2_CLAUSE` | `BSD-2-Clause` |
| `LGPL_3_0` | `LGPL-3.0` |
| `MPL_2_0` | `MPL-2.0` |
| `AGPL_3_0` | `AGPL-3.0` |
| `UNLICENSE` | `Unlicense` |

---

## Curator

```python
from skillos_core import Curator
```

Abstract base class for all curator implementations. SDK-specific packages (`skillos-strands`, `skillos-adk`, `skillos-langgraph`) each provide a concrete subclass.

### `async curate(history: ConversationHistory) -> Changelog`

Analyse a conversation history and apply changes to the skill repository. Returns a `Changelog` recording what was inserted, updated, or deleted.

---

## ConversationHistory

```python
from skillos_core import ConversationHistory, Message
```

Type alias for the conversation passed to a curator.

```python
Message = dict[str, Any]
ConversationHistory = list[Message]
```

Each message is a dictionary with at minimum a `"role"` key (`"user"`, `"assistant"`) and a `"content"` key. The content may be a string or a list of content blocks (text, tool calls, tool results) depending on the agent framework.

---

## Changelog

```python
from skillos_core import Changelog
```

Record of mutations produced by a single curator run.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `changes` | `list[Change]` | All changes attempted (applied and failed). |
| `applied` | `list[Change]` | Changes that succeeded. |
| `failed` | `list[Change]` | Changes that raised an exception. |

---

## Change

```python
from skillos_core import Change, ChangeKind
```

A single mutation record within a `Changelog`.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `kind` | `ChangeKind` | `INSERT`, `UPDATE`, or `DELETE`. |
| `name` | `str` | Name of the affected skill. |
| `applied` | `bool` | `True` if the operation succeeded. |
| `error` | `str \| None` | Error message if the operation failed. |
| `description` | `str \| None` | New description (insert/update only). |
| `body` | `str \| None` | New body (insert/update only). |
| `license` | `License \| str \| None` | New license (insert/update only). |
| `allowed_tools` | `list[str] \| None` | New allowed tools (insert/update only). |
| `compatibility` | `str \| None` | New compatibility string (insert/update only). |
| `metadata` | `dict \| None` | New metadata (insert/update only). |

---

## ChangeKind

```python
from skillos_core import ChangeKind
```

Enum for the type of skill mutation.

| Member | Value |
|--------|-------|
| `INSERT` | `"insert"` |
| `UPDATE` | `"update"` |
| `DELETE` | `"delete"` |
