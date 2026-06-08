from __future__ import annotations

import json
from pathlib import Path
from typing import Any

INVENTORY_FILE_NAME = "migration_inventory.json"
DATASET_PROFILES_FILE_NAME = "dataset_profiles.json"
SCHEMA_INVENTORY_FILE_NAME = "schema_inventory.json"
MAPPING_REVIEW_FILE_NAME = "mapping_review.json"
CONTRACT_REVIEW_FILE_NAME = "contract_review.json"
RECONCILIATION_RESULTS_FILE_NAME = "reconciliation_results.json"
SENSITIVE_FIELD_REVIEW_FILE_NAME = "sensitive_field_review.json"
TEST_EVIDENCE_REVIEW_FILE_NAME = "test_evidence_review.json"
EVIDENCE_COVERAGE_REVIEW_FILE_NAME = "evidence_coverage_review.json"
REVIEW_PACK_FILE_NAME = "review_pack.json"
REVIEWER_SUMMARY_FILE_NAME = "reviewer_summary.md"
LLM_REVIEWER_NOTES_FILE_NAME = "llm_reviewer_notes.json"
TRACE_FILE_NAME = "migration_readiness_trace.json"


def write_json_artifact(payload: dict[str, Any], output_dir: Path, file_name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / file_name
    artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact_path
