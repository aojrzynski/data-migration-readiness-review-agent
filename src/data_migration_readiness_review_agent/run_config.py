from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunConfig:
    pack_path: Path
    output_dir: Path
    manifest_path: Path | None
    no_llm: bool
    orchestrator: str
    llm_review: bool
    llm_provider: str
    llm_model: str | None
    llm_max_input_chars: int
