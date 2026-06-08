"""
Reviews mapping CSVs against observed source and target schemas. It checks required
source_field and target_field columns, missing references, duplicate mappings, and
unmapped columns without executing transformations.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.manifest import resolve_inside_pack
from data_migration_readiness_review_agent.models import LoadedManifest

MAPPING_REVIEW_FILE_NAME = "mapping_review.json"
# Mapping row summaries are bounded so large mapping files do not dominate artifacts.
MAPPING_ROW_SUMMARY_LIMIT = 200
MAPPING_ROW_ISSUE_LIMIT = 200
REQUIRED_MAPPING_COLUMNS = ("source_field", "target_field")
OPTIONAL_MAPPING_COLUMNS = ("transformation", "notes", "required")
MAPPING_REVIEW_NOTE = (
    "PR #4 reviews mapping files against source and target schemas only. It does not compare "
    "source and target records, run reconciliation, call an LLM, or assess readiness."
)


def build_mapping_review(
    loaded_manifest: LoadedManifest, schema_inventory: dict[str, Any]
) -> dict[str, Any]:
    """
    Build mapping_review.json by checking mapping files against observed source and
    target schemas. It records structural issues and does not run transformations.
    """
    schema_by_dataset = {dataset["dataset_id"]: dataset for dataset in schema_inventory["datasets"]}
    reviews = [
        review_mapping_entry(loaded_manifest, mapping, schema_by_dataset)
        for mapping in loaded_manifest.data.get("mappings", [])
    ]
    return {
        "artifact_type": "mapping_review",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "mapping_review_created",
        "mapping_reviews": reviews,
        "summary": build_mapping_summary(reviews),
        "notes": [MAPPING_REVIEW_NOTE],
    }


def review_mapping_entry(
    loaded_manifest: LoadedManifest,
    mapping: dict[str, Any],
    schema_by_dataset: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Review one declared mapping file and return either row-level issues, missing
    references, or file gaps in artifact form.
    """
    mapping_id = mapping.get("mapping_id", mapping["path"])
    dataset_id = mapping.get("dataset_id")
    relative_path = mapping["path"]
    dataset_schema = schema_by_dataset.get(dataset_id, {})
    source_columns = list(dataset_schema.get("source", {}).get("columns", []))
    target_columns = list(dataset_schema.get("target", {}).get("columns", []))
    base_review = base_mapping_review(
        mapping_id, dataset_id, relative_path, source_columns, target_columns
    )
    resolved_path = resolve_inside_pack(
        loaded_manifest.pack_path, Path(relative_path), description=f"mapping:{mapping_id}"
    )

    if not resolved_path.exists() or not resolved_path.is_file():
        # Missing mapping files are review gaps; other evidence can still be inspected.
        base_review["status"] = "gap_found"
        base_review["warnings"].append(f"Mapping CSV file is missing: {relative_path}")
        return base_review

    try:
        with resolved_path.open("r", encoding="utf-8", newline="") as file_obj:
            reader = csv.DictReader(file_obj, strict=True)
            if reader.fieldnames is None:
                base_review["status"] = "failed_check"
                base_review["warnings"].append(
                    f"Mapping CSV file has no header row: {relative_path}"
                )
                return base_review
            headers = [header or "" for header in reader.fieldnames]
            missing_required_columns = [
                column for column in REQUIRED_MAPPING_COLUMNS if column not in headers
            ]
            base_review["missing_required_columns"] = missing_required_columns
            base_review["required_columns_present"] = not missing_required_columns
            if missing_required_columns:
                base_review["status"] = "failed_check"
                base_review["warnings"].append(
                    "Mapping CSV is missing required column(s): "
                    + ", ".join(missing_required_columns)
                )
                return base_review
            rows = list(reader)
    except (csv.Error, OSError, UnicodeDecodeError) as exc:
        base_review["status"] = "failed_check"
        base_review["warnings"].append(f"Mapping CSV could not be parsed: {exc}")
        return base_review

    apply_mapping_checks(base_review, rows, source_columns, target_columns)
    return base_review


def base_mapping_review(
    mapping_id: str,
    dataset_id: str | None,
    relative_path: str,
    source_columns: list[str],
    target_columns: list[str],
) -> dict[str, Any]:
    """Create the default mapping review structure before CSV row checks are added."""
    return {
        "mapping_id": mapping_id,
        "dataset_id": dataset_id,
        "path": relative_path,
        "status": "reviewed",
        "required_columns_present": False,
        "missing_required_columns": list(REQUIRED_MAPPING_COLUMNS),
        "mapping_row_count": 0,
        "mapping_rows_reviewed": 0,
        "mapping_rows_omitted": 0,
        "source_columns": source_columns,
        "target_columns": target_columns,
        "mapped_source_fields": [],
        "mapped_target_fields": [],
        "reviewed_mapping_rows": [],
        "missing_source_field_references": [],
        "missing_target_field_references": [],
        "duplicate_source_mappings": [],
        "duplicate_target_mappings": [],
        "unmapped_source_columns": source_columns,
        "unmapped_target_columns": target_columns,
        "rows_with_issues": [],
        "warnings": [],
    }


