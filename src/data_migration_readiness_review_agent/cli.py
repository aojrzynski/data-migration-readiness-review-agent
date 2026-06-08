from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.artifacts import (
    INVENTORY_FILE_NAME,
    TRACE_FILE_NAME,
    write_json_artifact,
)
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.inventory import INVENTORY_NOTE, build_inventory
from data_migration_readiness_review_agent.manifest import ManifestError, load_manifest

TRACE_NOTE = (
    "PR #2 performed manifest and file inventory only. No profiling, reconciliation, LLM "
    "review, or readiness assessment was performed."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-migration-readiness-review",
        description="Inventory evidence referenced by a local migration pack manifest.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--pack",
        type=Path,
        help="Path to a local migration pack directory.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional manifest path. Relative paths are resolved inside the migration pack.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where inventory artifacts should be written.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Record that no LLM review should be used for this run.",
    )
    parser.add_argument(
        "--orchestrator",
        choices=["standard"],
        default="standard",
        help="Orchestrator mode to record. PR #2 only supports 'standard'.",
    )
    return parser


def validate_pack_path(parser: argparse.ArgumentParser, pack_path: Path | None) -> Path:
    if pack_path is None:
        parser.error("--pack is required unless --version is used")
    resolved_pack_path = pack_path.expanduser().resolve()
    if not resolved_pack_path.is_dir():
        parser.error(f"--pack must point to an existing directory: {pack_path}")
    return resolved_pack_path


def validate_output_dir(output_dir: Path | None) -> Path:
    if output_dir is None:
        return Path("outputs").resolve()
    return output_dir.expanduser().resolve()


def build_trace(
    *,
    pack_path: Path,
    output_dir: Path,
    manifest_path: Path,
    no_llm: bool,
    orchestrator: str,
    inventory_counts: dict[str, int],
) -> dict[str, Any]:
    return {
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "pack_path": str(pack_path),
        "output_directory": str(output_dir),
        "manifest_path": str(manifest_path),
        "no_llm": no_llm,
        "orchestrator": orchestrator,
        "status": "inventory_created",
        "artifacts_written": [INVENTORY_FILE_NAME, TRACE_FILE_NAME],
        "counts": inventory_counts,
        "note": TRACE_NOTE,
    }


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> tuple[Path, Path]:
    pack_path = validate_pack_path(parser, args.pack)
    output_dir = validate_output_dir(args.output_dir)
    try:
        loaded_manifest = load_manifest(pack_path, args.manifest)
        inventory = build_inventory(loaded_manifest)
    except ManifestError as exc:
        parser.error(str(exc))

    inventory_path = write_json_artifact(inventory, output_dir, INVENTORY_FILE_NAME)
    trace = build_trace(
        pack_path=pack_path,
        output_dir=output_dir,
        manifest_path=loaded_manifest.manifest_path,
        no_llm=args.no_llm,
        orchestrator=args.orchestrator,
        inventory_counts=inventory["counts"],
    )
    trace_path = write_json_artifact(trace, output_dir, TRACE_FILE_NAME)
    return inventory_path, trace_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    inventory_path, trace_path = run(args, parser)
    print(f"Wrote migration inventory: {inventory_path}")
    print(f"Wrote migration trace: {trace_path}")
    print(INVENTORY_NOTE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
