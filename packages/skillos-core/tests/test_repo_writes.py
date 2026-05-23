from pathlib import Path

import pytest
from skillos_core import SkillRepo
from skillos_core.repo import DESCRIPTION_MAX_LEN, NAME_MAX_LEN


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


def test_insert_creates_skill_with_required_frontmatter(repo: SkillRepo, tmp_path: Path) -> None:
    skill = repo.insert("hello", "A greeting skill.", "# Hello\n\nbody\n")

    assert skill.name == "hello"
    assert skill.description == "A greeting skill."
    assert skill.metadata["name"] == "hello"
    assert "# Hello" in skill.body
    assert "hello" in repo

    on_disk = (tmp_path / "hello" / "SKILL.md").read_text()
    assert on_disk.startswith("---\n")
    assert "name: hello" in on_disk
    assert "description: A greeting skill." in on_disk


def test_insert_merges_extra_metadata_but_preserves_required_fields(
    repo: SkillRepo,
) -> None:
    skill = repo.insert(
        "hello",
        "A greeting skill.",
        "body\n",
        metadata={"license": "MIT", "allowed-tools": ["Read"], "name": "ignored"},
    )
    assert skill.metadata["name"] == "hello"
    assert skill.metadata["description"] == "A greeting skill."
    assert skill.metadata["license"] == "MIT"
    assert skill.metadata["allowed-tools"] == ["Read"]


def test_insert_rejects_duplicate(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    with pytest.raises(FileExistsError):
        repo.insert("hello", "desc", "body\n")


@pytest.mark.parametrize(
    "bad_name",
    [
        "",
        "Hello",
        "hello_world",
        "hello world",
        "hello.world",
        "x" * (NAME_MAX_LEN + 1),
        "anthropic",
        "claude",
    ],
)
def test_insert_rejects_invalid_name(repo: SkillRepo, bad_name: str) -> None:
    with pytest.raises(ValueError):
        repo.insert(bad_name, "desc", "body\n")


def test_insert_accepts_name_at_max_length(repo: SkillRepo) -> None:
    name = "a" * NAME_MAX_LEN
    repo.insert(name, "desc", "body\n")
    assert name in repo


@pytest.mark.parametrize("bad_description", ["", "   ", None, 123])
def test_insert_rejects_invalid_description(repo: SkillRepo, bad_description) -> None:
    with pytest.raises(ValueError):
        repo.insert("hello", bad_description, "body\n")


def test_insert_rejects_oversize_description(repo: SkillRepo) -> None:
    with pytest.raises(ValueError):
        repo.insert("hello", "x" * (DESCRIPTION_MAX_LEN + 1), "body\n")


def test_insert_preserves_bundled_resources(repo: SkillRepo, tmp_path: Path) -> None:
    repo.insert("hello", "desc", "body\n")
    (tmp_path / "hello" / "script.py").write_text("print('hi')\n")
    skill = repo.read("hello")
    assert skill.list_resources() == ["script.py"]
    assert skill.read_resource("script.py") == b"print('hi')\n"


def test_update_changes_description(repo: SkillRepo) -> None:
    repo.insert("hello", "v1 desc", "body\n", metadata={"license": "MIT"})
    updated = repo.update("hello", description="v2 desc")
    assert updated.description == "v2 desc"
    assert updated.metadata["license"] == "MIT"
    assert "body" in updated.body


def test_update_body_only_leaves_metadata_intact(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "v1 body\n", metadata={"license": "MIT"})
    updated = repo.update("hello", body="v2 body\n")
    assert "v2 body" in updated.body
    assert updated.description == "desc"
    assert updated.metadata["license"] == "MIT"


def test_update_merges_metadata(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n", metadata={"license": "MIT"})
    updated = repo.update("hello", metadata={"allowed-tools": ["Read"]})
    assert updated.metadata["license"] == "MIT"
    assert updated.metadata["allowed-tools"] == ["Read"]


def test_update_can_drop_key_with_none(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n", metadata={"license": "MIT"})
    updated = repo.update("hello", metadata={"license": None})
    assert "license" not in updated.metadata
    assert updated.description == "desc"


def test_update_rejects_empty_description(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    with pytest.raises(ValueError):
        repo.update("hello", description="")


def test_update_keeps_name_aligned_with_directory(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    updated = repo.update("hello", metadata={"name": "tampered"})
    assert updated.metadata["name"] == "hello"


def test_update_missing_raises(repo: SkillRepo) -> None:
    with pytest.raises(FileNotFoundError):
        repo.update("nope", description="x")


def test_delete_removes_skill_and_resources(repo: SkillRepo, tmp_path: Path) -> None:
    repo.insert("hello", "desc", "body\n")
    (tmp_path / "hello" / "extra.txt").write_text("e")
    assert "hello" in repo

    repo.delete("hello")
    assert "hello" not in repo
    assert not (tmp_path / "hello").exists()


def test_delete_missing_raises(repo: SkillRepo) -> None:
    with pytest.raises(FileNotFoundError):
        repo.delete("nope")


def test_write_then_read_roundtrip_via_memory_backend() -> None:
    import fsspec

    fs = fsspec.filesystem("memory")
    for path in list(fs.store):
        fs.rm(path)

    repo = SkillRepo("memory:///write-roundtrip")
    repo.insert("alpha", "alpha skill", "alpha body\n", metadata={"license": "MIT"})
    repo.insert("beta", "beta skill", "beta body\n")

    assert repo.list_skills() == ["alpha", "beta"]
    alpha = repo.read("alpha")
    assert alpha.description == "alpha skill"
    assert alpha.metadata["license"] == "MIT"
    assert "alpha body" in alpha.body
