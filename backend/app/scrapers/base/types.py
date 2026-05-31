from dataclasses import dataclass
from typing import Mapping


@dataclass(slots=True)
class RawHttpResponse:
    url: str
    status_code: int
    headers: Mapping[str, str]
    body: bytes
    content_type: str | None = None
