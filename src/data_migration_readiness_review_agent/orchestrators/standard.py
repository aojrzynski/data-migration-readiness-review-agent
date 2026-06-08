from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
from data_migration_readiness_review_agent.artifacts import write_json_artifact
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
from data_migration_readiness_review_agent.manifest import load_manifest
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
from data_migration_readiness_review_agent.run_config import RunConfig
from data_migration_readiness_review_agent.run_result import RunResult
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
    "This run creates deterministic review artifacts and optional supplemental LLM notes. "
    "It does not assess readiness, score dimensions, approve migration, decide go-live, "
    "certify legal/privacy/compliance status, or replace human review."
)

STANDARD_ORCHESTRATION_STEPS = [
    "manifest_loaded",
    "inventory_created",
    "dataset_profiles_created",
    "schema_inventory_created",
    "mapping_review_created",
    "contract_review_created",
    "reconciliation_created",
    "sensitive_field_review_created",
    "test_evidence_review_created",
    "evidence_coverage_review_created",
    "review_pack_created",
    "reviewer_summary_created",
    "llm_reviewer_notes_created",
    "trace_created",
]


@dataclass(frozen=True)
class ReviewArtifacts:
    inventory: dict[str, Any]
    dataset_profiles: dict[str, Any]
    schema_inventory: dict[str, Any]
    mapping_review: dict[str, Any]
    contract_review: dict[str, Any]
    reconciliation_results: dict[str, Any]
    sensitive_field_review: dict[str, Any]
    test_evidence_review: dict[str, Any]
    evidence_coverage_review: dict[str, Any]
    review_pack: dict[str, Any]
    llm_reviewer_notes: dict[str, Any]
    trace: dict[str, Any]


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


def build_llm_review_summary(llm_reviewer_notes: dict[str, Any]) -> dict[str, Any]:
    return {
        "llm_requested": llm_reviewer_notes["llm_requested"],
        "llm_performed": llm_reviewer_notes["status"] == "llm_review_completed",
        "llm_status": llm_reviewer_notes["status"],
        "provider": llm_reviewer_notes["provider"],
        "model": llm_reviewer_notes["model"],
        "input_truncated": llm_reviewer_notes["input_policy"].get("input_truncated", False),
    }


def trace_notes() -> list[str]:
    return [
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
    ]


def build_trace(
    *,
    config: RunConfig,
    resolved_manifest_path: Path,
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
    orchestration_mode: str = "standard",
    orchestration_steps: list[str] | None = None,
    orchestration_implementation: str | None = None,
) -> dict[str, Any]:
    orchestration: dict[str, Any] = {
        "mode": orchestration_mode,
        "steps": orchestration_steps or STANDARD_ORCHESTRATION_STEPS,
    }
    if orchestration_implementation is not None:
        orchestration["implementation"] = orchestration_implementation
    return {
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "pack_path": str(config.pack_path),
        "output_directory": str(config.output_dir),
        "manifest_path": str(resolved_manifest_path),
        "no_llm": config.no_llm,
        "orchestrator": config.orchestrator,
        "orchestration": orchestration,
        "status": "review_summary_artifacts_created",
        "artifacts_written": list(ORDERED_ARTIFACT_FILE_NAMES),
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
        "notes": trace_notes(),
    }


def run_standard_review(config: RunConfig) -> RunResult:
    loaded_manifest = load_manifest(config.pack_path, config.manifest_path)
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
    reviewer_summary_path = config.output_dir / REVIEWER_SUMMARY_FILE_NAME
    llm_reviewer_notes = build_llm_reviewer_notes(
        review_pack=review_pack,
        llm_requested=config.llm_review,
        provider=config.llm_provider,
        model=config.llm_model,
        max_input_chars=config.llm_max_input_chars,
    )
    trace = build_trace(
        config=config,
        resolved_manifest_path=loaded_manifest.manifest_path,
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
        llm_review_summary=build_llm_review_summary(llm_reviewer_notes),
        orchestration_mode="standard",
    )
    artifacts = ReviewArtifacts(
        inventory=inventory,
        dataset_profiles=dataset_profiles,
        schema_inventory=schema_inventory,
        mapping_review=mapping_review,
        contract_review=contract_review,
        reconciliation_results=reconciliation_results,
        sensitive_field_review=sensitive_field_review,
        test_evidence_review=test_evidence_review,
        evidence_coverage_review=evidence_coverage_review,
        review_pack=review_pack,
        llm_reviewer_notes=llm_reviewer_notes,
        trace=trace,
    )
    artifact_paths = write_review_artifacts(artifacts, config.output_dir)
    return RunResult(
        artifacts=artifact_paths,
        notes=trace["notes"],
        trace=trace,
        status=trace["status"],
    )


def write_review_artifacts(artifacts: ReviewArtifacts, output_dir: Path) -> dict[str, Path]:
    artifact_payloads = {
        INVENTORY_FILE_NAME: artifacts.inventory,
        DATASET_PROFILES_FILE_NAME: artifacts.dataset_profiles,
        SCHEMA_INVENTORY_FILE_NAME: artifacts.schema_inventory,
        MAPPING_REVIEW_FILE_NAME: artifacts.mapping_review,
        CONTRACT_REVIEW_FILE_NAME: artifacts.contract_review,
        RECONCILIATION_RESULTS_FILE_NAME: artifacts.reconciliation_results,
        SENSITIVE_FIELD_REVIEW_FILE_NAME: artifacts.sensitive_field_review,
        TEST_EVIDENCE_REVIEW_FILE_NAME: artifacts.test_evidence_review,
        EVIDENCE_COVERAGE_REVIEW_FILE_NAME: artifacts.evidence_coverage_review,
        REVIEW_PACK_FILE_NAME: artifacts.review_pack,
        LLM_REVIEWER_NOTES_FILE_NAME: artifacts.llm_reviewer_notes,
        TRACE_FILE_NAME: artifacts.trace,
    }
    written_paths: dict[str, Path] = {}
    for file_name in ORDERED_ARTIFACT_FILE_NAMES:
        if file_name == REVIEWER_SUMMARY_FILE_NAME:
            written_paths[file_name] = write_reviewer_summary(
                artifacts.review_pack, output_dir, REVIEWER_SUMMARY_FILE_NAME
            )
        else:
            written_paths[file_name] = write_json_artifact(
                artifact_payloads[file_name], output_dir, file_name
            )
    return written_paths
