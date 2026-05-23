# skillos-core

Core abstractions for SkillOS.

## SkillRepo

`SkillRepo` is an abstraction over a directory of skills, backed by
[fsspec](https://filesystem-spec.readthedocs.io/). The backend is selected
from the URL protocol, so the same code works against local disk, S3, GCS,
Azure, in-memory test fixtures, and anything else fsspec supports.

A skill is any immediate subdirectory of the repo root that contains a
`SKILL.md` file. The `SKILL.md` may have YAML frontmatter; everything else
in the directory is treated as bundled resources.

```python
from skillos_core import SkillRepo

repo = SkillRepo("/path/to/skills")          # local
repo = SkillRepo("s3://bucket/skills")       # S3 (pip install skillos-core[s3])
repo = SkillRepo("gs://bucket/skills")       # GCS (pip install skillos-core[gcs])

for skill in repo:
    print(skill.name, "-", skill.description)

skill = repo.read("hello")
print(skill.body)
for path in skill.list_resources():
    data = skill.read_resource(path)
```

### Inserting, updating, and deleting skills

`insert`, `update`, and `delete` mutate the repo on the underlying fsspec
backend. `name` and `description` are validated against the SKILL.md
frontmatter spec on write (`name`: ≤64 chars, `[a-z0-9-]+`, not
`anthropic`/`claude`; `description`: 1–1024 chars). Extra fields like
`license` or `allowed-tools` pass through via `metadata`.

```python
repo.insert(
    "hello",
    "Greets the user. Use when the user asks for a hello.",
    "# Hello\n\n...",
    metadata={"license": "MIT"},
)

repo.update("hello", description="Greets the user warmly.")
repo.update("hello", metadata={"license": None})  # drop a key

repo.delete("hello")
```
