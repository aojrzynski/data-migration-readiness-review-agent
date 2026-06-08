"""
Reviews YAML/YML contract files against target schemas and profiles. It checks field
presence, required null counts, and simple type compatibility without providing legal or
compliance certification.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.manifest import load_yaml_text, resolve_inside_pack
from data_migration_readiness_review_agent.models import LoadedManifest

CONTRACT_REVIEW_FILE_NAME = "contract_review.json"
CONTRACT_REVIEW_NOTE = (
    "PR #4 reviews contract files against profiled target schemas only. It does not run "
    "reconciliation, call an LLM, or assess readiness."
)


def build_contract_review(
    loaded_manifest: LoadedManifest,
    dataset_profiles: dict[str, Any],
    schema_inventory: dict[str, Any],
) -> dict[str, Any]:
    """
    Build contract_review.json from declared contract files, target schemas, and target
    profiles without treating contracts as certification artifacts.
    """
    profiles_by_dataset = {
        dataset["dataset_id"]: dataset for dataset in dataset_profiles["datasets"]
    }
    schema_by_dataset = {dataset["dataset_id"]: dataset for dataset in schema_inventory["datasets"]}
    reviews = [
        review_contract_entry(loaded_manifest, contract, profiles_by_dataset, schema_by_dataset)
        for contract in loaded_manifest.data.get("contracts", [])
    ]
    return {
        "artifact_type": "contract_review",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "contract_review_created",
        "contract_reviews": reviews,
        "summary": build_contract_summary(reviews),
        "notes": [CONTRACT_REVIEW_NOTE],
    }


def review_contract_entry(
    loaded_manifest: LoadedManifest,
    contract: dict[str, Any],
    profiles_by_dataset: dict[str, dict[str, Any]],
    schema_by_dataset: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Review one contract file and return field checks or a failed-check artifact if the
    file is missing or malformed.
    """
    manifest_contract_id = contract.get("contract_id", contract["path"])
    dataset_id = contract.get("dataset_id")
    relative_path = contract["path"]
    target_columns = list(
        schema_by_dataset.get(dataset_id, {}).get("target", {}).get("columns", [])
    )
    target_profile_columns = target_profile_columns_by_name(profiles_by_dataset.get(dataset_id, {}))
    review = base_contract_review(manifest_contract_id, dataset_id, relative_path, target_columns)
    resolved_path = resolve_inside_pack(
        loaded_manifest.pack_path,
        Path(relative_path),
        description=f"contract:{manifest_contract_id}",
    )

    if not resolved_path.exists() or not resolved_path.is_file():
        # Missing contracts are captured as gaps instead of stopping the run.
        review["status"] = "gap_found"
        review["warnings"].append(f"Contract YAML file is missing: {relative_path}")
        return review

    try:
        parsed = parse_contract_yaml(resolved_path)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        # Malformed contracts produce failed-check artifacts that humans can inspect.
        review["status"] = "failed_check"
        review["warnings"].append(f"Contract YAML could not be parsed: {exc}")
        return review

    if not isinstance(parsed, dict):
        review["status"] = "failed_check"
        review["warnings"].append("Contract YAML top level must be a mapping.")
        return review

    file_contract_id = parsed.get("contract_id")
    if isinstance(file_contract_id, str) and file_contract_id.strip():
        review["contract_id_from_file"] = file_contract_id.strip()
    file_dataset_id = parsed.get("dataset_id")
    if isinstance(file_dataset_id, str) and file_dataset_id.strip():
        review["dataset_id_from_file"] = file_dataset_id.strip()
        if dataset_id is not None and file_dataset_id.strip() != dataset_id:
            review["warnings"].append(
                "Contract file dataset_id "
                f"'{file_dataset_id.strip()}' does not match manifest dataset_id "
                f"'{dataset_id}'."
            )

    fields = parsed.get("fields")
    if not isinstance(fields, list):
        review["status"] = "failed_check"
        review["warnings"].append("Contract field 'fields' must be a list.")
        return review

    field_reviews, validation_warnings = build_contract_field_reviews(
        manifest_contract_id, fields, target_columns, target_profile_columns
    )
    review["warnings"].extend(validation_warnings)
    review["contract_fields"] = field_reviews
    contract_field_names = [field["name"] for field in field_reviews if field["name"]]
    review.update(
        {
            "status": "failed_check" if validation_warnings else "reviewed",
            "field_count": len(field_reviews),
            "required_field_count": sum(1 for field in field_reviews if field["required"]),
            "missing_required_target_fields": [
                field["name"]
                for field in field_reviews
                if field["required"] and not field["target_column_present"] and field["name"]
            ],
            "required_target_fields_with_nulls": [
                field["name"]
                for field in field_reviews
                if field["required"] and (field.get("target_null_count") or 0) > 0
            ],
            "type_mismatch_warnings": [
                warning
                for field in field_reviews
                for warning in field["warnings"]
                if "type" in warning.lower()
            ],
            "target_columns_not_in_contract": [
                column for column in target_columns if column not in contract_field_names
            ],
        }
    )
    return review


