from pathlib import Path

import pytest
from skillos_core import License, SkillRepo
from skillos_core.repo import DESCRIPTION_MAX_LEN, NAME_MAX_LEN


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


def test_insert_writes_required_frontmatter_and_default_license(
    repo: SkillRepo, tmp_path: Path
) -> None:
    skill = repo.insert("hello", "A greeting skill.", "# Hello\n\nbody\n")

    assert skill.name == "hello"
    assert skill.description == "A greeting skill."
    assert skill.metadata["name"] == "hello"
    assert skill.metadata["license"] == "MIT"
    assert "# Hello" in skill.body

    on_disk = (tmp_path / "hello" / "SKILL.md").read_text()
    assert on_disk.startswith("---\n")
    assert "name: hello" in on_disk
    assert "description: A greeting skill." in on_disk
    assert "license: MIT" in on_disk


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


@pytest.mark.parametrize("bad_description", ["", "   "])
def test_insert_rejects_invalid_description(repo: SkillRepo, bad_description: str) -> None:
    with pytest.raises(ValueError):
        repo.insert("hello", bad_description, "body\n")


def test_is_name_taken(repo: SkillRepo) -> None:
    assert repo.is_name_taken("hello") is False
    repo.insert("hello", "desc", "body\n")
    assert repo.is_name_taken("hello") is True
    assert repo.is_name_taken("other") is False

    # __contains__ matches
    assert "hello" in repo
    assert "other" not in repo

    repo.delete("hello")
    assert repo.is_name_taken("hello") is False


def test_insert_rejects_oversize_description(repo: SkillRepo) -> None:
    with pytest.raises(ValueError):
        repo.insert("hello", "x" * (DESCRIPTION_MAX_LEN + 1), "body\n")


def test_insert_preserves_bundled_resources(repo: SkillRepo, tmp_path: Path) -> None:
    repo.insert("hello", "desc", "body\n")
    (tmp_path / "hello" / "script.py").write_text("print('hi')\n")
    skill = repo.read("hello")
    assert skill.list_resources() == ["script.py"]
    assert skill.read_resource("script.py") == b"print('hi')\n"


def test_insert_with_license_enum_member(repo: SkillRepo) -> None:
    skill = repo.insert("hello", "desc", "body\n", license=License.APACHE_2_0)
    assert skill.metadata["license"] == "Apache-2.0"


def test_insert_with_license_spdx_string(repo: SkillRepo) -> None:
    skill = repo.insert("hello", "desc", "body\n", license="GPL-3.0")
    assert skill.metadata["license"] == "GPL-3.0"


def test_insert_rejects_unknown_license(repo: SkillRepo) -> None:
    with pytest.raises(ValueError):
        repo.insert("hello", "desc", "body\n", license="MyCustomLicense-9.9")


def test_insert_with_allowed_tools_serializes_with_hyphen(repo: SkillRepo, tmp_path: Path) -> None:
    skill = repo.insert("hello", "desc", "body\n", allowed_tools=["Read", "Bash"])
    assert skill.metadata["allowed-tools"] == ["Read", "Bash"]
    on_disk = (tmp_path / "hello" / "SKILL.md").read_text()
    assert "allowed-tools:" in on_disk
    assert "allowed_tools" not in on_disk


def test_insert_with_compatibility(repo: SkillRepo) -> None:
    skill = repo.insert("hello", "desc", "body\n", compatibility="claude-1.x")
    assert skill.metadata["compatibility"] == "claude-1.x"


def test_insert_with_nested_metadata_field(repo: SkillRepo) -> None:
    skill = repo.insert("hello", "desc", "body\n", metadata={"version": "1.2.3", "author": "shea"})
    assert skill.metadata["metadata"] == {"version": "1.2.3", "author": "shea"}


def test_insert_body_is_unvalidated_freeform(repo: SkillRepo) -> None:
    weird = "anything goes here -- emoji 🚀 and <tags> and ---\nmid-document\n"
    skill = repo.insert("hello", "desc", weird)
    assert weird.rstrip("\n") in skill.body


def test_update_changes_description(repo: SkillRepo) -> None:
    repo.insert("hello", "v1 desc", "body\n", license=License.MIT)
    updated = repo.update("hello", description="v2 desc")
    assert updated.description == "v2 desc"
    assert updated.metadata["license"] == "MIT"


def test_update_body_only_leaves_frontmatter_intact(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "v1 body\n", license=License.APACHE_2_0)
    updated = repo.update("hello", body="v2 body\n")
    assert "v2 body" in updated.body
    assert updated.description == "desc"
    assert updated.metadata["license"] == "Apache-2.0"


def test_update_changes_license(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")  # defaults to MIT
    updated = repo.update("hello", license=License.GPL_3_0)
    assert updated.metadata["license"] == "GPL-3.0"


def test_update_changes_allowed_tools_compatibility_and_metadata(
    repo: SkillRepo,
) -> None:
    repo.insert("hello", "desc", "body\n")
    updated = repo.update(
        "hello",
        allowed_tools=["Read"],
        compatibility="claude-2.x",
        metadata={"version": "0.1.0"},
    )
    assert updated.metadata["allowed-tools"] == ["Read"]
    assert updated.metadata["compatibility"] == "claude-2.x"
    assert updated.metadata["metadata"] == {"version": "0.1.0"}


def test_update_unspecified_fields_remain_unchanged(repo: SkillRepo) -> None:
    repo.insert(
        "hello",
        "desc",
        "body\n",
        license=License.BSD_3_CLAUSE,
        allowed_tools=["Read"],
        compatibility="claude-1.x",
        metadata={"version": "0.1.0"},
    )
    updated = repo.update("hello", description="updated desc")
    assert updated.description == "updated desc"
    assert updated.metadata["license"] == "BSD-3-Clause"
    assert updated.metadata["allowed-tools"] == ["Read"]
    assert updated.metadata["compatibility"] == "claude-1.x"
    assert updated.metadata["metadata"] == {"version": "0.1.0"}


def test_update_rejects_empty_description(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    with pytest.raises(ValueError):
        repo.update("hello", description="")


def test_update_rejects_unknown_license(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    with pytest.raises(ValueError):
        repo.update("hello", license="MyCustomLicense-9.9")


def test_update_keeps_name_aligned_with_directory(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")
    updated = repo.update("hello", description="still hello")
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
    repo.insert(
        "alpha",
        "alpha skill",
        "alpha body\n",
        license=License.APACHE_2_0,
        compatibility="claude-1.x",
        metadata={"version": "0.1.0"},
    )
    repo.insert("beta", "beta skill", "beta body\n")

    assert repo.list_skills() == ["alpha", "beta"]
    alpha = repo.read("alpha")
    assert alpha.description == "alpha skill"
    assert alpha.metadata["license"] == "Apache-2.0"
    assert alpha.metadata["compatibility"] == "claude-1.x"
    assert alpha.metadata["metadata"] == {"version": "0.1.0"}
    assert "alpha body" in alpha.body
