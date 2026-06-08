"""
Return object describing what an orchestrator wrote. The CLI uses it to print artifact
paths and run notes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunResult:
    """
    Result returned by an orchestrator. artifacts maps artifact names to paths, notes
    are CLI messages, trace contains run metadata, and status summarizes the run
    outcome.
    """
    artifacts: dict[str, Path]
    notes: list[str]
    trace: dict[str, Any]
    status: str
