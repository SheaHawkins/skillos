import fsspec
import pytest
from skillos_core import Skill


@pytest.fixture
def mem_fs():
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
