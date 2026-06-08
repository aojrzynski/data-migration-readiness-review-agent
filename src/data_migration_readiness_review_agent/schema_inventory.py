from __future__ import annotations

from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME

SCHEMA_INVENTORY_NOTE = (
    "PR #3 inventories source and target schemas. It does not validate mappings or "
    "contracts and does not assess readiness."
)


def build_schema_inventory(dataset_profiles: dict[str, Any]) -> dict[str, Any]:
    datasets = [build_schema_dataset_entry(dataset) for dataset in dataset_profiles["datasets"]]
    return {
        "artifact_type": "schema_inventory",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "schema_inventory_created",
        "datasets": datasets,
        "notes": [SCHEMA_INVENTORY_NOTE],
    }


def build_schema_dataset_entry(dataset_profile: dict[str, Any]) -> dict[str, Any]:
    source = build_schema_side(dataset_profile["source"])
    target = build_schema_side(dataset_profile["target"])
    source_columns = source["columns"]
    target_columns = target["columns"]
    shared_columns = [column for column in source_columns if column in set(target_columns)]
    source_only_columns = [column for column in source_columns if column not in set(target_columns)]
    target_only_columns = [column for column in target_columns if column not in set(source_columns)]
    return {
        "dataset_id": dataset_profile["dataset_id"],
        "key_columns": list(dataset_profile["key_columns"]),
        "source": source,
        "target": target,
        "schema_overlap": {
            "shared_columns": shared_columns,
            "source_only_columns": source_only_columns,
            "target_only_columns": target_only_columns,
        },
        "status": "not_assessed",
    }


def build_schema_side(profile_side: dict[str, Any]) -> dict[str, Any]:
    columns = [column["name"] for column in profile_side["columns"]]
    return {
        "path": profile_side["path"],
        "status": profile_side["status"],
        "columns": columns,
        "column_count": profile_side["column_count"],
        "key_columns_present": profile_side["key_columns_present"],
        "missing_key_columns": list(profile_side["missing_key_columns"]),
        "warnings": list(profile_side["warnings"]),
    }


def build_schema_summary(schema_inventory: dict[str, Any]) -> dict[str, int]:
    datasets = schema_inventory["datasets"]
    return {
        "schemas_inventoried": len(datasets),
        "schemas_with_missing_key_columns": sum(
            1
            for dataset in datasets
            if dataset["source"]["missing_key_columns"] or dataset["target"]["missing_key_columns"]
        ),
    }
