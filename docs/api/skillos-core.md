# skillos-core API Reference

```bash
pip install skillos-core
```

---

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

A parsed skill. Returned by `SkillRepo.read()`, `SkillRepo.insert()`, and `SkillRepo.update()`.

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

Abstract base class for all curators. A curator analyzes an agent `Trace` and returns a `Changelog` describing which skills to add, update, or remove.

```python
class Curator(ABC):
    @abstractmethod
    async def curate(self, trace: Trace) -> Changelog: ...
```

Implement this interface to build your own LLM-backed curator. For most cases, use `AsyncCurator` instead.

---

## AsyncCurator

```python
from skillos_core import AsyncCurator
```

Concrete `Curator` that delegates analysis to a user-supplied async callable and eagerly applies each change to the repo.

### `AsyncCurator(repo, *, analyze)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `repo` | `SkillRepo` | The repository to mutate. |
| `analyze` | `Callable[[Trace], Awaitable[Changelog]]` | Async function that inspects the trace and returns a `Changelog`. |

### `async curate(trace) -> Changelog`

Calls `analyze(trace)`, then applies every `Change` in the returned `Changelog` to the repo. Each `Change` is marked `applied=True` on success or `applied=False` with an `error` message on failure. Returns the annotated `Changelog`.

```python
from skillos_core import AsyncCurator, Changelog, Change, ChangeKind, SkillRepo, Trace

repo = SkillRepo("./my-skills")

async def analyze(trace: Trace) -> Changelog:
    return Changelog(changes=[
        Change(kind=ChangeKind.INSERT, name="greet",
               description="Greets the user.", body="# Greet\n\n..."),
    ])

curator = AsyncCurator(repo, analyze=analyze)
changelog = await curator.curate(trace)
print(changelog.applied)   # successfully applied changes
print(changelog.failed)    # changes that raised an exception
```

---

## Changelog

```python
from skillos_core import Changelog
```

A list of `Change` records returned by a `Curator`.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `changes` | `list[Change]` | All changes, in order. |
| `applied` | `list[Change]` | Subset where `change.applied is True`. |
| `failed` | `list[Change]` | Subset where `change.applied is False`. |

---

## Change

```python
from skillos_core import Change
```

A single proposed mutation to the skill repository.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `kind` | `ChangeKind` | `INSERT`, `UPDATE`, or `DELETE`. |
| `name` | `str` | Name of the skill to create/update/delete. |
| `applied` | `bool` | Set by `AsyncCurator` after the change is attempted. |
| `error` | `str \| None` | Error message if the change failed, otherwise `None`. |
| `description` | `str \| None` | New description (required for INSERT). |
| `body` | `str \| None` | New markdown body (required for INSERT). |
| `license` | `License \| str \| None` | SPDX identifier. |
| `allowed_tools` | `list[str] \| None` | Tools the skill may use. |
| `compatibility` | `str \| None` | Compatibility string. |
| `metadata` | `dict \| None` | Arbitrary nested metadata. |

---

## ChangeKind

```python
from skillos_core import ChangeKind
```

Enum describing the type of mutation.

| Member | Value | Description |
|--------|-------|-------------|
| `INSERT` | `"insert"` | Create a new skill. |
| `UPDATE` | `"update"` | Modify an existing skill. |
| `DELETE` | `"delete"` | Remove a skill and its resources. |

---

## Trace

```python
from skillos_core import Trace
```

An OpenTelemetry trace produced by a running agent. Passed to `Curator.curate()` for analysis.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `trace_id` | `str` | The OpenTelemetry trace ID. |
| `spans` | `Sequence[ReadableSpan]` | The spans collected during the agent run. |
