from __future__ import annotations

from pathlib import Path

import pytest
from skillos_core import SkillRepo
from skillos_langchain import create_skill_tools


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


@pytest.fixture
def tools(repo: SkillRepo):
    ts = create_skill_tools(repo)
    return {t.name: t for t in ts}


def test_creates_five_tools(repo: SkillRepo) -> None:
    ts = create_skill_tools(repo)
    names = {t.name for t in ts}
    assert names == {"list_skills", "read_skill", "insert_skill", "update_skill", "delete_skill"}


def test_list_skills_empty(tools) -> None:
    assert tools["list_skills"].invoke({}) == []


def test_insert_and_list(tools) -> None:
    result = tools["insert_skill"].invoke(
        {"name": "hello", "description": "A greeting skill.", "body": "# Hello\n"}
    )
    assert result["name"] == "hello"
    assert result["applied"] is True
    assert tools["list_skills"].invoke({}) == ["hello"]


def test_insert_with_optional_fields(tools, repo: SkillRepo) -> None:
    tools["insert_skill"].invoke(
        {
            "name": "hello",
            "description": "desc",
            "body": "body\n",
            "license": "Apache-2.0",
            "allowed_tools": ["Read", "Bash"],
            "compatibility": "claude-1.x",
            "metadata": {"version": "0.1.0"},
        }
    )
    skill = repo.read("hello")
    assert skill.metadata["license"] == "Apache-2.0"
    assert skill.metadata["allowed-tools"] == ["Read", "Bash"]
    assert skill.metadata["compatibility"] == "claude-1.x"
    assert skill.metadata["metadata"] == {"version": "0.1.0"}


def test_insert_defaults_to_mit(tools, repo: SkillRepo) -> None:
    tools["insert_skill"].invoke({"name": "hello", "description": "desc", "body": "body\n"})
    assert repo.read("hello").metadata["license"] == "MIT"


def test_insert_duplicate_raises(tools) -> None:
    tools["insert_skill"].invoke({"name": "hello", "description": "desc", "body": "body\n"})
    with pytest.raises(FileExistsError):
        tools["insert_skill"].invoke({"name": "hello", "description": "desc", "body": "body\n"})


def test_insert_invalid_name_raises(tools) -> None:
    with pytest.raises(ValueError):
        tools["insert_skill"].invoke({"name": "BAD NAME", "description": "desc", "body": "body\n"})


def test_read_skill(tools) -> None:
    tools["insert_skill"].invoke(
        {"name": "hello", "description": "A greeting.", "body": "# Hello\n"}
    )
    result = tools["read_skill"].invoke({"name": "hello"})
    assert result["name"] == "hello"
    assert result["description"] == "A greeting."
    assert "# Hello" in result["body"]
    assert result["resources"] == []


def test_read_missing_raises(tools) -> None:
    with pytest.raises(FileNotFoundError):
        tools["read_skill"].invoke({"name": "nope"})


def test_update_description(tools, repo: SkillRepo) -> None:
    tools["insert_skill"].invoke({"name": "hello", "description": "v1", "body": "body\n"})
    result = tools["update_skill"].invoke({"name": "hello", "description": "v2"})
    assert result["applied"] is True
    assert repo.read("hello").description == "v2"


def test_update_body(tools, repo: SkillRepo) -> None:
    tools["insert_skill"].invoke({"name": "hello", "description": "desc", "body": "v1 body\n"})
    tools["update_skill"].invoke({"name": "hello", "body": "v2 body\n"})
    assert "v2 body" in repo.read("hello").body


def test_update_leaves_unspecified_fields(tools, repo: SkillRepo) -> None:
    tools["insert_skill"].invoke(
        {"name": "hello", "description": "desc", "body": "body\n", "license": "Apache-2.0"}
    )
    tools["update_skill"].invoke({"name": "hello", "description": "updated"})
    skill = repo.read("hello")
    assert skill.description == "updated"
    assert skill.metadata["license"] == "Apache-2.0"


def test_update_missing_raises(tools) -> None:
    with pytest.raises(FileNotFoundError):
        tools["update_skill"].invoke({"name": "nope", "description": "x"})


def test_delete_skill(tools, repo: SkillRepo) -> None:
    tools["insert_skill"].invoke({"name": "hello", "description": "desc", "body": "body\n"})
    result = tools["delete_skill"].invoke({"name": "hello"})
    assert result == {"name": "hello", "applied": True, "error": None}
    assert "hello" not in repo


def test_delete_missing_raises(tools) -> None:
    with pytest.raises(FileNotFoundError):
        tools["delete_skill"].invoke({"name": "nope"})


def test_tools_have_descriptions(tools) -> None:
    for t in tools.values():
        assert t.description, f"{t.name} missing description"


def test_full_lifecycle(tools, repo: SkillRepo) -> None:
    tools["insert_skill"].invoke({"name": "alpha", "description": "first", "body": "body a\n"})
    tools["insert_skill"].invoke({"name": "beta", "description": "second", "body": "body b\n"})
    assert tools["list_skills"].invoke({}) == ["alpha", "beta"]

    tools["update_skill"].invoke({"name": "alpha", "description": "updated first"})
    assert repo.read("alpha").description == "updated first"

    tools["delete_skill"].invoke({"name": "beta"})
    assert tools["list_skills"].invoke({}) == ["alpha"]

    result = tools["read_skill"].invoke({"name": "alpha"})
    assert result["description"] == "updated first"
