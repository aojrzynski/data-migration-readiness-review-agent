from __future__ import annotations

import json
from pathlib import Path

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
)
from data_migration_readiness_review_agent.cli import main
from data_migration_readiness_review_agent.safe_language import find_forbidden_terms
from helpers import EXPECTED_ARTIFACT_FILE_ORDER, EXPECTED_ARTIFACT_FILES, read_json

EXAMPLE_OUTPUT_DIR = Path("examples/example_outputs")
EXPECTED_JSON_STATUSES = {
    INVENTORY_FILE_NAME: ("migration_inventory", "inventory_created"),
    DATASET_PROFILES_FILE_NAME: ("dataset_profiles", "profile_created"),
    SCHEMA_INVENTORY_FILE_NAME: ("schema_inventory", "schema_inventory_created"),
    MAPPING_REVIEW_FILE_NAME: ("mapping_review", "mapping_review_created"),
    CONTRACT_REVIEW_FILE_NAME: ("contract_review", "contract_review_created"),
    RECONCILIATION_RESULTS_FILE_NAME: ("reconciliation_results", "reconciliation_created"),
    SENSITIVE_FIELD_REVIEW_FILE_NAME: (
        "sensitive_field_review",
        "sensitive_field_review_created",
    ),
    TEST_EVIDENCE_REVIEW_FILE_NAME: ("test_evidence_review", "test_evidence_review_created"),
    EVIDENCE_COVERAGE_REVIEW_FILE_NAME: (
        "evidence_coverage_review",
        "evidence_coverage_review_created",
    ),
    REVIEW_PACK_FILE_NAME: ("review_pack", "review_pack_created"),
    LLM_REVIEWER_NOTES_FILE_NAME: ("llm_reviewer_notes", "llm_review_not_requested"),
}


def test_committed_example_outputs_exist_and_json_files_parse() -> None:
    assert EXAMPLE_OUTPUT_DIR.exists()
    assert {path.name for path in EXAMPLE_OUTPUT_DIR.iterdir()} == EXPECTED_ARTIFACT_FILES

    for file_name in EXPECTED_ARTIFACT_FILES - {REVIEWER_SUMMARY_FILE_NAME}:
        json.loads((EXAMPLE_OUTPUT_DIR / file_name).read_text(encoding="utf-8"))


def test_committed_example_outputs_have_expected_statuses() -> None:
    for file_name, (artifact_type, status) in EXPECTED_JSON_STATUSES.items():
        artifact = read_json(EXAMPLE_OUTPUT_DIR / file_name)
        assert artifact["artifact_type"] == artifact_type
        assert artifact["status"] == status

    trace = read_json(EXAMPLE_OUTPUT_DIR / TRACE_FILE_NAME)
    assert trace["status"] == "review_summary_artifacts_created"
    assert trace["artifacts_written"] == EXPECTED_ARTIFACT_FILE_ORDER
    assert trace["orchestrator"] == "standard"
    assert trace["orchestration"]["mode"] == "standard"


def test_committed_example_llm_artifact_is_not_requested_and_safe() -> None:
    notes = read_json(EXAMPLE_OUTPUT_DIR / LLM_REVIEWER_NOTES_FILE_NAME)

    assert notes["status"] == "llm_review_not_requested"
    assert find_forbidden_terms(json.dumps(notes)) == []


def test_committed_example_reviewer_summary_exists_and_is_safe() -> None:
    summary = (EXAMPLE_OUTPUT_DIR / REVIEWER_SUMMARY_FILE_NAME).read_text(encoding="utf-8")

    assert "# Data Migration Review Summary" in summary
    assert find_forbidden_terms(summary) == []


def test_fresh_example_run_writes_same_artifact_filenames(tmp_path: Path) -> None:
    output_dir = tmp_path / "example_outputs"

    assert (
        main(
            [
                "--pack",
                "examples/migration_pack",
                "--output-dir",
                str(output_dir),
                "--no-llm",
            ]
        )
        == 0
    )

    assert {path.name for path in output_dir.iterdir()} == EXPECTED_ARTIFACT_FILES
