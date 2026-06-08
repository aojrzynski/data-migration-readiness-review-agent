from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LoadedManifest:
    pack_path: Path
    manifest_path: Path
    data: dict[str, Any]


@dataclass(frozen=True)
class FileReference:
    reference_id: str
    category: str
    path: str
    dataset_id: str | None = None
