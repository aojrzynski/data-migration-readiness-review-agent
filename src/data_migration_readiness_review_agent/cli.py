from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.artifacts import (
    CONTRACT_REVIEW_FILE_NAME,
    DATASET_PROFILES_FILE_NAME,
    EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
    INVENTORY_FILE_NAME,
    LLM_REVIEWER_NOTES_FILE_NAME,
    MAPPING_REVIEW_FILE_NAME,
    RECONCILIATION_RESULTS_FILE_NAME,
    REVIEW_PACK_FILE_NAME,
    REVIEWER_SUMMARY_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    SENSITIVE_FIELD_REVIEW_FILE_NAME,
    TEST_EVIDENCE_REVIEW_FILE_NAME,
    TRACE_FILE_NAME,
    write_json_artifact,
)
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.contract_review import (
    CONTRACT_REVIEW_NOTE,
    build_contract_review,
)
from data_migration_readiness_review_agent.csv_profile import PROFILE_NOTE, build_dataset_profiles
from data_migration_readiness_review_agent.evidence_coverage import (
    EVIDENCE_COVERAGE_REVIEW_NOTE,
    build_evidence_coverage_review,
)
from data_migration_readiness_review_agent.inventory import INVENTORY_NOTE, build_inventory
from data_migration_readiness_review_agent.llm_review import (
    LLM_REVIEW_NOTE,
    build_llm_reviewer_notes,
)
from data_migration_readiness_review_agent.manifest import ManifestError, load_manifest
from data_migration_readiness_review_agent.mapping_review import (
    MAPPING_REVIEW_NOTE,
    build_mapping_review,
)
from data_migration_readiness_review_agent.reconciliation import (
    RECONCILIATION_NOTE,
    build_reconciliation_results,
)
from data_migration_readiness_review_agent.review_pack import REVIEW_PACK_NOTE, build_review_pack
from data_migration_readiness_review_agent.reviewer_summary import (
    REVIEWER_SUMMARY_NOTE,
    write_reviewer_summary,
)
from data_migration_readiness_review_agent.schema_inventory import (
    SCHEMA_INVENTORY_NOTE,
    build_schema_inventory,
    build_schema_summary,
)
from data_migration_readiness_review_agent.sensitive_fields import (
    SENSITIVE_FIELD_REVIEW_NOTE,
    build_sensitive_field_review,
)
from data_migration_readiness_review_agent.test_evidence import (
    TEST_EVIDENCE_REVIEW_NOTE,
    build_test_evidence_review,
)

TRACE_NOTE = (
    "PR #9 creates deterministic review artifacts and an optional supplemental LLM notes "
    "artifact. It does not assess readiness, score dimensions, approve migration, decide "
    "go-live, certify legal/privacy/compliance status, or replace human review."
)


ArtifactPaths = tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path]


def build_parser() -> argparse.ArgumentParser:
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
        help="LLM provider to use when --llm-review is provided. PR #9 supports openai only.",
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
        choices=["standard"],
        default="standard",
        help=(
            "Orchestrator mode to record. The deterministic local workflow "
            "currently supports 'standard'."
        ),
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


def build_dataset_profile_summary(dataset_profiles: dict[str, Any]) -> dict[str, int]:
    datasets = dataset_profiles["datasets"]
    expected_files = len(datasets) * 2
    profiled_files = 0
    files_with_gaps = 0
    for dataset in datasets:
        for side in (dataset["source"], dataset["target"]):
            if side["status"] == "profile_created":
                profiled_files += 1
            else:
                files_with_gaps += 1
    return {
        "datasets_profiled": len(datasets),
        "dataset_files_expected": expected_files,
        "dataset_files_profiled": profiled_files,
        "dataset_files_with_gaps": files_with_gaps,
    }


