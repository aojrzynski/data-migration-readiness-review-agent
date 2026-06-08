"""
Run configuration passed from the thin CLI layer into an orchestrator. It carries parsed
choices without adding workflow behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunConfig:
    """
    Parsed CLI choices for one run. pack_path is the local migration pack, output_dir is
    where artifacts are written, manifest_path optionally selects a manifest, no_llm and
    llm_review control optional notes, orchestrator selects standard or LangGraph
    coordination, and llm_provider, llm_model, and llm_max_input_chars bound any
    optional LLM call.
    """
    pack_path: Path
    output_dir: Path
    manifest_path: Path | None
    no_llm: bool
    orchestrator: str
    llm_review: bool
    llm_provider: str
    llm_model: str | None
    llm_max_input_chars: int
