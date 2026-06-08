"""
Deterministic reconciliation between profiled source and target CSVs. It compares row
counts, key overlap, and direct mapped fields with bounded samples, without
transformations or a final migration decision.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.manifest import resolve_inside_pack
from data_migration_readiness_review_agent.models import LoadedManifest

# Reconciliation samples are capped so artifacts show examples without dumping records.
MISSING_KEY_SAMPLE_LIMIT = 20
UNEXPECTED_KEY_SAMPLE_LIMIT = 20
MISMATCH_SAMPLE_LIMIT = 50
SKIPPED_MAPPING_LIMIT = 50
RECONCILIATION_NOTE = (
    "PR #5 performs deterministic reconciliation checks only. It does not assess migration "
    "launch suitability, authorize migration activity, call an LLM, or apply transformations."
)


def build_reconciliation_results(
    loaded_manifest: LoadedManifest,
    dataset_profiles: dict[str, Any],
    schema_inventory: dict[str, Any],
    mapping_review: dict[str, Any],
) -> dict[str, Any]:
    """
    Build reconciliation_results.json with deterministic row-count, key-overlap, and
    direct mapped-field comparisons.
    """
    profiles_by_dataset = {
        dataset["dataset_id"]: dataset for dataset in dataset_profiles["datasets"]
    }
    schemas_by_dataset = {
        dataset["dataset_id"]: dataset for dataset in schema_inventory["datasets"]
    }
    mappings_by_dataset = group_mapping_reviews(mapping_review)
    datasets = [
        reconcile_dataset(
            loaded_manifest,
            dataset,
            profiles_by_dataset.get(dataset["dataset_id"]),
            schemas_by_dataset.get(dataset["dataset_id"]),
            mappings_by_dataset.get(dataset["dataset_id"], []),
        )
        for dataset in loaded_manifest.data["datasets"]
    ]
    return {
        "artifact_type": "reconciliation_results",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "reconciliation_created",
        "datasets": datasets,
        "summary": build_reconciliation_summary(datasets),
        "notes": [RECONCILIATION_NOTE],
    }


def reconcile_dataset(
    loaded_manifest: LoadedManifest,
    manifest_dataset: dict[str, Any],
    dataset_profile: dict[str, Any] | None,
    dataset_schema: dict[str, Any] | None,
    mapping_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run reconciliation checks for one dataset when source and target CSVs and relevant
    direct mappings are available.
    """
    dataset_id = manifest_dataset["dataset_id"]
    key_columns = list(manifest_dataset["key_columns"])
    source_profile = (dataset_profile or {}).get("source", {})
    target_profile = (dataset_profile or {}).get("target", {})
    warnings: list[str] = []
    row_count_check = build_row_count_check(manifest_dataset, source_profile, target_profile)
    duplicate_key_counts = {
        "source_duplicate_key_count": int(source_profile.get("duplicate_key_count", 0)),
        "target_duplicate_key_count": int(target_profile.get("duplicate_key_count", 0)),
    }
    if duplicate_key_counts["source_duplicate_key_count"]:
        warnings.append(
            "Source duplicate keys were found; first rows are used for mapped-field comparison."
        )
    if duplicate_key_counts["target_duplicate_key_count"]:
        warnings.append(
            "Target duplicate keys were found; first rows are used for mapped-field comparison."
        )

    source_columns = list((dataset_schema or {}).get("source", {}).get("columns", []))
    target_columns = list((dataset_schema or {}).get("target", {}).get("columns", []))
    missing_source_key_columns = [column for column in key_columns if column not in source_columns]
    missing_target_key_columns = [column for column in key_columns if column not in target_columns]
    if missing_source_key_columns:
        warnings.append(
            "Source dataset is missing key column(s): " + ", ".join(missing_source_key_columns)
        )
    if missing_target_key_columns:
        warnings.append(
            "Target dataset is missing key column(s): " + ", ".join(missing_target_key_columns)
        )

    source_rows: list[dict[str, str]] = []
    target_rows: list[dict[str, str]] = []
    row_load_warnings: list[str] = []
    can_load_rows = (
        source_profile.get("status") == "profile_created"
        and target_profile.get("status") == "profile_created"
        and not missing_source_key_columns
        and not missing_target_key_columns
    )
    if can_load_rows:
        source_rows, source_warning = load_csv_rows(
            loaded_manifest.pack_path, manifest_dataset["source_path"]
        )
        target_rows, target_warning = load_csv_rows(
            loaded_manifest.pack_path, manifest_dataset["target_path"]
        )
        row_load_warnings = [warning for warning in (source_warning, target_warning) if warning]
        warnings.extend(row_load_warnings)

    if not can_load_rows or row_load_warnings:
        key_overlap = skipped_key_overlap(missing_source_key_columns, missing_target_key_columns)
        field_comparison = skipped_field_comparison("key overlap was skipped")
    else:
        source_key_map = build_first_row_by_key(source_rows, key_columns)
        target_key_map = build_first_row_by_key(target_rows, key_columns)
        key_overlap = build_key_overlap(source_key_map, target_key_map, key_columns)
        field_comparison = compare_mapped_fields(
            source_key_map,
            target_key_map,
            key_columns,
            mapping_reviews,
        )
        if field_comparison["skipped_mapping_count"]:
            warnings.append("Some mapping rows were skipped during mapped-field comparison.")

    return {
        "dataset_id": dataset_id,
        "status": dataset_status(warnings, row_count_check, key_overlap, field_comparison),
        "key_columns": key_columns,
        "row_count_check": row_count_check,
        "duplicate_key_counts": duplicate_key_counts,
        "key_overlap": key_overlap,
        "field_comparison": field_comparison,
        "warnings": warnings,
    }


