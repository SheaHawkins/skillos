from pathlib import Path

import pytest
from skillos_core import Skill, SkillRepo

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
    assert skill.description is None
    assert "Just markdown" in skill.body


# Tests that exercise Skill directly, independent of SkillRepo.


@pytest.fixture
def mem_fs():
    import fsspec

    fs = fsspec.filesystem("memory")
    for path in list(fs.store):
        fs.rm(path)
    return fs


def test_skill_description_present(mem_fs) -> None:
    skill = Skill(
        name="x",
        metadata={"description": "hello"},
        body="",
        fs=mem_fs,
        root="/x",
    )
    assert skill.description == "hello"


def test_skill_description_missing_is_none(mem_fs) -> None:
    skill = Skill(name="x", metadata={}, body="", fs=mem_fs, root="/x")
    assert skill.description is None


def test_skill_list_resources_excludes_skill_md(mem_fs) -> None:
    mem_fs.pipe("/s/SKILL.md", b"body")
    mem_fs.pipe("/s/a.txt", b"a")
    mem_fs.pipe("/s/nested/b.txt", b"b")

    skill = Skill(name="s", metadata={}, body="", fs=mem_fs, root="/s")
    assert skill.list_resources() == ["a.txt", "nested/b.txt"]


def test_skill_read_resource_nested(mem_fs) -> None:
    mem_fs.pipe("/s/SKILL.md", b"body")
    mem_fs.pipe("/s/nested/deep.txt", b"payload")

    skill = Skill(name="s", metadata={}, body="", fs=mem_fs, root="/s")
    assert skill.read_resource("nested/deep.txt") == b"payload"


def test_skill_read_resource_missing_raises(mem_fs) -> None:
    mem_fs.pipe("/s/SKILL.md", b"body")
    skill = Skill(name="s", metadata={}, body="", fs=mem_fs, root="/s")
    with pytest.raises(FileNotFoundError):
        skill.read_resource("does-not-exist.txt")