def parse_contract_yaml(path: Path) -> Any:
    """
    Load one contract YAML/YML file and validate that it has a mapping shape usable by
    the deterministic checks.
    """
    text = path.read_text(encoding="utf-8")
    yaml_spec = importlib.util.find_spec("yaml")
    if yaml_spec is not None:
        import yaml

        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ValueError(exc) from exc
    return load_yaml_text(text)


def base_contract_review(
    contract_id: str, dataset_id: str | None, relative_path: str, target_columns: list[str]
) -> dict[str, Any]:
    """Create the default contract review structure before file-specific checks are added."""
    return {
        "contract_id": contract_id,
        "dataset_id": dataset_id,
        "path": relative_path,
        "status": "reviewed",
        "field_count": 0,
        "required_field_count": 0,
        "target_columns": target_columns,
        "contract_fields": [],
        "missing_required_target_fields": [],
        "required_target_fields_with_nulls": [],
        "type_mismatch_warnings": [],
        "target_columns_not_in_contract": target_columns,
        "warnings": [],
    }


def target_profile_columns_by_name(dataset_profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Index target profile columns by name for inferred types and null counts.
    """
    target = dataset_profile.get("target", {})
    return {column["name"]: column for column in target.get("columns", [])}


def build_contract_field_reviews(
    contract_id: str,
    fields: list[Any],
    target_columns: list[str],
    target_profile_columns: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Build per-field contract checks using observed target columns and profiled null
    counts.
    """
    reviews: list[dict[str, Any]] = []
    validation_warnings: list[str] = []
    target_column_set = set(target_columns)
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            # Validate field shape before field checks so malformed contracts stay readable.
            validation_warnings.append(f"Contract field at index {index} must be a mapping.")
            continue
        name_value = field.get("name")
        name = name_value.strip() if isinstance(name_value, str) else ""
        if not name:
            validation_warnings.append(
                f"Contract field at index {index} is missing a non-empty name."
            )
        type_value = field.get("type")
        expected_type = type_value.strip().lower() if isinstance(type_value, str) else None
        if type_value is not None and not isinstance(type_value, str):
            validation_warnings.append(
                f"Contract field '{name or index}' type must be a string when present."
            )
        required = field.get("required", False)
        if not isinstance(required, bool):
            validation_warnings.append(
                f"Contract field '{name or index}' required flag must be a boolean when present."
            )
            required = False
        reviews.append(
            build_contract_field_review(
                contract_id,
                name,
                required,
                expected_type,
                target_column_set,
                target_profile_columns,
            )
        )
    return reviews, validation_warnings


def build_contract_field_review(
    contract_id: str,
    name: str,
    required: bool,
    expected_type: str | None,
    target_columns: set[str],
    target_profile_columns: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Check one contract field for presence, required-value null counts, and simple
    inferred-type compatibility.
    """
    target_present = name in target_columns
    target_profile = target_profile_columns.get(name, {})
    target_type = target_profile.get("inferred_type") if target_present else None
    target_null_count = target_profile.get("null_count") if target_present else None
    warnings: list[str] = []
    checks = [
        {
            "check_id": f"contract:{contract_id}:field:{name}:target_present",
            "status": "passed_check" if target_present else "failed_check",
            "message": "Contract field is present in target schema."
            if target_present
            else "Contract field is not present in target schema.",
        }
    ]
    if required and target_present:
        # Required checks use profiled target null counts; the contract file alone is not enough.
        null_check_passed = target_null_count == 0
        checks.append(
            {
                "check_id": f"contract:{contract_id}:field:{name}:required_null_count",
                "status": "passed_check" if null_check_passed else "failed_check",
                "message": "Required contract field has no profiled target nulls."
                if null_check_passed
                else "Required contract field has profiled target nulls.",
            }
        )
    if expected_type and target_present:
        compatible, message = type_check(expected_type, str(target_type or ""))
        checks.append(
            {
                "check_id": f"contract:{contract_id}:field:{name}:type_check",
                "status": "passed_check" if compatible else "warning",
                "message": message,
            }
        )
        if not compatible:
            warnings.append(message)

    status = (
        "passed_check" if all(check["status"] == "passed_check" for check in checks) else "warning"
    )
    if any(check["status"] == "failed_check" for check in checks):
        status = "failed_check"
    return {
        "name": name,
        "required": required,
        "expected_type": expected_type,
        "target_column_present": target_present,
        "target_inferred_type": target_type,
        "target_null_count": target_null_count,
        "checks": checks,
        "warnings": warnings,
        "status": status,
    }


def type_check(expected_type: str, inferred_type: str) -> tuple[bool, str]:
    """
    Compare a declared contract type to an inferred CSV type using conservative
    compatibility rules.
    """
    if not inferred_type or inferred_type == "empty":
        return (
            False,
            f"Expected type '{expected_type}' could not be checked against empty target type.",
        )
    # Text is compatible with narrower inferred CSV types because CSV inference may be specific.
    compatible_types = {
        "integer": {"integer"},
        "decimal": {"decimal", "integer"},
        "text": {"text", "integer", "decimal", "boolean", "date", "datetime", "mixed"},
        "date": {"date"},
        "datetime": {"datetime"},
        "boolean": {"boolean"},
    }
    allowed = compatible_types.get(expected_type)
    if allowed is None:
        return False, f"Expected type '{expected_type}' is not in the local compatibility map."
    if inferred_type in allowed:
        return (
            True,
            f"Expected type '{expected_type}' is compatible with target type '{inferred_type}'.",
        )
    return (
        False,
        f"Expected type '{expected_type}' differs from target inferred type '{inferred_type}'.",
    )


def build_contract_summary(reviews: list[dict[str, Any]]) -> dict[str, int]:
    """Count contract review outcomes for the contract_review.json summary."""
    return {
        "contracts_expected": len(reviews),
        "contracts_reviewed": sum(1 for review in reviews if review["status"] == "reviewed"),
        "contract_files_with_gaps": sum(1 for review in reviews if review["status"] == "gap_found"),
        "contract_files_failed_checks": sum(
            1 for review in reviews if review["status"] == "failed_check"
        ),
        "contract_fields_reviewed": sum(int(review["field_count"]) for review in reviews),
        "missing_required_target_fields": sum(
            len(review["missing_required_target_fields"]) for review in reviews
        ),
        "required_target_fields_with_nulls": sum(
            len(review["required_target_fields_with_nulls"]) for review in reviews
        ),
        "type_mismatch_warnings": sum(len(review["type_mismatch_warnings"]) for review in reviews),
    }
