from skillos_curator import Change, ChangeKind, Changelog


def test_empty_changelog() -> None:
    cl = Changelog()
    assert cl.applied == []
    assert cl.failed == []


def test_applied_filters_correctly() -> None:
    c1 = Change(kind=ChangeKind.INSERT, name="a", applied=True)
    c2 = Change(kind=ChangeKind.UPDATE, name="b", applied=False, error="boom")
    c3 = Change(kind=ChangeKind.DELETE, name="c", applied=True)
    cl = Changelog(changes=[c1, c2, c3])
    assert cl.applied == [c1, c3]
    assert cl.failed == [c2]


def test_all_failed() -> None:
    changes = [
        Change(kind=ChangeKind.INSERT, name="x", applied=False, error="e1"),
        Change(kind=ChangeKind.DELETE, name="y", applied=False, error="e2"),
    ]
    cl = Changelog(changes=changes)
    assert cl.applied == []
    assert cl.failed == changes


def test_change_defaults() -> None:
    c = Change(kind=ChangeKind.INSERT, name="test")
    assert c.applied is False
    assert c.error is None
    assert c.description is None
    assert c.body is None
    assert c.license is None
    assert c.allowed_tools is None
    assert c.compatibility is None
    assert c.metadata is None
