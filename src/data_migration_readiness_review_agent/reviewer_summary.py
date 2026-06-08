"""
Renders reviewer_summary.md deterministically from review_pack.json. The Markdown is the
first file for a human to open, groups findings and checklist items, includes no raw
data values, and is checked for safe language before writing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent.review_pack import CATEGORY_TITLES
from data_migration_readiness_review_agent.safe_language import assert_safe_generated_text

REVIEWER_SUMMARY_NOTE = (
    "PR #7 writes a deterministic reviewer summary for human review only. It does not assess "
    "readiness, approve migration, decide go-live, certify compliance, or replace human review."
)

ARTIFACT_PURPOSES = {
    "migration_inventory.json": "Lists manifest-declared files and file-presence gaps.",
    "dataset_profiles.json": "Profiles CSV headers, row counts, nulls, types, and duplicate keys.",
    "schema_inventory.json": "Lists source and target columns and key-column presence.",
    "mapping_review.json": "Reviews mapping files against source and target schemas.",
    "contract_review.json": (
        "Reviews contract files against target schemas and profiled target fields."
    ),
    "reconciliation_results.json": (
        "Checks row counts, key overlap, and direct mapped-field comparisons."
    ),
    "sensitive_field_review.json": "Records sensitive-field indicators from column names.",
    "test_evidence_review.json": "Reviews supplied test evidence structure and test status counts.",
    "evidence_coverage_review.json": "Checks declared expected evidence types and file presence.",
    "review_pack.json": "Aggregates deterministic findings and human follow-up checklist items.",
    "reviewer_summary.md": "Provides this human-readable deterministic summary.",
    "migration_readiness_trace.json": (
        "Records run settings, artifact paths, summaries, and boundary notes."
    ),
}

SUMMARY_COUNT_LABELS = [
    ("datasets", "Datasets"),
    ("referenced_files_missing", "Missing referenced files"),
    ("dataset_files_with_gaps", "Dataset files with gaps"),
    ("row_count_failures", "Row count failures"),
    ("missing_source_keys_in_target", "Missing source keys in target"),
    ("unexpected_target_keys", "Unexpected target keys"),
    ("mismatched_cells", "Mismatched cells"),
    ("datasets_with_sensitive_indicators", "Datasets with sensitive-field indicators"),
    ("failed_like_test_rows", "Failed-like test rows"),
    ("warning_like_test_rows", "Warning-like test rows"),
    ("evidence_types_missing", "Missing evidence types"),
    ("follow_up_items", "Follow-up items"),
]


def build_reviewer_summary_markdown(review_pack: dict[str, Any]) -> str:
    """
    Render deterministic Markdown from review_pack.json so the summary matches the
    machine-readable aggregation layer.
    """
    # Render Markdown from review_pack so the readable summary matches JSON evidence.
    migration = review_pack["migration"]
    lines: list[str] = [
        "# Data Migration Review Summary",
        "",
        "## Scope",
        "",
        f"- Migration: {migration.get('name', '')}",
        f"- Source system: {migration.get('source_system', '')}",
        f"- Target system: {migration.get('target_system', '')}",
        "- Generated artifacts: "
        + ", ".join(
            review_pack["source_artifacts"]
            + ["review_pack.json", "reviewer_summary.md", "migration_readiness_trace.json"]
        ),
        "",
        "## Important boundary",
        "",
        (
            "This summary organises deterministic evidence for human review. It does not assess "
            "readiness, approve migration, decide go-live, certify compliance, or replace human "
            "review."
        ),
        "",
        "## Artifact index",
        "",
        "| Artifact | Purpose |",
        "|---|---|",
    ]
    for artifact in review_pack["source_artifacts"] + [
        "review_pack.json",
        "reviewer_summary.md",
        "migration_readiness_trace.json",
    ]:
        lines.append(f"| {artifact} | {ARTIFACT_PURPOSES[artifact]} |")
    lines.extend(["", "## Summary counts", "", "| Count | Value |", "|---|---:|"])
    summary = review_pack["summary"]
    for key, label in SUMMARY_COUNT_LABELS:
        lines.append(f"| {label} | {summary.get(key, 0)} |")
    lines.extend(["", "## Findings for human review", ""])
    for category, title in CATEGORY_TITLES.items():
        lines.extend([f"### {title}", ""])
        category_findings = [
            finding for finding in review_pack["findings"] if finding["category"] == category
        ]
        if not category_findings:
            lines.extend(["No findings generated for this category.", ""])
            continue
        for item in category_findings:
            dataset_text = f" Dataset: {item['dataset_id']}." if "dataset_id" in item else ""
            lines.append(
                f"- Severity: {item['severity']}. Status: {item['status']}. "
                f"{item['message']}{dataset_text} Source: {item['source_artifact']}"
            )
        lines.append("")
    lines.extend(["## Follow-up checklist", ""])
    if review_pack["follow_up_checklist"]:
        for item in review_pack["follow_up_checklist"]:
            lines.append(f"- [ ] {item['message']} Source: {item['source_artifact']}")
    else:
        lines.append("No follow-up checklist items generated.")
    lines.extend(
        [
            "",
            "## Non-goals in this run",
            "",
            "The run did not:",
            "",
            "- assess readiness",
            "- approve migration",
            "- decide go-live",
            "- certify compliance/security/privacy/legal/governance status",
            "- call an LLM",
            "- use LangGraph",
            "- connect to cloud services",
            "",
        ]
    )
    markdown = "\n".join(lines)
    # Run safe-language validation before writing the first file a reviewer opens.
    assert_safe_generated_text(markdown, context="reviewer_summary.md")
    return markdown


def write_reviewer_summary(review_pack: dict[str, Any], output_dir: Path, file_name: str) -> Path:
    """
    Write reviewer_summary.md after rendering from review_pack and passing safe-language
    validation.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / file_name
    path.write_text(build_reviewer_summary_markdown(review_pack), encoding="utf-8")
    return path
