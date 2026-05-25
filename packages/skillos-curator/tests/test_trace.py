from opentelemetry.sdk.trace import TracerProvider
from skillos_curator import Trace


def _make_span(name: str):
    provider = TracerProvider()
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span(name) as span:
        pass
    return span


def test_trace_holds_spans() -> None:
    s1 = _make_span("op-a")
    s2 = _make_span("op-b")
    t = Trace(trace_id="abc123", spans=[s1, s2])
    assert t.trace_id == "abc123"
    assert len(t.spans) == 2


def test_trace_empty_spans() -> None:
    t = Trace(trace_id="empty", spans=[])
    assert t.spans == []
