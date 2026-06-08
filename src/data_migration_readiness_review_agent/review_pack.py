from __future__ import annotations

import json
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.artifacts import (
    CONTRACT_REVIEW_FILE_NAME,
    DATASET_PROFILES_FILE_NAME,
    EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
    INVENTORY_FILE_NAME,
    MAPPING_REVIEW_FILE_NAME,
    RECONCILIATION_RESULTS_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    SENSITIVE_FIELD_REVIEW_FILE_NAME,
    TEST_EVIDENCE_REVIEW_FILE_NAME,
)
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.safe_language import assert_safe_generated_text

REVIEW_PACK_NOTE = (
    "PR #7 aggregates deterministic review artifacts for human review. It does not assess "
    "readiness, approve migration, decide go-live, certify legal/privacy/compliance status, "
    "call an LLM, or replace human review."
)

SOURCE_ARTIFACTS = [
    INVENTORY_FILE_NAME,
    DATASET_PROFILES_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    MAPPING_REVIEW_FILE_NAME,
    CONTRACT_REVIEW_FILE_NAME,
    RECONCILIATION_RESULTS_FILE_NAME,
    SENSITIVE_FIELD_REVIEW_FILE_NAME,
    TEST_EVIDENCE_REVIEW_FILE_NAME,
    EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
]

CATEGORY_TITLES = {
    "inventory": "Migration pack inventory",
    "dataset_profiling": "Dataset profiling",
    "mapping": "Mapping",
    "contracts": "Contracts",
    "reconciliation": "Reconciliation",
    "sensitive_field_indicators": "Sensitive-field indicators",
    "test_evidence": "Test evidence",
    "evidence_coverage": "Evidence coverage",
}


