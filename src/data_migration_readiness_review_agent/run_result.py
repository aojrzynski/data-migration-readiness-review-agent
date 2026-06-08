from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunResult:
    artifacts: dict[str, Path]
    notes: list[str]
    trace: dict[str, Any]
    status: str
