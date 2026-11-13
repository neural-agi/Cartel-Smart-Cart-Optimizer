"""Small dependency-free metrics registry with bounded labels."""
from __future__ import annotations

import re
from collections import defaultdict
from threading import Lock

_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}")
_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?![A-Za-z])")


def normalized_route(path: str) -> str:
    return _NUMBER.sub(":n", _UUID.sub(":id", path or "/"))[:256]


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = defaultdict(int)
        self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = defaultdict(list)

    def inc(self, name: str, **labels: str | int) -> None:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        with self._lock:
            self._counters[key] += 1

    def observe(self, name: str, value: float, **labels: str | int) -> None:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        with self._lock:
            if len(self._histograms[key]) < 2000:
                self._histograms[key].append(value)

    def prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            for (name, labels), value in sorted(self._counters.items()):
                lines.append(f"{name}{_format_labels(labels)} {value}")
            for (name, labels), values in sorted(self._histograms.items()):
                if values:
                    lines.extend((f"{name}_count{_format_labels(labels)} {len(values)}", f"{name}_sum{_format_labels(labels)} {sum(values):.6f}"))
        return "\n".join(lines) + ("\n" if lines else "")


def _format_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    values = (f'{key}="{value.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"' for key, value in labels)
    return "{" + ",".join(values) + "}"


metrics = Metrics()
