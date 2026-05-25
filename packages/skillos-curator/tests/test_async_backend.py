from __future__ import annotations

from pathlib import Path

import pytest
from skillos_core import License, SkillRepo
from skillos_curator import Change, ChangeKind, Changelog, Trace
from skillos_curator.backends import AsyncCurator


@pytest.fixture
def repo(tmp_path: Path) -> SkillRepo:
    return SkillRepo(str(tmp_path))


def _make_trace() -> Trace:
    return Trace(trace_id="test-trace", spans=[])


@pytest.mark.asyncio
async def test_insert_applies(repo: SkillRepo) -> None:
    async def analyze(trace: Trace) -> Changelog:
        return Changelog(
            changes=[
                Change(
                    kind=ChangeKind.INSERT,
                    name="hello",
                    description="A greeting skill.",
                    body="# Hello\n",
                ),
            ]
        )

    curator = AsyncCurator(repo, analyze=analyze)
    cl = await curator.curate(_make_trace())

    assert len(cl.applied) == 1
    assert cl.applied[0].name == "hello"
    assert cl.applied[0].applied is True
    assert "hello" in repo
    assert repo.read("hello").description == "A greeting skill."


@pytest.mark.asyncio
async def test_insert_with_optional_fields(repo: SkillRepo) -> None:
    async def analyze(trace: Trace) -> Changelog:
        return Changelog(
            changes=[
                Change(
                    kind=ChangeKind.INSERT,
                    name="hello",
                    description="A greeting skill.",
                    body="# Hello\n",
                    license=License.APACHE_2_0,
                    allowed_tools=["Read"],
                    compatibility="claude-1.x",
                    metadata={"version": "0.1.0"},
                ),
            ]
        )

    curator = AsyncCurator(repo, analyze=analyze)
    cl = await curator.curate(_make_trace())

    assert len(cl.applied) == 1
    skill = repo.read("hello")
    assert skill.metadata["license"] == "Apache-2.0"
    assert skill.metadata["allowed-tools"] == ["Read"]
    assert skill.metadata["compatibility"] == "claude-1.x"
    assert skill.metadata["metadata"] == {"version": "0.1.0"}


@pytest.mark.asyncio
async def test_update_applies(repo: SkillRepo) -> None:
    repo.insert("hello", "v1", "old body\n")

    async def analyze(trace: Trace) -> Changelog:
        return Changelog(
            changes=[
                Change(kind=ChangeKind.UPDATE, name="hello", body="new body\n"),
            ]
        )

    curator = AsyncCurator(repo, analyze=analyze)
    cl = await curator.curate(_make_trace())

    assert len(cl.applied) == 1
    assert "new body" in repo.read("hello").body


@pytest.mark.asyncio
async def test_delete_applies(repo: SkillRepo) -> None:
    repo.insert("hello", "desc", "body\n")

    async def analyze(trace: Trace) -> Changelog:
        return Changelog(
            changes=[
                Change(kind=ChangeKind.DELETE, name="hello"),
            ]
        )

    curator = AsyncCurator(repo, analyze=analyze)
    cl = await curator.curate(_make_trace())

    assert len(cl.applied) == 1
    assert "hello" not in repo


@pytest.mark.asyncio
async def test_failed_change_records_error(repo: SkillRepo) -> None:
    async def analyze(trace: Trace) -> Changelog:
        return Changelog(
            changes=[
                Change(kind=ChangeKind.DELETE, name="nonexistent"),
            ]
        )

    curator = AsyncCurator(repo, analyze=analyze)
    cl = await curator.curate(_make_trace())

    assert len(cl.failed) == 1
    assert cl.failed[0].applied is False
    assert cl.failed[0].error is not None
    assert "nonexistent" in cl.failed[0].error


@pytest.mark.asyncio
async def test_mixed_success_and_failure(repo: SkillRepo) -> None:
    async def analyze(trace: Trace) -> Changelog:
        return Changelog(
            changes=[
                Change(
                    kind=ChangeKind.INSERT,
                    name="good",
                    description="works",
                    body="body\n",
                ),
                Change(kind=ChangeKind.DELETE, name="missing"),
            ]
        )

    curator = AsyncCurator(repo, analyze=analyze)
    cl = await curator.curate(_make_trace())

    assert len(cl.applied) == 1
    assert len(cl.failed) == 1
    assert cl.applied[0].name == "good"
    assert cl.failed[0].name == "missing"
    assert "good" in repo


@pytest.mark.asyncio
async def test_insert_without_description_fails_validation(repo: SkillRepo) -> None:
    async def analyze(trace: Trace) -> Changelog:
        return Changelog(
            changes=[
                Change(kind=ChangeKind.INSERT, name="bad", body="body\n"),
            ]
        )

    curator = AsyncCurator(repo, analyze=analyze)
    cl = await curator.curate(_make_trace())

    assert len(cl.failed) == 1
    assert "bad" not in repo
