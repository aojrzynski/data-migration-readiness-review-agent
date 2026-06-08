from __future__ import annotations

from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.models import LoadedManifest

SENSITIVE_FIELD_REVIEW_NOTE = (
    "PR #6 reviews sensitive-field indicators only. It does not classify legal/privacy "
    "status or decide whether data handling is acceptable."
)

BUILT_IN_INDICATORS = (
    "email",
    "phone",
    "mobile",
    "date_of_birth",
    "dob",
    "birth_date",
    "address",
    "postcode",
    "postal_code",
    "national_insurance",
    "ni_number",
    "tax_id",
    "ssn",
    "passport",
    "bank_account",
    "sort_code",
    "iban",
    "card_number",
)


def build_sensitive_field_review(
    loaded_manifest: LoadedManifest,
    schema_inventory: dict[str, Any],
    dataset_profiles: dict[str, Any],
    mapping_review: dict[str, Any],
    contract_review: dict[str, Any],
) -> dict[str, Any]:
    manifest_hints = [
        str(hint).strip()
        for hint in loaded_manifest.data.get("sensitive_field_hints", [])
        if str(hint).strip()
    ]
    schemas_by_dataset = {
        dataset["dataset_id"]: dataset for dataset in schema_inventory["datasets"]
    }
    profiles_by_dataset = {
        dataset["dataset_id"]: dataset for dataset in dataset_profiles["datasets"]
    }
    mappings_by_dataset = group_by_dataset(mapping_review.get("mapping_reviews", []))
    contracts_by_dataset = group_by_dataset(contract_review.get("contract_reviews", []))
    datasets = []
    for manifest_dataset in loaded_manifest.data["datasets"]:
        dataset_id = manifest_dataset["dataset_id"]
        schema_dataset = schemas_by_dataset.get(dataset_id, {})
        profile_dataset = profiles_by_dataset.get(dataset_id, {})
        source = review_side(
            schema_dataset.get("source", {}), profile_dataset.get("source", {}), manifest_hints
        )
        target = review_side(
            schema_dataset.get("target", {}), profile_dataset.get("target", {}), manifest_hints
        )
        source_flags = {item["column_name"]: item for item in source["flagged_columns"]}
        target_flags = {item["column_name"]: item for item in target["flagged_columns"]}
        mapping_mentions = build_mapping_mentions(
            mappings_by_dataset.get(dataset_id, []), source_flags, target_flags
        )
        contract_mentions = build_contract_mentions(
            contracts_by_dataset.get(dataset_id, []), target_flags
        )
        warnings = [*source["warnings"], *target["warnings"]]
        datasets.append(
            {
                "dataset_id": dataset_id,
                "status": "reviewed" if not warnings else "warning",
                "source": source,
                "target": target,
                "mapping_mentions": mapping_mentions,
                "contract_mentions": contract_mentions,
                "warnings": warnings,
            }
        )
    return {
        "artifact_type": "sensitive_field_review",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "sensitive_field_review_created",
        "review_scope": "column_name_indicators",
        "datasets": datasets,
        "summary": build_summary(datasets),
        "notes": [SENSITIVE_FIELD_REVIEW_NOTE],
    }


def group_by_dataset(reviews: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for review in reviews:
        dataset_id = review.get("dataset_id")
        if isinstance(dataset_id, str):
            grouped.setdefault(dataset_id, []).append(review)
    return grouped


def review_side(
    schema_side: dict[str, Any], profile_side: dict[str, Any], manifest_hints: list[str]
) -> dict[str, Any]:
    columns = list(schema_side.get("columns", []))
    flagged_columns = [flag_column(column, manifest_hints) for column in columns]
    flagged = [flag for flag in flagged_columns if flag]
    warnings = list(schema_side.get("warnings", []))
    if profile_side.get("status") == "gap_found":
        warnings.extend(profile_side.get("warnings", []))
    return {
        "path": schema_side.get("path", profile_side.get("path")),
        "status": "reviewed" if not warnings else "warning",
        "flagged_columns": flagged,
        "flagged_column_count": len(flagged),
        "warnings": unique_in_order(warnings),
    }


def flag_column(column_name: str, manifest_hints: list[str]) -> dict[str, Any] | None:
    for hint in manifest_hints:
        if names_match(column_name, hint):
            return {
                "column_name": column_name,
                "indicator_type": "manifest_hint",
                "matched_indicator": hint,
                "confidence": "high",
                "evidence": ["column_name_match"],
            }
    for indicator in BUILT_IN_INDICATORS:
        if names_match(column_name, indicator):
            return {
                "column_name": column_name,
                "indicator_type": "built_in_column_name_pattern",
                "matched_indicator": indicator,
                "confidence": "medium",
                "evidence": ["column_name_match"],
            }
    return None


def names_match(column_name: str, indicator: str) -> bool:
    return column_name.casefold() == indicator.casefold() or normalize_name(
        column_name
    ) == normalize_name(indicator)


def normalize_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character not in {"_", "-", " "})


def build_mapping_mentions(
    mapping_reviews: list[dict[str, Any]],
    source_flags: dict[str, dict[str, Any]],
    target_flags: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    mentions: list[dict[str, Any]] = []
    for review in mapping_reviews:
        for row in review.get("reviewed_mapping_rows", []):
            source_field = row.get("source_field", "")
            target_field = row.get("target_field", "")
            source_flag = source_flags.get(source_field)
            target_flag = target_flags.get(target_field)
            flag = source_flag or target_flag
            if flag:
                mentions.append(
                    {
                        "source_field": source_field,
                        "target_field": target_field,
                        "indicator_type": flag["indicator_type"],
                        "matched_indicator": flag["matched_indicator"],
                    }
                )
    return mentions


def build_contract_mentions(
    contract_reviews: list[dict[str, Any]], target_flags: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    mentions: list[dict[str, Any]] = []
    for review in contract_reviews:
        for field in review.get("contract_fields", []):
            field_name = field.get("name", "")
            flag = target_flags.get(field_name)
            if flag:
                mentions.append(
                    {
                        "field_name": field_name,
                        "indicator_type": flag["indicator_type"],
                        "matched_indicator": flag["matched_indicator"],
                    }
                )
    return mentions


def build_summary(datasets: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "datasets_reviewed": len(datasets),
        "flagged_source_columns": sum(
            dataset["source"]["flagged_column_count"] for dataset in datasets
        ),
        "flagged_target_columns": sum(
            dataset["target"]["flagged_column_count"] for dataset in datasets
        ),
        "datasets_with_sensitive_indicators": sum(
            1
            for dataset in datasets
            if dataset["source"]["flagged_column_count"]
            or dataset["target"]["flagged_column_count"]
        ),
        "files_with_gaps": sum(
            1
            for dataset in datasets
            for side in (dataset["source"], dataset["target"])
            if side["warnings"]
        ),
    }


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
