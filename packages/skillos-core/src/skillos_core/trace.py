from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from opentelemetry.sdk.trace import ReadableSpan


@dataclass
class Trace:
    trace_id: str
    spans: Sequence[ReadableSpan]
