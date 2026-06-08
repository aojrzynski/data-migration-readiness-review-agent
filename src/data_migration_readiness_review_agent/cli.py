from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent import __version__

TOOL_NAME = "Data Migration Readiness Review Agent"
TRACE_FILE_NAME = "migration_readiness_trace.json"
SCAFFOLD_NOTE = (
    "PR #1 scaffold only: this run does not perform manifest intake, dataset profiling, "
    "mapping review, contract review, reconciliation, sensitive-field detection, LLM review, "
    "LangGraph orchestration, or readiness assessment. Human review is still required."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-migration-readiness-review",
        description="Write a local scaffold trace for a migration review pack.",
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
        "--output-dir",
        type=Path,
        help="Directory where scaffold artifacts should be written.",
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
        help="Orchestrator mode to record. PR #1 only supports 'standard'.",
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
    no_llm: bool,
    orchestrator: str,
) -> dict[str, Any]:
    return {
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "pack_path": str(pack_path),
        "output_directory": str(output_dir),
        "no_llm": no_llm,
        "orchestrator": orchestrator,
        "status": "scaffold_trace_written",
        "note": SCAFFOLD_NOTE,
    }


def write_trace(trace: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / TRACE_FILE_NAME
    trace_path.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return trace_path


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> Path:
    pack_path = validate_pack_path(parser, args.pack)
    output_dir = validate_output_dir(args.output_dir)
    trace = build_trace(
        pack_path=pack_path,
        output_dir=output_dir,
        no_llm=args.no_llm,
        orchestrator=args.orchestrator,
    )
    return write_trace(trace, output_dir)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    trace_path = run(args, parser)
    print(f"Wrote scaffold trace: {trace_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
