# SkillOS

SkillOS is a backend-agnostic skill repository format built on [fsspec](https://filesystem-spec.readthedocs.io/). It lets you store, discover, and manage agent skills — locally, on S3, GCS, Azure, or any filesystem fsspec supports.

## Packages

| Package | Description |
|---------|-------------|
| [skillos-core](api/skillos-core.md) | Core abstractions: `SkillRepo`, `Skill`, `License`. |

## Quick example

```python
from skillos_core import SkillRepo

repo = SkillRepo("./my-skills")

# list all skills
for skill in repo:
    print(f"{skill.name}: {skill.description}")

# create a new skill
repo.insert(
    name="hello-world",
    description="A minimal example skill.",
    body="# Hello World\n\nThis skill does nothing yet.",
)
```
