from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent.artifact_registry import (
    CONTRACT_REVIEW_FILE_NAME,
    DATASET_PROFILES_FILE_NAME,
    EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
    INVENTORY_FILE_NAME,
    JSON_ARTIFACT_FILE_NAMES,
    LLM_REVIEWER_NOTES_FILE_NAME,
    MAPPING_REVIEW_FILE_NAME,
    MARKDOWN_ARTIFACT_FILE_NAMES,
    ORDERED_ARTIFACT_FILE_NAMES,
    RECONCILIATION_RESULTS_FILE_NAME,
    REVIEW_PACK_FILE_NAME,
    REVIEWER_SUMMARY_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    SENSITIVE_FIELD_REVIEW_FILE_NAME,
    TEST_EVIDENCE_REVIEW_FILE_NAME,
    TRACE_FILE_NAME,
)

__all__ = [
    "CONTRACT_REVIEW_FILE_NAME",
    "DATASET_PROFILES_FILE_NAME",
    "EVIDENCE_COVERAGE_REVIEW_FILE_NAME",
    "INVENTORY_FILE_NAME",
    "JSON_ARTIFACT_FILE_NAMES",
    "LLM_REVIEWER_NOTES_FILE_NAME",
    "MAPPING_REVIEW_FILE_NAME",
    "MARKDOWN_ARTIFACT_FILE_NAMES",
    "ORDERED_ARTIFACT_FILE_NAMES",
    "RECONCILIATION_RESULTS_FILE_NAME",
    "REVIEW_PACK_FILE_NAME",
    "REVIEWER_SUMMARY_FILE_NAME",
    "SCHEMA_INVENTORY_FILE_NAME",
    "SENSITIVE_FIELD_REVIEW_FILE_NAME",
    "TEST_EVIDENCE_REVIEW_FILE_NAME",
    "TRACE_FILE_NAME",
    "write_json_artifact",
]


def write_json_artifact(payload: dict[str, Any], output_dir: Path, file_name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / file_name
    artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact_path