def build_trace(
    *,
    pack_path: Path,
    output_dir: Path,
    manifest_path: Path,
    no_llm: bool,
    orchestrator: str,
    inventory_counts: dict[str, int],
    dataset_profile_summary: dict[str, int],
    schema_inventory_summary: dict[str, int],
    mapping_review_summary: dict[str, int],
    contract_review_summary: dict[str, int],
    reconciliation_summary: dict[str, int],
    sensitive_field_summary: dict[str, int],
    test_evidence_summary: dict[str, int],
    evidence_coverage_summary: dict[str, int],
    review_pack_summary: dict[str, int],
    reviewer_summary_path: Path,
    llm_review_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "pack_path": str(pack_path),
        "output_directory": str(output_dir),
        "manifest_path": str(manifest_path),
        "no_llm": no_llm,
        "orchestrator": orchestrator,
        "status": "review_summary_artifacts_created",
        "artifacts_written": [
            INVENTORY_FILE_NAME,
            DATASET_PROFILES_FILE_NAME,
            SCHEMA_INVENTORY_FILE_NAME,
            MAPPING_REVIEW_FILE_NAME,
            CONTRACT_REVIEW_FILE_NAME,
            RECONCILIATION_RESULTS_FILE_NAME,
            SENSITIVE_FIELD_REVIEW_FILE_NAME,
            TEST_EVIDENCE_REVIEW_FILE_NAME,
            EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
            REVIEW_PACK_FILE_NAME,
            REVIEWER_SUMMARY_FILE_NAME,
            LLM_REVIEWER_NOTES_FILE_NAME,
            TRACE_FILE_NAME,
        ],
        "counts": inventory_counts,
        "dataset_profile_summary": dataset_profile_summary,
        "schema_inventory_summary": schema_inventory_summary,
        "mapping_review_summary": mapping_review_summary,
        "contract_review_summary": contract_review_summary,
        "reconciliation_summary": reconciliation_summary,
        "sensitive_field_summary": sensitive_field_summary,
        "test_evidence_summary": test_evidence_summary,
        "evidence_coverage_summary": evidence_coverage_summary,
        "review_pack_summary": review_pack_summary,
        "reviewer_summary_path": str(reviewer_summary_path),
        "reviewer_summary_written": True,
        "llm_review_summary": llm_review_summary,
        "notes": [
            INVENTORY_NOTE,
            PROFILE_NOTE,
            SCHEMA_INVENTORY_NOTE,
            MAPPING_REVIEW_NOTE,
            CONTRACT_REVIEW_NOTE,
            RECONCILIATION_NOTE,
            SENSITIVE_FIELD_REVIEW_NOTE,
            TEST_EVIDENCE_REVIEW_NOTE,
            EVIDENCE_COVERAGE_REVIEW_NOTE,
            REVIEW_PACK_NOTE,
            REVIEWER_SUMMARY_NOTE,
            LLM_REVIEW_NOTE,
            TRACE_NOTE,
        ],
    }


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> ArtifactPaths:
    if args.no_llm and args.llm_review:
        parser.error("--no-llm cannot be used with --llm-review")
    if args.llm_max_input_chars < 1:
        parser.error("--llm-max-input-chars must be a positive integer")
    pack_path = validate_pack_path(parser, args.pack)
    output_dir = validate_output_dir(args.output_dir)
    try:
        loaded_manifest = load_manifest(pack_path, args.manifest)
        inventory = build_inventory(loaded_manifest)
        dataset_profiles = build_dataset_profiles(loaded_manifest)
        schema_inventory = build_schema_inventory(dataset_profiles)
        mapping_review = build_mapping_review(loaded_manifest, schema_inventory)
        contract_review = build_contract_review(loaded_manifest, dataset_profiles, schema_inventory)
        reconciliation_results = build_reconciliation_results(
            loaded_manifest, dataset_profiles, schema_inventory, mapping_review
        )
        sensitive_field_review = build_sensitive_field_review(
            loaded_manifest,
            schema_inventory,
            dataset_profiles,
            mapping_review,
            contract_review,
        )
        test_evidence_review = build_test_evidence_review(loaded_manifest)
        evidence_coverage_review = build_evidence_coverage_review(loaded_manifest)
        review_pack = build_review_pack(
            inventory=inventory,
            dataset_profiles=dataset_profiles,
            mapping_review=mapping_review,
            contract_review=contract_review,
            reconciliation_results=reconciliation_results,
            sensitive_field_review=sensitive_field_review,
            test_evidence_review=test_evidence_review,
            evidence_coverage_review=evidence_coverage_review,
        )
    except ManifestError as exc:
        parser.error(str(exc))

    inventory_path = write_json_artifact(inventory, output_dir, INVENTORY_FILE_NAME)
    dataset_profiles_path = write_json_artifact(
        dataset_profiles, output_dir, DATASET_PROFILES_FILE_NAME
    )
    schema_inventory_path = write_json_artifact(
        schema_inventory, output_dir, SCHEMA_INVENTORY_FILE_NAME
    )
    mapping_review_path = write_json_artifact(mapping_review, output_dir, MAPPING_REVIEW_FILE_NAME)
    contract_review_path = write_json_artifact(
        contract_review, output_dir, CONTRACT_REVIEW_FILE_NAME
    )
    reconciliation_results_path = write_json_artifact(
        reconciliation_results, output_dir, RECONCILIATION_RESULTS_FILE_NAME
    )
    sensitive_field_review_path = write_json_artifact(
        sensitive_field_review, output_dir, SENSITIVE_FIELD_REVIEW_FILE_NAME
    )
    test_evidence_review_path = write_json_artifact(
        test_evidence_review, output_dir, TEST_EVIDENCE_REVIEW_FILE_NAME
    )
    evidence_coverage_review_path = write_json_artifact(
        evidence_coverage_review, output_dir, EVIDENCE_COVERAGE_REVIEW_FILE_NAME
    )
    review_pack_path = write_json_artifact(review_pack, output_dir, REVIEW_PACK_FILE_NAME)
    reviewer_summary_path = write_reviewer_summary(
        review_pack, output_dir, REVIEWER_SUMMARY_FILE_NAME
    )
    llm_reviewer_notes = build_llm_reviewer_notes(
        review_pack=review_pack,
        llm_requested=args.llm_review,
        provider=args.llm_provider,
        model=args.llm_model,
        max_input_chars=args.llm_max_input_chars,
    )
    llm_reviewer_notes_path = write_json_artifact(
        llm_reviewer_notes, output_dir, LLM_REVIEWER_NOTES_FILE_NAME
    )
    llm_review_summary = {
        "llm_requested": llm_reviewer_notes["llm_requested"],
        "llm_performed": llm_reviewer_notes["status"] == "llm_review_completed",
        "llm_status": llm_reviewer_notes["status"],
        "provider": llm_reviewer_notes["provider"],
        "model": llm_reviewer_notes["model"],
        "input_truncated": llm_reviewer_notes["input_policy"].get("input_truncated", False),
    }
    trace = build_trace(
        pack_path=pack_path,
        output_dir=output_dir,
        manifest_path=loaded_manifest.manifest_path,
        no_llm=args.no_llm,
        orchestrator=args.orchestrator,
        inventory_counts=inventory["counts"],
        dataset_profile_summary=build_dataset_profile_summary(dataset_profiles),
        schema_inventory_summary=build_schema_summary(schema_inventory),
        mapping_review_summary=mapping_review["summary"],
        contract_review_summary=contract_review["summary"],
        reconciliation_summary=reconciliation_results["summary"],
        sensitive_field_summary=sensitive_field_review["summary"],
        test_evidence_summary=test_evidence_review["summary"],
        evidence_coverage_summary=evidence_coverage_review["summary"],
        review_pack_summary=review_pack["summary"],
        reviewer_summary_path=reviewer_summary_path,
        llm_review_summary=llm_review_summary,
    )
    trace_path = write_json_artifact(trace, output_dir, TRACE_FILE_NAME)
    return (
        inventory_path,
        dataset_profiles_path,
        schema_inventory_path,
        mapping_review_path,
        contract_review_path,
        reconciliation_results_path,
        sensitive_field_review_path,
        test_evidence_review_path,
        evidence_coverage_review_path,
        review_pack_path,
        reviewer_summary_path,
        llm_reviewer_notes_path,
        trace_path,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    (
        inventory_path,
        dataset_profiles_path,
        schema_inventory_path,
        mapping_review_path,
        contract_review_path,
        reconciliation_results_path,
        sensitive_field_review_path,
        test_evidence_review_path,
        evidence_coverage_review_path,
        review_pack_path,
        reviewer_summary_path,
        llm_reviewer_notes_path,
        trace_path,
    ) = run(args, parser)
    print(f"Wrote migration inventory: {inventory_path}")
    print(f"Wrote dataset profiles: {dataset_profiles_path}")
    print(f"Wrote schema inventory: {schema_inventory_path}")
    print(f"Wrote mapping review: {mapping_review_path}")
    print(f"Wrote contract review: {contract_review_path}")
    print(f"Wrote reconciliation results: {reconciliation_results_path}")
    print(f"Wrote sensitive field review: {sensitive_field_review_path}")
    print(f"Wrote test evidence review: {test_evidence_review_path}")
    print(f"Wrote evidence coverage review: {evidence_coverage_review_path}")
    print(f"Wrote review pack: {review_pack_path}")
    print(f"Wrote reviewer summary: {reviewer_summary_path}")
    print(f"Wrote LLM reviewer notes: {llm_reviewer_notes_path}")
    print(f"Wrote migration trace: {trace_path}")
    print(INVENTORY_NOTE)
    print(PROFILE_NOTE)
    print(MAPPING_REVIEW_NOTE)
    print(CONTRACT_REVIEW_NOTE)
    print(RECONCILIATION_NOTE)
    print(SENSITIVE_FIELD_REVIEW_NOTE)
    print(TEST_EVIDENCE_REVIEW_NOTE)
    print(EVIDENCE_COVERAGE_REVIEW_NOTE)
    print(REVIEW_PACK_NOTE)
    print(REVIEWER_SUMMARY_NOTE)
    print(LLM_REVIEW_NOTE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