def build_row_count_check(
    manifest_dataset: dict[str, Any], source_profile: dict[str, Any], target_profile: dict[str, Any]
) -> dict[str, Any]:
    """Compare profiled source and target row counts using the dataset tolerance."""
    # row_count_tolerance is evidence configuration, not a migration decision threshold.
    tolerance = int(manifest_dataset.get("row_count_tolerance", 0) or 0)
    source_count = (
        source_profile.get("row_count")
        if source_profile.get("status") == "profile_created"
        else None
    )
    target_count = (
        target_profile.get("row_count")
        if target_profile.get("status") == "profile_created"
        else None
    )
    difference = (
        None
        if source_count is None or target_count is None
        else abs(int(source_count) - int(target_count))
    )
    if difference is None:
        status = "skipped"
    elif difference <= tolerance:
        status = "passed_check"
    else:
        status = "failed_check"
    return {
        "source_row_count": source_count,
        "target_row_count": target_count,
        "difference": difference,
        "tolerance": tolerance,
        "status": status,
    }


def load_csv_rows(pack_path: Path, relative_path: str) -> tuple[list[dict[str, str]], str | None]:
    """
    Load CSV rows for reconciliation only, keeping row dictionaries local and using
    downstream caps for reported samples.
    """
    resolved_path = resolve_inside_pack(pack_path, Path(relative_path), description=relative_path)
    try:
        with resolved_path.open("r", encoding="utf-8", newline="") as file_obj:
            reader = csv.DictReader(file_obj, strict=True)
            if reader.fieldnames is None:
                return [], f"Dataset CSV has no header row: {relative_path}"
            return [normalize_dict_row(row) for row in reader], None
    except (csv.Error, OSError, UnicodeDecodeError) as exc:
        return [], f"Dataset CSV could not be loaded for reconciliation: {relative_path}: {exc}"


def normalize_dict_row(row: dict[str, str | None]) -> dict[str, str]:
    """Convert a DictReader row into a plain string dictionary."""
    return {str(key): normalize_value(value or "") for key, value in row.items() if key is not None}


def normalize_value(value: str) -> str:
    """Normalize line endings before deterministic row comparisons."""
    return value.replace("\r\n", "\n").replace("\r", "\n")


