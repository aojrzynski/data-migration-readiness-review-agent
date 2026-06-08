"""
Command-line entry point. The CLI stays thin: it parses arguments, validates simple
constraints, builds RunConfig, dispatches an orchestrator, and prints written artifacts
and notes.
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.artifact_registry import (
    CONTRACT_REVIEW_FILE_NAME,
    DATASET_PROFILES_FILE_NAME,
    EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
    INVENTORY_FILE_NAME,
    LLM_REVIEWER_NOTES_FILE_NAME,
    MAPPING_REVIEW_FILE_NAME,
    ORDERED_ARTIFACT_FILE_NAMES,
    RECONCILIATION_RESULTS_FILE_NAME,
    REVIEW_PACK_FILE_NAME,
    REVIEWER_SUMMARY_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    SENSITIVE_FIELD_REVIEW_FILE_NAME,
    TEST_EVIDENCE_REVIEW_FILE_NAME,
    TRACE_FILE_NAME,
)
from data_migration_readiness_review_agent.manifest import ManifestError
from data_migration_readiness_review_agent.orchestrators.langgraph import (
    LangGraphDependencyError,
    run_langgraph_review,
)
from data_migration_readiness_review_agent.orchestrators.standard import run_standard_review
from data_migration_readiness_review_agent.run_config import RunConfig
from data_migration_readiness_review_agent.run_result import RunResult

ARTIFACT_PRINT_LABELS = {
    INVENTORY_FILE_NAME: "migration inventory",
    DATASET_PROFILES_FILE_NAME: "dataset profiles",
    SCHEMA_INVENTORY_FILE_NAME: "schema inventory",
    MAPPING_REVIEW_FILE_NAME: "mapping review",
    CONTRACT_REVIEW_FILE_NAME: "contract review",
    RECONCILIATION_RESULTS_FILE_NAME: "reconciliation results",
    SENSITIVE_FIELD_REVIEW_FILE_NAME: "sensitive field review",
    TEST_EVIDENCE_REVIEW_FILE_NAME: "test evidence review",
    EVIDENCE_COVERAGE_REVIEW_FILE_NAME: "evidence coverage review",
    REVIEW_PACK_FILE_NAME: "review pack",
    REVIEWER_SUMMARY_FILE_NAME: "reviewer summary",
    LLM_REVIEWER_NOTES_FILE_NAME: "LLM reviewer notes",
    TRACE_FILE_NAME: "migration trace",
}


def build_parser() -> argparse.ArgumentParser:
    """
    Create the CLI argument parser without running the workflow. The parser defines
    flags but does not inspect pack contents.
    """
    parser = argparse.ArgumentParser(
        prog="data-migration-readiness-review",
        description="Inventory and profile evidence referenced by a local migration pack manifest.",
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
        "--llm-review",
        action="store_true",
        help="Explicitly request optional supplemental LLM reviewer notes.",
    )
    parser.add_argument(
        "--llm-provider",
        choices=["openai"],
        default="openai",
        help=(
            "LLM provider to use when --llm-review is provided. "
            "The optional LLM reviewer currently supports openai only."
        ),
    )
    parser.add_argument(
        "--llm-model",
        help="Model name used for optional LLM reviewer notes.",
    )
    parser.add_argument(
        "--llm-max-input-chars",
        type=int,
        default=20000,
        help="Maximum serialized review-pack context characters sent to the optional LLM.",
    )
    parser.add_argument(
        "--orchestrator",
        choices=["standard", "langgraph"],
        default="standard",
        help=(
            "Orchestrator mode to use. The deterministic standard workflow is the default; "
            "the optional langgraph workflow requires the graph extra."
        ),
    )
    return parser


def validate_pack_path(parser: argparse.ArgumentParser, pack_path: Path | None) -> Path:
    """
    Resolve and validate the migration pack directory supplied by the CLI. This keeps
    the workflow anchored to a local directory.
    """
    if pack_path is None:
        parser.error("--pack is required unless --version is used")
    resolved_pack_path = pack_path.expanduser().resolve()
    if not resolved_pack_path.is_dir():
        parser.error(f"--pack must point to an existing directory: {pack_path}")
    return resolved_pack_path


def validate_output_dir(output_dir: Path | None) -> Path:
    """
    Resolve the output directory for local artifacts. The directory may be created later
    by artifact writers.
    """
    if output_dir is None:
        return Path("outputs").resolve()
    return output_dir.expanduser().resolve()


def build_run_config(args: argparse.Namespace, parser: argparse.ArgumentParser) -> RunConfig:
    """
    Convert parsed CLI arguments into RunConfig after checking simple CLI-only
    constraints such as conflicting LLM flags and input caps.
    """
    # These flags describe opposite LLM choices, so reject the pair before any work starts.
    if args.no_llm and args.llm_review:
        parser.error("--no-llm cannot be used with --llm-review")
    # The LLM context cap must be positive so prompt construction can always make progress.
    if args.llm_max_input_chars < 1:
        parser.error("--llm-max-input-chars must be a positive integer")
    return RunConfig(
        pack_path=validate_pack_path(parser, args.pack),
        output_dir=validate_output_dir(args.output_dir),
        manifest_path=args.manifest,
        no_llm=args.no_llm,
        orchestrator=args.orchestrator,
        llm_review=args.llm_review,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_max_input_chars=args.llm_max_input_chars,
    )


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> RunResult:
    """
    Dispatch a validated RunConfig to the selected orchestrator and surface workflow
    setup errors as CLI errors.
    """
    config = build_run_config(args, parser)
    try:
        # Standard and LangGraph modes choose orchestration only; artifact meaning stays the same.
        if config.orchestrator == "standard":
            return run_standard_review(config)
        if config.orchestrator == "langgraph":
            return run_langgraph_review(config)
    except LangGraphDependencyError as exc:
        # Missing optional graph support is a setup problem, so show it as a clear CLI error.
        parser.error(str(exc))
    except ManifestError as exc:
        # Manifest problems are user-actionable and should not produce a Python traceback.
        parser.error(str(exc))
    parser.error(f"Unsupported orchestrator: {config.orchestrator}")


def main(argv: Sequence[str] | None = None) -> int:
    """
    CLI entry point used by the console script. It runs the workflow and prints
    artifacts in registry order.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run(args, parser)
    for file_name in ORDERED_ARTIFACT_FILE_NAMES:
        print(f"Wrote {ARTIFACT_PRINT_LABELS[file_name]}: {result.artifacts[file_name]}")
    for note in result.notes:
        print(note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
