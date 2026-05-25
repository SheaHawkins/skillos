# Getting Started

## Installation

```bash
pip install skillos-core
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add skillos-core
```

## Create a skill repository

A skill repository is any directory (or remote path) where each subdirectory contains a `SKILL.md` file.

```
my-skills/
├── hello-world/
│   └── SKILL.md
└── code-review/
    ├── SKILL.md
    └── prompt.txt
```

## Open and read skills

```python
from skillos_core import SkillRepo

repo = SkillRepo("./my-skills")

# list skill names
print(repo.list_skills())  # ['code-review', 'hello-world']

# read a specific skill
skill = repo.read("hello-world")
print(skill.description)
print(skill.body)
```

## Write skills

```python
repo.insert(
    name="summarize",
    description="Summarize a document into bullet points.",
    body="# Summarize\n\nGiven a document, produce a concise summary.",
    license="MIT",
    allowed_tools=["Read", "Write"],
)
```

Update an existing skill:

```python
repo.update("summarize", description="Summarize any document concisely.")
```

Delete a skill:

```python
repo.delete("summarize")
```

## Remote backends

Because SkillOS uses fsspec, any supported protocol works:

```python
# S3
repo = SkillRepo("s3://my-bucket/skills", anon=False)

# GCS
repo = SkillRepo("gs://my-bucket/skills")

# In-memory (useful for tests)
repo = SkillRepo("memory://test-repo")
```