def build_first_row_by_key(
    rows: list[dict[str, str]], key_columns: list[str]
) -> dict[tuple[str, ...], dict[str, str]]:
    """
    Index rows by single or composite key, keeping the first row for duplicate keys so
    comparison remains deterministic.
    """
    row_map: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        # Composite keys are represented as tuples; duplicates keep the first row deterministically.
        key = tuple(row.get(column, "") for column in key_columns)
        row_map.setdefault(key, row)
    return row_map


def build_key_overlap(
    source_key_map: dict[tuple[str, ...], dict[str, str]],
    target_key_map: dict[tuple[str, ...], dict[str, str]],
    key_columns: list[str],
) -> dict[str, Any]:
    """
    Compare source and target key sets and return bounded samples of missing source and
    unexpected target keys.
    """
    source_keys = set(source_key_map)
    target_keys = set(target_key_map)
    # Missing source keys and unexpected target keys answer different review questions.
    missing = sorted(source_keys - target_keys)
    unexpected = sorted(target_keys - source_keys)
    return {
        "status": "passed_check" if not missing and not unexpected else "failed_check",
        "source_key_count": len(source_keys),
        "target_key_count": len(target_keys),
        "shared_key_count": len(source_keys & target_keys),
        "missing_source_keys_in_target_count": len(missing),
        "unexpected_target_keys_count": len(unexpected),
        "missing_source_key_samples": [
            key_to_sample(key_columns, key) for key in missing[:MISSING_KEY_SAMPLE_LIMIT]
        ],
        "unexpected_target_key_samples": [
            key_to_sample(key_columns, key) for key in unexpected[:UNEXPECTED_KEY_SAMPLE_LIMIT]
        ],
    }


def skipped_key_overlap(
    missing_source_key_columns: list[str], missing_target_key_columns: list[str]
) -> dict[str, Any]:
    """Build the key-overlap result used when key comparison cannot run."""
    return {
        "status": "skipped",
        "source_key_count": 0,
        "target_key_count": 0,
        "shared_key_count": 0,
        "missing_source_keys_in_target_count": 0,
        "unexpected_target_keys_count": 0,
        "missing_source_key_samples": [],
        "unexpected_target_key_samples": [],
        "missing_source_key_columns": missing_source_key_columns,
        "missing_target_key_columns": missing_target_key_columns,
    }


