"""Lightweight shared data models used between manifest loading and review stages."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LoadedManifest:
    """
    Manifest loaded from a migration pack, including the pack root, manifest file path,
    and parsed manifest data shared by downstream stages.
    """
    pack_path: Path
    manifest_path: Path
    data: dict[str, Any]


@dataclass(frozen=True)
class FileReference:
    """
    A manifest-declared file reference with category and optional dataset context for
    inventory and coverage checks.
    """
    reference_id: str
    category: str
    path: str
    dataset_id: str | None = None
