from pathlib import Path

import pytest

from skillos_strands import Skill, SkillRepo


SKILL_MD = """---
name: hello
description: a hello skill
license: MIT
---

# Hello

This is the body.
"""


@pytest.fixture
def local_repo(tmp_path: Path) -> Path:
    hello = tmp_path / "hello"
    hello.mkdir()
    (hello / "SKILL.md").write_text(SKILL_MD)
    (hello / "script.py").write_text("print('hi')\n")
    (hello / "data").mkdir()
    (hello / "data" / "notes.txt").write_text("notes")

    # A directory without SKILL.md should be ignored.
    junk = tmp_path / "not-a-skill"
    junk.mkdir()
    (junk / "readme.txt").write_text("nope")

    return tmp_path


def test_list_skills_local(local_repo: Path) -> None:
    repo = SkillRepo(str(local_repo))
    assert repo.list_skills() == ["hello"]
    assert "hello" in repo
    assert "not-a-skill" not in repo


def test_read_skill_local(local_repo: Path) -> None:
    repo = SkillRepo(str(local_repo))
    skill = repo.read("hello")
    assert isinstance(skill, Skill)
    assert skill.name == "hello"
    assert skill.description == "a hello skill"
    assert skill.metadata["license"] == "MIT"
    assert "# Hello" in skill.body
    assert "This is the body." in skill.body


def test_resources(local_repo: Path) -> None:
    skill = SkillRepo(str(local_repo)).read("hello")
    assert skill.list_resources() == ["data/notes.txt", "script.py"]
    assert skill.read_resource("script.py") == b"print('hi')\n"
    assert skill.read_resource("data/notes.txt") == b"notes"


def test_iter(local_repo: Path) -> None:
    repo = SkillRepo(str(local_repo))
    skills = list(repo)
    assert [s.name for s in skills] == ["hello"]


def test_missing_skill(local_repo: Path) -> None:
    repo = SkillRepo(str(local_repo))
    with pytest.raises(FileNotFoundError):
        repo.read("does-not-exist")


def test_memory_backend() -> None:
    import fsspec

    fs = fsspec.filesystem("memory")
    # Ensure clean state across tests in the same process.
    for path in list(fs.store):
        fs.rm(path)

    fs.pipe("/mem-repo/alpha/SKILL.md", b"---\ndescription: alpha skill\n---\nbody\n")
    fs.pipe("/mem-repo/alpha/extra.txt", b"x")
    fs.pipe("/mem-repo/beta/SKILL.md", b"---\ndescription: beta skill\n---\nbody\n")

    repo = SkillRepo("memory:///mem-repo")
    assert repo.list_skills() == ["alpha", "beta"]
    alpha = repo.read("alpha")
    assert alpha.description == "alpha skill"
    assert alpha.list_resources() == ["extra.txt"]
    assert alpha.read_resource("extra.txt") == b"x"


def test_no_frontmatter(tmp_path: Path) -> None:
    skill_dir = tmp_path / "plain"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Just markdown, no frontmatter\n")

    skill = SkillRepo(str(tmp_path)).read("plain")
    assert skill.metadata == {}
    assert skill.description == ""
    assert "Just markdown" in skill.body