def compare_mapped_fields(
    source_key_map: dict[tuple[str, ...], dict[str, str]],
    target_key_map: dict[tuple[str, ...], dict[str, str]],
    key_columns: list[str],
    mapping_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compare direct source-to-target mapped fields for matching keys and cap reported
    mismatch samples.
    """
    direct_mappings, skipped_mappings = collect_direct_mappings(mapping_reviews)
    shared_keys = sorted(set(source_key_map) & set(target_key_map))
    compared_cell_count = 0
    matched_cell_count = 0
    mismatch_samples: list[dict[str, Any]] = []
    mismatched_cell_count = 0
    for key in shared_keys:
        source_row = source_key_map[key]
        target_row = target_key_map[key]
        for mapping in direct_mappings:
            compared_cell_count += 1
            source_value = normalize_value(source_row.get(mapping["source_field"], ""))
            target_value = normalize_value(target_row.get(mapping["target_field"], ""))
            if source_value == target_value:
                matched_cell_count += 1
            else:
                mismatched_cell_count += 1
                if len(mismatch_samples) < MISMATCH_SAMPLE_LIMIT:
                    # Cap samples; counts remain aggregate evidence for the full comparison.
                    mismatch_samples.append(
                        {
                            "key": key_to_sample(key_columns, key),
                            "source_field": mapping["source_field"],
                            "target_field": mapping["target_field"],
                            "source_value": source_value,
                            "target_value": target_value,
                        }
                    )
    if not direct_mappings or not shared_keys:
        status = "warning" if skipped_mappings else "skipped"
    elif mismatched_cell_count:
        status = "failed_check"
    elif skipped_mappings:
        status = "warning"
    else:
        status = "passed_check"
    return {
        "status": status,
        "mapped_fields_compared": len(direct_mappings),
        "compared_cell_count": compared_cell_count,
        "matched_cell_count": matched_cell_count,
        "mismatched_cell_count": mismatched_cell_count,
        "mismatch_samples": mismatch_samples,
        "skipped_mapping_count": len(skipped_mappings),
        "skipped_mappings": skipped_mappings[:SKIPPED_MAPPING_LIMIT],
    }


def skipped_field_comparison(reason: str) -> dict[str, Any]:
    """Build the mapped-field comparison result used when comparison cannot run."""
    return {
        "status": "skipped",
        "mapped_fields_compared": 0,
        "compared_cell_count": 0,
        "matched_cell_count": 0,
        "mismatched_cell_count": 0,
        "mismatch_samples": [],
        "skipped_mapping_count": 0,
        "skipped_mappings": [],
        "reason": reason,
    }


def collect_direct_mappings(
    mapping_reviews: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """
    Collect valid direct mappings for reconciliation and skip transformed mappings
    because this tool does not execute transformation logic.
    """
    direct_mappings: list[dict[str, str]] = []
    skipped_mappings: list[dict[str, Any]] = []
    for review in mapping_reviews:
        if review.get("status") != "reviewed":
            continue
        for row in review.get("reviewed_mapping_rows", []):
            if row.get("issues"):
                continue
            source_field = str(row.get("source_field") or "").strip()
            target_field = str(row.get("target_field") or "").strip()
            if not source_field or not target_field:
                continue
            transformation = str(row.get("metadata", {}).get("transformation", "")).strip()
            if transformation:
                # Transformed mappings are skipped; this tool does not execute them.
                skipped_mappings.append(
                    {
                        "mapping_id": review.get("mapping_id"),
                        "row_number": row.get("row_number"),
                        "source_field": source_field,
                        "target_field": target_field,
                        "reason": "skipped_transformed_mapping",
                    }
                )
                continue
            direct_mappings.append({"source_field": source_field, "target_field": target_field})
    return direct_mappings, skipped_mappings


def group_mapping_reviews(mapping_review: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Group reviewed mapping artifacts by dataset for reconciliation."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for review in mapping_review.get("mapping_reviews", []):
        dataset_id = review.get("dataset_id")
        if dataset_id:
            grouped.setdefault(dataset_id, []).append(review)
    return grouped


def key_to_sample(key_columns: list[str], key: tuple[str, ...]) -> dict[str, str]:
    """Convert a key tuple into the sample dictionary shape used in reconciliation output."""
    return dict(zip(key_columns, key, strict=True))


def dataset_status(
    warnings: list[str],
    row_count_check: dict[str, Any],
    key_overlap: dict[str, Any],
    field_comparison: dict[str, Any],
) -> str:
    """Choose the reconciliation dataset status from warnings and check results."""
    if row_count_check["status"] == "skipped" or key_overlap["status"] == "skipped":
        return "gap_found"
    if warnings or field_comparison["status"] == "warning":
        return "warning"
    return "reviewed"


def build_reconciliation_summary(datasets: list[dict[str, Any]]) -> dict[str, int]:
    """Count reconciliation outcomes and comparison totals across datasets."""
    return {
        "datasets_reconciled": sum(
            1 for dataset in datasets if dataset["status"] in {"reviewed", "warning"}
        ),
        "datasets_with_gaps": sum(1 for dataset in datasets if dataset["status"] == "gap_found"),
        "row_count_failures": sum(
            1 for dataset in datasets if dataset["row_count_check"]["status"] == "failed_check"
        ),
        "missing_source_keys_in_target": sum(
            dataset["key_overlap"]["missing_source_keys_in_target_count"] for dataset in datasets
        ),
        "unexpected_target_keys": sum(
            dataset["key_overlap"]["unexpected_target_keys_count"] for dataset in datasets
        ),
        "mismatched_cells": sum(
            dataset["field_comparison"]["mismatched_cell_count"] for dataset in datasets
        ),
    }
