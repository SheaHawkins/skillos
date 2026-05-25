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
| `name` | `str` | Lowercase letters, digits, hyphens. Max 64 chars. Not `"anthropic"` or `"claude"`. |
| `description` | `str` | 1–1024 chars, non-empty. |
| `body` | `str` | Free-form markdown body. |
| `license` | `License \| str` | SPDX identifier. Default `"MIT"`. |
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

## Curator

```python
from skillos_core import Curator, AsyncCurator
```

The `Curator` interface drives trace-based skill curation: given an OpenTelemetry
trace, produce a `Changelog` of changes to apply to a `SkillRepo`.

### `Curator` (abstract base class)

```python
class Curator:
    async def curate(self, trace: Trace) -> Changelog: ...
```

Implement this interface to build a custom curation backend.

### `AsyncCurator`

A concrete `Curator` that delegates analysis to a callable and applies the
resulting `Changelog` to a `SkillRepo`.

```python
AsyncCurator(repo: SkillRepo, analyze: Callable[[Trace], Awaitable[Changelog]])
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `repo` | `SkillRepo` | The repository to mutate. |
| `analyze` | `async (Trace) -> Changelog` | Async function that maps a trace to a changelog. |

#### `async curate(trace: Trace) -> Changelog`

Calls `analyze(trace)` then applies each `Change` in the returned `Changelog`
to `repo`. Each `Change` is marked `applied=True` on success or
`applied=False, error=<message>` on failure. Returns the updated `Changelog`.

```python
import asyncio
from skillos_core import AsyncCurator, Changelog, Change, ChangeKind, SkillRepo

async def my_analyzer(trace):
    return Changelog(changes=[
        Change(kind=ChangeKind.INSERT, name="new-skill",
               description="Added by curator.", body="# New Skill"),
    ])

repo = SkillRepo("memory://skills")
curator = AsyncCurator(repo, my_analyzer)
changelog = asyncio.run(curator.curate(trace))
print(changelog.applied)   # successfully applied changes
print(changelog.failed)    # changes that raised an error
```

---

## Changelog

```python
from skillos_core import Changelog, Change, ChangeKind
```

A structured log of insert/update/delete operations produced by a `Curator`.

### `ChangeKind`

Enum of mutation types.

| Member | Value |
|--------|-------|
| `INSERT` | `"INSERT"` |
| `UPDATE` | `"UPDATE"` |
| `DELETE` | `"DELETE"` |

### `Change`

Dataclass representing a single mutation.

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `ChangeKind` | The operation type. |
| `name` | `str` | Target skill name. |
| `applied` | `bool \| None` | Set by `AsyncCurator` after execution. |
| `error` | `str \| None` | Error message if `applied` is `False`. |
| `description` | `str \| None` | New description (INSERT/UPDATE). |
| `body` | `str \| None` | New body (INSERT/UPDATE). |
| `license` | `str \| None` | New license (INSERT/UPDATE). |
| `allowed_tools` | `list[str] \| None` | New allowed tools (INSERT/UPDATE). |
| `compatibility` | `str \| None` | New compatibility string (INSERT/UPDATE). |
| `metadata` | `dict \| None` | New metadata (INSERT/UPDATE). |

### `Changelog`

```python
Changelog(changes: list[Change])
```

| Property | Type | Description |
|----------|------|-------------|
| `applied` | `list[Change]` | Changes where `applied` is `True`. |
| `failed` | `list[Change]` | Changes where `applied` is `False`. |

---

## Trace

```python
from skillos_core import Trace
```

Input to `Curator.curate()`. Carries an OpenTelemetry trace for analysis.

### `Trace`

```python
Trace(trace_id: str, spans: Sequence[ReadableSpan])
```

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | `str` | The OpenTelemetry trace ID. |
| `spans` | `Sequence[ReadableSpan]` | Completed spans from the trace. |

---

## License

```python
from skillos_core import License
```

Enum of common SPDX license identifiers. Accepts string coercion (`License("MIT")`).

| Member | Value |
|--------|-------|
| `MIT` | `"MIT"` |
| `APACHE_2_0` | `"Apache-2.0"` |
| `GPL_3_0` | `"GPL-3.0"` |
| `BSD_3_CLAUSE` | `"BSD-3-Clause"` |
| `GPL_2_0` | `"GPL-2.0"` |
| `BSD_2_CLAUSE` | `"BSD-2-Clause"` |
| `LGPL_3_0` | `"LGPL-3.0"` |
| `MPL_2_0` | `"MPL-2.0"` |
| `AGPL_3_0` | `"AGPL-3.0"` |
| `UNLICENSE` | `"Unlicense"` |