def build_review_pack(
    *,
    inventory: dict[str, Any],
    dataset_profiles: dict[str, Any],
    mapping_review: dict[str, Any],
    contract_review: dict[str, Any],
    reconciliation_results: dict[str, Any],
    sensitive_field_review: dict[str, Any],
    test_evidence_review: dict[str, Any],
    evidence_coverage_review: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    findings.extend(inventory_findings(inventory))
    findings.extend(dataset_profile_findings(dataset_profiles))
    findings.extend(mapping_findings(mapping_review))
    findings.extend(contract_findings(contract_review))
    findings.extend(reconciliation_findings(reconciliation_results))
    findings.extend(sensitive_field_findings(sensitive_field_review))
    findings.extend(test_evidence_findings(test_evidence_review))
    findings.extend(evidence_coverage_findings(evidence_coverage_review))
    follow_up = build_follow_up_checklist(findings)
    pack = {
        "artifact_type": "review_pack",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "review_pack_created",
        "migration": dict(inventory["migration"]),
        "source_artifacts": SOURCE_ARTIFACTS,
        "summary": build_summary(
            inventory,
            dataset_profiles,
            mapping_review,
            contract_review,
            reconciliation_results,
            sensitive_field_review,
            test_evidence_review,
            evidence_coverage_review,
            len(follow_up),
        ),
        "sections": build_sections(findings),
        "findings": findings,
        "follow_up_checklist": follow_up,
        "notes": [REVIEW_PACK_NOTE],
    }
    assert_safe_generated_text(
        json.dumps(pack, sort_keys=True), context="review_pack.json generated wording"
    )
    return pack


def finding(
    *,
    finding_id: str,
    category: str,
    status: str,
    severity: str,
    message: str,
    source_artifact: str,
    path: str,
    dataset_id: str | None = None,
    human_follow_up: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "finding_id": finding_id,
        "category": category,
        "status": status,
        "severity": severity,
        "message": message,
        "source_artifact": source_artifact,
        "evidence": {"artifact": source_artifact, "path": path},
    }
    if dataset_id:
        item["dataset_id"] = dataset_id
    if human_follow_up:
        item["human_follow_up"] = human_follow_up
    return item


def inventory_findings(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        finding(
            finding_id=f"inventory:{gap['gap_id']}",
            category="inventory",
            status="gap_found",
            severity="high",
            message=gap["message"],
            source_artifact=INVENTORY_FILE_NAME,
            path=f"gaps[{index}]",
            human_follow_up="Locate or update the missing manifest reference.",
        )
        for index, gap in enumerate(inventory.get("gaps", []))
    ]


def dataset_profile_findings(dataset_profiles: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, dataset in enumerate(dataset_profiles.get("datasets", [])):
        dataset_id = dataset["dataset_id"]
        for side_name in ("source", "target"):
            side = dataset[side_name]
            base_path = f"datasets[{index}].{side_name}"
            if side.get("status") in {"gap_found", "failed_check"}:
                findings.append(
                    finding(
                        finding_id=f"dataset_profile:{dataset_id}:{side_name}:gap",
                        category="dataset_profiling",
                        status=side["status"],
                        severity="high",
                        dataset_id=dataset_id,
                        message=f"{side_name.title()} dataset profile has file or parsing gaps.",
                        source_artifact=DATASET_PROFILES_FILE_NAME,
                        path=base_path,
                        human_follow_up="Review the dataset file reference and CSV structure.",
                    )
                )
            if side.get("missing_key_columns"):
                findings.append(
                    finding(
                        finding_id=f"dataset_profile:{dataset_id}:{side_name}:missing_key_columns",
                        category="dataset_profiling",
                        status="failed_check",
                        severity="high",
                        dataset_id=dataset_id,
                        message=(
                            f"{side_name.title()} dataset is missing key column(s): "
                            + ", ".join(side["missing_key_columns"])
                        ),
                        source_artifact=DATASET_PROFILES_FILE_NAME,
                        path=f"{base_path}.missing_key_columns",
                        human_follow_up="Confirm the expected key columns for this dataset.",
                    )
                )
            if int(side.get("duplicate_key_count", 0)):
                findings.append(
                    finding(
                        finding_id=f"dataset_profile:{dataset_id}:{side_name}:duplicate_keys",
                        category="dataset_profiling",
                        status="warning",
                        severity="medium",
                        dataset_id=dataset_id,
                        message=(
                            f"{side_name.title()} dataset has "
                            f"{side['duplicate_key_count']} duplicate key row(s)."
                        ),
                        source_artifact=DATASET_PROFILES_FILE_NAME,
                        path=f"{base_path}.duplicate_key_count",
                        human_follow_up=(
                            "Review duplicate keys before relying on key-based comparisons."
                        ),
                    )
                )
            if side.get("status") == "profile_created" and int(side.get("row_count", 0)) == 0:
                findings.append(
                    finding(
                        finding_id=f"dataset_profile:{dataset_id}:{side_name}:empty_csv",
                        category="dataset_profiling",
                        status="warning",
                        severity="medium",
                        dataset_id=dataset_id,
                        message=f"{side_name.title()} dataset profile has zero data rows.",
                        source_artifact=DATASET_PROFILES_FILE_NAME,
                        path=f"{base_path}.row_count",
                        human_follow_up="Confirm whether an empty dataset is expected.",
                    )
                )
    return findings


def mapping_findings(mapping_review: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, review in enumerate(mapping_review.get("mapping_reviews", [])):
        dataset_id = review.get("dataset_id")
        base = f"mapping_reviews[{index}]"
        if review.get("status") == "gap_found":
            findings.append(
                _mapping_finding(
                    review, base, "missing_file", "gap_found", "high", "Mapping file is missing."
                )
            )
        elif review.get("status") == "failed_check":
            findings.append(
                _mapping_finding(
                    review,
                    base,
                    "failed_check",
                    "failed_check",
                    "high",
                    "Mapping file failed structural checks.",
                )
            )
        for field_name, severity, message in (
            (
                "missing_source_field_references",
                "high",
                "Mapping references source fields not found in the source schema.",
            ),
            (
                "missing_target_field_references",
                "high",
                "Mapping references target fields not found in the target schema.",
            ),
            ("duplicate_source_mappings", "medium", "Duplicate source field mappings were found."),
            ("duplicate_target_mappings", "medium", "Duplicate target field mappings were found."),
            (
                "unmapped_target_columns",
                "medium",
                "Target columns are not covered by the mapping file.",
            ),
        ):
            if review.get(field_name):
                findings.append(
                    finding(
                        finding_id=f"mapping:{review['mapping_id']}:{field_name}",
                        category="mapping",
                        status="warning" if severity == "medium" else "failed_check",
                        severity=severity,
                        dataset_id=dataset_id,
                        message=message,
                        source_artifact=MAPPING_REVIEW_FILE_NAME,
                        path=f"{base}.{field_name}",
                        human_follow_up=(
                            "Review the mapping file against source and target schemas."
                        ),
                    )
                )
    return findings


def _mapping_finding(
    review: dict[str, Any], base: str, suffix: str, status: str, severity: str, message: str
) -> dict[str, Any]:
    return finding(
        finding_id=f"mapping:{review['mapping_id']}:{suffix}",
        category="mapping",
        status=status,
        severity=severity,
        dataset_id=review.get("dataset_id"),
        message=message,
        source_artifact=MAPPING_REVIEW_FILE_NAME,
        path=base,
        human_follow_up="Review the manifest mapping reference and mapping CSV structure.",
    )


def contract_findings(contract_review: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, review in enumerate(contract_review.get("contract_reviews", [])):
        base = f"contract_reviews[{index}]"
        if review.get("status") == "gap_found":
            findings.append(
                _contract_finding(
                    review, base, "missing_file", "gap_found", "high", "Contract file is missing."
                )
            )
        elif review.get("status") == "failed_check":
            findings.append(
                _contract_finding(
                    review,
                    base,
                    "failed_check",
                    "failed_check",
                    "high",
                    "Contract file failed structural checks.",
                )
            )
        for field_name, severity, status, message in (
            (
                "missing_required_target_fields",
                "high",
                "failed_check",
                "Required contract fields are missing from the target schema.",
            ),
            (
                "required_target_fields_with_nulls",
                "high",
                "failed_check",
                "Required contract fields have profiled target nulls.",
            ),
            ("type_mismatch_warnings", "medium", "warning", "Contract type warnings were found."),
        ):
            if review.get(field_name):
                findings.append(
                    finding(
                        finding_id=f"contract:{review['contract_id']}:{field_name}",
                        category="contracts",
                        status=status,
                        severity=severity,
                        dataset_id=review.get("dataset_id"),
                        message=message,
                        source_artifact=CONTRACT_REVIEW_FILE_NAME,
                        path=f"{base}.{field_name}",
                        human_follow_up=(
                            "Review the contract file against target schema expectations."
                        ),
                    )
                )
    return findings


def _contract_finding(
    review: dict[str, Any], base: str, suffix: str, status: str, severity: str, message: str
) -> dict[str, Any]:
    return finding(
        finding_id=f"contract:{review['contract_id']}:{suffix}",
        category="contracts",
        status=status,
        severity=severity,
        dataset_id=review.get("dataset_id"),
        message=message,
        source_artifact=CONTRACT_REVIEW_FILE_NAME,
        path=base,
        human_follow_up="Review the manifest contract reference and contract structure.",
    )


def reconciliation_findings(reconciliation_results: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, dataset in enumerate(reconciliation_results.get("datasets", [])):
        dataset_id = dataset["dataset_id"]
        base = f"datasets[{index}]"
        row_count = dataset["row_count_check"]
        key_overlap = dataset["key_overlap"]
        field_comparison = dataset["field_comparison"]
        duplicates = dataset["duplicate_key_counts"]
        if row_count["status"] == "failed_check":
            findings.append(
                _recon(
                    dataset_id,
                    "row_count",
                    "failed_check",
                    "high",
                    "Row-count check exceeded the configured tolerance.",
                    f"{base}.row_count_check",
                )
            )
        if key_overlap["missing_source_keys_in_target_count"]:
            findings.append(
                _recon(
                    dataset_id,
                    "missing_source_keys_in_target",
                    "failed_check",
                    "high",
                    "Source keys are missing in the target dataset.",
                    f"{base}.key_overlap",
                )
            )
        if key_overlap["unexpected_target_keys_count"]:
            findings.append(
                _recon(
                    dataset_id,
                    "unexpected_target_keys",
                    "failed_check",
                    "high",
                    "Unexpected target keys were found.",
                    f"{base}.key_overlap",
                )
            )
        if field_comparison["mismatched_cell_count"]:
            findings.append(
                _recon(
                    dataset_id,
                    "mismatched_cells",
                    "failed_check",
                    "high",
                    "Mapped-field mismatches were found for this dataset.",
                    f"{base}.field_comparison",
                )
            )
        if duplicates["source_duplicate_key_count"] or duplicates["target_duplicate_key_count"]:
            findings.append(
                _recon(
                    dataset_id,
                    "duplicate_keys",
                    "warning",
                    "medium",
                    "Duplicate key warnings were found for reconciliation inputs.",
                    f"{base}.duplicate_key_counts",
                )
            )
        if field_comparison["status"] == "skipped" or field_comparison["skipped_mapping_count"]:
            findings.append(
                _recon(
                    dataset_id,
                    "skipped_field_comparison",
                    "skipped",
                    "medium",
                    "Mapped-field comparison was skipped or partially skipped.",
                    f"{base}.field_comparison",
                )
            )
    return findings


def _recon(
    dataset_id: str, suffix: str, status: str, severity: str, message: str, path: str
) -> dict[str, Any]:
    return finding(
        finding_id=f"reconciliation:{dataset_id}:{suffix}",
        category="reconciliation",
        status=status,
        severity=severity,
        dataset_id=dataset_id,
        message=message,
        source_artifact=RECONCILIATION_RESULTS_FILE_NAME,
        path=path,
        human_follow_up=(
            "Review reconciliation details and determine whether differences are expected."
        ),
    )


def sensitive_field_findings(sensitive_field_review: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, dataset in enumerate(sensitive_field_review.get("datasets", [])):
        dataset_id = dataset["dataset_id"]
        total = (
            dataset["source"]["flagged_column_count"] + dataset["target"]["flagged_column_count"]
        )
        if total:
            findings.append(
                finding(
                    finding_id=f"sensitive_field_indicators:{dataset_id}:columns",
                    category="sensitive_field_indicators",
                    status="warning",
                    severity="medium",
                    dataset_id=dataset_id,
                    message="Sensitive-field indicators were found by column name.",
                    source_artifact=SENSITIVE_FIELD_REVIEW_FILE_NAME,
                    path=f"datasets[{index}]",
                    human_follow_up="Confirm handling expectations for the indicated fields.",
                )
            )
        if dataset.get("warnings"):
            findings.append(
                finding(
                    finding_id=f"sensitive_field_indicators:{dataset_id}:file_gaps",
                    category="sensitive_field_indicators",
                    status="warning",
                    severity="medium",
                    dataset_id=dataset_id,
                    message="Sensitive-field indicator review has file or schema gaps.",
                    source_artifact=SENSITIVE_FIELD_REVIEW_FILE_NAME,
                    path=f"datasets[{index}].warnings",
                    human_follow_up="Review source files for the sensitive-field indicator check.",
                )
            )
    return findings


def test_evidence_findings(test_evidence_review: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, review in enumerate(test_evidence_review.get("test_results", [])):
        base = f"test_results[{index}]"
        test_id = review["test_result_id"]
        if review.get("status") == "gap_found":
            findings.append(
                finding(
                    finding_id=f"test_evidence:{test_id}:missing_file",
                    category="test_evidence",
                    status="gap_found",
                    severity="high",
                    message="Test result file is missing.",
                    source_artifact=TEST_EVIDENCE_REVIEW_FILE_NAME,
                    path=base,
                    human_follow_up="Locate the missing test result file or update the manifest.",
                )
            )
        elif review.get("status") == "failed_check":
            findings.append(
                finding(
                    finding_id=f"test_evidence:{test_id}:parse_failure",
                    category="test_evidence",
                    status="failed_check",
                    severity="high",
                    message="CSV test evidence parsing failed.",
                    source_artifact=TEST_EVIDENCE_REVIEW_FILE_NAME,
                    path=base,
                    human_follow_up="Review the test evidence CSV structure.",
                )
            )
        if int(review.get("failed_like_count", 0)):
            findings.append(
                finding(
                    finding_id=f"test_evidence:{test_id}:failed_like_rows",
                    category="test_evidence",
                    status="failed_check",
                    severity="medium",
                    message="Failed-like test evidence rows were found.",
                    source_artifact=TEST_EVIDENCE_REVIEW_FILE_NAME,
                    path=f"{base}.failed_like_count",
                    human_follow_up="Review failed-like test rows in the source artifact.",
                )
            )
        if int(review.get("warning_like_count", 0)):
            findings.append(
                finding(
                    finding_id=f"test_evidence:{test_id}:warning_like_rows",
                    category="test_evidence",
                    status="warning",
                    severity="medium",
                    message="Warning-like test evidence rows were found.",
                    source_artifact=TEST_EVIDENCE_REVIEW_FILE_NAME,
                    path=f"{base}.warning_like_count",
                    human_follow_up="Review warning-like test rows in the source artifact.",
                )
            )
    return findings


def evidence_coverage_findings(evidence_coverage_review: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, item in enumerate(evidence_coverage_review.get("expected_evidence_types", [])):
        evidence_type = item["evidence_type"]
        if item["status"] == "evidence_missing":
            findings.append(
                finding(
                    finding_id=f"evidence_coverage:{evidence_type}:missing_type",
                    category="evidence_coverage",
                    status="evidence_missing",
                    severity="high",
                    message=f"Expected evidence type is missing: {evidence_type}.",
                    source_artifact=EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
                    path=f"expected_evidence_types[{index}]",
                    human_follow_up=(
                        "Provide the expected evidence type or document why it is absent."
                    ),
                )
            )
        elif item["status"] == "gap_found":
            findings.append(
                finding(
                    finding_id=f"evidence_coverage:{evidence_type}:file_gaps",
                    category="evidence_coverage",
                    status="gap_found",
                    severity="high",
                    message=f"Expected evidence type has file gaps: {evidence_type}.",
                    source_artifact=EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
                    path=f"expected_evidence_types[{index}]",
                    human_follow_up="Locate missing evidence files or update manifest references.",
                )
            )
    return findings


def build_follow_up_checklist(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checklist: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for item in findings:
        category = item["category"]
        dataset_id = item.get("dataset_id")
        key = (category, dataset_id)
        if key in seen:
            continue
        seen.add(key)
        checklist_item: dict[str, Any] = {
            "item_id": f"human:{category}" + (f":{dataset_id}" if dataset_id else ""),
            "category": category,
            "status": "follow_up_needed",
            "message": follow_up_message(category, dataset_id),
            "source_artifact": item["source_artifact"],
        }
        if dataset_id:
            checklist_item["dataset_id"] = dataset_id
        checklist.append(checklist_item)
    return checklist


def follow_up_message(category: str, dataset_id: str | None) -> str:
    scope = f" for {dataset_id}" if dataset_id else ""
    messages = {
        "inventory": "Review missing files or evidence gaps in the manifest references.",
        "dataset_profiling": f"Review dataset profiling gaps{scope}.",
        "mapping": f"Review mapping issues{scope}.",
        "contracts": f"Review contract issues{scope}.",
        "reconciliation": f"Review reconciliation mismatches or key issues{scope}.",
        "sensitive_field_indicators": (
            f"Confirm handling expectations for sensitive-field indicators{scope}."
        ),
        "test_evidence": "Review failed or warning-like test evidence rows.",
        "evidence_coverage": "Review missing expected evidence types or evidence file gaps.",
    }
    return messages[category]


def build_sections(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "section_id": category,
            "title": title,
            "status": "reviewed",
            "finding_ids": [
                item["finding_id"] for item in findings if item["category"] == category
            ],
            "summary": {
                "findings": sum(1 for item in findings if item["category"] == category),
                "follow_up_needed": sum(
                    1
                    for item in findings
                    if item["category"] == category and item.get("human_follow_up")
                ),
            },
        }
        for category, title in CATEGORY_TITLES.items()
    ]


def build_summary(
    inventory: dict[str, Any],
    dataset_profiles: dict[str, Any],
    mapping_review: dict[str, Any],
    contract_review: dict[str, Any],
    reconciliation_results: dict[str, Any],
    sensitive_field_review: dict[str, Any],
    test_evidence_review: dict[str, Any],
    evidence_coverage_review: dict[str, Any],
    follow_up_items: int,
) -> dict[str, int]:
    return {
        "datasets": int(inventory["counts"]["datasets"]),
        "referenced_files_missing": int(inventory["counts"]["referenced_files_missing"]),
        "dataset_files_with_gaps": sum(
            1
            for dataset in dataset_profiles.get("datasets", [])
            for side in (dataset["source"], dataset["target"])
            if side["status"] != "profile_created"
        ),
        "mapping_files_with_gaps": int(mapping_review["summary"].get("mapping_files_with_gaps", 0)),
        "contract_files_with_gaps": int(
            contract_review["summary"].get("contract_files_with_gaps", 0)
        ),
        "row_count_failures": int(reconciliation_results["summary"].get("row_count_failures", 0)),
        "missing_source_keys_in_target": int(
            reconciliation_results["summary"].get("missing_source_keys_in_target", 0)
        ),
        "unexpected_target_keys": int(
            reconciliation_results["summary"].get("unexpected_target_keys", 0)
        ),
        "mismatched_cells": int(reconciliation_results["summary"].get("mismatched_cells", 0)),
        "datasets_with_sensitive_indicators": int(
            sensitive_field_review["summary"].get("datasets_with_sensitive_indicators", 0)
        ),
        "failed_like_test_rows": int(test_evidence_review["summary"].get("failed_like_rows", 0)),
        "warning_like_test_rows": int(test_evidence_review["summary"].get("warning_like_rows", 0)),
        "evidence_types_missing": int(
            evidence_coverage_review["summary"].get("evidence_types_missing", 0)
        ),
        "evidence_types_with_gaps": int(
            evidence_coverage_review["summary"].get("evidence_types_with_gaps", 0)
        ),
        "follow_up_items": follow_up_items,
    }