def apply_mapping_checks(
    review: dict[str, Any],
    rows: list[dict[str, str | None]],
    source_columns: list[str],
    target_columns: list[str],
) -> None:
    """
    Apply deterministic mapping checks after a CSV mapping has been parsed, including
    missing references, duplicates, and unmapped columns.
    """
    review["required_columns_present"] = True
    review["missing_required_columns"] = []
    review["mapping_row_count"] = len(rows)
    review["mapping_rows_reviewed"] = min(len(rows), MAPPING_ROW_SUMMARY_LIMIT)
    review["mapping_rows_omitted"] = max(0, len(rows) - MAPPING_ROW_SUMMARY_LIMIT)

    source_set = set(source_columns)
    target_set = set(target_columns)
    mapped_sources: list[str] = []
    mapped_targets: list[str] = []
    rows_with_issues: list[dict[str, Any]] = []
    reviewed_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=2):
        source_field = (row.get("source_field") or "").strip()
        target_field = (row.get("target_field") or "").strip()
        row_issues: list[str] = []
        if not source_field:
            row_issues.append("blank_source_field")
        elif source_field not in source_set:
            row_issues.append("missing_source_field_reference")
        else:
            mapped_sources.append(source_field)
        if not target_field:
            row_issues.append("blank_target_field")
        elif target_field not in target_set:
            row_issues.append("missing_target_field_reference")
        else:
            mapped_targets.append(target_field)

        row_summary = {
            "row_number": index,
            "source_field": source_field,
            "target_field": target_field,
            "issues": row_issues,
        }
        metadata = lightweight_metadata(row)
        if metadata:
            row_summary["metadata"] = metadata
        if len(reviewed_rows) < MAPPING_ROW_SUMMARY_LIMIT:
            # Keep representative row summaries, not a full copy of the mapping CSV.
            reviewed_rows.append(row_summary)
        if row_issues and len(rows_with_issues) < MAPPING_ROW_ISSUE_LIMIT:
            rows_with_issues.append(row_summary)

    # This is structural mapping review only; reconciliation compares data later.
    source_counts = Counter(mapped_sources)
    target_counts = Counter(mapped_targets)
    review.update(
        {
            "mapped_source_fields": unique_in_order(mapped_sources),
            "mapped_target_fields": unique_in_order(mapped_targets),
            "reviewed_mapping_rows": reviewed_rows,
            "missing_source_field_references": unique_issue_values(
                rows_with_issues, "source_field", "missing_source_field_reference"
            ),
            "missing_target_field_references": unique_issue_values(
                rows_with_issues, "target_field", "missing_target_field_reference"
            ),
            "duplicate_source_mappings": [
                field for field in unique_in_order(mapped_sources) if source_counts[field] > 1
            ],
            "duplicate_target_mappings": [
                field for field in unique_in_order(mapped_targets) if target_counts[field] > 1
            ],
            "unmapped_source_columns": [
                column for column in source_columns if column not in mapped_sources
            ],
            "unmapped_target_columns": [
                column for column in target_columns if column not in mapped_targets
            ],
            "rows_with_issues": rows_with_issues,
        }
    )


def lightweight_metadata(row: dict[str, str | None]) -> dict[str, str]:
    """Keep optional mapping metadata fields that help explain a reviewed mapping row."""
    return {
        column: str(row[column]).strip()
        for column in OPTIONAL_MAPPING_COLUMNS
        if row.get(column) not in (None, "")
    }


def unique_in_order(values: list[str]) -> list[str]:
    """Return unique values in their first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def unique_issue_values(rows: list[dict[str, Any]], field_name: str, issue: str) -> list[str]:
    """Return the unique field values from rows that contain a specific issue."""
    values = [row[field_name] for row in rows if issue in row["issues"] and row[field_name]]
    return unique_in_order(values)


def build_mapping_summary(reviews: list[dict[str, Any]]) -> dict[str, int]:
    """Count mapping review outcomes for the mapping_review.json summary."""
    return {
        "mappings_expected": len(reviews),
        "mappings_reviewed": sum(1 for review in reviews if review["status"] == "reviewed"),
        "mapping_files_with_gaps": sum(1 for review in reviews if review["status"] == "gap_found"),
        "mapping_files_failed_checks": sum(
            1 for review in reviews if review["status"] == "failed_check"
        ),
        "mapping_rows_reviewed": sum(int(review["mapping_rows_reviewed"]) for review in reviews),
        "mapping_rows_with_issues": sum(len(review["rows_with_issues"]) for review in reviews),
        "missing_source_field_references": sum(
            len(review["missing_source_field_references"]) for review in reviews
        ),
        "missing_target_field_references": sum(
            len(review["missing_target_field_references"]) for review in reviews
        ),
        "unmapped_target_columns": sum(
            len(review["unmapped_target_columns"]) for review in reviews
        ),
    }
