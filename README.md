# skillos-strands

Strands plugin for SkillOS.

## SkillRepo

`SkillRepo` is a read-only abstraction over a directory of skills, backed by
[fsspec](https://filesystem-spec.readthedocs.io/). The backend is selected
from the URL protocol, so the same code works against local disk, S3, GCS,
Azure, in-memory test fixtures, and anything else fsspec supports.

A skill is any immediate subdirectory of the repo root that contains a
`SKILL.md` file. The `SKILL.md` may have YAML frontmatter; everything else
in the directory is treated as bundled resources.

```python
from skillos_strands import SkillRepo

repo = SkillRepo("/path/to/skills")          # local
repo = SkillRepo("s3://bucket/skills")       # S3 (pip install skillos-strands[s3])
repo = SkillRepo("gs://bucket/skills")       # GCS (pip install skillos-strands[gcs])

for skill in repo:
    print(skill.name, "-", skill.description)

skill = repo.read("hello")
print(skill.body)
for path in skill.list_resources():
    data = skill.read_resource(path)
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for environment and
dependency management. The Python version is pinned in `.python-version`
and resolved deps are locked in `uv.lock`.

```
uv sync           # create .venv and install all deps (incl. dev group)
uv run pytest     # run the test suite
```

Cloud backends ship as extras: `uv sync --extra s3`, `--extra gcs`,
`--extra azure`.
